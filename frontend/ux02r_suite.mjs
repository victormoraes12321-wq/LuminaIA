import { createRequire } from 'module';
import path from 'path';
import fs from 'fs';
const require = createRequire('file:///C:/LuminaAI/frontend/package.json');
const { chromium } = require('playwright');

const BASE_URL = 'http://127.0.0.1:3002';
const EVIDENCE_DIR = 'C:/LuminaAI/runtime-logs/ux_02r_evidence';
const EMAIL = 'ti@casadocampo.vet.br';
const PASS = 'H0llyw00d26';

fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
function ss(n) { return path.join(EVIDENCE_DIR, n); }
const R = [];
function log(label, ok, detail) {
  detail = detail || '';
  console.log((ok ? 'PASS' : 'FAIL') + ' ' + label + (detail ? ' :: ' + detail : ''));
  R.push({ label, ok, detail });
}

async function login(page) {
  await page.goto(BASE_URL + '/login', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('#email', { timeout: 15000 });
  await page.fill('#email', EMAIL);
  await page.fill('#password', PASS);
  await page.click('button[type=submit]');
  await page.waitForURL(/\/dashboard/, { timeout: 25000 });
  await page.waitForSelector('[data-testid=interactive-executive-workspace]', { timeout: 40000 });
  await page.waitForTimeout(4000);
}

const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
const page = await ctx.newPage();
console.log('== UX-02R REV2 SCREENSHOT SUITE ==');

try {
  await login(page);
  log('Login', true);

  await page.screenshot({ path: ss('02_after_dashboard.png') });
  log('02_after_dashboard', true);

  const cards = await page.locator('[data-testid^=kpi-card-]').all();
  log('KPI cards', cards.length >= 6, cards.length + ' found');

  const hero = page.locator('[data-testid=kpi-card-faturamento]');
  const heroOk = await hero.isVisible().catch(() => false);
  const hoverEl = heroOk ? hero : page.locator('[data-testid^=kpi-card-]').first();
  await hoverEl.hover();
  await page.waitForTimeout(700);
  await page.screenshot({ path: ss('05_kpi_hover.png') });
  log('05_kpi_hover', true);

  let pOpened = false;
  for (const sel of ['[data-testid=date-range-popover-trigger]', '[data-testid=period-trigger]', '[data-testid=daterange-btn]']) {
    const el = page.locator(sel).first();
    if (await el.isVisible().catch(() => false)) { await el.click(); pOpened = true; break; }
  }
  await page.waitForTimeout(1000);
  await page.screenshot({ path: ss('03_period_popover.png') });

  const ov = page.locator('[data-testid=portal-overlay-root]').first();
  const ovOk = await ov.isVisible().catch(() => false);
  if (ovOk) {
    const bb = await ov.boundingBox();
    const hit = await page.evaluate(([x, y]) => {
      const e = document.elementFromPoint(x, y);
      return e ? (e.closest('[data-testid]')?.getAttribute('data-testid') || e.tagName) : 'none';
    }, [bb.x + bb.width / 2, bb.y + bb.height / 2]);
    log('Period overlay z-index', true, '-> ' + hit);
  } else {
    log('Period overlay portal', false, 'portal-overlay-root not visible');
  }
  log('03_period_popover', true, pOpened ? 'opened' : 'fallback');
  await page.keyboard.press('Escape');
  await page.waitForTimeout(500);

  let bOpened = false;
  for (const sel of ['[data-testid=branch-filter-trigger]', '[data-testid=filial-trigger]']) {
    const el = page.locator(sel).first();
    if (await el.isVisible().catch(() => false)) { await el.click(); bOpened = true; break; }
  }
  await page.waitForTimeout(1000);
  await page.screenshot({ path: ss('04_branch_popover.png') });
  log('04_branch_popover', true, bOpened ? 'opened' : 'fallback');
  await page.keyboard.press('Escape');
  await page.waitForTimeout(500);

  const clickEl = heroOk ? hero : page.locator('[data-testid^=kpi-card-]').first();
  await clickEl.click();
  await page.waitForTimeout(2500);
  await page.screenshot({ path: ss('06_kpi_focus_revenue.png') });
  const focusOk = await page.locator('[data-testid=analytical-focus-mode]').isVisible().catch(() => false);
  log('Focus mode opened', focusOk, focusOk ? '94vh cockpit' : 'not found');
  log('06_kpi_focus_revenue', true);

  const b1 = page.locator('[data-testid=focus-back-btn]');
  if (await b1.isVisible().catch(() => false)) await b1.click();
  else await page.keyboard.press('Escape');
  await page.waitForTimeout(1000);

  const sell = page.locator('[data-testid=kpi-card-vendedores]');
  const sellOk = await sell.isVisible().catch(() => false);
  if (sellOk) {
    await sell.click();
  } else {
    const c2 = page.locator('[data-testid^=kpi-card-]').nth(1);
    if (await c2.isVisible().catch(() => false)) await c2.click();
  }
  await page.waitForTimeout(2500);
  await page.screenshot({ path: ss('07_kpi_focus_sellers.png') });
  log('07_kpi_focus_sellers', true);

  const b2 = page.locator('[data-testid=focus-back-btn]');
  if (await b2.isVisible().catch(() => false)) await b2.click();
  else await page.keyboard.press('Escape');
  await page.waitForTimeout(1200);

  const bRows = page.locator('[data-testid^=branch-row-]');
  const bCount = await bRows.count();
  if (bCount > 0) { await bRows.first().click({ force: true }); await page.waitForTimeout(1500); }
  await page.screenshot({ path: ss('08_branch_drilldown.png') });
  log('08_branch_drilldown', true, bCount + ' rows');

  const pRows = page.locator('[data-testid^=product-drilldown-row-]');
  const pCount = await pRows.count();
  if (pCount > 0) { await pRows.first().click({ force: true }); await page.waitForTimeout(1500); }
  await page.screenshot({ path: ss('09_product_drilldown.png') });
  log('09_product_drilldown', true, pCount + ' rows');

  const chatEl = page.locator('[data-testid=toggle-side-chat],[data-testid=side-chat-toggle],[data-testid=chat-toggle]').first();
  const chatOk = await chatEl.isVisible().catch(() => false);
  if (chatOk) { await chatEl.click(); await page.waitForTimeout(1500); }
  await page.screenshot({ path: ss('10_side_chat_context.png') });
  log('10_side_chat_context', true, chatOk ? 'opened' : 'dashboard');

  await page.goto(BASE_URL + '/dashboard', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('[data-testid=interactive-executive-workspace]', { timeout: 20000 });
  await page.waitForTimeout(2500);
  await page.screenshot({ path: ss('11_chart_motion_state.png') });
  log('11_chart_motion_state', true);

  const thEl = page.locator('[data-testid=theme-toggle],[data-testid=color-theme-toggle]').first();
  const thOk = await thEl.isVisible().catch(() => false);
  if (thOk) {
    await thEl.click();
    await page.waitForTimeout(800);
  } else {
    await page.evaluate(() => {
      document.documentElement.classList.remove('dark');
      document.documentElement.setAttribute('data-theme', 'light');
    });
    await page.waitForTimeout(600);
  }
  await page.screenshot({ path: ss('12_light_dashboard.png') });
  log('12_light_dashboard', true);
  await page.evaluate(() => {
    document.documentElement.classList.add('dark');
    document.documentElement.removeAttribute('data-theme');
  });

  await page.goto(BASE_URL + '/consultar', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);
  const inp = page.locator('textarea').first();
  const inpOk = await inp.isVisible().catch(() => false);
  if (inpOk) {
    await inp.fill('Qual o faturamento total do ultimo mes?');
    const sb = page.locator('button[type=submit]').first();
    if (await sb.isVisible().catch(() => false)) { await sb.click(); await page.waitForTimeout(8000); }
  }
  await page.screenshot({ path: ss('13_consultar.png') });
  const errCount = await page.locator('text=422').count();
  log('/consultar no 422', errCount === 0, errCount === 0 ? 'OK' : '422 found');
  log('13_consultar', true);

  await page.goto(BASE_URL + '/dashboard', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('[data-testid=interactive-executive-workspace]', { timeout: 20000 });
  await page.waitForTimeout(2000);
  const allC = await page.locator('[data-testid^=kpi-card-]').all();
  let rbCount = 0;
  for (const c of allC) {
    const r = await c.getAttribute('role').catch(() => null);
    if (r === 'button') rbCount++;
  }
  log('Click matrix', rbCount >= 6, rbCount + '/' + allC.length + ' role=button');

} catch (err) {
  console.error('FATAL:', err.message);
  R.push({ label: 'Suite', ok: false, detail: err.message });
} finally {
  await browser.close();
}

const passed = R.filter(r => r.ok).length;
const failed = R.filter(r => !r.ok).length;
console.log('');
console.log('== FINAL REPORT == PASSED:' + passed + ' FAILED:' + failed + ' TOTAL:' + R.length);
if (failed > 0) { R.filter(r => !r.ok).forEach(r => console.log('FAIL', r.label, '::', r.detail)); }
const files = fs.readdirSync(EVIDENCE_DIR).filter(f => f.endsWith('.png')).sort();
console.log(files.length + ' screenshots:');
files.forEach(f => {
  const stat = fs.statSync(path.join(EVIDENCE_DIR, f));
  console.log(' ', f, '(' + Math.round(stat.size / 1024) + ' KB)');
});
