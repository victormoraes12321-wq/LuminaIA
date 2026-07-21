'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Sparkles,
  History,
  Star,
  User,
  ChevronRight,
  BarChart3,
  TrendingUp,
  PieChart,
  Table2,
  Gauge,
  Menu,
  X,
  LogOut,
  Settings,
  Grid,
  Blocks,
  Filter,
  LayoutDashboard,
  Layers,
} from 'lucide-react'
import { cn, formatRelativeTime } from '@/lib/utils'
import { Badge } from '@/components/ui/Badge'
import { ThemeToggle } from '@/components/ThemeToggle'
import { useAuth } from '@/context/AuthContext'
import type { ChartType, FavoriteItem, HistoryItem } from '@/types/lumina'

// ── Chart type icons ───────────────────────────────────────────

const ChartIcons: Record<ChartType, React.ComponentType<{ size?: number; className?: string }>> = {
  BAR:     BarChart3,
  LINE:    TrendingUp,
  AREA:    TrendingUp,
  PIE:     PieChart,
  TABLE:   Table2,
  KPI:     Gauge,
  SCATTER: BarChart3,
  HEATMAP: Grid,
  TREEMAP: Blocks,
  FUNNEL:  Filter,
}

type SidebarIconComponent = React.ComponentType<{
  size?: number
  className?: string
  style?: React.CSSProperties
}>

function ChartTypeIcon({ type, size = 13 }: { type: ChartType | null; size?: number }) {
  if (!type) return null
  const Icon = ChartIcons[type]
  return <Icon size={size} />
}

// ── Logo ───────────────────────────────────────────────────────

function LuminaLogo({ onClick }: { onClick?: () => void }) {
  return (
    <Link
      href="/dashboard"
      onClick={onClick}
      className="flex items-center gap-2.5 px-5 py-5 hover:opacity-90 transition-opacity cursor-pointer"
    >
      {/* Icon mark */}
      <div className="relative w-8 h-8 flex-shrink-0">
        <div className="w-8 h-8 rounded-xl bg-lumina-gradient flex items-center justify-center shadow-lumina">
          <Sparkles size={15} className="text-white" />
        </div>
        {/* Glow */}
        <div className="absolute -inset-1 rounded-xl bg-lumina-500/20 blur-md -z-10" />
      </div>

      {/* Name + tagline */}
      <div>
        <h1 className="text-base font-bold leading-tight text-gradient">
          LuminaAI
        </h1>
        <p className="text-xs leading-tight" style={{ color: 'rgb(var(--text-muted))' }}>
          Business Intelligence
        </p>
      </div>
    </Link>
  )
}

// ── Section header ─────────────────────────────────────────────

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-xs font-semibold uppercase tracking-widest px-4 mb-2 select-none"
      style={{ color: 'rgb(var(--text-muted))' }}>
      {children}
    </p>
  )
}

// ── History Item ──────────────────────────────────────────────

interface HistoryItemRowProps {
  item: HistoryItem
  onClick: (pergunta: string) => void
}

function HistoryItemRow({ item, onClick }: HistoryItemRowProps) {
  return (
    <motion.button
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className={cn(
        'w-full flex items-start gap-2.5 px-4 py-2.5 rounded-lg text-left group',
        'transition-colors hover:bg-[rgb(var(--bg-elevated))]',
      )}
      onClick={() => onClick(item.pergunta)}
    >
      <div
        className="mt-0.5 w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0"
        style={{ background: 'rgb(var(--bg-elevated))', color: 'rgb(var(--text-muted))' }}
      >
        <ChartTypeIcon type={item.chartType} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-xs leading-snug line-clamp-2 transition-colors group-hover:text-lumina-400"
          style={{ color: 'rgb(var(--text-secondary))' }}>
          {item.pergunta}
        </p>
        <p className="text-xs mt-0.5" style={{ color: 'rgb(var(--text-muted))' }}>
          {formatRelativeTime(item.timestamp)}
        </p>
      </div>
      <ChevronRight
        size={12}
        className="flex-shrink-0 mt-1 opacity-0 group-hover:opacity-60 transition-opacity"
        style={{ color: 'rgb(var(--text-muted))' }}
      />
    </motion.button>
  )
}

// ── Favorite Item ──────────────────────────────────────────────

interface FavoriteItemRowProps {
  item: FavoriteItem
  onClick: (titulo: string) => void
}

function FavoriteItemRow({ item, onClick }: FavoriteItemRowProps) {
  return (
    <motion.button
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className={cn(
        'w-full flex items-center gap-2.5 px-4 py-2.5 rounded-lg text-left group',
        'transition-colors hover:bg-[rgb(var(--bg-elevated))]',
      )}
      onClick={() => onClick(item.titulo)}
    >
      <Star
        size={13}
        className="flex-shrink-0 fill-yellow-400 text-yellow-400 mt-px"
      />
      <div className="min-w-0 flex-1">
        <p className="text-xs leading-snug truncate transition-colors group-hover:text-yellow-400"
          style={{ color: 'rgb(var(--text-secondary))' }}>
          {item.titulo}
        </p>
        <p className="text-xs mt-0.5" style={{ color: 'rgb(var(--text-muted))' }}>
          {item.viewName}
        </p>
      </div>
    </motion.button>
  )
}

// ── Empty State ────────────────────────────────────────────────

function EmptyHint({ icon: Icon, text }: { icon: SidebarIconComponent; text: string }) {
  return (
    <div className="flex items-center gap-2 px-4 py-2">
      <Icon size={12} className="flex-shrink-0" style={{ color: 'rgb(var(--text-muted))' }} />
      <p className="text-xs italic leading-snug" style={{ color: 'rgb(var(--text-muted))' }}>
        {text}
      </p>
    </div>
  )
}

// ── Sidebar ───────────────────────────────────────────────────

interface SidebarProps {
  history?: HistoryItem[]
  favorites?: FavoriteItem[]
  onSelectHistory?: (pergunta: string) => void
  onSelectFavorite?: (titulo: string) => void
  onLogoClick?: () => void
  activePage?: string
}

export function Sidebar({
  history = [],
  favorites = [],
  onSelectHistory = () => {},
  onSelectFavorite = () => {},
  onLogoClick,
}: SidebarProps) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const { user, logout } = useAuth()
  const pathname = usePathname()

  const renderSidebarContent = () => (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <LuminaLogo
        onClick={() => {
          onLogoClick?.()
          setMobileOpen(false)
        }}
      />

      {/* Divisor superior */}
      <div className="mx-4 mb-4" style={{ height: 1, background: 'rgb(var(--border) / 0.5)' }} />

      {/* Conteúdo de Navegação */}
      <div className="flex-1 overflow-y-auto thin-scroll space-y-5 pb-2">
        {/* Navegação Principal */}
        <section>
          <div className="space-y-0.5 px-1">
            <Link
              href="/dashboard"
              className={cn(
                'w-full flex items-center gap-2.5 px-4 py-2.5 rounded-lg text-left text-xs font-semibold transition-colors',
                pathname === '/dashboard'
                  ? 'bg-[rgb(var(--bg-elevated))] text-lumina-400'
                  : 'text-[rgb(var(--text-secondary))] hover:bg-[rgb(var(--bg-elevated))]',
              )}
            >
              <Sparkles size={13} className={pathname === '/dashboard' ? 'text-lumina-400' : 'text-zinc-500'} />
              <span>Consultar Dados</span>
            </Link>

            {(user?.role === 'ADMIN' || user?.role === 'GESTOR') && (
              <Link
                href="/dashboard/studio"
                className={cn(
                  'w-full flex items-center gap-2.5 px-4 py-2.5 rounded-lg text-left text-xs font-semibold transition-colors',
                  pathname === '/dashboard/studio'
                    ? 'bg-[rgb(var(--bg-elevated))] text-lumina-400'
                    : 'text-[rgb(var(--text-secondary))] hover:bg-[rgb(var(--bg-elevated))]',
                )}
              >
                <LayoutDashboard size={13} className={pathname === '/dashboard/studio' ? 'text-lumina-400' : 'text-zinc-500'} />
                <span>Dashboard Studio</span>
              </Link>
            )}
          </div>
        </section>

        {/* Menu de Administração (RBAC: ADMIN e GESTOR) */}
        {(user?.role === 'ADMIN' || user?.role === 'GESTOR') && (
          <section>
            <div className="flex items-center justify-between px-4 mb-1">
              <SectionTitle>Administração</SectionTitle>
            </div>
            <div className="space-y-0.5 px-1">
              {/* Gerenciamento de Usuários (Apenas ADMIN) */}
              {user?.role === 'ADMIN' && (
                <Link
                  href="/dashboard/admin/users"
                  className={cn(
                    'w-full flex items-center gap-2.5 px-4 py-2.5 rounded-lg text-left text-xs font-semibold transition-colors',
                    pathname === '/dashboard/admin/users'
                      ? 'bg-[rgb(var(--bg-elevated))] text-lumina-400'
                      : 'text-[rgb(var(--text-secondary))] hover:bg-[rgb(var(--bg-elevated))]',
                  )}
                >
                  <User size={13} className={pathname === '/dashboard/admin/users' ? 'text-lumina-400' : 'text-zinc-500'} />
                  <span>Gerenciar Usuários</span>
                </Link>
              )}

              {/* Dicionário de Views (ADMIN e GESTOR) */}
              <Link
                href="/dashboard/admin/catalog"
                className={cn(
                  'w-full flex items-center gap-2.5 px-4 py-2.5 rounded-lg text-left text-xs font-semibold transition-colors',
                  pathname === '/dashboard/admin/catalog'
                    ? 'bg-[rgb(var(--bg-elevated))] text-lumina-400'
                    : 'text-[rgb(var(--text-secondary))] hover:bg-[rgb(var(--bg-elevated))]',
                )}
              >
                <Table2 size={13} className={pathname === '/dashboard/admin/catalog' ? 'text-lumina-400' : 'text-zinc-500'} />
                <span>Dicionário de Views</span>
              </Link>

              {/* Version Center (SVR) */}
              {user?.role === 'ADMIN' && (
                <Link
                  href="/dashboard/svr"
                  className={cn(
                    'w-full flex items-center gap-2.5 px-4 py-2.5 rounded-lg text-left text-xs font-semibold transition-colors',
                    pathname === '/dashboard/svr'
                      ? 'bg-[rgb(var(--bg-elevated))] text-lumina-400'
                      : 'text-[rgb(var(--text-secondary))] hover:bg-[rgb(var(--bg-elevated))]',
                  )}
                >
                  <Layers size={13} className={pathname === '/dashboard/svr' ? 'text-lumina-400' : 'text-zinc-500'} />
                  <span>Version Center (SVR)</span>
                </Link>
              )}

              {/* Configurações do SaaS (Apenas ADMIN) */}
              {user?.role === 'ADMIN' && (
                <Link
                  href="/dashboard/admin/settings"
                  className={cn(
                    'w-full flex items-center gap-2.5 px-4 py-2.5 rounded-lg text-left text-xs font-semibold transition-colors',
                    pathname === '/dashboard/admin/settings'
                      ? 'bg-[rgb(var(--bg-elevated))] text-lumina-400'
                      : 'text-[rgb(var(--text-secondary))] hover:bg-[rgb(var(--bg-elevated))]',
                  )}
                >
                  <Settings size={13} className={pathname === '/dashboard/admin/settings' ? 'text-lumina-400' : 'text-zinc-500'} />
                  <span>Configurações SaaS</span>
                </Link>
              )}

              {/* Pipeline Inspector */}
              {user?.role === 'ADMIN' && <Link
                href="/dashboard/inspector"
                className={cn(
                  'w-full flex items-center gap-2.5 px-4 py-2.5 rounded-lg text-left text-xs font-semibold transition-colors',
                  pathname === '/dashboard/inspector'
                    ? 'bg-[rgb(var(--bg-elevated))] text-lumina-400'
                    : 'text-[rgb(var(--text-secondary))] hover:bg-[rgb(var(--bg-elevated))]',
                )}
              >
                <Layers size={13} className={pathname === '/dashboard/inspector' ? 'text-lumina-400' : 'text-zinc-500'} />
                <span>Inspector de Pipeline</span>
              </Link>}
            </div>
          </section>
        )}

        {/* Consultas Recentes (Ocultado em páginas administrativas para focar) */}
        {!pathname.startsWith('/dashboard/admin') && (
          <section>
            <div className="flex items-center justify-between px-4 mb-1">
              <SectionTitle>Recentes</SectionTitle>
              {history.length > 0 && (
                <span className="text-xs font-semibold px-1.5 py-0.5 rounded-full bg-lumina-500/15 text-lumina-400">
                  {history.length}
                </span>
              )}
            </div>
            <div className="space-y-0.5 px-1">
              {history.length === 0 ? (
                <EmptyHint icon={History} text="Suas perguntas recentes aparecerão aqui." />
              ) : (
                history.slice(0, 8).map(item => (
                  <HistoryItemRow
                    key={item.id}
                    item={item}
                    onClick={onSelectHistory}
                  />
                ))
              )}
            </div>
          </section>
        )}

        {/* Favoritos (Ocultado em páginas administrativas para focar) */}
        {!pathname.startsWith('/dashboard/admin') && (
          <section>
            <div className="flex items-center justify-between px-4 mb-1">
              <SectionTitle>Favoritos</SectionTitle>
              {favorites.length > 0 && (
                <span className="text-xs font-semibold px-1.5 py-0.5 rounded-full bg-yellow-400/15 text-yellow-400">
                  {favorites.length}
                </span>
              )}
            </div>
            <div className="space-y-0.5 px-1">
              {favorites.length === 0 ? (
                <EmptyHint icon={Star} text="Favorite consultas para acesso rápido." />
              ) : (
                favorites.map(item => (
                  <FavoriteItemRow
                    key={item.id}
                    item={item}
                    onClick={onSelectFavorite}
                  />
                ))
              )}
            </div>
          </section>
        )}
      </div>

      {/* Rodapé — Perfil do Usuário */}
      <div
        className="flex-shrink-0 border-t p-4 space-y-3"
        style={{ borderColor: 'rgb(var(--border) / 0.5)' }}
      >

        {/* Theme toggle row */}
        <div className="flex items-center justify-between">
          <span className="text-xs" style={{ color: 'rgb(var(--text-muted))' }}>
            Tema
          </span>
          <ThemeToggle size="sm" />
        </div>

        {/* User */}
        {user && (
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-lumina-gradient flex items-center justify-center flex-shrink-0">
              <User size={14} className="text-white" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold truncate" style={{ color: 'rgb(var(--text-primary))' }}>
                {user.nome}
              </p>
              <p className="text-[10px] truncate" style={{ color: 'rgb(var(--text-muted))' }}>
                {user.email}
              </p>
            </div>
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <Badge variant="lumina" size="xs">
                {user.role}
              </Badge>
              <button
                onClick={() => void logout()}
                aria-label="Sair da conta"
                title="Sair da conta"
                className="w-7 h-7 rounded-lg flex items-center justify-center hover:bg-red-500/10 text-slate-400 hover:text-red-400 transition-colors"
              >
                <LogOut size={13} />
              </button>
            </div>
          </div>
        )}
        {!user && (
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-red-500/15 flex items-center justify-center flex-shrink-0">
              <LogOut size={14} className="text-red-300" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold truncate" style={{ color: 'rgb(var(--text-primary))' }}>
                Sessao indisponivel
              </p>
              <p className="text-[10px] truncate" style={{ color: 'rgb(var(--text-muted))' }}>
                Entre novamente para continuar.
              </p>
            </div>
            <button
              onClick={() => void logout()}
              aria-label="Sair e voltar ao login"
              title="Sair e voltar ao login"
              className="px-2.5 py-1.5 rounded-lg text-[10px] font-bold text-red-300 hover:bg-red-500/10 transition-colors"
            >
              Sair
            </button>
          </div>
        )}
      </div>
    </div>
  )

  return (
    <>
      {/* Mobile toggle button */}
      <button
        className="fixed top-4 left-4 z-50 lg:hidden w-9 h-9 rounded-xl flex items-center justify-center lumina-card"
        onClick={() => setMobileOpen(v => !v)}
        aria-label="Toggle sidebar"
      >
        {mobileOpen ? <X size={16} /> : <Menu size={16} />}
      </button>

      {/* Desktop sidebar */}
      <aside className="sidebar hidden lg:flex" aria-label="Navegação lateral LuminaAI">
        {renderSidebarContent()}
      </aside>

      {/* Mobile sidebar (overlay) */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              key="backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
              onClick={() => setMobileOpen(false)}
            />

            {/* Slide-in panel */}
            <motion.aside
              key="mobile-sidebar"
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              className="sidebar fixed z-50 lg:hidden flex"
              style={{ boxShadow: '4px 0 32px rgb(0 0 0 / 0.25)' }}
              aria-label="Navegação lateral móvel"
            >
              {renderSidebarContent()}
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
