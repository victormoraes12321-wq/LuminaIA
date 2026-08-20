import { notFound } from 'next/navigation'
import { DashboardEditorPage } from '@/components/dashboard-v2/DashboardEditorPage'
import { dashboardModeAllowsAuthoring } from '@/lib/dashboard-v2/config'
import { getServerDashboardUiMode } from '@/lib/dashboard-v2/serverConfig'
import { getServerDashboardAiMode } from '@/lib/dashboard-ai/serverConfig'

export default async function GovernedDashboardEditorRoute({ params }: { readonly params: Promise<{ readonly dashboardId: string }> }) {
  const mode = getServerDashboardUiMode()
  if (!dashboardModeAllowsAuthoring(mode)) notFound()
  const { dashboardId } = await params
  return <DashboardEditorPage dashboardId={dashboardId} mode={mode} aiMode={getServerDashboardAiMode()} />
}
