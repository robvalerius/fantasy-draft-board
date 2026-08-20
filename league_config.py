"""Battle for the Belt XIV - league rules, encoded exactly.

League ID 204761 | 14 teams | Live Salary Cap (auction) | Half PPR
Draft: Sat Aug 22, 8:00pm EDT
"""

LEAGUE_NAME = "Battle for the Belt XIV"
LEAGUE_ID = 204761
NUM_TEAMS = 14
BUDGET = 269
MIN_BID = 1

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

FLEX_ELIGIBLE = {
    "W/T": {"WR", "TE"},
    "W/R/T": {"WR", "RB", "TE"},
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
