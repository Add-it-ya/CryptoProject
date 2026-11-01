const { chromium } = require('playwright');
const SHOT = process.env.SHOT_DIR || require('path').join(__dirname, '..', '..', 'report', 'screenshots') + '/';
const URL = process.env.APP_URL || 'http://localhost:5000';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function login(page, u, p) {
  await page.goto(URL + '/login');
  await page.getByRole('button', { name: new RegExp('^' + u) }).click();
  await page.locator('form button.btn.primary').click();
  await page.waitForURL(URL + '/', { timeout: 30000 });
  await sleep(800);
}
async function upload(page, sample, scheme, shareWith) {
  await page.getByRole('button', { name: sample }).click();
  await page.locator(`button.scheme.${scheme === 'base' ? 'base' : 'prop'}`).click();
  for (const u of shareWith) {
    const chip = page.locator('label.chip', { hasText: u });
    if (!(await chip.getAttribute('class')).includes('on')) await chip.click();
  }
  await page.getByRole('button', { name: 'Encrypt & upload' }).click();
  await page.waitForSelector('.alert.inline.green', { timeout: 30000 });
  await sleep(500);
}

(async () => {
  const browser = await chromium.launch();
  const errors = [];
  const ctxA = await browser.newContext({ viewport: { width: 1680, height: 1000 }, deviceScaleFactor: 1 });
  const a = await ctxA.newPage();
  a.on('pageerror', (e) => errors.push('alice pageerror ' + e.message));
  a.on('console', (m) => m.type() === 'error' && errors.push('alice console ' + m.text()));

  await login(a, 'alice', 'Alice@Cloud2026');
  await a.screenshot({ path: SHOT + '01_login_trace.png' });
  await upload(a, 'payment_order.txt', 'base', ['bob']);
  await a.screenshot({ path: SHOT + '02_upload_base.png' });
  await a.getByRole('button', { name: 'Clear' }).click();
  await upload(a, 'payment_order.txt', 'proposed', ['bob']);
  await a.screenshot({ path: SHOT + '03_upload_proposed.png' });
  await upload(a, 'cloud_logo.png', 'base', []);
  await upload(a, 'salary_records.csv', 'proposed', ['bob', 'charlie']);
  await upload(a, 'salary_records.csv', 'base', ['bob']);

  // open proposed file
  await a.getByRole('button', { name: 'Clear' }).click();
  const rows = a.locator('table.tbl tbody tr');
  const n = await rows.count();
  for (let i = 0; i < n; i++) {
    const t = await rows.nth(i).innerText();
    if (t.includes('payment_order.txt') && t.includes('PROPOSED')) {
      await rows.nth(i).getByRole('button', { name: 'Open' }).click();
      break;
    }
  }
  await a.waitForSelector('.modal', { timeout: 20000 });
  await sleep(600);
  await a.screenshot({ path: SHOT + '04_open_proposed.png' });
  await a.locator('.modal-head button').click();

  // attack lab
  await a.getByRole('link', { name: 'Attack Lab' }).click();
  await sleep(1500);
  // choose payment order files
  const selBase = a.locator('select').nth(0);
  const selProp = a.locator('select').nth(1);
  const pick = async (sel, text) => {
    const opts = await sel.locator('option').allInnerTexts();
    const idx = opts.findIndex((o) => o.includes(text));
    const val = await sel.locator('option').nth(idx).getAttribute('value');
    await sel.selectOption(val);
  };
  await pick(selBase, 'payment_order.txt');
  await pick(selProp, 'payment_order.txt');
  await a.getByRole('button', { name: 'Clear' }).click();
  await a.getByRole('button', { name: 'Attack the BASE file' }).click();
  await sleep(1200);
  await a.getByRole('button', { name: 'Attack the PROPOSED file' }).click();
  await sleep(1500);
  await a.screenshot({ path: SHOT + '05_attack1_public_key.png' });

  await a.getByRole('button', { name: 'Clear' }).click();
  await a.getByRole('button', { name: 'Tamper BASE file' }).click();
  await sleep(800);
  await a.getByRole('button', { name: 'Open as me' }).nth(0).click();
  await sleep(1200);
  await a.getByRole('button', { name: 'Tamper PROPOSED file' }).click();
  await sleep(800);
  await a.getByRole('button', { name: 'Open as me' }).nth(1).click();
  await sleep(1500);
  await a.locator('.card.attack').nth(1).scrollIntoViewIfNeeded();
  await a.screenshot({ path: SHOT + '06_attack2_tamper.png' });

  await a.getByRole('button', { name: 'Clear' }).click();
  await a.getByRole('button', { name: 'Run with sample logo' }).click();
  await sleep(2500);
  await a.locator('.ecb-grid').scrollIntoViewIfNeeded();
  await a.screenshot({ path: SHOT + '07_attack3_ecb.png' });
  await a.locator('.ecb-grid').screenshot({ path: SHOT + '07b_ecb_grid.png' });
  await a.getByRole('button', { name: 'Restore originals' }).click();
  await sleep(500);

  // cloud view
  await a.getByRole('link', { name: 'What the Cloud Sees' }).click();
  await sleep(2000);
  await a.screenshot({ path: SHOT + '08_cloud_view.png' });

  // results
  await a.getByRole('link', { name: 'Results' }).click();
  await sleep(2500);
  await a.screenshot({ path: SHOT + '09_results.png', fullPage: false });

  // bob opens shared file
  const ctxB = await browser.newContext({ viewport: { width: 1680, height: 1000 } });
  const b = await ctxB.newPage();
  b.on('pageerror', (e) => errors.push('bob pageerror ' + e.message));
  await login(b, 'bob', 'Bob@Cloud2026');
  await sleep(1500);
  const brows = b.locator('table.tbl tbody tr');
  const bn = await brows.count();
  let opened = false;
  for (let i = 0; i < bn; i++) {
    const t = await brows.nth(i).innerText();
    if (t.includes('salary_records.csv') && t.includes('PROPOSED')) {
      await brows.nth(i).getByRole('button', { name: 'Open' }).click();
      opened = true;
      break;
    }
  }
  await b.waitForSelector('.modal', { timeout: 20000 });
  await sleep(600);
  await b.screenshot({ path: SHOT + '10_bob_opens_shared.png' });
  await b.locator('.modal-head button').click();

  // alice revokes bob from salary_records (proposed)
  await a.getByRole('link', { name: 'Files' }).click();
  await sleep(1500);
  await a.getByRole('button', { name: 'Clear' }).click();
  const arows = a.locator('table.tbl tbody tr');
  const an = await arows.count();
  for (let i = 0; i < an; i++) {
    const t = await arows.nth(i).innerText();
    if (t.includes('salary_records.csv') && t.includes('PROPOSED')) {
      await arows.nth(i).getByRole('button', { name: 'Share / Revoke' }).click();
      break;
    }
  }
  await a.waitForSelector('.modal');
  const bobRow = a.locator('.share-row', { hasText: 'bob' });
  await bobRow.getByRole('button', { name: 'Revoke' }).click();
  await sleep(2500);
  await a.screenshot({ path: SHOT + '11_revoke_rekey.png' });

  // bob refreshes
  await b.getByRole('button', { name: 'Refresh' }).click();
  await sleep(1500);
  await b.getByRole('button', { name: 'Clear' }).click();
  const brows2 = b.locator('table.tbl tbody tr');
  const bn2 = await brows2.count();
  for (let i = 0; i < bn2; i++) {
    const t = await brows2.nth(i).innerText();
    if (t.includes('revoked')) {
      await brows2.nth(i).getByRole('button', { name: 'Open' }).click();
      break;
    }
  }
  await b.waitForSelector('.modal', { timeout: 20000 });
  await sleep(800);
  await b.screenshot({ path: SHOT + '12_bob_after_revoke.png' });
  console.log('BOB MODAL:', await b.locator('.modal').innerText());

  console.log('opened by bob:', opened);
  console.log('ERRORS:', JSON.stringify(errors, null, 1));
  // print some UI text for verification
  console.log((await a.locator('.inspector').innerText()).slice(0, 1500));
  await browser.close();
})().catch((e) => {
  console.error('E2E FAILED', e);
  process.exit(1);
});
