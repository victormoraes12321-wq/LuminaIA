import type { DashboardPatchOperationV2 } from '@/types/dashboard_blueprint_v2'
import type { DashboardSideChatActionV2 } from '@/types/dashboard_ui_sidechat_v2'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function stringValue(record: Record<string, unknown>, key: string): string | undefined {
  return typeof record[key] === 'string' ? record[key] : undefined
}

function isPrimitive(value: unknown): value is string | number | boolean {
  return typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'
}

function parseOperation(value: unknown): DashboardPatchOperationV2 | undefined {
  if (!isRecord(value)) return undefined
  const operation = stringValue(value, 'operation')
  const path = stringValue(value, 'path')
  if (!operation || !['ADD', 'REPLACE', 'REMOVE', 'MOVE'].includes(operation) || !path?.startsWith('/')) return undefined
  const fromPath = stringValue(value, 'from_path')
  const patchValue = value.value
  if (patchValue !== undefined && patchValue !== null && !isPrimitive(patchValue) && !isRecord(patchValue)) return undefined
  return {
    operation: operation as DashboardPatchOperationV2['operation'],
    path,
    ...(patchValue !== undefined ? { value: patchValue as DashboardPatchOperationV2['value'] } : {}),
    ...(fromPath ? { from_path: fromPath } : {}),
  }
}

export function parseDashboardSideChatActionV2(value: unknown): DashboardSideChatActionV2 | undefined {
  if (!isRecord(value)) return undefined
  const actionType = stringValue(value, 'action_type')
  if (actionType === 'NO_ACTION' || actionType === 'RESET_FILTERS') return { action_type: actionType }
  if (actionType === 'FOCUS_WIDGET') {
    const widgetId = stringValue(value, 'widget_id')
    return widgetId ? { action_type: actionType, widget_id: widgetId } : undefined
  }
  if (actionType === 'OPEN_PROVENANCE') {
    const widgetId = stringValue(value, 'widget_id')
    return { action_type: actionType, ...(widgetId ? { widget_id: widgetId } : {}) }
  }
  if (actionType === 'APPLY_FILTER') {
    const filterId = stringValue(value, 'filter_id')
    const values = value.values
    return filterId && Array.isArray(values) && values.every(isPrimitive)
      ? { action_type: actionType, filter_id: filterId, values }
      : undefined
  }
  if (actionType === 'DRILLDOWN') {
    const interactionId = stringValue(value, 'interaction_id')
    const sourceWidgetId = stringValue(value, 'source_widget_id')
    const canonicalValue = stringValue(value, 'canonical_value')
    return interactionId && sourceWidgetId && canonicalValue
      ? { action_type: actionType, interaction_id: interactionId, source_widget_id: sourceWidgetId, canonical_value: canonicalValue }
      : undefined
  }
  if (actionType === 'BLOCKED') {
    const code = stringValue(value, 'code')
    const message = stringValue(value, 'message')
    return code && message ? { action_type: actionType, code, message } : undefined
  }
  if (actionType === 'VISUAL_PATCH_PROPOSAL' || actionType === 'VISUAL_PATCH_APPLY') {
    const dashboardId = stringValue(value, 'dashboard_id')
    const revisionId = stringValue(value, 'revision_id')
    const semanticChecksum = stringValue(value, 'semantic_checksum')
    const summary = stringValue(value, 'summary')
    const rawOperations = value.operations
    if (!dashboardId || !revisionId || !semanticChecksum || !summary || !Array.isArray(rawOperations)) return undefined
    const operations = rawOperations.map(parseOperation)
    if (operations.some(operation => operation === undefined)) return undefined
    return { action_type: actionType, dashboard_id: dashboardId, revision_id: revisionId, semantic_checksum: semanticChecksum, summary, operations: operations as readonly DashboardPatchOperationV2[] }
  }
  return undefined
}
