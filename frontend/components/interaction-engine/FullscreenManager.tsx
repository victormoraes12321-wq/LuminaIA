'use client';

/**
 * ============================================================
 * LUMINA AI — Fullscreen Manager (Interaction Engine)
 * ============================================================
 * Provides a fullscreen portal overlay for any dashboard
 * component. Manages keyboard (Escape), focus trap, and
 * smooth enter/exit animations.
 * ============================================================
 */

import React, { useEffect, useCallback, memo } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Maximize2, Minimize2 } from 'lucide-react';
import { cn } from '@/lib/utils';

// ─────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────

interface FullscreenManagerProps {
  /** Component ID being expanded */
  componentId: string | null;
  /** Title of the expanded component */
  title?: string;
  /** Content to render fullscreen */
  children: React.ReactNode;
  /** Called when the user closes fullscreen */
  onClose: () => void;
  /** Extra class for the content wrapper */
  className?: string;
}

// ─────────────────────────────────────────────
// COMPONENT
// ─────────────────────────────────────────────

export const FullscreenManager = memo(function FullscreenManager({
  componentId,
  title,
  children,
  onClose,
  className,
}: FullscreenManagerProps) {
  const isOpen = !!componentId;

  // Keyboard: Escape to close
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose();
    },
    [isOpen, onClose],
  );

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isOpen, handleKeyDown]);

  if (typeof document === 'undefined') return null;

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            key="fullscreen-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm"
            onClick={onClose}
            aria-hidden="true"
          />

          {/* Panel */}
          <motion.div
            key="fullscreen-panel"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            className={cn(
              'fixed inset-4 z-50 md:inset-8 flex flex-col',
              'rounded-2xl border border-white/[0.08]',
              'bg-[#0d0d14] shadow-2xl overflow-hidden',
              className,
            )}
            role="dialog"
            aria-modal="true"
            aria-label={title ?? 'Componente expandido'}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.06] shrink-0">
              <div className="flex items-center gap-2">
                <Maximize2 className="h-4 w-4 text-[#6C63FF]" aria-hidden="true" />
                {title && (
                  <span className="text-sm font-semibold text-white/80">{title}</span>
                )}
              </div>
              <button
                onClick={onClose}
                className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-white/50
                  hover:text-white hover:bg-white/5 transition-all"
                aria-label="Fechar visualização expandida"
              >
                <Minimize2 className="h-3.5 w-3.5" />
                <span>Fechar</span>
                <kbd className="hidden md:inline text-[10px] text-white/30 border border-white/10 rounded px-1 py-0.5 ml-1">
                  Esc
                </kbd>
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto p-4">
              {children}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>,
    document.body,
  );
});

// ─────────────────────────────────────────────
// EXPAND BUTTON (embedded in component cards)
// ─────────────────────────────────────────────

interface ExpandButtonProps {
  componentId: string;
  isExpanded: boolean;
  onExpand: (id: string | null) => void;
  className?: string;
}

export const ExpandButton = memo(function ExpandButton({
  componentId,
  isExpanded,
  onExpand,
  className,
}: ExpandButtonProps) {
  return (
    <button
      onClick={() => onExpand(isExpanded ? null : componentId)}
      className={cn(
        'flex h-6 w-6 items-center justify-center rounded-md',
        'text-white/30 hover:text-white/80 hover:bg-white/5 transition-all',
        className,
      )}
      aria-label={isExpanded ? 'Minimizar' : 'Expandir tela cheia'}
      aria-pressed={isExpanded}
    >
      {isExpanded
        ? <Minimize2 className="h-3.5 w-3.5" />
        : <Maximize2 className="h-3.5 w-3.5" />}
    </button>
  );
});
