import { expect, test, type Page } from '@playwright/test'

const consoleErrorsByPage = new WeakMap<Page, string[]>()
const visualBaseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:3100'

const user = {
  id: '11111111-1111-4111-8111-111111111111',
  nome: 'Admin Lumina',
  email: 'admin@luminaai.demo',
  role: 'ADMIN',
  tenant_id: 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
  must_change_password: false,
}

const template = {
  id: 'template-1',
  name: 'Executive Overview',
  description: 'Template visual de certificacao',
  category: 'EXECUTIVE',
  version: 1,
  grid: {
    columns: 12,
    items: [
      { id: 'kpi-revenue', x: 0, y: 0, w: 3, h: 2 },
      { id: 'sales-line', x: 3, y: 0, w: 6, h: 4 },
      { id: 'ranking', x: 9, y: 0, w: 3, h: 4 },
    ],
  },
  components: [
    { id: 'kpi-revenue', type: 'KPI', title: 'Receita Total' },
    { id: 'sales-line', type: 'LINE', title: 'Evolucao de Vendas' },
    { id: 'ranking', type: 'RANKING', title: 'Top Vendedores' },
  ],
  theme: {},
  atualizado_em: '2026-07-08T00:00:00.000Z',
}

const instance = {
  id: 'instance-1',
  template_id: template.id,
  name: 'Minha Dashboard Executiva',
  version: 1,
  is_favorite: true,
  layout_override: {},
  panel_positions: {},
  preferences: {},
  atualizado_em: '2026-07-08T00:00:00.000Z',
}

async function mockEnterpriseApi(page: Page) {
  await page.route('**/api/v2/dashboards**', route => route.fulfill({ json: [] }))
  await page.route('**/api/v1/**', async route => {
    const url = route.request().url()
    const method = route.request().method()

    if (url.includes('/auth/session')) {
      return route.fulfill({ json: user })
    }

    if (url.includes('/query/history') || url.includes('/query/favorites')) {
      return route.fulfill({ json: [] })
    }

    if (url.includes('/catalog/')) {
      return route.fulfill({
        json: [
          {
            id: 'view-1',
            nome_view_oracle: 'VW_VENDAS_MENSAIS',
            descricao_para_ia: 'Vendas mensais consolidadas',
            tipo_grafico_padrao: 'BAR',
            parametros_schema: {},
            ativo: true,
            criado_em: '2026-07-08T00:00:00.000Z',
          },
        ],
      })
    }

    if (url.includes('/users/')) {
      return route.fulfill({ json: [user] })
    }

    if (url.includes('/tenant/audit-logs')) {
      return route.fulfill({ json: [] })
    }

    if (url.includes('/tenant/settings')) {
      return route.fulfill({
        json: {
          ia_config: { registered_models: [], active_model_id: null, temperature: 0.2 },
          db_config: {},
          postgres_clone_config: {},
          sync_config: { enabled: false, times: [] },
          last_sync: null,
        },
      })
    }

    if (url.includes('/dashboard-studio/templates') && method === 'GET') {
      return route.fulfill({ json: [template] })
    }

    if (url.includes('/dashboard-studio/instances') && method === 'GET') {
      return route.fulfill({ json: [instance] })
    }

    return route.fulfill({ json: { ok: true } })
  })
}

async function authenticateProxy(page: Page) {
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url')
  const payload = Buffer.from(JSON.stringify({
    sub: user.email,
    tenant_id: user.tenant_id,
    role: user.role,
    must_change_password: false,
    exp: Math.floor(Date.now() / 1000) + 3600,
  })).toString('base64url')

  await page.context().addCookies([
    {
      name: 'lumina-token',
      value: `${header}.${payload}.visual-test`,
      url: visualBaseURL,
      httpOnly: true,
      sameSite: 'Lax',
    },
  ])
}

async function expectNoHorizontalOverflow(page: Page) {
  await page.waitForLoadState('domcontentloaded')
  await page.locator('body').waitFor({ state: 'visible' })
  const overflow = await page.evaluate(() => {
    const documentElement = document.documentElement
    const body = document.body
    return Math.max(documentElement.scrollWidth, body.scrollWidth) - window.innerWidth
  })
  expect(overflow).toBeLessThanOrEqual(2)
}

test.beforeEach(async ({ page }) => {
  const consoleErrors: string[] = []
  consoleErrorsByPage.set(page, consoleErrors)
  page.on('console', message => {
    if (message.type() === 'error') {
      consoleErrors.push(message.text())
    }
  })
  await mockEnterpriseApi(page)
  await page.addInitScript(() => {
    window.localStorage.setItem('lumina-theme', 'light')
  })
})

test.afterEach(async ({ page }) => {
  const consoleErrors = consoleErrorsByPage.get(page) || []
  expect(consoleErrors, consoleErrors.join('\n')).toEqual([])
})

test('login remains visually stable across enterprise viewports', async ({ page }) => {
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: /luminaai/i })).toBeVisible()
  await expectNoHorizontalOverflow(page)
})

test('dashboard shell renders without layout overflow', async ({ page }) => {
  await authenticateProxy(page)
  await page.goto('/dashboard')
  await expect(page.locator('body')).toBeVisible()
  await expectNoHorizontalOverflow(page)
})

test('dashboard studio renders template and instance panels responsively', async ({ page }) => {
  await authenticateProxy(page)
  await page.goto('/dashboard/studio')
  await expect(page.getByText('Executive Overview')).toBeVisible()
  await expect(page.getByText('Minha Dashboard Executiva')).toBeVisible()
  await expectNoHorizontalOverflow(page)
})

test('admin pages keep responsive shell integrity', async ({ page }) => {
  await authenticateProxy(page)
  for (const path of ['/dashboard/admin/catalog', '/dashboard/admin/users', '/dashboard/admin/settings']) {
    await page.goto(path)
    await expect(page.locator('body')).toBeVisible()
    await expectNoHorizontalOverflow(page)
  }
})
