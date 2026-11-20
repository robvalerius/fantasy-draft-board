/* Shared by the static view and Node's rule tests. No account or API key. */
(function (root) {
  'use strict';
  const API = 'https://api.sleeper.app/v1';
  const LEAGUE_ID = '1384568263651897344';
  const SEASON = '2026';
  const numeric = value => typeof value === 'number' && Number.isFinite(value);

  function completedThrough(league, state) {
    const last = league.settings?.last_scored_leg;
    if (league.status === 'pre_draft' || league.status === 'drafting') return 0;
    if (!Number.isInteger(last) || last < 0 || last > 18) {
      throw new Error('Sleeper did not provide a valid last scored week.');
    }
    if (String(state.season) < String(league.season)) {
      throw new Error('Sleeper NFL season state is behind this league.');
    }
    if (String(state.season) === String(league.season) &&
        state.season_type === 'regular' && league.status !== 'complete') {
      if (!Number.isInteger(state.week) || state.week < 0 || state.week > 18) {
        throw new Error('Sleeper did not provide a valid current NFL week.');
      }
      return Math.min(last, Math.max(0, state.week - 1));
    }
    return last;
  }

  function analyze({ league, users, rosters, players, weeks }) {
    const userMap = new Map(users.map(user => [user.user_id, user]));
    const teams = rosters.map(roster => {
      const owner = userMap.get(roster.owner_id);
      return {
        id: roster.roster_id,
        name: owner?.metadata?.team_name || owner?.display_name || `Roster ${roster.roster_id}`,
        manager: owner?.display_name || 'Unassigned owner',
      };
    }).sort((a, b) => a.name.localeCompare(b.name) || a.id - b.id);
    const teamMap = new Map(teams.map(team => [team.id, team]));
    const debts = [], warnings = [], coverage = [];
    for (const { week, matchups } of weeks) {
      if (!Array.isArray(matchups) || matchups.length !== rosters.length || !matchups.length) {
        throw new Error(`Week ${week}: incomplete matchup data. No report was produced.`);
      }
      const seen = new Set(), groups = new Map();
      for (const lineup of matchups) {
        if (!teamMap.has(lineup.roster_id) || seen.has(lineup.roster_id)) {
          throw new Error(`Week ${week}: unknown or duplicate roster.`);
        }
        seen.add(lineup.roster_id);
        if (lineup.matchup_id == null) continue;
        const group = groups.get(lineup.matchup_id) || [];
        group.push(lineup);
        groups.set(lineup.matchup_id, group);
      }
      let games = 0, byes = matchups.filter(row => row.matchup_id == null).length;
      for (const [matchupId, group] of groups) {
        if (group.length === 1) { byes++; continue; }
        if (group.length !== 2) {
          throw new Error(`Week ${week}, matchup ${matchupId}: expected two opponents.`);
        }
        games++;
        for (const lineup of group) {
          const opponent = group.find(row => row.roster_id !== lineup.roster_id);
          if (!Array.isArray(lineup.starters)) {
            throw new Error(`Week ${week}, roster ${lineup.roster_id}: missing starting lineup.`);
          }
          const starterIds = new Set();
          lineup.starters.forEach((rawId, index) => {
            const playerId = String(rawId ?? '');
            if (!playerId || playerId === '0') return;
            if (starterIds.has(playerId)) {
              throw new Error(`Week ${week}, roster ${lineup.roster_id}: duplicate starter.`);
            }
            starterIds.add(playerId);
            const aligned = lineup.starters_points?.[index];
            const points = numeric(aligned) ? aligned : lineup.players_points?.[playerId];
            if (!numeric(points)) {
              warnings.push(`Week ${week}: ${teamMap.get(lineup.roster_id).name}, player ${playerId} has no score; excluded, not treated as zero.`);
              return;
            }
            if (points > 0) return;
            const player = players[playerId];
            if (!player) warnings.push(`Player ${playerId} is missing from Sleeper's player directory; verify their name.`);
            debts.push({
              id: `${league.league_id}:${week}:${lineup.roster_id}:${playerId}`,
              week, matchupId, from: lineup.roster_id, to: opponent.roster_id,
              playerId,
              player: player?.full_name ||
                [player?.first_name, player?.last_name].filter(Boolean).join(' ') ||
                `Player ${playerId}`,
              position: player?.position || league.roster_positions?.[index] || '?',
              points,
            });
          });
        }
      }
      coverage.push({ week, games, byes });
    }
    debts.sort((a, b) => b.week - a.week || a.from - b.from || a.player.localeCompare(b.player));
    return { leagueId: league.league_id, league: league.name, season: league.season,
      teams, debts, warnings, coverage };
  }

  async function loadReport(fetchImpl = globalThis.fetch) {
    async function get(path) {
      const response = await fetchImpl(`${API}/${path}`, {
        cache: 'no-store', signal: AbortSignal.timeout(60000),
      });
      if (!response.ok) throw new Error(`Sleeper ${path}: HTTP ${response.status}`);
      const data = await response.json();
      if (data == null) throw new Error(`Sleeper ${path}: no data returned.`);
      return data;
    }
    const [league, state, users, rosters] = await Promise.all([
      get(`league/${LEAGUE_ID}`), get('state/nfl'),
      get(`league/${LEAGUE_ID}/users`), get(`league/${LEAGUE_ID}/rosters`),
    ]);
    if (league.season !== SEASON || String(league.league_id) !== LEAGUE_ID) {
      throw new Error(`Expected the configured ${SEASON} league; Sleeper returned a different league or season.`);
    }
    if (!Array.isArray(users) || !Array.isArray(rosters) || !rosters.length ||
        new Set(rosters.map(row => row.roster_id)).size !== rosters.length) {
      throw new Error('Sleeper returned incomplete league members or rosters.');
    }
    const through = completedThrough(league, state);
    const start = league.settings?.start_week ?? 1;
    if (!Number.isInteger(start) || start < 1 || start > 18) {
      throw new Error('Sleeper did not provide a valid league start week.');
    }
    const weeks = [];
    // Small batches avoid hammering the public API on every page load.
    for (let week = start; week <= through; week += 3) {
      weeks.push(...await Promise.all(
        Array.from({ length: Math.min(3, through - week + 1) }, (_, offset) => week + offset)
          .map(async number => ({
            week: number, matchups: await get(`league/${LEAGUE_ID}/matchups/${number}`),
          }))));
    }
    const players = weeks.length ? await get('players/nfl') : {};
    if (typeof players !== 'object' || Array.isArray(players)) {
      throw new Error('Sleeper returned an invalid player directory.');
    }
    return { ...analyze({ league, users, rosters, players, weeks }), through,
      fetchedAt: new Date().toISOString() };
  }

  function readPurchased(storage, leagueId, season) {
    const raw = storage.getItem(`sleeper-cards:purchased:${leagueId}:${season}`);
    if (raw === null) return new Set();
    const ids = JSON.parse(raw);
    if (!Array.isArray(ids) || !ids.every(id =>
      typeof id === 'string' && id.startsWith(`${leagueId}:`))) {
      throw new Error('Saved purchased-card data is invalid.');
    }
    return new Set(ids);
  }

  function writePurchased(storage, leagueId, season, ids) {
    storage.setItem(`sleeper-cards:purchased:${leagueId}:${season}`, JSON.stringify([...ids]));
  }

  function shoppingOptions(debt) {
    const catalog = typeof module !== 'undefined' && module.exports
      ? require('./card-products.js') : root.SleeperCardProducts;
    if (!catalog) throw new Error('The verified card-product catalog could not be loaded. Reload the page.');
    const normalize = name => name.toLowerCase().replace(/[^a-z0-9]/g, '');
    const substitution = debt.position === 'DEF' && Object.hasOwn(catalog.defensePlayers, debt.playerId)
      ? catalog.defensePlayers[debt.playerId] : null;
    const player = substitution ? substitution.player : debt.player;
    const listings = catalog.products.filter(product =>
      product.playerId === debt.playerId && normalize(product.player) === normalize(player))
      .map(product => ({ ...product }))
      .sort((a, b) => a.price - b.price || a.title.localeCompare(b.title));
    return {
      checkedAt: catalog.checkedAt,
      substitution: substitution ? { ...substitution } : null,
      listings,
      unavailable: ['Amazon', 'Etsy', 'eBay'].filter(shop => !listings.some(product => product.marketplace === shop)),
    };
  }

  const exported = { analyze, completedThrough, loadReport, readPurchased, writePurchased, shoppingOptions };
  if (typeof module !== 'undefined' && module.exports) module.exports = exported;
  else root.SleeperCards = exported;
})(globalThis);
