'use client'

/**
 * LuminaAI — Componente de Tooltip Interativo (?) v3.0
 * --------------------------------------------------
 * Exibe um balão explicativo estilizado com glassmorphism ao ser clicado.
 * Usa React Portals para renderizar fora do DOM do card, evitando que seja
 * cortado por contêineres com 'overflow: hidden'.
 * Ajusta o posicionamento horizontal dinamicamente para não estourar a tela.
 */

import React, { useState, useRef, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { HelpCircle } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface TooltipHelpProps {
  content: string
}

export function TooltipHelp({ content }: TooltipHelpProps) {
  const [isOpen, setIsOpen] = useState(false)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const [position, setPosition] = useState({
    bottom: 0,
    left: 0,
    transform: 'translateX(-50%)',
    arrowLeft: '50%',
  })

  // Calcula a posição do tooltip em relação ao botão no viewport
  const updatePosition = () => {
    if (!buttonRef.current) return
    const rect = buttonRef.current.getBoundingClientRect()
    const tooltipWidth = 256 // w-64 = 16rem = 256px
    const halfWidth = tooltipWidth / 2
    const screenWidth = window.innerWidth

    let left = rect.left + rect.width / 2
    let transform = 'translateX(-50%)'
    let arrowLeft = '50%'

    // Ajusta se estiver prestes a estourar a tela à direita
    if (left + halfWidth > screenWidth - 16) {
      left = rect.right
      transform = 'translateX(-100%)'
      arrowLeft = `calc(100% - ${rect.width / 2}px)`
    }
    // Ajusta se estiver prestes a estourar a tela à esquerda
    else if (left - halfWidth < 16) {
      left = rect.left
      transform = 'translateX(0%)'
      arrowLeft = `${rect.width / 2}px`
    }

    // Posiciona logo acima do botão (Fixed)
    const bottom = window.innerHeight - rect.top + 8

    setPosition({
      bottom,
      left,
      transform,
      arrowLeft,
    })
  }

  // Fecha o tooltip automaticamente ao clicar fora
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      const target = event.target as Node
      if (
        tooltipRef.current && 
        !tooltipRef.current.contains(target) &&
        buttonRef.current &&
        !buttonRef.current.contains(target)
      ) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      updatePosition()
      document.addEventListener('mousedown', handleClickOutside)
      window.addEventListener('resize', updatePosition)
      window.addEventListener('scroll', updatePosition, true)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition, true)
    }
  }, [isOpen])

  return (
    <div className="relative inline-flex items-center ml-1.5 z-30">
      <button
        ref={buttonRef}
        type="button"
        onClick={(e) => {
          e.preventDefault()
          e.stopPropagation()
          setIsOpen(!isOpen)
        }}
        className="text-zinc-500 hover:text-lumina-400 transition-colors p-0.5 rounded focus:outline-none inline-flex items-center justify-center cursor-pointer select-none"
        title="Clique para saber mais"
      >
        <HelpCircle size={13} />
      </button>

      {isOpen && typeof document !== 'undefined' && createPortal(
        <AnimatePresence>
          <motion.div
            ref={tooltipRef}
            initial={{ opacity: 0, scale: 0.95, y: 5 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 5 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            style={{
              position: 'fixed',
              bottom: position.bottom,
              left: position.left,
              transform: position.transform,
              width: '256px',
              zIndex: 99999, // Fica sobre absolutamente tudo
            }}
            className="p-3 rounded-xl border border-zinc-300 dark:border-zinc-800 bg-white dark:bg-zinc-950 shadow-2xl backdrop-blur-md text-xs text-zinc-700 dark:text-zinc-300 font-normal leading-relaxed text-left select-none pointer-events-auto"
          >
            {content}
            {/* Indicador / Triângulo apontando para baixo */}
            <div 
              style={{ left: position.arrowLeft }}
              className="absolute top-full -translate-x-1/2 -translate-y-1 w-2 h-2 bg-white dark:bg-zinc-950 border-r border-b border-zinc-300 dark:border-zinc-800 rotate-45" 
            />
          </motion.div>
        </AnimatePresence>,
        document.body
      )}
    </div>
  )
}
