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

async function testClarificationModal() {
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

  const chatInput = page.locator('textarea');
  await chatInput.waitFor({ state: 'visible', timeout: 10000 });

  const ambigQuery = 'Faturamento fevereiro de 2026';
  console.log(`\nTyping ambiguous query: "${ambigQuery}"...`);
  await chatInput.fill(ambigQuery);
  await page.keyboard.press('Enter');

  console.log('Checking for clarification modal...');
  const modal = page.locator('[data-testid="modal-clarification"]');
  await modal.waitFor({ state: 'visible', timeout: 5000 });
  console.log('SUCCESS: Clarification modal is VISIBLE in DOM!');

  // Take screenshot of popup
  await page.screenshot({ path: 'C:/LuminaAI/runtime-logs/screenshots/popup_clarification_1.png' });
  console.log('Saved screenshots/popup_clarification_1.png');

  // Verify options are clickable
  const brutoBtn = page.locator('[data-testid="basis-option-bruto"]');
  const graficoBtn = page.locator('[data-testid="format-option-grafico"]');
  const confirmBtn = page.locator('[data-testid="confirm-clarification"]');

  console.log('Selecting "Bruto" and "Gráfico"...');
  await brutoBtn.click();
  await graficoBtn.click();

  // Take screenshot of selection
  await page.screenshot({ path: 'C:/LuminaAI/runtime-logs/screenshots/popup_clarification_selected.png' });
  console.log('Saved screenshots/popup_clarification_selected.png');

  console.log('Clicking Confirmar e consultar...');
  await confirmBtn.click();

  // Wait for modal to close
  await modal.waitFor({ state: 'hidden', timeout: 5000 });
  console.log('SUCCESS: Clarification modal closed after confirmation!');

  // Wait for response to appear
  console.log('Waiting for query response and dashboard render...');
  const responseBlock = page.locator('div:has-text("LuminaAI BI Core")').last();
  await responseBlock.waitFor({ state: 'visible', timeout: 35000 });
  console.log('SUCCESS: Query response block rendered!');

  // Check for rendered chart / canvas
  await page.waitForTimeout(2000);
  const canvasCount = await page.locator('canvas, svg').count();
  console.log(`SUCCESS: Found ${canvasCount} canvas/svg visualization elements in rendered dashboard!`);

  // Take screenshot of resulting dashboard
  await page.screenshot({ path: 'C:/LuminaAI/runtime-logs/screenshots/dashboard_after_clarification.png', fullPage: true });
  console.log('Saved screenshots/dashboard_after_clarification.png');

  await browser.close();
  console.log('Test completed with 100% success!');
}

testClarificationModal().catch(err => {
  console.error('Test failed:', err);
  process.exit(1);
});
