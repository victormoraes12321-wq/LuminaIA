import { chromium } from 'playwright';

async function testLaunch() {
  try {
    const browser = await chromium.launch({ headless: true });
    console.log('Chromium launched successfully!');
    const page = await browser.newPage();
    await page.goto('http://127.0.0.1:3002/healthz');
    const content = await page.content();
    console.log('Page content:', content);
    await browser.close();
  } catch (err) {
    console.error('Launch failed:', err.message);
  }
}

testLaunch();
