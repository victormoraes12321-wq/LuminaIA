import type { DashboardUiModeV2 } from '@/types/dashboard_ui_sidechat_v2'

const MODES: readonly DashboardUiModeV2[] = [
  'LEGACY_ONLY',
  'V2_PREVIEW',
  'V2_READ',
  'V2_AUTHORING',
  'V2_SIDE_CHAT',
]

export function parseDashboardUiMode(value: string | undefined): DashboardUiModeV2 {
  const normalized = value?.trim().toUpperCase()
  return MODES.find(mode => mode === normalized) ?? 'LEGACY_ONLY'
}

export function getPublicDashboardUiMode(): DashboardUiModeV2 {
  return parseDashboardUiMode(process.env.NEXT_PUBLIC_DASHBOARD_UI_MODE)
}

export function dashboardModeAllowsRead(mode: DashboardUiModeV2): boolean {
  return mode !== 'LEGACY_ONLY'
}

export function dashboardModeAllowsAuthoring(mode: DashboardUiModeV2): boolean {
  return mode === 'V2_AUTHORING' || mode === 'V2_SIDE_CHAT'
}

export function dashboardModeAllowsSideChat(mode: DashboardUiModeV2): boolean {
  return mode === 'V2_SIDE_CHAT'
}

export function isDashboardPreviewMode(mode: DashboardUiModeV2): boolean {
  return mode === 'V2_PREVIEW'
}
