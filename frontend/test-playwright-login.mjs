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

async function runTest() {
  console.log('Launching browser...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 }
  });
  const page = await context.newPage();

  // Listen to console logs and errors
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log(`[BROWSER CONSOLE ERROR] ${msg.text()}`);
    }
  });

  page.on('pageerror', err => {
    console.log(`[BROWSER PAGE ERROR] ${err.message}`);
  });

  console.log('Navigating to http://127.0.0.1:3002/login...');
  await page.goto('http://127.0.0.1:3002/login', { waitUntil: 'domcontentloaded' });

  console.log('Filling credentials...');
  await page.fill('#email', adminEmail);
  await page.fill('#password', adminPassword);
  await page.click('button[type="submit"]');

  console.log('Waiting for dashboard navigation...');
  await page.waitForURL('**/dashboard**', { timeout: 15000 });
  console.log('Successfully arrived at dashboard:', page.url());

  // Wait for main chat input
  const chatInput = page.locator('textarea, input[placeholder*="pergunt"], input[placeholder*="Pergunt"]');
  await chatInput.waitFor({ state: 'visible', timeout: 10000 });
  console.log('Chat input is ready!');

  // Take screenshot
  await page.screenshot({ path: 'C:/LuminaAI/runtime-logs/screenshot_dashboard_initial.png' });
  console.log('Saved screenshot_dashboard_initial.png');

  await browser.close();
}

runTest().catch(err => {
  console.error('Test failed:', err);
  process.exit(1);
});
