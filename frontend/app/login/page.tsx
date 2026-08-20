'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Mail, Lock, Sparkles, AlertCircle, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { ThemeToggle } from '@/components/ThemeToggle'

export default function LoginPage() {
  const { login, error, loading, clearError } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)
    clearError()

    if (!email.trim() || !password.trim()) {
      setFormError('Por favor, preencha todos os campos.')
      return
    }

    try {
      await login(email, password)
    } catch (_err) {
      // O erro é tratado no AuthContext e disponibilizado via useAuth().error
    }
  }

  const activeError = formError || error

  return (
    <main className="relative min-h-[100dvh] flex items-center justify-center p-4 overflow-hidden bg-[rgb(var(--bg-base))]">
      {/* Background visual effects */}
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
        className="w-full max-w-[420px] z-10"
      >
        {/* Logo Header */}
        <div className="flex flex-col items-center mb-8">
          <div className="relative w-12 h-12 mb-3">
            <div className="w-12 h-12 rounded-2xl bg-lumina-gradient flex items-center justify-center shadow-lumina">
              <Sparkles size={22} className="text-white" />
            </div>
            <div className="absolute -inset-1 rounded-2xl bg-lumina-500/20 blur-md -z-10" />
          </div>
          <h1 className="text-2xl font-bold text-gradient leading-tight">LuminaAI</h1>
          <p className="text-xs mt-1" style={{ color: 'rgb(var(--text-muted))' }}>
            Consulte seus dados corporativos de forma inteligente
          </p>
        </div>

        {/* Card Form */}
        <div 
          className="glass rounded-[20px] p-6 md:p-8"
          style={{
            background: 'rgb(var(--glass-bg) / 0.5)',
            borderColor: 'rgb(var(--border) / 0.4)'
          }}
        >
          <h2 className="text-lg font-bold mb-6" style={{ color: 'rgb(var(--text-primary))' }}>
            Faça login em sua conta
          </h2>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* E-mail field */}
            <div className="space-y-1.5">
              <label 
                htmlFor="email" 
                className="text-xs font-semibold select-none"
                style={{ color: 'rgb(var(--text-secondary))' }}
              >
                E-mail corporativo
              </label>
              <div className="relative">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2" style={{ color: 'rgb(var(--text-muted))' }}>
                  <Mail size={16} />
                </span>
                <input
                  id="email"
                  type="email"
                  placeholder="nome@empresa.com"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value)
                    setFormError(null)
                  }}
                  disabled={loading}
                  className="w-full pl-10 pr-4 py-3 text-sm rounded-xl lumina-input bg-[rgb(var(--bg-elevated))]/40"
                  style={{
                    borderColor: 'rgb(var(--border) / 0.6)',
                  }}
                />
              </div>
            </div>

            {/* Password field */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label 
                  htmlFor="password" 
                  className="text-xs font-semibold select-none"
                  style={{ color: 'rgb(var(--text-secondary))' }}
                >
                  Senha
                </label>
              </div>
              <div className="relative">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2" style={{ color: 'rgb(var(--text-muted))' }}>
                  <Lock size={16} />
                </span>
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Digite sua senha"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value)
                    setFormError(null)
                  }}
                  disabled={loading}
                  className="w-full pl-10 pr-10 py-3 text-sm rounded-xl lumina-input bg-[rgb(var(--bg-elevated))]/40"
                  style={{
                    borderColor: 'rgb(var(--border) / 0.6)',
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 hover:text-white/80 transition-colors"
                  style={{ color: 'rgb(var(--text-muted))' }}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Error Message */}
            <AnimatePresence mode="wait">
              {activeError && (
                <motion.div
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.2 }}
                  className="flex items-start gap-2.5 p-3.5 rounded-xl border"
                  style={{
                    background: 'rgb(var(--danger) / 0.08)',
                    borderColor: 'rgb(var(--danger) / 0.2)',
                    color: 'rgb(var(--danger))'
                  }}
                >
                  <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />
                  <span className="text-xs leading-relaxed font-medium">{activeError}</span>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Submit Button */}
            <motion.button
              type="submit"
              disabled={loading}
              className="w-full relative py-3 text-sm font-semibold rounded-xl text-white select-none transition-all"
              style={{
                background: 'linear-gradient(135deg, rgb(var(--accent)) 0%, #8B83FF 100%)',
                boxShadow: '0 4px 16px rgb(var(--accent) / 0.25)',
              }}
              whileHover={{ scale: 1.02, filter: 'brightness(1.08)' }}
              whileTap={{ scale: 0.98 }}
            >
              {loading ? (
                <div className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <span>Autenticando...</span>
                </div>
              ) : (
                <span>Entrar</span>
              )}
            </motion.button>
          </form>
        </div>
      </motion.div>
    </main>
  )
}
