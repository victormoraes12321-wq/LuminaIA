import type { DashboardTelemetryEventV2 } from '@/types/dashboard_ui_sidechat_v2'

export function emitDashboardTelemetryV2(event: DashboardTelemetryEventV2): void {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent('lumina:dashboard-ui-sidechat-v2', {
    detail: event,
  }))
}
