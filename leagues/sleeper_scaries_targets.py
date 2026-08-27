"""Recommended targets for Sunday Scaries Society - the purple tier.

Built from three things:
  1. This league's scoring model (data/sleeper_scaries/auction_values.csv)
  2. Where 12-team ADP disagrees with that model - the exploitable gap
  3. August 2026 situation research (trades, depth charts, camp reports)

Tiers:
  anchor      spend real money, these win the league under our scoring
  value       market underprices them badly - the core of the plan
  dark_horse  cheap fliers with a genuine path to volume
  avoid       do not pay the market price, for price or for risk

Nothing here is a constraint. The board still prices everyone honestly.

------------------------------------------------------------------------
Notes carry no dollar figures, on purpose. The Yahoo league's notes rotted
exactly that way: they hardcoded prices from an early model and several
ended up backwards. Notes are qualitative - situation, news, reasoning -
and the live numbers come from the board, which renders VALUE, MKT and
EDGE on the same row.

Run `FF_LEAGUE=sleeper_scaries python targets.py` to audit.
------------------------------------------------------------------------
"""

from __future__ import annotations

# ---------------------------------------------------------------- the plan

PLAN = [
    ("RB",   "62-88", "Three backs is the shape, and it is worth roughly fifty points "
                      "a season over two - a rushing first down pays 1.75 here against "
                      "0.25 in a normal league, so the backfield is where points live. "
                      "How you BUY those three is open, though. An elite anchor plus two "
                      "cheap backs and three mid-priced backs come out within a handful "
                      "of points of each other, so do not panic if the anchor gets away "
                      "from you. Win the room's one bidding war or skip it entirely; "
                      "just do not end up with two backs."),
    ("RB",   "22-62", "Second every-week starter with a clean backfield. Committee "
                      "backs never clear the first-down threshold. The range is wide "
                      "on purpose: if you landed the anchor cheap, spend here."),
    ("WR",   "7-40",  "One receiver you start without thinking - and the loosest slot "
                      "on the board. If the backfield went to plan this is a cheap "
                      "complementary piece; only if BOTH of the backs you wanted got "
                      "away does paying up here become correct."),
    ("WR",   "1-11",  "Second starter. Half PPR plus a rushing-first-down "
                      "premium means the receiver room is where the market overpays. "
                      "Take whoever falls rather than paying for a name."),
    ("TE",   "23-27", "Pay this. Correcting earlier guidance: the first-down bonus "
                      "lifts the whole position, but the top of it is genuinely worth "
                      "real money and every run of the optimizer buys a tight end in "
                      "this range. It is still a bargain relative to what the position "
                      "produces - just not a single-digit one."),
    ("QB",   "3-32",  "Do not wait until the end. Completions, attempts, passing "
                      "first downs and the 25-completion bonus mean every volume "
                      "passer clears a big number, so a cheap arm is usually right. "
                      "But if the backfield came in under budget, the elite arm is a "
                      "legitimate place to put the savings rather than reaching at WR."),
    ("FLEX", "19-38", "The third back. This slot is an RB, not a WR."),
    ("REC_FLEX", "3-11", "The quiet structural edge: this slot takes a TIGHT END. A "
                        "second cheap TE here scores close to the WR3 you would "
                        "otherwise start, and frees most of that money for the "
                        "backfield. Do not spend WR3 money on this slot."),
    ("K/DEF", "2",    "Minimum bid, both. Neither is projected and neither should be."),
    ("BN",   "15-28", "Four spots. Handcuff your anchor first, then dart throws."),
]

BUDGET_NOTE = (
    "Twelve teams and a $250 cap means $3,000 chasing 168 players, so the room is "
    "shallower than a 14-team league and stars cost relatively more. The scoring "
    "hands you one big structural edge: consensus ADP is format-blind, so it prices "
    "quarterbacks and tight ends as if the volume and first-down bonuses did not "
    "exist. Both positions are nearly free, and REC_FLEX accepts a tight end. "
    "The optimizer is emphatic about the SHAPE - three backs, a real tight end "
    "plus a cheap second one in REC_FLEX, receivers last - and relaxed about the "
    "SPEND. Anchoring the backfield and spreading it across three mid-priced backs "
    "finish within a handful of points, so treat the one big-ticket bid as optional "
    "rather than mandatory, and let the room decide which path you take. Nominate "
    "the expensive receivers early to drain other rosters while the cheap passers "
    "sit untouched."
)

# ---------------------------------------------------------------- targets

TARGETS: dict[str, tuple[str, str]] = {
    # ---------------------------------------------------------- anchor
    "Bijan Robinson": (
        "anchor",
        "The archetype this scoring was built to reward: every-down back, goal-line "
        "work, and a receiving role that stacks reception first downs on top of "
        "rushing ones. If you win one bidding war, win this one.",
    ),
    "Jahmyr Gibbs": (
        "anchor",
        "Elite efficiency plus real receiving volume. The Detroit split caps his "
        "carries slightly, which is the only reason he is not clear of Bijan here.",
    ),
    "Jonathan Taylor": (
        "anchor",
        "Pure volume rusher on a run-first offense. Almost none of his value depends "
        "on touchdown luck, which is exactly what you want when first downs pay.",
    ),
    "De'Von Achane": (
        "anchor",
        "Carries and targets in the same body. Miami's pace inflates the raw play "
        "count he needs to clear per-game bonuses.",
    ),
    "James Cook": (
        "anchor",
        "Buffalo's backfield is his, and a rushing offense that leads late converts "
        "an unusual number of short-yardage first downs.",
    ),
    "Puka Nacua": (
        "avoid",
        "A price objection, not a player objection - he really does generate "
        "reception first downs at a rate nobody else at the position matches. "
        "But the bigger budget inflated receiver bidding faster than it moved his "
        "value, and the model now has him a full tier above his worth. Let someone "
        "else pay the premium and take the back instead.",
    ),

    # ---------------------------------------------------------- value
    "Kyren Williams": (
        "value",
        "The purest expression of this league's scoring. Enormous carry share, "
        "goal-line monopoly, and he clears the 20-carry game bonus repeatedly. "
        "ADP treats him as a boring back; the model treats him as a top-five asset.",
    ),
    "Breece Hall": (
        "value",
        "Volume plus receiving work, and the market has soured on him after a "
        "middling season. The usage that matters here never went away.",
    ),
    "Bucky Irving": (
        "value",
        "Won the backfield outright. A back with a full workload is worth far more "
        "here than his draft position implies.",
    ),
    "Quinshon Judkins": (
        "value",
        "Lead back on a team that wants to run. Thin sample, but the snaps he has "
        "played came with real first-down volume.",
    ),
    "D'Andre Swift": (
        "value",
        "Unloved, but he holds a starting job and catches passes. First downs do not "
        "care whether the offense around him is exciting.",
    ),
    "J.K. Dobbins": (
        "value",
        "Starting job, cheap price, and an offense that runs. The injury history is "
        "already baked into an ADP this low.",
    ),
    "TreVeyon Henderson": (
        "value",
        "Explosive back trending toward the larger share of the committee. Buy before "
        "the split resolves publicly.",
    ),

    "Josh Allen": (
        "value",
        "The rushing quarterback in a format that pays 1.5 per rushing first down on "
        "top of a generous passing line, and the highest-scoring player in the league "
        "by raw points. Genuinely underpriced - but the cheap volume passers below "
        "give up only a couple of points a game for a small fraction of the cost, so "
        "take him only if the room lets him fall.",
    ),
    "Jalen Hurts": (
        "value",
        "Tush-push first downs are worth real money here, and nobody converts more of "
        "them. This is close to a scoring-format arbitrage.",
    ),
    "Brock Purdy": (
        "value",
        "High completion volume in a rhythm offense. The 25-completion game bonus and "
        "per-completion scoring reward him repeatedly while ADP ignores him.",
    ),
    "Bo Nix": (
        "value",
        "Attempts, completions and rushing first downs all at once, at a price that "
        "assumes he is a streamer. The most mispriced player on the board.",
    ),
    "Jayden Daniels": (
        "value",
        "Rushing quarterback, and his scrambles convert first downs rather than "
        "chewing yardage. Cheap relative to what he produces here.",
    ),
    "Drake Maye": (
        "value",
        "Volume passer on an offense that trails often. Attempts and incompletions "
        "are close to a wash in this format, so the volume is nearly free upside.",
    ),
    "Trevor Lawrence": (
        "value",
        "Pure attempt volume. Nothing about him needs to improve for the scoring to "
        "pay him more than his price.",
    ),
    "Patrick Mahomes": (
        "value",
        "Attempt and completion volume have stayed elite even as the efficiency "
        "narrative turned. The room has moved on; the scoring has not.",
    ),

    "Trey McBride": (
        "value",
        "Reception first downs plus the tight-end first-down bonus make him score "
        "like a WR1. He is the largest single positional inefficiency in this league.",
    ),
    "Brock Bowers": (
        "value",
        "Target volume unheard of at the position. Same first-down mechanics as "
        "McBride, at a slightly lower price.",
    ),
    "Sam LaPorta": (
        "value",
        "Chain-moving tight end on a good offense. His profile is short receptions "
        "that convert, which is precisely what this scoring pays for.",
    ),
    "George Kittle": (
        "value",
        "Came off PUP this week and the market has not repriced him at all - he is "
        "still carried at a backup's price. Nobody at the position converts "
        "receptions into first downs at his rate, which is the single thing this "
        "scoring pays most for. Still carrying a questionable tag, so confirm he "
        "practices before the draft, but at this price the flier is nearly free and "
        "he is cheap enough to start in REC_FLEX.",
    ),
    "Tucker Kraft": (
        "value",
        "Grabbed the job and never gave it back. Priced as a backup tight end.",
    ),
    "Kyle Pitts": (
        "value",
        "Perennial disappointment by yardage, but the reception volume still lands "
        "first downs, and the price now assumes nothing at all.",
    ),

    "Brian Thomas Jr.": (
        "value",
        "One of the few receivers whose target volume clears the bar this format "
        "sets. Down season depressed the price without changing the role.",
    ),
    "Jordan Addison": (
        "value",
        "Full-season starting role at a price built on a partial season.",
    ),

    # ---------------------------------------------------------- dark horse
    "Tyrone Tracy Jr.": (
        "dark_horse",
        "A hurt starter ahead of him is all that separates him from a real workload, "
        "and a workload is what pays here.",
    ),
    "Harold Fannin Jr.": (
        "dark_horse",
        "Young tight end with a target share already trending up. The position is so "
        "cheap that the flier costs nothing.",
    ),

    # ---------------------------------------------------------- avoid
    "Justin Jefferson": (
        "avoid",
        "The best receiver alive and still the wrong buy at this price. Half PPR "
        "plus a rushing-first-down premium means elite receiver production simply "
        "does not separate the way it does in a normal league.",
    ),
    "Ja'Marr Chase": (
        "avoid",
        "Same problem as Jefferson, one tier louder. The room will pay a full-PPR "
        "price for a half-PPR outcome.",
    ),
    "CeeDee Lamb": (
        "avoid",
        "Priced off name and target share. Neither converts into enough here.",
    ),
    "A.J. Brown": (
        "avoid",
        "Big plays over volume is the wrong shape for a format that pays per first "
        "down and per reception.",
    ),
    "Rashee Rice": (
        "avoid",
        "Availability risk on top of a price that already assumes a full season.",
    ),
    "Derrick Henry": (
        "avoid",
        "Everything about the profile fits this scoring except his age, and the age "
        "is the part that decides the season. Let someone else buy the last year.",
    ),
    "Saquon Barkley": (
        "avoid",
        "Enormous workload already behind him and a price that assumes it repeats.",
    ),
    "Christian McCaffrey": (
        "avoid",
        "Would be the best player in this format at twenty-seven. He is not "
        "twenty-seven, and the market is still charging as if he is.",
    ),
    "Kenneth Walker III": (
        "avoid",
        "Committee usage and a persistent soft-tissue history. The workload this "
        "scoring demands has never actually arrived.",
    ),
}

# Players parked in `avoid` for injury, age or shape reasons rather than price.
# The audit will not flag these for carrying a positive edge.
RISK_NOT_PRICE: set[str] = set()
