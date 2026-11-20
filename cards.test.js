const { test } = require('node:test');
const assert = require('node:assert/strict');
const { analyze, completedThrough, loadReport, readPurchased, writePurchased,
  shoppingOptions, cheapestUniqueListings } = require('./docs/sleeper/cards.js');

const league = {
  league_id: '1384568263651897344', name: 'Test league', season: '2026', status: 'in_season',
  settings: { last_scored_leg: 9, start_week: 1 },
  roster_positions: ['QB', 'K', 'DEF', 'FLEX'],
};
const users = [
  { user_id: 'a', display_name: 'Alice', metadata: { team_name: 'Team A' } },
  { user_id: 'b', display_name: 'Bob' },
];
const rosters = [{ roster_id: 1, owner_id: 'a' }, { roster_id: 2, owner_id: 'b' }];
const players = {
  qb: { full_name: 'Quarterback', position: 'QB' },
  k: { full_name: 'Kicker', position: 'K' },
  DEF: { first_name: 'Team', last_name: 'Defense', position: 'DEF' },
  bench: { full_name: 'Bench Player', position: 'RB' },
};
function fixture() {
  return {
    league, users, rosters, players, weeks: [{ week: 1, matchups: [
      { roster_id: 1, matchup_id: 7, starters: ['qb', 'k', 'DEF', '0'],
        starters_points: [0, -0.01, -2, 0], players_points: { qb: 0, k: -0.01, DEF: -2, bench: -5 } },
      { roster_id: 2, matchup_id: 7, starters: ['qb', 'k'], starters_points: [0, 0.01] },
    ] }],
  };
}

test('zero and negative starters incur one card each, including K and DEF; bench and empty slots do not', () => {
  const report = analyze(fixture());
  assert.equal(report.debts.length, 4);
  assert.deepEqual(report.debts.filter(row => row.from === 1).map(row => row.player).sort(),
    ['Kicker', 'Quarterback', 'Team Defense']);
  assert.ok(report.debts.filter(row => row.from === 1).every(row => row.to === 2));
  assert.equal(report.debts.filter(row => row.from === 2 && row.to === 1).length, 1);
  assert.deepEqual(report.coverage, [{ week: 1, games: 1, byes: 0 }]);
  assert.equal(report.teams.find(team => team.id === 1).name, 'Team A');
  assert.equal(report.teams.find(team => team.id === 2).manager, 'Bob');
});

test('missing scores are not fabricated as zero; player score fallback preserves an actual zero', () => {
  const input = fixture(), lineup = input.weeks[0].matchups[0];
  lineup.starters_points = [null, null, null];
  lineup.players_points = { qb: 0, k: null };
  const report = analyze(input);
  assert.equal(report.debts.filter(row => row.from === 1).length, 1);
  assert.equal(report.warnings.length, 2);
  assert.match(report.warnings[0], /no score/);
});

test('unpaired playoff byes and league-median scoring do not invent card recipients', () => {
  const input = fixture();
  input.weeks[0].matchups[0].matchup_id = null;
  input.weeks[0].matchups[1].matchup_id = 8;
  const report = analyze(input);
  assert.equal(report.debts.length, 0);
  assert.equal(report.coverage[0].byes, 2);
});

test('each week uses its own opponent and repeated players create separate cards', () => {
  const input = fixture();
  input.rosters = [...rosters, { roster_id: 3, owner_id: null }];
  input.weeks[0].matchups.push({ roster_id: 3, matchup_id: null });
  input.weeks.push({ week: 2, matchups: [
    { roster_id: 1, matchup_id: 9, starters: ['qb'], starters_points: [0] },
    { roster_id: 2, matchup_id: null },
    { roster_id: 3, matchup_id: 9, starters: ['k'], starters_points: [5] },
  ] });
  const rows = analyze(input).debts.filter(row => row.from === 1 && row.playerId === 'qb');
  assert.deepEqual(rows.map(row => [row.week, row.to]), [[2, 3], [1, 2]]);
  assert.notEqual(rows[0].id, rows[1].id);
});

test('incomplete weeks, duplicate rosters, and ambiguous matchups fail explicitly', () => {
  const missing = fixture();
  missing.weeks[0].matchups.pop();
  assert.throws(() => analyze(missing), /incomplete matchup/);
  const duplicate = fixture();
  duplicate.weeks[0].matchups[1].roster_id = 1;
  assert.throws(() => analyze(duplicate), /duplicate roster/);
  const ambiguous = fixture();
  ambiguous.rosters = [...rosters, { roster_id: 3 }];
  ambiguous.weeks[0].matchups.push({ roster_id: 3, matchup_id: 7 });
  assert.throws(() => analyze(ambiguous), /two opponents/);
});

test('current week is excluded even when Sleeper has partially scored it', () => {
  const state = { season: '2026', season_type: 'regular', week: 10 };
  assert.equal(completedThrough(league, state), 9);
  assert.equal(completedThrough({ ...league, settings: { last_scored_leg: 10 } }, state), 9);
  assert.equal(completedThrough({ ...league, settings: { last_scored_leg: 8 } }, state), 8);
  assert.equal(completedThrough({ ...league, status: 'pre_draft' }, state), 0);
  assert.equal(completedThrough({ ...league, settings: { last_scored_leg: 17 } },
    { season: '2026', season_type: 'post', week: 1 }), 17);
  assert.equal(completedThrough(league, { season: '2027' }), 9);
  assert.throws(() => completedThrough({ ...league, settings: {} }, state), /last scored/);
});

test('loader fetches every completed week, never current or future weeks, and surfaces HTTP failures', async () => {
  const paths = [];
  const fetcher = async url => {
    const path = url.replace('https://api.sleeper.app/v1/', '');
    paths.push(path);
    let data;
    if (path === `league/${league.league_id}`) data = league;
    else if (path === 'state/nfl') data = { season: '2026', season_type: 'regular', week: 10 };
    else if (path.endsWith('/users')) data = users;
    else if (path.endsWith('/rosters')) data = rosters;
    else if (path === 'players/nfl') data = players;
    else data = fixture().weeks[0].matchups;
    return { ok: true, json: async () => data };
  };
  const report = await loadReport(fetcher);
  assert.deepEqual(report.coverage.map(row => row.week), [1, 2, 3, 4, 5, 6, 7, 8, 9]);
  assert.equal(report.debts.length, 36);
  assert.equal(paths.filter(path => path.includes('/matchups/')).length, 9);
  assert.ok(!paths.some(path => path.endsWith('/10')));
  await assert.rejects(loadReport(async () => ({ ok: false, status: 503 })), /HTTP 503/);
});

test('purchased cards persist by stable obligation ID, can be undone, and stay isolated by league and season', () => {
  const data = new Map(), storage = {
    getItem: key => data.get(key) ?? null,
    setItem: (key, value) => data.set(key, value),
  };
  const rows = analyze(fixture()).debts;
  const id = rows[0].id;
  const purchased = readPurchased(storage, league.league_id, '2026');
  purchased.add(id);
  writePurchased(storage, league.league_id, '2026', purchased);
  const restored = readPurchased(storage, league.league_id, '2026');
  assert.ok(restored.has(id));
  assert.equal(rows.filter(row => !restored.has(row.id)).length, 3);
  assert.equal(rows.filter(row => restored.has(row.id)).length, 1);
  assert.equal(readPurchased(storage, league.league_id, '2027').size, 0);
  assert.equal(readPurchased(storage, 'another-league', '2026').size, 0);
  restored.delete(id);
  writePurchased(storage, league.league_id, '2026', restored);
  assert.equal(readPurchased(storage, league.league_id, '2026').size, 0);
});

test('corrupt or unavailable browser storage is surfaced, not silently reset', () => {
  for (const value of ['invalid json', '{}', '[null]', '["another-league:1:1:qb"]']) {
    assert.throws(() => readPurchased({ getItem: () => value }, league.league_id, '2026'));
  }
  assert.throws(() => readPurchased({ getItem() { throw new Error('Storage blocked'); } },
    league.league_id, '2026'), /Storage blocked/);
  assert.throws(() => writePurchased({ setItem() { throw new Error('Quota exceeded'); } },
    league.league_id, '2026', new Set()), /Quota exceeded/);
});

test('unknown players or mismatched identities never get fabricated or wrong-player shopping links', () => {
  for (const debt of [
    { player: 'Unknown rookie', playerId: 'unknown' },
    { player: 'Odell Beckham Jr.', playerId: '11625' },
    { player: '<script>wrong player</script>', playerId: '4881' },
    { player: 'Marvin Harrison Sr.', playerId: '11628' },
  ]) {
    const options = shoppingOptions(debt);
    assert.deepEqual(options.listings, []);
    assert.deepEqual(options.funListings, []);
    assert.deepEqual(options.unavailable, ['Amazon', 'Etsy', 'eBay']);
    assert.equal(options.searches, undefined, 'do not fall back to unverified search results');
  }
});

test('verified catalog links and photos stay paired with the right player and marketplace', () => {
  const { products } = require('./docs/sleeper/card-products.js');
  const normalize = name => name.replace(/\s+(?:Jr\.?|Sr\.?|III|II)$/i, '')
    .toLowerCase().replace(/[^a-z0-9]/g, '');
  const urls = new Set();
  for (const product of products) {
    const url = new URL(product.url), image = new URL(product.image);
    assert.equal(url.protocol, 'https:');
    assert.equal(image.protocol, 'https:');
    if (product.game) {
      assert.ok(['Pokemon', 'Magic: The Gathering'].includes(product.game));
      assert.ok(product.nameMatch);
      assert.ok(normalize(product.title).includes(normalize(product.cardName)), product.title);
    } else {
      assert.ok(normalize(product.title).includes(normalize(product.player)), product.title);
    }
    assert.ok(Number.isFinite(product.price) && product.price > 0);
    assert.ok(!urls.has(product.url), 'avoid duplicate recommendations');
    urls.add(product.url);
    if (product.marketplace === 'Amazon') {
      assert.equal(url.hostname, 'www.amazon.com');
      assert.match(url.pathname, /\/dp\/[A-Z0-9]{10}$/);
      assert.equal(image.hostname, 'm.media-amazon.com');
    } else if (product.marketplace === 'Etsy') {
      assert.equal(url.hostname, 'www.etsy.com');
      assert.match(url.pathname, /^\/listing\/\d+\//);
      assert.equal(image.hostname, 'i.etsystatic.com');
    } else if (product.marketplace === 'Card Kingdom') {
      assert.ok(product.game, 'Card Kingdom offers are name-match game cards, not NFL recommendations');
      assert.equal(url.hostname, 'www.cardkingdom.com');
      assert.match(url.pathname, /^\/mtg\/[a-z0-9-]+\/[a-z0-9-]+$/);
      assert.equal(image.hostname, 'www.cardkingdom.com');
      assert.match(image.pathname, /^\/images\/magic-the-gathering\/.*\.jpg$/);
    } else {
      assert.equal(product.marketplace, 'eBay');
      assert.equal(url.hostname, 'www.ebay.com');
      assert.match(url.pathname, /^\/itm\/\d+$/);
      assert.equal(image.hostname, 'i.ebayimg.com');
      assert.doesNotMatch(product.title, /\b(pick|choose|minimum|min|lot|packs?|box|digital)\b/i,
        'recommend an individual physical card without minimum-order conditions');
    }
    if (product.playerId === '11628') assert.match(product.title, /harrison\s+jr/i);
  }
});

test('verified options are price ordered, include exact listing images, and do not mutate the catalog', () => {
  const mitchell = shoppingOptions({ player: 'Adonai Mitchell', playerId: '11625', position: 'WR' });
  assert.ok(mitchell.listings.length > 0);
  assert.ok(mitchell.listings.every(listing => /Adonai Mitchell/i.test(listing.title)));
  assert.ok(mitchell.listings.some(listing => listing.marketplace === 'eBay'));
  assert.deepEqual(mitchell.listings.map(listing => listing.price),
    mitchell.listings.map(listing => listing.price).sort((a, b) => a - b));
  const image = mitchell.listings[0].image;
  assert.equal(image, require('./docs/sleeper/card-products.js').products
    .find(product => product.url === mitchell.listings[0].url).image);
  mitchell.listings[0].image = 'not-a-real-image';
  assert.equal(shoppingOptions({ player: 'Adonai Mitchell', playerId: '11625' }).listings[0].image, image);
  const lamar = shoppingOptions({ player: 'Lamar Jackson', playerId: '4881', position: 'QB' });
  assert.ok(lamar.listings.some(listing => listing.marketplace === 'Etsy' && listing.fun));
});

test('defense shopping uses selected standout players without changing debts or existing purchases', () => {
  for (const [playerId, team, player] of [
    ['PHI', 'Philadelphia Eagles', 'Jalen Carter'],
    ['HOU', 'Houston Texans', 'Will Anderson Jr.'],
    ['GB', 'Green Bay Packers', 'Micah Parsons'],
  ]) {
    const input = fixture();
    input.players = { ...input.players, [playerId]: { full_name: team, position: 'DEF' } };
    input.weeks[0].matchups[0].starters[2] = playerId;
    const debt = analyze(input).debts.find(row => row.playerId === playerId);
    const original = { ...debt }, saved = new Map();
    const storage = { getItem: key => saved.get(key), setItem: (key, value) => saved.set(key, value) };
    writePurchased(storage, league.league_id, '2026', new Set([debt.id]));
    const options = shoppingOptions(debt);
    assert.deepEqual(options.substitution, { team, player });
    assert.ok(options.listings.length > 0);
    assert.ok(options.listings.every(listing => listing.player === player));
    assert.deepEqual(new Set(options.listings.map(listing => listing.marketplace)),
      new Set(['Amazon', 'Etsy', 'eBay']));
    assert.deepEqual(options.unavailable, []);
    assert.deepEqual(debt, original, 'shopping cannot change the original team, score, recipient, or ID');
    assert.ok(readPurchased(storage, league.league_id, '2026').has(debt.id));
    assert.equal(debt.id, `${league.league_id}:1:1:${playerId}`);
  }
  const unknown = shoppingOptions({ player: 'Another defense', playerId: 'XXX', position: 'DEF' });
  assert.equal(unknown.substitution, null);
  assert.deepEqual(unknown.listings, [], 'do not guess a star for an unreviewed defense');
});

test('duplicate card editions keep the cheaper offer without hiding distinct cards or claiming a source is missing', () => {
  for (const [playerId, player, position] of [
    ['650', 'Nick Folk', 'K'], ['13276', 'Omar Cooper Jr.', 'WR'],
    ['12481', 'Cam Skattebo', 'RB'], ['13330', 'Kenyon Sadiq', 'TE'],
  ]) {
    const options = shoppingOptions({ playerId, player, position });
    assert.equal(options.hiddenDuplicates, 1);
    assert.ok(!options.listings.some(listing => listing.marketplace === 'Amazon'));
    assert.ok(options.listings.some(listing => listing.marketplace === 'eBay' && listing.price === 0.99));
    assert.ok(!options.unavailable.includes('Amazon'), 'a duplicate is not an unverified source');
  }
});

test('duplicate photo variants and connected card/photo matches choose the cheapest without mutating inputs', () => {
  const products = [
    { playerId: 'k', title: 'First photo', cardId: 'base', price: 4,
      image: 'https://m.media-amazon.com/images/I/example._AC_SL1200_.jpg' },
    { playerId: 'k', title: 'Other photo', price: 1,
      image: 'https://i.ebayimg.com/images/g/example/s-l400.jpg' },
    { playerId: 'k', title: 'Connecting offer', cardId: 'base', price: 5,
      image: 'https://i.ebayimg.com/images/g/example/s-l1600.webp?width=500' },
    { playerId: 'k', title: 'Distinct foil', cardId: 'foil', price: 2,
      image: 'https://i.etsystatic.com/shop/il_1080xN.foil.jpg' },
    { playerId: 'k', title: 'Same foil photo resized', price: 3,
      image: 'https://i.etsystatic.com/shop/il_340x270.foil.jpg' },
    { playerId: 'k', title: 'Same Amazon photo resized', price: 6,
      image: 'https://m.media-amazon.com/images/I/example._AC_UL320_.jpg' },
  ];
  const original = structuredClone(products);
  const chosen = cheapestUniqueListings(products);
  assert.deepEqual(chosen.map(product => [product.title, product.price]),
    [['Other photo', 1], ['Distinct foil', 2]]);
  chosen[0].price = 99;
  assert.deepEqual(products, original);
});

test('kicker game-card name matches are separate optional gifts, never replacement NFL player listings', () => {
  for (const [playerId, player, cardName] of [
    ['13545', 'Trey Smack', 'Thwackey'], ['650', 'Nick Folk', 'Nickit'],
    ['2747', 'Jason Myers', 'Jace, Mirror Mage'], ['11792', 'Will Reichard', 'Will, Scion of Peace'],
    ['12015', 'Harrison Mevis', 'Maeve, Insidious Singer'], ['8259', 'Cameron Dicker', 'Mega Camerupt ex'],
    ['11533', 'Brandon Aubrey', 'Brandon'],
  ]) {
    const debt = { playerId, player, position: 'K' };
    const original = { ...debt };
    const options = shoppingOptions(debt);
    assert.ok(options.listings.length > 0);
    assert.ok(options.listings.every(listing => !listing.game && listing.player === player));
    assert.ok(options.funListings.some(listing => listing.cardName === cardName && listing.nameMatch));
    assert.deepEqual(debt, original);
    assert.deepEqual(shoppingOptions({ ...debt, position: 'WR' }).funListings, []);
    assert.deepEqual(shoppingOptions({ ...debt, player: 'Unrelated kicker' }).funListings, []);
  }
});

test('view auto-refreshes only when visible, prevents overlapping loads, and preserves purchases after retries', async () => {
  const vm = require('node:vm');
  const fs = require('node:fs');
  const elements = new Map(), events = new Map(), requests = [], intervals = [];
  function element() {
    return {
      value: '', hidden: false, options: [], textContent: '', listeners: {},
      append() {},
      replaceChildren(...children) { this.options = children; },
      add(option) { this.options.push(option); },
      addEventListener(name, callback) { this.listeners[name] = callback; },
    };
  }
  const document = {
    hidden: false,
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, element());
      return elements.get(id);
    },
    createElement: element,
    addEventListener(name, callback) { events.set(name, callback); },
  };
  document.getElementById('report').hidden = true;
  const purchases = new Set([`${league.league_id}:1:1:qb`]);
  const context = {
    document, localStorage: {}, console,
    Option: function (text, value) { return { text, value }; },
    SleeperCards: {
      loadReport: () => new Promise((resolve, reject) => requests.push({ resolve, reject })),
      readPurchased: () => new Set(purchases),
    },
    setInterval(callback, milliseconds) { intervals.push({ callback, milliseconds }); },
  };
  const report = { leagueId: league.league_id, league: league.name, season: '2026',
    teams: [], debts: [], coverage: [], warnings: [], fetchedAt: '2026-11-20T16:00:00Z' };
  const flush = () => new Promise(resolve => setImmediate(resolve));
  vm.runInNewContext(fs.readFileSync(require.resolve('./docs/sleeper/cards-view.js'), 'utf8'), context);
  assert.equal(requests.length, 1);
  assert.equal(intervals[0].milliseconds, 300000);
  intervals[0].callback();
  events.get('visibilitychange')();
  assert.equal(requests.length, 1, 'initial load cannot overlap');
  requests[0].resolve(report);
  await flush();
  assert.equal(document.getElementById('report').hidden, false);
  document.hidden = true;
  intervals[0].callback();
  events.get('visibilitychange')();
  assert.equal(requests.length, 1, 'hidden tabs do not poll');
  document.hidden = false;
  events.get('visibilitychange')();
  assert.equal(requests.length, 2, 'returning to the tab refreshes');
  assert.equal(document.getElementById('report').hidden, false, 'keep report during refresh');
  intervals[0].callback();
  assert.equal(requests.length, 2, 'background requests cannot overlap');
  requests[1].reject(new Error('Offline'));
  await flush();
  assert.match(document.getElementById('status').textContent, /last report.*out of date/);
  assert.equal(document.getElementById('report').hidden, false);
  intervals[0].callback();
  assert.equal(requests.length, 3, 'timer retries after a failed request');
  requests[2].resolve(report);
  await flush();
  assert.equal(document.getElementById('status').className, 'muted');
  assert.deepEqual([...purchases], [`${league.league_id}:1:1:qb`]);
  assert.equal(document.getElementById('refresh').disabled, false);
});
