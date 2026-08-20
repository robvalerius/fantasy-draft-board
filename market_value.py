"""Market auction price (AAV) for Battle for the Belt XIV.

The best market data we have is Yahoo's own "Avg. $" column from the mock
draft room - that is what teams in this exact format actually paid. The mock
runs on Yahoo's default $200 cap while our league uses $269, so every observed
price is scaled by the budget multiple:

    OUR_MULTIPLE = 269 / 200 = 1.345

Observed prices live in data/yahoo_aav.csv and cover roughly the top 135
players. Anyone not in that file falls back to a curve fitted to the same
observations and extended down to the $1 minimum. Observed always wins.

That file also carries Yahoo's injury tag. It matters: a player can look like a
huge bargain purely because the market knows he is hurt and we do not. George
Kittle at $2.7 is not market stupidity, he is on PUP.

To extend: add rows to data/yahoo_aav.csv. No code change needed.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from league_config import BUDGET, NUM_TEAMS, ROSTER_SIZE

DATA = Path(__file__).parent / "data"

YAHOO_BUDGET = 200
OUR_MULTIPLE = BUDGET / YAHOO_BUDGET

# Tags that mean the player is not expected to be available week 1. The market
# has priced this in and our projections have not, so any "edge" is an illusion.
OUT_TAGS = {"PUP-P", "IR", "O", "SUSP", "NFI-R"}

# ---------------------------------------------------------------- observed
# Yahoo "Avg. $" at a $200 cap, read straight from the draft room, in
# data/yahoo_aav.csv. That file is the only real auction market data we have -
# ADP sites publish draft position, not dollars.

# ---------------------------------------------------------------- the curve
# Fallback for anyone with no observed price. Fitted to the observations,
# then extended to the $1 tail. (ADP, dollars at a $200 cap)
CURVE = [
    (1, 74), (5, 62), (10, 54), (15, 48), (20, 42), (25, 36), (30, 31),
    (40, 24), (50, 19), (65, 13), (80, 9), (100, 5), (120, 3), (150, 2),
    (182, 1), (400, 1),
]


def _norm(name: str) -> str:
    return (
        str(name).lower()
        .replace(".", "").replace("'", "").replace("-", " ")
        .replace(" jr", "").replace(" sr", "").replace(" iii", "").replace(" ii", "")
        .strip()
    )


def load_observed() -> pd.DataFrame:
    df = pd.read_csv(DATA / "yahoo_aav.csv")
    df["key"] = df["name"].map(_norm)
    df["status"] = df["status"].fillna("").str.strip()
    df["out"] = df["status"].isin(OUT_TAGS)
    return df.drop_duplicates("key")


_OBS = load_observed()
_OBSERVED = dict(zip(_OBS["key"], _OBS["aav_200"]))
_STATUS = dict(zip(_OBS["key"], _OBS["status"]))
_OUT = set(_OBS.loc[_OBS["out"], "key"])


def curve_price_200(adp: float) -> float:
    """Expected $200-cap price for a given ADP."""
    xs = [c[0] for c in CURVE]
    ys = [c[1] for c in CURVE]
    return float(np.interp(adp, xs, ys))


def _fit_deflation(aav: np.ndarray) -> float:
    """Undo the deflation baked into Yahoo's Avg. $ column.

    Yahoo averages a player's cost over every mock, including the ones where he
    went undrafted at $0. Mocks also get abandoned, and autodraft then fills the
    back half at $1. Elite players are drafted in every mock so their number is
    clean - Gibbs at $73.3 is 36.6% of a $200 team, exactly where real rooms
    clear. The tail is not clean: our top 182 sums to $2,098 when a $200 league
    must spend $2,800.

    So the shape is right and the level is wrong, in a way that grows toward the
    tail. Correcting with

        true = 1 + top^(1-q) * (observed - 1)^q

    keeps the ordering, pins the most expensive player to his observed price,
    and lifts the tail by more than the top. q is solved so the pool balances,
    which means this recalibrates itself as more prices are added.
    """
    x = np.clip(aav - 1.0, 0, None)
    top = float(aav.max())
    slots = ROSTER_SIZE * NUM_TEAMS
    target = YAHOO_BUDGET * NUM_TEAMS

    def total(q: float) -> float:
        return slots + (top ** (1 - q)) * float(np.sum(x ** q))

    lo, hi = 0.05, 1.0
    if total(hi) > target:      # already rich enough, no correction possible
        return 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if total(mid) > target:
            lo = mid
        else:
            hi = mid
    return lo


def _scale_to_our_budget(aav_200: pd.Series) -> pd.Series:
    """Convert a $200-cap price into our $269-cap price.

    A flat x1.345 is wrong. All 182 drafted players cost at least $1 in either
    format, so that floor does not scale - only the money above it does.
    """
    slots = ROSTER_SIZE * NUM_TEAMS
    k = (BUDGET * NUM_TEAMS - slots) / (YAHOO_BUDGET * NUM_TEAMS - slots)
    return 1 + (aav_200 - 1).clip(lower=0) * k


def build() -> pd.DataFrame:
    adp = pd.read_csv(DATA / "adp_half-ppr.csv")
    adp = adp.dropna(subset=["adp"]).sort_values("adp").reset_index(drop=True)
    adp["key"] = adp["name"].map(_norm)

    # Observed players missing from the ADP file still need a row
    missing = _OBS[~_OBS["key"].isin(adp["key"])]
    if len(missing):
        extra = missing[["key", "name", "position"]].copy()
        extra["team"] = ""
        extra["adp"] = np.nan
        adp = pd.concat([adp, extra], ignore_index=True)

    adp["curve_200"] = adp["adp"].map(curve_price_200)
    adp["obs_200"] = adp["key"].map(_OBSERVED)
    adp["source"] = np.where(adp["obs_200"].notna(), "yahoo", "curve")
    adp["raw_200"] = adp["obs_200"].fillna(adp["curve_200"]).fillna(1.0)
    adp["status"] = adp["key"].map(_STATUS).fillna("")
    adp["out"] = adp["key"].isin(_OUT)

    # Calibrate the deflation fix on the players who actually get drafted,
    # then apply it to everyone.
    drafted = adp.dropna(subset=["adp"]).nsmallest(ROSTER_SIZE * NUM_TEAMS, "adp")
    q = _fit_deflation(drafted["raw_200"].to_numpy())
    top = float(drafted["raw_200"].max())
    adp["aav_200"] = 1 + (top ** (1 - q)) * np.clip(adp["raw_200"] - 1, 0, None) ** q

    adp["market"] = _scale_to_our_budget(adp["aav_200"]).round(0).clip(lower=1).astype(int)

    out = adp[["key", "name", "position", "team", "adp", "raw_200", "aav_200",
               "market", "source", "status", "out"]]
    out.to_csv(DATA / "market_values.csv", index=False)
    return out


def merged() -> pd.DataFrame:
    """League value joined to market price, with the gap between them."""
    vals = pd.read_csv(DATA / "auction_values.csv")
    vals["key"] = vals["name"].map(_norm)

    # aav_200 rides along as a reference: it is the price on the $200 scale that
    # every published auction board uses, so it can be compared directly against
    # any list without mentally undoing our $269 budget.
    mkt = build()[["key", "adp", "market", "aav_200", "source", "status", "out"]].drop_duplicates("key")

    df = vals.merge(mkt, on="key", how="left")
    df["has_market"] = df["market"].notna()
    df["market"] = df["market"].fillna(1).astype(int)
    df["mkt_200"] = df["aav_200"].round(0).clip(lower=1).fillna(1).astype(int)
    df["source"] = df["source"].fillna("curve")
    df["status"] = df["status"].fillna("")
    df["out"] = df["out"].fillna(False).astype(bool)
    df["edge"] = df["value"] - df["market"]

    # Two different kinds of uncertainty, previously conflated.
    #
    # "thin" means we have a real but small sample. The projection shrinks a
    # player's own rate toward the positional prior by n/(n+12), so the estimate
    # is already appropriately conservative - showing it is more useful than
    # hiding it. These get a caution marker, not a blackout. This used to be a
    # blackout because the old prior was broken and produced nonsense for young
    # players (Skattebo at $6 against a $33 market); with the prior fixed the
    # numbers are worth reading.
    #
    # "no_opinion" means we genuinely cannot say anything and any edge would be
    # an artifact rather than an insight.
    games = df.get("games_total", pd.Series(99, index=df.index)).fillna(0)
    df["thin"] = games < 28

    no_opinion = games < 6

    # A player the market knows is hurt looks like a screaming bargain to a model
    # that only sees last year's box scores. Kittle at $2.7 is not a market error,
    # he is on PUP.
    no_opinion |= df["out"]

    # No observed price and no ADP means we are guessing at market entirely,
    # so the gap between value and market is meaningless.
    no_opinion |= df["adp"].isna() & (df["source"] != "yahoo")

    df["low_conf"] = no_opinion

    # ------------------------------------------------------------------
    # Defer to the market wherever we have nothing better to say.
    #
    # Our projection measures a per-game scoring rate from past box scores. It
    # is blind to 2026 opportunity - who won a job in camp, who inherited a
    # backfield. The market prices both. So when our evidence is thin, the
    # market price is the better estimate and we should not invent a gap.
    #
    # The deference is deliberately asymmetric, because the evidence is:
    #
    #   A thin sample can show a player is good. It cannot show he is bad.
    #
    # Bhayshul Tuten played 15 games as a backup and scored little. That is
    # absence of evidence, not evidence of absence - Etienne left and Tuten has
    # the job now, which is why the room pays $21. Our $1 was never a read on
    # Tuten, it was a read on his 2025 role. So we take the market.
    #
    # Cam Skattebo also has a thin sample, but he scored 17.7 ppg in it. He
    # proved something in his snaps, so his $42 stands over a $33 market.
    #
    # Net effect: thin players are never marked as traps, because we have no
    # standing to call them one, and their downside is already in the price.
    df["model_value"] = df["value"]
    lift = df["thin"] & (df["market"] > df["value"])
    df.loc[lift, "value"] = df.loc[lift, "market"]

    # Where we have no opinion at all, sit exactly on the market.
    df.loc[no_opinion, "value"] = df.loc[no_opinion, "market"]

    df["edge"] = df["value"] - df["market"]
    df.loc[no_opinion, "edge"] = 0

    # Pinning players to market adds dollars without taking any away, which puts
    # a small upward bias in every edge. Rebalance the players we do have an
    # opinion on so the drafted pool still sums to the real money in the room.
    #
    # There is a genuine bias underneath this, not just bookkeeping: a model
    # built on past box scores gives unproven players almost nothing, then hands
    # their share to established veterans - even though those unproven players
    # will absorb real dollars on draft night. Rebalancing takes that back.
    pinned = (df["thin"] & (df["value"] > df["model_value"])) | no_opinion
    drafted = df.dropna(subset=["adp"]).nsmallest(ROSTER_SIZE * NUM_TEAMS, "adp")
    d_pin = pinned.reindex(drafted.index, fill_value=False)
    free_total = drafted.loc[~d_pin, "value"].sum()
    if free_total > 0:
        factor = (BUDGET * NUM_TEAMS - drafted.loc[d_pin, "value"].sum()) / free_total
        adj = ~pinned
        df.loc[adj, "value"] = (
            np.maximum(1, (1 + (df.loc[adj, "value"] - 1) * factor).round()).astype(int)
        )
        df["edge"] = df["value"] - df["market"]
        df.loc[no_opinion, "edge"] = 0

    return df

if __name__ == "__main__":
    mkt = build()
    print(f"\n=== MARKET CURVE  (Yahoo ${YAHOO_BUDGET} -> our ${BUDGET}, "
          f"x{OUR_MULTIPLE:.3f}) ===")
    print(f"{'adp':>5} {'player':24} {'$200':>6} {'ours':>6}  src")
    for a in (1, 3, 5, 10, 15, 20, 30, 50, 75, 100, 130, 160):
        r = mkt.iloc[a - 1]
        print(f"{r.adp:>5.1f} {r['name'][:23]:24} {r.aav_200:>6.1f} "
              f"{r.market:>6}  {r.source}")

    total = mkt.head(ROSTER_SIZE * NUM_TEAMS)["market"].sum()
    print(f"\nTop {ROSTER_SIZE * NUM_TEAMS} market dollars: ${total:,} "
          f"vs league pool ${BUDGET * NUM_TEAMS:,}")

    df = merged()
    drafted = df[df["value"] > 0]

    print("\n=== BIGGEST BARGAINS (our value > market price) ===")
    print(f"{'player':24} {'pos':6} {'ours':>5} {'mkt':>5} {'edge':>6} {'adp':>6}")
    for r in drafted.nlargest(25, "edge").itertuples():
        print(f"{r.name[:23]:24} {r.position + str(r.pos_rank):6} "
              f"{r.value:>5} {r.market:>5} {r.edge:>+6} {r.adp:>6.0f}")

    print("\n=== BIGGEST TRAPS (market price > our value) ===")
    for r in df.nsmallest(20, "edge").itertuples():
        print(f"{r.name[:23]:24} {r.position + str(r.pos_rank):6} "
              f"{r.value:>5} {r.market:>5} {r.edge:>+6} {r.adp:>6.0f}")
