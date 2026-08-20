import { expect, test, type Page } from '@playwright/test'


const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:3100'
const tenantId = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'
const userId = '11111111-1111-4111-8111-111111111114'
const indexId = '71000000-0000-4000-8000-000000000001'
const versionId = '72000000-0000-4000-8000-000000000001'

const user = {
  id: userId,
  nome: 'Admin Técnico',
  email: 'admin@lumina.test',
  role: 'ADMIN',
  tenant_id: tenantId,
  must_change_password: false,
}

async function authenticate(page: Page) {
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url')
  const payload = Buffer.from(JSON.stringify({
    sub: userId,
    tenant_id: tenantId,
    role: 'ADMIN',
    must_change_password: false,
    exp: Math.floor(Date.now() / 1000) + 3600,
  })).toString('base64url')
  await page.context().addCookies([{
    name: 'lumina-token',
    value: `${header}.${payload}.semantic-test`,
    url: baseURL,
    httpOnly: true,
    sameSite: 'Lax',
  }])
}

async function installRoutes(page: Page) {
  await page.route('**/api/v1/**', route => {
    if (route.request().url().includes('/auth/session')) {
      return route.fulfill({ json: user })
    }
    return route.fulfill({ json: [] })
  })
  await page.route('**/api/v2/semantic/**', route => {
    const url = route.request().url()
    if (url.endsWith('/capabilities')) {
      return route.fulfill({
        json: {
          contract_version: 'lumina.semantic-retrieval/1.0',
          mode: 'HYBRID_READ',
          frontend_enabled: true,
          entity_instance_indexing_enabled: false,
          vector_channel_enabled: false,
          profile_tie_breaker_enabled: false,
          admin_inspector_enabled: true,
          cache_enabled: true,
          incremental_build_enabled: false,
          permission_fingerprint: 'a'.repeat(64),
        },
      })
    }
    if (url.endsWith('/admin/indexes')) {
      return route.fulfill({
        json: [{
          index_id: indexId,
          tenant_id: tenantId,
          name: 'Índice empresarial',
          locale: 'pt-BR',
          document_types: ['METRIC', 'DIMENSION'],
          entity_policies: [],
          source_policies: ['ENTERPRISE_KNOWLEDGE', 'METRIC_REGISTRY'],
          allowed_classifications: ['TENANT_BUSINESS_METADATA'],
          representation_provider: 'DETERMINISTIC_FEATURE_HASH',
          representation_version: 'lumina.deterministic-feature-hash/1.0',
          ranking_policy: { policy_version: 'lumina.semantic-ranking/1.0' },
          threshold_policy: {
            policy_version: 'lumina.semantic-thresholds/1.0',
            minimum_retrieval_score: 0.3,
            minimum_automatic_resolution_score: 0.72,
            ambiguity_margin: 0.08,
          },
          status: 'ACTIVE',
          owner_user_id: userId,
          lock_version: 2,
          active_version_id: versionId,
          created_at: '2026-07-30T10:00:00Z',
          updated_at: '2026-07-30T11:00:00Z',
        }],
      })
    }
    if (url.includes('/stale-sources')) {
      return route.fulfill({ json: [] })
    }
    if (url.includes('/evaluations')) {
      return route.fulfill({
        json: [{
          evaluation_id: '75000000-0000-4000-8000-000000000001',
          tenant_id: tenantId,
          index_version_id: versionId,
          corpus_version: 'semantic-synthetic-v1',
          case_count: 24,
          passed: true,
          metrics: [{ name: 'TOP_1_ACCURACY', value: 1 }],
          checksum: 'f'.repeat(64),
          executed_at: '2026-07-30T10:03:00Z',
        }],
      })
    }
    if (url.includes('/versions')) {
      return route.fulfill({
        json: [{
          version_id: versionId,
          tenant_id: tenantId,
          index_id: indexId,
          version: 1,
          lifecycle: 'PUBLISHED',
          source_manifest: {
            sources: [{
              source_type: 'ENTERPRISE_KNOWLEDGE',
              source_id: 'published-knowledge',
              source_version: '12',
              source_checksum: 'b'.repeat(64),
              stale: false,
            }],
            checksum: 'c'.repeat(64),
          },
          document_count: 248,
          entity_count: 90,
          alias_count: 113,
          relation_count: 41,
          representation_version: 'lumina.deterministic-feature-hash/1.0',
          build_mode: 'FULL',
          watermark: null,
          build_started_at: '2026-07-30T10:00:00Z',
          build_completed_at: '2026-07-30T10:01:00Z',
          checksum: 'd'.repeat(64),
          created_by: userId,
          reviewed_by: userId,
          published_by: userId,
          published_at: '2026-07-30T10:02:00Z',
          superseded_version_id: null,
          failure_summary: null,
          lock_version: 2,
        }],
      })
    }
    if (url.includes('/admin/audit')) {
      return route.fulfill({
        json: [{
          event_id: '73000000-0000-4000-8000-000000000001',
          tenant_id: tenantId,
          index_id: indexId,
          version_id: versionId,
          actor_user_id: userId,
          event_type: 'INDEX_VERSION_PUBLISHED',
          reason_code: 'EXPLICIT_PUBLICATION',
          structural_fingerprint: 'e'.repeat(64),
          created_at: '2026-07-30T10:02:00Z',
        }],
      })
    }
    if (url.endsWith('/admin/search')) {
      return route.fulfill({
        json: {
          decision: 'RESOLVED',
          normalized_query: 'receita de vendas',
          public_explanation: 'Correspondência identificada: Faturamento.',
          index_version_id: versionId,
          candidates: [{
            document_id: '74000000-0000-4000-8000-000000000001',
            public_label: 'Faturamento',
            entity_type: 'METRIC',
            domain: 'sales',
            score: 0.96,
            confidence_band: 'EXACT',
            matched_channels: ['EXACT_ALIAS'],
            canonical_reference: {
              canonical_id: 'faturamento_comercial',
              display_label: 'Faturamento',
              source_type: 'ENTERPRISE_KNOWLEDGE',
              source_version: '12',
            },
            breakdown: {
              final_score: 0.96,
              positive_score: 0.96,
              penalties: 0,
              channels: [{
                channel: 'EXACT_ALIAS',
                raw_score: 1,
                contribution: 0.96,
                reason_code: 'PUBLISHED_ALIAS',
              }],
            },
          }],
        },
      })
    }
    return route.fulfill({ json: {} })
  })
}

test('ADMIN inspects the published semantic index without layout overflow', async ({ page }) => {
  await authenticate(page)
  await installRoutes(page)
  await page.goto('/dashboard/admin/semantic')
  await expect(page.getByRole('heading', { name: 'Índice semântico' })).toBeVisible()
  await expect(page.getByRole('cell', { name: 'PUBLISHED', exact: true })).toBeVisible()
  await expect(page.getByText('248')).toBeVisible()
  await expect(page.getByText('INDEX_VERSION_PUBLISHED')).toBeVisible()
  await expect(page.getByText('Nenhuma fonte desatualizada.')).toBeVisible()
  await expect(page.getByText('semantic-synthetic-v1 · 24 casos')).toBeVisible()

  await page.getByLabel('Termo').fill('receita de vendas')
  await page.getByRole('button', { name: 'Inspecionar' }).click()
  await expect(page.getByText('faturamento_comercial')).toBeVisible()
  await expect(page.getByText('EXACT_ALIAS')).toBeVisible()

  const overflow = await page.evaluate(() =>
    Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - window.innerWidth,
  )
  expect(overflow).toBeLessThanOrEqual(2)
})
