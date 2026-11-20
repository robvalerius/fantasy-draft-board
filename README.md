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

## Sleeper card debts

Open `docs/sleeper/cards.html` on the static site (or serve `docs` locally with
`python -m http.server 5055 --directory docs` and visit
<http://localhost:5055/sleeper/cards.html>). The Sleeper draft boards link to it.
No login, password, API key, or Python data build is needed.

The view reads Sunday Scaries Society's **2026** league directly from Sleeper.
Each starter scoring **0 or less**, including kickers and team defenses, incurs
one card payable to that week's head-to-head opponent. Benched players, empty
slots, byes, and league-median games do not incur cards. Opposite-direction
obligations are not netted. Filters show cards owed or received by team and week;
cards are grouped under the owing manager with listing photos, recipients,
scores, and weeks. When no verified product exists, a labeled player photo or
team logo is shown instead. Unavailable photos show an explicit placeholder.

Football shopping links on Amazon, Etsy, and eBay use the reviewed catalog in
`docs/sleeper/card-products.js`, not generated searches (which returned unrelated
players). Each included product
page was reviewed on November 20, 2026 for the matching player,
availability, and a loading product image. The primary photo and every option's
thumbnail come from the linked listing. Prices are USD item-price snapshots,
sorted low to high among the verified options, not a guarantee of the cheapest
delivered card. Custom/reprint options are labeled, and seller autograph claims
are not independently certified. Missing matches show "no verified matching
card" instead of an unrelated search result or a guessed product/photo.

Repeated editions and repeated listing photos appear only once per obligation,
using the lowest verified item-price snapshot. Shared `cardId` values identify
the same printing/variant even when sellers use different photos or titles;
resized versions of the same CDN photo are also grouped. Different parallels,
custom art, reprints, and signed versions remain separate when their editions
and photos differ. A hidden duplicate is not reported as a missing source.
Shipping and tax can still change which seller has the lowest delivered total.

For defense debts, the catalog selects a current defensive standout: Philadelphia
Eagles - Jalen Carter; Houston Texans - Will Anderson Jr.; Green Bay Packers -
Micah Parsons. These are curated picks, not an automated player ranking.
Both outstanding and purchased entries identify the substitute while retaining
the original D/ST, week, points, opponent, and debt ID, so existing checkmarks
remain valid. Older cards may show the player's former team. New defenses need
an explicitly reviewed mapping and product rather than a guessed substitute.
eBay options are checked Buy It Now single-card listings, not auctions or
pick-your-card variations.

Each current kicker also has a separately labeled Pokemon or Magic name-match
gift option with a matching explanation and listing photo: Trey Smack -
Thwackey; Nick Folk - Nickit; Jason Myers - Jace, Mirror Mage; Will Reichard -
Will, Scion of Peace; Harrison Mevis - Maeve, Insidious Singer (a loose
sound-alike); Cameron Dicker - Mega Camerupt ex; Brandon Aubrey - Brandon.
The Magic options link to reviewed Card Kingdom singles. These are optional
wordplay gifts, not NFL player cards, and never replace the primary NFL photo,
change the debt, or create additional cards owed. They also appear in purchased
entries' card options.

Debts owed **to** Jino / Team Trash Can finish with a Caleb Williams 2025 Score
Trick or Treat Pumpkin card alternative. Debts owed **to** Rob / Bryce's Bench
finish with the Jaguars' Trevor Lawrence Pumpkin card. These recipient picks
are scoped to this league's roster IDs (4 and 3), appear after every other
option in both outstanding and purchased entries, and do not change the
original player, primary photo, debt ID, totals, or purchased status. A card
already offered normally is linked only once, at the end; duplicate editions
still use the cheapest reviewed offer.

The static site cannot read arbitrary marketplace search pages across origins.
It intentionally does not scrape the first result on page load: sponsored,
irrelevant, or unavailable items could be shown. Catalog updates require
revalidating the actual product pages and photos; Sleeper auto-refresh does not
update marketplace prices or stock. Unavailable product photos show an explicit
message rather than silently switching to an unrelated image.

Check **Purchased** on a card to remove it from the owed list and move it into
the **Already purchased** side table (below the ledger on phones). Uncheck it
there to undo. Remaining totals update immediately, and both lists use the same
filters. This status is stored only in this browser's localStorage, scoped to
the league and season; it survives reloads but is not shared across devices or
league members and is lost if site data is cleared. Purchasing does not confirm
delivery. Storage failures are shown explicitly rather than pretending to save.

Only completed weeks through Sleeper's `last_scored_leg` are analyzed; the
current NFL week is conservatively excluded until the following week starts.
Refresh reloads the source scores, including corrections. The open page refreshes automatically
every five minutes while visible and when you return to the tab, without
overlapping requests or clearing purchased checkmarks. Failed refreshes keep the
last report visible with an explicit stale-data warning and retry automatically.
Missing scores produce visible warnings rather than false zeroes; failed/incomplete initial matchup requests
produce an error instead of a partial ledger. Incurred totals come from Sleeper;
remaining totals subtract only cards marked purchased locally. Team/manager labels use current
Sleeper ownership; weekly opponents and starters come from historical matchups.

The page and its scripts live directly in `docs/sleeper` and survive draft-board
rebuilds. Run the focused analysis tests with `npm test` (Node.js, no dependencies).

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
