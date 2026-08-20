'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  CircleSlash2,
  Clock3,
  Database,
  Download,
  Info,
  LineChart,
  LockKeyhole,
  Maximize2,
  Minus,
  ShieldCheck,
  Table2,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ComparisonChart } from './ComparisonChart'
import { calculationLabel, directionLabel, formatDateTime } from './comparisonFormatters'
import { downloadComparisonCsv } from './comparisonExport'
import type {
  ComparisonCalculationPresentation,
  ComparisonDirection,
  ComparisonPresentationModel,
  ComparisonPresentationStatus,
  ComparisonVisualizationPresentation,
} from './comparisonPresentationTypes'

interface ComparisonRendererProps {
  model: ComparisonPresentationModel
  className?: string
}

const STATE_CONTENT: Record<
  ComparisonPresentationStatus,
  { title: string; description: string; icon: typeof Info }
> = {
  SUCCESS: {
    title: 'Comparacao concluida',
    description: 'Todos os dados recebidos estao disponiveis para analise.',
    icon: CheckCircle2,
  },
  PARTIAL: {
    title: 'Resultado parcial',
    description: 'Parte da comparacao nao foi concluida. Considere reduzir o periodo ou os filtros.',
    icon: AlertTriangle,
  },
  EMPTY: {
    title: 'Nenhum registro encontrado',
    description: 'A execucao foi valida, mas nao encontrou valores para os filtros informados.',
    icon: Info,
  },
  NOT_APPLICABLE: {
    title: 'Calculo nao aplicavel',
    description: 'O backend informou que esta comparacao nao possui resultado aplicavel.',
    icon: CircleSlash2,
  },
  CLARIFICATION_REQUIRED: {
    title: 'Mais informacoes necessarias',
    description: 'A pergunta precisa ser detalhada antes de executar a comparacao.',
    icon: Info,
  },
  OUT_OF_SCOPE: {
    title: 'Fora do escopo analitico',
    description: 'A solicitacao nao corresponde a uma analise disponivel.',
    icon: CircleSlash2,
  },
  UNSUPPORTED: {
    title: 'Comparacao ainda nao suportada',
    description: 'O formato solicitado nao possui uma fonte ou regra governada.',
    icon: CircleSlash2,
  },
  BLOCKED: {
    title: 'Execucao bloqueada',
    description: 'A comparacao foi impedida por uma regra de seguranca ou permissao.',
    icon: LockKeyhole,
  },
  TIMEOUT: {
    title: 'Tempo limite atingido',
    description: 'A consulta nao terminou no tempo permitido e nao foi tratada como resultado vazio.',
    icon: Clock3,
  },
  ERROR: {
    title: 'Nao foi possivel apresentar a comparacao',
    description: 'O contrato ou a execucao retornou uma falha que precisa ser revisada.',
    icon: AlertTriangle,
  },
}

function DirectionIcon({ direction }: { direction: ComparisonDirection }) {
  if (direction === 'INCREASE') return <ArrowUpRight aria-hidden="true" className="h-4 w-4" />
  if (direction === 'DECREASE') return <ArrowDownRight aria-hidden="true" className="h-4 w-4" />
  if (direction === 'STABLE') return <Minus aria-hidden="true" className="h-4 w-4" />
  return <CircleSlash2 aria-hidden="true" className="h-4 w-4" />
}

function StateBanner({ model }: { model: ComparisonPresentationModel }) {
  const content = STATE_CONTENT[model.status]
  const Icon = content.icon
  const show = model.status !== 'SUCCESS' || model.partial || model.truncated
  if (!show) return null
  return (
    <div
      role={model.status === 'ERROR' || model.status === 'BLOCKED' ? 'alert' : 'status'}
      aria-live="polite"
      className="flex items-start gap-3 border-y border-amber-500/30 bg-amber-500/8 px-3 py-3 text-sm"
      data-testid="comparison-state-banner"
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" aria-hidden="true" />
      <div className="min-w-0">
        <p className="font-semibold text-zinc-900 dark:text-zinc-100">{content.title}</p>
        <p className="mt-0.5 text-xs leading-relaxed text-zinc-600 dark:text-zinc-400">
          {content.description}
          {model.truncated ? ' O payload recebido esta truncado.' : ''}
        </p>
      </div>
    </div>
  )
}

function ComparisonSummary({ model }: { model: ComparisonPresentationModel }) {
  return (
    <header className="space-y-3" data-testid="comparison-summary">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase text-indigo-600 dark:text-indigo-400">
            Analise comparativa
          </p>
          <h3 className="mt-1 break-words text-lg font-bold text-zinc-950 dark:text-white">
            {model.title}
          </h3>
          <p className="mt-1 max-w-3xl text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
            {model.subtitle}
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2 text-xs">
          <span className="inline-flex items-center gap-1.5 rounded-md border border-zinc-300 px-2 py-1 text-zinc-700 dark:border-zinc-700 dark:text-zinc-300">
            <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
            {model.validation.label}
          </span>
          {model.partial && (
            <span className="rounded-md border border-amber-500/40 px-2 py-1 text-amber-700 dark:text-amber-300">
              Parcial
            </span>
          )}
        </div>
      </div>
      {model.displayPolicy.volumeWarning && (
        <p className="text-xs text-zinc-500 dark:text-zinc-400">
          Visualizacao densa: todos os dados recebidos foram preservados. Use a tabela ou tela cheia para inspecionar.
        </p>
      )}
    </header>
  )
}

function OperandGrid({ model }: { model: ComparisonPresentationModel }) {
  return (
    <section aria-labelledby="comparison-operands-title">
      <h4 id="comparison-operands-title" className="mb-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
        Valores comparados
      </h4>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {model.operands.map(operand => (
          <article
            key={operand.operandId}
            className="min-w-0 rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-800 dark:bg-zinc-950"
            aria-label={operand.accessibilityLabel}
            data-testid="comparison-operand-card"
          >
            <div className="flex items-start justify-between gap-2">
              <p className="min-w-0 break-words text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                {operand.label}
              </p>
              <span className="shrink-0 rounded-md bg-zinc-100 px-1.5 py-0.5 text-[10px] font-semibold text-zinc-600 dark:bg-zinc-900 dark:text-zinc-400">
                {operand.isBaseline ? 'Base' : 'Comparado'}
              </span>
            </div>
            <p className="mt-3 break-words text-xl font-bold text-zinc-950 dark:text-white">
              {operand.formattedValue}
            </p>
            <p className="mt-1 break-words text-[11px] text-zinc-500 dark:text-zinc-400">
              {[operand.metricLabel, operand.periodLabel, operand.entityLabel].filter(Boolean).join(' | ')}
            </p>
            {operand.valueState !== 'VALUE' && operand.valueState !== 'ZERO' && (
              <p className="mt-2 text-[11px] font-medium text-amber-700 dark:text-amber-300">
                Estado: {operand.valueState.replace(/_/g, ' ').toLocaleLowerCase('pt-BR')}
              </p>
            )}
          </article>
        ))}
      </div>
    </section>
  )
}

function CalculationGrid({ calculations }: { calculations: ComparisonCalculationPresentation[] }) {
  if (calculations.length === 0) return null
  const visible = calculations.filter((item, index, values) =>
    values.findIndex(candidate =>
      candidate.calculation === item.calculation &&
      candidate.targetOperandId === item.targetOperandId &&
      candidate.alignmentKey === item.alignmentKey,
    ) === index,
  )
  return (
    <section aria-labelledby="comparison-calculations-title">
      <h4 id="comparison-calculations-title" className="mb-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
        Resultados calculados pelo backend
      </h4>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-4">
        {visible.slice(0, 12).map((calculation, index) => (
          <article
            key={`${calculation.calculation}-${calculation.targetOperandId}-${calculation.alignmentKey}-${index}`}
            className="rounded-lg border border-zinc-200 p-3 dark:border-zinc-800"
            aria-label={calculation.accessibilityLabel}
            data-testid={`comparison-calculation-${calculation.calculation.toLowerCase()}`}
          >
            <p className="text-[11px] font-semibold text-zinc-500 dark:text-zinc-400">
              {calculationLabel(calculation.calculation)}
            </p>
            <p className="mt-2 break-words text-lg font-bold text-zinc-950 dark:text-white">
              {calculation.formattedResult}
            </p>
            {calculation.calculation !== 'DIRECTION' && (
              <div className="mt-2 flex items-center gap-1.5 text-xs text-zinc-600 dark:text-zinc-300">
                <DirectionIcon direction={calculation.direction} />
                <span>{directionLabel(calculation.direction)}</span>
              </div>
            )}
            {calculation.zeroDenominator && (
              <p className="mt-2 text-[11px] text-amber-700 dark:text-amber-300">
                Nao aplicavel: denominador zero.
              </p>
            )}
          </article>
        ))}
      </div>
    </section>
  )
}

function ComparisonTable({ model }: { model: ComparisonPresentationModel }) {
  const [page, setPage] = useState(0)
  const pageSize = 50
  const rows = model.calculations
  const pageRows = rows.slice(page * pageSize, (page + 1) * pageSize)
  const pageCount = Math.max(1, Math.ceil(rows.length / pageSize))

  return (
    <section aria-labelledby="comparison-table-title" data-testid="comparison-table">
      <div className="mb-2 flex items-end justify-between gap-3">
        <div>
          <h4 id="comparison-table-title" className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            Tabela comparativa
          </h4>
          <p className="text-[11px] text-zinc-500">
            Valores e calculos exatamente como recebidos do backend.
          </p>
        </div>
        {model.truncated && (
          <span className="text-[11px] font-semibold text-amber-700 dark:text-amber-300">
            Resultado truncado
          </span>
        )}
      </div>
      <div className="max-w-full overflow-auto rounded-lg border border-zinc-200 dark:border-zinc-800" tabIndex={0}>
        <table className="w-full min-w-[760px] border-collapse text-left text-xs">
          <caption className="sr-only">
            Comparacao {model.title}, com valores, diferencas, percentuais, direcao e estado.
          </caption>
          <thead className="sticky top-0 z-10 bg-zinc-100 dark:bg-zinc-900">
            <tr>
              {['Calculo', 'Base', 'Comparado', 'Valor base', 'Valor comparado', 'Resultado', 'Direcao', 'Status'].map(label => (
                <th key={label} scope="col" className="whitespace-nowrap px-3 py-2.5 font-semibold text-zinc-700 dark:text-zinc-300">
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageRows.map((row, index) => (
              <tr
                key={`${row.calculation}-${row.targetOperandId}-${row.alignmentKey}-${index}`}
                className="border-t border-zinc-200 dark:border-zinc-800"
              >
                <th scope="row" className="px-3 py-2.5 font-medium text-zinc-900 dark:text-zinc-100">
                  {calculationLabel(row.calculation)}
                </th>
                <td className="px-3 py-2.5 text-zinc-600 dark:text-zinc-400">{row.baselineOperandId ?? 'Nao aplicavel'}</td>
                <td className="px-3 py-2.5 text-zinc-600 dark:text-zinc-400">{row.targetOperandId}</td>
                <td className="px-3 py-2.5 font-mono text-zinc-700 dark:text-zinc-300">{row.baselineRawValue ?? 'Sem valor'}</td>
                <td className="px-3 py-2.5 font-mono text-zinc-700 dark:text-zinc-300">{row.targetRawValue ?? 'Sem valor'}</td>
                <td className="px-3 py-2.5 font-semibold text-zinc-900 dark:text-white">{row.formattedResult}</td>
                <td className="px-3 py-2.5 text-zinc-600 dark:text-zinc-300">{directionLabel(row.direction)}</td>
                <td className="px-3 py-2.5 text-zinc-600 dark:text-zinc-300">{row.status}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-zinc-500">
                  Nenhum calculo comparativo foi recebido.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {pageCount > 1 && (
        <div className="mt-2 flex items-center justify-end gap-2 text-xs">
          <button
            type="button"
            onClick={() => setPage(current => Math.max(0, current - 1))}
            disabled={page === 0}
            className="rounded-md border border-zinc-300 px-2 py-1 disabled:opacity-40 dark:border-zinc-700"
          >
            Anterior
          </button>
          <span>Página {page + 1} de {pageCount}</span>
          <button
            type="button"
            onClick={() => setPage(current => Math.min(pageCount - 1, current + 1))}
            disabled={page >= pageCount - 1}
            className="rounded-md border border-zinc-300 px-2 py-1 disabled:opacity-40 dark:border-zinc-700"
          >
            Proxima
          </button>
        </div>
      )}
    </section>
  )
}

function ActualVsTarget({ model }: { model: ComparisonPresentationModel }) {
  if (model.comparisonKind !== 'ACTUAL_VS_TARGET') return null
  const actual = model.operands.find(item => item.isBaseline) ?? model.operands[0]
  const target = model.operands.find(item => item.isTarget) ?? model.operands[1]
  const gap = model.calculations.find(item => item.calculation === 'ABSOLUTE_DIFFERENCE')
  return (
    <section
      aria-labelledby="actual-target-title"
      className="border-y border-zinc-200 py-3 dark:border-zinc-800"
      data-testid="actual-vs-target"
    >
      <h4 id="actual-target-title" className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
        Realizado versus meta oficial
      </h4>
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div><p className="text-xs text-zinc-500">Realizado</p><p className="mt-1 font-bold">{actual?.formattedValue ?? 'Sem valor'}</p></div>
        <div><p className="text-xs text-zinc-500">Meta</p><p className="mt-1 font-bold">{target?.formattedValue ?? 'Meta ausente'}</p></div>
        <div><p className="text-xs text-zinc-500">Gap informado</p><p className="mt-1 font-bold">{gap?.formattedResult ?? 'Nao aplicavel'}</p></div>
      </div>
      <p className="mt-3 text-xs text-zinc-500">
        Nenhum gauge ou atingimento foi calculado no navegador.
      </p>
    </section>
  )
}

function ValidationPanel({ model }: { model: ComparisonPresentationModel }) {
  const [open, setOpen] = useState(false)
  return (
    <section className="border-t border-zinc-200 pt-3 dark:border-zinc-800" data-testid="comparison-validation">
      <button
        type="button"
        onClick={() => setOpen(value => !value)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 rounded-md px-1 py-1.5 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-500"
      >
        <span className="inline-flex items-center gap-2 text-sm font-semibold text-zinc-800 dark:text-zinc-200">
          <ShieldCheck className="h-4 w-4 text-indigo-600 dark:text-indigo-400" aria-hidden="true" />
          Validacao: {model.validation.label}
        </span>
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {open && (
        <div className="mt-2 space-y-2 text-xs text-zinc-600 dark:text-zinc-400">
          {model.validation.checks.length > 0 ? model.validation.checks.map(check => (
            <div key={check.code} className="flex items-start justify-between gap-3 border-b border-zinc-200 py-2 last:border-0 dark:border-zinc-800">
              <span>{check.message || check.code}</span>
              <span className="shrink-0 font-semibold">{check.status}</span>
            </div>
          )) : (
            <p>O perfil atual recebe apenas o estado resumido da validacao.</p>
          )}
        </div>
      )}
    </section>
  )
}

function ProvenancePanel({ model }: { model: ComparisonPresentationModel }) {
  const [open, setOpen] = useState(false)
  if (!model.displayPolicy.showProvenance || !model.provenance) return null
  const provenance = model.provenance
  return (
    <section className="border-t border-zinc-200 pt-3 dark:border-zinc-800" data-testid="comparison-provenance">
      <button
        type="button"
        onClick={() => setOpen(value => !value)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 rounded-md px-1 py-1.5 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-500"
      >
        <span className="inline-flex items-center gap-2 text-sm font-semibold text-zinc-800 dark:text-zinc-200">
          <Database className="h-4 w-4 text-cyan-700 dark:text-cyan-400" aria-hidden="true" />
          Origem e atualizacao
        </span>
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {open && (
        <dl className="mt-2 grid grid-cols-1 gap-x-5 gap-y-2 text-xs sm:grid-cols-2">
          <div><dt className="text-zinc-500">Fonte</dt><dd className="font-medium text-zinc-800 dark:text-zinc-200">{provenance.sourceLabel}</dd></div>
          <div><dt className="text-zinc-500">Atualizacao</dt><dd className="font-medium text-zinc-800 dark:text-zinc-200">{formatDateTime(provenance.updatedAt)}</dd></div>
          <div><dt className="text-zinc-500">Executor</dt><dd className="font-medium text-zinc-800 dark:text-zinc-200">{provenance.executorVersion ?? 'Nao informado'}</dd></div>
          <div><dt className="text-zinc-500">Cache</dt><dd className="font-medium text-zinc-800 dark:text-zinc-200">{provenance.cacheStatus ?? 'Nao informado'}</dd></div>
          {model.accessPolicy.role === 'ADMIN' && (
            <>
              <div><dt className="text-zinc-500">Planner</dt><dd className="font-medium text-zinc-800 dark:text-zinc-200">{provenance.plannerVersion ?? 'Nao informado'}</dd></div>
              <div><dt className="text-zinc-500">Normalizador</dt><dd className="font-medium text-zinc-800 dark:text-zinc-200">{provenance.normalizerVersion ?? 'Nao informado'}</dd></div>
            </>
          )}
        </dl>
      )}
    </section>
  )
}

function VisualizationBlock({
  model,
  visualization,
}: {
  model: ComparisonPresentationModel
  visualization: ComparisonVisualizationPresentation
}) {
  const icon = visualization.kind === 'TABLE'
    ? <Table2 className="h-4 w-4" aria-hidden="true" />
    : visualization.kind === 'LINE' || visualization.kind === 'AREA'
      ? <LineChart className="h-4 w-4" aria-hidden="true" />
      : <BarChart3 className="h-4 w-4" aria-hidden="true" />
  return (
    <section className="border-t border-zinc-200 pt-4 dark:border-zinc-800" data-testid="comparison-visualization">
      <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
        {icon}
        <h4>{visualization.title}</h4>
      </div>
      {!visualization.compatible ? (
        <div role="status" className="border-y border-amber-500/30 bg-amber-500/8 px-3 py-3 text-xs text-amber-800 dark:text-amber-200">
          {visualization.incompatibilityReason} A tabela foi mantida como fallback seguro.
          <div className="mt-3"><ComparisonTable model={model} /></div>
        </div>
      ) : visualization.kind === 'TABLE' ? (
        <ComparisonTable model={model} />
      ) : visualization.kind === 'KPI' ? (
        <CalculationGrid calculations={model.calculations} />
      ) : visualization.kind === 'BAR' || visualization.kind === 'LINE' ||
        visualization.kind === 'AREA' || visualization.kind === 'PIE' ? (
        <ComparisonChart model={model} visualization={visualization} />
      ) : (
        <ComparisonTable model={model} />
      )}
    </section>
  )
}

export function ComparisonRenderer({ model, className }: ComparisonRendererProps) {
  const [fullscreen, setFullscreen] = useState(false)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const hasResult = ![
    'CLARIFICATION_REQUIRED',
    'OUT_OF_SCOPE',
    'UNSUPPORTED',
    'BLOCKED',
    'TIMEOUT',
    'ERROR',
  ].includes(model.status)

  useEffect(() => {
    if (!fullscreen) return
    closeButtonRef.current?.focus()
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setFullscreen(false)
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [fullscreen])

  const uniqueVisualizations = useMemo(
    () => model.visualizations,
    [model.visualizations],
  )

  const content = (
    <div
      className={cn(
        'comparison-renderer w-full min-w-0 space-y-5 text-zinc-950 dark:text-zinc-100',
        fullscreen && 'mx-auto max-w-[1500px] p-4 sm:p-6',
        className,
      )}
      data-testid="comparison-renderer"
      data-presentation-version={model.presentationVersion}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1"><ComparisonSummary model={model} /></div>
        <div className="flex shrink-0 items-center gap-1">
          {model.exportPolicy.allowed && (
            <button
              type="button"
              onClick={() => downloadComparisonCsv(model)}
              className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-zinc-300 text-zinc-600 hover:bg-zinc-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-500 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-900"
              aria-label="Exportar comparacao em CSV"
              title="Exportar CSV"
            >
              <Download className="h-4 w-4" aria-hidden="true" />
            </button>
          )}
          {!fullscreen && (
            <button
              type="button"
              onClick={() => setFullscreen(true)}
              className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-zinc-300 text-zinc-600 hover:bg-zinc-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-500 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-900"
              aria-label="Abrir comparacao em tela cheia"
              title="Tela cheia"
            >
              <Maximize2 className="h-4 w-4" aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      <StateBanner model={model} />

      {hasResult && (
        <>
          <OperandGrid model={model} />
          <CalculationGrid calculations={model.calculations} />
          <ActualVsTarget model={model} />
          <div className="space-y-5">
            {uniqueVisualizations.map((visualization, index) => (
              <VisualizationBlock
                key={`${visualization.id}-${index}`}
                model={model}
                visualization={visualization}
              />
            ))}
          </div>
        </>
      )}

      {(model.alignment.missingBucketCount > 0 || model.alignment.nullBucketCount > 0) && (
        <div role="status" className="flex flex-wrap gap-x-4 gap-y-1 border-y border-zinc-200 py-2 text-xs text-zinc-600 dark:border-zinc-800 dark:text-zinc-400">
          {model.alignment.missingBucketCount > 0 && (
            <span>Sem registro: {model.alignment.missingBucketCount} bucket(s)</span>
          )}
          {model.alignment.nullBucketCount > 0 && (
            <span>Sem valor: {model.alignment.nullBucketCount} bucket(s)</span>
          )}
        </div>
      )}

      {model.warnings.length > 0 && (
        <div role="status" className="border-l-2 border-amber-500 pl-3 text-xs text-zinc-600 dark:text-zinc-400">
          {model.warnings.join(' ')}
        </div>
      )}
      {model.errors.length > 0 && (
        <div role="alert" className="border-l-2 border-rose-500 pl-3 text-xs text-zinc-700 dark:text-zinc-300">
          {model.errors.join(' ')}
        </div>
      )}

      <section
        aria-labelledby="comparison-trust-center-title"
        className="border-t border-zinc-200 pt-3 dark:border-zinc-800"
        data-testid="comparison-trust-center"
      >
        <h4
          id="comparison-trust-center-title"
          className="text-sm font-semibold text-zinc-900 dark:text-zinc-100"
        >
          Trust Center
        </h4>
        <ValidationPanel model={model} />
        <ProvenancePanel model={model} />
      </section>

      {model.displayPolicy.showTechnicalDetails && model.technicalMetadata && (
        <details className="border-t border-zinc-200 pt-3 text-xs dark:border-zinc-800" data-testid="comparison-technical-metadata">
          <summary className="cursor-pointer font-semibold text-zinc-700 dark:text-zinc-300">
            Metadados tecnicos permitidos
          </summary>
          <dl className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
            <div><dt className="text-zinc-500">Versao</dt><dd>{model.presentationVersion}</dd></div>
            <div><dt className="text-zinc-500">Estrategia</dt><dd>{model.technicalMetadata.strategy ?? 'Nao informada'}</dd></div>
            <div><dt className="text-zinc-500">Executor</dt><dd>{model.technicalMetadata.executorVersion ?? 'Nao informado'}</dd></div>
            <div><dt className="text-zinc-500">Cache</dt><dd>{model.technicalMetadata.cacheStatus ?? 'Nao informado'}</dd></div>
          </dl>
        </details>
      )}
    </div>
  )

  return (
    <>
      {!fullscreen && content}
      {fullscreen && (
        <div
          className="fixed inset-0 z-[70] overflow-y-auto bg-white dark:bg-zinc-950"
          role="dialog"
          aria-modal="true"
          aria-label={`Comparacao em tela cheia: ${model.title}`}
          data-testid="comparison-fullscreen"
        >
          <button
            ref={closeButtonRef}
            type="button"
            onClick={() => setFullscreen(false)}
            className="fixed right-4 top-4 z-10 inline-flex h-10 w-10 items-center justify-center rounded-md border border-zinc-300 bg-white text-zinc-700 shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200"
            aria-label="Fechar tela cheia"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
          {content}
        </div>
      )}
    </>
  )
}
