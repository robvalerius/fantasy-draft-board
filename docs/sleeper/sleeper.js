/* Live draft sync for Sleeper leagues.

Sleeper's draft API is public, unauthenticated and sends
`access-control-allow-origin: *`, so this static page can poll it directly.
There is no server and no key.

Design rules, chosen because a live auction is unforgiving:

  - Manual entry stays the primary path. This never takes anything away.
  - Additive only. Sync records picks it finds; it never removes or edits a
    pick, so a wrong guess costs one Undo rather than the whole draft.
  - Off by default. You turn it on, and the choice is remembered.
  - Fails silently and visibly. A network error stops the clock in the
    indicator instead of throwing, and manual entry carries on untouched.
  - Anything it cannot match is counted out loud rather than swallowed, so you
    know to enter those by hand.

Only loaded for non-default leagues; the Yahoo board never sees this file.
*/

(function () {
  const DRAFT_ID = DATA.sleeper_draft_id;
  if (!DRAFT_ID) return;

  const ENDPOINT = `https://api.sleeper.app/v1/draft/${DRAFT_ID}/picks`;
  const PERIOD = 5000;
  const ON_KEY = `ff-sync-on-${DATA.league_slug}`;
  const ME_KEY = `ff-sync-me-${DATA.league_slug}`;

  let on = localStorage.getItem(ON_KEY) === '1';
  let meId = localStorage.getItem(ME_KEY) || '';
  let lastOk = 0, unmatched = 0, applied = 0, failing = false, busy = false;
  // Players this session has already handed to the shim, so a 168-pick draft
  // does not replay 168 records into it every five seconds.
  const done = new Set();

  // Must match _norm() in valuation.py, which is what built player.key.
  const norm = s => String(s).toLowerCase()
    .replace(/\./g, '').replace(/'/g, '').replace(/-/g, ' ')
    .replace(/ jr/g, '').replace(/ sr/g, '')
    .replace(/ iii/g, '').replace(/ ii/g, '')
    .trim();

  const byName = new Map();
  for (const p of DATA.players) byName.set(norm(p.name), p);

  // ---------------------------------------------------------------- UI
  const box = document.createElement('div');
  box.id = 'sleeper-sync';
  box.innerHTML = `
    <style>
      #sleeper-sync{position:fixed;left:8px;bottom:64px;z-index:60;display:flex;
        gap:6px;align-items:center;background:var(--card,#1b1d22);
        border:1px solid var(--line,#333);border-radius:999px;padding:5px 10px;
        font:500 12px/1.2 system-ui,sans-serif;color:var(--muted,#9aa)}
      #sleeper-sync button{all:unset;cursor:pointer;padding:2px 8px;border-radius:999px;
        border:1px solid var(--line,#333);color:inherit}
      #sleeper-sync button.on{background:#1f6f43;border-color:#2c9c5f;color:#fff}
      #sleeper-sync select{background:transparent;color:inherit;border:0;font:inherit;
        max-width:110px}
      #sleeper-sync .bad{color:#e0704f}
    </style>
    <button id="ss-toggle"></button>
    <select id="ss-me" title="Which team is yours? Their picks count as ME.">
      <option value="">who are you?</option>
      ${(DATA.sleeper_users || []).map(u =>
        `<option value="${u.id}">${u.name}</option>`).join('')}
    </select>
    <span id="ss-status"></span>`;
  document.body.appendChild(box);

  const $t = box.querySelector('#ss-toggle');
  const $s = box.querySelector('#ss-status');
  const $me = box.querySelector('#ss-me');
  $me.value = meId;

  $t.onclick = () => {
    on = !on;
    localStorage.setItem(ON_KEY, on ? '1' : '0');
    render();
    if (on) tick();
  };
  $me.onchange = () => {
    meId = $me.value;
    localStorage.setItem(ME_KEY, meId);
  };

  function render() {
    $t.textContent = on ? 'Sync on' : 'Sync off';
    $t.className = on ? 'on' : '';
    if (!on) { $s.textContent = ''; $s.className = ''; return; }
    if (failing) { $s.textContent = 'no connection'; $s.className = 'bad'; return; }
    if (!lastOk) { $s.textContent = 'connecting…'; $s.className = ''; return; }
    const secs = Math.round((Date.now() - lastOk) / 1000);
    $s.className = '';
    $s.textContent = `synced ${secs}s ago`
      + (applied ? ` · ${applied} auto` : '')
      + (unmatched ? ` · ${unmatched} manual` : '');
  }

  // ---------------------------------------------------------------- sync
  async function tick() {
    if (!on || busy) return;
    busy = true;
    try {
      const res = await fetch(ENDPOINT, { cache: 'no-store' });
      if (!res.ok) throw new Error(res.status);
      const picks = await res.json();
      failing = false;
      lastOk = Date.now();
      await apply(Array.isArray(picks) ? picks : []);
    } catch (e) {
      // Never throw out of the poll loop: manual entry has to keep working.
      failing = true;
    } finally {
      busy = false;
      render();
    }
  }

  async function apply(picks) {
    let missed = 0, changed = false;

    for (const pick of picks) {
      const m = pick.metadata || {};
      const full = `${m.first_name || ''} ${m.last_name || ''}`.trim();
      const p = byName.get(norm(full));
      if (!p) { missed++; continue; }
      if (done.has(p.name)) continue;

      const amount = parseInt(m.amount, 10);
      const body = {
        player: p.name,
        price: Number.isFinite(amount) && amount > 0 ? amount : null,
        team: meId && pick.picked_by === meId ? 'ME' : 'OTHER',
      };

      // The shim answers this, and returns 409 for anyone already off the
      // board - which is exactly the dedupe we want, whether the pick came
      // from a previous poll or from Rob typing it in himself.
      const r = await fetch('/api/record', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (r.status === 200) { applied++; changed = true; }
      if (r.status === 200 || r.status === 409) done.add(p.name);
    }

    unmatched = missed;
    // Repaint through the page's own loader so the board and the side panel
    // stay in step with whatever the shim now believes.
    if (changed && typeof window.load === 'function') window.load();
  }

  render();
  setInterval(tick, PERIOD);
  setInterval(render, 1000);
  if (on) tick();
})();
