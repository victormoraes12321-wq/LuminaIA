import { getApiBase } from '@/lib/utils'
import type {
  DashboardDetailResponseV2,
  DashboardListItemResponseV2,
  DashboardPublicationV2,
  DashboardRevisionRecordV2,
  DashboardRuntimeResultV2,
} from '@/types/dashboard_backend_v2'
import type {
  DashboardSideChatContextV2,
  DashboardSideChatModeV2,
} from '@/types/dashboard_ui_sidechat_v2'
import type { DashboardSemanticPatchV2, DashboardVisualPatchV2 } from '@/types/dashboard_blueprint_v2'

export class DashboardApiErrorV2 extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.name = 'DashboardApiErrorV2'
    this.status = status
    this.code = code
  }
}

interface ApiErrorPayload {
  readonly detail?: { readonly code?: string; readonly message?: string }
  readonly error?: { readonly code?: string; readonly message?: string }
}

async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController()
  const timeoutId = globalThis.setTimeout(() => controller.abort('DASHBOARD_REQUEST_TIMEOUT'), 60_000)
  const forwardAbort = () => controller.abort(init.signal?.reason)
  if (init.signal?.aborted) forwardAbort()
  else init.signal?.addEventListener('abort', forwardAbort, { once: true })
  try {
    const response = await fetch(`${getApiBase()}${path}`, {
      ...init,
      signal: controller.signal,
      credentials: 'include',
      cache: 'no-store',
      headers: {
        Accept: 'application/json',
        'X-Correlation-ID': globalThis.crypto.randomUUID(),
        ...(init.body ? { 'Content-Type': 'application/json' } : {}),
        ...init.headers,
      },
    })
    if (!response.ok) {
      const payload = await response.json().catch(() => ({})) as ApiErrorPayload
      throw new DashboardApiErrorV2(
        response.status,
        payload.detail?.code ?? payload.error?.code ?? `HTTP_${response.status}`,
        payload.detail?.message ?? payload.error?.message ?? 'Não foi possível concluir a operação.',
      )
    }
    if (response.status === 204) return undefined as T
    return response.json() as Promise<T>
  } finally {
    globalThis.clearTimeout(timeoutId)
    init.signal?.removeEventListener('abort', forwardAbort)
  }
}

export function createDashboardIdempotencyKey(): string {
  return globalThis.crypto.randomUUID()
}

export function listDashboardsV2(signal?: AbortSignal): Promise<readonly DashboardListItemResponseV2[]> {
  return requestJson('/api/v2/dashboards?limit=50', { signal })
}

export function getDashboardV2(dashboardId: string, signal?: AbortSignal): Promise<DashboardDetailResponseV2> {
  return requestJson(`/api/v2/dashboards/${encodeURIComponent(dashboardId)}`, { signal })
}

export interface DashboardRuntimeRequestPayloadV2 {
  readonly publication_id?: string
  readonly blueprint_checksum?: string
  readonly filters: readonly { readonly filter_id: string; readonly values: readonly (string | number | boolean)[] }[]
  readonly interactions: readonly {
    readonly interaction_id: string
    readonly action: 'CROSS_FILTER' | 'DRILLDOWN' | 'RESET' | 'SORTING' | 'PAGINATION' | 'PROVENANCE' | 'EXPAND'
    readonly source_widget_id: string
    readonly target_widget_id?: string
  }[]
  readonly requested_widget_ids: readonly string[]
  readonly deadline_ms: number
  readonly allow_partial: boolean
}

export function executeDashboardV2(
  dashboardId: string,
  payload: DashboardRuntimeRequestPayloadV2,
  idempotencyKey: string,
  signal?: AbortSignal,
): Promise<DashboardRuntimeResultV2> {
  return requestJson(`/api/v2/dashboards/${encodeURIComponent(dashboardId)}/runtime/execute`, {
    method: 'POST',
    headers: { 'Idempotency-Key': idempotencyKey },
    body: JSON.stringify(payload),
    signal,
  })
}

export function applyVisualPatchV2(
  dashboardId: string,
  patch: DashboardVisualPatchV2,
  expectedDashboardLockVersion: number,
  expectedRevisionLockVersion: number,
  reason: string,
  idempotencyKey: string,
  signal?: AbortSignal,
): Promise<DashboardRevisionRecordV2> {
  return requestJson(`/api/v2/dashboards/${encodeURIComponent(dashboardId)}/patches/visual`, {
    method: 'POST',
    headers: { 'Idempotency-Key': idempotencyKey },
    body: JSON.stringify({
      patch,
      expected_dashboard_lock_version: expectedDashboardLockVersion,
      expected_revision_lock_version: expectedRevisionLockVersion,
      reason,
    }),
    signal,
  })
}

export function applySemanticPatchV2(
  dashboardId: string,
  patch: DashboardSemanticPatchV2,
  expectedDashboardLockVersion: number,
  expectedRevisionLockVersion: number,
  reason: string,
  idempotencyKey: string,
  signal?: AbortSignal,
): Promise<DashboardRevisionRecordV2> {
  return requestJson(`/api/v2/dashboards/${encodeURIComponent(dashboardId)}/patches/semantic`, {
    method: 'POST',
    headers: { 'Idempotency-Key': idempotencyKey },
    body: JSON.stringify({ patch, expected_dashboard_lock_version: expectedDashboardLockVersion, expected_revision_lock_version: expectedRevisionLockVersion, reason }),
    signal,
  })
}

export function submitDashboardReviewV2(dashboardId: string, revisionId: string, expectedLockVersion: number, comment: string, idempotencyKey: string, signal?: AbortSignal): Promise<void> {
  return requestJson(`/api/v2/dashboards/${encodeURIComponent(dashboardId)}/review`, { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey }, body: JSON.stringify({ action: 'SUBMITTED', revision_id: revisionId, expected_dashboard_lock_version: expectedLockVersion, comment }), signal })
}

export function approveDashboardV2(dashboardId: string, revisionId: string, expectedLockVersion: number, comment: string, idempotencyKey: string, signal?: AbortSignal): Promise<unknown> {
  return requestJson(`/api/v2/dashboards/${encodeURIComponent(dashboardId)}/approve`, { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey }, body: JSON.stringify({ decision: 'APPROVED', revision_id: revisionId, expected_dashboard_lock_version: expectedLockVersion, comment }), signal })
}

export function rejectDashboardV2(dashboardId: string, revisionId: string, expectedLockVersion: number, comment: string, idempotencyKey: string, signal?: AbortSignal): Promise<void> {
  return requestJson(`/api/v2/dashboards/${encodeURIComponent(dashboardId)}/reject`, { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey }, body: JSON.stringify({ decision: 'REJECTED', revision_id: revisionId, expected_dashboard_lock_version: expectedLockVersion, comment }), signal })
}

export function requestDashboardChangesV2(dashboardId: string, revisionId: string, expectedLockVersion: number, comment: string, idempotencyKey: string, signal?: AbortSignal): Promise<void> {
  return requestJson(`/api/v2/dashboards/${encodeURIComponent(dashboardId)}/review`, { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey }, body: JSON.stringify({ action: 'CHANGES_REQUESTED', revision_id: revisionId, expected_dashboard_lock_version: expectedLockVersion, comment }), signal })
}

export function publishDashboardV2(dashboardId: string, revisionId: string, expectedLockVersion: number, expectedGeneration: number, publicationVersion: string, idempotencyKey: string, signal?: AbortSignal): Promise<unknown> {
  return requestJson(`/api/v2/dashboards/${encodeURIComponent(dashboardId)}/publish`, { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey }, body: JSON.stringify({ revision_id: revisionId, expected_dashboard_lock_version: expectedLockVersion, expected_active_generation: expectedGeneration, publication_version: publicationVersion, confirmation: 'PUBLISH_APPROVED_REVISION' }), signal })
}

export function rollbackDashboardV2(dashboardId: string, publicationId: string, expectedLockVersion: number, expectedGeneration: number, publicationVersion: string, reason: string, idempotencyKey: string, signal?: AbortSignal): Promise<unknown> {
  return requestJson(`/api/v2/dashboards/${encodeURIComponent(dashboardId)}/rollback`, { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey }, body: JSON.stringify({ target_publication_id: publicationId, expected_dashboard_lock_version: expectedLockVersion, expected_active_generation: expectedGeneration, publication_version: publicationVersion, confirmation: 'CREATE_ROLLBACK_PUBLICATION', reason }), signal })
}

export function cloneDashboardV2(dashboardId: string, canonicalName: string, title: string, description: string, reason: string, idempotencyKey: string, signal?: AbortSignal): Promise<unknown> {
  return requestJson(`/api/v2/dashboards/${encodeURIComponent(dashboardId)}/clone`, { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey }, body: JSON.stringify({ canonical_name: canonicalName, title, description, reason }), signal })
}

export function listDashboardRevisionsV2(dashboardId: string, signal?: AbortSignal): Promise<readonly DashboardRevisionRecordV2[]> {
  return requestJson(`/api/v2/dashboards/${encodeURIComponent(dashboardId)}/revisions`, { signal })
}

export function listDashboardPublicationsV2(dashboardId: string, signal?: AbortSignal): Promise<readonly DashboardPublicationV2[]> {
  return requestJson(`/api/v2/dashboards/${encodeURIComponent(dashboardId)}/publications`, { signal })
}

export function addDashboardCollaboratorV2(dashboardId: string, userReference: string, role: string, signal?: AbortSignal): Promise<DashboardDetailResponseV2['collaborators'][number]> {
  return requestJson(`/api/v2/dashboards/${encodeURIComponent(dashboardId)}/collaborators`, { method: 'POST', body: JSON.stringify({ user_reference: userReference, role }), signal })
}

export function updateDashboardCollaboratorV2(dashboardId: string, collaboratorId: string, role: string, expectedLockVersion: number, signal?: AbortSignal): Promise<DashboardDetailResponseV2['collaborators'][number]> {
  return requestJson(`/api/v2/dashboards/${encodeURIComponent(dashboardId)}/collaborators/${encodeURIComponent(collaboratorId)}`, { method: 'PATCH', body: JSON.stringify({ role, expected_lock_version: expectedLockVersion }), signal })
}

export function removeDashboardCollaboratorV2(dashboardId: string, collaboratorId: string, expectedLockVersion: number, signal?: AbortSignal): Promise<void> {
  const query = new URLSearchParams({ expected_lock_version: String(expectedLockVersion) })
  return requestJson(`/api/v2/dashboards/${encodeURIComponent(dashboardId)}/collaborators/${encodeURIComponent(collaboratorId)}?${query}`, { method: 'DELETE', signal })
}

export interface DashboardSideChatApiResponseV2 {
  readonly status?: string
  readonly resposta_direta?: string
  readonly ia_analise?: string
  readonly mensagem?: string
  readonly session_id?: string
  readonly context_version?: number
  readonly dashboard_action?: unknown
}

export interface DashboardSideChatStreamObserverV2 {
  readonly onReceiving?: () => void
}

export function askDashboardSideChatV2(
  question: string,
  mode: DashboardSideChatModeV2,
  context: DashboardSideChatContextV2,
  tenantId: string,
  signal?: AbortSignal,
  observer?: DashboardSideChatStreamObserverV2,
): Promise<DashboardSideChatApiResponseV2> {
  const controller = new AbortController()
  const timeoutId = globalThis.setTimeout(() => controller.abort('DASHBOARD_SIDE_CHAT_TIMEOUT'), 60_000)
  const forwardAbort = () => controller.abort(signal?.reason)
  if (signal?.aborted) forwardAbort()
  else signal?.addEventListener('abort', forwardAbort, { once: true })

  return fetch(`${getApiBase()}/api/v1/query/`, {
    method: 'POST',
    credentials: 'include',
    cache: 'no-store',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-Correlation-ID': globalThis.crypto.randomUUID(),
    },
    body: JSON.stringify({
      pergunta: question,
      tenant_id: tenantId,
      session_id: context.conversation_session_id,
      expected_context_version: context.context_version,
      client_message_id: createDashboardIdempotencyKey(),
      dashboard_context: context,
      history: [{ role: 'assistant', content: `Modo governado do side chat: ${mode}` }],
      mode: 'analytical',
      use_new_pipeline: true,
    }),
    signal: controller.signal,
  }).then(async response => {
    if (!response.ok) {
      const payload = await response.json().catch(() => ({})) as ApiErrorPayload
      throw new DashboardApiErrorV2(
        response.status,
        payload.detail?.code ?? payload.error?.code ?? `HTTP_${response.status}`,
        payload.detail?.message ?? payload.error?.message ?? 'Não foi possível concluir a operação.',
      )
    }

    if (!response.body) {
      observer?.onReceiving?.()
      return response.json() as Promise<DashboardSideChatApiResponseV2>
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8', { fatal: true })
    let envelope = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      observer?.onReceiving?.()
      envelope += decoder.decode(value, { stream: true })
      if (envelope.length > 2_000_000) {
        await reader.cancel('DASHBOARD_SIDE_CHAT_RESPONSE_TOO_LARGE')
        throw new DashboardApiErrorV2(413, 'RESPONSE_TOO_LARGE', 'A resposta do side chat excedeu o limite seguro.')
      }
    }
    envelope += decoder.decode()
    return JSON.parse(envelope) as DashboardSideChatApiResponseV2
  }).finally(() => {
    globalThis.clearTimeout(timeoutId)
    signal?.removeEventListener('abort', forwardAbort)
  })
}
