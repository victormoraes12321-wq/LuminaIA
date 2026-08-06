import { notFound } from 'next/navigation'
import { connection } from 'next/server'
import { getServerDashboardUiMode } from '@/lib/dashboard-v2/serverConfig'

export default async function GovernedDashboardLayout({ children }: { readonly children: React.ReactNode }) {
  await connection()
  const mode = getServerDashboardUiMode()
  if (mode === 'LEGACY_ONLY') notFound()
  return children
}
