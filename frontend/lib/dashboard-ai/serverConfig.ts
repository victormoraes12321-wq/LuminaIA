import 'server-only'
import { parseDashboardAiMode } from './config'

export function getServerDashboardAiMode() {
  return parseDashboardAiMode(process.env.DASHBOARD_AI_ASSISTANCE_MODE)
}
