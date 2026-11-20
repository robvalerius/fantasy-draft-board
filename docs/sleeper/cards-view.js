'use strict';

(function () {
  const $ = id => document.getElementById(id);
  let report;
  let refreshing = false;
  let purchased = new Set(), purchasesAvailable = false;
  const node = (tag, text, className) => {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (className) element.className = className;
    return element;
  };
  const plural = count => count === 1 ? 'card' : 'cards';
  const teamName = id => report.teams.find(team => team.id === id).name;

  function shoppingLinks(debt) {
    const options = SleeperCards.shoppingOptions(debt);
    const section = node('div', undefined, 'shopping');
    const links = node('div', undefined, 'shopping-links');
    for (const option of options.listings) {
      const link = node('a', undefined, 'product-link');
      link.href = option.url;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.setAttribute('aria-label', `${option.marketplace}: ${option.title} (opens in a new tab)`);
      const photo = document.createElement('img');
      photo.src = option.image;
      photo.alt = option.title;
      photo.loading = 'lazy';
      photo.width = 40;
      photo.height = 56;
      const description = node('span');
      const badge = `${option.fun ? 'Fun pick / ' : ''}${option.marketplace} / $${option.price.toFixed(2)}`;
      description.append(node('strong', badge), node('small', option.title));
      if (/custom|reprint|facsimile|replica/i.test(option.title)) {
        description.append(node('small', 'Custom/reprint: read the listing', 'product-notice'));
      }
      photo.addEventListener('error', () => {
        photo.remove();
        description.append(node('small', 'Listing photo unavailable', 'product-notice'));
      }, { once: true });
      link.append(photo, description);
      links.append(link);
    }
    section.append(links);
    for (const shop of options.unavailable) {
      section.append(node('small', `${shop}: no verified matching card.`, 'muted'));
    }
    return section;
  }

  function purchaseCheckbox(debt, checked) {
    const label = node('label', undefined, 'purchase-toggle');
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = checked;
    checkbox.disabled = !purchasesAvailable;
    checkbox.setAttribute('aria-label',
      `${checked ? 'Mark still owed' : 'Mark purchased'}: ${debt.player}, week ${debt.week}, ${teamName(debt.from)} to ${teamName(debt.to)}`);
    checkbox.addEventListener('change', () => {
      const next = new Set(purchased);
      if (checkbox.checked) next.add(debt.id);
      else next.delete(debt.id);
      try {
        SleeperCards.writePurchased(localStorage, report.leagueId, report.season, next);
      } catch (error) {
        checkbox.checked = checked;
        $('purchase-error').textContent = `Could not save purchased status: ${error.message} Your change was not applied.`;
        return;
      }
      purchased = next;
      $('purchase-error').textContent = '';
      renderTotals();
      renderLedger();
    });
    label.append(checkbox, document.createTextNode('Purchased'));
    return label;
  }

  function playerPhoto(debt) {
    const product = SleeperCards.shoppingOptions(debt).listings[0];
    const figure = node('figure', undefined, 'card-photo');
    const frame = node(product ? 'a' : 'span', undefined, 'photo');
    if (product) {
      frame.href = product.url;
      frame.target = '_blank';
      frame.rel = 'noopener noreferrer';
      frame.setAttribute('aria-label', `View ${product.title} on ${product.marketplace} (opens in a new tab)`);
    }
    const placeholder = node('span', debt.position, 'photo-placeholder');
    const image = document.createElement('img');
    image.alt = product ? product.title : '';
    image.loading = 'lazy';
    image.width = 64;
    image.height = 64;
    image.src = product ? product.image : debt.position === 'DEF'
      ? `https://sleepercdn.com/images/team_logos/nfl/${encodeURIComponent(debt.playerId.toLowerCase())}.png`
      : `https://sleepercdn.com/content/nfl/players/${encodeURIComponent(debt.playerId)}.jpg`;
    image.addEventListener('error', () => {
      image.remove();
      placeholder.textContent = product ? 'Listing photo unavailable' : `${debt.position} / no photo`;
    }, { once: true });
    frame.append(placeholder, image);
    figure.append(frame, node('figcaption', product ? `${product.marketplace} listing photo`
      : `${debt.position === 'DEF' ? 'Team logo' : 'Player photo'} / no verified card`));
    return figure;
  }

  function renderLedger() {
    const team = $('team').value, week = $('week').value, direction = $('direction').value;
    const matching = report.debts.filter(debt =>
      (!week || String(debt.week) === week) && (!team ||
        (direction !== 'receives' && String(debt.from) === team) ||
        (direction !== 'owes' && String(debt.to) === team)));
    const debts = matching.filter(debt => !purchased.has(debt.id));
    const bought = matching.filter(debt => purchased.has(debt.id));
    $('count').textContent = `${debts.length} still owed / ${bought.length} purchased in this view`;
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
        const substitution = SleeperCards.shoppingOptions(debt).substitution;
        if (substitution) {
          player.append(node('small',
            `Defense substitute: buy a ${substitution.player} card (${substitution.team}).`, 'product-notice'));
        }
        player.append(shoppingLinks(debt), purchaseCheckbox(debt, false));
        item.append(playerPhoto(debt), player);
        items.append(item);
      }
      group.append(summary, items);
      $('ledger').append(group);
    }
    if (!debts.length) $('ledger').append(node('p', report.warnings.length
      ? 'No confirmed cards match these filters. Review the data warnings above.'
      : 'No cards still owed for these filters.', 'muted'));
    $('purchased-cards').replaceChildren();
    for (const debt of bought) {
      const row = node('tr');
      const card = node('td', debt.player);
      const substitution = SleeperCards.shoppingOptions(debt).substitution;
      if (substitution) card.append(node('small', `Card: ${substitution.player}`, 'product-notice'));
      const shopping = node('details', undefined, 'purchased-shopping');
      shopping.append(node('summary', 'Card options'), shoppingLinks(debt));
      card.append(node('small', `Week ${debt.week} / ${debt.position}`), shopping);
      const route = node('td', teamName(debt.from));
      route.append(node('small', `For ${teamName(debt.to)}`));
      const action = node('td');
      action.append(purchaseCheckbox(debt, true));
      row.append(card, route, action);
      $('purchased-cards').append(row);
    }
    $('purchased-empty').hidden = bought.length > 0;
    $('purchased-table').hidden = bought.length === 0;
  }

  function renderTotals() {
    const outstanding = report.debts.filter(debt => !purchased.has(debt.id));
    $('total').textContent = outstanding.length;
    $('purchased-total').textContent = report.debts.length - outstanding.length;
    $('owing').textContent = new Set(outstanding.map(debt => debt.from)).size;
    $('incurred').textContent = `${report.debts.length} cards incurred across completed weeks. Purchased status is saved only in this browser, not shared with the league.`;
    $('teams').replaceChildren();
    const totals = report.teams.map(team => ({
      ...team, owes: outstanding.filter(debt => debt.from === team.id).length,
      receives: outstanding.filter(debt => debt.to === team.id).length,
    })).sort((a, b) => b.owes - a.owes || a.name.localeCompare(b.name));
    for (const team of totals) {
      const row = node('tr'), name = node('td', team.name);
      name.append(node('small', team.manager));
      row.append(name, node('td', team.owes), node('td', team.receives));
      $('teams').append(row);
    }
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
    renderTotals();
    $('games').textContent = report.coverage.reduce((sum, row) => sum + row.games, 0);
    $('warnings').replaceChildren();
    if (report.warnings.length) {
      $('warnings').append(node('strong', 'Incomplete data: totals below include confirmed cards only.'));
      for (const warning of report.warnings) $('warnings').append(node('p', warning));
    }
    $('coverage').textContent = report.coverage.map(row =>
      `Week ${row.week}: ${row.games} matchups${row.byes ? `, ${row.byes} byes` : ''}`).join(' / ') ||
      'No completed weeks yet.';
    renderLedger();
    $('report').hidden = false;
  }

  async function refresh() {
    if (refreshing) return;
    refreshing = true;
    $('refresh').disabled = true;
    $('status').className = 'muted';
    $('status').textContent = 'Loading completed matchups from Sleeper...';
    try {
      report = await SleeperCards.loadReport();
      purchasesAvailable = false;
      purchased = new Set();
      $('purchase-error').textContent = '';
      try {
        purchased = SleeperCards.readPurchased(localStorage, report.leagueId, report.season);
        purchasesAvailable = true;
      } catch (error) {
        $('purchase-error').textContent = `Could not read purchased status: ${error.message} Checkboxes are disabled; the list below shows all incurred cards. Enable browser storage and refresh.`;
      }
      render();
      const range = report.coverage.length
        ? `Weeks ${report.coverage[0].week}-${report.through} analyzed.`
        : 'No completed weeks available.';
      $('status').textContent = `${report.league} / ${report.season}. ${range} Updated ${new Date(report.fetchedAt).toLocaleString()}.`;
    } catch (error) {
      $('status').className = 'error';
      const previous = report && !$('report').hidden
        ? ` Showing the last report from ${new Date(report.fetchedAt).toLocaleString()}; it may be out of date.`
        : ' No current report is shown.';
      $('status').textContent = `Unable to load card debts: ${error.message}${previous} Automatic refresh will retry, or use Refresh from Sleeper.`;
    } finally {
      refreshing = false;
      $('refresh').disabled = false;
    }
  }

  for (const id of ['team', 'direction', 'week']) $(id).addEventListener('change', renderLedger);
  $('refresh').addEventListener('click', refresh);
  setInterval(() => {
    if (!document.hidden) refresh();
  }, 5 * 60 * 1000);
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) refresh();
  });
  refresh();
})();
