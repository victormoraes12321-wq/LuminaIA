import { chromium } from 'playwright';
import { execFile } from 'child_process';

async function runSqlBridge(sqlQuery) {
  return new Promise((resolve) => {
    const pythonExe = 'C:/LuminaAI/backend/.venv/Scripts/python.exe';
    const bridgeScript = 'C:/LuminaAI/scripts/sql_truth_bridge.py';
    const child = execFile(pythonExe, [bridgeScript], { cwd: 'C:/LuminaAI' }, (err, stdout) => {
      if (err) {
        resolve({ success: false, error: err.message, rows: [] });
      } else {
        try {
          resolve(JSON.parse(stdout.trim()));
        } catch (parseErr) {
          resolve({ success: false, error: stdout, rows: [] });
        }
      }
    });
    child.stdin.write(sqlQuery);
    child.stdin.end();
  });
}

async function debug() {
  const sellerSql = await runSqlBridge("SELECT nome_ FROM vw_vendas_lm GROUP BY nome_ ORDER BY SUM(ptotal_) DESC LIMIT 10;");
  console.log("SQL Top Sellers:", sellerSql.rows);

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto('http://127.0.0.1:3002/login');
  await page.fill('#email', 'ti@casadocampo.vet.br');
  await page.fill('#password', 'H0llyw00d26');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/dashboard**');
  await page.waitForSelector('[data-testid="widget-top-sellers"]');
  await page.waitForTimeout(1000);

  const sellerText = await page.locator('[data-testid="widget-top-sellers"]').innerText();
  console.log("UI Top Sellers Text:\n", sellerText);

  const focusEvolution = page.locator('[data-testid="fullscreen-evolution"]').first();
  console.log("Fullscreen Evolution count:", await focusEvolution.count(), "visible:", await focusEvolution.isVisible());

  await focusEvolution.click({ force: true });
  await page.waitForTimeout(500);

  const focusModal = page.locator('[data-testid="analytical-focus-mode"]').first();
  console.log("Focus Modal visible after click:", await focusModal.isVisible());

  const sideChatInput = page.locator('[data-testid="side-chat-input"]').first();
  console.log("Side chat input count:", await sideChatInput.count(), "visible:", await sideChatInput.isVisible());

  await browser.close();
}

debug();
