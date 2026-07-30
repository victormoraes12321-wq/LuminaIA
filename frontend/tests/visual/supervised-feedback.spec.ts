import { expect, test, type Page, type Route } from '@playwright/test'

import { buildComparisonResponse } from '../fixtures/comparisonResponse'


const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:3100'
const tenantId = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'
const consultaId = '11111111-1111-4111-8111-111111111113'
const adminId = '11111111-1111-4111-8111-111111111114'
const responseNodeId = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1'
const queryNodeId = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb1'
const sessionId = 'lumina-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
const responseChecksum = 'a'.repeat(64)
const feedbackId = 'f0000000-0000-4000-8000-000000000001'

function user(role: 'CONSULTA' | 'ADMIN') {
  return {
    id: role === 'ADMIN' ? adminId : consultaId,
    nome: role === 'ADMIN' ? 'Admin Lumina' : 'Consulta Lumina',
    email: `${role.toLowerCase()}@lumina.test`,
    role,
    tenant_id: tenantId,
    must_change_password: false,
  }
}

async function authenticate(page: Page, role: 'CONSULTA' | 'ADMIN' = 'CONSULTA') {
  const current = user(role)
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url')
  const payload = Buffer.from(JSON.stringify({
    sub: current.id,
    tenant_id: tenantId,
    role,
    must_change_password: false,
    exp: Math.floor(Date.now() / 1000) + 3600,
  })).toString('base64url')
  await page.context().addCookies([{
    name: 'lumina-token',
    value: `${header}.${payload}.feedback-test`,
    url: baseURL,
    httpOnly: true,
    sameSite: 'Lax',
  }])
}

function queryResponse() {
  const base = buildComparisonResponse('period', 'CONSULTA')
  return {
    ...base,
    query_id: 'cccccccc-cccc-4ccc-8ccc-ccccccccccc1',
    request_id: 'cccccccc-cccc-4ccc-8ccc-ccccccccccc1',
    session_id: sessionId,
    query_node_id: queryNodeId,
    response_node_id: responseNodeId,
    feedback_target_checksum: responseChecksum,
    context_version: 1,
    context_epoch: 0,
    conversation_status: 'ACTIVE',
  }
}

function feedbackRecord(lifecycle = 'TRIAGED', role: 'CONSULTA' | 'ADMIN' = 'CONSULTA') {
  return {
    feedback_id: feedbackId,
    tenant_id: tenantId,
    user_id: consultaId,
    target: {
      response_node_id: responseNodeId,
      session_id: sessionId,
      response_checksum: responseChecksum,
      query_node_id: queryNodeId,
      response_contract_version: 'lumina.query-response/1.0',
    },
    category: 'INCORRECT_VALUE',
    correction: null,
    explanation: 'O valor correto precisa ser conferido.',
    lifecycle,
    triage: {
      triage_id: 'f1000000-0000-4000-8000-000000000001',
      category: 'INCORRECT_VALUE',
      severity: 'HIGH',
      priority: 'P2',
      review_queue: 'DATA_INTEGRITY',
      duplicate_fingerprint: 'b'.repeat(64),
      suspected_security: false,
      suspected_formula_conflict: true,
      suspected_tenant_issue: false,
      needs_specialist: true,
      classification_confidence: 100,
      rule_ids: ['TRIAGE_OFFICIAL_DATA_P2'],
      warnings: [],
      checksum: 'c'.repeat(64),
    },
    reviewer_user_id: lifecycle === 'IN_REVIEW' ? (role === 'ADMIN' ? adminId : null) : null,
    review_decision: null,
    duplicate_group: 'b'.repeat(64),
    redaction_manifest_id: 'f2000000-0000-4000-8000-000000000001',
    lock_version: lifecycle === 'IN_REVIEW' ? 1 : 0,
    checksum: 'd'.repeat(64),
    created_at: '2026-07-29T12:00:00Z',
    updated_at: '2026-07-29T12:00:00Z',
    contract_version: 'lumina.supervised-feedback/1.0',
  }
}

async function commonRoutes(
  page: Page,
  role: 'CONSULTA' | 'ADMIN',
  feedbackHandler?: (route: Route) => Promise<void>,
) {
  await page.route('**/api/v2/**', async route => {
    if (feedbackHandler) return feedbackHandler(route)
    return route.fulfill({ json: [] })
  })
  await page.route('**/api/v1/**', async route => {
    const url = route.request().url()
    if (url.includes('/auth/session')) return route.fulfill({ json: user(role) })
    if (url.includes('/query/history') || url.includes('/query/favorites')) {
      return route.fulfill({ json: [] })
    }
    if (url.includes('/dashboard-preferences/default')) {
      return route.fulfill({ json: { basis: 'liquido', format: 'ambos', instructions: '' } })
    }
    if (url.endsWith('/api/v1/query/')) return route.fulfill({ json: queryResponse() })
    return route.fulfill({ json: { ok: true } })
  })
}

async function ask(page: Page) {
  await page.goto('/dashboard')
  const input = page.getByRole('textbox')
  await input.fill('Compare o faturamento de junho e julho')
  await input.press('Enter')
  await expect(page.getByText('Esta resposta ajudou?')).toBeVisible()
}

test('positive feedback sends only target references and no response body', async ({ page }) => {
  const writes: Array<Record<string, unknown>> = []
  await commonRoutes(page, 'CONSULTA', async route => {
    writes.push(route.request().postDataJSON() as Record<string, unknown>)
    return route.fulfill({ status: 201, json: feedbackRecord() })
  })
  await authenticate(page)
  await ask(page)
  await page.getByRole('button', { name: 'Marcar resposta como correta' }).click()
  await expect(page.getByText('Avaliação registrada para revisão.')).toBeVisible()
  expect(writes).toHaveLength(1)
  expect(writes[0]).toMatchObject({
    target: {
      response_node_id: responseNodeId,
      session_id: sessionId,
      response_checksum: responseChecksum,
    },
    category: 'POSITIVE',
  })
  expect(JSON.stringify(writes[0])).not.toContain('O faturamento')
  expect(JSON.stringify(writes[0])).not.toContain('chart_data')
})

test('partial feedback requires explanation and sends structured correction', async ({ page }) => {
  const writes: Array<Record<string, unknown>> = []
  await commonRoutes(page, 'CONSULTA', async route => {
    writes.push(route.request().postDataJSON() as Record<string, unknown>)
    return route.fulfill({ status: 201, json: feedbackRecord() })
  })
  await authenticate(page)
  await ask(page)
  await page.getByRole('button', { name: 'Marcar resposta como parcialmente correta' }).click()
  await page.getByRole('button', { name: 'Enviar avaliação' }).click()
  await expect(page.getByText('Conte brevemente o que precisa ser corrigido.')).toBeVisible()
  await page.getByPlaceholder(/o período correto/i).fill('O período correto era julho de 2026.')
  await page.getByRole('button', { name: 'Enviar avaliação' }).click()
  await expect.poll(() => writes.length).toBe(1)
  expect(writes[0]).toMatchObject({
    category: 'PARTIALLY_CORRECT',
    correction: {
      items: [{ kind: 'FREE_TEXT_EXPLANATION' }],
    },
  })
})

test('owner history lists and withdraws eligible feedback', async ({ page }) => {
  let withdrawn = false
  await commonRoutes(page, 'CONSULTA', async route => {
    const url = route.request().url()
    if (url.endsWith('/withdraw')) {
      withdrawn = true
      return route.fulfill({ json: feedbackRecord('WITHDRAWN') })
    }
    return route.fulfill({ json: [feedbackRecord()] })
  })
  await authenticate(page)
  await page.goto('/dashboard/feedback')
  await expect(page.getByRole('heading', { name: 'Minhas avaliações' })).toBeVisible()
  await expect(page.getByText('INCORRECT_VALUE')).toBeVisible()
  await page.getByRole('button', { name: 'Retirar' }).click()
  await expect.poll(() => withdrawn).toBe(true)
})

test('owner answers a governed request for more information', async ({ page }) => {
  let answered = false
  await commonRoutes(page, 'CONSULTA', async route => {
    const url = route.request().url()
    if (url.endsWith('/information-response')) {
      answered = true
      return route.fulfill({ json: feedbackRecord('IN_REVIEW') })
    }
    return route.fulfill({ json: [feedbackRecord('NEEDS_INFORMATION')] })
  })
  await authenticate(page)
  await page.goto('/dashboard/feedback')
  await page.getByPlaceholder('Informação complementar').fill(
    'A referência é o fechamento mensal homologado.',
  )
  await page.getByRole('button', { name: 'Responder' }).click()
  await expect.poll(() => answered).toBe(true)
})

test('admin review queue assigns and records a human decision', async ({ page }) => {
  let assigned = false
  let reviewed = false
  await commonRoutes(page, 'ADMIN', async route => {
    const url = route.request().url()
    if (url.endsWith('/reviewer')) {
      assigned = true
      return route.fulfill({ json: feedbackRecord('IN_REVIEW', 'ADMIN') })
    }
    if (url.endsWith('/review')) {
      reviewed = true
      return route.fulfill({
        json: {
          review_id: 'f3000000-0000-4000-8000-000000000001',
          feedback_id: feedbackId,
          reviewer_user_id: adminId,
          decision: 'INCORRECT',
          rationale: 'A evidência estrutural confirma o erro.',
          evidence: [],
          expected_lock_version: 1,
          created_at: '2026-07-29T12:10:00Z',
          checksum: 'e'.repeat(64),
        },
      })
    }
    return route.fulfill({ json: [assigned ? feedbackRecord('IN_REVIEW', 'ADMIN') : feedbackRecord()] })
  })
  await authenticate(page, 'ADMIN')
  await page.goto('/dashboard/admin/feedback')
  await expect(page.getByRole('heading', { name: 'Revisão de feedback' })).toBeVisible()
  await page.getByRole('button', { name: 'Assumir' }).click()
  await expect.poll(() => assigned).toBe(true)
  await page.getByLabel('Justificativa técnica').fill('A evidência estrutural confirma o erro.')
  await page.getByRole('button', { name: 'Incorreta' }).click()
  await expect.poll(() => reviewed).toBe(true)
})

test('admin curates a candidate and creates a governed dataset snapshot', async ({ page }) => {
  let candidateStatus = 'CANDIDATE'
  let snapshotCreated = false
  const exampleId = 'f4000000-0000-4000-8000-000000000001'
  await commonRoutes(page, 'ADMIN', async route => {
    const url = route.request().url()
    const method = route.request().method()
    if (url.includes('/training-candidates/') && url.endsWith('/validate')) {
      candidateStatus = 'VALIDATED'
      return route.fulfill({ json: { ok: true } })
    }
    if (url.includes('/training-candidates')) {
      return route.fulfill({
        json: [{
          candidate_id: 'f5000000-0000-4000-8000-000000000001',
          feedback_id: feedbackId,
          status: candidateStatus,
          quality_status: 'VALID',
          quality_rule_ids: ['HUMAN_REVIEW_PRESENT'],
          lock_version: candidateStatus === 'VALIDATED' ? 1 : 0,
          checksum: 'f'.repeat(64),
        }],
      })
    }
    if (url.includes('/training-examples')) {
      return route.fulfill({
        json: [{
          example_id: exampleId,
          candidate_id: 'f5000000-0000-4000-8000-000000000001',
          domain: 'SALES',
          quality_score: 100,
          checksum: '1'.repeat(64),
        }],
      })
    }
    if (url.includes('/feedback/datasets') && method === 'POST') {
      snapshotCreated = true
      return route.fulfill({ status: 201, json: { ok: true } })
    }
    if (url.includes('/feedback/datasets')) return route.fulfill({ json: [] })
    if (url.includes('/review/queue')) return route.fulfill({ json: [] })
    return route.fulfill({ json: [] })
  })
  await authenticate(page, 'ADMIN')
  await page.goto('/dashboard/admin/feedback')
  await page.getByRole('tab', { name: 'Curadoria' }).click()
  await expect(page.getByRole('heading', { name: 'Candidatos' })).toBeVisible()
  await page.getByRole('button', { name: 'Validar' }).click()
  await expect.poll(() => candidateStatus).toBe('VALIDATED')
  await page.getByText('SALES · qualidade 100').click()
  await page.getByRole('button', { name: 'Criar snapshot' }).click()
  await expect.poll(() => snapshotCreated).toBe(true)
})
