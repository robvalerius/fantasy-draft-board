"""Roster optimizer: best starting lineup buyable at expected market prices.

Two things this has to get right that a naive knapsack does not:

1. COST is the *market* price (what the player will actually go for), not our
   value. We are shopping in a real room, not our own model.

2. POINTS must be consistent with the deference logic in market_value.merged().
   For thin/no-opinion players we overrode `value` up to the market but their
   `proj_points` still reflects a backward-looking box-score model that has no
   idea they won a job. Feeding raw proj_points to the optimizer would make it
   structurally refuse to draft any rookie. So we fit points ~ f(value) on the
   confident players and impute market-implied points for the deferred ones.
"""

import numpy as np
import pandas as pd

import market_value
from league_config import BUDGET, ROSTER_SIZE

# 8 offensive starters: QB1 RB2 WR2 TE1 + W/T + W/R/T.
# Extra RBs can only fill W/R/T, so nRB is capped at 3.
SHAPES = [
    (1, 2, 4, 1),
    (1, 2, 3, 2),
    (1, 2, 2, 3),
    (1, 3, 3, 1),
    (1, 3, 2, 2),
]
POS = ["QB", "RB", "WR", "TE"]


def effective_points(d):
    """Points consistent with the deferred value, per the module docstring."""
    d = d.copy()
    conf = d[(~d.thin) & (~d.low_conf) & (d.value >= 3)]
    eff = {}
    for p in POS:
        c = conf[conf.position == p]
        # log-log fit: points rise sublinearly in dollars
        a, b = np.polyfit(np.log(c.value.clip(lower=1)), np.log(c.proj_points.clip(lower=1)), 1)
        eff[p] = (a, b)

    def row(r):
        if r.position not in eff:
            return r.proj_points
        if r.value <= r.model_value:
            return r.proj_points          # we kept our own opinion
        a, b = eff[r.position]
        implied = np.exp(b) * (max(r.value, 1) ** a)
        # deference is a floor, never a haircut
        return max(r.proj_points, implied)

    d["eff_points"] = d.apply(row, axis=1)
    return d


def pool(min_market=0, use_expert=True):
    d = market_value.merged()
    d = d[d.position.isin(POS)]
    d = d[~d.out]                                  # no PUP/IR bodies in a starting slot
    d = d[d.market >= max(1, min_market)]
    # points imputation keys off market deference only, so compute it before the
    # expert tilt - his opinion should move prices, not invent production.
    d = effective_points(d)
    if use_expert:
        import expert
        ev = expert.apply()[["key", "value", "expert_move"]].rename(
            columns={"value": "exp_value"})
        d = d.merge(ev, on="key", how="left")
        d["value"] = d["exp_value"].fillna(d["value"]).astype(int)
        d["expert_move"] = d["expert_move"].fillna(0).astype(int)
        d = d.drop(columns=["exp_value"])
    d["cost"] = d.market.astype(int).clip(lower=1)
    return d.reset_index(drop=True)


def _pos_table(df, kmax, budget):
    """best[k][c] = max eff_points using exactly k players from df costing exactly <= c."""
    NEG = -1e9
    best = np.full((kmax + 1, budget + 1), NEG)
    best[0, :] = 0.0
    pick = [[None] * (budget + 1) for _ in range(kmax + 1)]
    for i, r in enumerate(df.itertuples()):
        c, v = int(r.cost), float(r.eff_points)
        for k in range(kmax, 0, -1):
            for b in range(budget, c - 1, -1):
                cand = best[k - 1][b - c] + v
                if cand > best[k][b]:
                    best[k][b] = cand
                    pick[k][b] = (i, b - c)
    return best, pick


def _unwind(df, pick, k, b):
    out = []
    while k > 0:
        p = pick[k][b]
        if p is None:
            break
        i, prev = p
        out.append(df.iloc[i])
        k, b = k - 1, prev
    return out


def optimize(budget_starters, d=None, ban=(), lock=()):
    """Return the best 8-man offensive core for a given starter budget."""
    d = pool() if d is None else d
    if ban:
        d = d[~d.name.isin(ban)]

    locked = [d[d.name == n].iloc[0] for n in lock]
    spent = sum(int(p.cost) for p in locked)
    need = {p: 0 for p in POS}
    for p in locked:
        need[p.position] += 1
    d = d[~d.name.isin(lock)]
    b = budget_starters - spent
    if b < 0:
        return None

    tables = {}
    for p in POS:
        sub = d[d.position == p].sort_values("eff_points", ascending=False).head(70).reset_index(drop=True)
        tables[p] = (sub,) + _pos_table(sub, 5, b)

    best = None
    for shape in SHAPES:
        want = dict(zip(POS, shape))
        if any(want[p] < need[p] for p in POS):
            continue
        k = {p: want[p] - need[p] for p in POS}

        # convolve the four position tables over budget
        cur = np.zeros(b + 1)
        traces = {}
        for p in POS:
            row = tables[p][1][k[p]]
            nxt = np.full(b + 1, -1e9)
            nt = [None] * (b + 1)
            for c in range(b + 1):
                if cur[c] < -1e8:
                    continue
                for c2 in range(0, b - c + 1):
                    if row[c2] < -1e8:
                        continue
                    t = cur[c] + row[c2]
                    if t > nxt[c + c2]:
                        nxt[c + c2] = t
                        nt[c + c2] = (c, c2)
            cur, traces[p] = nxt, nt

        c_best = int(np.argmax(cur))
        if best is None or cur[c_best] > best[0]:
            best = (cur[c_best], shape, k, c_best, traces)

    if best is None:
        return None

    _, shape, k, c_best, traces = best
    # walk the convolution backwards to recover each position's spend
    spends = {}
    c = c_best
    for p in reversed(POS):
        prev, mine = traces[p][c]
        spends[p] = mine
        c = prev

    roster = list(locked)
    for p in POS:
        sub, tb, pick = tables[p]
        roster += _unwind(sub, pick, k[p], spends[p])

    return {
        "shape": dict(zip(POS, shape)),
        "roster": roster,
        "spend": sum(int(r.cost) for r in roster),
        "points": sum(float(r.eff_points) for r in roster),
    }


def show(res, bench_budget, label=""):
    if not res:
        print(f"{label}: infeasible")
        return
    rows = sorted(res["roster"], key=lambda r: (-int(r.cost)))
    print(f"\n{'='*74}\n{label}   shape {res['shape']}   starters ${res['spend']}   proj {res['points']:.0f}\n{'-'*74}")
    print(f"{'POS':<4} {'PLAYER':<24} {'COST':>5} {'VAL':>5} {'EDGE':>5} {'PTS':>7}")
    for r in rows:
        edge = int(r.value) - int(r.cost)
        print(f"{r.position:<4} {r["name"]:<24} {int(r.cost):>5} {int(r.value):>5} {edge:>+5} {r.eff_points:>7.1f}")
    print(f"{'-'*74}\nK+DEF $2   bench ${bench_budget}   TOTAL ${res['spend'] + 2 + bench_budget} of ${BUDGET}")
