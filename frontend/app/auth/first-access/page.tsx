'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ShieldAlert, Check, X, Sparkles, KeyRound, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { ThemeToggle } from '@/components/ThemeToggle'

export default function FirstAccessPage() {
  const { changePassword, login, user, error, loading, clearError } = useAuth()
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showOldPassword, setShowOldPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  
  const [formError, setFormError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  // Password Validation Rules
  const hasMinLen = newPassword.length >= 8
  const hasDigit = /\d/.test(newPassword)
  const hasSpecial = /[!@#$%^&*()_+\-=\[\]{};':",\\|.<>\/?]/.test(newPassword)
  const passwordsMatch = newPassword === confirmPassword && newPassword !== ''

  const isPasswordValid = hasMinLen && hasDigit && hasSpecial

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)
    clearError()

    if (!oldPassword.trim() || !newPassword.trim() || !confirmPassword.trim()) {
      setFormError('Por favor, preencha todos os campos.')
      return
    }

    if (!isPasswordValid) {
      setFormError('A nova senha não atende a todos os requisitos de segurança.')
      return
    }

    if (!passwordsMatch) {
      setFormError('A confirmação da senha não coincide com a nova senha.')
      return
    }

    try {
      // 1. Envia a troca de senha para o backend
      await changePassword(oldPassword, newPassword)
      
      // 2. Transiciona para o estado de sucesso
      setSuccess(true)
      
      // 3. Efetua o login sob o capô com a nova senha para gerar o novo JWT correto com must_change_password = False
      const userEmail = user?.email || ''
      
      setTimeout(async () => {
        try {
          await login(userEmail, newPassword)
        } catch (_loginErr) {
          // Se falhar o re-login sob o capô, joga para o login
          window.location.href = '/login'
        }
      }, 2000)
      
    } catch (_err) {
      // O erro é tratado no AuthContext e exposto via useAuth().error
    }
  }

  const activeError = formError || error

  return (
    <main className="relative min-h-[100dvh] flex items-center justify-center p-4 overflow-hidden bg-[rgb(var(--bg-base))]">
      {/* Background effects */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-lumina-500/10 blur-[120px] pointer-events-none -z-10" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-teal-400/10 blur-[120px] pointer-events-none -z-10" />

      {/* Floating Theme Toggle */}
      <div className="absolute top-4 right-4 z-50">
        <ThemeToggle size="md" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 30, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="w-full max-w-[450px] z-10"
      >
        <AnimatePresence mode="wait">
          {!success ? (
            <motion.div
              key="form-card"
              exit={{ opacity: 0, scale: 0.95 }}
              className="glass rounded-[20px] p-6 md:p-8"
              style={{
                background: 'rgb(var(--glass-bg) / 0.5)',
                borderColor: 'rgb(var(--border) / 0.4)'
              }}
            >
              {/* Header */}
              <div className="flex flex-col items-center text-center mb-6">
                <div className="w-10 h-10 rounded-xl bg-lumina-500/15 flex items-center justify-center mb-3">
                  <KeyRound size={20} className="text-lumina-400" />
                </div>
                <h2 className="text-lg font-bold" style={{ color: 'rgb(var(--text-primary))' }}>
                  Primeiro Acesso
                </h2>
                <p className="text-xs mt-1 leading-relaxed max-w-[280px]" style={{ color: 'rgb(var(--text-muted))' }}>
                  Para garantir a segurança, você precisa alterar sua senha temporária.
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Old Password field */}
                <div className="space-y-1">
                  <label htmlFor="oldPassword" className="text-xs font-semibold" style={{ color: 'rgb(var(--text-secondary))' }}>
                    Senha Atual (Temporária)
                  </label>
                  <div className="relative">
                    <input
                      id="oldPassword"
                      type={showOldPassword ? 'text' : 'password'}
                      placeholder="Digite a senha temporária"
                      value={oldPassword}
                      onChange={(e) => setOldPassword(e.target.value)}
                      disabled={loading}
                      className="w-full pl-4 pr-10 py-2.5 text-sm rounded-xl lumina-input bg-[rgb(var(--bg-elevated))]/40"
                    />
                    <button
                      type="button"
                      onClick={() => setShowOldPassword(!showOldPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 hover:text-white/80 transition-colors"
                      style={{ color: 'rgb(var(--text-muted))' }}
                    >
                      {showOldPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                  </div>
                </div>

                {/* New Password field */}
                <div className="space-y-1">
                  <label htmlFor="newPassword" className="text-xs font-semibold" style={{ color: 'rgb(var(--text-secondary))' }}>
                    Nova Senha
                  </label>
                  <div className="relative">
                    <input
                      id="newPassword"
                      type={showNewPassword ? 'text' : 'password'}
                      placeholder="Digite a nova senha segura"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      disabled={loading}
                      className="w-full pl-4 pr-10 py-2.5 text-sm rounded-xl lumina-input bg-[rgb(var(--bg-elevated))]/40"
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 hover:text-white/80 transition-colors"
                      style={{ color: 'rgb(var(--text-muted))' }}
                    >
                      {showNewPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                  </div>
                </div>

                {/* Confirm Password field */}
                <div className="space-y-1">
                  <label htmlFor="confirmPassword" className="text-xs font-semibold" style={{ color: 'rgb(var(--text-secondary))' }}>
                    Confirme a Nova Senha
                  </label>
                  <div className="relative">
                    <input
                      id="confirmPassword"
                      type={showConfirmPassword ? 'text' : 'password'}
                      placeholder="Confirme a nova senha"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      disabled={loading}
                      className="w-full pl-4 pr-10 py-2.5 text-sm rounded-xl lumina-input bg-[rgb(var(--bg-elevated))]/40"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 hover:text-white/80 transition-colors"
                      style={{ color: 'rgb(var(--text-muted))' }}
                    >
                      {showConfirmPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                  </div>
                </div>

                {/* Password Strength Validation Checklist */}
                <div className="p-3 rounded-xl bg-[rgb(var(--bg-elevated))]/30 border border-slate-700/10 space-y-2">
                  <p className="text-[10px] font-bold uppercase tracking-wide" style={{ color: 'rgb(var(--text-muted))' }}>
                    Requisitos de Segurança da Senha
                  </p>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
                    {[
                      { validated: hasMinLen, label: 'Mínimo de 8 caracteres' },
                      { validated: hasDigit, label: 'Pelo menos um número' },
                      { validated: hasSpecial, label: 'Caractere especial (!@#$)' },
                      { validated: passwordsMatch, label: 'Senhas coincidem' },
                    ].map((req, i) => (
                      <div key={i} className="flex items-center gap-1.5 select-none">
                        <span
                          className={`w-3.5 h-3.5 rounded-full flex items-center justify-center transition-colors ${
                            req.validated ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-500/10 text-slate-500'
                          }`}
                        >
                          {req.validated ? <Check size={9} strokeWidth={3} /> : <X size={9} strokeWidth={3} />}
                        </span>
                        <span
                          className={`text-[11px] leading-tight transition-colors ${
                            req.validated ? 'text-emerald-400' : 'text-slate-400'
                          }`}
                          style={!req.validated ? { color: 'rgb(var(--text-muted))' } : undefined}
                        >
                          {req.label}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Error Message */}
                <AnimatePresence mode="wait">
                  {activeError && (
                    <motion.div
                      initial={{ opacity: 0, y: -5 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -5 }}
                      className="flex items-start gap-2.5 p-3 rounded-xl border text-xs"
                      style={{
                        background: 'rgb(var(--danger) / 0.08)',
                        borderColor: 'rgb(var(--danger) / 0.2)',
                        color: 'rgb(var(--danger))'
                      }}
                    >
                      <ShieldAlert size={14} className="flex-shrink-0 mt-0.5" />
                      <span className="font-medium">{activeError}</span>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Submit Button */}
                <motion.button
                  type="submit"
                  disabled={loading || !isPasswordValid || !passwordsMatch}
                  className={`w-full py-2.5 text-sm font-semibold rounded-xl text-white select-none transition-all ${
                    (!isPasswordValid || !passwordsMatch) ? 'opacity-50 cursor-not-allowed' : ''
                  }`}
                  style={{
                    background: 'linear-gradient(135deg, rgb(var(--accent)) 0%, #8B83FF 100%)',
                    boxShadow: (!isPasswordValid || !passwordsMatch) ? 'none' : '0 4px 16px rgb(var(--accent) / 0.25)',
                  }}
                  whileHover={(!isPasswordValid || !passwordsMatch) ? {} : { scale: 1.01, filter: 'brightness(1.06)' }}
                  whileTap={(!isPasswordValid || !passwordsMatch) ? {} : { scale: 0.99 }}
                >
                  {loading ? (
                    <div className="flex items-center justify-center gap-2">
                      <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      <span>Atualizando senha...</span>
                    </div>
                  ) : (
                    <span>Salvar Nova Senha</span>
                  )}
                </motion.button>
              </form>
            </motion.div>
          ) : (
            <motion.div
              key="success-card"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="glass rounded-[20px] p-8 text-center flex flex-col items-center"
              style={{
                background: 'rgb(var(--glass-bg) / 0.6)',
                borderColor: 'rgb(var(--border) / 0.5)'
              }}
            >
              <div className="relative w-16 h-16 mb-4">
                <motion.div
                  className="absolute inset-0 rounded-full bg-emerald-500/20 blur-md"
                  animate={{ scale: [1, 1.2, 1], opacity: [0.6, 0.3, 0.6] }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
                <div className="relative w-16 h-16 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center">
                  <Check size={28} className="text-emerald-400" />
                </div>
              </div>
              
              <h2 className="text-xl font-bold mb-2 text-gradient">Senha Atualizada!</h2>
              <p className="text-sm max-w-[280px]" style={{ color: 'rgb(var(--text-secondary))' }}>
                Sua senha foi redefinida com sucesso. Redirecionando para a Dashboard...
              </p>
              
              <div className="mt-6 flex items-center gap-1.5 text-xs text-lumina-400 font-medium select-none">
                <Sparkles size={13} className="animate-pulse" />
                <span>Inicializando dashboard segura...</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </main>
  )
}
