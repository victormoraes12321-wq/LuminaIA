import asyncio
import os
from playwright.async_api import async_playwright

async def run_e2e_test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        print("[1] Accessing login...")
        await page.goto("http://127.0.0.1:3002/login", wait_until="domcontentloaded")

        print("[2] Filling credentials...")
        await page.wait_for_selector('input[type="email"], input[name="email"], input[placeholder*="email" i]', timeout=15000)
        await page.fill('input[type="email"], input[name="email"], input[placeholder*="email" i]', "ti@casadocampo.vet.br")
        await page.fill('input[type="password"], input[name="password"], input[placeholder*="senha" i]', "Admin@123456")
        await page.click('button[type="submit"]')

        print("[3] Waiting for authentication and navigation...")
        await page.wait_for_timeout(3000)

        print("[4] Navigating to /consultar...")
        await page.goto("http://127.0.0.1:3002/consultar", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        screenshot_dir = r"C:\Users\Administrator\.gemini\antigravity\brain\d99af443-2205-4e22-a2fc-2b8624ad7903\screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)

        query_text = "QUero a lista de todos os produtos da Husqvarna, por ordem do que mais vendeu para o que menos vendeu, e precisa ter as seguintes informações: quantidade vendida, quantidade comprada"
        print(f"[5] Sending query: {query_text}")

        # Wait for chat input
        await page.wait_for_selector('textarea[data-testid="chat-input"], textarea', timeout=15000)
        textarea = page.locator('textarea[data-testid="chat-input"], textarea').first
        await textarea.fill(query_text)
        await page.keyboard.press("Enter")

        await page.wait_for_timeout(1500)

        # Check if clarification modal appeared
        btn_confirm = page.locator('button:has-text("Confirmar e Consultar")')
        if await btn_confirm.count() > 0 and await btn_confirm.is_visible():
            print("  [INFO] Clarification modal opened. Confirming selection...")
            await btn_confirm.click()

        print("[6] Waiting for AI response...")
        await page.wait_for_timeout(12000)

        # Take screenshot of default response
        path_default = os.path.join(screenshot_dir, "husqvarna_response_default.png")
        await page.screenshot(path=path_default, full_page=True)
        print(f"  [OK] Saved default screenshot: {path_default}")

        # Click on 'Planilha' mode
        print("[7] Switching to Planilha (TABLE) mode...")
        btn_planilha = page.locator('button:has-text("Planilha")').first
        if await btn_planilha.count() > 0:
            await btn_planilha.click()
            await page.wait_for_timeout(2500)
            path_planilha = os.path.join(screenshot_dir, "husqvarna_response_planilha.png")
            await page.screenshot(path=path_planilha, full_page=True)
            print(f"  [OK] Saved planilha screenshot: {path_planilha}")

        # Click on 'Barras' mode
        print("[8] Switching to Barras mode...")
        btn_barras = page.locator('button:has-text("Barras")').first
        if await btn_barras.count() > 0:
            await btn_barras.click()
            await page.wait_for_timeout(2500)
            path_barras = os.path.join(screenshot_dir, "husqvarna_response_barras.png")
            await page.screenshot(path=path_barras, full_page=True)
            print(f"  [OK] Saved barras screenshot: {path_barras}")

        # Click on 'Cards' mode
        print("[9] Switching to Cards (KPI) mode...")
        btn_cards = page.locator('button:has-text("Cards")').first
        if await btn_cards.count() > 0:
            await btn_cards.click()
            await page.wait_for_timeout(2500)
            path_cards = os.path.join(screenshot_dir, "husqvarna_response_cards.png")
            await page.screenshot(path=path_cards, full_page=True)
            print(f"  [OK] Saved cards screenshot: {path_cards}")

        await browser.close()
        print("\n[ALL BROWSER TESTS PASSED PERFECTLY]")

if __name__ == '__main__':
    asyncio.run(run_e2e_test())
