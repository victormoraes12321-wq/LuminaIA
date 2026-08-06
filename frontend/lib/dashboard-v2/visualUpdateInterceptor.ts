import type { DashboardVisualPatchV2, DashboardPatchOperationV2 } from '@/types/dashboard_blueprint_v2'
import type { DashboardCapabilityBackendV2, DashboardRevisionRecordV2 } from '@/types/dashboard_backend_v2'
import type {
  DashboardSideChatActionResultV2,
  DashboardSideChatActionV2,
  DashboardUiModeV2,
} from '@/types/dashboard_ui_sidechat_v2'

const SEMANTIC_PATH_PARTS = ['/binding_id', '/data_bindings', '/metrics', '/dimensions', '/period', '/comparison', '/filters'] as const

export function isVisualPatchOperationV2(operation: DashboardPatchOperationV2): boolean {
  const allowed = /^\/identity\/(title|description)$/.test(operation.path)
    || /^\/layout\/breakpoints\/\d+\/(items|grid)(\/.*)?$/.test(operation.path)
    || /^\/widgets\/\d+\/(title|formatting|theme_token|visible)(\/.*)?$/.test(operation.path)
  if (!allowed) return false
  return !SEMANTIC_PATH_PARTS.some(part => operation.path.includes(part))
}

export interface DashboardVisualInterceptorInputV2 {
  readonly action: DashboardSideChatActionV2
  readonly dashboard_id: string
  readonly revision: DashboardRevisionRecordV2
  readonly capabilities: readonly DashboardCapabilityBackendV2[]
  readonly mode: DashboardUiModeV2
  readonly backend_revision?: DashboardRevisionRecordV2
}

export function dashboardVisualUpdateInterceptor(
  input: DashboardVisualInterceptorInputV2,
): DashboardSideChatActionResultV2 {
  const { action } = input
  if (action.action_type === 'NO_ACTION') return { outcome: 'NO_OP', message: 'Nenhuma ação visual solicitada.' }
  if (action.action_type === 'BLOCKED') return { outcome: 'BLOCKED', message: action.message }
  if (action.action_type !== 'VISUAL_PATCH_PROPOSAL' && action.action_type !== 'VISUAL_PATCH_APPLY') {
    return { outcome: 'INVALID_ACTION', message: 'A ação não é uma atualização visual.' }
  }
  if (input.mode !== 'V2_SIDE_CHAT' && input.mode !== 'V2_AUTHORING') {
    return { outcome: 'BLOCKED', message: 'Atualização visual indisponível neste modo.' }
  }
  if (!input.capabilities.includes('dashboard:edit_visual')) {
    return { outcome: 'BLOCKED', message: 'Permissão de edição visual ausente.' }
  }
  if (action.dashboard_id !== input.dashboard_id || action.revision_id !== input.revision.revision_id) {
    return { outcome: 'CONFLICT', message: 'A ação pertence a outro dashboard ou revisão.' }
  }
  if (action.semantic_checksum !== input.revision.semantic.checksum) {
    return { outcome: 'FULL_RENDERING_REQUIRED', message: 'A referência semântica mudou e exige recarga governada.' }
  }
  if (action.operations.length === 0) return { outcome: 'NO_OP', message: 'O patch visual está vazio.' }
  if (!action.operations.every(isVisualPatchOperationV2)) {
    return { outcome: 'INVALID_ACTION', message: 'O patch contém operação semântica ou caminho não permitido.' }
  }

  const patch: DashboardVisualPatchV2 = {
    patch_type: 'VISUAL',
    blueprint_id: input.revision.blueprint.identity.blueprint_id,
    base_blueprint_checksum: input.revision.blueprint_checksum,
    base_semantic_checksum: input.revision.semantic.checksum,
    base_visual_revision: input.revision.visual.number,
    target_visual_revision: input.revision.visual.number + 1,
    operations: action.operations,
  }
  if (!input.backend_revision) {
    return { outcome: 'NO_OP', message: 'Preview visual pronto para confirmação.', preview_patch: patch }
  }
  if (input.backend_revision.semantic.checksum !== input.revision.semantic.checksum) {
    return { outcome: 'FULL_RENDERING_REQUIRED', message: 'O backend confirmou mudança semântica; recarga obrigatória.' }
  }
  if (input.backend_revision.revision_id === input.revision.revision_id) {
    return { outcome: 'CONFLICT', message: 'O backend não criou a nova revisão visual.' }
  }
  return {
    outcome: 'UI_MODIFIED',
    message: 'Revisão visual confirmada sem recarregar o resultado analítico.',
    preview_patch: patch,
    revision_id: input.backend_revision.revision_id,
  }
}
