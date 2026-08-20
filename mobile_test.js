/* Phone-viewport smoke test for the draft board.

    node mobile_test.js [url]

Drives the real page in Edge at iPhone size, then reports anything that
overflows the viewport and walks the three bottom-nav views.
*/

const puppeteer = require('puppeteer-core');

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const URL = process.argv[2] || 'http://localhost:5055/index.html';
const W = 390, H = 844;

(async () => {
  const browser = await puppeteer.launch({
    executablePath: EDGE, headless: 'new',
    args: ['--disable-gpu', '--no-sandbox'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: W, height: H, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  await page.goto(URL, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 900));

  const doc = await page.evaluate(W => {
    const out = { scrollWidth: document.documentElement.scrollWidth, offenders: [] };
    for (const el of document.querySelectorAll('body *')) {
      const r = el.getBoundingClientRect();
      if (r.width === 0) continue;
      if (r.right > W + 1) {
        out.offenders.push({
          tag: el.tagName.toLowerCase(),
          id: el.id || null,
          cls: el.className && el.className.toString().slice(0, 40),
          right: Math.round(r.right), width: Math.round(r.width),
          text: (el.textContent || '').trim().slice(0, 26),
        });
      }
    }
    out.offenders = out.offenders.slice(0, 14);
    return out;
  }, W);

  console.log(`viewport ${W}px  |  scrollWidth ${doc.scrollWidth}px  ` +
              (doc.scrollWidth > W ? `<-- OVERFLOW by ${doc.scrollWidth - W}px` : 'no overflow'));
  for (const o of doc.offenders)
    console.log(`   ${o.tag}${o.id ? '#' + o.id : ''}.${o.cls}  right=${o.right} w=${o.width}  "${o.text}"`);

  const shots = process.env.TEMP + '\\ffshots\\';

  // Populate some state so the roster and log panes are not just empty shells.
  await page.evaluate(async () => {
    localStorage.removeItem('bftb14-draft');
    const buy = (player, price, team) => fetch('/api/record', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ player, price, team }),
    });
    await buy('Jahmyr Gibbs', 104, 'ME');
    await buy('Sam LaPorta', 14, 'ME');
    await buy('Brock Purdy', 4, 'ME');
    await buy("Ja'Marr Chase", 91, 'TEAM2');
    await buy('Puka Nacua', 86, 'TEAM3');
    await buy('Bijan Robinson', 97, 'TEAM4');
  });
  await page.reload({ waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 700));

  for (const view of ['players', 'team', 'log']) {
    await page.evaluate(v => {
      document.querySelector(`.nb[data-view="${v}"]`).click();
    }, view);
    await new Promise(r => setTimeout(r, 400));
    await page.screenshot({ path: shots + view + '.png' });
  }
  const badge = await page.evaluate(() =>
    document.getElementById('nav-roster').textContent + '/' + document.getElementById('nav-log').textContent);
  console.log(`nav badges (roster/picks): ${badge}  ${badge === '3/6' ? 'good' : '<-- WRONG, expected 3/6'}`);

  // The whole point of the touch changes: tapping a row must not open a keyboard.
  await page.evaluate(() => document.querySelector('.nb[data-view="players"]').click());
  await new Promise(r => setTimeout(r, 300));
  await page.tap('.row');
  await new Promise(r => setTimeout(r, 500));
  const active = await page.evaluate(() => document.activeElement.id || document.activeElement.tagName);
  console.log(`after tapping a row, focus is on: ${active}  ` +
              (active === 'q' ? '<-- BAD, keyboard would open' : 'good'));

  await browser.close();
})();
