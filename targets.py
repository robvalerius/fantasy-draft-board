"""My recommended targets - the purple tier.

Built from three things:
  1. This league's scoring model (data/auction_values.csv)
  2. Where public ADP disagrees with that model - the exploitable gap
  3. August 2026 situation research (trades, depth charts, camp reports)

Tiers:
  anchor      spend real money, these win the league under our scoring
  value       market underprices them badly - the core of the plan
  dark_horse  cheap fliers with a genuine path to volume
  avoid       do not pay the market price, for price or for risk

Nothing here is a constraint. The board still prices everyone honestly.

------------------------------------------------------------------------
IMPORTANT - why these notes contain no dollar figures.

They used to. Every note carried a hardcoded "$42 value, market $5", and
those numbers were written against an early version of the model. After
the deflation fit, discretionary-only budget scaling and low-confidence
deference landed, most of them were wrong - several were backwards. The
Kittle note still advertised a huge bargain on a player the model had
already pinned at replacement level after he landed on PUP.

So notes are now qualitative only: situation, news, and reasoning. The
live numbers come from the board itself, which renders VALUE, MKT, EDGE
and @200 on the same row. A note can go stale in judgement, but it can no
longer contradict the model's arithmetic.

Run `python targets.py` to audit tiers against the current model.
------------------------------------------------------------------------
"""

from __future__ import annotations

# ---------------------------------------------------------------- the plan

PLAN = [
    ("QB",  "5-18",   "WAIT. The elite QB costs a fifth of your budget and "
                      "QB2-QB9 sit within 35 pts of each other. Nix, Hurts, "
                      "Purdy, Lawrence or Shough late."),
    ("RB",  "95-135", "One anchor. Carries (0.1) + first downs (0.25) make bell-cows "
                      "the highest-scoring players in this league."),
    ("RB",  "50-90",  "A second real starter. Kyren or Irving, not a committee back."),
    ("WR",  "50-65",  "One WR you actually want every week."),
    ("WR",  "30-50",  "Second starter. Value is deep here - don't reach."),
    ("TE",  "10-25",  "The single biggest inefficiency. LaPorta and Kraft carry "
                      "starter-grade value at backup prices."),
    ("FLEX", "8-20",  "Best available RB/WR after the above."),
    ("K/DEF", "2",    "Minimum bid. Never more."),
    ("BN",  "15-30",  "Three dark horses. This is where you find the league-winner."),
]

BUDGET_NOTE = (
    "Rough shape: ~$210 on six starters, ~$25 on TE+QB combined, ~$30 on bench "
    "darts, $2 on K/DEF. Leaving $40+ unspent is how you lose an auction."
)

# ---------------------------------------------------------------- targets

TARGETS = {
    # ---- ANCHOR: the top of the board is RB in this format -----------
    "Jahmyr Gibbs": ("anchor",
        "RB1 overall in our model. Elite carry volume plus receiving work. "
        "Priced at what he is worth, so this is not a bargain - it is a "
        "decision to buy the best player. Win him and you are done spending big."),
    "Bijan Robinson": ("anchor",
        "Effectively tied with Gibbs in our model, and the room prices him "
        "the same way. Interchangeable target - take whichever runs cheaper."),
    "De'Von Achane": ("anchor",
        "The only elite RB the market actually discounts. Best value-to-cost "
        "ratio of the anchors, and the cheapest path to a top-tier back."),

    # ---- VALUE: model says far more than the market does --------------
    "Brock Purdy": ("value",
        "The largest edge on the entire board. High completion rate is ideal "
        "for our +0.1 completion / -0.25 incompletion scoring, and the room "
        "treats him as a backup. Take the QB position off the table for pennies."),
    "Brian Thomas Jr.": ("value",
        "Big-play profile fits the 40+ yard bonuses, and he goes far later "
        "than a receiver of his ceiling should."),
    "Bucky Irving": ("value",
        "Efficient with a carry share that is trending up. The largest RB edge "
        "on the board and the core of the mid-round plan."),
    "Bo Nix": ("value",
        "Efficient passer, so the incompletion penalty barely touches him, "
        "and he runs. If Purdy goes, this is the same play one tier down."),
    "Sam LaPorta": ("value",
        "The room does not pay for tight ends. Starter-grade production at a "
        "price that belongs to a backup."),
    "Jalen Hurts": ("value",
        "Rushing QB, and rushing TDs are worth 6 here. Costs more than Nix or "
        "Purdy but carries the highest floor of the three."),
    "Tucker Kraft": ("value",
        "Same story as LaPorta - cheap purely because of the position label."),
    "Kyren Williams": ("value",
        "Workhorse carries are worth more under this scoring than the market "
        "assumes. The best of the second-tier RBs."),
    "Jameson Williams": ("value",
        "Big-play bonuses (40+ yd) suit him, and the price has not caught up."),
    "Trevor Lawrence": ("value",
        "Cheaper fallback if Purdy, Nix and Hurts all go. Still a real edge."),
    "Trey McBride": ("value",
        "TE1 in our model with a WR1 target share. The edge is real but "
        "smaller than the other tight ends - the market has partly caught on."),

    # ---- DARK HORSE: cheap, with a real path to volume ----------------
    "Bhayshul Tuten": ("dark_horse",
        "Etienne left for New Orleans - Tuten inherits the JAX backfield. "
        "2nd-best missed-tackle rate in the NFL (31%) as a rookie. Jags ran the "
        "8th-most attempts. Most-cited breakout in the industry."),
    "Luther Burden III": ("dark_horse",
        "DJ Moore to Buffalo vacates 150+ targets in Chicago. Strong route "
        "efficiency in 2025, Ben Johnson offense. Model and market agree on "
        "price, so you are buying the situation, not a discount."),
    "Wan'Dale Robinson": ("dark_horse",
        "New scheme in Tennessee under Saleh/Daboll, large role expected."),
    "Zach Charbonnet": ("dark_horse",
        "Now a minimum-bid flier rather than a value play - the ACL rehab and "
        "a crowded Seattle backfield collapsed his projection. Minimum bid only."),
    "Josh Downs": ("dark_horse",
        "Pittman traded - 100+ vacated targets. Pierce started camp on PUP. "
        "70+ catches a year already on limited snaps. On your watchlist."),
    "Jayden Higgins": ("dark_horse",
        "Locked into a three-down boundary role opposite Collins, who has an "
        "extensive injury history."),
    "Tyler Shough": ("dark_horse",
        "QB12 per game over his last 6 starts, six straight 17+ point games. "
        "Adds Etienne and Tyson. Runs near the goal line. Free QB1 upside."),
    "Matthew Golden": ("dark_horse",
        "Second-year jump in Green Bay."),
    "Greg Dulcich": ("dark_horse",
        "Miami let Hill, Waddle AND Waller go. PFF's favorite to lead the team in "
        "targets. 3rd among TEs in yards per route run. Often undrafted."),
    "Oronde Gadsden II": ("dark_horse",
        "ADP fell TE9 to TE16 on the Njoku signing - widely called an "
        "overcorrection. Herbert throwing, McDaniel scheme."),
    "Emanuel Wilson": ("dark_horse",
        "Green Bay's backup behind Jacobs, who carries a heavy career workload "
        "and an age-28 profile. Minimum bid for a genuine handcuff."),

    # ---- AVOID: bad price, or good price with a risk I won't take ----
    "Justin Jefferson": ("avoid",
        "The single worst price on the board. Elite talent, but the room is "
        "paying a standard-league premium that our scoring does not reward."),
    "Derrick Henry": ("avoid",
        "Age 32, and our scoring pays for receiving work he does not do. "
        "One of the biggest overpays in the room."),
    "Kenneth Walker III": ("avoid",
        "The move to Kansas City is real, but the market has already priced in "
        "the upside and then some. Our model still sees the Seattle usage. "
        "Largest RB trap on the board - previous notes had this backwards."),
    "Christian McCaffrey": ("avoid",
        "The RB age curve is steep and the market is paying for the name. "
        "Fine player, badly wrong use of your money."),
    "A.J. Brown": ("avoid",
        "Traded to New England. Our valuation is built on Philadelphia usage, "
        "so treat the number as unreliable - and the price assumes no decline."),
    "Nico Collins": ("avoid",
        "Alpha target share when healthy, but the room pays a premium our "
        "scoring will not return."),
    "Jonathan Taylor": ("avoid",
        "Pure volume back and a good fit for the format, but the market has "
        "fully priced it. No edge left at the going rate."),
    "George Pickens": ("avoid",
        "Real ceiling, but you are paying retail. Spend the money on the RB "
        "and TE edges instead."),
    "James Cook": ("avoid",
        "Buffalo volume is genuine, and the room now pays for it. The bargain "
        "that earlier notes described no longer exists."),
    "George Kittle": ("avoid",
        "PUP-P to open camp. Our model pins him at replacement level and the "
        "market agrees, so there is no discount to capture. Previous notes "
        "advertised this as the cheapest big edge in the draft - that was "
        "written before the injury and was badly wrong. Do not chase the name."),
    "Omarion Hampton": ("avoid",
        "Model and market now agree on him. The large gap earlier notes claimed "
        "has closed entirely. On your watchlist, so decide deliberately."),
    "Mike Evans": ("avoid",
        "Age 33 and in San Francisco now. New system, declining role."),
    "Rashee Rice": ("avoid",
        "Real player, but only marginally overpriced now - the edge earlier "
        "notes claimed has mostly closed. No reason to reach."),
    "Josh Allen": ("avoid",
        "RISK/SHAPE, NOT PRICE. Our model does not hate the number. The problem "
        "is opportunity cost: a quarter of your budget at the one position "
        "where the drop-off is smallest, when Purdy or Nix gets you most of "
        "the production for a rounding error."),
    "Malik Nabers": ("avoid",
        "RISK, NOT PRICE. Our model likes the number - this is a deliberate "
        "disagreement. Torn ACL Week 4 2025 and ADP has not fully discounted "
        "the return risk. If you are comfortable with the medicals, he is "
        "genuinely underpriced."),
    "Josh Jacobs": ("avoid",
        "RISK, NOT PRICE. Our model likes the number - another deliberate "
        "disagreement. Age 28, 2,100+ career touches, legal uncertainty and a "
        "new team. ESPN flags him as a bust candidate."),
}

TIER_ORDER = ("anchor", "value", "dark_horse", "avoid")

TIER_LABEL = {
    "anchor": "Anchor - spend here",
    "value": "Value - market is wrong",
    "dark_horse": "Dark horse - cheap upside",
    "avoid": "Avoid - let them overpay",
}

# Players parked in `avoid` for injury, age or shape reasons rather than
# price. The audit below must not flag these for having a positive edge.
RISK_NOT_PRICE = {"Josh Allen", "Malik Nabers", "Josh Jacobs"}


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

    This is what stops the notes from rotting again. It catches four things:
      - a note that hardcodes a dollar figure (they go stale)
      - a `value` pick the model no longer thinks is cheap
      - an `avoid` pick the model actually likes, without a risk exemption
      - a name the board cannot price at all
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
