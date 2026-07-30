import { expect, test, type Page, type Route } from '@playwright/test'

import { buildComparisonResponse } from '../fixtures/comparisonResponse'


const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:3100'
const tenantId = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'
const userId = '11111111-1111-4111-8111-111111111113'
const profileId = '51000000-0000-4000-8000-000000000001'
const analyticalPreferenceId = '52000000-0000-4000-8000-000000000004'

const user = {
  id: userId,
  nome: 'Consulta Lumina',
  email: 'consulta@lumina.test',
  role: 'CONSULTA',
  tenant_id: tenantId,
  must_change_password: false,
}

const capabilities = {
  mode: 'V2_READ_WRITE',
  frontend_enabled: true,
  defaults_enabled: true,
  saved_filters_enabled: true,
  export_enabled: true,
  deletion_enabled: true,
  legacy_import_enabled: false,
}

function preference(
  preferenceId: string,
  preferenceType: string,
  preferenceKey: string,
  content: Record<string, unknown>,
  risk = 'SAFE_PRESENTATION',
) {
  return {
    preference_id: preferenceId,
    preference_type: preferenceType,
    preference_key: preferenceKey,
    content,
    risk,
    origin: {
      kind: 'USER_EXPLICIT',
      source_label: 'Definida pelo usuário',
      confirmed_at: '2026-07-29T12:00:00Z',
    },
    status: 'ACTIVE',
    consent: risk === 'VISIBLE_ANALYTICAL_DEFAULT'
      ? {
          consent_id: '53000000-0000-4000-8000-000000000001',
          status: 'GRANTED',
          purpose: 'Aplicar o padrão somente quando a pergunta não definir filial.',
          scope: preferenceKey,
          policy_version: 'user-profile-consent/1.0',
          lock_version: 1,
          granted_at: '2026-07-29T12:00:00Z',
          revoked_at: null,
        }
      : null,
    effective_from: null,
    effective_to: null,
    expires_at: null,
    version: 1,
    lock_version: 1,
    updated_at: '2026-07-29T12:00:00Z',
  }
}

function profile() {
  return {
    schema_version: 'lumina.user-analytical-profile/1.0',
    profile_id: profileId,
    tenant_id: tenantId,
    user_id: userId,
    status: 'ACTIVE',
    profile_version: 4,
    lock_version: 4,
    checksum: 'a'.repeat(64),
    preferences: [
      preference(
        '52000000-0000-4000-8000-000000000001',
        'LOCALE',
        'display.locale',
        {
          kind: 'LOCALE',
          locale: 'pt-BR',
          timezone: 'America/Sao_Paulo',
          currency_display: 'BRL',
          date_format: 'DD/MM/YYYY',
          number_format: 'pt-BR',
        },
      ),
      preference(
        '52000000-0000-4000-8000-000000000002',
        'PRESENTATION',
        'display.presentation',
        {
          kind: 'PRESENTATION',
          preferred_visualization: 'BAR_CHART',
          table_first: true,
          table_density: 'COMPACT',
          page_size: 50,
          decimal_places: 2,
          ordering: 'DEFAULT',
          chart_granularity: 'AUTO',
          theme: 'SYSTEM',
        },
      ),
      preference(
        '52000000-0000-4000-8000-000000000003',
        'ACCESSIBILITY',
        'display.accessibility',
        {
          kind: 'ACCESSIBILITY',
          reduced_motion: false,
          high_contrast: false,
          larger_text: false,
          accessible_labels: true,
        },
      ),
      preference(
        analyticalPreferenceId,
        'ANALYTICAL_DEFAULT',
        'analysis.default.filial',
        {
          kind: 'ANALYTICAL_DEFAULT',
          field: 'filial',
          canonical_id: 'filial-centro',
          display_label: 'Filial Centro',
        },
        'VISIBLE_ANALYTICAL_DEFAULT',
      ),
    ],
    updated_at: '2026-07-29T12:00:00Z',
    disabled_at: null,
  }
}

async function authenticate(page: Page) {
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url')
  const payload = Buffer.from(JSON.stringify({
    sub: userId,
    tenant_id: tenantId,
    role: user.role,
    must_change_password: false,
    exp: Math.floor(Date.now() / 1000) + 3600,
  })).toString('base64url')
  await page.context().addCookies([{
    name: 'lumina-token',
    value: `${header}.${payload}.profile-test`,
    url: baseURL,
    httpOnly: true,
    sameSite: 'Lax',
  }])
}

async function installAuth(page: Page) {
  await page.route('**/api/v1/**', route => {
    const url = route.request().url()
    if (url.includes('/auth/session')) return route.fulfill({ json: user })
    if (url.includes('/query/history') || url.includes('/query/favorites')) {
      return route.fulfill({ json: [] })
    }
    if (url.includes('/dashboard-preferences/default')) {
      return route.fulfill({ json: { basis: 'liquido', format: 'ambos', instructions: '' } })
    }
    return route.fulfill({ json: { ok: true } })
  })
}

async function installProfileRoutes(
  page: Page,
  handler?: (route: Route) => Promise<void>,
) {
  await installAuth(page)
  await page.route('**/api/v2/me/**', async route => {
    if (handler) return handler(route)
    const url = route.request().url()
    if (url.endsWith('/capabilities')) return route.fulfill({ json: capabilities })
    if (url.endsWith('/analytical-profile')) return route.fulfill({ json: profile() })
    return route.fulfill({ json: preference(
      analyticalPreferenceId,
      'ANALYTICAL_DEFAULT',
      'analysis.default.filial',
      {
        kind: 'ANALYTICAL_DEFAULT',
        field: 'filial',
        canonical_id: 'filial-centro',
        display_label: 'Filial Centro',
      },
      'VISIBLE_ANALYTICAL_DEFAULT',
    ) })
  })
}

async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(() =>
    Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - window.innerWidth,
  )
  expect(overflow).toBeLessThanOrEqual(2)
}

test('profile renders localized owner settings without leaking technical data', async ({ page }) => {
  await installProfileRoutes(page)
  await authenticate(page)
  await page.goto('/dashboard/settings/profile')

  await expect(page.getByRole('heading', { name: 'Meu perfil analítico' })).toBeVisible()
  await expect(page.getByText('Idioma e formatação')).toBeVisible()
  await expect(page.getByText('Padrões, favoritos e referências')).toBeVisible()
  await expect(page.getByTestId('analytical-preference-list')).toContainText('analysis.default.filial')
  await expect(page.getByText(tenantId)).toHaveCount(0)
  await expect(page.getByText('SELECT', { exact: true })).toHaveCount(0)
  await expectNoHorizontalOverflow(page)
})

test('saving presentation settings sends three bounded preference updates', async ({ page }) => {
  const writes: Array<Record<string, unknown>> = []
  await installProfileRoutes(page, async route => {
    const url = route.request().url()
    if (url.endsWith('/capabilities')) return route.fulfill({ json: capabilities })
    if (route.request().method() === 'GET') return route.fulfill({ json: profile() })
    writes.push(route.request().postDataJSON() as Record<string, unknown>)
    return route.fulfill({ json: profile().preferences[0] })
  })
  await authenticate(page)
  await page.goto('/dashboard/settings/profile')

  await page.getByLabel('Visualização').selectOption('TABLE')
  await page.getByLabel('Itens por página').fill('75')
  await page.getByLabel('Reduzir movimento').check()
  await page.getByRole('button', { name: 'Salvar preferências' }).click()

  await expect.poll(() => writes.length).toBe(3)
  expect(writes.every(write => !('tenant_id' in write) && !('user_id' in write))).toBe(true)
  expect(writes[1]).toMatchObject({
    expected_lock_version: 1,
    content: {
      kind: 'PRESENTATION',
      preferred_visualization: 'TABLE',
      page_size: 75,
    },
  })
})

test('analytical defaults expose consent and status controls', async ({ page }) => {
  const operations: string[] = []
  await installProfileRoutes(page, async route => {
    const url = route.request().url()
    if (url.endsWith('/capabilities')) return route.fulfill({ json: capabilities })
    if (route.request().method() === 'GET') return route.fulfill({ json: profile() })
    operations.push(`${route.request().method()} ${new URL(url).pathname}`)
    return route.fulfill({ json: profile().preferences[3] })
  })
  await authenticate(page)
  await page.goto('/dashboard/settings/profile')

  await page.getByRole('button', { name: 'Revogar consentimento' }).click()
  await expect.poll(() => operations.length).toBe(1)
  expect(operations[0]).toContain(`/preferences/${analyticalPreferenceId}/consent`)

  await page.getByRole('button', { name: 'Desativar', exact: true }).last().click()
  await expect.poll(() => operations.length).toBe(2)
  expect(operations[1]).toContain(`/preferences/${analyticalPreferenceId}/disable`)
})

test('privacy controls support disable, export and idempotent deletion request', async ({ page }) => {
  const operations: Array<{ method: string; path: string; idempotency: string | null }> = []
  await installProfileRoutes(page, async route => {
    const url = route.request().url()
    if (url.endsWith('/capabilities')) return route.fulfill({ json: capabilities })
    if (route.request().method() === 'GET' && url.endsWith('/analytical-profile')) {
      return route.fulfill({ json: profile() })
    }
    if (url.endsWith('/profile/export')) {
      return route.fulfill({ json: { schema_version: 'lumina.user-analytical-profile/1.0', profile: profile() } })
    }
    operations.push({
      method: route.request().method(),
      path: new URL(url).pathname,
      idempotency: route.request().headers()['idempotency-key'] ?? null,
    })
    return route.fulfill({ json: profile() })
  })
  await authenticate(page)
  await page.goto('/dashboard/settings/profile')

  await page.getByRole('button', { name: 'Desativar perfil' }).click()
  await expect.poll(() => operations.length).toBe(1)
  expect(operations[0].path).toContain('/analytical-profile/disable')

  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Exportar JSON' }).click()
  expect((await download).suggestedFilename()).toBe('lumina-perfil-analitico.json')

  await page.getByRole('button', { name: 'Solicitar exclusão' }).click()
  await expect(page.getByRole('alertdialog')).toBeVisible()
  await page.getByLabel('Motivo opcional').fill('Não desejo mais manter padrões pessoais.')
  await page.getByRole('button', { name: 'Confirmar solicitação' }).click()
  await expect.poll(() => operations.length).toBe(2)
  expect(operations[1].idempotency).toMatch(/^[0-9a-f-]{36}$/i)
})

test('legacy rollout is fail-closed and does not fetch a V2 profile', async ({ page }) => {
  let profileReads = 0
  await installProfileRoutes(page, async route => {
    const url = route.request().url()
    if (url.endsWith('/capabilities')) {
      return route.fulfill({
        json: { ...capabilities, mode: 'LEGACY_ONLY', frontend_enabled: false },
      })
    }
    profileReads += 1
    return route.fulfill({ json: profile() })
  })
  await authenticate(page)
  await page.goto('/dashboard/settings/profile')

  await expect(page.getByTestId('profile-disabled-state')).toBeVisible()
  await expect(page.getByText('Perfil V2 ainda não ativado')).toBeVisible()
  expect(profileReads).toBe(0)
})

test('optimistic concurrency conflict is visible and preserves the form', async ({ page }) => {
  await installProfileRoutes(page, async route => {
    const url = route.request().url()
    if (url.endsWith('/capabilities')) return route.fulfill({ json: capabilities })
    if (route.request().method() === 'GET') return route.fulfill({ json: profile() })
    return route.fulfill({
      status: 409,
      json: {
        error: {
          code: 'USER_PROFILE_VERSION_CONFLICT',
          message: 'O perfil foi atualizado em outra sessão. Recarregue antes de salvar.',
        },
      },
    })
  })
  await authenticate(page)
  await page.goto('/dashboard/settings/profile')
  await page.getByLabel('Visualização').selectOption('LINE_CHART')
  await page.getByRole('button', { name: 'Salvar preferências' }).click()

  await expect(page.getByRole('alert').filter({ hasText: 'atualizado em outra sessão' })).toBeVisible()
  await expect(page.getByLabel('Visualização')).toHaveValue('LINE_CHART')
})

test('chat discloses applied preferences and supports a one-turn removal request', async ({ page }) => {
  const payloads: Array<Record<string, unknown>> = []
  await installAuth(page)
  await page.route('**/api/v1/query/', async route => {
    payloads.push(route.request().postDataJSON() as Record<string, unknown>)
    const response = buildComparisonResponse('period', 'CONSULTA')
    const turn = payloads.length
    const traceId = `55000000-0000-4000-8000-${turn.toString().padStart(12, '0')}`
    return route.fulfill({
      json: {
        ...response,
        query_id: traceId,
        request_id: traceId,
        response_node_id: `57000000-0000-4000-8000-${turn.toString().padStart(12, '0')}`,
        applied_preference_summary: {
          schema_version: 'lumina.user-analytical-profile/1.0',
          applied: [{
            preference_type: 'ANALYTICAL_DEFAULT',
            label: 'Filial padrão',
            value_label: 'Filial Centro',
            origin_label: 'Definida pelo usuário',
            removable_this_turn: true,
            settings_path: '/dashboard/settings/profile',
            expires_at: null,
          }],
          ignored: [],
          consent_required: [],
          has_visible_analytical_default: true,
        },
      },
    })
  })
  await authenticate(page)
  await page.goto('/dashboard')
  const input = page.getByRole('textbox')
  await input.fill('Faturamento de julho de 2026')
  await input.press('Enter')

  const summary = page.getByTestId('applied-preference-summary')
  await expect(summary).toContainText('Filial padrão')
  await expect(summary).toContainText('Filial Centro')
  await summary.getByRole('button', { name: 'Remover preferências desta análise' }).click()
  await expect.poll(() => payloads.length).toBe(2)
  expect(payloads[1].pergunta).toContain('não use as preferências')
})
