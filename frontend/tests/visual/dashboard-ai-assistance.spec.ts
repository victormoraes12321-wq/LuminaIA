import { expect, test, type Page } from '@playwright/test'
import { dashboardBlueprintFixture } from '../fixtures/dashboardV2'
import type { DashboardAiProposalV2 } from '../../types/dashboard_ai_assistance_v2'

const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:3100'
const aiMode = process.env.PLAYWRIGHT_DASHBOARD_AI_MODE || 'AI_ASSISTED_EDIT'
const user = { id: 'user-admin', nome: 'Admin Lumina', email: 'admin@lumina.test', role: 'ADMIN', tenant_id: 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', must_change_password: false }
const HASH_A = 'a'.repeat(64), HASH_B = 'b'.repeat(64), HASH_C = 'c'.repeat(64)

async function authenticate(page: Page) {
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url')
  const payload = Buffer.from(JSON.stringify({ sub: user.id, tenant_id: user.tenant_id, role: user.role, exp: Math.floor(Date.now() / 1000) + 3600 })).toString('base64url')
  await page.context().addCookies([{ name: 'lumina-token', value: `${header}.${payload}.dashboard-ai-test`, url: baseURL, httpOnly: true, sameSite: 'Lax' }])
}

function readyProposal(status: DashboardAiProposalV2['status'] = 'READY_FOR_REVIEW', lock = 6): DashboardAiProposalV2 {
  return {
    contract_version: 'lumina.dashboard-ai-assistance/1.0', proposal_id: 'proposal.ai.001', operation: 'CREATE_DASHBOARD', origin: 'CREATION_WIZARD', status,
    current_version: 1, lock_version: lock, created_at: '2026-08-05T12:00:00Z', updated_at: '2026-08-05T12:00:01Z',
    latest: {
      proposal_id: 'proposal.ai.001', version: 1, status: 'READY_FOR_REVIEW', created_at: '2026-08-05T12:00:01Z', content_checksum: HASH_A,
      blueprint_proposal: { design_spec: { design_spec_id: 'design.ai.001', title: 'Dashboard assistido', description: 'Dashboard assistido e governado para decisões empresariais.', template_id: 'SALES_PERFORMANCE', metric_ids: ['metric.average.ticket'], dimension_ids: ['dimension.month'], canonical_period_id: 'period.2026.07', widgets: [{ widget_key: 'widget.kpi', purpose: 'Apresentar ticket médio', widget_type: 'KPI', metric_ids: ['metric.average.ticket'], dimension_ids: [] }], resolution_checksum: HASH_B }, blueprint: { ...dashboardBlueprintFixture, lifecycle: 'DRAFT', created_origin: 'AI_PROPOSED' }, blueprint_checksum: HASH_A, semantic_checksum: HASH_B, visual_checksum: HASH_C },
      rationale: { summary: 'Template e widgets foram selecionados por regras determinísticas.', decisions: ['Métrica canônica validada', 'Período normalizado'], omitted_details_notice: 'Raciocínio interno do modelo não é armazenado nem exibido.' },
      evidence: [{ evidence_id: 'evidence.metric.001', evidence_type: 'METRIC_REGISTRY', canonical_reference: 'metric.average.ticket', public_label: 'Ticket médio', authority_version: 'metric-registry/1', checksum: HASH_A }],
      warnings: [], risks: [],
    },
  }
}

async function mockBase(page: Page) {
  await page.route('**/api/v1/**', route => route.fulfill({ json: user }))
}

test('server guard exposes no route or request in LEGACY_ONLY', async ({ page }) => {
  let requests = 0
  await authenticate(page); await mockBase(page)
  await page.route('**/api/v2/dashboard-ai/**', route => { requests += 1; return route.fulfill({ json: readyProposal() }) })
  await page.goto('/dashboard/v2/new')
  if (aiMode === 'LEGACY_ONLY') {
    await expect(page.getByRole('heading', { name: '404' })).toBeVisible()
    expect(requests).toBe(0)
  } else {
    await expect(page.getByTestId('dashboard-ai-wizard')).toBeVisible()
  }
})

test('wizard renders governed evidence and structural placeholders without fake facts', async ({ page }) => {
  await authenticate(page); await mockBase(page)
  await page.route('**/api/v2/dashboard-ai/proposals', route => route.fulfill({ status: 201, json: readyProposal() }))
  await page.goto('/dashboard/v2/new')
  if (aiMode === 'LEGACY_ONLY') {
    await expect(page.getByRole('heading', { name: '404' })).toBeVisible()
    return
  }
  await page.getByRole('button', { name: 'Gerar proposta' }).click()
  await expect(page.getByText('Pronta para revisão humana')).toBeVisible()
  await expect(page.getByTestId('dashboard-ai-blueprint-preview')).toBeVisible()
  await expect(page.getByText('Ticket médio', { exact: false }).first()).toBeVisible()
  await expect(page.getByText('Raciocínio interno do modelo não é armazenado nem exibido.')).toBeVisible()
  await expect(page.getByTestId('dashboard-ai-blueprint-preview')).not.toContainText('400.00')
  await expect(page.getByRole('button', { name: 'Aceitar esta versão' })).toBeVisible()
})

test('typed clarification must be answered before a reviewable proposal appears', async ({ page }) => {
  await authenticate(page); await mockBase(page)
  const needs = { ...readyProposal('NEEDS_CLARIFICATION', 4), latest: undefined, clarification: { proposal_id: 'proposal.ai.001', proposal_version: 1, lock_version: 1, expires_at: '2026-08-05T12:15:00Z', questions: [{ question_id: 'question.revenue.001', kind: 'METRIC', prompt: 'Você quer faturamento comercial ou bruto?', allow_multiple: false, options: [{ option_id: 'option.commercial', label: 'Faturamento comercial', description: 'Receita comercial governada.', canonical_reference: 'metric.revenue' }, { option_id: 'option.gross', label: 'Faturamento bruto', description: 'Total bruto governado.', canonical_reference: 'metric.gross.revenue' }] }] } }
  await page.route('**/api/v2/dashboard-ai/proposals', route => route.fulfill({ status: 201, json: needs }))
  await page.route('**/api/v2/dashboard-ai/proposals/*/clarifications', route => route.fulfill({ json: readyProposal() }))
  await page.goto('/dashboard/v2/new')
  if (aiMode === 'LEGACY_ONLY') {
    await expect(page.getByRole('heading', { name: '404' })).toBeVisible()
    return
  }
  await page.getByRole('textbox', { name: 'Objetivo', exact: true }).fill('Criar painel de faturamento')
  await page.getByRole('button', { name: 'Gerar proposta' }).click()
  await expect(page.getByTestId('dashboard-ai-clarification')).toBeVisible()
  await page.getByRole('button', { name: /Faturamento comercial/ }).click()
  await expect(page.getByText('Pronta para revisão humana')).toBeVisible()
})

test('human revision appends a new immutable proposal version', async ({ page }) => {
  await authenticate(page); await mockBase(page)
  const first = readyProposal()
  const second = { ...readyProposal('READY_FOR_REVIEW', 11), current_version: 2, latest: { ...readyProposal().latest!, version: 2 } }
  await page.route('**/api/v2/dashboard-ai/proposals', route => route.fulfill({ status: 201, json: first }))
  await page.route('**/api/v2/dashboard-ai/proposals/proposal.ai.001/revise', route => route.fulfill({ json: second }))
  await page.goto('/dashboard/v2/new')
  if (aiMode === 'LEGACY_ONLY') {
    await expect(page.getByRole('heading', { name: '404' })).toBeVisible()
    return
  }
  await page.getByRole('button', { name: 'Gerar proposta' }).click()
  await page.getByRole('button', { name: 'Gerar nova versão' }).click()
  await expect(page.getByText('v2 · CAS 11')).toBeVisible()
})

test('accept and apply are separate human actions and only the second creates DRAFT', async ({ page }) => {
  await authenticate(page); await mockBase(page)
  let state = readyProposal()
  let accepts = 0, applies = 0
  await page.route('**/api/v2/dashboard-ai/proposals', route => route.fulfill({ status: 201, json: state }))
  await page.route('**/api/v2/dashboard-ai/proposals/proposal.ai.001', route => route.fulfill({ json: state }))
  await page.route('**/api/v2/dashboard-ai/proposals/proposal.ai.001/accept', route => { accepts += 1; state = readyProposal('ACCEPTED', 7); return route.fulfill({ json: { decision_id: 'decision.ai.001' } }) })
  await page.route('**/api/v2/dashboard-ai/proposals/proposal.ai.001/apply', route => { applies += 1; state = { ...readyProposal('APPLIED', 9), applied_dashboard_id: 'dashboard.ai.001', applied_revision_id: 'revision.ai.001' }; return route.fulfill({ json: { proposal_id: 'proposal.ai.001', proposal_version: 1, status: 'APPLIED', dashboard_id: 'dashboard.ai.001', revision_id: 'revision.ai.001', replayed: false } }) })
  await page.goto('/dashboard/v2/new')
  if (aiMode === 'LEGACY_ONLY' || aiMode === 'AI_PROPOSAL_PREVIEW') {
    await expect(page.getByRole('heading', { name: '404' })).toBeVisible()
    return
  }
  await page.getByRole('button', { name: 'Gerar proposta' }).click()
  await page.getByRole('button', { name: 'Aceitar esta versão' }).click()
  await expect.poll(() => accepts).toBe(1)
  expect(applies).toBe(0)
  await expect(page.getByRole('heading', { name: '4. Aplicação separada' })).toBeVisible()
  await page.getByRole('button', { name: 'Confirmar e criar DRAFT' }).click()
  await expect.poll(() => applies).toBe(1)
  await expect(page.getByText('DRAFT criado. Nenhuma publicação ou aprovação foi realizada.')).toBeVisible()
})
