'use client'

import { motion } from 'framer-motion'
import { useAuth } from '@/context/AuthContext'
import { Sidebar } from '@/components/Sidebar'
import { ExecutiveDashboardWorkspace } from '@/components/dashboard-ux/ExecutiveDashboardWorkspace'

export default function DashboardPage() {
  const { loading: authLoading } = useAuth()

  if (authLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[rgb(var(--bg-base))]">
        <div className="flex flex-col items-center gap-4">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            className="w-8 h-8 rounded-full border-2 border-t-transparent border-lumina-400"
          />
          <span className="text-sm font-medium text-[rgb(var(--text-secondary))]">
            Carregando sua sessão...
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-dvh overflow-hidden bg-[rgb(var(--bg-base))]">
      {/* ── Collapsible Global Sidebar ── */}
      <Sidebar />

      {/* ── Main Executive Analytics Dashboard Workspace ── */}
      <main className="flex-1 min-w-0 overflow-hidden">
        <ExecutiveDashboardWorkspace />
      </main>
    </div>
  )
}
