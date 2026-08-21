"""Blend an expert's positional rankings into our valuation.

FIRST ATTEMPT reassigned each position's dollars in the expert's order.
Measuring it showed why that is the wrong instrument: the expert correlates
0.89-0.97 with ADP but only 0.71-0.88 with us. Most of his list simply *is* the
consensus, so blending it wholesale just re-imports the market and deletes the
edges we built the model to find.

WHAT WE ACTUALLY WANT is the part of his opinion that is his own - where he
disagrees with ADP. So:

    tilt   = curve(expert_rank) - curve(adp_pos_rank)
    value += w * tilt

`curve(k)` is the dollar price the market puts on the k-th player at that
position. If he ranks a guy exactly where ADP does, tilt is zero and we do not
touch him. If he has RB29 as his RB19, we move him by the dollar gap between
those two rungs. The consensus half of his list contributes nothing, which is
correct - we already have the consensus, priced.
"""

import numpy as np
import pandas as pd

import market_value as MV
from league_config import EXPERT_RANKS, SHARED_DATA

WEIGHT = 0.60          # how much of his disagreement-with-ADP we take
PATH = SHARED_DATA / EXPERT_RANKS

ALIAS = {"kenneth gainwell": "kenny gainwell"}


def load():
    e = pd.read_csv(PATH)
    e["key"] = e["name"].map(MV._norm).replace(ALIAS)
    return e


def _curve(d, pos):
    """Dollar price the market puts on the k-th ranked player at a position."""
    v = np.sort(d.loc[d.position == pos, "market"].values)[::-1].astype(float)
    v = v[v >= 1]

    def f(k):
        k = np.clip(np.asarray(k, dtype=float), 1, len(v))
        lo = np.floor(k).astype(int) - 1
        hi = np.ceil(k).astype(int) - 1
        frac = k - np.floor(k)
        return v[lo] * (1 - frac) + v[hi] * frac

    return f


def apply(d=None, w=WEIGHT):
    """Tilt our values by the expert's disagreement with ADP."""
    d = MV.merged() if d is None else d.copy()
    e = load()

    d["model_only"] = d["value"].astype(int)
    d["value"] = d["value"].astype(float)
    d["expert_rank"] = np.nan
    d["expert_adp_rank"] = np.nan
    d["expert_tilt"] = 0.0

    for pos, grp in e.groupby("position"):
        curve = _curve(d, pos)
        m = (d.position == pos) & d.key.isin(grp.key)
        if not m.any():
            continue
        g = grp.set_index("key")
        er = d.loc[m, "key"].map(g["expert_rank"]).astype(float)
        ar = d.loc[m, "key"].map(g["adp_pos_rank"]).astype(float)
        d.loc[m, "expert_rank"] = er
        d.loc[m, "expert_adp_rank"] = ar
        d.loc[m, "expert_tilt"] = curve(er.values) - curve(ar.values)

    # never tilt a player pinned to market for lack of any opinion
    d.loc[d.low_conf, "expert_tilt"] = 0.0

    d["value"] = (d["value"] + w * d["expert_tilt"]).clip(lower=1)
    d = _rebalance(d)
    d["value"] = d["value"].round().astype(int)
    d["edge"] = d["value"] - d["market"]
    d["expert_move"] = d["value"] - d["model_only"]
    return d


def _rebalance(d):
    from league_config import BUDGET, NUM_TEAMS, TOTAL_DRAFTED
    target = BUDGET * NUM_TEAMS
    cur = d.nlargest(TOTAL_DRAFTED, "value")["value"].sum()
    if cur <= TOTAL_DRAFTED:
        return d
    f = (target - TOTAL_DRAFTED) / (cur - TOTAL_DRAFTED)
    d["value"] = 1 + (d["value"] - 1).clip(lower=0) * f
    return d


def unmatched():
    d = MV.merged()
    e = load()
    return e[~e["key"].isin(d["key"])]


def report(w=WEIGHT, n=14):
    d = apply(w=w)
    d = d[d.expert_rank.notna() & (d.expert_move != 0)]

    def blk(sub, title):
        print(f"\n{'='*96}\n{title}\n{'='*96}")
        print(f"{'PLAYER':<24} {'EXPERT':>7} {'ADP':>7} {'SHIFT':>6} "
              f"{'WAS':>5} {'NOW':>5} {'MKT':>5} {'EDGE':>6}")
        for r in sub.to_dict("records"):
            tag = f"{r['position']}{int(r['expert_rank'])}"
            adp = f"{r['position']}{int(r['expert_adp_rank'])}"
            print(f"{r['name']:<24} {tag:>7} {adp:>7} "
                  f"{int(r['expert_adp_rank'])-int(r['expert_rank']):>+6} "
                  f"{r['model_only']:>5} {r['value']:>5} {r['market']:>5} {r['edge']:>+6}")

    blk(d.nlargest(n, "expert_move"), "HE IS HIGHER THAN CONSENSUS  ->  we raise them")
    blk(d.nsmallest(n, "expert_move"), "HE IS LOWER THAN CONSENSUS  ->  we cut them")
    return d


if __name__ == "__main__":
    miss = unmatched()
    if len(miss):
        print("2026 rookies with no NFL history - cannot value: "
              + ", ".join(miss["name"]))
    report()
