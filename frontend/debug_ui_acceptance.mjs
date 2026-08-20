import { chromium } from 'playwright';

async function debug() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  page.on('console', msg => console.log(`[CONSOLE ${msg.type().toUpperCase()}]`, msg.text()));
  page.on('pageerror', err => console.log('[PAGE ERROR]', err.message));
  page.on('request', req => console.log('[REQUEST]', req.method(), req.url()));

  await page.goto('http://127.0.0.1:3002/login');
  await page.fill('#email', 'ti@casadocampo.vet.br');
  await page.fill('#password', 'H0llyw00d26');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/dashboard**');
  await page.waitForTimeout(4000);

  await browser.close();
}

debug();
