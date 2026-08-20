"""Your watchlist - players flagged across all analysis.

Soft preference, not a constraint. Tools mark these with * and can filter to them,
but valuations stay honest: if a guy is bad value, the tool still says so.
"""

WATCHLIST = [
    # RB
    "Jahmyr Gibbs",
    "Bijan Robinson",
    "Christian McCaffrey",
    "Ashton Jeanty",
    "Kenneth Walker III",
    "Omarion Hampton",
    "Jeremiyah Love",
    "Bhayshul Tuten",
    # WR
    "Jaxon Smith-Njigba",
    "CeeDee Lamb",
    "Tee Higgins",
    "Malik Nabers",
    "Rashee Rice",
    "Emeka Egbuka",
    "Ladd McConkey",
    "Parker Washington",
    "Carnell Tate",
    "Marvin Harrison Jr.",
    "Josh Downs",
    "Makai Lemon",
    "Jakobi Meyers",
    "Jalen Coker",
    "Jalen Nailor",
    # TE
    "Trey McBride",
    "Tyler Warren",
    "Tucker Kraft",
    "Sam LaPorta",
    # QB
    "Josh Allen",
    "Lamar Jackson",
    "Drake Maye",
    "Trevor Lawrence",
]

# Teams differ from 2025 - affects projections that assume prior situation
TEAM_CHANGES = {
    "Kenneth Walker III": "KC",
    "Omarion Hampton": "LAC",
    "Jeremiyah Love": "ARI",
    "Carnell Tate": "TEN",
    "Makai Lemon": "PHI",
    "Jakobi Meyers": "JAX",
    "Jalen Nailor": "LV",
    "Bhayshul Tuten": "JAX",
    "Parker Washington": "JAX",
    "Tee Higgins": "CIN",
}


def _norm(name: str) -> str:
    return (
        str(name).lower()
        .replace(".", "").replace("'", "").replace("-", " ")
        .replace(" jr", "").replace(" sr", "").replace(" iii", "").replace(" ii", "")
        .strip()
    )


WATCH_KEYS = {_norm(n) for n in WATCHLIST}


def is_watched(name: str) -> bool:
    return _norm(name) in WATCH_KEYS
