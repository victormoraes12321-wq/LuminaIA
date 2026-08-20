'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Sparkles,
  LayoutDashboard,
  Users,
  Layers,
  Settings,
  ChevronLeft,
  ChevronRight,
  LogOut,
  User as UserIcon,
  Menu,
  X,
  ShieldAlert,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ThemeToggle } from '@/components/ThemeToggle'
import { useAuth } from '@/context/AuthContext'

interface SidebarProps {
  onLogoClick?: () => void
  activePage?: string
}

export function Sidebar({ onLogoClick }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const { user, logout } = useAuth()
  const pathname = usePathname()

  // Load persistent collapsed state
  useEffect(() => {
    try {
      const stored = localStorage.getItem('lumina_sidebar_collapsed')
      if (stored !== null) {
        setCollapsed(stored === 'true')
      }
    } catch {}
  }, [])

  const toggleCollapsed = () => {
    const next = !collapsed
    setCollapsed(next)
    try {
      localStorage.setItem('lumina_sidebar_collapsed', String(next))
    } catch {}
  }

  // 5 Canonical Primary Menu Items
  const navItems = [
    {
      label: 'Dashboard',
      href: '/dashboard',
      icon: LayoutDashboard,
      active: pathname === '/dashboard' || pathname === '/',
      badge: null,
      adminOnly: false,
    },
    {
      label: 'Consultar Dados',
      href: '/consultar',
      icon: Sparkles,
      active: pathname === '/consultar',
      badge: 'IA',
      adminOnly: false,
    },
    {
      label: 'Operações & Sentinela',
      href: '/dashboard/operacoes',
      icon: ShieldAlert,
      active: pathname.startsWith('/dashboard/operacoes'),
      badge: 'NEW',
      adminOnly: false,
    },
    {
      label: 'Gerenciar Usuários',
      href: '/dashboard/admin/users',
      icon: Users,
      active: pathname.startsWith('/dashboard/admin/users'),
      badge: null,
      adminOnly: true,
    },
    {
      label: 'Dicionário de Views',
      href: '/dashboard/admin/catalog',
      icon: Layers,
      active: pathname.startsWith('/dashboard/admin/catalog'),
      badge: null,
      adminOnly: true,
    },
    {
      label: 'Configurações SaaS',
      href: '/dashboard/admin/settings',
      icon: Settings,
      active: pathname.startsWith('/dashboard/admin/settings'),
      badge: null,
      adminOnly: true,
    },
  ]

  const visibleItems = navItems.filter(item => {
    if (!item.adminOnly) return true
    return user?.role === 'ADMIN' || user?.role === 'GESTOR'
  })

  return (
    <>
      {/* ── Mobile Hamburger Button ───────────────────────────── */}
      <div className="lg:hidden fixed top-3 left-3 z-50">
        <button
          type="button"
          aria-label="Abrir menu de navegação"
          onClick={() => setMobileOpen(!mobileOpen)}
          className="p-2 rounded-xl bg-zinc-900/90 border border-zinc-800 text-zinc-300 shadow-md backdrop-blur-md"
        >
          {mobileOpen ? <X size={18} /> : <Menu size={18} />}
        </button>
      </div>

      {/* ── Mobile Drawer Overlay ─────────────────────────────── */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setMobileOpen(false)}
            className="lg:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
          />
        )}
      </AnimatePresence>

      {/* ── Desktop & Mobile Sidebar Container ────────────────── */}
      <aside
        aria-label="Navegação Lateral LuminaAI"
        data-testid="lumina-global-sidebar"
        className={cn(
          'flex flex-col h-full shrink-0 z-40 transition-all duration-300 ease-in-out',
          'border-r border-[rgb(var(--border)/0.6)] bg-[rgb(var(--bg-surface))]',
          'relative select-none',
          // Desktop Width
          collapsed ? 'hidden lg:flex w-[72px]' : 'hidden lg:flex w-[260px]',
          // Mobile Width & Drawer
          mobileOpen && '!flex fixed inset-y-0 left-0 w-[270px] shadow-2xl z-50'
        )}
      >
        {/* ── Top Header & Logo ── */}
        <div className="flex items-center justify-between px-4 py-4 border-b border-[rgb(var(--border)/0.5)]">
          <Link
            href="/dashboard"
            onClick={() => {
              onLogoClick?.()
              setMobileOpen(false)
            }}
            className="flex items-center gap-2.5 min-w-0 group"
          >
            {/* Logo Mark */}
            <div className="relative w-8 h-8 shrink-0">
              <div className="w-8 h-8 rounded-xl bg-lumina-gradient flex items-center justify-center shadow-lumina transition-transform group-hover:scale-105">
                <Sparkles size={16} className="text-white" />
              </div>
              <div className="absolute -inset-1 rounded-xl bg-lumina-500/20 blur-md -z-10" />
            </div>

            {/* Logo Text (Hidden if collapsed) */}
            {!collapsed && (
              <div className="min-w-0 overflow-hidden">
                <h1 className="text-sm font-bold leading-tight text-gradient truncate">
                  LuminaAI
                </h1>
                <p className="text-[10px] leading-tight text-[rgb(var(--text-muted))] truncate">
                  Executive Intelligence
                </p>
              </div>
            )}
          </Link>

          {/* Desktop Collapse / Expand Toggle Button */}
          <button
            type="button"
            data-testid="sidebar-collapse-toggle"
            title={collapsed ? 'Expandir menu lateral' : 'Recolher menu lateral'}
            aria-label={collapsed ? 'Expandir menu lateral' : 'Recolher menu lateral'}
            onClick={toggleCollapsed}
            className="hidden lg:flex h-6 w-6 items-center justify-center rounded-lg border border-[rgb(var(--border)/0.6)] bg-[rgb(var(--bg-elevated))] text-[rgb(var(--text-muted))] hover:text-[rgb(var(--text-primary))] hover:border-lumina-500/50 transition-colors"
          >
            {collapsed ? <ChevronRight size={13} /> : <ChevronLeft size={13} />}
          </button>
        </div>

        {/* ── Navigation Items List ── */}
        <nav className="flex-1 overflow-y-auto thin-scroll py-4 px-2 space-y-1.5">
          {visibleItems.map(item => {
            const Icon = item.icon
            return (
              <Link
                key={item.href}
                href={item.href}
                data-testid={`nav-item-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
                title={collapsed ? item.label : undefined}
                onClick={() => setMobileOpen(false)}
                className={cn(
                  'group flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all duration-200',
                  item.active
                    ? 'bg-lumina-500/15 text-lumina-400 border border-lumina-500/30 shadow-sm'
                    : 'text-[rgb(var(--text-secondary))] hover:bg-[rgb(var(--bg-elevated))] hover:text-[rgb(var(--text-primary))]',
                  collapsed && 'justify-center px-2'
                )}
              >
                <Icon
                  size={16}
                  className={cn(
                    'shrink-0 transition-colors',
                    item.active ? 'text-lumina-400' : 'text-[rgb(var(--text-muted))] group-hover:text-[rgb(var(--text-primary))]'
                  )}
                />
                {!collapsed && (
                  <span className="truncate flex-1">
                    {item.label}
                  </span>
                )}
                {!collapsed && item.badge && (
                  <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-lumina-500/20 text-lumina-400 border border-lumina-500/30">
                    {item.badge}
                  </span>
                )}
              </Link>
            )
          })}
        </nav>

        {/* ── Bottom Section: User & Theme ── */}
        <div className="p-3 border-t border-[rgb(var(--border)/0.5)] bg-[rgb(var(--bg-elevated)/0.3)] space-y-2">
          {/* User badge */}
          <div className={cn('flex items-center gap-2.5 px-2 py-1.5', collapsed && 'justify-center px-0')}>
            <div className="w-7 h-7 rounded-lg bg-[rgb(var(--bg-elevated))] border border-[rgb(var(--border)/0.8)] flex items-center justify-center shrink-0 text-[rgb(var(--text-secondary))]">
              <UserIcon size={14} />
            </div>
            {!collapsed && (
              <div className="min-w-0 flex-1">
                <p className="text-xs font-bold truncate text-[rgb(var(--text-primary))]">
                  {user?.nome || 'Usuário'}
                </p>
                <p className="text-[10px] truncate text-[rgb(var(--text-muted))] uppercase tracking-wider font-mono">
                  {user?.role || 'CONSULTA'}
                </p>
              </div>
            )}
          </div>

          {/* Controls: Theme & Logout */}
          <div className={cn('flex items-center justify-between pt-1', collapsed && 'flex-col gap-2')}>
            <ThemeToggle size="sm" />
            <button
              type="button"
              title="Sair do sistema"
              aria-label="Sair do sistema"
              onClick={() => logout()}
              className="p-1.5 rounded-lg border border-[rgb(var(--border)/0.6)] text-[rgb(var(--text-muted))] hover:text-red-400 hover:border-red-500/40 hover:bg-red-500/10 transition-colors"
            >
              <LogOut size={13} />
            </button>
          </div>
        </div>
      </aside>
    </>
  )
}
