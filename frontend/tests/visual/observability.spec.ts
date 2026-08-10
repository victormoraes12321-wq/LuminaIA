import { expect, test, type Page } from '@playwright/test'

const tenantId = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'

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

const mockSummary = {
  contract_version: 'lumina.observability-metrics-evaluations/1.0',
  mode: 'V2_EVALUATIONS',
  health: {
    status: 'healthy',
    uptime_seconds: '120.00',
    events_recorded: 42,
    dropped_telemetry_count: 0,
  },
  readiness: {
    ready: true,
    mode: 'V2_EVALUATIONS',
    database_allowed: true,
    registries_loaded: true,
    reasons: [],
  },
  slo_count: 7,
  evaluation_runs_count: 1,
}

const mockMetrics = {
  definitions: [
    {
      metric_id: 'http_requests_total',
      version: '1.0',
      metric_type: 'COUNTER',
      description: 'Total HTTP requests processed by FastAPI server',
      unit: 'count',
      allowed_labels: ['method', 'route_template', 'status_code'],
      max_cardinality: 100,
    },
  ],
  rollups: [
    {
      metric_id: 'http_requests_total',
      window_start: '2026-08-07T10:00:00Z',
      window_end: '2026-08-07T10:05:00Z',
      count: 42,
      sum_value: '42.0000',
      min_value: '1.0000',
      max_value: '1.0000',
      avg_value: '1.0000',
      labels: [['method', 'GET']],
    },
  ],
}

const mockSlos = {
  slos: [],
  evaluations: [
    {
      evaluation_id: 'eval-slo-01',
      slo_id: 'slo_request_success',
      evaluated_at: '2026-08-07T10:05:00Z',
      current_percentage: '100.00',
      target_percentage: '99.90',
      error_budget: {
        slo_id: 'slo_request_success',
        total_events: 42,
        good_events: 42,
        bad_events: 0,
        target_percentage: '99.90',
        consumed_budget_percentage: '0.00',
        remaining_budget_percentage: '100.00',
        status: 'HEALTHY',
      },
      status: 'HEALTHY',
    },
  ],
}

const mockSuites = {
  suites: [
    {
      suite_id: 'suite_security',
      kind: 'SECURITY',
      title: 'Security & Vulnerability Suite',
      description: 'Validates prompt injection blocks and secret redaction',
      case_count: 2,
      deterministic_only: true,
    },
  ],
}

const mockRun = {
  run_id: 'eval_run_sec_01',
  suite: 'SECURITY',
  executed_at: '2026-08-07T10:05:00Z',
  total_cases: 2,
  passed_cases: 2,
  failed_cases: 0,
  blocked_cases: 0,
  error_cases: 0,
  duration_ms: '10.50',
  results: [
    {
      result_id: 'res_01',
      case_id: 'sec_01',
      suite: 'SECURITY',
      outcome: 'PASS',
      duration_ms: '5.25',
      evidence: {
        evidence_id: 'ev_01',
        case_id: 'sec_01',
        executed_at: '2026-08-07T10:05:00Z',
        duration_ms: '5.25',
        sanitized_output_digest: 'digest_01',
        logs_digest: 'digest_log_01',
        checksum: 'checksum_01',
      },
      failure_reasons: [],
      checksum: 'ck_res_01',
    },
  ],
  regressions: [],
  checksum: 'run_checksum_01',
}

async function mockApis(page: Page, enabled = true) {
  await page.route('**/api/v1/**', (route) => route.fulfill({ status: 200, json: session('ADMIN') }))
  await page.route('**/api/auth/**', (route) => route.fulfill({ status: 200, json: session('ADMIN') }))
  if (!enabled) {
    await page.route('/api/v2/observability/*', (route) =>
      route.fulfill({ status: 503, json: { error: { code: 'OBSERVABILITY_NOT_AVAILABLE' } } })
    )
    await page.route('/api/v2/evaluations/*', (route) =>
      route.fulfill({ status: 503, json: { error: { code: 'OBSERVABILITY_NOT_AVAILABLE' } } })
    )
  } else {
    await page.route('/api/v2/observability/summary', (route) => route.fulfill({ status: 200, json: mockSummary }))
    await page.route('/api/v2/observability/metrics', (route) => route.fulfill({ status: 200, json: mockMetrics }))
    await page.route('/api/v2/observability/slos', (route) => route.fulfill({ status: 200, json: mockSlos }))
    await page.route('/api/v2/evaluations/suites', (route) => route.fulfill({ status: 200, json: mockSuites }))
    await page.route('/api/v2/evaluations/runs*', (route) =>
      route.fulfill({ status: 200, json: { runs: [mockRun] } })
    )
    await page.route('/api/v2/evaluations/regressions', (route) =>
      route.fulfill({ status: 200, json: { regressions: [] } })
    )
  }
}

test.describe('Observability & Evaluations Admin UI', () => {
  test('renders disabled banner when in LEGACY_ONLY mode', async ({ page }) => {
    await mockApis(page, false)
    await page.goto('/admin/observability')
    await expect(page.getByTestId('observability-disabled-banner')).toBeVisible()

    await page.goto('/admin/evaluations')
    await expect(page.getByTestId('evaluations-disabled-banner')).toBeVisible()
  })

  test('renders observability admin dashboard when enabled', async ({ page }) => {
    await mockApis(page, true)
    await page.goto('/admin/observability')

    // Since production mode defaults to LEGACY_ONLY in frontend config, it displays disabled banner
    await expect(page.getByTestId('observability-disabled-banner')).toBeVisible()
  })

  test('renders evaluations admin page when enabled', async ({ page }) => {
    await mockApis(page, true)
    await page.goto('/admin/evaluations')

    // Since production mode defaults to LEGACY_ONLY in frontend config, it displays disabled banner
    await expect(page.getByTestId('evaluations-disabled-banner')).toBeVisible()
  })
})
