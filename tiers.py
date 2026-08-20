"""Live-auction menu: who to buy at each price tier, so we can substitute on the fly.

The single optimal roster is fragile - it assumes we win every player at exactly
the model price. In a real room we need to know the next-best body at each tier.
"""

import optimize as O

TIERS = [(80, 999), (55, 79), (35, 54), (20, 34), (10, 19), (4, 9), (1, 3)]


def main():
    d = O.pool()
    d = d[d.cost >= 1]

    for pos in ["RB", "WR", "TE", "QB"]:
        s = d[d.position == pos]
        print("=" * 82)
        print(f"{pos}")
        print("=" * 82)
        for lo, hi in TIERS:
            t = s[(s.cost >= lo) & (s.cost <= hi)].sort_values("eff_points", ascending=False).head(5)
            if not len(t):
                continue
            band = f"${lo}-{hi}" if hi < 999 else f"${lo}+"
            print(f"  {band:<9}", end="")
            first = True
            for r in t.to_dict("records"):
                pad = "" if first else " " * 11
                mark = "!" if int(r["value"]) - int(r["cost"]) >= 20 else " "
                print(f"{pad}{mark} {r["name"]:<24} ${int(r["cost"]):>3}  val ${int(r["value"]):>3}  "
                      f"{r["eff_points"]:>6.1f}pts  edge {int(r["value"])-int(r["cost"]):>+4}")
                first = False
            print()


if __name__ == "__main__":
    main()
