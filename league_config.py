"""Active-league dispatcher.

This folder hosts more than one league. Every module still does

    from league_config import BUDGET, NUM_TEAMS, ...

exactly as before; which league that resolves to is decided once, here, by the
FF_LEAGUE environment variable:

    (unset)                     -> yahoo_belt        Battle for the Belt XIV
    FF_LEAGUE=sleeper_scaries   -> sleeper_scaries   Sunday Scaries Society

The default is deliberate. Every existing command - `python valuation.py`,
`python build_static.py`, `python draft.py` - keeps its old behaviour and
writes to its old paths with no flag, so the deployed Yahoo board cannot be
changed by accident.

Adding a league means adding a module under leagues/ and one line to LEAGUES.
"""

import importlib
import os

LEAGUES = {
    "yahoo_belt": "leagues.yahoo_belt",
    "sleeper_scaries": "leagues.sleeper_scaries",
}

DEFAULT = "yahoo_belt"

ACTIVE = os.environ.get("FF_LEAGUE", DEFAULT).strip() or DEFAULT

if ACTIVE not in LEAGUES:
    raise SystemExit(
        f"Unknown FF_LEAGUE={ACTIVE!r}. Known leagues: {', '.join(sorted(LEAGUES))}"
    )

_module = importlib.import_module(LEAGUES[ACTIVE])

# Re-export the league's public names so `from league_config import X` works.
globals().update({k: v for k, v in vars(_module).items() if not k.startswith("_")})
