import { DashboardLibrary } from '@/components/dashboard-v2/DashboardLibrary'
import { getServerDashboardUiMode } from '@/lib/dashboard-v2/serverConfig'
import { getServerDashboardAiMode } from '@/lib/dashboard-ai/serverConfig'

export default function GovernedDashboardLibraryPage() {
  return <DashboardLibrary mode={getServerDashboardUiMode()} aiMode={getServerDashboardAiMode()} />
}
