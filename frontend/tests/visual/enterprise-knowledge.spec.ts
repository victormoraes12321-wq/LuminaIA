import { expect, test, type Page } from '@playwright/test'


const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:3100'
const tenantId = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'
const assetId = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1'
const versionId = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb1'

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

const asset = {
  schema_version: 'lumina.enterprise-knowledge/1.0',
  asset_id: assetId,
  tenant_id: tenantId,
  canonical_key: 'faturamento',
  asset_type: 'BUSINESS_TERM',
  domain: 'Vendas',
  ownership: {
    owner_user_id: '11111111-1111-4111-8111-111111111112',
    steward_label: 'Gestão comercial',
    accountable_area: 'Comercial',
    transferred_at: null,
  },
  status: 'ACTIVE',
  current_published_version_id: versionId,
  lock_version: 1,
  created_at: '2026-07-29T10:00:00Z',
  updated_at: '2026-07-29T11:00:00Z',
}

const content = {
  kind: 'BUSINESS_TERM',
  canonical_name: 'faturamento',
  display_name: 'Faturamento',
  definition: 'Receita comercial reconhecida conforme a política de vendas.',
  domain: 'Vendas',
  short_description: 'Receita comercial reconhecida.',
  full_description: 'Receita comercial reconhecida conforme a política de vendas.',
  allowed_examples: [],
  incorrect_examples: [],
  aliases: ['receita de vendas'],
  related_terms: [],
  source_references: [],
  locale: 'pt-BR',
  tags: [],
}

const version = {
  schema_version: 'lumina.enterprise-knowledge/1.0',
  version_id: versionId,
  tenant_id: tenantId,
  asset_id: assetId,
  version_number: 1,
  lifecycle: 'PUBLISHED',
  content,
  checksum: 'a'.repeat(64),
  author_user_id: '11111111-1111-4111-8111-111111111112',
  previous_version_id: null,
  effective_from: '2026-07-29T10:00:00Z',
  effective_to: null,
  lock_version: 3,
  created_at: '2026-07-29T10:00:00Z',
  updated_at: '2026-07-29T11:00:00Z',
}

async function authenticate(page: Page, role: 'ADMIN' | 'CONSULTA') {
  const user = session(role)
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url')
  const payload = Buffer.from(JSON.stringify({
    sub: user.id,
    tenant_id: tenantId,
    role,
    must_change_password: false,
    exp: Math.floor(Date.now() / 1000) + 3600,
  })).toString('base64url')
  await page.context().addCookies([{
    name: 'lumina-token',
    value: `${header}.${payload}.knowledge-test`,
    url: baseURL,
    httpOnly: true,
    sameSite: 'Lax',
  }])
}

async function installRoutes(page: Page, role: 'ADMIN' | 'CONSULTA') {
  await page.route('**/api/v1/**', route => {
    if (route.request().url().includes('/auth/session')) {
      return route.fulfill({ json: session(role) })
    }
    return route.fulfill({ json: [] })
  })
  await page.route('**/api/v2/enterprise-knowledge/**', route => {
    const url = route.request().url()
    if (url.includes('/glossary')) {
      return route.fulfill({
        json: {
          schema_version: 'lumina.enterprise-knowledge/1.0',
          query_normalized: 'receita de vendas',
          candidates: [{
            asset_id: assetId,
            version_id: versionId,
            canonical_key: 'faturamento',
            asset_type: 'BUSINESS_TERM',
            display_name: 'Faturamento',
            domain: 'Vendas',
            score: 950,
            match_type: 'ALIAS_EXACT',
            matched_field: 'alias',
            matched_text: 'receita de vendas',
            checksum: 'a'.repeat(64),
            provenance: [],
          }],
          next_cursor: null,
          ambiguous: false,
          duration_ms: 2.4,
        },
      })
    }
    if (url.includes('/published/faturamento')) {
      return route.fulfill({ json: { asset, versions: [version] } })
    }
    if (url.endsWith(`/assets/${assetId}/audit`)) {
      return route.fulfill({
        json: [{
          event_id: 'cccccccc-cccc-4ccc-8ccc-ccccccccccc1',
          asset_id: assetId,
          version_id: versionId,
          actor_user_id: session('ADMIN').id,
          event_type: 'VERSION_PUBLISHED',
          reason_code: 'HUMAN_PUBLICATION',
          created_at: '2026-07-29T11:00:00Z',
        }],
      })
    }
    if (url.endsWith(`/assets/${assetId}/diff`)) {
      return route.fulfill({
        json: {
          asset_id: assetId,
          from_version: 1,
          to_version: 1,
          added_fields: [],
          removed_fields: [],
          changed_fields: [],
          from_checksum: 'a'.repeat(64),
          to_checksum: 'a'.repeat(64),
        },
      })
    }
    if (url.endsWith(`/assets/${assetId}`)) {
      return route.fulfill({ json: { asset, versions: [version] } })
    }
    if (url.includes('/assets?')) {
      return route.fulfill({ json: [asset] })
    }
    return route.fulfill({ json: { version, publication: {} } })
  })
}

async function expectNoOverflow(page: Page) {
  const overflow = await page.evaluate(() =>
    Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - window.innerWidth,
  )
  expect(overflow).toBeLessThanOrEqual(2)
}

test('CONSULTA searches only the published glossary', async ({ page }) => {
  await installRoutes(page, 'CONSULTA')
  await authenticate(page, 'CONSULTA')
  await page.addInitScript(() => window.localStorage.setItem('lumina-theme', 'light'))
  await page.goto('/dashboard/knowledge')
  await expect(page.getByRole('heading', { name: 'Base de Conhecimento' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Governança' })).toHaveCount(0)
  await page.getByPlaceholder('Pesquisar termo ou alias').fill('receita de vendas')
  await page.getByRole('button', { name: 'Pesquisar' }).click()
  await expect(page.getByRole('heading', { name: 'Faturamento' })).toBeVisible()
  await expect(page.getByText('Publicado')).toBeVisible()
  await page.getByRole('button', { name: 'Abrir definição' }).click()
  await expect(page.getByText(content.definition)).toBeVisible()
  await expect(page.getByText('Gestão comercial')).toBeVisible()
  await expectNoOverflow(page)
})

test('ADMIN opens governance, version history and audit timeline', async ({ page }) => {
  await installRoutes(page, 'ADMIN')
  await authenticate(page, 'ADMIN')
  await page.addInitScript(() => window.localStorage.setItem('lumina-theme', 'dark'))
  await page.goto('/dashboard/knowledge')
  await page.getByRole('button', { name: 'Governança' }).click()
  await expect(page.getByRole('heading', { name: 'Assets' })).toBeVisible()
  await page.getByRole('button', { name: /faturamento/i }).click()
  await expect(page.getByRole('heading', { name: 'Faturamento' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Versões' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Auditoria' })).toBeVisible()
  await expect(page.getByText('VERSION_PUBLISHED')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Nova revisão' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Ownership' })).toBeVisible()
  await expect(page.getByLabel('Estado')).toBeVisible()
  await expectNoOverflow(page)
})
