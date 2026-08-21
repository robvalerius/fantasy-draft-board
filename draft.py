"""Live auction assistant for Battle for the Belt XIV.

Run during the draft:  python draft.py

Commands:
  <player> $<price> <team>   record a sale     e.g.  bijan $54 mike
  me <player> $<price>       record YOUR win   e.g.  me bijan $54
  best [pos] [n]             best available by value
  edge [n]                   biggest gaps vs public ADP
  watch [pos]                your watchlist, still available
  bid <player>               max bid advice for a player
  roster                     your roster + budget
  teams                      all teams' remaining budgets
  undo                       undo last sale
  quit
"""

import re
import sys

import pandas as pd

import expert
import market_value
from league_config import BUDGET, DATA_DIR, NUM_TEAMS, ROSTER_SIZE, STARTERS
from targets import TIER_LABEL, note_of, tier_of
from watchlist import TEAM_CHANGES, is_watched

DATA_DIR.mkdir(parents=True, exist_ok=True)
STATE = DATA_DIR / "draft_state.csv"


def _paid(sale: dict) -> int:
    """Price actually paid, or our value estimate when the price wasn't recorded."""
    p = sale.get("price")
    if p is None or (isinstance(p, float) and pd.isna(p)):
        return int(sale.get("value", 0))
    return int(p)


class Draft:
    def __init__(self) -> None:
        # expert.apply() wraps market_value.merged(): our league values joined to
        # Yahoo market price, then tilted by where the expert disagrees with ADP.
        self.players = expert.apply().rename(columns={"key": "nkey"})
        self.players["key"] = self.players["name"].str.lower()
        self.players["watch"] = self.players["name"].map(is_watched)
        self.players["target"] = self.players["name"].map(tier_of)
        self.sales: list[dict] = []
        if STATE.exists():
            prior = pd.read_csv(STATE)
            self.sales = prior.to_dict("records")
            print(f"Resumed draft: {len(self.sales)} picks already recorded.\n")

    # ------------------------------------------------------------- helpers

    def find(self, text: str) -> pd.Series | None:
        t = text.lower().strip()
        exact = self.players[self.players["key"] == t]
        if len(exact):
            return exact.iloc[0]
        hits = self.players[self.players["key"].str.contains(re.escape(t), na=False)]
        if len(hits) == 1:
            return hits.iloc[0]
        if len(hits) > 1:
            watched = hits[hits["watch"]]
            if len(watched) == 1:
                print(f"  ({', '.join(hits['name'].head(5))} -> using watchlist match)")
                return watched.iloc[0]
            print("  ambiguous:", ", ".join(hits["name"].head(6)))
            return None
        # last-name fallback
        hits = self.players[self.players["key"].str.split().str[-1] == t]
        return hits.iloc[0] if len(hits) == 1 else None

    @property
    def drafted(self) -> set[str]:
        return {s["player"].lower() for s in self.sales}

    @property
    def available(self) -> pd.DataFrame:
        return self.players[~self.players["key"].isin(self.drafted)]

    @property
    def my_picks(self) -> list[dict]:
        return [s for s in self.sales if s["team"] == "ME"]

    @property
    def my_spent(self) -> int:
        return sum(_paid(s) for s in self.my_picks)

    @property
    def my_budget(self) -> int:
        return BUDGET - self.my_spent

    @property
    def my_slots_left(self) -> int:
        return ROSTER_SIZE - len(self.my_picks)

    @property
    def max_bid(self) -> int:
        """Most I can spend and still fill every roster spot at $1."""
        return max(0, self.my_budget - (self.my_slots_left - 1))

    def inflation(self) -> float:
        """Ratio of money left to value left. >1 means players go over sticker."""
        money_left = BUDGET * NUM_TEAMS - sum(_paid(s) for s in self.sales)
        slots_left = ROSTER_SIZE * NUM_TEAMS - len(self.sales)
        value_left = self.available.nlargest(max(slots_left, 1), "value")["value"].sum()
        return money_left / value_left if value_left else 1.0

    # -------------------------------------------------------------- actions

    def record(self, name: str, price: int | None, team: str) -> dict | None:
        p = self.find(name)
        if p is None:
            print(f"  ? no match for '{name}'")
            return None
        if p["name"].lower() in self.drafted:
            print(f"  ! {p['name']} is already off the board")
            return None
        sale = {"player": p["name"], "position": p["position"],
                "price": price, "value": int(p["value"]), "team": team.upper()}
        self.sales.append(sale)
        pd.DataFrame(self.sales).to_csv(STATE, index=False)
        if price is None:
            print(f"  {p['name']} -> {team.upper()} (price unknown, est ${p['value']})")
            return sale
        delta = price - p["value"]
        verdict = "BARGAIN" if delta <= -8 else "overpay" if delta >= 8 else "fair"
        who = "YOU" if team.upper() == "ME" else team.upper()
        print(f"  {p['name']} -> {who} ${price} (value ${p['value']}, {delta:+d} {verdict})")
        if team.upper() == "ME":
            print(f"  budget ${self.my_budget} | {self.my_slots_left} slots | max bid ${self.max_bid}")
        return sale

    def undo(self) -> dict | None:
        if not self.sales:
            print("  nothing to undo")
            return None
        s = self.sales.pop()
        pd.DataFrame(self.sales).to_csv(STATE, index=False)
        print(f"  removed {s['player']} (${s['price']} to {s['team']})")
        return s

    def best(self, pos: str | None = None, n: int = 15) -> None:
        df = self.available
        if pos:
            df = df[df["position"] == pos.upper()]
        infl = self.inflation()
        print(f"\n  inflation {infl:.2f}x | your budget ${self.my_budget}, max bid ${self.max_bid}\n")
        print(f"  {'player':24} {'pos':6} {'proj':>7} {'$val':>5} {'$adj':>5} {'ADP':>6}")
        for r in df.head(n).itertuples():
            adj = round(r.value * infl)
            adp = f"{r.adp:.0f}" if pd.notna(r.adp) else "-"
            flag = "  <<" if adj > self.max_bid else ""
            disp = ("*" if r.watch else " ") + r.name
            print(f"  {disp[:23]:24} {r.position + str(r.pos_rank):6} "
                  f"{r.proj_points:>7.1f} {r.value:>5} {adj:>5} {adp:>6}{flag}")

    def watch(self, pos: str | None = None) -> None:
        """Your watchlist, still available, ranked by value."""
        df = self.available[self.available["watch"]]
        if pos:
            df = df[df["position"] == pos.upper()]
        infl = self.inflation()
        gone = [s["player"] for s in self.sales if is_watched(s["player"])]
        print(f"\n  YOUR WATCHLIST | inflation {infl:.2f}x | budget ${self.my_budget}\n")
        print(f"  {'player':24} {'pos':6} {'proj':>7} {'$val':>5} {'$adj':>5} {'ADP':>6}")
        for r in df.itertuples():
            adj = round(r.value * infl)
            adp = f"{r.adp:.0f}" if pd.notna(r.adp) else "-"
            flag = "  <<" if adj > self.max_bid else ""
            note = "  (new team)" if r.name in TEAM_CHANGES else ""
            print(f"  {r.name[:23]:24} {r.position + str(r.pos_rank):6} "
                  f"{r.proj_points:>7.1f} {r.value:>5} {adj:>5} {adp:>6}{flag}{note}")
        print(f"\n  ${df['value'].sum()} of watchlist value still on the board")
        if gone:
            print(f"  gone: {', '.join(gone)}")

    def edge(self, n: int = 20) -> None:
        """Where our custom scoring disagrees most with public ADP."""
        df = self.available[self.available["adp"].notna()].copy()
        if df.empty:
            print("  no ADP data")
            return
        df["adp_rank"] = df["adp"].rank()
        df["our_rank"] = df["value"].rank(ascending=False)
        df["gap"] = df["adp_rank"] - df["our_rank"]
        print(f"\n  UNDERVALUED by the room (we rank them higher):\n")
        print(f"  {'player':24} {'pos':6} {'ours':>5} {'ADP':>6} {'gap':>6} {'$':>5}")
        for r in df.nlargest(n, "gap").itertuples():
            disp = ("*" if r.watch else " ") + r.name
            print(f"  {disp[:23]:24} {r.position + str(r.pos_rank):6} "
                  f"{r.our_rank:>5.0f} {r.adp:>6.1f} {r.gap:>+6.0f} {r.value:>5}")
        print(f"\n  OVERVALUED by the room (let them have these):\n")
        for r in df.nsmallest(8, "gap").itertuples():
            disp = ("*" if r.watch else " ") + r.name
            print(f"  {disp[:23]:24} {r.position + str(r.pos_rank):6} "
                  f"{r.our_rank:>5.0f} {r.adp:>6.1f} {r.gap:>+6.0f} {r.value:>5}")

    def bid(self, name: str) -> None:
        p = self.find(name)
        if p is None:
            print(f"  ? no match for '{name}'")
            return
        infl = self.inflation()
        adj = round(p["value"] * infl)
        walk = min(adj, self.max_bid)
        print(f"\n  {p['name']}  {p['position']}{p['pos_rank']}"
              + ("   * ON YOUR WATCHLIST" if p["watch"] else ""))
        print(f"    projected     {p['proj_points']:.1f} pts ({p['proj_ppg']:.1f}/g)")
        print(f"    VORP          {p['vorp']:.1f}")
        print(f"    sticker       ${p['value']}")
        print(f"    inflation adj ${adj}  ({infl:.2f}x)")
        print(f"    YOUR MAX BID  ${walk}")
        if adj > self.max_bid:
            print(f"    !! costs more than you can afford (${self.max_bid})")
        if pd.notna(p.get("injury_status")):
            print(f"    injury: {p['injury_status']}")
        if p["name"] in TEAM_CHANGES:
            print(f"    NOTE: now on {TEAM_CHANGES[p['name']]} - projection uses prior situation")

    def roster(self) -> None:
        print(f"\n  YOUR ROSTER  (${self.my_spent} spent, ${self.my_budget} left, "
              f"{self.my_slots_left} slots, max bid ${self.max_bid})\n")
        if not self.my_picks:
            print("    empty")
        for s in self.my_picks:
            print(f"    {s['position']:4} {s['player'][:24]:26} ${_paid(s):>3} (val ${s['value']})")
        have = {}
        for s in self.my_picks:
            have[s["position"]] = have.get(s["position"], 0) + 1
        print(f"\n  counts: " + "  ".join(f"{k}:{v}" for k, v in sorted(have.items())))
        need = [f"{p}({STARTERS[p] - have.get(p, 0)})"
                for p in ("QB", "RB", "WR", "TE", "K", "DEF")
                if have.get(p, 0) < STARTERS.get(p, 0)]
        if need:
            print(f"  still need starters: {' '.join(need)}")

    def teams(self) -> None:
        spend: dict[str, int] = {}
        count: dict[str, int] = {}
        for s in self.sales:
            spend[s["team"]] = spend.get(s["team"], 0) + s["price"]
            count[s["team"]] = count.get(s["team"], 0) + 1
        print(f"\n  {'team':10} {'spent':>6} {'left':>6} {'slots':>6} {'max':>5}")
        for t in sorted(spend, key=lambda x: -(BUDGET - spend[x])):
            left = BUDGET - spend[t]
            slots = ROSTER_SIZE - count[t]
            print(f"  {t:10} {spend[t]:>6} {left:>6} {slots:>6} {max(0, left - slots + 1):>5}")
        print(f"\n  inflation: {self.inflation():.2f}x")


# ------------------------------------------------------------------- REPL

PRICE = re.compile(r"\$?(\d+)")


def main() -> None:
    d = Draft()
    print(__doc__)
    print(f"  {len(d.players)} players loaded | ${BUDGET} cap | {NUM_TEAMS} teams "
          f"| {ROSTER_SIZE} roster spots\n")

    while True:
        try:
            line = input("draft> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        parts = line.split()
        cmd = parts[0].lower()

        if cmd in ("quit", "exit", "q"):
            break
        elif cmd == "best":
            pos = next((p for p in parts[1:] if not p.isdigit()), None)
            n = next((int(p) for p in parts[1:] if p.isdigit()), 15)
            d.best(pos, n)
        elif cmd == "edge":
            d.edge(int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 20)
        elif cmd in ("watch", "w"):
            d.watch(parts[1] if len(parts) > 1 else None)
        elif cmd == "bid":
            d.bid(" ".join(parts[1:]))
        elif cmd == "roster":
            d.roster()
        elif cmd == "teams":
            d.teams()
        elif cmd == "undo":
            d.undo()
        elif cmd == "me":
            m = PRICE.search(line)
            if not m:
                print("  usage: me <player> $<price>")
                continue
            name = line[2:m.start()].strip()
            d.record(name, int(m.group(1)), "ME")
        else:
            m = PRICE.search(line)
            if not m:
                print("  ? try:  <player> $<price> <team>   or  help")
                continue
            name = line[:m.start()].strip()
            team = line[m.end():].strip() or "OTHER"
            d.record(name, int(m.group(1)), team)


if __name__ == "__main__":
    main()
