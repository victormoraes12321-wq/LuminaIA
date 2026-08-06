import { notFound } from 'next/navigation'
import { DashboardHistoryPage } from '@/components/dashboard-v2/DashboardHistoryPage'
import { dashboardModeAllowsAuthoring } from '@/lib/dashboard-v2/config'
import { getServerDashboardUiMode } from '@/lib/dashboard-v2/serverConfig'

export default async function GovernedDashboardHistoryRoute({ params }: { readonly params: Promise<{ readonly dashboardId: string }> }) {
  const mode = getServerDashboardUiMode()
  if (!dashboardModeAllowsAuthoring(mode)) notFound()
  const { dashboardId } = await params
  return <DashboardHistoryPage dashboardId={dashboardId} />
}
