'use strict';

(function () {
  const $ = id => document.getElementById(id);
  let report;
  const node = (tag, text, className) => {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (className) element.className = className;
    return element;
  };
  const plural = count => count === 1 ? 'card' : 'cards';
  const teamName = id => report.teams.find(team => team.id === id).name;

  function playerPhoto(debt) {
    const frame = node('span', undefined, 'photo');
    const placeholder = node('span', debt.position, 'photo-placeholder');
    const image = document.createElement('img');
    image.alt = '';
    image.loading = 'lazy';
    image.width = 64;
    image.height = 64;
    image.src = debt.position === 'DEF'
      ? `https://sleepercdn.com/images/team_logos/nfl/${encodeURIComponent(debt.playerId.toLowerCase())}.png`
      : `https://sleepercdn.com/content/nfl/players/${encodeURIComponent(debt.playerId)}.jpg`;
    image.addEventListener('error', () => {
      image.remove();
      placeholder.textContent = `${debt.position} / no photo`;
    }, { once: true });
    frame.append(placeholder, image);
    return frame;
  }

  function renderLedger() {
    const team = $('team').value, week = $('week').value, direction = $('direction').value;
    const debts = report.debts.filter(debt =>
      (!week || String(debt.week) === week) && (!team ||
        (direction !== 'receives' && String(debt.from) === team) ||
        (direction !== 'owes' && String(debt.to) === team)));
    $('count').textContent = `${debts.length} ${plural(debts.length)} in this view`;
    $('ledger').replaceChildren();
    const managers = new Map();
    for (const debt of debts) {
      if (!managers.has(debt.from)) managers.set(debt.from, []);
      managers.get(debt.from).push(debt);
    }
    for (const rows of [...managers.values()].sort((a, b) =>
      b.length - a.length || teamName(a[0].from).localeCompare(teamName(b[0].from)))) {
      const group = node('details', undefined, 'debt');
      group.open = true;
      const owner = report.teams.find(team => team.id === rows[0].from);
      const summary = node('summary');
      summary.append(node('strong', owner.name),
        document.createTextNode(` owes ${rows.length} ${plural(rows.length)}`),
        node('small', `Manager: ${owner.manager}`));
      const items = node('ul', undefined, 'items');
      for (const debt of rows) {
        const item = node('li');
        const player = node('div', undefined, 'card-info');
        player.append(node('strong', debt.player),
          node('small', `Week ${debt.week} / ${debt.position} / 1 card`),
          node('div', `Deliver to ${teamName(debt.to)}`, 'recipient'),
          node('span', `${debt.points} pts`, 'points'));
        item.append(playerPhoto(debt), player);
        items.append(item);
      }
      group.append(summary, items);
      $('ledger').append(group);
    }
    if (!debts.length) $('ledger').append(node('p', report.warnings.length
      ? 'No confirmed cards match these filters. Review the data warnings above.'
      : 'No cards owed for these filters.', 'muted'));
  }

  function render() {
    const oldTeam = $('team').value, oldWeek = $('week').value;
    $('team').replaceChildren(new Option('All teams', ''));
    for (const team of report.teams) {
      $('team').add(new Option(`${team.name} (${team.manager})`, String(team.id)));
    }
    $('week').replaceChildren(new Option('All completed weeks', ''));
    for (const { week } of report.coverage) $('week').add(new Option(`Week ${week}`, String(week)));
    if ([...$('team').options].some(option => option.value === oldTeam)) $('team').value = oldTeam;
    if ([...$('week').options].some(option => option.value === oldWeek)) $('week').value = oldWeek;
    $('total').textContent = report.debts.length;
    $('owing').textContent = new Set(report.debts.map(debt => debt.from)).size;
    $('games').textContent = report.coverage.reduce((sum, row) => sum + row.games, 0);
    $('warnings').replaceChildren();
    if (report.warnings.length) {
      $('warnings').append(node('strong', 'Incomplete data: totals below include confirmed cards only.'));
      for (const warning of report.warnings) $('warnings').append(node('p', warning));
    }
    $('teams').replaceChildren();
    const totals = report.teams.map(team => ({
      ...team, owes: report.debts.filter(debt => debt.from === team.id).length,
      receives: report.debts.filter(debt => debt.to === team.id).length,
    })).sort((a, b) => b.owes - a.owes || a.name.localeCompare(b.name));
    for (const team of totals) {
      const row = node('tr'), name = node('td', team.name);
      name.append(node('small', team.manager));
      row.append(name, node('td', team.owes), node('td', team.receives));
      $('teams').append(row);
    }
    $('coverage').textContent = report.coverage.map(row =>
      `Week ${row.week}: ${row.games} matchups${row.byes ? `, ${row.byes} byes` : ''}`).join(' / ') ||
      'No completed weeks yet.';
    renderLedger();
    $('report').hidden = false;
  }

  async function refresh() {
    $('refresh').disabled = true;
    $('report').hidden = true;
    $('status').className = 'muted';
    $('status').textContent = 'Loading completed matchups from Sleeper...';
    try {
      report = await SleeperCards.loadReport();
      render();
      const range = report.coverage.length
        ? `Weeks ${report.coverage[0].week}-${report.through} analyzed.`
        : 'No completed weeks available.';
      $('status').textContent = `${report.league} / ${report.season}. ${range} Updated ${new Date(report.fetchedAt).toLocaleString()}.`;
    } catch (error) {
      $('status').className = 'error';
      $('status').textContent = `Unable to load card debts: ${error.message} No current report is shown. Try Refresh from Sleeper.`;
    } finally {
      $('refresh').disabled = false;
    }
  }

  for (const id of ['team', 'direction', 'week']) $(id).addEventListener('change', renderLedger);
  $('refresh').addEventListener('click', refresh);
  refresh();
})();
