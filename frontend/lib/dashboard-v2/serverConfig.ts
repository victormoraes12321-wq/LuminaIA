import 'server-only'

import { parseDashboardUiMode } from './config'
import type { DashboardUiModeV2 } from '@/types/dashboard_ui_sidechat_v2'

export function getServerDashboardUiMode(): DashboardUiModeV2 {
  const mode = parseDashboardUiMode(process.env.DASHBOARD_UI_MODE)
  if (mode === 'V2_PREVIEW' && process.env.NODE_ENV === 'production') {
    const allowlisted = process.env.DASHBOARD_UI_PREVIEW_ALLOWLISTED === 'true'
    return allowlisted ? mode : 'LEGACY_ONLY'
  }
  return mode
}
