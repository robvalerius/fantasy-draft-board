"""Download all public data sources into ./data. Run: python fetch_data.py"""

import json
from pathlib import Path

import pandas as pd
import requests

DATA = Path(__file__).parent / "data"
DATA.mkdir(exist_ok=True)

NFLVERSE = "https://github.com/nflverse/nflverse-data/releases/download"
SEASONS = [2023, 2024, 2025]


def fetch_nflverse_stats() -> None:
    for season in SEASONS:
        out = DATA / f"stats_{season}.csv"
        if out.exists():
            print(f"  cached  stats_{season}.csv")
            continue
        url = f"{NFLVERSE}/stats_player/stats_player_reg_{season}.csv"
        df = pd.read_csv(url, low_memory=False)
        df.to_csv(out, index=False)
        print(f"  saved   stats_{season}.csv ({len(df)} rows)")


def fetch_nflverse_weekly() -> None:
    """Per-game box scores.

    The Yahoo league scores off season totals, which is why only the season
    files existed. That is wrong for any league with per-game bonuses: Sleeper
    pays 1 pt for a 20-carry game and 2 pts for a 25-completion game, and those
    fire eight or ten times a year, not once. Scoring them off a season total
    would award them a single time. So leagues with STATS_GRAIN == "week" score
    from these files instead.
    """
    for season in SEASONS:
        out = DATA / f"stats_week_{season}.csv"
        if out.exists():
            print(f"  cached  stats_week_{season}.csv")
            continue
        url = f"{NFLVERSE}/stats_player/stats_player_week_{season}.csv"
        df = pd.read_csv(url, low_memory=False)
        df.to_csv(out, index=False)
        print(f"  saved   stats_week_{season}.csv ({len(df)} rows)")


def fetch_team_defense() -> None:
    for season in SEASONS:
        out = DATA / f"team_stats_{season}.csv"
        if out.exists():
            print(f"  cached  team_stats_{season}.csv")
            continue
        url = f"{NFLVERSE}/stats_team/stats_team_reg_{season}.csv"
        df = pd.read_csv(url, low_memory=False)
        df.to_csv(out, index=False)
        print(f"  saved   team_stats_{season}.csv ({len(df)} rows)")


def fetch_sleeper_players(force: bool = False) -> None:
    """Sleeper carries the injury tags. Unlike the historical stats files this
    one goes stale fast, so it takes a --refresh flag. Injury status drives
    OUT_TAGS in market_value.py, which pins hurt players to replacement level.
    """
    out = DATA / "sleeper_players.json"
    if out.exists() and not force:
        print("  cached  sleeper_players.json  (use --refresh for live injuries)")
        return
    r = requests.get("https://api.sleeper.app/v1/players/nfl", timeout=120)
    r.raise_for_status()
    players = {
        pid: {
            k: p.get(k)
            for k in (
                "full_name", "position", "team", "age", "years_exp",
                "injury_status", "status", "depth_chart_order",
                "search_rank", "number",
            )
        }
        for pid, p in r.json().items()
        if p.get("position") in ("QB", "RB", "WR", "TE", "K", "DEF")
        and p.get("status") != "Inactive"
    }
    out.write_text(json.dumps(players, indent=1))
    print(f"  saved   sleeper_players.json ({len(players)} players)")


def fetch_adp() -> None:
    """FantasyFootballCalculator ADP - closest public proxy for market value.

    Pulled per league size, because a 14-team board and a 12-team board are
    genuinely different markets. The unsuffixed files are the original 14-team
    pull and are what the Yahoo league reads; do not rename them.
    """
    for teams, suffix in ((14, ""), (12, "_12tm")):
        for fmt in ("half-ppr", "ppr", "standard"):
            out = DATA / f"adp_{fmt}{suffix}.csv"
            if out.exists():
                print(f"  cached  adp_{fmt}{suffix}.csv")
                continue
            url = (f"https://fantasyfootballcalculator.com/api/v1/adp/{fmt}"
                   f"?teams={teams}&year=2026")
            r = requests.get(url, timeout=60)
            if not r.ok:
                print(f"  MISS    adp_{fmt}{suffix} ({r.status_code})")
                continue
            players = r.json().get("players", [])
            if not players:
                print(f"  EMPTY   adp_{fmt}{suffix}")
                continue
            pd.DataFrame(players).to_csv(out, index=False)
            print(f"  saved   adp_{fmt}{suffix}.csv ({len(players)} players)")


def fetch_rosters() -> None:
    out = DATA / "roster_2025.csv"
    if out.exists():
        print("  cached  roster_2025.csv")
        return
    df = pd.read_csv(f"{NFLVERSE}/rosters/roster_2025.csv", low_memory=False)
    df.to_csv(out, index=False)
    print(f"  saved   roster_2025.csv ({len(df)} rows)")


if __name__ == "__main__":
    import sys

    force = "--refresh" in sys.argv
    print("nflverse player stats:")
    fetch_nflverse_stats()
    print("nflverse weekly stats:")
    fetch_nflverse_weekly()
    print("nflverse team stats:")
    fetch_team_defense()
    print("nflverse rosters:")
    fetch_rosters()
    print("sleeper:")
    fetch_sleeper_players(force=force)
    print("adp:")
    fetch_adp()
    print(f"\nAll data in {DATA}")
