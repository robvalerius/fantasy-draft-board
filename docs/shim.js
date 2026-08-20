/* Client-side stand-in for the Flask API.

The static build has no server, so this intercepts window.fetch and answers the
four endpoints from a baked players.json plus draft state in localStorage.
Everything here is a direct port of app.py / draft.py - keep them in sync.
*/

const CAP = DATA.cap, TEAMS = DATA.num_teams, ROSTER = DATA.roster_size;
const STARTERS = DATA.starters, POSITIONS = DATA.positions;
const KEY = 'bftb14-draft';

let sales = JSON.parse(localStorage.getItem(KEY) || '[]');
const save = () => localStorage.setItem(KEY, JSON.stringify(sales));

const paid = s => s.price === null || s.price === undefined ? s.value : s.price;
const drafted = () => new Set(sales.map(s => s.player.toLowerCase()));

function available() {
  const d = drafted();
  return DATA.players.filter(p => !d.has(p.name.toLowerCase()));
}

// app.py bid_range()
function bidRange(adj) {
  if (adj <= 1) return [1, 2];
  if (adj <= 5) return [Math.max(1, adj - 2), adj + 3];
  if (adj <= 20) return [Math.round(adj * 0.70), Math.round(adj * 1.30)];
  if (adj <= 60) return [Math.round(adj * 0.78), Math.round(adj * 1.15)];
  return [Math.round(adj * 0.82), Math.round(adj * 1.02)];
}

const myPicks = () => sales.filter(s => s.team === 'ME');
const mySpent = () => myPicks().reduce((a, s) => a + paid(s), 0);
const myBudget = () => CAP - mySpent();
const mySlots = () => ROSTER - myPicks().length;
const maxBid = () => Math.max(0, myBudget() - (mySlots() - 1));

// draft.py inflation(): money left over value left
function inflation() {
  const moneyLeft = CAP * TEAMS - sales.reduce((a, s) => a + paid(s), 0);
  const slotsLeft = ROSTER * TEAMS - sales.length;
  const pool = available().map(p => p.value).sort((a, b) => b - a);
  const valueLeft = pool.slice(0, Math.max(slotsLeft, 1)).reduce((a, v) => a + v, 0);
  return valueLeft ? moneyLeft / valueLeft : 1.0;
}

function statePayload() {
  const have = {};
  for (const s of myPicks()) have[s.position] = (have[s.position] || 0) + 1;

  const spend = { ME: 0 }, count = { ME: 0 };
  for (const s of sales) {
    spend[s.team] = (spend[s.team] || 0) + paid(s);
    count[s.team] = (count[s.team] || 0) + 1;
  }
  const teams = Object.keys(spend).map(t => {
    const left = CAP - spend[t], slots = ROSTER - count[t];
    return { team: t, spent: spend[t], left, slots, max_bid: Math.max(0, left - slots + 1) };
  }).sort((a, b) => b.left - a.left);

  const needs = {};
  for (const p of POSITIONS) needs[p] = Math.max(0, (STARTERS[p] || 0) - (have[p] || 0));

  return {
    budget: myBudget(), spent: mySpent(), slots_left: mySlots(), max_bid: maxBid(),
    inflation: Math.round(inflation() * 1000) / 1000,
    picks_made: sales.length, picks_total: ROSTER * TEAMS,
    roster: myPicks().map(s => ({ ...s, paid: paid(s) })),
    counts: have, needs, teams,
    recent: sales.slice(-15).reverse().map(s => ({ ...s, paid: paid(s) })),
    cap: CAP,
  };
}

function apiPlayers(qs) {
  const q = (qs.get('q') || '').trim().toLowerCase();
  const pos = (qs.get('pos') || '').trim().toUpperCase();
  const limit = parseInt(qs.get('limit') || '400');
  let df = available();

  if (pos && pos !== 'ALL') df = df.filter(p => p.position === pos);
  if (qs.get('watch') === '1') df = df.filter(p => p.watch);
  if (qs.get('target') === '1') df = df.filter(p => p.target);
  if (q) df = df.filter(p => p.key.includes(q));

  const col = ({ value: 'value', market: 'market', edge: 'edge', adp: 'adp' })[qs.get('sort')] || 'value';
  const asc = col === 'adp';
  // stable sort with nulls last, matching pandas na_position="last"
  df = df.map((p, i) => [p, i]).sort((a, b) => {
    const x = a[0][col], y = b[0][col];
    if (x === null && y === null) return a[1] - b[1];
    if (x === null) return 1;
    if (y === null) return -1;
    return x === y ? a[1] - b[1] : (asc ? x - y : y - x);
  }).map(t => t[0]);

  const infl = inflation(), mb = maxBid();
  const out = df.slice(0, limit).map(p => {
    const adj = Math.round(p.value * infl);
    const [lo, hi] = bidRange(adj);
    return { ...p, adj, min: lo, max: hi, over_budget: hi > mb, affordable: adj <= mb };
  });
  return { players: out, shown: out.length, total: df.length };
}

function apiRecord(body) {
  const name = (body.player || '').toLowerCase();
  const p = DATA.players.find(x => x.name.toLowerCase() === name)
         || DATA.players.find(x => x.key.includes(name));
  if (!p) return [404, { ok: false, error: `no match for '${body.player}'` }];
  if (drafted().has(p.name.toLowerCase()))
    return [409, { ok: false, error: `${p.name} is already off the board` }];

  let price = body.price;
  if (price === null || price === undefined || price === '' || price === '?') price = null;
  else {
    price = parseInt(price);
    if (isNaN(price)) return [400, { ok: false, error: 'price must be a number' }];
    if (price < 1) return [400, { ok: false, error: 'price must be at least $1' }];
  }

  const sale = { player: p.name, position: p.position, price,
                 value: p.value, team: (body.team || 'OTHER').toUpperCase() };
  sales.push(sale); save();

  const delta = price === null ? null : price - sale.value;
  const verdict = delta === null ? 'unknown' : delta <= -8 ? 'bargain' : delta >= 8 ? 'overpay' : 'fair';
  return [200, { ok: true, sale, delta, verdict, state: statePayload() }];
}

const ROUTES = {
  '/api/state': () => [200, statePayload()],
  '/api/players': (qs) => [200, apiPlayers(qs)],
  '/api/edge': () => {
    const df = available().filter(p => !p.low_conf && p.market > 1);
    const by = (a, b) => b.edge - a.edge;
    return [200, {
      under: [...df].sort(by).slice(0, 20),
      over: [...df].sort((a, b) => a.edge - b.edge).slice(0, 12),
      plan: DATA.plan, note: DATA.budget_note,
    }];
  },
};

const realFetch = window.fetch.bind(window);

window.fetch = async (url, opts = {}) => {
  const u = new URL(url, location.href);
  if (!u.pathname.startsWith('/api/')) return realFetch(url, opts);

  const path = u.pathname;
  let status = 200, body;

  if (opts.method === 'POST') {
    const payload = opts.body ? JSON.parse(opts.body) : {};
    if (path === '/api/record') [status, body] = apiRecord(payload);
    else if (path === '/api/undo') {
      const s = sales.pop(); save();
      body = s ? { ok: true, removed: s, state: statePayload() }
               : (status = 400, { ok: false, error: 'nothing to undo' });
    } else if (path === '/api/reset') {
      sales = []; save();
      body = { ok: true, state: statePayload() };
    } else { status = 404; body = { ok: false, error: 'no route' }; }
  } else {
    const h = ROUTES[path];
    if (h) [status, body] = h(u.searchParams);
    else { status = 404; body = { ok: false, error: 'no route' }; }
  }

  return new Response(JSON.stringify(body), {
    status, headers: { 'Content-Type': 'application/json' },
  });
};
