import { chromium } from 'playwright';

async function testFocusMode() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  page.on('console', msg => console.log('LOG:', msg.type(), msg.text()));
  page.on('pageerror', err => console.log('PAGE ERROR:', err.message));

  await page.goto('http://127.0.0.1:3002/login');
  await page.fill('#email', 'ti@casadocampo.vet.br');
  await page.fill('#password', 'H0llyw00d26');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/dashboard**');
  await page.waitForSelector('[data-testid="seller-item-1"]', { timeout: 15000 });
  await page.waitForTimeout(500);

  const focusButtons = [
    'fullscreen-evolution',
    'fullscreen-branch-performance',
    'fullscreen-top-sellers',
    'fullscreen-top-products',
    'fullscreen-top-clients',
  ];

  for (const btnId of focusButtons) {
    const btn = page.locator(`[data-testid="${btnId}"]`).first();
    console.log(`Checking ${btnId}: count=${await btn.count()}, visible=${await btn.isVisible()}`);
    await btn.click({ force: true });
    await page.waitForTimeout(400);

    const modal = page.locator('[data-testid="analytical-focus-mode"]').first();
    console.log(`  Modal after click ${btnId}: count=${await modal.count()}, visible=${await modal.isVisible()}`);

    const closeBtn = page.locator('[data-testid="close-focus-mode"]').first();
    if (await closeBtn.isVisible()) {
      await closeBtn.click({ force: true });
      await page.waitForTimeout(200);
    }
  }

  await browser.close();
}

testFocusMode();
