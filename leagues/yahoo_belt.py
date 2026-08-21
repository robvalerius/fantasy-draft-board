"""Battle for the Belt XIV - league rules, encoded exactly.

League ID 204761 | 14 teams | Live Salary Cap (auction) | Half PPR
Draft: Sat Aug 22, 8:00pm EDT

Scoring here was transcribed by hand from Yahoo's league settings, because
Yahoo's Fantasy API is a closed door. Sleeper leagues do not need this - see
sleeper_sync.py, which reads scoring straight from the API.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LEAGUE_SLUG = "yahoo_belt"
LEAGUE_NAME = "Battle for the Belt XIV"
LEAGUE_ID = 204761
NUM_TEAMS = 14
BUDGET = 269
MIN_BID = 1

# ------------------------------------------------------------------- paths
# SHARED_DATA holds raw inputs that mean the same thing to every league:
# nflverse box scores, rosters, the Sleeper player dump, ADP pulls. Nothing
# league-specific is ever written there.
#
# DATA_DIR holds this league's derived artifacts (scored_history, auction and
# market values, live draft state). For this league it IS data/, unchanged, so
# every path the deployed Yahoo board depends on stays exactly where it was.
SHARED_DATA = ROOT / "data"
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
STANDALONE_HTML = ROOT / "draft-board.html"

ADP_FILE = "adp_half-ppr.csv"       # 14-team half-PPR pull
MARKET_SOURCE = "yahoo_aav"         # observed Yahoo mock prices in yahoo_aav.csv
EXPERT_RANKS = "expert_ranks.csv"
TARGETS_MODULE = "leagues.yahoo_belt_targets"

# Season totals, not weekly. This league's yardage bonuses are therefore
# applied once per season rather than per game - a known simplification that
# predates the second league. Left alone deliberately: the board built on it is
# deployed and in use. The Sleeper config scores weekly instead.
STATS_GRAIN = "season"

# Extra keys baked into docs/data.js. Empty for this league on purpose: its
# board is deployed and its payload must not gain keys. See build_static.py.
EXTRA_PAYLOAD: dict = {}

# This league has no per-game threshold bonuses and no positional first-down
# bonus. Both empty means scoring.py behaves exactly as it always has.
GAME_BONUSES: list[tuple[str, float, float]] = []
FIRST_DOWN_BONUS: dict[str, float] = {}

# 10 starters + 3 bench + 1 IR
STARTERS = {
    "QB": 1,
    "RB": 2,
    "WR": 2,
    "TE": 1,
    "W/T": 1,      # WR or TE
    "W/R/T": 1,    # WR, RB, or TE
    "K": 1,
    "DEF": 1,
}
BENCH = 3
IR = 1
ROSTER_SIZE = sum(STARTERS.values()) + BENCH  # 13 draftable spots

# Ordered on purpose: the replacement-level walk in valuation.py fills each
# flex slot with the best remaining eligible player, and this order is what
# breaks exact ties. Do not reorder.
FLEX_ELIGIBLE = {
    "W/T": ("WR", "TE"),
    "W/R/T": ("WR", "RB", "TE"),
}

TOTAL_DRAFTED = NUM_TEAMS * ROSTER_SIZE  # 182

# ---------------------------------------------------------------- offense

OFFENSE = {
    "completions": 0.1,
    "incompletions": -0.25,
    "passing_yards": 1 / 25,
    "passing_tds": 5,
    "interceptions": -3,
    "sacks_taken": -1,
    "rushing_attempts": 0.1,
    "rushing_yards": 0.1,
    "rushing_tds": 6,
    "receptions": 0.5,
    "receiving_yards": 0.1,
    "receiving_tds": 6,
    "return_tds": 10,
    "two_point_conversions": 3,
    "fumbles": -1,
    "fumbles_lost": -2,  # stacks with the -1 above
    "offensive_fumble_return_td": 6,
    "pick_sixes_thrown": -2,
    "completions_40_plus": 1,
    "rushes_40_plus": 1,
    "receptions_40_plus": 1,
    "receiving_first_downs": 0.25,
    "rushing_first_downs": 0.25,
}

# Yardage milestone bonuses (threshold -> bonus, cumulative)
PASSING_YARD_BONUSES = [(400, 1.5), (500, 3)]
RUSHING_YARD_BONUSES = [(200, 1.5), (250, 3)]
RECEIVING_YARD_BONUSES = [(200, 1.5), (250, 3)]

# ---------------------------------------------------------------- kicking

KICKING = {
    "fg_0_19": 3,
    "fg_20_29": 3,
    "fg_30_39": 3,
    "fg_40_49": 4,
    "fg_50_plus": 5,
    "fg_missed_0_19": -4,
    "fg_missed_20_29": -3.5,
    "fg_missed_40_49": -2.5,
    "fg_missed_50_plus": -2,
    "pat_made": 1,
    "pat_missed": -1.75,
    "fg_total_yards": 1 / 100,
}

# ---------------------------------------------------------------- defense

DEFENSE = {
    "sacks": 1,
    "interceptions": 3,
    "fumble_recoveries": 2,
    "touchdowns": 6,
    "safeties": 3,
    "blocked_kicks": 2,
    "return_tds": 6,
    "fourth_down_stops": 1,
    "tackles_for_loss": 0.25,
    "three_and_outs_forced": 0.25,
    "extra_point_returned": 3,
}

# Points allowed tiers: (max_points_allowed, score)
POINTS_ALLOWED = [
    (0, 15),
    (6, 7),
    (13, 4),
    (20, 1),
    (27, 0),
    (34, -3),
    (float("inf"), -7),
]

# Yards allowed tiers: (max_yards_allowed, score)
YARDS_ALLOWED = [
    (99, 5),
    (199, 2),
    (399, 0),
    (499, -2.5),
    (float("inf"), -5),
]
