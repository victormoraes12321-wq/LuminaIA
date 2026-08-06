import type { DashboardAiAssistanceModeV2 } from '@/types/dashboard_ai_assistance_v2'

const MODES: readonly DashboardAiAssistanceModeV2[] = ['LEGACY_ONLY', 'SHADOW_ANALYZE', 'AI_PROPOSAL_PREVIEW', 'AI_DRAFT_CREATE', 'AI_ASSISTED_EDIT']

export function parseDashboardAiMode(value: string | undefined): DashboardAiAssistanceModeV2 {
  const normalized = value?.trim().toUpperCase()
  return MODES.find(mode => mode === normalized) ?? 'LEGACY_ONLY'
}

export function getPublicDashboardAiMode(): DashboardAiAssistanceModeV2 {
  return parseDashboardAiMode(process.env.NEXT_PUBLIC_DASHBOARD_AI_ASSISTANCE_MODE)
}

export function dashboardAiAllowsPreview(mode: DashboardAiAssistanceModeV2): boolean {
  return ['AI_PROPOSAL_PREVIEW', 'AI_DRAFT_CREATE', 'AI_ASSISTED_EDIT'].includes(mode)
}

export function dashboardAiAllowsApply(mode: DashboardAiAssistanceModeV2): boolean {
  return mode === 'AI_DRAFT_CREATE' || mode === 'AI_ASSISTED_EDIT'
}

export function dashboardAiAllowsEdit(mode: DashboardAiAssistanceModeV2): boolean {
  return mode === 'AI_ASSISTED_EDIT'
}
