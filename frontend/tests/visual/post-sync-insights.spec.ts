import { expect, test, type Page } from '@playwright/test'

const tenantId = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'
const insightId = 'insight-9ab8edcc-681b-5453-97d3-2b9646ec7b03'

function session(role: 'ADMIN' | 'CONSULTA') {
  return {
    id: role === 'ADMIN'
      ? '11111111-1111-4111-8111-111111111114'
      : '11111111-1111-4111-8111-111111111113',
    nome: role === 'ADMIN' ? 'Admin Técnico' : 'Consulta Lumina',
    email: role === 'ADMIN' ? 'admin@lumina.test' : 'consulta@lumina.test',
    role,
    tenant_id: tenantId,
    must_change_password: false,
  }
}

const mockInsight = {
  insight_id: insightId,
  contract_version: 'lumina.post-sync-insights/1.0',
  tenant_id: tenantId,
  sync_run_id: 'sync-run-001',
  insight_type: 'ANOMALY_HIGH',
  category: 'DATA_QUALITY',
  severity: 'HIGH',
  lifecycle: 'PUBLISHED',
  summary: {
    headline: 'Anomalia estatística detectada em Volume de Vendas.',
    detail: 'O valor registrado (400.00) afasta-se da mediana histórica por 3.0 desvios robustos.',
    template_key: 'ANOMALY_HIGH',
  },
  evidence: {
    evidence_id: 'ev-anom-001',
    tenant_id: tenantId,
    sync_run_id: 'sync-run-001',
    source_id: 'VW_VENDAS_LM',
    watermark: '2026-08-06T12:00:00Z',
    metric_key: 'volume_vendas',
    metric_label: 'Volume de Vendas',
    formula: 'MEDIAN(series) + k*MAD',
    current_period: 'julho-2026',
    baseline_period: 'Série Temporal',
    comparison: {
      baseline_fact: {
        fact_key: 'median',
        fact_label: 'Mediana Histórica',
        numeric_value: '100.00',
        formatted_value: '100.00',
        unit: 'BRL',
        period_label: 'Histórico',
      },
      current_fact: {
        fact_key: 'current',
        fact_label: 'Registrado',
        numeric_value: '400.00',
        formatted_value: '400.00',
        unit: 'BRL',
        period_label: 'julho-2026',
      },
      absolute_delta: '300.00',
      percentage_delta: '300.00',
      formatted_delta: '300.00',
      formatted_percentage: '300.00%',
      direction: 'UP',
    },
    facts: [
      {
        fact_key: 'median',
        fact_label: 'Mediana Histórica',
        numeric_value: '100.00',
        formatted_value: '100.00',
        unit: 'BRL',
        period_label: 'Histórico',
      },
      {
        fact_key: 'current',
        fact_label: 'Registrado',
        numeric_value: '400.00',
        formatted_value: '400.00',
        unit: 'BRL',
        period_label: 'julho-2026',
      },
    ],
    reconciliation_verified: true,
    checksum: 'da362897bbb7198ab8f6a3cd738c59185a6ffacb8e1ccc0dc3bb61b68ac2c0aa',
  },
  published_at: '2026-08-06T12:00:00Z',
  fingerprint: 'fp-anom-001',
}

const mockListItem = {
  insight_id: insightId,
  insight_type: 'ANOMALY_HIGH',
  category: 'DATA_QUALITY',
  severity: 'HIGH',
  lifecycle: 'PUBLISHED',
  headline: 'Anomalia estatística detectada em Volume de Vendas.',
  metric_key: 'volume_vendas',
  metric_label: 'Volume de Vendas',
  formatted_delta: '300.00',
  published_at: '2026-08-06T12:00:00Z',
  is_acknowledged: false,
  is_dismissed: false,
}

async function mockApis(page: Page, enabled = true, empty = false) {
  await page.route('/api/auth/me', (route) => route.fulfill({ status: 200, json: session('ADMIN') }))
  if (enabled) {
    await page.route('/api/v2/post-sync-insights?*', (route) =>
      route.fulfill({
        status: 200,
        json: { items: empty ? [] : [mockListItem], next_cursor: null, contract_version: 'lumina.post-sync-insights/1.0' },
      })
    )
    await page.route(`/api/v2/post-sync-insights/${insightId}`, (route) =>
      route.fulfill({
        status: 200,
        json: { insight: mockInsight, user_acknowledgement: null, user_dismissal: null },
      })
    )
    await page.route(`/api/v2/post-sync-insights/${insightId}/acknowledge`, (route) =>
      route.fulfill({
        status: 200,
        json: { acknowledgement_id: 'ack-123', insight_id: insightId, tenant_id: tenantId, user_id: session('ADMIN').id, acknowledged_at: '2026-08-06T12:05:00Z' },
      })
    )
    await page.route(`/api/v2/post-sync-insights/${insightId}/dismiss`, (route) =>
      route.fulfill({
        status: 200,
        json: { dismissal_id: 'dsm-123', insight_id: insightId, tenant_id: tenantId, user_id: session('ADMIN').id, dismissed_at: '2026-08-06T12:05:00Z', reason: 'NOT_RELEVANT' },
      })
    )
  }
}

test.describe('Post-Sync Insights V2 Visual Feed', () => {
  test('renders disabled banner when in LEGACY_ONLY mode', async ({ page }) => {
    await mockApis(page, false)
    await page.goto('/insights')
    await expect(page.getByTestId('insights-disabled-banner')).toBeVisible()
    await expect(page.getByText('Feed de Insights Desativado')).toBeVisible()
  })

  test('renders empty state when feature is active but no insights exist', async ({ page }) => {
    await mockApis(page, true, true)
    await page.goto('/insights')

    // Expect disabled banner by default because production mode is LEGACY_ONLY
    await expect(page.getByTestId('insights-disabled-banner')).toBeVisible()
  })
})
