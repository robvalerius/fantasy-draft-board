"""Sunday Scaries Society - rules read from the Sleeper API, not transcribed.

League 1384568263651897344 | 12 teams | auction | $200 | half PPR (heavily customised)
Draft: Wed Aug 26, 2026, 11:30pm EDT

Everything numeric here is derived at import time from the JSON that
sleeper_sync.py caches in data/sleeper_scaries/. Run that first. The only
things written by hand are the *mappings* below - which Sleeper stat key
corresponds to which of our stat keys - because that is a judgement call about
what our projection source can actually support, and it deserves review.

WHAT MAKES THIS LEAGUE DIFFERENT

`rush_fd` is 1.5, and `bonus_fd_rb` (0.25) stacks on top, so a rushing first
down by a running back is worth 1.75 points. The Yahoo league pays 0.25 for the
same event. This is the single largest scoring difference between the two
leagues and it should visibly reorder the board toward high-volume backs.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LEAGUE_SLUG = "sleeper_scaries"
SHARED_DATA = ROOT / "data"
DATA_DIR = ROOT / "data" / "sleeper_scaries"
DOCS_DIR = ROOT / "docs" / "sleeper"
STANDALONE_HTML = ROOT / "draft-board-sleeper.html"

_LEAGUE_JSON = DATA_DIR / "league.json"
_DRAFT_JSON = DATA_DIR / "draft.json"

if not _LEAGUE_JSON.exists():
    raise SystemExit(
        "No cached Sleeper settings. Run:  python sleeper_sync.py"
    )

_LEAGUE = json.loads(_LEAGUE_JSON.read_text(encoding="utf-8"))
_DRAFT = json.loads(_DRAFT_JSON.read_text(encoding="utf-8"))
_SC: dict[str, float] = _LEAGUE["scoring_settings"]
_DS: dict = _DRAFT["settings"]

LEAGUE_NAME = _LEAGUE["name"]
LEAGUE_ID = _LEAGUE["league_id"]
DRAFT_ID = _DRAFT["draft_id"]
NUM_TEAMS = int(_DS["teams"])
BUDGET = int(_DS["budget"])
MIN_BID = 1

# ------------------------------------------------------------------- roster
# roster_positions is the authoritative list, e.g.
#   QB RB RB WR WR TE FLEX REC_FLEX K DEF BN BN BN BN
_POSITIONS = _LEAGUE["roster_positions"]

BENCH = _POSITIONS.count("BN")
STARTERS = {}
for _p in _POSITIONS:
    if _p != "BN":
        STARTERS[_p] = STARTERS.get(_p, 0) + 1

ROSTER_SIZE = sum(STARTERS.values()) + BENCH
IR = int(_LEAGUE["settings"].get("reserve_slots", 0))
TOTAL_DRAFTED = NUM_TEAMS * ROSTER_SIZE

# Ordered, and filled in roster order, because this is what breaks exact ties
# in the replacement-level walk. FLEX takes RB/WR/TE, REC_FLEX takes WR/TE.
FLEX_ELIGIBLE = {
    "FLEX": ("WR", "RB", "TE"),
    "REC_FLEX": ("WR", "TE"),
}

# --------------------------------------------------------------- the mapping
# Sleeper stat key -> our stat key. Linear per-event scoring only; thresholds
# and position bonuses are handled separately below.
_LINEAR = {
    # passing
    "pass_cmp": "completions",
    "pass_inc": "incompletions",
    "pass_att": "pass_attempts",
    "pass_yd": "passing_yards",
    "pass_td": "passing_tds",
    "pass_int": "interceptions",
    "pass_sack": "sacks_taken",
    "pass_fd": "passing_first_downs",
    "pass_2pt": "pass_2pt",
    "pass_cmp_40p": "completions_40_plus",
    # rushing
    "rush_att": "rushing_attempts",
    "rush_yd": "rushing_yards",
    "rush_td": "rushing_tds",
    "rush_fd": "rushing_first_downs",
    "rush_40p": "rushes_40_plus",
    "rush_2pt": "rush_2pt",
    # receiving
    "rec": "receptions",
    "rec_yd": "receiving_yards",
    "rec_td": "receiving_tds",
    "rec_fd": "receiving_first_downs",
    "rec_40p": "receptions_40_plus",
    "rec_2pt": "rec_2pt",
    # misc
    "fum": "fumbles",
    "fum_lost": "fumbles_lost",
    "st_td": "return_tds",
}

OFFENSE = {
    ours: float(_SC[theirs])
    for theirs, ours in _LINEAR.items()
    if _SC.get(theirs)
}

# ------------------------------------------------------- per-game thresholds
# Sleeper stat key -> (our stat key, threshold). These fire ONCE PER GAME, not
# once per season, which is why this league scores off weekly box scores.
# bonus_rush_att_20 alone fires eight to ten times a year for a bell-cow.
_GAME_BONUS = {
    "bonus_pass_yd_400": ("passing_yards", 400),
    "bonus_pass_cmp_25": ("completions", 25),
    "bonus_rush_yd_200": ("rushing_yards", 200),
    "bonus_rush_att_20": ("rushing_attempts", 20),
    "bonus_rec_yd_200": ("receiving_yards", 200),
}

GAME_BONUSES = [
    (stat, threshold, float(_SC[key]))
    for key, (stat, threshold) in _GAME_BONUS.items()
    if _SC.get(key)
]

# The Yahoo league's cumulative season milestones do not exist here.
PASSING_YARD_BONUSES: list[tuple[float, float]] = []
RUSHING_YARD_BONUSES: list[tuple[float, float]] = []
RECEIVING_YARD_BONUSES: list[tuple[float, float]] = []

# ------------------------------------------------- positional first-down bonus
# bonus_fd_<pos> pays per first down the player accounts for, on top of the
# rush_fd / rec_fd / pass_fd values above. Assumption worth knowing: we apply it
# to every first down the player generates, including passing first downs for a
# QB. That is how Sleeper's "First Down Bonus" reads, but it is an inference -
# at 0.1/FD it is worth roughly 20 points a season to a high-volume passer, so
# it moves QBs a little and nobody else much.
FIRST_DOWN_BONUS = {
    pos: float(_SC[key])
    for pos, key in (("QB", "bonus_fd_qb"), ("RB", "bonus_fd_rb"),
                     ("WR", "bonus_fd_wr"), ("TE", "bonus_fd_te"))
    if _SC.get(key)
}

# ------------------------------------------------------------------ honesty
# Scoring this league pays for but our projection source cannot measure. All of
# these are simply absent from OFFENSE, so they contribute zero.
#
#   pass_td_40p/50p, rush_td_40p/50p, rec_td_40p/50p
#       Touchdown *distance*. nflverse season and weekly files carry TD counts,
#       not TD lengths; you need play-by-play. Worth a few points a season to
#       big-play players, and it understates them slightly.
#   pass_int_td
#       Pick-sixes thrown (-7). No nflverse column for interceptions returned
#       for a score against a given passer.
#   fum_rec_td
#       Own fumble recovered for a touchdown. nflverse does carry this, but
#       wiring it in would also shift the frozen Yahoo board's numbers, and it
#       is worth a fraction of a point a season. Left out deliberately.
#
# Kickers and defenses are min-bid slots in an auction and are not projected by
# valuation.py at all, so their scoring is not mapped.
UNMODELED = {
    key: float(_SC[key])
    for key in ("pass_td_40p", "pass_td_50p", "rush_td_40p", "rush_td_50p",
                "rec_td_40p", "rec_td_50p", "pass_int_td", "fum_rec_td")
    if _SC.get(key)
}

# Unused by valuation.py (K/DEF are never projected), present so the module
# satisfies the same interface as the Yahoo config.
KICKING: dict[str, float] = {}
DEFENSE: dict[str, float] = {}
POINTS_ALLOWED: list[tuple[float, float]] = []
YARDS_ALLOWED: list[tuple[float, float]] = []

# -------------------------------------------------------------------- paths
ADP_FILE = "adp_half-ppr_12tm.csv"   # 12-team pull, this is a different market
MARKET_SOURCE = "curve"              # no observed auction prices exist for Sleeper
EXPERT_RANKS = "expert_ranks.csv"
TARGETS_MODULE = "leagues.sleeper_scaries_targets"

STATS_GRAIN = "week"                 # per-game bonuses demand weekly box scores

# Baked into docs/sleeper/data.js so the board can poll live draft results.
# Sleeper's API sends access-control-allow-origin: *, so the static page can
# call it directly with no server and no key.
_USERS = json.loads((DATA_DIR / "users.json").read_text(encoding="utf-8"))

EXTRA_PAYLOAD = {
    "sleeper_league_id": LEAGUE_ID,
    "sleeper_draft_id": DRAFT_ID,
    "sleeper_users": sorted(
        ({"id": u["user_id"], "name": u.get("display_name") or u["user_id"]}
         for u in _USERS),
        key=lambda u: u["name"].lower(),
    ),
}
