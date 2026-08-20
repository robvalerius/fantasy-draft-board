"""Web UI for the Battle for the Belt XIV auction draft.

    .\.venv\Scripts\python.exe app.py

Then open http://localhost:5000 . Shares data/draft_state.csv with draft.py, so
you can use either interface (or both) during the draft.
"""

from __future__ import annotations

import math

import pandas as pd
from flask import Flask, jsonify, render_template, request

from draft import Draft, STATE, _paid
from league_config import BUDGET, NUM_TEAMS, ROSTER_SIZE, STARTERS
from targets import BUDGET_NOTE, PLAN, note_of
from watchlist import TEAM_CHANGES

app = Flask(__name__)
draft = Draft()

POSITIONS = ("QB", "RB", "WR", "TE", "K", "DEF")


def _clean(v):
    """JSON can't hold NaN/inf; pandas is full of them."""
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, (pd.Timestamp,)):
        return str(v)
    return v


def bid_range(adj: int) -> tuple[int, int]:
    """Bargain price and walk-away price around an inflation-adjusted value.

    The band is proportionally wider at the cheap end, where being $2 off matters
    little, and tighter at the top, where discipline decides your draft. Above $60
    the ceiling sits just under our own estimate: on an expensive player our point
    estimate is the least reliable, and overpaying there is what wrecks a roster.
    """
    if adj <= 1:
        return 1, 2
    if adj <= 5:
        return max(1, adj - 2), adj + 3
    if adj <= 20:
        return round(adj * 0.70), round(adj * 1.30)
    if adj <= 60:
        return round(adj * 0.78), round(adj * 1.15)
    return round(adj * 0.82), round(adj * 1.02)


def state_payload() -> dict:
    infl = draft.inflation()
    have: dict[str, int] = {}
    for s in draft.my_picks:
        have[s["position"]] = have.get(s["position"], 0) + 1

    spend: dict[str, int] = {"ME": 0}
    count: dict[str, int] = {"ME": 0}
    for s in draft.sales:
        spend[s["team"]] = spend.get(s["team"], 0) + _paid(s)
        count[s["team"]] = count.get(s["team"], 0) + 1

    teams = []
    for t in spend:
        left = BUDGET - spend[t]
        slots = ROSTER_SIZE - count[t]
        teams.append({
            "team": t,
            "spent": spend[t],
            "left": left,
            "slots": slots,
            "max_bid": max(0, left - slots + 1),
        })
    teams.sort(key=lambda x: -x["left"])

    return {
        "budget": draft.my_budget,
        "spent": draft.my_spent,
        "slots_left": draft.my_slots_left,
        "max_bid": draft.max_bid,
        "inflation": round(infl, 3),
        "picks_made": len(draft.sales),
        "picks_total": ROSTER_SIZE * NUM_TEAMS,
        "roster": [dict(s, paid=_paid(s)) for s in draft.my_picks],
        "counts": have,
        "needs": {p: max(0, STARTERS.get(p, 0) - have.get(p, 0)) for p in POSITIONS},
        "teams": teams,
        "recent": [dict(s, paid=_paid(s)) for s in reversed(draft.sales[-15:])],
        "cap": BUDGET,
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/state")
def api_state():
    return jsonify(state_payload())


@app.get("/api/players")
def api_players():
    q = request.args.get("q", "").strip().lower()
    pos = request.args.get("pos", "").strip().upper()
    only_watch = request.args.get("watch") == "1"
    only_target = request.args.get("target") == "1"
    limit = int(request.args.get("limit", 400))

    df = draft.available
    if pos and pos != "ALL":
        df = df[df["position"] == pos]
    if only_watch:
        df = df[df["watch"]]
    if only_target:
        df = df[df["target"].notna()]
    if q:
        df = df[df["key"].str.contains(q, na=False, regex=False)]

    sort = request.args.get("sort", "value")
    cols = {"value": "value", "market": "market", "edge": "edge", "adp": "adp"}
    col = cols.get(sort, "value")
    df = df.sort_values(col, ascending=(col == "adp"),
                        na_position="last", kind="stable")

    infl = draft.inflation()
    max_bid = draft.max_bid
    out = []
    for r in df.head(limit).itertuples():
        adj = round(r.value * infl)
        lo, hi = bid_range(adj)
        out.append({
            "name": r.name,
            "position": r.position,
            "pos_rank": int(r.pos_rank),
            "proj_points": round(float(r.proj_points), 1),
            "proj_ppg": round(float(r.proj_ppg), 1),
            "vorp": round(float(r.vorp), 1),
            "value": int(r.value),
            "adj": adj,
            "min": lo,
            "max": hi,
            "over_budget": hi > max_bid,
            "affordable": adj <= max_bid,
            "adp": _clean(round(float(r.adp), 1) if pd.notna(r.adp) else None),
            "market": int(r.market),
            "edge": int(r.edge),
            "low_conf": bool(r.low_conf),
            "thin": bool(getattr(r, "thin", False)) and int(r.edge) != 0,
            "deferred": bool(getattr(r, "thin", False)) and int(r.edge) == 0,
            "status": _clean(getattr(r, "status", None) or None),
            "target": _clean(getattr(r, "target", None)),
            "target_note": note_of(r.name),
            "watch": bool(r.watch),
            "injury": _clean(getattr(r, "injury_status", None)),
            "team_change": TEAM_CHANGES.get(r.name),
            "exp_rank": _clean(int(r.expert_rank) if pd.notna(getattr(r, "expert_rank", None)) else None),
            "exp_adp": _clean(int(r.expert_adp_rank) if pd.notna(getattr(r, "expert_adp_rank", None)) else None),
            "exp_move": int(getattr(r, "expert_move", 0) or 0),
        })
    return jsonify({"players": out, "shown": len(out), "total": len(df)})


@app.get("/api/edge")
def api_edge():
    """Dollar edge: our league value minus what the market actually pays."""
    df = draft.available
    df = df[(~df["low_conf"]) & (df["market"] > 1)]
    if df.empty:
        return jsonify({"under": [], "over": [], "plan": PLAN, "note": BUDGET_NOTE})

    def rows(sub):
        return [{
            "name": r.name,
            "position": r.position,
            "pos_rank": int(r.pos_rank),
            "adp": _clean(round(float(r.adp), 1) if pd.notna(r.adp) else None),
            "value": int(r.value),
            "market": int(r.market),
            "edge": int(r.edge),
            "watch": bool(r.watch),
            "target": _clean(getattr(r, "target", None)),
        } for r in sub.itertuples()]

    return jsonify({
        "under": rows(df.nlargest(20, "edge")),
        "over": rows(df.nsmallest(12, "edge")),
        "plan": [{"pos": p, "spend": s, "note": n} for p, s, n in PLAN],
        "note": BUDGET_NOTE,
    })


@app.post("/api/record")
def api_record():
    body = request.get_json(force=True)
    name = body.get("player", "")
    team = (body.get("team") or "OTHER").strip().upper() or "OTHER"
    raw = body.get("price")

    price: int | None
    if raw in (None, "", "?"):
        price = None
    else:
        try:
            price = int(raw)
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "price must be a number"}), 400
        if price < 1:
            return jsonify({"ok": False, "error": "price must be at least $1"}), 400

    sale = draft.record(name, price, team)
    if sale is None:
        hit = draft.find(name)
        if hit is not None and hit["name"].lower() in draft.drafted:
            return jsonify({"ok": False,
                            "error": f"{hit['name']} is already off the board"}), 409
        return jsonify({"ok": False, "error": f"no match for '{name}'"}), 404
    delta = None if price is None else price - sale["value"]
    verdict = ("unknown" if delta is None else
               "bargain" if delta <= -8 else "overpay" if delta >= 8 else "fair")
    return jsonify({"ok": True, "sale": sale, "delta": delta,
                    "verdict": verdict, "state": state_payload()})


@app.post("/api/undo")
def api_undo():
    s = draft.undo()
    if s is None:
        return jsonify({"ok": False, "error": "nothing to undo"}), 400
    return jsonify({"ok": True, "removed": s, "state": state_payload()})


@app.post("/api/reset")
def api_reset():
    draft.sales = []
    if STATE.exists():
        STATE.unlink()
    return jsonify({"ok": True, "state": state_payload()})


if __name__ == "__main__":
    print("\n  Draft board:  http://localhost:5000\n")
    app.run(host="127.0.0.1", port=5000, debug=False)
