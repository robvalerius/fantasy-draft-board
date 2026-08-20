"""Convert raw stat lines into Battle for the Belt XIV fantasy points."""

from league_config import (
    DEFENSE,
    KICKING,
    OFFENSE,
    PASSING_YARD_BONUSES,
    POINTS_ALLOWED,
    RECEIVING_YARD_BONUSES,
    RUSHING_YARD_BONUSES,
    YARDS_ALLOWED,
)


def _bonus(value: float, tiers: list[tuple[float, float]]) -> float:
    """Cumulative milestone bonuses."""
    return sum(pts for threshold, pts in tiers if value >= threshold)


def _tier(value: float, tiers: list[tuple[float, float]]) -> float:
    """First matching tier wins."""
    for ceiling, pts in tiers:
        if value <= ceiling:
            return pts
    return 0.0


def score_offense(s: dict) -> float:
    """Score a QB/RB/WR/TE stat line. Missing keys count as zero."""
    pts = sum(weight * s.get(stat, 0) for stat, weight in OFFENSE.items())
    pts += _bonus(s.get("passing_yards", 0), PASSING_YARD_BONUSES)
    pts += _bonus(s.get("rushing_yards", 0), RUSHING_YARD_BONUSES)
    pts += _bonus(s.get("receiving_yards", 0), RECEIVING_YARD_BONUSES)
    return round(pts, 2)


def score_kicker(s: dict) -> float:
    return round(sum(w * s.get(stat, 0) for stat, w in KICKING.items()), 2)


def score_defense(s: dict) -> float:
    pts = sum(w * s.get(stat, 0) for stat, w in DEFENSE.items())
    pts += _tier(s.get("points_allowed", 0), POINTS_ALLOWED)
    pts += _tier(s.get("yards_allowed", 0), YARDS_ALLOWED)
    return round(pts, 2)


def score(stats: dict, position: str) -> float:
    if position == "K":
        return score_kicker(stats)
    if position in ("DEF", "DST"):
        return score_defense(stats)
    return score_offense(stats)


# ------------------------------------------------------------------ helpers

def explain(stats: dict, position: str = "OFF") -> list[tuple[str, float]]:
    """Per-stat point contributions, largest absolute impact first."""
    table = {"K": KICKING, "DEF": DEFENSE, "DST": DEFENSE}.get(position, OFFENSE)
    rows = [
        (stat, round(weight * stats[stat], 2))
        for stat, weight in table.items()
        if stats.get(stat)
    ]

    if position not in ("K", "DEF", "DST"):
        for label, key, tiers in (
            ("pass yd bonus", "passing_yards", PASSING_YARD_BONUSES),
            ("rush yd bonus", "rushing_yards", RUSHING_YARD_BONUSES),
            ("rec yd bonus", "receiving_yards", RECEIVING_YARD_BONUSES),
        ):
            if (b := _bonus(stats.get(key, 0), tiers)):
                rows.append((label, b))
    else:
        if position in ("DEF", "DST"):
            rows.append(("points allowed", _tier(stats.get("points_allowed", 0), POINTS_ALLOWED)))
            rows.append(("yards allowed", _tier(stats.get("yards_allowed", 0), YARDS_ALLOWED)))

    return sorted(rows, key=lambda r: -abs(r[1]))
