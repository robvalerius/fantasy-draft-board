const { test } = require('node:test');
const assert = require('node:assert/strict');
const { analyze, completedThrough, loadReport } = require('./docs/sleeper/cards.js');

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
