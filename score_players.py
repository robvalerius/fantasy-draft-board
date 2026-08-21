"""Score every real NFL player under the active league's rules."""

import pandas as pd

from league_config import DATA_DIR, SHARED_DATA
from scoring import score_offense

# Raw box scores are the same for every league; the scored output is not.
DATA = SHARED_DATA

# nflverse column -> our scoring key
OFFENSE_MAP = {
    "completions": "completions",
    "passing_yards": "passing_yards",
    "passing_tds": "passing_tds",
    "passing_interceptions": "interceptions",
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


def _row_to_stats(row: pd.Series) -> dict:
    stats = {
        ours: float(row.get(theirs) or 0)
        for theirs, ours in OFFENSE_MAP.items()
    }
    # nflverse gives attempts + completions; we need incompletions
    attempts = float(row.get("attempts") or 0)
    stats["incompletions"] = max(0.0, attempts - stats["completions"])
    stats["two_point_conversions"] += float(row.get("rushing_2pt_conversions") or 0)
    stats["two_point_conversions"] += float(row.get("receiving_2pt_conversions") or 0)
    return stats


def score_season(season: int) -> pd.DataFrame:
    df = pd.read_csv(DATA / f"stats_{season}.csv", low_memory=False)
    df = df[df["position"].isin(["QB", "RB", "WR", "TE"])].copy()

    df["points"] = df.apply(lambda r: score_offense(_row_to_stats(r)), axis=1)
    df["games"] = df["games"].fillna(0).astype(int)
    df["ppg"] = (df["points"] / df["games"].clip(lower=1)).round(2)
    df["season"] = season

    return df[[
        "season", "player_id", "player_display_name", "position", "recent_team",
        "games", "points", "ppg",
        "attempts", "completions", "passing_yards", "passing_tds", "passing_interceptions",
        "carries", "rushing_yards", "rushing_tds", "rushing_first_downs",
        "targets", "receptions", "receiving_yards", "receiving_tds", "receiving_first_downs",
    ]].rename(columns={"player_display_name": "name", "recent_team": "team"})


def all_seasons() -> pd.DataFrame:
    return pd.concat([score_season(s) for s in (2023, 2024, 2025)], ignore_index=True)


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
