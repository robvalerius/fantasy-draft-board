"""My recommended targets - the purple tier.

Built from three things:
  1. This league's scoring model (data/auction_values.csv)
  2. Where public ADP disagrees with that model - the exploitable gap
  3. August 2026 situation research (trades, depth charts, camp reports)

Tiers:
  anchor      spend real money, these win the league under our scoring
  value       market underprices them badly - the core of the plan
  dark_horse  cheap fliers with a genuine path to volume
  avoid       market overprices them - let someone else pay

Nothing here is a constraint. The board still prices everyone honestly.
"""

# ---------------------------------------------------------------- the plan

PLAN = [
    ("QB",  "5-18",   "WAIT. Allen is $74 of your $269 and QB2-QB9 are within "
                      "35 pts of each other. Nix, Lawrence, Mahomes or Shough late."),
    ("RB",  "95-135", "One anchor. Carries (0.1) + first downs (0.25) make bell-cows "
                      "the highest-scoring players in this league."),
    ("RB",  "50-90",  "A second real starter. Kyren or Cook, not a committee back."),
    ("WR",  "50-65",  "One WR you actually want every week."),
    ("WR",  "30-50",  "Second starter. Value is deep here - don't reach."),
    ("TE",  "10-25",  "The single biggest inefficiency. LaPorta/Kittle/Kraft are "
                      "worth $40+ but public ADP has them at 93-113."),
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
        "RB1 overall in our model, 334 proj. Elite carry volume plus receiving. "
        "If you win him, you are done spending big."),
    "Bijan Robinson": ("anchor",
        "329 proj, effectively tied with Gibbs. Same plan, likely $5-10 cheaper."),
    "De'Von Achane": ("anchor",
        "303 proj but ADP 11 - the room ranks him below our model. Best "
        "value-to-cost ratio in the elite RB tier."),
    "Jonathan Taylor": ("anchor",
        "294 proj, pure volume back. Exactly the profile this scoring rewards."),

    # ---- VALUE: model says far more than the market does --------------
    "Kyren Williams": ("value",
        "$90 value at ADP 32. The largest gap of any high-end RB. Workhorse "
        "carries are worth more here than the market assumes."),
    "James Cook": ("value",
        "$85 value, barely drafted in public data. Buffalo volume."),
    "Bucky Irving": ("value",
        "$53 value at ADP 45. Efficient, and the carry share is trending up."),
    "Trey McBride": ("value",
        "TE1 at $77 but market pays $29. The biggest dollar gap on the board. "
        "A WR1 target share at a position nobody pays for."),
    "Brock Bowers": ("value",
        "$62 value, market $28. Same TE story, half the price."),
    "Sam LaPorta": ("value",
        "TE3 at $43 but market pays $9. The room does not pay for TEs - you should."),
    "George Kittle": ("value",
        "$42 value, market $5. Age-driven ADP fade, but the target share held. "
        "Cheapest big edge in the draft."),
    "Tucker Kraft": ("value",
        "$40 value, market $6. Same story - cheap because he is a TE."),
    "Bo Nix": ("value",
        "$33 value, market $4. THE QB play. Efficient passer, so the -0.25 "
        "incompletion penalty barely touches him, and he runs."),
    "Jalen Hurts": ("value",
        "$41 value, market $14. Rushing QB, and rushing TDs are worth 6 here."),
    "Brock Purdy": ("value",
        "$39 value, market $16. High completion rate is ideal for our "
        "+0.1 completion / -0.25 incompletion scoring."),
    "Trevor Lawrence": ("value",
        "$19 value at ADP 88. Cheaper fallback if Nix and Hurts both go."),
    "Brian Thomas Jr.": ("value",
        "$38 value, market $16. Big-play profile fits the 40+ yard bonuses."),
    "Zach Charbonnet": ("value",
        "$25 value, market $3. Walker left for KC - Charbonnet is the Seattle "
        "lead back if the ACL rehab holds."),
    "George Pickens": ("value",
        "$61 value at ADP 20. Fair price, real ceiling."),
    "Nico Collins": ("value",
        "$57 value at ADP 24. Alpha target share when healthy."),
    "Chris Olave": ("value",
        "$50 value at ADP 23."),
    "Tee Higgins": ("value",
        "$47 value at ADP 38. On your watchlist too."),
    "Jameson Williams": ("value",
        "$40 value at ADP 42. Big-play bonuses (40+ yd) suit him."),

    # ---- DARK HORSE: cheap, with a real path to volume ----------------
    "Bhayshul Tuten": ("dark_horse",
        "Etienne left for New Orleans - Tuten inherits the JAX backfield. "
        "2nd-best missed-tackle rate in the NFL (31%) as a rookie. Jags ran the "
        "8th-most attempts. Most-cited breakout in the industry."),
    "Emanuel Wilson": ("dark_horse",
        "Walker left Seattle, Charbonnet rehabbing an ACL. Wilson is the Week 1 "
        "favorite in a run-heavy scheme. 15-20 carries would be a windfall here."),
    "Greg Dulcich": ("dark_horse",
        "Miami let Hill, Waddle AND Waller go. PFF's favorite to lead the team in "
        "targets. 3rd among TEs in yards per route run. Often undrafted."),
    "Josh Downs": ("dark_horse",
        "Pittman traded - 100+ vacated targets. Pierce started camp on PUP. "
        "70+ catches a year already on limited snaps. On your watchlist."),
    "Luther Burden III": ("dark_horse",
        "DJ Moore to Buffalo vacates 150+ targets in Chicago. 2.69 yds/route in "
        "2025. Ben Johnson offense. Note: our model rates him poorly - it cannot "
        "see the trade."),
    "Tyler Shough": ("dark_horse",
        "QB12 per game over his last 6 starts, six straight 17+ point games. "
        "Adds Etienne and Tyson. Runs near the goal line. Free QB1 upside."),
    "Oronde Gadsden II": ("dark_horse",
        "ADP fell TE9 to TE16 on the Njoku signing - widely called an "
        "overcorrection. Herbert throwing, McDaniel scheme."),
    "Jayden Higgins": ("dark_horse",
        "Locked into a three-down boundary role opposite Collins, who has an "
        "extensive injury history."),
    "Wan'Dale Robinson": ("dark_horse",
        "New scheme in Tennessee under Saleh/Daboll, large role expected."),
    "Matthew Golden": ("dark_horse",
        "Second-year jump in Green Bay."),
    "Kaytron Allen": ("dark_horse",
        "Genuine path to lead-back carries in Washington."),
    "Jonathon Brooks": ("dark_horse",
        "Carolina lead back if preseason confirms the knee. High risk, high carries."),
    "Kenneth Walker III": ("dark_horse",
        "Now in Kansas City with Mahomes - a big situation upgrade. Our $48 value "
        "is built on Seattle usage, so the real number is likely higher."),

    # ---- AVOID: the market will overpay, let them --------------------
    "Josh Allen": ("avoid",
        "Worth $74 on paper, but that is 27% of budget on the one position where "
        "the drop-off is smallest. Nix at $10 gets you 83% of the production."),
    "Christian McCaffrey": ("avoid",
        "Market pays $82, we value him at $82. No edge, and the RB age curve is "
        "steep. Fine player, terrible use of your money."),
    "Derrick Henry": ("avoid",
        "The worst price on the board: market $73, our value $30. Age 32, and "
        "our scoring pays for receiving work he does not do."),
    "Justin Jefferson": ("avoid",
        "Market $65 vs our $37. Elite talent, but the room is paying a standard-"
        "league premium that our scoring does not reward."),
    "Rashee Rice": ("avoid",
        "Market $69 vs our $51. Real player, $18 too expensive."),
    "Malik Nabers": ("avoid",
        "Torn ACL Week 4 2025. ADP has not fully discounted the return risk."),
    "Josh Jacobs": ("avoid",
        "Age 28, 2,100+ career touches, legal uncertainty, new team. ESPN flags "
        "him as a bust candidate."),
    "Mike Evans": ("avoid",
        "Age 33 and in San Francisco now. New system, declining role."),
    "A.J. Brown": ("avoid",
        "Traded to New England. Our $40 value is built on Philadelphia usage - "
        "treat it as unreliable."),
    "Omarion Hampton": ("avoid",
        "Model has him RB32/$6 while ADP is 22. The room is paying for the "
        "narrative. On your watchlist, so decide deliberately."),
}

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
