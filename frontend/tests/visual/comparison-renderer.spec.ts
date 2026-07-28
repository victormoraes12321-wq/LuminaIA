import { expect, test, type Page } from '@playwright/test'
import {
  buildComparisonResponse,
  type ComparisonFixtureScenario,
} from '../fixtures/comparisonResponse'

const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:3100'

function testUser(role: 'ADMIN' | 'GESTOR' | 'CONSULTA') {
  return {
    id: `user-${role.toLowerCase()}`,
    nome: `${role} Lumina`,
    email: `${role.toLowerCase()}@luminaai.demo`,
    role,
    tenant_id: 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    must_change_password: false,
  }
}

async function authenticate(page: Page, role: 'ADMIN' | 'GESTOR' | 'CONSULTA') {
  const user = testUser(role)
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url')
  const payload = Buffer.from(JSON.stringify({
    sub: user.email,
    tenant_id: user.tenant_id,
    role: user.role,
    must_change_password: false,
    exp: Math.floor(Date.now() / 1000) + 3600,
  })).toString('base64url')
  await page.context().addCookies([{
    name: 'lumina-token',
    value: `${header}.${payload}.comparison-test`,
    url: baseURL,
    httpOnly: true,
    sameSite: 'Lax',
  }])
}

async function mockComparisonApi(
  page: Page,
  scenario: ComparisonFixtureScenario,
  role: 'ADMIN' | 'GESTOR' | 'CONSULTA',
) {
  const user = testUser(role)
  await page.route('**/api/v1/**', async route => {
    const url = route.request().url()
    const method = route.request().method()
    if (url.includes('/auth/session')) return route.fulfill({ json: user })
    if (url.includes('/query/history') || url.includes('/query/favorites')) {
      return route.fulfill({ json: [] })
    }
    if (url.endsWith('/api/v1/query/') && method === 'POST') {
      return route.fulfill({ json: buildComparisonResponse(scenario, role) })
    }
    if (url.includes('/dashboard-preferences/default')) {
      return route.fulfill({
        json: { basis: 'liquido', format: 'ambos', instructions: '' },
      })
    }
    return route.fulfill({ json: { ok: true } })
  })
}

async function openComparison(
  page: Page,
  scenario: ComparisonFixtureScenario,
  role: 'ADMIN' | 'GESTOR' | 'CONSULTA' = 'ADMIN',
  theme: 'light' | 'dark' = 'light',
) {
  await page.addInitScript(selectedTheme => {
    window.localStorage.setItem('luminaai-theme', selectedTheme)
    window.localStorage.setItem('lumina-comparison-renderer-v2', 'enabled')
    window.localStorage.setItem('lumina-comparison-renderer-v2-shadow', 'disabled')
  }, theme)
  await mockComparisonApi(page, scenario, role)
  await authenticate(page, role)
  await page.goto('/dashboard')
  const input = page.getByPlaceholder('Faça uma pergunta sobre seus dados...')
  await expect(input).toBeVisible()
  await input.fill('Compare o faturamento do Mes 06/2026 e 07/2026')
  await input.press('Enter')
  await expect(page.getByTestId('comparison-renderer')).toBeVisible({ timeout: 15_000 })
}

async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(() =>
    Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - window.innerWidth,
  )
  expect(overflow).toBeLessThanOrEqual(2)
}

test('period comparison renders backend values, delta, percentage, direction, table and chart', async ({ page }) => {
  await openComparison(page, 'period')
  await expect(page.getByTestId('comparison-operand-card')).toHaveCount(2)
  await expect(page.getByText('R$ 300,00', { exact: true }).first()).toBeVisible()
  await expect(page.getByText('R$ 400,00', { exact: true }).first()).toBeVisible()
  await expect(page.getByText('R$ 100,00', { exact: true }).first()).toBeVisible()
  await expect(page.getByText('33,33%', { exact: true }).first()).toBeVisible()
  await expect(page.getByText('Aumentou').first()).toBeVisible()
  await expect(page.getByTestId('comparison-calculation-direction')).not.toContainText('Sem valor')
  await expect(page.getByTestId('comparison-table')).toBeVisible()
  await expect(page.getByTestId('comparison-chart-bar')).toBeVisible()
})

test('multi-period preserves three operands and renders a temporal line', async ({ page }) => {
  await openComparison(page, 'multi_period')
  await expect(page.getByTestId('comparison-operand-card')).toHaveCount(3)
  await expect(page.getByText('Agosto de 2026').first()).toBeVisible()
  await expect(page.getByTestId('comparison-chart-line')).toBeVisible()
})

test('entity comparison keeps canonical entities and long labels visible', async ({ page }) => {
  await openComparison(page, 'entity')
  await expect(page.getByText('Filial Centro').first()).toBeVisible()
  await expect(page.getByText('Filial Sul com nome empresarial extenso').first()).toBeVisible()
  await expect(page.getByTestId('comparison-chart-bar')).toBeVisible()
})

test('multi-entity comparison preserves every entity in one visual result', async ({ page }) => {
  await openComparison(page, 'multi_entity')
  await expect(page.getByTestId('comparison-operand-card')).toHaveCount(3)
  await expect(page.getByText('Filial Centro').first()).toBeVisible()
  await expect(page.getByText('Filial Sul com nome empresarial extenso').first()).toBeVisible()
  await expect(page.getByText('Filial Norte').first()).toBeVisible()
  await expect(page.getByTestId('comparison-chart-bar')).toBeVisible()
})

test('metric comparison with incompatible units falls back to a table', async ({ page }) => {
  await openComparison(page, 'metric_incompatible')
  await expect(page.getByText('Unidades diferentes exigem visoes separadas.')).toBeVisible()
  await expect(page.getByTestId('comparison-table').first()).toBeVisible()
})

test('actual versus target renders official target without a browser gauge', async ({ page }) => {
  await openComparison(page, 'actual_target')
  const view = page.getByTestId('actual-vs-target')
  await expect(view).toBeVisible()
  await expect(view.getByText('Realizado', { exact: true })).toBeVisible()
  await expect(view.getByText('Meta', { exact: true })).toBeVisible()
  await expect(view.getByText('Nenhum gauge ou atingimento foi calculado no navegador.')).toBeVisible()
})

test('missing target remains absent and never becomes target zero', async ({ page }) => {
  await openComparison(page, 'actual_target_missing')
  const view = page.getByTestId('actual-vs-target')
  await expect(view).toContainText('Sem valor')
  await expect(page.getByTestId('comparison-renderer')).toContainText('Meta oficial ausente para o periodo.')
  await expect(view).not.toContainText('R$ 0,00')
})

test('area chart renders a backend-requested temporal view', async ({ page }) => {
  await openComparison(page, 'area')
  await expect(page.getByTestId('comparison-operand-card')).toHaveCount(3)
  await expect(page.getByTestId('comparison-chart-area')).toBeVisible()
})

test('pie chart renders only with backend share calculations', async ({ page }) => {
  await openComparison(page, 'pie')
  await expect(page.getByTestId('comparison-chart-pie')).toBeVisible()
  await expect(page.getByText('42,86%', { exact: true }).first()).toBeVisible()
  await expect(page.getByText('57,14%', { exact: true }).first()).toBeVisible()
})

test('partial and truncated result is announced before visualizations', async ({ page }) => {
  await openComparison(page, 'partial')
  const banner = page.getByTestId('comparison-state-banner')
  await expect(banner).toContainText('Resultado parcial')
  await expect(banner).toContainText('truncado')
  await expect(page.getByText('Resultado truncado').first()).toBeVisible()
})

test('zero denominator is not rendered as zero percent', async ({ page }) => {
  await openComparison(page, 'zero_denominator')
  await expect(page.getByText('Nao aplicavel: denominador zero.').first()).toBeVisible()
  await expect(page.getByTestId('comparison-renderer')).not.toContainText('Infinity')
  await expect(page.getByTestId('comparison-renderer')).not.toContainText('NaN')
})

test('null and missing buckets have distinct labels', async ({ page }) => {
  await openComparison(page, 'null_missing')
  await expect(page.getByText('Sem valor', { exact: true }).first()).toBeVisible()
  await expect(page.getByText('Sem registro', { exact: true }).first()).toBeVisible()
  await expect(page.getByText(/Sem registro: 1 bucket/)).toBeVisible()
  await expect(page.getByText(/Sem valor: 1 bucket/)).toBeVisible()
})

test('multiple visualizations preserve backend order', async ({ page }) => {
  await openComparison(page, 'multiple_visualizations')
  const titles = page.getByTestId('comparison-visualization').locator(':scope > div:first-child h4')
  await expect(titles).toHaveText([
    'Primeiro: tabela',
    'Segundo: barras',
    'Terceiro: indicadores',
  ])
})

test('ADMIN can inspect permitted validation checks', async ({ page }) => {
  await openComparison(page, 'period', 'ADMIN')
  const panel = page.getByTestId('comparison-validation')
  await panel.getByRole('button').click()
  await expect(panel.getByText('Diferenca assinada conferida.')).toBeVisible()
  await expect(panel.getByText('Isolamento do tenant conferido.')).toBeVisible()
})

test('GESTOR sees summarized provenance without technical metadata', async ({ page }) => {
  await openComparison(page, 'period', 'GESTOR')
  const panel = page.getByTestId('comparison-provenance')
  await panel.getByRole('button').click()
  await expect(panel.getByText('PostgreSQL analitico')).toBeVisible()
  await expect(page.getByTestId('comparison-technical-metadata')).toHaveCount(0)
})

test('CONSULTA does not see provenance or administrative diagnostics', async ({ page }) => {
  await openComparison(page, 'period', 'CONSULTA')
  await expect(page.getByTestId('comparison-provenance')).toHaveCount(0)
  await expect(page.getByTestId('comparison-technical-metadata')).toHaveCount(0)
  await expect(page.getByText('Metadados tecnicos permitidos')).toHaveCount(0)
})

test('ADMIN sees sanitized technical metadata without SQL or binds', async ({ page }) => {
  await openComparison(page, 'period', 'ADMIN')
  const details = page.getByTestId('comparison-technical-metadata')
  await details.locator('summary').click()
  await expect(details).toContainText('lumina.comparison-executor/1.0')
  await expect(details).not.toContainText('SELECT')
  await expect(details).not.toContainText('binds')
  await expect(details).not.toContainText('connection_string')
})

test('comparison remains responsive at the active project viewport', async ({ page }, testInfo) => {
  await openComparison(page, 'multiple_visualizations')
  await expectNoHorizontalOverflow(page)
  const screenshot = await page.getByTestId('comparison-renderer').screenshot({
    path: testInfo.outputPath('comparison-renderer.png'),
  })
  expect(screenshot.byteLength).toBeGreaterThan(10_000)
  const chart = page.getByTestId('comparison-chart-bar')
  await chart.scrollIntoViewIfNeeded()
  await expect(chart).toBeVisible()
  const chartScreenshot = await chart.screenshot({
    path: testInfo.outputPath('comparison-chart-bar.png'),
  })
  expect(chartScreenshot.byteLength).toBeGreaterThan(5_000)
})

test('comparison exposes accessible controls, table caption and chart description', async ({ page }) => {
  await openComparison(page, 'period')
  await expect(page.getByRole('button', { name: 'Exportar comparacao em CSV' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Abrir comparacao em tela cheia' })).toBeVisible()
  await expect(page.getByRole('img', { name: /PERIOD_VS_PERIOD/ })).toBeVisible()
  await expect(page.locator('caption')).toContainText('Comparacao')
  const fullscreenButton = page.getByRole('button', { name: 'Abrir comparacao em tela cheia' })
  await fullscreenButton.focus()
  await expect(fullscreenButton).toBeFocused()
  await fullscreenButton.press('Enter')
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
})

test('CSV export downloads raw comparative values and no sensitive metadata', async ({ page }) => {
  await openComparison(page, 'period')
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Exportar comparacao em CSV' }).click()
  const download = await downloadPromise
  const stream = await download.createReadStream()
  let content = ''
  for await (const chunk of stream) content += chunk.toString()
  expect(content).toContain('300.00')
  expect(content).toContain('400.00')
  expect(content).toContain('100.00')
  expect(content.toLowerCase()).not.toContain('select ')
  expect(content.toLowerCase()).not.toContain('binds')
})

test('dark theme preserves the comparison content and contrast classes', async ({ page }) => {
  await openComparison(page, 'period', 'ADMIN', 'dark')
  await expect(page.locator('html')).toHaveClass(/dark/)
  await expect(page.getByTestId('comparison-summary')).toBeVisible()
  await expect(page.getByText('R$ 300,00', { exact: true }).first()).toBeVisible()
})

test('shadow mode adapts structure without replacing the legacy runtime', async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('luminaai-theme', 'light')
    window.localStorage.setItem('lumina-comparison-renderer-v2', 'disabled')
    window.localStorage.setItem('lumina-comparison-renderer-v2-shadow', 'enabled')
    const target = window as typeof window & { __comparisonEvents?: unknown[] }
    target.__comparisonEvents = []
    window.addEventListener('lumina:comparison-presentation', event => {
      target.__comparisonEvents?.push((event as CustomEvent).detail)
    })
  })
  await mockComparisonApi(page, 'period', 'ADMIN')
  await authenticate(page, 'ADMIN')
  await page.goto('/dashboard')
  const input = page.getByPlaceholder('Faça uma pergunta sobre seus dados...')
  await input.fill('Compare o faturamento do Mes 06/2026 e 07/2026')
  await input.press('Enter')
  await expect.poll(async () => page.evaluate(() => {
    const target = window as typeof window & { __comparisonEvents?: unknown[] }
    return target.__comparisonEvents?.length ?? 0
  })).toBeGreaterThan(0)
  await expect(page.getByTestId('comparison-renderer')).toHaveCount(0)
  const renderer = await page.evaluate(() => {
    const target = window as typeof window & {
      __comparisonEvents?: Array<{ renderer?: string }>
    }
    return target.__comparisonEvents?.[0]?.renderer
  })
  expect(renderer).toBe('SHADOW')
})

test('timeout is announced and never presented as empty data', async ({ page }) => {
  await openComparison(page, 'timeout')
  await expect(page.getByTestId('comparison-state-banner')).toContainText('Tempo limite atingido')
  await expect(page.getByTestId('comparison-renderer')).not.toContainText('Nenhum registro encontrado')
  await expect(page.getByTestId('comparison-chart-bar')).toHaveCount(0)
})

test('blocked result is announced without exposing a dataset', async ({ page }) => {
  await openComparison(page, 'blocked')
  await expect(page.getByTestId('comparison-state-banner')).toContainText('Execucao bloqueada')
  await expect(page.getByTestId('comparison-table')).toHaveCount(0)
  await expect(page.getByTestId('comparison-chart-bar')).toHaveCount(0)
})
