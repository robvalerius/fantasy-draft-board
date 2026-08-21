"""Score every real NFL player under the active league's rules.

Two grains, chosen by the league config:

  STATS_GRAIN = "season"  one row per player-season, scored once. What the
                          Yahoo board has always done.
  STATS_GRAIN = "week"    one row per player-game, scored individually and then
                          summed. Required when a league pays per-game bonuses
                          such as "20+ carries in a game" - scoring those off a
                          season total would fire them once instead of ten
                          times.
"""

import pandas as pd

from league_config import DATA_DIR, SHARED_DATA, STATS_GRAIN
from scoring import score_offense

# Raw box scores are the same for every league; the scored output is not.
DATA = SHARED_DATA

POSITIONS = ("QB", "RB", "WR", "TE")
SEASONS = (2023, 2024, 2025)

# nflverse column -> our scoring key. This is a superset: a league's OFFENSE
# dict picks out the keys it actually pays for and ignores the rest, so adding
# a key here cannot change a league that does not score it.
OFFENSE_MAP = {
    "completions": "completions",
    "attempts": "pass_attempts",
    "passing_yards": "passing_yards",
    "passing_tds": "passing_tds",
    "passing_interceptions": "interceptions",
    "passing_first_downs": "passing_first_downs",
    "sacks_suffered": "sacks_taken",
    "passing_40": "completions_40_plus",
    "passing_2pt_conversions": "two_point_conversions",
    "carries": "rushing_attempts",
    "rushing_yards": "rushing_yards",
    "rushing_tds": "rushing_tds",
    "rushing_first_downs": "rushing_first_downs",
    "rushing_40": "rushes_40_plus",
    "receptions": "receptions",
    "receiving_yards": "receiving_yards",
    "receiving_tds": "receiving_tds",
    "receiving_first_downs": "receiving_first_downs",
    "receiving_40": "receptions_40_plus",
    "special_teams_tds": "return_tds",
    "fumbles_total": "fumbles",
    "fumbles_lost_total": "fumbles_lost",
}

# Columns carried through to scored_history.csv for downstream display.
CARRY = [
    "attempts", "completions", "passing_yards", "passing_tds", "passing_interceptions",
    "carries", "rushing_yards", "rushing_tds", "rushing_first_downs",
    "targets", "receptions", "receiving_yards", "receiving_tds", "receiving_first_downs",
]

OUT_COLS = ["season", "player_id", "name", "position", "team", "games", "points", "ppg"] + CARRY


def _row_to_stats(row: pd.Series) -> dict:
    stats = {
        ours: float(row.get(theirs) or 0)
        for theirs, ours in OFFENSE_MAP.items()
    }
    # nflverse gives attempts + completions; we need incompletions
    stats["incompletions"] = max(0.0, stats["pass_attempts"] - stats["completions"])

    # Yahoo pays one flat rate for any two-point conversion, so it reads the
    # combined key. Sleeper pays 3/2/3 for pass/rush/rec, so it reads the split
    # keys. Emit both.
    stats["pass_2pt"] = float(row.get("passing_2pt_conversions") or 0)
    stats["rush_2pt"] = float(row.get("rushing_2pt_conversions") or 0)
    stats["rec_2pt"] = float(row.get("receiving_2pt_conversions") or 0)
    stats["two_point_conversions"] += stats["rush_2pt"] + stats["rec_2pt"]
    return stats


def score_season(season: int) -> pd.DataFrame:
    df = pd.read_csv(DATA / f"stats_{season}.csv", low_memory=False)
    df = df[df["position"].isin(POSITIONS)].copy()

    df["points"] = df.apply(
        lambda r: score_offense(_row_to_stats(r), r["position"]), axis=1)
    df["games"] = df["games"].fillna(0).astype(int)
    df["ppg"] = (df["points"] / df["games"].clip(lower=1)).round(2)
    df["season"] = season

    df = df.rename(columns={"player_display_name": "name", "recent_team": "team"})
    return df[OUT_COLS]


def score_season_weekly(season: int) -> pd.DataFrame:
    """Score each game on its own, then roll up to a season line.

    Points are summed from per-game scores, so per-game bonuses fire once for
    every game that earned them. `games` counts games actually played rather
    than trusting a season-file column.
    """
    df = pd.read_csv(DATA / f"stats_week_{season}.csv", low_memory=False)
    df = df[df["position"].isin(POSITIONS) & (df["season_type"] == "REG")].copy()

    df["points"] = df.apply(
        lambda r: score_offense(_row_to_stats(r), r["position"]), axis=1)

    for col in CARRY:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = df[col].fillna(0)

    df = df.sort_values(["player_id", "week"])
    agg = df.groupby("player_id", as_index=False).agg(
        name=("player_display_name", "last"),
        position=("position", "last"),
        team=("team", "last"),
        games=("week", "count"),
        points=("points", "sum"),
        **{c: (c, "sum") for c in CARRY},
    )
    agg["season"] = season
    agg["points"] = agg["points"].round(2)
    agg["ppg"] = (agg["points"] / agg["games"].clip(lower=1)).round(2)

    return agg[OUT_COLS]


def all_seasons() -> pd.DataFrame:
    fn = score_season_weekly if STATS_GRAIN == "week" else score_season
    return pd.concat([fn(s) for s in SEASONS], ignore_index=True)


if __name__ == "__main__":
    df = all_seasons()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATA_DIR / "scored_history.csv", index=False)

    latest = df[df["season"] == 2025].sort_values("points", ascending=False)
    print(f"\n=== 2025 in YOUR scoring: top 20 overall ===\n")
    print(f"{'#':>3} {'player':24} {'pos':4} {'tm':4} {'g':>3} {'pts':>7} {'ppg':>6}")
    for i, r in enumerate(latest.head(20).itertuples(), 1):
        print(f"{i:>3} {r.name[:23]:24} {r.position:4} {str(r.team)[:3]:4} {r.games:>3} {r.points:>7.1f} {r.ppg:>6.1f}")

    print(f"\n=== positional leaders (min 8 games) ===")
    qual = latest[latest["games"] >= 8]
    for pos in ("QB", "RB", "WR", "TE"):
        top = qual[qual["position"] == pos].head(5)
        print(f"\n{pos}:")
        for i, r in enumerate(top.itertuples(), 1):
            print(f"  {i}. {r.name[:22]:23} {r.points:>7.1f} pts  {r.ppg:>5.1f}/g")

    print(f"\nSaved {len(df)} player-seasons -> {DATA_DIR / 'scored_history.csv'}")
