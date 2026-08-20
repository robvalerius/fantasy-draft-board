"""Injury/concentration risk - the thing the points model is blind to.

A projection is an expectation. Two rosters with the same expected points can
have very different downside if one concentrates its production in fewer bodies.
This scores each build on what happens when a player misses time, and on how
replaceable he is from our own bench.
"""

import numpy as np
import optimize as O

BUILDS = {
    "1. Optimal (Nacua + Achane)": ["Puka Nacua", "De'Von Achane", "Kyren Williams",
                                    "Bucky Irving", "Jameson Williams", "Sam LaPorta",
                                    "Brian Thomas Jr.", "Brock Purdy"],
    "2. No Nacua": ["Jahmyr Gibbs", "De'Von Achane", "Malik Nabers", "Bucky Irving",
                    "Sam LaPorta", "Brian Thomas Jr.", "Brock Purdy", "Jordan Addison"],
    "3. No Achane": ["Jahmyr Gibbs", "Puka Nacua", "Kyren Williams", "Sam LaPorta",
                     "Brian Thomas Jr.", "Brock Purdy", "Quentin Johnston", "Jordan Addison"],
    "4. RB-RB (Gibbs + Bijan)": ["Jahmyr Gibbs", "Bijan Robinson", "Bucky Irving",
                                 "Jameson Williams", "Sam LaPorta", "Brian Thomas Jr.",
                                 "Brock Purdy", "Jordan Addison"],
}


def rows(d, names):
    return [d[d.name == n].iloc[0] for n in names]


def concentration(r):
    """Share of projected points sitting in the single biggest player, and HHI."""
    p = np.array([float(x.eff_points) for x in r])
    s = p / p.sum()
    return s.max(), (s ** 2).sum()


def miss_cost(d, r, weeks=4):
    """Points lost if a player misses `weeks`, replaced by the best $1 body at his position."""
    worst = 0
    who = None
    for x in r:
        repl = d[(d.position == x.position) & (d.cost <= 1)]
        rp = repl.eff_points.max() if len(repl) else 0.0
        loss = (float(x.eff_points) - rp) * weeks / 17
        if loss > worst:
            worst, who = loss, x["name"]
    return worst, who


def main():
    d = O.pool()
    print(f"{'BUILD':<30} {'PROJ':>6} {'COST':>6} {'TOP%':>6} {'HHI':>6} {'4wk LOSS':>9}  WORST CASE")
    print("-" * 96)
    for lbl, names in BUILDS.items():
        r = rows(d, names)
        pts = sum(float(x.eff_points) for x in r)
        cost = sum(int(x.cost) for x in r)
        top, hhi = concentration(r)
        loss, who = miss_cost(d, r)
        print(f"{lbl:<30} {pts:>6.0f} {cost:>6} {top:>5.1%} {hhi:>6.3f} {loss:>9.0f}  {who}")

    print("\n" + "=" * 96)
    print("HANDCUFF COST - can we insure the concentrated bets cheaply?")
    print("=" * 96)
    for tm, star in [("MIA", "De'Von Achane"), ("DET", "Jahmyr Gibbs"),
                     ("ATL", "Bijan Robinson"), ("LA", "Puka Nacua")]:
        s = d[(d.team == tm) & (d.position == d[d.name == star].iloc[0].position)]
        s = s[s.name != star].sort_values("eff_points", ascending=False).head(2)
        alt = ", ".join(f"{x['name']} ${int(x['cost'])} ({x['eff_points']:.0f}pts)"
                        for x in s.to_dict("records")) or "NONE"
        print(f"  {star:<20} backup: {alt}")


if __name__ == "__main__":
    main()
