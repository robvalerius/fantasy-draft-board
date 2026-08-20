"""Run a spread of roster constructions so we can compare shapes, not just find one."""

import optimize as O

BENCH = 3          # 3 bench spots at $1
KDEF = 2           # K + DEF at $1 each
STARTER_BUDGET = 269 - BENCH - KDEF   # 264


def core(res):
    return {r["name"] for r in res["roster"]} if res else set()


def summary(res, label):
    if not res:
        return None
    return (label, res["points"], res["spend"], res["shape"], res["roster"])


def main():
    d = O.pool()
    out = []

    base = O.optimize(STARTER_BUDGET, d)
    out.append(summary(base, "A. Unconstrained max"))

    # force each shape so we can see the tradeoff explicitly
    saved = O.SHAPES
    names = {
        (1, 2, 4, 1): "B. 2RB / 4WR / 1TE",
        (1, 3, 3, 1): "C. 3RB / 3WR / 1TE",
        (1, 2, 3, 2): "D. 2RB / 3WR / 2TE",
        (1, 3, 2, 2): "E. 3RB / 2WR / 2TE",
        (1, 2, 2, 3): "F. 2RB / 2WR / 3TE",
    }
    for shp, lbl in names.items():
        O.SHAPES = [shp]
        out.append(summary(O.optimize(STARTER_BUDGET, d), lbl))
    O.SHAPES = saved

    # studs-and-scrubs vs balanced: cap the most expensive player
    for cap, lbl in [(60, "G. No player over $60"), (45, "H. No player over $45")]:
        O.SHAPES = saved
        sub = d[d.cost <= cap]
        out.append(summary(O.optimize(STARTER_BUDGET, sub), lbl))

    # anchor builds - lock the elite RB and see what's left
    for anchor in ["Jahmyr Gibbs", "Bijan Robinson", "Ashton Jeanty", "De'Von Achane"]:
        O.SHAPES = saved
        r = O.optimize(STARTER_BUDGET, d, lock=[anchor])
        out.append(summary(r, f"I. Anchor: {anchor}"))

    out = [o for o in out if o]
    out.sort(key=lambda x: -x[1])

    print(f"{'BUILD':<28} {'PROJ':>7} {'SPEND':>6}  SHAPE")
    print("-" * 74)
    for lbl, pts, spend, shape, _ in out:
        s = f"{shape['QB']}QB {shape['RB']}RB {shape['WR']}WR {shape['TE']}TE"
        print(f"{lbl:<28} {pts:>7.0f} {spend:>6}  {s}")

    for lbl, pts, spend, shape, roster in out:
        res = {"shape": shape, "roster": roster, "spend": spend, "points": pts}
        O.show(res, BENCH, lbl)


if __name__ == "__main__":
    main()
