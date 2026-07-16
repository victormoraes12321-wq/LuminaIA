'use client';

/**
 * ============================================================
 * LUMINA AI — Runtime Renderer
 * ============================================================
 * Renders a single dashboard widget using the Component
 * Library Registry. Handles: card wrapper, title, expand
 * button, error boundary, and fullscreen integration.
 *
 * Rule: NEVER imports chart types directly. Uses registry.
 * ============================================================
 */

import React, { memo, Suspense } from 'react';
import { motion } from 'framer-motion';
import { RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { RuntimeWidget } from '@/types/dashboard-runtime';
import { getRegistryEntry } from '@/components/component-library/index';
import { SkeletonCard, ErrorState } from '@/components/component-library/status/StatusComponents';
import { ExpandButton } from '@/components/interaction-engine/FullscreenManager';

// ─────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────

interface RuntimeRendererProps {
  widget: RuntimeWidget;
  expandedComponentId: string | null;
  onExpand: (id: string | null) => void;
  isRefreshing?: boolean;
  animate?: boolean;
  animationDelay?: number;
}

// ─────────────────────────────────────────────
// ERROR BOUNDARY
// ─────────────────────────────────────────────

interface ErrorBoundaryState { hasError: boolean; error: string }

class WidgetErrorBoundary extends React.Component<
  { children: React.ReactNode; componentId: string },
  ErrorBoundaryState
> {
  constructor(props: { children: React.ReactNode; componentId: string }) {
    super(props);
    this.state = { hasError: false, error: '' };
  }

  static getDerivedStateFromError(err: Error): ErrorBoundaryState {
    return { hasError: true, error: err.message };
  }

  render() {
    if (this.state.hasError) {
      return (
        <ErrorState
          title="Erro ao renderizar componente"
          message={this.state.error}
          className="h-full"
        />
      );
    }
    return this.props.children;
  }
}

// ─────────────────────────────────────────────
// CARD WRAPPER
// ─────────────────────────────────────────────

interface CardWrapperProps {
  title?: string;
  subtitle?: string;
  expandable: boolean;
  componentId: string;
  expandedComponentId: string | null;
  onExpand: (id: string | null) => void;
  isRefreshing?: boolean;
  children: React.ReactNode;
  className?: string;
}

function CardWrapper({
  title,
  subtitle,
  expandable,
  componentId,
  expandedComponentId,
  onExpand,
  isRefreshing,
  children,
  className,
}: CardWrapperProps) {
  const isExpanded = expandedComponentId === componentId;
  const hasHeader = title || expandable;

  return (
    <div
      className={cn(
        'flex flex-col rounded-xl h-full overflow-hidden',
        'border transition-all duration-200',
        className,
      )}
      style={{
        background: 'rgb(var(--bg-surface) / 0.72)',
        borderColor: 'rgb(var(--border) / 0.55)',
      }}
    >
      {hasHeader && (
        <div className="flex items-start justify-between gap-2 px-4 pt-4 pb-0 shrink-0">
          {title && (
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-semibold truncate" style={{ color: 'rgb(var(--text-primary))' }}>
                {title}
              </h3>
              {subtitle && (
                <p className="text-xs truncate mt-0.5" style={{ color: 'rgb(var(--text-muted))' }}>{subtitle}</p>
              )}
            </div>
          )}
          <div className="flex items-center gap-1 shrink-0">
            {isRefreshing && (
              <RefreshCw className="h-3 w-3 text-[#6C63FF] animate-spin" aria-label="Atualizando..." />
            )}
            {expandable && (
              <ExpandButton
                componentId={componentId}
                isExpanded={isExpanded}
                onExpand={onExpand}
              />
            )}
          </div>
        </div>
      )}
      <div className="flex-1 overflow-hidden p-4">
        {children}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// RUNTIME RENDERER
// ─────────────────────────────────────────────

export const RuntimeRenderer = memo(function RuntimeRenderer({
  widget,
  expandedComponentId,
  onExpand,
  isRefreshing = false,
  animate = true,
  animationDelay = 0,
}: RuntimeRendererProps) {
  const meta = widget.ece_metadata;
  const registryEntry = getRegistryEntry(widget.component_type);

  // Widget has a backend error
  if (widget.error) {
    return (
      <ErrorState
        title="Dados indisponíveis"
        message={widget.error}
        className="h-full"
      />
    );
  }

  // Unknown component type
  if (!registryEntry) {
    return (
      <ErrorState
        title={`Tipo desconhecido: ${widget.component_type}`}
        className="h-full"
      />
    );
  }

  const Component = registryEntry.component;

  const componentNode = (
    <WidgetErrorBoundary componentId={widget.id}>
      <Suspense fallback={<SkeletonCard rows={3} className="h-full" />}>
        <Component data={widget.data} {...widget.data} />
      </Suspense>
    </WidgetErrorBoundary>
  );

  const content = registryEntry.hasWrapper ? (
    <CardWrapper
      title={meta.title}
      subtitle={meta.subtitle}
      expandable={meta.expandable}
      componentId={widget.id}
      expandedComponentId={expandedComponentId}
      onExpand={onExpand}
      isRefreshing={isRefreshing}
    >
      {componentNode}
    </CardWrapper>
  ) : (
    componentNode
  );

  if (!animate) return content;

  return (
    <motion.div
      key={widget.id}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.3,
        delay: animationDelay,
        ease: [0.22, 1, 0.36, 1],
      }}
      className="h-full"
      data-component-id={widget.id}
      data-component-type={widget.component_type}
      aria-label={meta.aria_label ?? meta.title}
    >
      {content}
    </motion.div>
  );
});
