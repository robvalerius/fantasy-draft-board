"""2026 projections + VORP + auction dollar values for the active league."""

import numpy as np
import pandas as pd

from league_config import (
    BUDGET,
    DATA_DIR,
    FLEX_ELIGIBLE,
    NUM_TEAMS,
    ROSTER_SIZE,
    SHARED_DATA,
    STARTERS,
)

DATA = SHARED_DATA

# The positions a player can actually be. Everything else in STARTERS is a flex
# slot, resolved through FLEX_ELIGIBLE.
BASE_POSITIONS = ("QB", "RB", "WR", "TE")

SEASON_WEIGHTS = {2025: 0.60, 2024: 0.28, 2023: 0.12}

# Typical games played, used to convert ppg into a season projection
DURABILITY = {"QB": 15.5, "RB": 14.5, "WR": 15.0, "TE": 15.0}

# Age curve: peak years by position, penalty per year beyond
AGE_PEAK = {"QB": 30, "RB": 25, "WR": 27, "TE": 28}
AGE_DECLINE = {"QB": 0.015, "RB": 0.055, "WR": 0.030, "TE": 0.025}
AGE_GROWTH = {"QB": 0.020, "RB": 0.030, "WR": 0.045, "TE": 0.040}

# Auction dollars scale as vorp ** VORP_CONCAVITY. 1.0 is a straight linear split,
# which is far too top-heavy. 0.65 would reproduce the market's top-12 spend exactly;
# 0.75 keeps us modestly above market at the top so genuine edge survives, while
# landing the #1 overall pick near 37% of budget, in line with real auction rooms.
VORP_CONCAVITY = 0.75

# Games at which per-game fantasy scoring stabilizes, used as the empirical-Bayes
# shrinkage constant: a player's own rate gets weight n/(n+k).
PPG_STABILIZE = 12


def _load_sleeper() -> pd.DataFrame:
    import json
    raw = json.loads((DATA / "sleeper_players.json").read_text())
    rows = [
        {
            "name": p["full_name"],
            "position": p["position"],
            "team": p["team"],
            "age": p["age"],
            "years_exp": p["years_exp"],
            "injury_status": p["injury_status"],
            "search_rank": p["search_rank"],
        }
        for p in raw.values()
        if p.get("full_name")
    ]
    return pd.DataFrame(rows)


def _norm(name: str) -> str:
    return (
        str(name).lower()
        .replace(".", "").replace("'", "").replace("-", " ")
        .replace(" jr", "").replace(" sr", "").replace(" iii", "").replace(" ii", "")
        .strip()
    )


def build_projections() -> pd.DataFrame:
    hist = pd.read_csv(DATA_DIR / "scored_history.csv")
    hist["key"] = hist["name"].map(_norm)

    # Weighted per-game average across seasons
    hist["w"] = hist["season"].map(SEASON_WEIGHTS).fillna(0)
    hist["w"] *= hist["games"].clip(0, 17) / 17          # trust full seasons more
    hist["wppg"] = hist["ppg"] * hist["w"]

    agg = hist.groupby(["key", "position"], as_index=False).agg(
        name=("name", "last"),
        team=("team", "last"),
        wppg_sum=("wppg", "sum"),
        w_sum=("w", "sum"),
        games_total=("games", "sum"),
        seasons=("season", "nunique"),
        last_season=("season", "max"),
        best_ppg=("ppg", "max"),
    )
    agg = agg[agg["w_sum"] > 0].copy()
    agg["base_ppg"] = (agg["wppg_sum"] / agg["w_sum"]).round(2)

    # Merge age / injury from Sleeper
    sleeper = _load_sleeper()
    sleeper["key"] = sleeper["name"].map(_norm)
    sleeper = sleeper.drop_duplicates("key")
    df = agg.merge(
        sleeper[["key", "age", "years_exp", "injury_status", "search_rank"]],
        on="key", how="left",
    )

    # Only players still active in 2025
    df = df[df["last_season"] == 2025].copy()

    # Age adjustment
    def age_mult(r):
        age, pos = r["age"], r["position"]
        if pd.isna(age):
            return 1.0
        peak = AGE_PEAK.get(pos, 27)
        if age < peak:
            return min(1.18, 1 + AGE_GROWTH.get(pos, 0.03) * (peak - age))
        return max(0.62, 1 - AGE_DECLINE.get(pos, 0.03) * (age - peak))

    df["age_mult"] = df.apply(age_mult, axis=1).round(3)

    # Small-sample regression toward a positional prior.
    #
    # Two things matter here and both were wrong before.
    #
    # 1. The prior. An unweighted positional mean averages in every third-string
    #    back and one-game callup - 151 "RBs" played in 2025 and most were not
    #    real contributors, dragging the RB mean to 6.98 ppg. A player who
    #    commanded eight starts should be regressed toward the mean of players
    #    who actually play, so the prior is weighted by games. That lifts the RB
    #    prior to 8.94 and stops punishing young starters for the league's
    #    backups.
    #
    # 2. The shape. games/34 is a straight ramp, but the correct empirical-Bayes
    #    weight is n/(n+k), where k is roughly the sample size at which the stat
    #    stabilizes. k=12 games is the usual estimate for fantasy ppg.
    #
    # Together these took Cam Skattebo from 141.8 projected points (regressed 76%
    # toward a replacement-level mean despite a 17.7 ppg rate) to 185.6. The
    # young-to-veteran projection ratio moved from 0.69 to 0.87, which is far
    # closer to how the market prices the same players. Established players are
    # untouched: at 60+ games the weight is already ~0.85 either way.
    weights = df["games_total"].clip(lower=1)
    pos_mean = df["position"].map(
        df.groupby("position").apply(
            lambda g: np.average(g["base_ppg"], weights=g["games_total"].clip(lower=1))
        )
    )
    conf = df["games_total"] / (df["games_total"] + PPG_STABILIZE)
    df["proj_ppg"] = ((df["base_ppg"] * conf + pos_mean * (1 - conf)) * df["age_mult"]).round(2)

    df["proj_games"] = df["position"].map(DURABILITY).fillna(15.0)
    df["proj_points"] = (df["proj_ppg"] * df["proj_games"]).round(1)

    return df.sort_values("proj_points", ascending=False).reset_index(drop=True)


def replacement_levels(df: pd.DataFrame) -> dict[str, float]:
    """Points of the last startable player at each position, flex-aware."""
    need = {
        pos: STARTERS.get(pos, 0) * NUM_TEAMS
        for pos in BASE_POSITIONS
        if STARTERS.get(pos, 0)
    }

    pools = {p: df[df["position"] == p].sort_values("proj_points", ascending=False)
             for p in need}
    taken = {p: need[p] for p in need}

    # Each flex slot takes the best remaining eligible player. FLEX_ELIGIBLE is
    # ordered, which is what breaks exact ties, so iterate it as given.
    for slot, eligible in FLEX_ELIGIBLE.items():
        for _ in range(STARTERS.get(slot, 0) * NUM_TEAMS):
            best_pos, best_val = None, -1e9
            for pos in eligible:
                idx = taken[pos]
                if idx < len(pools[pos]):
                    val = pools[pos].iloc[idx]["proj_points"]
                    if val > best_val:
                        best_pos, best_val = pos, val
            if best_pos:
                taken[best_pos] += 1

    levels = {}
    for pos, idx in taken.items():
        pool = pools[pos]
        i = min(idx, len(pool) - 1)
        levels[pos] = float(pool.iloc[i]["proj_points"])
    return levels


def add_values(df: pd.DataFrame) -> pd.DataFrame:
    levels = replacement_levels(df)
    df = df.copy()
    df["replacement"] = df["position"].map(levels)
    df["vorp"] = (df["proj_points"] - df["replacement"]).round(1)

    # Auction dollars: distribute the leaguewide budget across positive-VORP players.
    # Dollars scale as vorp ** VORP_CONCAVITY, not linearly. A linear split makes the
    # top of the board absurd (our #1 came out at 49% of a single team's budget, where
    # real rooms clear around 35-37%). Two effects justify the concavity: a concentrated
    # bet carries injury/bust risk the linear model ignores, and the player our own
    # projections rank first is there partly because of positive model error, so the
    # top estimates deserve shrinking.
    total_budget = BUDGET * NUM_TEAMS
    roster_slots = ROSTER_SIZE * NUM_TEAMS
    discretionary = total_budget - roster_slots  # $1 minimum reserved per slot

    draftable = df.nlargest(roster_slots, "vorp")
    weight = df["vorp"].clip(lower=0) ** VORP_CONCAVITY
    weight_pool = weight[draftable.index[(draftable["vorp"] > 0).to_numpy()]].sum()

    dollars_per_weight = discretionary / weight_pool if weight_pool else 0
    df["value"] = (weight * dollars_per_weight + 1).round(0).astype(int)
    df.loc[~df.index.isin(draftable.index), "value"] = 0

    return df.sort_values("value", ascending=False).reset_index(drop=True)


def build() -> pd.DataFrame:
    df = add_values(build_projections())
    df["rank"] = range(1, len(df) + 1)
    df["pos_rank"] = df.groupby("position")["value"].rank(ascending=False, method="first").astype(int)
    out = df[[
        "rank", "name", "position", "pos_rank", "team", "age",
        "proj_points", "proj_ppg", "vorp", "value", "injury_status",
        "games_total", "seasons",
    ]]
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(DATA_DIR / "auction_values.csv", index=False)
    return out


if __name__ == "__main__":
    df = build()
    levels = replacement_levels(build_projections())

    print(f"\n=== REPLACEMENT LEVEL ({NUM_TEAMS}-team, flex-aware) ===")
    for pos, pts in sorted(levels.items()):
        print(f"  {pos:4} {pts:7.1f} pts")

    print(f"\n=== TOP 40 AUCTION VALUES (${BUDGET} cap) ===")
    print(f"{'#':>3} {'player':24} {'pos':5} {'proj':>7} {'vorp':>7} {'$':>5}")
    for r in df.head(40).itertuples():
        tag = f"{r.position}{r.pos_rank}"
        print(f"{r.rank:>3} {r.name[:23]:24} {tag:5} {r.proj_points:>7.1f} {r.vorp:>7.1f} {r.value:>4}")

    spend = df["value"].sum()
    print(f"\nTotal allocated: ${spend} across {(df['value'] > 0).sum()} players")
    print(f"League budget:   ${BUDGET * NUM_TEAMS}")
