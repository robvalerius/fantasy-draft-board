r"""Bake the draft board into a static site for GitHub Pages.

    .\.venv\Scripts\python.exe build_static.py

Writes docs/ - index.html, data.js, shim.js. There is no server in the output:
static_shim.js intercepts fetch and answers the same four endpoints from a
baked snapshot, with draft state in localStorage. That way templates/index.html
stays the single source of truth for the UI.
"""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import pandas as pd

from app import POSITIONS, bid_range  # noqa: F401  (bid_range ported in JS)
from draft import Draft
from league_config import BUDGET, NUM_TEAMS, ROSTER_SIZE, STARTERS
from targets import BUDGET_NOTE, PLAN, note_of
from watchlist import TEAM_CHANGES

OUT = Path("docs")


def _clean(v):
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def players_payload(draft: Draft) -> list[dict]:
    df = draft.players.sort_values("value", ascending=False, kind="stable")
    out = []
    for r in df.itertuples():
        edge = int(r.edge)
        thin = bool(getattr(r, "thin", False))
        out.append({
            "name": r.name,
            "key": str(r.key),
            "position": r.position,
            "pos_rank": int(r.pos_rank),
            "proj_points": round(float(r.proj_points), 1),
            "proj_ppg": round(float(r.proj_ppg), 1),
            "value": int(r.value),
            "adp": _clean(round(float(r.adp), 1) if pd.notna(r.adp) else None),
            "market": int(r.market),
            "mkt_200": int(getattr(r, "mkt_200", 1)),
            "edge": edge,
            "low_conf": bool(r.low_conf),
            "thin": thin and edge != 0,
            "deferred": thin and edge == 0,
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
    return out


def build_html() -> str:
    html = Path("templates/index.html").read_text(encoding="utf-8")

    # The shim must replace fetch before the page's own <script> runs.
    html = html.replace(
        "<script>",
        '<script src="data.js"></script>\n<script src="shim.js"></script>\n<script>',
        1,
    )
    # No server means no shared state; say so rather than implying sync.
    html = html.replace(
        "Clears every pick and restores all players. Cannot be undone.",
        "Clears every pick on this device. Draft state is saved in this browser only.",
    )
    return html


def main() -> None:
    draft = Draft()
    OUT.mkdir(exist_ok=True)

    data = {
        "cap": BUDGET,
        "num_teams": NUM_TEAMS,
        "roster_size": ROSTER_SIZE,
        "starters": dict(STARTERS),
        "positions": list(POSITIONS),
        "plan": [{"pos": p, "spend": s, "note": n} for p, s, n in PLAN],
        "budget_note": BUDGET_NOTE,
        "players": players_payload(draft),
    }

    (OUT / "data.js").write_text(
        "const DATA = " + json.dumps(data, separators=(",", ":")) + ";",
        encoding="utf-8")
    shutil.copy("static_shim.js", OUT / "shim.js")
    (OUT / "index.html").write_text(build_html(), encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    # A single self-contained file needs no hosting at all: AirDrop or email it
    # to a phone and open it from Files. Same board, fully offline.
    single = (build_html()
              .replace('<script src="data.js"></script>',
                       "<script>" + (OUT / "data.js").read_text(encoding="utf-8") + "</script>")
              .replace('<script src="shim.js"></script>',
                       "<script>" + Path("static_shim.js").read_text(encoding="utf-8") + "</script>"))
    Path("draft-board.html").write_text(single, encoding="utf-8")

    kb = sum(f.stat().st_size for f in OUT.iterdir()) // 1024
    print(f"  docs/  {len(data['players'])} players, {kb} KB")
    print(f"  draft-board.html  {Path('draft-board.html').stat().st_size // 1024} KB standalone")
    print("  open docs/index.html to test, then push and enable Pages on /docs")


if __name__ == "__main__":
    main()
