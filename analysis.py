"""Second-order questions the headline build does not answer.

1. How much does a real bench actually cost us in starter points?
2. If someone outbids us on a linchpin, what is plan B and what does it cost?
3. Does the build survive prices coming in different from the model?
"""

import numpy as np
import optimize as O

KDEF = 2


def line(res):
    return " | ".join(f"{r['name']} ${int(r.cost)}" for r in
                      sorted(res["roster"], key=lambda x: -int(x.cost)))


def main():
    d = O.pool()

    print("=" * 78)
    print("1. BENCH TRADEOFF - what a real bench costs in starting points")
    print("=" * 78)
    print(f"{'BENCH $':>8} {'STARTER $':>10} {'PROJ':>7} {'LOSS':>7}")
    ref = None
    for bench in [3, 8, 15, 25, 40]:
        r = O.optimize(269 - KDEF - bench, d)
        if ref is None:
            ref = r["points"]
        print(f"{bench:>8} {r['spend']:>10} {r['points']:>7.0f} {r['points']-ref:>+7.0f}")

    print()
    print("=" * 78)
    print("2. CONTINGENCY - we get outbid on a linchpin")
    print("=" * 78)
    base = O.optimize(264, d)
    print(f"{'BASE':<22} {base['points']:>7.0f}   {line(base)}")
    for who in ["Puka Nacua", "Brock Purdy", "Sam LaPorta", "De'Von Achane",
                "Bucky Irving", "Kyren Williams", "Brian Thomas Jr."]:
        r = O.optimize(264, d, ban=[who])
        print(f"{'lose ' + who:<22} {r['points']:>7.0f} {r['points']-base['points']:>+6.0f}   {line(r)}")

    print()
    print("=" * 78)
    print("3. PRICE SHOCK - build with model prices, pay real prices")
    print("=" * 78)
    rng = np.random.default_rng(7)
    names = [r["name"] for r in base["roster"]]
    over = 0
    for trial in range(400):
        # auction prices are noisy and skew high on the guys everyone wants
        shock = rng.lognormal(0.0, 0.22, len(names))
        cost = sum(int(r.cost) * s for r, s in zip(base["roster"], shock))
        if cost > 264:
            over += 1
    print(f"base build costs $264 at model prices")
    print(f"with +/-22% lognormal price noise, over budget in {over/400:.0%} of rooms")

    print()
    print("=" * 78)
    print("4. VALUE-MAXIMIZING build (max our $ value, not points)")
    print("=" * 78)
    dv = d.copy()
    dv["eff_points"] = dv["value"]
    r = O.optimize(264, dv)
    for x in sorted(r["roster"], key=lambda y: -int(y.cost)):
        print(f"  {x.position:<4} {x['name']:<24} ${int(x.cost):>3}  val ${int(x.value):>3}  "
              f"edge {int(x.value)-int(x.cost):>+4}")
    print(f"  total cost ${r['spend']}  total value ${r['points']:.0f}  "
          f"surplus ${r['points']-r['spend']:.0f}")


if __name__ == "__main__":
    main()
