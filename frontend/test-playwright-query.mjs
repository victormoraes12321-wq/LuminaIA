import { chromium } from 'playwright';
import fs from 'fs';

const envContent = fs.readFileSync('C:/LuminaAI/backend/.env', 'utf-8');
const envVars = {};
for (const line of envContent.split('\n')) {
  const match = line.match(/^\s*([\w.-]+)\s*=\s*(.*)?\s*$/);
  if (match) {
    let v = match[2] || '';
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
      v = v.slice(1, -1);
    }
    envVars[match[1]] = v.trim();
  }
}

const adminEmail = envVars.INITIAL_ADMIN_EMAIL || 'ti@casadocampo.vet.br';
const adminPassword = envVars.INITIAL_ADMIN_PASSWORD;

async function runQueryTest() {
  console.log('Launching browser...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log(`[BROWSER ERROR] ${msg.text()}`);
    }
  });

  console.log('Logging in...');
  await page.goto('http://127.0.0.1:3002/login', { waitUntil: 'domcontentloaded' });
  await page.fill('#email', adminEmail);
  await page.fill('#password', adminPassword);
  await page.click('button[type="submit"]');

  await page.waitForURL('**/dashboard**', { timeout: 15000 });
  console.log('Arrived at dashboard.');

  // Find chat input
  const chatInput = page.locator('textarea');
  await chatInput.waitFor({ state: 'visible', timeout: 10000 });

  // Query 1: Faturamento do mês 02/2026
  console.log('Sending query: "Faturamento do mês 02/2026"...');
  await chatInput.fill('Faturamento do mês 02/2026');
  await page.keyboard.press('Enter');

  console.log('Waiting for response...');
  // Wait for assistant response block to appear
  const responseBlock = page.locator('div[class*="rounded-3xl"], div[class*="rounded-2xl"], div:has-text("LuminaAI BI Core")').first();
  await responseBlock.waitFor({ state: 'visible', timeout: 35000 });
  console.log('Response block visible!');

  // Take screenshot
  await page.screenshot({ path: 'C:/LuminaAI/runtime-logs/screenshot_query1_fat022026.png', fullPage: true });
  console.log('Saved screenshot_query1_fat022026.png');

  // Check for rendered chart or table or KPI
  const hasKPI = await page.locator('text=R$').count();
  const hasCanvas = await page.locator('canvas, svg').count();
  const hasTable = await page.locator('table').count();
  console.log(`Elements found -> KPI values: ${hasKPI}, Canvas/SVG: ${hasCanvas}, Table: ${hasTable}`);

  await browser.close();
}

runQueryTest().catch(err => {
  console.error('Test failed:', err);
  process.exit(1);
});
