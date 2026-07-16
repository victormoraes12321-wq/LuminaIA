'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { Sun, Moon } from 'lucide-react'
import { useTheme } from '@/context/ThemeContext'
import { cn } from '@/lib/utils'

// ── ThemeToggle ───────────────────────────────────────────────

interface ThemeToggleProps {
  size?: 'sm' | 'md'
  className?: string
}

export function ThemeToggle({ size = 'md', className }: ThemeToggleProps) {
  const { isDark, toggleTheme } = useTheme()

  const dim = size === 'sm' ? 'w-8 h-8' : 'w-9 h-9'
  const iconSize = size === 'sm' ? 14 : 16

  return (
    <motion.button
      aria-label={isDark ? 'Ativar tema claro' : 'Ativar tema escuro'}
      onClick={toggleTheme}
      className={cn(
        dim,
        'relative flex items-center justify-center rounded-xl',
        'transition-colors duration-200',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lumina-500/50',
        className,
      )}
      style={{
        background: isDark
          ? 'rgb(var(--bg-elevated))'
          : 'rgb(var(--bg-hover))',
        border: '1px solid rgb(var(--border) / 0.6)',
      }}
      whileHover={{ scale: 1.08 }}
      whileTap={{ scale: 0.92 }}
    >
      {/* Track glow */}
      <motion.span
        className="absolute inset-0 rounded-xl"
        animate={{ opacity: isDark ? 0 : 0.15 }}
        transition={{ duration: 0.3 }}
        style={{ background: 'radial-gradient(circle, #FECA57, transparent)' }}
      />

      {/* Icon swap */}
      <AnimatePresence mode="wait" initial={false}>
        {isDark ? (
          <motion.span
            key="moon"
            initial={{ rotate: -90, opacity: 0, scale: 0.5 }}
            animate={{ rotate: 0,   opacity: 1, scale: 1 }}
            exit={{   rotate:  90,  opacity: 0, scale: 0.5 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            className="flex items-center justify-center"
          >
            <Moon size={iconSize} className="text-lumina-400" />
          </motion.span>
        ) : (
          <motion.span
            key="sun"
            initial={{ rotate: 90, opacity: 0, scale: 0.5 }}
            animate={{ rotate: 0,  opacity: 1, scale: 1 }}
            exit={{   rotate: -90, opacity: 0, scale: 0.5 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            className="flex items-center justify-center"
          >
            <Sun size={iconSize} className="text-yellow-400" />
          </motion.span>
        )}
      </AnimatePresence>
    </motion.button>
  )
}
