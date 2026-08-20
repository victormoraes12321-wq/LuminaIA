import { expect, test } from '@playwright/test'
import { parseDashboardUiMode } from '../../lib/dashboard-v2/config'
import { parseDashboardSideChatActionV2 } from '../../lib/dashboard-v2/actionValidator'
import { dashboardVisualUpdateInterceptor, isVisualPatchOperationV2 } from '../../lib/dashboard-v2/visualUpdateInterceptor'
import { dashboardRevisionFixture, revisedDashboardFixture } from '../fixtures/dashboardV2'

test('feature mode is fail-closed and LEGACY_ONLY is the default', () => {
  expect(parseDashboardUiMode(undefined)).toBe('LEGACY_ONLY')
  expect(parseDashboardUiMode('invalid')).toBe('LEGACY_ONLY')
  expect(parseDashboardUiMode('v2_side_chat')).toBe('V2_SIDE_CHAT')
})

test('action parser rejects HTML-like free text, arbitrary URLs and open action names', () => {
  expect(parseDashboardSideChatActionV2('<script>alert(1)</script>')).toBeUndefined()
  expect(parseDashboardSideChatActionV2({ action_type: 'OPEN_URL', url: 'https://evil.invalid' })).toBeUndefined()
  expect(parseDashboardSideChatActionV2({ action_type: 'PUBLISH_AI' })).toBeUndefined()
})

test('visual allowlist accepts title and layout but rejects metric and accessibility mutations', () => {
  expect(isVisualPatchOperationV2({ operation: 'REPLACE', path: '/identity/title', value: 'Novo título' })).toBe(true)
  expect(isVisualPatchOperationV2({ operation: 'REPLACE', path: '/layout/breakpoints/0/items/0/x', value: 1 })).toBe(true)
  expect(isVisualPatchOperationV2({ operation: 'REPLACE', path: '/data_bindings/0/metrics/0/metric_id', value: 'metric.margin' })).toBe(false)
  expect(isVisualPatchOperationV2({ operation: 'REPLACE', path: '/accessibility/accessible_title', value: 'Incompatível' })).toBe(false)
})

test('UI_MODIFIED requires backend confirmation and preserved semantic checksum', () => {
  const action = parseDashboardSideChatActionV2({ action_type: 'VISUAL_PATCH_APPLY', dashboard_id: 'dashboard.sales.001', revision_id: 'revision.sales.001', semantic_checksum: 'a'.repeat(64), operations: [{ operation: 'REPLACE', path: '/identity/title', value: 'Novo título' }], summary: 'Título' })!
  const preview = dashboardVisualUpdateInterceptor({ action, dashboard_id: 'dashboard.sales.001', revision: dashboardRevisionFixture, capabilities: ['dashboard:edit_visual'], mode: 'V2_SIDE_CHAT' })
  expect(preview.outcome).toBe('NO_OP')
  const confirmed = dashboardVisualUpdateInterceptor({ action, dashboard_id: 'dashboard.sales.001', revision: dashboardRevisionFixture, capabilities: ['dashboard:edit_visual'], mode: 'V2_SIDE_CHAT', backend_revision: revisedDashboardFixture() })
  expect(confirmed.outcome).toBe('UI_MODIFIED')
})

test('visual interceptor distinguishes blocked, conflict, invalid and full-render outcomes', () => {
  const base = { action_type: 'VISUAL_PATCH_APPLY' as const, dashboard_id: 'dashboard.sales.001', revision_id: 'revision.sales.001', semantic_checksum: 'a'.repeat(64), operations: [{ operation: 'REPLACE' as const, path: '/identity/title', value: 'Novo título' }], summary: 'Título' }
  expect(dashboardVisualUpdateInterceptor({ action: base, dashboard_id: 'dashboard.sales.001', revision: dashboardRevisionFixture, capabilities: [], mode: 'V2_SIDE_CHAT' }).outcome).toBe('BLOCKED')
  expect(dashboardVisualUpdateInterceptor({ action: { ...base, dashboard_id: 'dashboard.other' }, dashboard_id: 'dashboard.sales.001', revision: dashboardRevisionFixture, capabilities: ['dashboard:edit_visual'], mode: 'V2_SIDE_CHAT' }).outcome).toBe('CONFLICT')
  expect(dashboardVisualUpdateInterceptor({ action: { ...base, operations: [{ operation: 'REPLACE', path: '/data_bindings/0/metrics/0/metric_id', value: 'metric.margin' }] }, dashboard_id: 'dashboard.sales.001', revision: dashboardRevisionFixture, capabilities: ['dashboard:edit_visual'], mode: 'V2_SIDE_CHAT' }).outcome).toBe('INVALID_ACTION')
  expect(dashboardVisualUpdateInterceptor({ action: { ...base, semantic_checksum: 'f'.repeat(64) }, dashboard_id: 'dashboard.sales.001', revision: dashboardRevisionFixture, capabilities: ['dashboard:edit_visual'], mode: 'V2_SIDE_CHAT' }).outcome).toBe('FULL_RENDERING_REQUIRED')
})
