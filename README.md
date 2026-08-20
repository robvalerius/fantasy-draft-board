# Battle for the Belt XIV — Draft Tooling

Custom draft assistant for Yahoo league 204761. 14 teams, live salary cap auction,
$269 budget, Aug 22 8:00pm EDT.

## Why this exists

Your league's scoring is unusual enough that public rankings and ADP are actively
misleading:

- **Rushing attempts (0.1)** and **first downs (0.25)** reward volume backs heavily
- **Incompletions (−0.25)**, **INT (−3)**, **sacks (−1)** punish inefficient QBs
- **Pass TD 5**, half PPR, 40+ yard play bonuses, yardage milestone bonuses
- Only **3 bench spots** — durability over upside stashes

Everything here scores real NFL stat lines under *your* exact rules.

## Setup

```powershell
.\.venv\Scripts\python.exe fetch_data.py      # download public data (~110 MB)
.\.venv\Scripts\python.exe score_players.py   # score history under league rules
.\.venv\Scripts\python.exe valuation.py       # build auction values
```

## Draft day

Start the board:

```powershell
.\.venv\Scripts\python.exe app.py
```

Open <http://localhost:5000>.

**The fast path:** type a few letters of a name, hit `Enter`. That player is gone.
No price needed — keep up with the room first, worry about detail later.

| Do this | Get this |
|---|---|
| `Enter` | sold to someone else, price unknown |
| `Shift`+`Enter` | **you** won them |
| type `gibbs 45` then `Enter` | sold for $45 |
| `↑` `↓` | move between matches |
| click a row | select it, then use the Sold / Mine buttons |
| `Undo` | reverse the last entry |

Every entry recalculates inflation and re-prices everyone still available, so the
dollar figures always reflect the money actually left in the room.

Position tabs and a ★ Watchlist filter sit above the list. The right rail tracks
your roster, remaining starter needs, recent picks, and every team's budget.

### Terminal version

`draft.py` is the same engine with a keyboard REPL, if you prefer it:

```powershell
.\.venv\Scripts\python.exe draft.py
```

| Command | Does |
|---|---|
| `bijan $54 mike` | record a sale to another team |
| `me bijan $54` | record a player *you* won |
| `best [pos] [n]` | best available by value, inflation-adjusted |
| `edge [n]` | biggest disagreements vs public ADP — your edge |
| `watch [pos]` | your watchlist, still available |
| `bid <player>` | max bid advice for one player |
| `roster` | your roster, budget, remaining needs |
| `teams` | every team's remaining budget and max bid |
| `undo` | undo last sale |

Both interfaces share `data/draft_state.csv`, so you can switch between them
mid-draft. State saves after every entry — a crash loses nothing.

## Files

| File | Purpose |
|---|---|
| `league_config.py` | Exact scoring rules and roster structure |
| `scoring.py` | Stat line → fantasy points |
| `score_players.py` | Score all NFL players 2023–2025 |
| `valuation.py` | Projections → VORP → auction dollars |
| `draft.py` | Live auction assistant (terminal) |
| `app.py` + `templates/` | Draft board web UI |
| `watchlist.py` | Your flagged players — edit this to add/remove |
| `fetch_data.py` | Download public data sources |

## Data sources

All free, no auth: [nflverse](https://github.com/nflverse/nflverse-data) (stats),
[Sleeper](https://docs.sleeper.com) (player DB, injuries),
[FantasyFootballCalculator](https://fantasyfootballcalculator.com) (market ADP).

## Yahoo API

`yahoo_client.py` and `auth.py` are a working OAuth2 client, but Yahoo closed
self-serve Fantasy API access in 2025–26 — new apps get
`additional_authorization_required` on every fantasy endpoint. The code is ready if
access is ever granted via <https://sports.yahoo.com/developer/access/> (App ID
`WIF6oTh9`).

## Method notes

Projections weight 2025 (60%), 2024 (28%), 2023 (12%), regress small samples toward
positional means, and apply a position-specific age curve. Replacement level is
flex-aware for the W/T and W/R/T slots. Dollar values distribute the league's
$3,766 across positive-VORP players, reserving $1 per roster slot.

These are top-heavy by design — with 10 starters and 3 bench spots, stars carry
disproportionate weight.
