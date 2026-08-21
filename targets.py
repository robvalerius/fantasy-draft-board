"""Target tiers and the audit that keeps them honest.

The tier data itself is per-league and lives in leagues/<league>_targets.py.
This module holds the parts that are the same for every league: the tier
vocabulary, name lookup, and the audit that checks every note against the
live model.

Run `python targets.py` to audit the active league (FF_LEAGUE selects it).
"""

from __future__ import annotations

import importlib

from league_config import TARGETS_MODULE

_league = importlib.import_module(TARGETS_MODULE)

PLAN = _league.PLAN
BUDGET_NOTE = _league.BUDGET_NOTE
TARGETS = _league.TARGETS

# Players parked in `avoid` for injury, age or shape reasons rather than
# price. The audit below must not flag these for having a positive edge.
RISK_NOT_PRICE = _league.RISK_NOT_PRICE

TIER_ORDER = ("anchor", "value", "dark_horse", "avoid")

TIER_LABEL = {
    "anchor": "Anchor - spend here",
    "value": "Value - market is wrong",
    "dark_horse": "Dark horse - cheap upside",
    "avoid": "Avoid - let them overpay",
}



def _norm(name: str) -> str:
    return (
        str(name).lower()
        .replace(".", "").replace("'", "").replace("-", " ")
        .replace(" jr", "").replace(" sr", "").replace(" iii", "").replace(" ii", "")
        .strip()
    )


_LOOKUP = {_norm(k): v for k, v in TARGETS.items()}


def tier_of(name: str) -> str | None:
    hit = _LOOKUP.get(_norm(name))
    return hit[0] if hit else None


def note_of(name: str) -> str | None:
    hit = _LOOKUP.get(_norm(name))
    return hit[1] if hit else None


# ---------------------------------------------------------------- audit

VALUE_MIN_EDGE = 10   # a "value" pick must beat market by at least this
AVOID_MAX_EDGE = 3    # an "avoid" pick must not have a real positive edge


def audit(verbose: bool = True) -> list[str]:
    """Check every target against the live model. Returns a list of problems.

    This is what stops the notes from rotting again. It catches five things:
      - a note that hardcodes a dollar figure (they go stale)
      - a `value` pick the model no longer thinks is cheap
      - an `avoid` pick the model actually likes, without a risk exemption
      - a name the board cannot price at all
      - a player you are told to buy who is flagged out (PUP/IR/etc)
    """
    from draft import Draft

    df = Draft().available.copy()
    df["k"] = df["name"].map(_norm)
    idx = {r.k: r for r in df.itertuples()}

    problems: list[str] = []
    for nm, (tier, note) in TARGETS.items():
        if "$" in note:
            problems.append(f"{nm}: note hardcodes a dollar figure")

        r = idx.get(_norm(nm))
        if r is None:
            problems.append(f"{nm}: not present in the player pool")
            continue

        # Never point at a hurt player with a buy marker. The board renders any
        # non-avoid tier as a purple diamond, so this would actively mislead.
        if tier != "avoid" and bool(getattr(r, "out", False)):
            problems.append(
                f"{nm}: tier={tier} but flagged out "
                f"({getattr(r, 'injury_status', None) or getattr(r, 'status', '?')})"
            )

        edge = int(r.value) - int(r.market)
        if tier == "value" and edge < VALUE_MIN_EDGE:
            problems.append(f"{nm}: tier=value but edge is only {edge:+d}")
        if tier == "avoid" and edge > AVOID_MAX_EDGE and nm not in RISK_NOT_PRICE:
            problems.append(f"{nm}: tier=avoid but edge is {edge:+d}")
        if tier == "anchor" and edge < -10:
            problems.append(f"{nm}: tier=anchor but edge is {edge:+d}")

    if verbose:
        if problems:
            print(f"{len(problems)} problem(s):")
            for p in problems:
                print("  -", p)
        else:
            print(f"All {len(TARGETS)} targets consistent with the current model.")
    return problems


if __name__ == "__main__":
    import sys
    sys.exit(1 if audit() else 0)
