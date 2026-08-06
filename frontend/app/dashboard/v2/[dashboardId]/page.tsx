import { DashboardRuntimePage } from '@/components/dashboard-v2/DashboardRuntimePage'
import { getServerDashboardUiMode } from '@/lib/dashboard-v2/serverConfig'

export default async function GovernedDashboardPage({ params }: { readonly params: Promise<{ readonly dashboardId: string }> }) {
  const { dashboardId } = await params
  return <DashboardRuntimePage dashboardId={dashboardId} mode={getServerDashboardUiMode()} />
}
