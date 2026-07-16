'use client';

/**
 * ============================================================
 * LUMINA AI — Alert Banner (ECE Component)
 * ============================================================
 * Renders backend-driven alert banners with severity levels.
 * Used for business alerts, thresholds, and system notices.
 * ============================================================
 */

import React, { memo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, AlertCircle, Info, CheckCircle2, X } from 'lucide-react';
import { cn } from '@/lib/utils';

// ─────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────

export type AlertSeverity = 'info' | 'warning' | 'error' | 'success';

export interface AlertBannerData {
  severity: AlertSeverity;
  title: string;
  message?: string;
  dismissible?: boolean;
  action_label?: string;
  action_url?: string;
}

// ─────────────────────────────────────────────
// SEVERITY CONFIG
// ─────────────────────────────────────────────

const SEVERITY_CONFIG: Record<AlertSeverity, {
  icon: React.FC<{ className?: string }>;
  container: string;
  title: string;
  message: string;
  iconClass: string;
}> = {
  info:    { icon: Info,          container: 'border-blue-500/20 bg-blue-500/[0.06]',   title: 'text-blue-300',  message: 'text-blue-400/70',  iconClass: 'text-blue-400'  },
  warning: { icon: AlertTriangle, container: 'border-amber-500/20 bg-amber-500/[0.06]', title: 'text-amber-300', message: 'text-amber-400/70', iconClass: 'text-amber-400' },
  error:   { icon: AlertCircle,   container: 'border-red-500/20 bg-red-500/[0.06]',     title: 'text-red-300',   message: 'text-red-400/70',   iconClass: 'text-red-400'   },
  success: { icon: CheckCircle2,  container: 'border-green-500/20 bg-green-500/[0.06]', title: 'text-green-300', message: 'text-green-400/70', iconClass: 'text-green-400' },
};

// ─────────────────────────────────────────────
// COMPONENT
// ─────────────────────────────────────────────

interface AlertBannerProps {
  data: AlertBannerData;
  className?: string;
}

export const AlertBanner = memo(function AlertBanner({
  data,
  className,
}: AlertBannerProps) {
  const [dismissed, setDismissed] = useState(false);
  const config = SEVERITY_CONFIG[data.severity];
  const Icon = config.icon;

  return (
    <AnimatePresence>
      {!dismissed && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8, height: 0 }}
          transition={{ duration: 0.25 }}
          className={cn(
            'flex items-start gap-3 rounded-xl border px-4 py-3 w-full',
            config.container,
            className,
          )}
          role="alert"
          aria-live="assertive"
          aria-label={`${data.severity}: ${data.title}`}
        >
          <Icon className={cn('h-4 w-4 mt-0.5 shrink-0', config.iconClass)} aria-hidden="true" />

          <div className="flex-1 min-w-0">
            <p className={cn('text-sm font-medium', config.title)}>{data.title}</p>
            {data.message && (
              <p className={cn('text-xs mt-0.5', config.message)}>{data.message}</p>
            )}
            {data.action_label && data.action_url && (
              <a
                href={data.action_url}
                className={cn('mt-2 inline-block text-xs font-medium underline underline-offset-2', config.title)}
                target="_blank"
                rel="noopener noreferrer"
              >
                {data.action_label}
              </a>
            )}
          </div>

          {data.dismissible && (
            <button
              onClick={() => setDismissed(true)}
              className={cn('shrink-0 opacity-60 hover:opacity-100 transition-opacity', config.iconClass)}
              aria-label="Fechar alerta"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
});
