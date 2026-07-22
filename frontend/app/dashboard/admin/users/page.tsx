'use client'

/**
 * LuminaAI — Painel Administrativo de Usuários
 * --------------------------------------------
 * Página responsável pela listagem, ativação/suspensão e deleção de usuários
 * do tenant atual. Contém um modal interativo para cadastro de novos usuários
 * com geração e exibição segura de senha temporária.
 * 
 * Regra de Segurança (RBAC):
 * - Acesso restrito a usuários com papel 'ADMIN'.
 * - Caso um usuário não autorizado acesse, exibe uma tela elegante de Acesso Negado.
 */

import { useCallback, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  UserPlus,
  Trash2,
  Power,
  ShieldAlert,
  Copy,
  Check,
  Search,
  ArrowLeft,
  UserCheck,
  Loader2,
  AlertCircle,
  Edit2
} from 'lucide-react'
import Link from 'next/link'
import { useAuth } from '@/context/AuthContext'
import { Badge } from '@/components/ui/Badge'
import { GlassCard } from '@/components/ui/GlassCard'
import { cn, getApiBase } from '@/lib/utils'
import { TooltipHelp } from '@/components/ui/TooltipHelp'
import { Sidebar } from '@/components/Sidebar'

// Interface local que espelha UserResponse do backend
type UserRole = 'ADMIN' | 'GESTOR' | 'CONSULTA'

interface UserItem {
  id: string
  nome: string
  email: string
  role: UserRole
  tenant_id: string
  ativo: boolean
  must_change_password: boolean
  criado_em: string
}

interface EditUserPayload {
  nome: string
  email: string
  role: UserRole
  ativo: boolean
  password?: string
}

export default function AdminUsersPage() {
  const { user, token } = useAuth()
  
  // Estados de listagem e controle
  const [users, setUsers] = useState<UserItem[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Controle do modal de criação
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [newUserName, setNewUserName] = useState('')
  const [newUserEmail, setNewUserEmail] = useState('')
  const [newUserRole, setNewUserRole] = useState<UserRole>('CONSULTA')
  const [submitting, setSubmitting] = useState(false)
  
  // Estado pós-criação (exibição de senha temporária)
  const [tempPassword, setTempPassword] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  
  // Estado de confirmação de exclusão
  const [deletingUserId, setDeletingUserId] = useState<string | null>(null)

  // Controle do modal de edição
  const [isEditOpen, setIsEditOpen] = useState(false)
  const [editingUserId, setEditingUserId] = useState<string | null>(null)
  const [editUserName, setEditUserName] = useState('')
  const [editUserEmail, setEditUserEmail] = useState('')
  const [editUserRole, setEditUserRole] = useState<UserRole>('CONSULTA')
  const [editUserPassword, setEditUserPassword] = useState('')
  const [editUserAtivo, setEditUserAtivo] = useState(true)

  const API_BASE = getApiBase()
  const isAdmin = user?.role === 'ADMIN'

  // Busca lista de usuários do tenant
  const fetchUsers = useCallback(async () => {
    if (!token || !isAdmin) return
    try {
      setLoading(true)
      setError(null)
      const res = await fetch(`${API_BASE}/api/v1/users/`, {
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.error?.message ?? 'Erro ao buscar usuários.')
      }
      const data = await res.json()
      setUsers(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro na requisição dos usuários.')
    } finally {
      setLoading(false)
    }
  }, [API_BASE, isAdmin, token])

  // Efeito para carregar dados iniciais
  useEffect(() => {
    if (user && !isAdmin) {
      queueMicrotask(() => setLoading(false))
    } else if (token && isAdmin) {
      void Promise.resolve().then(fetchUsers)
    }
  }, [fetchUsers, isAdmin, token, user])

  // Alterna o status ativo do usuário (suspende ou reativa)
  const handleToggleActive = async (targetUser: UserItem) => {
    if (targetUser.id === user?.id) {
      alert('Você não pode suspender sua própria conta.')
      return
    }
    try {
      setError(null)
      const res = await fetch(`${API_BASE}/api/v1/users/${targetUser.id}/toggle-active`, {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.error?.message ?? 'Erro ao alterar status do usuário.')
      }
      const updatedUser = await res.json()
      setUsers(prev => prev.map(u => (u.id === updatedUser.id ? updatedUser : u)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao alterar status.')
    }
  }

  // Deleta permanentemente um usuário
  const handleDeleteUser = async (targetUserId: string) => {
    try {
      setError(null)
      const res = await fetch(`${API_BASE}/api/v1/users/${targetUserId}`, {
        method: 'DELETE',
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.error?.message ?? 'Erro ao deletar usuário.')
      }
      // Remove da lista local
      setUsers(prev => prev.filter(u => u.id !== targetUserId))
      setDeletingUserId(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao deletar.')
    }
  }

  // Cria um novo usuário chamando o backend
  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newUserName.trim() || !newUserEmail.trim()) return
    try {
      setSubmitting(true)
      setError(null)
      const res = await fetch(`${API_BASE}/api/v1/users/`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          nome: newUserName,
          email: newUserEmail,
          role: newUserRole,
          tenant_id: user?.tenant_id
        })
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.error?.message ?? 'Erro ao cadastrar usuário.')
      }
      const data = await res.json() // Retorna { user: UserResponse, temp_password: str }
      
      // Atualiza listagem local
      setUsers(prev => [data.user, ...prev])
      // Exibe a senha gerada
      setTempPassword(data.temp_password)
      
      // Limpa formulário
      setNewUserName('')
      setNewUserEmail('')
      setNewUserRole('CONSULTA')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao cadastrar.')
    } finally {
      setSubmitting(false)
    }
  }

  // Copia a senha temporária para o clipboard
  const copyToClipboard = () => {
    if (!tempPassword) return
    navigator.clipboard.writeText(tempPassword)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Limpa o estado da senha e fecha o modal
  const handleCloseCreateModal = () => {
    setIsCreateOpen(false)
    setTempPassword(null)
    setCopied(false)
  }

  // Inicia o processo de edição carregando os dados do usuário
  const handleOpenEditModal = (targetUser: UserItem) => {
    setEditingUserId(targetUser.id)
    setEditUserName(targetUser.nome)
    setEditUserEmail(targetUser.email)
    setEditUserRole(targetUser.role)
    setEditUserAtivo(targetUser.ativo)
    setEditUserPassword('')
    setIsEditOpen(true)
  }

  const handleEditUser = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingUserId || !editUserName.trim() || !editUserEmail.trim()) return
    try {
      setSubmitting(true)
      setError(null)
      const body: EditUserPayload = {
        nome: editUserName,
        email: editUserEmail,
        role: editUserRole,
        ativo: editUserAtivo,
      }
      if (editUserPassword.trim() !== '') {
        body.password = editUserPassword
      }
      const res = await fetch(`${API_BASE}/api/v1/users/${editingUserId}`, {
        method: 'PATCH',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(body)
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.error?.message ?? 'Erro ao salvar alterações.')
      }
      const updatedUser = await res.json()
      setUsers(prev => prev.map(u => (u.id === updatedUser.id ? updatedUser : u)))
      setIsEditOpen(false)
      setEditingUserId(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao salvar alterações.')
    } finally {
      setSubmitting(false)
    }
  }

  // ── Proteção RBAC / Acesso Negado ──────────────────────────────
  if (!loading && user?.role !== 'ADMIN') {
    return (
      <div className="flex h-dvh w-screen items-center justify-center p-6" style={{ background: 'rgb(var(--bg-base))' }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-md w-full text-center"
        >
          <GlassCard padding="lg" className="flex flex-col items-center gap-6 border-red-500/25">
            <div className="w-16 h-16 rounded-2xl bg-red-500/10 flex items-center justify-center text-red-500">
              <ShieldAlert size={36} />
            </div>
            <div>
              <h2 className="text-xl font-bold mb-2" style={{ color: 'rgb(var(--text-primary))' }}>
                Acesso Restrito
              </h2>
              <p className="text-sm leading-relaxed" style={{ color: 'rgb(var(--text-secondary))' }}>
                Desculpe, a área de gerenciamento de usuários é restrita para administradores do sistema.
              </p>
            </div>
            <Link href="/dashboard" className="w-full">
              <button
                className="w-full flex items-center justify-center gap-2 text-xs font-semibold py-3 px-4 rounded-xl transition-all interactive hover:bg-zinc-100 dark:hover:bg-zinc-800"
                style={{
                  background: 'rgb(var(--bg-elevated))',
                  border: '1px solid rgb(var(--border) / 0.6)',
                  color: 'rgb(var(--text-secondary))',
                }}
              >
                <ArrowLeft size={14} />
                <span>Voltar ao Dashboard</span>
              </button>
            </Link>
          </GlassCard>
        </motion.div>
      </div>
    )
  }

  // Filtragem local baseada na busca por nome ou e-mail
  const filteredUsers = users.filter(u =>
    u.nome.toLowerCase().includes(searchQuery.toLowerCase()) ||
    u.email.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="flex h-dvh overflow-hidden" style={{ background: 'rgb(var(--bg-base))' }}>
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0 dashboard-main-content">
        
        {/* Top Header */}
        <header
          className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 px-8 py-6 flex-shrink-0"
          style={{ borderBottom: '1px solid rgb(var(--border) / 0.5)' }}
        >
          <div>
            <h1 className="text-xl font-bold text-gradient">
              Gerenciar Usuários
            </h1>
            <p className="text-xs mt-0.5" style={{ color: 'rgb(var(--text-muted))' }}>
              Adicione colaboradores, defina níveis de permissão (RBAC) e gerencie o status das contas.
            </p>
          </div>
          
          <button
            onClick={() => setIsCreateOpen(true)}
            className="flex items-center justify-center gap-2 text-xs font-semibold px-4 py-2.5 rounded-xl bg-lumina-gradient text-white shadow-lumina-lg transition-all hover:scale-102 interactive"
          >
            <UserPlus size={14} />
            <span>Cadastrar Usuário</span>
          </button>
        </header>

        {/* Corpo Principal da Tela */}
        <main className="flex-1 overflow-y-auto px-8 py-6 space-y-6">
          
          {/* Alertas de Erro Globais */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-4 rounded-xl border border-red-500/20 bg-red-500/10 flex items-start gap-3"
            >
              <AlertCircle className="text-red-400 mt-0.5 flex-shrink-0" size={16} />
              <div>
                <p className="text-xs font-semibold text-red-400">Erro detectado pelo servidor</p>
                <p className="text-xs leading-normal mt-0.5" style={{ color: 'rgb(var(--text-secondary))' }}>
                  {error}
                </p>
              </div>
            </motion.div>
          )}

          {/* Barra de Filtros e Busca */}
          <div className="flex items-center gap-3 w-full max-w-md">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-400 dark:text-zinc-500" size={15} />
              <input
                type="text"
                placeholder="Buscar usuário por nome ou email..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 text-xs lumina-input"
              />
            </div>
          </div>

          {/* Grid de Usuários (Bento-style / Cards Estilizados) */}
          {loading ? (
            <div className="flex items-center justify-center h-64 gap-3">
              <Loader2 className="text-lumina-400 animate-spin" size={24} />
              <span className="text-xs" style={{ color: 'rgb(var(--text-muted))' }}>Buscando colaboradores ativos...</span>
            </div>
          ) : filteredUsers.length === 0 ? (
            <GlassCard className="flex flex-col items-center justify-center py-16 text-center border-dashed border-zinc-300 dark:border-zinc-700/50">
              <UserCheck size={36} className="text-zinc-400 dark:text-zinc-600 mb-3" />
              <h3 className="text-sm font-semibold mb-1" style={{ color: 'rgb(var(--text-primary))' }}>
                Nenhum usuário localizado
              </h3>
              <p className="text-xs leading-relaxed max-w-xs" style={{ color: 'rgb(var(--text-muted))' }}>
                {searchQuery ? 'Tente ajustar sua palavra-chave de busca.' : 'Cadastre o primeiro colaborador da sua empresa clicando no botão acima.'}
              </p>
            </GlassCard>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredUsers.map(u => (
                <GlassCard
                  key={u.id}
                  padding="md"
                  className={cn(
                    'flex flex-col justify-between gap-5 relative transition-all border-zinc-200 dark:border-zinc-800/40',
                    !u.ativo && 'opacity-60 grayscale-[30%]'
                  )}
                >
                  {/* Cabeçalho do Card */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="text-sm font-bold truncate" style={{ color: 'rgb(var(--text-primary))' }}>
                        {u.nome}
                      </h3>
                      <p className="text-xs truncate mt-0.5" style={{ color: 'rgb(var(--text-muted))' }}>
                        {u.email}
                      </p>
                    </div>
                    
                    <Badge variant={u.role === 'ADMIN' ? 'lumina' : u.role === 'GESTOR' ? 'info' : 'neutral'} size="xs">
                      {u.role}
                    </Badge>
                  </div>

                  {/* Informações Auxiliares */}
                  <div className="flex flex-col gap-1.5 text-[11px] leading-none" style={{ color: 'rgb(var(--text-muted))' }}>
                    <div className="flex items-center gap-1.5">
                      <span>Status da Conta:</span>
                      <span className={cn('font-semibold', u.ativo ? 'text-emerald-500' : 'text-zinc-500 dark:text-zinc-400')}>
                        {u.ativo ? 'Ativo' : 'Suspenso'}
                      </span>
                    </div>
                    {u.must_change_password && (
                      <div className="flex items-center gap-1.5 mt-0.5 text-yellow-500">
                        <AlertCircle size={10} />
                        <span>Requer troca de senha</span>
                      </div>
                    )}
                  </div>

                  {/* Barra de Ações Rápidas */}
                  <div className="flex items-center justify-between border-t border-zinc-200 dark:border-zinc-800/50 pt-3">
                    <button
                      onClick={() => handleToggleActive(u)}
                      disabled={u.id === user?.id}
                      className={cn(
                        'flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1.5 rounded-lg transition-colors border select-none disabled:opacity-50 disabled:cursor-not-allowed',
                        u.ativo
                          ? 'text-zinc-500 dark:text-zinc-400 hover:text-red-400 border-zinc-300 dark:border-zinc-800 hover:bg-red-500/10'
                          : 'text-emerald-500 dark:text-emerald-400 hover:text-emerald-600 border-zinc-300 dark:border-zinc-800 hover:bg-emerald-500/10'
                      )}
                      title={u.ativo ? 'Suspender Usuário' : 'Ativar Usuário'}
                    >
                      <Power size={11} />
                      <span>{u.ativo ? 'Suspender' : 'Reativar'}</span>
                    </button>

                    <div className="flex gap-2">
                      <button
                        onClick={() => handleOpenEditModal(u)}
                        className="flex items-center justify-center w-8 h-8 rounded-lg border border-zinc-300 dark:border-zinc-800 text-zinc-500 dark:text-zinc-400 hover:text-lumina-400 hover:bg-lumina-500/10 transition-colors"
                        title="Editar Usuário"
                      >
                        <Edit2 size={12} />
                      </button>
                      <button
                        onClick={() => setDeletingUserId(u.id)}
                        disabled={u.id === user?.id}
                        className="flex items-center justify-center w-8 h-8 rounded-lg border border-zinc-300 dark:border-zinc-800 text-zinc-500 dark:text-zinc-400 hover:text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Excluir Usuário"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </div>
                </GlassCard>
              ))}
            </div>
          )}
        </main>
      </div>

      {/* ── MODAL: CONFIRMAÇÃO DE DELEÇÃO ────────────────────────────── */}
      <AnimatePresence>
        {deletingUserId && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setDeletingUserId(null)}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="relative w-full max-w-sm glass-strong rounded-2xl p-6 shadow-2xl z-10 border border-zinc-200 dark:border-zinc-800"
            >
              <div className="flex flex-col items-center text-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-red-500/10 flex items-center justify-center text-red-400">
                  <ShieldAlert size={24} />
                </div>
                <div>
                  <h3 className="text-base font-bold" style={{ color: 'rgb(var(--text-primary))' }}>
                    Confirmar Exclusão?
                  </h3>
                  <p className="text-xs mt-2 leading-relaxed" style={{ color: 'rgb(var(--text-secondary))' }}>
                    Esta ação é permanente. Todos os logs de pesquisa e permissões do usuário serão excluídos para sempre.
                  </p>
                </div>
                <div className="flex gap-2 w-full mt-2">
                  <button
                    onClick={() => setDeletingUserId(null)}
                    className="flex-1 py-2 px-3 rounded-lg text-xs font-semibold border border-zinc-300 dark:border-zinc-800 transition-colors hover:bg-zinc-100 dark:hover:bg-zinc-800"
                    style={{ color: 'rgb(var(--text-secondary))' }}
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={() => deletingUserId && handleDeleteUser(deletingUserId)}
                    className="flex-1 py-2 px-3 rounded-lg text-xs font-semibold bg-red-500 hover:bg-red-600 text-white transition-colors"
                  >
                    Excluir
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* ── MODAL: CADASTRO DE NOVO USUÁRIO ──────────────────────────── */}
      <AnimatePresence>
        {isCreateOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={handleCloseCreateModal}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 30 }}
              className="relative w-full max-w-md glass-strong rounded-2xl p-6 shadow-2xl z-10 border border-zinc-200 dark:border-zinc-800"
            >
              {/* Se a senha temporária foi gerada, exibe a tela de sucesso para cópia */}
              {tempPassword ? (
                <div className="flex flex-col items-center gap-6 py-4">
                  <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 flex items-center justify-center text-emerald-400">
                    <UserCheck size={28} />
                  </div>
                  <div className="text-center">
                    <h3 className="text-base font-bold" style={{ color: 'rgb(var(--text-primary))' }}>
                      Usuário Cadastrado com Sucesso!
                    </h3>
                    <p className="text-xs mt-2 max-w-xs leading-relaxed" style={{ color: 'rgb(var(--text-secondary))' }}>
                      Copie a senha temporária abaixo e envie para o novo colaborador. Ela será solicitada no primeiro login.
                    </p>
                  </div>

                  <div className="w-full flex items-center justify-between p-3.5 rounded-xl border border-emerald-500/25 bg-emerald-500/5 select-all">
                    <span className="font-mono text-xs font-bold text-emerald-300">
                      {tempPassword}
                    </span>
                    <button
                      onClick={copyToClipboard}
                      className="p-2 rounded-lg hover:bg-emerald-500/10 text-emerald-400 transition-colors"
                      title="Copiar senha"
                    >
                      {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
                    </button>
                  </div>

                  <button
                    onClick={handleCloseCreateModal}
                    className="w-full py-2.5 rounded-xl bg-lumina-gradient text-white text-xs font-semibold shadow-lumina interactive"
                  >
                    Fechar e Voltar
                  </button>
                </div>
              ) : (
                /* Formulário Padrão */
                <form onSubmit={handleCreateUser} className="space-y-5">
                  <div>
                    <h3 className="text-base font-bold" style={{ color: 'rgb(var(--text-primary))' }}>
                      Cadastrar Novo Usuário
                    </h3>
                    <p className="text-[11px] mt-0.5" style={{ color: 'rgb(var(--text-muted))' }}>
                      Insira os dados do colaborador para gerar a conta.
                    </p>
                  </div>

                  <div className="space-y-4">
                    {/* Nome */}
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[11px] font-semibold uppercase tracking-wider flex items-center" style={{ color: 'rgb(var(--text-muted))' }}>
                        Nome Completo
                        <TooltipHelp content="Nome completo do novo usuário. Será exibido no cabeçalho e relatórios do sistema." />
                      </label>
                      <input
                        type="text"
                        required
                        value={newUserName}
                        onChange={e => setNewUserName(e.target.value)}
                        placeholder="Ex: João da Silva"
                        className="py-2.5 px-3.5 text-xs lumina-input"
                      />
                    </div>

                    {/* Email */}
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[11px] font-semibold uppercase tracking-wider flex items-center" style={{ color: 'rgb(var(--text-muted))' }}>
                        Endereço de E-mail
                        <TooltipHelp content="O endereço de e-mail corporativo do colaborador. Servirá como login exclusivo para acesso ao sistema." />
                      </label>
                      <input
                        type="email"
                        required
                        value={newUserEmail}
                        onChange={e => setNewUserEmail(e.target.value)}
                        placeholder="Ex: joao.silva@empresa.com"
                        className="py-2.5 px-3.5 text-xs lumina-input"
                      />
                    </div>

                    {/* Cargo / Nível (RBAC) */}
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[11px] font-semibold uppercase tracking-wider flex items-center" style={{ color: 'rgb(var(--text-muted))' }}>
                        Nível de Permissão (Role)
                        <TooltipHelp content="Nível de controle de acesso (RBAC). CONSULTA: pode realizar pesquisas no chat; GESTOR: gerencia o catálogo de views; ADMINISTRADOR: acesso a todas as configurações de marca, banco e chaves." />
                      </label>
                      <select
                        value={newUserRole}
                        onChange={e => setNewUserRole(e.target.value as UserRole)}
                        className="py-2.5 px-3.5 text-xs lumina-input"
                      >
                        <option value="CONSULTA">CONSULTA (Visualizar e pesquisar com IA)</option>
                        <option value="GESTOR">GESTOR (Visualizar + Editar Dicionário de Views)</option>
                        <option value="ADMIN">ADMINISTRADOR (Acesso total às configurações)</option>
                      </select>
                    </div>
                  </div>

                  <div className="flex gap-2.5 pt-2">
                    <button
                      type="button"
                      onClick={handleCloseCreateModal}
                      className="flex-1 py-2.5 rounded-xl border border-zinc-300 dark:border-zinc-800 text-xs font-semibold hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                      style={{ color: 'rgb(var(--text-secondary))' }}
                    >
                      Cancelar
                    </button>
                    <button
                      type="submit"
                      disabled={submitting}
                      className="flex-1 py-2.5 rounded-xl bg-lumina-gradient text-white text-xs font-semibold shadow-lumina transition-all hover:scale-102 flex items-center justify-center gap-1.5 disabled:opacity-50"
                    >
                      {submitting ? (
                        <Loader2 className="animate-spin" size={14} />
                      ) : (
                        <span>Salvar</span>
                      )}
                    </button>
                  </div>
                </form>
              )}
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* ── MODAL: EDIÇÃO DE USUÁRIO ─────────────────────────────────── */}
      <AnimatePresence>
        {isEditOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsEditOpen(false)}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 30 }}
              className="relative w-full max-w-md glass-strong rounded-2xl p-6 shadow-2xl z-10 border border-zinc-200 dark:border-zinc-800"
            >
              <form onSubmit={handleEditUser} className="space-y-5">
                <div>
                  <h3 className="text-base font-bold" style={{ color: 'rgb(var(--text-primary))' }}>
                    Editar Usuário
                  </h3>
                  <p className="text-[11px] mt-0.5" style={{ color: 'rgb(var(--text-muted))' }}>
                    Atualize os dados de cadastro e permissão do colaborador.
                  </p>
                </div>

                <div className="space-y-4">
                  {/* Nome */}
                  <div className="flex flex-col gap-1.5">
                    <label className="text-[11px] font-semibold uppercase tracking-wider flex items-center" style={{ color: 'rgb(var(--text-muted))' }}>
                      Nome Completo
                      <TooltipHelp content="Nome completo do usuário. Será atualizado em todo o sistema." />
                    </label>
                    <input
                      type="text"
                      required
                      value={editUserName}
                      onChange={e => setEditUserName(e.target.value)}
                      placeholder="Ex: João da Silva"
                      className="py-2.5 px-3.5 text-xs lumina-input"
                    />
                  </div>

                  {/* Email */}
                  <div className="flex flex-col gap-1.5">
                    <label className="text-[11px] font-semibold uppercase tracking-wider flex items-center" style={{ color: 'rgb(var(--text-muted))' }}>
                      Endereço de E-mail
                      <TooltipHelp content="Login exclusivo de acesso do colaborador. Deve ser único no tenant." />
                    </label>
                    <input
                      type="email"
                      required
                      value={editUserEmail}
                      onChange={e => setEditUserEmail(e.target.value)}
                      placeholder="Ex: joao.silva@empresa.com"
                      className="py-2.5 px-3.5 text-xs lumina-input"
                    />
                  </div>

                  {/* Cargo / Nível (RBAC) */}
                  <div className="flex flex-col gap-1.5">
                    <label className="text-[11px] font-semibold uppercase tracking-wider flex items-center" style={{ color: 'rgb(var(--text-muted))' }}>
                      Nível de Permissão (Role)
                      <TooltipHelp content="Nível de controle de acesso (RBAC). Não é possível alterar seu próprio nível de permissão." />
                    </label>
                    <select
                      value={editUserRole}
                      disabled={editingUserId === user?.id}
                      onChange={e => setEditUserRole(e.target.value as UserRole)}
                      className="py-2.5 px-3.5 text-xs lumina-input disabled:opacity-50"
                    >
                      <option value="CONSULTA">CONSULTA (Visualizar e pesquisar com IA)</option>
                      <option value="GESTOR">GESTOR (Visualizar + Editar Dicionário de Views)</option>
                      <option value="ADMIN">ADMINISTRADOR (Acesso total às configurações)</option>
                    </select>
                  </div>

                  {/* Ativo / Suspenso */}
                  <div className="flex items-center justify-between py-1.5 border-y border-zinc-200 dark:border-zinc-800">
                    <label className="text-[11px] font-semibold uppercase tracking-wider flex items-center" style={{ color: 'rgb(var(--text-muted))' }}>
                      Conta Ativa
                      <TooltipHelp content="Marque para permitir o login do usuário, ou desmarque para suspender seu acesso temporariamente." />
                    </label>
                    <input
                      type="checkbox"
                      checked={editUserAtivo}
                      disabled={editingUserId === user?.id}
                      onChange={e => setEditUserAtivo(e.target.checked)}
                      className="w-4 h-4 rounded border-zinc-300 dark:border-zinc-700 bg-transparent text-violet-600 focus:ring-violet-500 disabled:opacity-50"
                    />
                  </div>

                  {/* Nova Senha (Opcional) */}
                  <div className="flex flex-col gap-1.5">
                    <label className="text-[11px] font-semibold uppercase tracking-wider flex items-center" style={{ color: 'rgb(var(--text-muted))' }}>
                      Definir Nova Senha (Opcional)
                      <TooltipHelp content="Preencha apenas se desejar alterar/redefinir a senha de acesso deste colaborador. Mínimo de 8 caracteres." />
                    </label>
                    <input
                      type="password"
                      value={editUserPassword}
                      onChange={e => setEditUserPassword(e.target.value)}
                      placeholder="Deixe em branco para manter a atual"
                      className="py-2.5 px-3.5 text-xs lumina-input"
                    />
                  </div>
                </div>

                <div className="flex gap-2.5 pt-2">
                  <button
                    type="button"
                    onClick={() => setIsEditOpen(false)}
                    className="flex-1 py-2.5 rounded-xl border border-zinc-300 dark:border-zinc-800 text-xs font-semibold hover:bg-zinc-100 dark:hover:bg-zinc-850 transition-colors"
                    style={{ color: 'rgb(var(--text-secondary))' }}
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="flex-1 py-2.5 rounded-xl bg-lumina-gradient text-white text-xs font-semibold shadow-lumina transition-all hover:scale-102 flex items-center justify-center gap-1.5 disabled:opacity-50"
                  >
                    {submitting ? (
                      <Loader2 className="animate-spin" size={14} />
                    ) : (
                      <span>Salvar Alterações</span>
                    )}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}

