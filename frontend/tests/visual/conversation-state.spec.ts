import { expect, test, type Page, type Route } from '@playwright/test'

import { buildComparisonResponse } from '../fixtures/comparisonResponse'


const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:3100'
const tenantId = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'
const userId = '11111111-1111-4111-8111-111111111113'
const serverSessionId = 'lumina-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
const responseNode1 = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1'
const responseNode2 = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2'

const user = {
  id: userId,
  nome: 'Consulta Lumina',
  email: 'consulta@luminaai.demo',
  role: 'CONSULTA',
  tenant_id: tenantId,
  must_change_password: false,
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
    value: `${header}.${payload}.conversation-test`,
    url: baseURL,
    httpOnly: true,
    sameSite: 'Lax',
  }])
}

async function openSidebarIfCollapsed(page: Page) {
  const toggle = page.getByRole('button', { name: 'Toggle sidebar' })
  if (await toggle.isVisible()) await toggle.click()
}

function responseForTurn(turn: number) {
  const queryId = `cccccccc-cccc-4ccc-8ccc-ccccccccccc${turn}`
  const response = buildComparisonResponse('period', 'CONSULTA')
  return {
    ...response,
    query_id: queryId,
    request_id: queryId,
    analytical_contract: response.analytical_contract
      ? {
          ...response.analytical_contract,
          contract: {
            ...response.analytical_contract.contract,
            request_id: queryId,
          },
        }
      : null,
    session_id: serverSessionId,
    query_node_id: `bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb${turn}`,
    response_node_id: turn === 1 ? responseNode1 : responseNode2,
    parent_id: turn === 1 ? null : responseNode1,
    context_version: turn,
    context_epoch: 0,
    conversation_status: 'ACTIVE',
    idempotent_replay: false,
    context_relationship: turn === 1 ? 'NEW_TOPIC' : 'REFINEMENT',
    public_context_summary: {
      active_metrics: ['Faturamento comercial'],
      active_periods: [turn === 1 ? 'Junho de 2026' : 'Julho de 2026'],
      inherited_filters: turn === 1 ? [] : ['filial: Centro'],
      active_dimensions: turn >= 4 ? ['Produto'] : [],
      active_comparison: turn >= 3 ? 'PERIOD_VS_PERIOD' : null,
      replaced_fields: turn === 2 ? ['active_time_windows'] : [],
      removed_fields: [],
      reset: false,
      clarification_required: false,
    },
  }
}

async function installCommonRoutes(page: Page, queryHandler: (route: Route) => Promise<void>) {
  await page.route('**/api/v1/**', async route => {
    const url = route.request().url()
    if (url.includes('/auth/session')) return route.fulfill({ json: user })
    if (url.includes('/auth/logout')) {
      return route.fulfill({
        json: { ok: true },
        headers: { 'set-cookie': 'lumina-token=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax' },
      })
    }
    if (url.includes('/query/history') || url.includes('/query/favorites')) {
      return route.fulfill({ json: [] })
    }
    if (url.includes('/dashboard-preferences/default')) {
      return route.fulfill({
        json: { basis: 'liquido', format: 'ambos', instructions: '' },
      })
    }
    if (url.endsWith('/api/v1/query/')) return queryHandler(route)
    return route.fulfill({ json: { ok: true } })
  })
}

test('query continuity uses server session, response parent and context version', async ({ page }) => {
  const payloads: Array<Record<string, unknown>> = []
  await installCommonRoutes(page, async route => {
    payloads.push(route.request().postDataJSON() as Record<string, unknown>)
    return route.fulfill({ json: responseForTurn(payloads.length) })
  })
  await authenticate(page)
  await page.goto('/dashboard')
  const input = page.getByRole('textbox')

  await input.fill('Compare junho e julho de 2026')
  await input.press('Enter')
  await expect.poll(() => payloads.length).toBe(1)

  await input.fill('Agora separe por produto')
  await input.press('Enter')
  await expect.poll(() => payloads.length).toBe(2)

  expect(payloads[0].expected_context_version).toBe(0)
  expect(payloads[0].client_message_id).toMatch(
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
  )
  expect(payloads[1]).toMatchObject({
    session_id: serverSessionId,
    parent_id: responseNode1,
    expected_context_version: 1,
  })
  expect(payloads[1].client_message_id).not.toBe(payloads[0].client_message_id)

  await expect.poll(async () => {
    const stored = await page.evaluate(
      key => window.localStorage.getItem(key),
      `lumina-conversation:${tenantId}:${userId}`,
    )
    return JSON.parse(stored || '{}')
  }).toMatchObject({
      sessionId: serverSessionId,
      contextVersion: 2,
      parentId: responseNode2,
    })
})

test('four-turn context summary remains readable without exposing technical metadata', async ({ page }) => {
  let turn = 0
  await installCommonRoutes(page, async route => {
    turn += 1
    const response = responseForTurn(turn)
    return route.fulfill({
      json: {
        ...response,
        response_node_id: `aaaaaaaa-aaaa-4aaa-8aaa-${turn.toString().padStart(12, '0')}`,
        context_resolution_metadata: {
          patch_fingerprint: 'must-not-be-rendered',
        },
      },
    })
  })
  await authenticate(page)
  await page.goto('/dashboard')
  const input = page.getByRole('textbox')
  const questions = [
    'Faturamento de junho de 2026 da filial Centro',
    'E em julho?',
    'Agora compare os dois meses',
    'Separe por produto',
  ]
  for (const [index, question] of questions.entries()) {
    await input.fill(question)
    await input.press('Enter')
    await expect.poll(() => turn).toBe(index + 1)
  }

  const summaries = page.getByTestId('public-context-summary')
  await expect(summaries.last()).toContainText('Contexto mantido')
  await expect(summaries.last()).toContainText('Faturamento comercial')
  await expect(summaries.last()).toContainText('Produto')
  await expect(page.getByText('must-not-be-rendered')).toHaveCount(0)
})

test('automatic network recovery reuses the same client message id', async ({ page }) => {
  const payloads: Array<Record<string, unknown>> = []
  await installCommonRoutes(page, async route => {
    payloads.push(route.request().postDataJSON() as Record<string, unknown>)
    if (payloads.length === 1) {
      return route.fulfill({ status: 503, json: { detail: { message: 'retry' } } })
    }
    return route.fulfill({ json: responseForTurn(1) })
  })
  await authenticate(page)
  await page.goto('/dashboard')
  const input = page.getByRole('textbox')
  await input.fill('Faturamento de julho de 2026')
  await input.press('Enter')

  await expect.poll(() => payloads.length, { timeout: 10_000 }).toBe(2)
  expect(payloads[0].client_message_id).toBe(payloads[1].client_message_id)
  expect(payloads[0].session_id).toBe(payloads[1].session_id)
})

test('logo reset clears the visible conversation and starts a fresh binding', async ({ page }) => {
  const payloads: Array<Record<string, unknown>> = []
  await installCommonRoutes(page, async route => {
    payloads.push(route.request().postDataJSON() as Record<string, unknown>)
    return route.fulfill({ json: responseForTurn(payloads.length) })
  })
  await authenticate(page)
  await page.goto('/dashboard')
  const input = page.getByRole('textbox')
  await input.fill('Faturamento de junho')
  await input.press('Enter')
  await expect.poll(() => payloads.length).toBe(1)
  await expect.poll(async () => {
    const stored = await page.evaluate(
      key => window.localStorage.getItem(key),
      `lumina-conversation:${tenantId}:${userId}`,
    )
    return JSON.parse(stored || '{}').sessionId
  }).toBe(serverSessionId)

  await openSidebarIfCollapsed(page)
  await page.getByRole('link', { name: /LuminaAI/ }).click()
  await expect(page.locator('main').getByText('Faturamento de junho', { exact: true })).toHaveCount(0)
  await expect.poll(async () => {
    const stored = await page.evaluate(
      key => window.localStorage.getItem(key),
      `lumina-conversation:${tenantId}:${userId}`,
    )
    return JSON.parse(stored || '{}')
  }).toMatchObject({ contextVersion: 0, parentId: null })

  await input.fill('Faturamento de julho')
  await input.press('Enter')
  await expect.poll(() => payloads.length).toBe(2)
  expect(payloads[1].session_id).not.toBe(serverSessionId)
  expect(payloads[1].parent_id).toBeNull()
  expect(payloads[1].expected_context_version).toBe(0)
})

test('logout removes every tenant and user conversation binding', async ({ page }) => {
  await installCommonRoutes(page, async route => route.fulfill({ json: responseForTurn(1) }))
  await authenticate(page)
  await page.goto('/dashboard')
  await page.evaluate(([currentKey]) => {
    window.localStorage.setItem(currentKey, '{"sessionId":"current"}')
    window.localStorage.setItem(
      'lumina-conversation:other-tenant:other-user',
      '{"sessionId":"other"}',
    )
  }, [`lumina-conversation:${tenantId}:${userId}`])

  await openSidebarIfCollapsed(page)
  await page.getByRole('button', { name: 'Sair da conta' }).click()
  await page.waitForURL('**/login')
  const remaining = await page.evaluate(() => Object.keys(window.localStorage)
    .filter(key => key.startsWith('lumina-conversation:')))
  expect(remaining).toEqual([])
})

test('typed version conflict advances only the expected context version', async ({ page }) => {
  const payloads: Array<Record<string, unknown>> = []
  await installCommonRoutes(page, async route => {
    payloads.push(route.request().postDataJSON() as Record<string, unknown>)
    if (payloads.length === 1) {
      return route.fulfill({
        status: 409,
        json: {
          detail: {
            code: 'CONTEXT_VERSION_CONFLICT',
            message: 'A conversa foi atualizada em outra janela.',
            actual_context_version: 7,
          },
        },
      })
    }
    return route.fulfill({ json: { ...responseForTurn(2), context_version: 8 } })
  })
  await authenticate(page)
  await page.goto('/dashboard')
  const input = page.getByRole('textbox')
  await input.fill('Primeira tentativa')
  await input.press('Enter')
  await expect(page.getByText('A conversa foi atualizada em outra janela.').first()).toBeVisible()

  await input.fill('Tentar novamente')
  await input.press('Enter')
  await expect.poll(() => payloads.length).toBe(2)
  expect(payloads[1].expected_context_version).toBe(7)
})

test('expired server session is discarded before the next question', async ({ page }) => {
  const payloads: Array<Record<string, unknown>> = []
  await installCommonRoutes(page, async route => {
    payloads.push(route.request().postDataJSON() as Record<string, unknown>)
    if (payloads.length === 1) {
      return route.fulfill({
        status: 409,
        json: {
          detail: {
            code: 'CONVERSATION_EXPIRED',
            message: 'A conversa expirou.',
            actual_context_version: 2,
          },
        },
      })
    }
    return route.fulfill({ json: responseForTurn(1) })
  })
  await authenticate(page)
  await page.goto('/dashboard')
  const key = `lumina-conversation:${tenantId}:${userId}`
  await page.evaluate(([storageKey, session, parent]) => {
    window.localStorage.setItem(
      storageKey,
      JSON.stringify({ sessionId: session, contextVersion: 2, parentId: parent }),
    )
  }, [key, serverSessionId, responseNode2])
  await page.reload()

  const input = page.getByRole('textbox')
  await input.fill('Consulta expirada')
  await input.press('Enter')
  await expect(page.getByText('A conversa expirou.').first()).toBeVisible()
  await input.fill('Nova conversa')
  await input.press('Enter')
  await expect.poll(() => payloads.length).toBe(2)
  expect(payloads[1].session_id).not.toBe(serverSessionId)
  expect(payloads[1].parent_id).toBeNull()
  expect(payloads[1].expected_context_version).toBe(0)
})
