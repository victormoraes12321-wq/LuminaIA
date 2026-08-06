import { getApiBase } from '@/lib/utils'
import type { DashboardAiApplyResultV2, DashboardAiAssistanceRequestV2, DashboardAiProposalV2 } from '@/types/dashboard_ai_assistance_v2'

export class DashboardAiApiErrorV2 extends Error {
  constructor(readonly status: number, readonly code: string, message: string) { super(message); this.name = 'DashboardAiApiErrorV2' }
}

async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${getApiBase()}${path}`, {
    ...init, credentials: 'include', cache: 'no-store',
    headers: { Accept: 'application/json', 'X-Correlation-ID': crypto.randomUUID(), ...(init.body ? { 'Content-Type': 'application/json' } : {}), ...init.headers },
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({})) as { detail?: { code?: string; message?: string } }
    throw new DashboardAiApiErrorV2(response.status, payload.detail?.code ?? `HTTP_${response.status}`, payload.detail?.message ?? 'A assistência não pôde concluir a operação.')
  }
  return response.json() as Promise<T>
}

export function createDashboardAiProposal(payload: DashboardAiAssistanceRequestV2, idempotencyKey: string, signal?: AbortSignal): Promise<DashboardAiProposalV2> {
  return requestJson('/api/v2/dashboard-ai/proposals', { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey }, body: JSON.stringify(payload), signal })
}

export function getDashboardAiProposal(proposalId: string, signal?: AbortSignal): Promise<DashboardAiProposalV2> {
  return requestJson(`/api/v2/dashboard-ai/proposals/${encodeURIComponent(proposalId)}`, { signal })
}

export function answerDashboardAiClarification(proposalId: string, questionId: string, selectedOptionIds: readonly string[], expectedLockVersion: number, signal?: AbortSignal): Promise<DashboardAiProposalV2> {
  return requestJson(`/api/v2/dashboard-ai/proposals/${encodeURIComponent(proposalId)}/clarifications`, { method: 'POST', body: JSON.stringify({ question_id: questionId, selected_option_ids: selectedOptionIds, expected_lock_version: expectedLockVersion }), signal })
}

export function reviseDashboardAiProposal(proposal: DashboardAiProposalV2, instruction: string, idempotencyKey: string, signal?: AbortSignal): Promise<DashboardAiProposalV2> {
  return requestJson(`/api/v2/dashboard-ai/proposals/${encodeURIComponent(proposal.proposal_id)}/revise`, { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey }, body: JSON.stringify({ instruction, expected_proposal_version: proposal.current_version, expected_lock_version: proposal.lock_version, client_request_id: crypto.randomUUID() }), signal })
}

export function decideDashboardAiProposal(proposal: DashboardAiProposalV2, decision: 'accept' | 'reject', comment: string, idempotencyKey: string, signal?: AbortSignal): Promise<unknown> {
  return requestJson(`/api/v2/dashboard-ai/proposals/${encodeURIComponent(proposal.proposal_id)}/${decision}`, { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey }, body: JSON.stringify({ proposal_version: proposal.current_version, expected_lock_version: proposal.lock_version, comment }), signal })
}

export function applyDashboardAiProposal(proposal: DashboardAiProposalV2, idempotencyKey: string, signal?: AbortSignal): Promise<DashboardAiApplyResultV2> {
  return requestJson(`/api/v2/dashboard-ai/proposals/${encodeURIComponent(proposal.proposal_id)}/apply`, { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey }, body: JSON.stringify({ proposal_version: proposal.current_version, expected_lock_version: proposal.lock_version, confirmation: 'APPLY_ACCEPTED_DASHBOARD_AI_PROPOSAL' }), signal })
}

export function cancelDashboardAiProposal(proposal: DashboardAiProposalV2, signal?: AbortSignal): Promise<DashboardAiProposalV2> {
  return requestJson(`/api/v2/dashboard-ai/proposals/${encodeURIComponent(proposal.proposal_id)}/cancel`, { method: 'POST', body: JSON.stringify({ expected_lock_version: proposal.lock_version, confirmation: 'CANCEL_DASHBOARD_AI_PROPOSAL' }), signal })
}
