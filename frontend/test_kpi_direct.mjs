import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

async function testKpis() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });

  await page.goto('http://127.0.0.1:3002/login');
  await page.fill('#email', 'ti@casadocampo.vet.br');
  await page.fill('#password', 'H0llyw00d26');
  await page.click('button[type="submit"]', { force: true });
  await page.waitForURL('**/dashboard**');

  await page.waitForSelector('[data-testid="interactive-executive-workspace"]');

  const cards = ['faturamento', 'quantidade', 'vendedores', 'clientes'];
  for (const m of cards) {
    const el = page.locator(`[data-testid="kpi-card-${m}"]`).first();
    console.log(`Checking ${m}: visible =`, await el.isVisible());
    await el.evaluate(b => b.click());
    console.log(`Clicked ${m}`);
    await page.waitForTimeout(100);
  }

  await page.screenshot({ path: 'C:/LuminaAI/runtime-logs/test_kpis.png' });
  console.log('Saved test_kpis.png');
  await browser.close();
}

testKpis().catch(console.error);
