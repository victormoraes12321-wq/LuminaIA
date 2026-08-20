import { notFound } from 'next/navigation'
import { DashboardAiCreationWizard } from '@/components/dashboard-ai/DashboardAiCreationWizard'
import { dashboardAiAllowsPreview } from '@/lib/dashboard-ai/config'
import { getServerDashboardAiMode } from '@/lib/dashboard-ai/serverConfig'

export default async function GovernedDashboardAiCreationPage({ searchParams }: { readonly searchParams: Promise<{ readonly target?: string; readonly revision?: string; readonly kind?: string; readonly origin?: string }> }) {
  const mode = getServerDashboardAiMode()
  if (!dashboardAiAllowsPreview(mode)) notFound()
  const query = await searchParams
  const editKind = query.kind === 'visual' || query.kind === 'semantic' ? query.kind : undefined
  const origin = query.origin === 'DASHBOARD_EDITOR' || query.origin === 'SIDE_CHAT' ? query.origin : 'CREATION_WIZARD'
  if ((query.target || query.revision || editKind) && (!query.target || !query.revision || !editKind)) notFound()
  return <DashboardAiCreationWizard mode={mode} targetDashboardId={query.target} targetRevisionId={query.revision} editKind={editKind} origin={origin} />
}
