r"""Pull a Sleeper league's real settings from the public API.

    .\.venv\Scripts\python.exe sleeper_sync.py

Sleeper's API is free, read-only and unauthenticated, which is the whole reason
this league's config can be *derived* rather than transcribed. The Yahoo league
needed its scoring typed in by hand off screenshots; here we read
`scoring_settings` straight from the source and let leagues/sleeper_scaries.py
map it onto our stat keys.

This script only fetches and caches. It deliberately does not generate Python:
the mapping from Sleeper's stat keys to ours involves real judgement about what
our projection source can support, so that mapping lives in reviewable code in
leagues/sleeper_scaries.py rather than in generated output.

Cached files (data/sleeper_scaries/):
    league.json    name, scoring_settings, roster_positions, settings
    draft.json     auction budget, rounds, slot counts, start time
    users.json     who is in the league
    rosters.json   keepers, if any are ever set
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

API = "https://api.sleeper.app/v1"
LEAGUE_ID = "1384568263651897344"          # Sunday Scaries Society
CACHE = Path(__file__).parent / "data" / "sleeper_scaries"


def _get(path: str):
    r = requests.get(f"{API}/{path}", timeout=60)
    r.raise_for_status()
    return r.json()


def sync(league_id: str = LEAGUE_ID) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)

    league = _get(f"league/{league_id}")
    drafts = _get(f"league/{league_id}/drafts")
    if not drafts:
        raise SystemExit(f"League {league_id} has no draft.")
    draft = _get(f"draft/{drafts[0]['draft_id']}")

    files = {
        "league.json": league,
        "draft.json": draft,
        "users.json": _get(f"league/{league_id}/users"),
        "rosters.json": _get(f"league/{league_id}/rosters"),
    }
    for name, payload in files.items():
        (CACHE / name).write_text(json.dumps(payload, indent=1), encoding="utf-8")
        print(f"  saved   {CACHE.name}/{name}")

    return league, draft


def summarize(league: dict, draft: dict) -> None:
    ds = draft["settings"]
    print(f"\n=== {league['name']} ===")
    print(f"  status         {league['status']} / draft {draft['status']}")
    print(f"  type           {draft['type']}  ({draft['metadata'].get('scoring_type')})")
    print(f"  teams          {ds['teams']}")
    print(f"  budget         ${ds['budget']}")
    print(f"  rounds         {ds['rounds']}")
    print(f"  roster         {' '.join(league['roster_positions'])}")

    keepers = [r for r in json.loads((CACHE / "rosters.json").read_text()) if r.get("keepers")]
    prev = league.get("previous_league_id")
    print(f"  keepers        {len(keepers)} set"
          f"{' (no prior season, so none possible)' if not prev else ''}")

    sc = league["scoring_settings"]
    print(f"\n  scoring_settings: {len(sc)} keys. Most distinctive vs a standard half-PPR:")
    for k in ("rec", "rush_fd", "rec_fd", "pass_fd", "pass_att", "pass_cmp",
              "pass_inc", "pass_td", "pass_int", "fum_lost",
              "bonus_fd_rb", "bonus_fd_wr", "bonus_rush_att_20", "bonus_pass_cmp_25"):
        if k in sc:
            print(f"    {k:20} {sc[k]:>7}")


if __name__ == "__main__":
    lid = sys.argv[1] if len(sys.argv) > 1 else LEAGUE_ID
    league, draft = sync(lid)
    summarize(league, draft)
    print("\nNow run, with FF_LEAGUE=sleeper_scaries:")
    print("  python score_players.py && python valuation.py && "
          "python market_value.py && python build_static.py")
