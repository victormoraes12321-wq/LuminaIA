import type {
  AnalyticalComparison,
  AnalyticalDatasetV2,
  AnalyticalResponseV2,
  AnalyticalVisualization,
  AnyChartData,
  ChartDataBar,
  ChartType,
  JsonValue,
  QueryResponse,
  VisualizationItem,
} from '@/types/lumina'
import {
  calculationLabel,
  classifyRawValue,
  directionLabel,
  formatComparisonValue,
} from './comparisonFormatters'
import {
  COMPARISON_PRESENTATION_VERSION,
  ComparisonPresentationContractError,
} from './comparisonPresentationTypes'
import type {
  ComparisonCalculationPresentation,
  ComparisonDatasetPresentation,
  ComparisonDirection,
  ComparisonOperandPresentation,
  ComparisonPresentationModel,
  ComparisonPresentationStatus,
  ComparisonProvenancePresentation,
  ComparisonUserRole,
  ComparisonValidationPresentation,
  ComparisonVisualizationPresentation,
} from './comparisonPresentationTypes'

const VISUALIZATION_KIND_MAP: Record<string, ChartType> = {
  KPI_CARD: 'KPI',
  SUMMARY_CARD: 'KPI',
  DATA_TABLE: 'TABLE',
  BAR_CHART: 'BAR',
  LINE_CHART: 'LINE',
  AREA_CHART: 'AREA',
  PIE_CHART: 'PIE',
  DONUT_CHART: 'PIE',
  SCATTER_CHART: 'SCATTER',
  HEATMAP: 'HEATMAP',
  TREEMAP: 'TREEMAP',
  FUNNEL: 'FUNNEL',
  INSIGHTS_LIST: 'TABLE',
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function asString(value: unknown): string | null {
  return typeof value === 'string' ? value : null
}

function asBoolean(value: unknown): boolean | null {
  return typeof value === 'boolean' ? value : null
}

function asRawValue(value: unknown): string | number | null {
  return typeof value === 'string' || typeof value === 'number' ? value : null
}

function isDirection(value: unknown): value is ComparisonDirection {
  return value === 'INCREASE' || value === 'DECREASE' ||
    value === 'STABLE' || value === 'NOT_APPLICABLE'
}

function sanitizeText(value: unknown): string {
  if (typeof value !== 'string') return ''
  return value.length > 500 ? `${value.slice(0, 497)}...` : value
}

function rolePolicy(role: ComparisonUserRole) {
  if (role === 'ADMIN') {
    return {
      technicalLevel: 'FULL' as const,
      showTechnicalDetails: true,
      showProvenance: true,
      includeTechnicalMetadata: true,
    }
  }
  if (role === 'GESTOR') {
    return {
      technicalLevel: 'SUMMARY' as const,
      showTechnicalDetails: false,
      showProvenance: true,
      includeTechnicalMetadata: false,
    }
  }
  return {
    technicalLevel: 'BASIC' as const,
    showTechnicalDetails: false,
    showProvenance: false,
    includeTechnicalMetadata: false,
  }
}

function normalizeRole(value: unknown): ComparisonUserRole {
  return value === 'ADMIN' || value === 'GESTOR' || value === 'CONSULTA'
    ? value
    : 'CONSULTA'
}

function statusFromResponse(
  response: QueryResponse,
  contract: AnalyticalResponseV2 | null,
  rowCount: number,
  partial: boolean,
): ComparisonPresentationStatus {
  const explicit = (response.status ?? '').toUpperCase()
  if (explicit.includes('TIMEOUT') || explicit.includes('TIMED_OUT')) return 'TIMEOUT'
  if (explicit.includes('BLOCK')) return 'BLOCKED'
  if (explicit.includes('UNSUPPORTED')) return 'UNSUPPORTED'
  if (explicit.includes('OUT_OF_SCOPE')) return 'OUT_OF_SCOPE'
  if (explicit.includes('CLARIFICATION')) return 'CLARIFICATION_REQUIRED'
  if (explicit.includes('ERROR') || explicit.includes('FAILED')) return 'ERROR'
  if (partial) return 'PARTIAL'
  if (contract?.intent.readiness === 'CLARIFICATION_REQUIRED') return 'CLARIFICATION_REQUIRED'
  if (contract?.intent.readiness === 'OUT_OF_SCOPE') return 'OUT_OF_SCOPE'
  if (contract?.intent.readiness === 'UNSUPPORTED') return 'UNSUPPORTED'
  if (contract?.intent.readiness === 'BLOCKED') return 'BLOCKED'
  if (contract?.intent.readiness === 'ERROR') return 'ERROR'
  if (rowCount === 0) return 'EMPTY'
  return 'SUCCESS'
}

function comparisonTitle(comparison: AnalyticalComparison): string {
  const operands = comparison.operands.map(item => item.label).filter(Boolean)
  const metric = comparison.operands[0]?.metric_refs[0]?.display_name ?? 'Comparacao'
  if (operands.length >= 2) return `${metric} - ${operands.join(' x ')}`
  return metric
}

function defaultVisualizations(
  comparison: AnalyticalComparison,
): ComparisonVisualizationPresentation[] {
  const kinds: ChartType[] = comparison.kind === 'MULTI_PERIOD'
    ? ['LINE', 'TABLE']
    : comparison.kind === 'ENTITY_VS_ENTITY' || comparison.kind === 'MULTI_ENTITY'
      ? ['BAR', 'TABLE']
      : ['KPI', 'TABLE']
  return kinds.map((kind, index) => ({
    id: `default-${kind.toLowerCase()}-${index + 1}`,
    kind,
    title: kind === 'TABLE' ? 'Detalhamento comparativo' : 'Visao comparativa',
    dataReference: 'comparison_result',
    isPrimary: index === 0,
    priority: index,
    compatible: true,
    incompatibilityReason: null,
    source: 'DEFAULT',
  }))
}

function visualizationCompatibility(
  visualization: AnalyticalVisualization,
  comparison: AnalyticalComparison,
): { compatible: boolean; reason: string | null } {
  const kind = VISUALIZATION_KIND_MAP[visualization.kind] ?? 'TABLE'
  const units = new Set(
    comparison.operands.flatMap(item => item.metric_refs.map(metric => metric.unit)),
  )
  if (kind === 'PIE' && !comparison.calculations.includes('SHARE')) {
    return { compatible: false, reason: 'Pizza exige participacao oficial do backend.' }
  }
  if ((kind === 'BAR' || kind === 'LINE' || kind === 'AREA') && units.size > 1) {
    return { compatible: false, reason: 'Unidades diferentes exigem visoes separadas.' }
  }
  return { compatible: true, reason: null }
}

function adaptVisualizations(
  contract: AnalyticalResponseV2,
  comparison: AnalyticalComparison,
): ComparisonVisualizationPresentation[] {
  const requested = contract.visualizations.length > 0
    ? contract.visualizations
    : contract.intent.requested_visualizations
  if (requested.length === 0) return defaultVisualizations(comparison)
  return requested.map(item => {
    const compatibility = visualizationCompatibility(item, comparison)
    return {
      id: item.visualization_id,
      kind: VISUALIZATION_KIND_MAP[item.kind] ?? 'TABLE',
      title: item.title,
      dataReference: item.data_reference || null,
      isPrimary: item.is_primary,
      priority: item.priority,
      compatible: compatibility.compatible,
      incompatibilityReason: compatibility.reason,
      source: item.origin === 'EXPLICIT_USER' ? 'EXPLICIT' : 'BACKEND',
    }
  })
}

function adaptDatasets(
  datasets: AnalyticalDatasetV2[],
  contract: AnalyticalResponseV2,
): ComparisonDatasetPresentation[] {
  const executor = contract.contract.extensions.comparison_executor
  return datasets.map(dataset => {
    const summary = executor?.aligned_datasets.find(
      item => item.dataset_id === dataset.dataset_id,
    )
    const columns = dataset.columns.map((column, index) => {
      const record = isRecord(column) ? column : {}
      return {
        key: asString(record.column_id) ?? `column_${index + 1}`,
        label: asString(record.label) ?? `Coluna ${index + 1}`,
        dataType: asString(record.data_type) ?? 'STRING',
      }
    })
    return {
      datasetId: dataset.dataset_id,
      columns,
      rows: dataset.rows,
      alignmentKeys: summary?.alignment_keys ?? [],
      units: {},
      missingBuckets: summary?.missing_bucket_count ?? 0,
      nullBuckets: summary?.null_bucket_count ?? 0,
      rowCount: dataset.row_count,
      truncated: dataset.truncated || Boolean(summary?.truncated),
      visualCompatibility: ['TABLE', 'KPI', 'BAR', 'LINE', 'AREA'],
      exportable: dataset.data_classification !== 'RESTRICTED',
    }
  })
}

function calculationRows(datasets: AnalyticalDatasetV2[]): Array<Record<string, JsonValue>> {
  const preferred = datasets.find(dataset => dataset.dataset_id === 'comparison_result')
  return preferred?.rows ?? datasets.flatMap(dataset => dataset.rows)
}

function rawValueForOperand(
  operandId: string,
  baselineId: string | null,
  rows: Array<Record<string, JsonValue>>,
): { value: string | number | null; found: boolean } {
  for (const row of rows) {
    if (row.target_operand_id === operandId) {
      return { value: asRawValue(row.target_value), found: true }
    }
    if (baselineId === operandId && row.baseline_operand_id === operandId) {
      return { value: asRawValue(row.baseline_value), found: true }
    }
  }
  return { value: null, found: false }
}

function adaptOperands(
  comparison: AnalyticalComparison,
  rows: Array<Record<string, JsonValue>>,
  partial: boolean,
): ComparisonOperandPresentation[] {
  return comparison.operands.map((operand, index) => {
    const metric = operand.metric_refs[0]
    const unit = metric?.unit ?? 'DECIMAL'
    const raw = rawValueForOperand(
      operand.operand_id,
      comparison.baseline_operand_id,
      rows,
    )
    const state = raw.found ? classifyRawValue(raw.value) : 'MISSING'
    const periodLabel = operand.time_windows.map(window => window.label).join(', ') || null
    const entityLabel = operand.entity_refs
      .map(entity => isRecord(entity) ? asString(entity.label) ?? asString(entity.entity_id) : null)
      .filter((value): value is string => Boolean(value))
      .join(', ') || null
    const formatted = formatComparisonValue(raw.value, unit, state)
    const label = operand.label || periodLabel || entityLabel || `Operando ${index + 1}`
    return {
      operandId: operand.operand_id,
      label,
      shortLabel: label.length > 34 ? `${label.slice(0, 31)}...` : label,
      metricId: metric?.metric_id ?? 'metric_not_informed',
      metricLabel: metric?.display_name ?? 'Metrica',
      unit,
      periodLabel,
      entityLabel,
      rawValue: raw.value,
      formattedValue: formatted,
      valueState: state,
      status: raw.found ? 'READY' : 'EMPTY',
      isBaseline: operand.operand_id === comparison.baseline_operand_id,
      isTarget: operand.operand_id !== comparison.baseline_operand_id,
      isMissing: state === 'MISSING',
      isNull: state === 'NULL',
      isPartial: partial,
      warnings: raw.found ? [] : ['O backend nao forneceu valor para este operando.'],
      accessibilityLabel: `${label}: ${formatted}. ${operand.operand_id === comparison.baseline_operand_id ? 'Base da comparacao.' : 'Valor comparado.'}`,
    }
  })
}

function adaptCalculations(
  rows: Array<Record<string, JsonValue>>,
  comparison: AnalyticalComparison,
  zeroDenominatorCount: number,
): ComparisonCalculationPresentation[] {
  let remainingZeroDenominators = zeroDenominatorCount
  return rows.flatMap(row => {
    const calculation = asString(row.calculation)
    if (!calculation || !comparison.calculations.includes(
      calculation as AnalyticalComparison['calculations'][number],
    )) return []
    const targetOperandId = asString(row.target_operand_id)
    const metricId = asString(row.metric_id)
    if (!targetOperandId || !metricId) return []
    const direction = isDirection(row.direction) ? row.direction : 'NOT_APPLICABLE'
    const status = asString(row.status) ?? 'NOT_APPLICABLE'
    const zeroDenominator = status === 'NOT_APPLICABLE' &&
      calculation === 'PERCENTAGE_DIFFERENCE' &&
      remainingZeroDenominators > 0
    if (zeroDenominator) remainingZeroDenominators -= 1
    const rawResult = asRawValue(row.result_value)
    const unit = calculation === 'PERCENTAGE_DIFFERENCE' || calculation === 'SHARE'
      ? 'PERCENT'
      : calculation === 'RANK'
        ? 'COUNT'
        : comparison.operands.find(
          operand => operand.operand_id === targetOperandId,
        )?.metric_refs[0]?.unit ?? 'DECIMAL'
    const state = status === 'NOT_APPLICABLE' ? 'NOT_APPLICABLE' : classifyRawValue(rawResult)
    const formattedResult = calculation === 'DIRECTION'
      ? directionLabel(direction)
      : formatComparisonValue(rawResult, unit, state)
    return [{
      calculation: calculation as AnalyticalComparison['calculations'][number],
      baselineOperandId: asString(row.baseline_operand_id),
      targetOperandId,
      metricId,
      alignmentKey: asString(row.alignment_key) ?? '',
      baselineRawValue: asRawValue(row.baseline_value),
      targetRawValue: asRawValue(row.target_value),
      rawResult,
      formattedResult,
      direction,
      status,
      zeroDenominator,
      notApplicableReason: zeroDenominator
        ? 'Denominador zero informado pelo backend.'
        : status === 'NOT_APPLICABLE'
          ? 'Calculo nao aplicavel informado pelo backend.'
          : null,
      roundingApplied: false,
      accessibilityLabel: calculation === 'DIRECTION'
        ? `${calculationLabel(calculation)}: ${formattedResult}.`
        : `${calculationLabel(calculation)}: ${formattedResult}. ${directionLabel(direction)}.`,
    }]
  })
}

function adaptValidation(
  contract: AnalyticalResponseV2,
  role: ComparisonUserRole,
): ComparisonValidationPresentation {
  const status = contract.validation.status
  const labels = {
    PASSED: 'Validado',
    WARNING: 'Validado com ressalvas',
    FAILED: 'Nao validado',
    NOT_EXECUTED: 'Validacao nao executada',
  }
  const checks = role === 'ADMIN'
    ? contract.validation.checks.flatMap((check, index) => {
      if (!isRecord(check)) return []
      return [{
        code: asString(check.code) ?? `check_${index + 1}`,
        status: asString(check.status) ?? 'NOT_EXECUTED',
        message: sanitizeText(check.public_message ?? check.message ?? ''),
        required: asBoolean(check.required) ?? false,
      }]
    })
    : []
  return {
    status,
    label: labels[status],
    validatorVersion: role === 'ADMIN' ? contract.validation.validator_version : null,
    validatedAt: contract.validation.validated_at,
    checks,
  }
}

function adaptProvenance(
  contract: AnalyticalResponseV2,
  role: ComparisonUserRole,
): ComparisonProvenancePresentation | null {
  if (role === 'CONSULTA') return null
  const firstValue = contract.provenance.find(item => isRecord(item))
  const first: Record<string, unknown> = isRecord(firstValue) ? firstValue : {}
  const executor = contract.contract.extensions.comparison_executor
  const planner = contract.contract.extensions.comparison_planner
  const temporal = contract.contract.extensions.temporal
  return {
    sourceLabel: asString(first.source_label) ?? asString(first.source_id) ?? 'PostgreSQL analitico',
    updatedAt: asString(first.synced_at) ?? asString(first.source_updated_at) ?? null,
    periods: contract.intent.time_windows.map(window => window.label),
    metrics: contract.intent.metric_refs.map(metric => ({
      id: metric.metric_id,
      label: metric.display_name,
      version: metric.metric_version,
    })),
    executorVersion: executor?.executor_version ?? null,
    plannerVersion: planner?.planner_version ?? null,
    normalizerVersion: temporal?.normalizer_version ?? null,
    cacheStatus: executor?.cache_status ?? null,
    validationStatus: contract.validation.status,
    tenantIsolationVerified: asBoolean(first.tenant_isolation_verified),
  }
}

function buildV2Presentation(
  response: QueryResponse,
  contract: AnalyticalResponseV2,
  role: ComparisonUserRole,
): ComparisonPresentationModel {
  const comparison = contract.intent.comparison
  if (!comparison) {
    throw new ComparisonPresentationContractError(
      'COMPARISON_MISSING',
      'O contrato V2 nao contem a comparacao esperada.',
    )
  }
  const executor = contract.contract.extensions.comparison_executor
  const partial = executor?.partial ?? false
  const datasets = adaptDatasets(contract.datasets, contract)
  const rows = calculationRows(contract.datasets)
  const operands = adaptOperands(comparison, rows, partial)
  if (operands.length < 2) {
    throw new ComparisonPresentationContractError(
      'OPERANDS_INCOMPLETE',
      'A comparacao precisa preservar pelo menos dois operandos.',
    )
  }
  const calculations = adaptCalculations(
    rows,
    comparison,
    executor?.zero_denominator_count ?? 0,
  )
  const policy = rolePolicy(role)
  const truncated = datasets.some(dataset => dataset.truncated)
  const totalRows = datasets.reduce((total, dataset) => total + dataset.rowCount, 0)
  const visualizations = adaptVisualizations(contract, comparison)
  const status = statusFromResponse(response, contract, totalRows, partial)
  const errors = contract.errors.map(error =>
    isRecord(error)
      ? sanitizeText(error.public_message ?? error.message ?? 'Erro de execucao.')
      : 'Erro de execucao.',
  )
  return {
    presentationVersion: COMPARISON_PRESENTATION_VERSION,
    comparisonId: comparison.comparison_id,
    comparisonKind: comparison.kind,
    title: comparisonTitle(comparison),
    subtitle: contract.summary ?? 'Resultado comparativo validado pelo backend.',
    status,
    partial,
    truncated,
    baselineOperandId: comparison.baseline_operand_id,
    targetOperandIds: comparison.operands
      .filter(operand => operand.operand_id !== comparison.baseline_operand_id)
      .map(operand => operand.operand_id),
    operands,
    calculations,
    datasets,
    visualizations,
    alignment: {
      dimensions: comparison.alignment_dimensions,
      missingBucketCount: executor?.aligned_datasets.reduce(
        (total, dataset) => total + dataset.missing_bucket_count,
        0,
      ) ?? 0,
      nullBucketCount: executor?.aligned_datasets.reduce(
        (total, dataset) => total + dataset.null_bucket_count,
        0,
      ) ?? 0,
    },
    validation: adaptValidation(contract, role),
    provenance: adaptProvenance(contract, role),
    warnings: [...contract.warnings],
    errors,
    displayPolicy: {
      dense: operands.length > 8 || totalRows > 100,
      showTechnicalDetails: policy.showTechnicalDetails,
      showProvenance: policy.showProvenance,
      volumeWarning: operands.length > 10 || totalRows > 200,
    },
    exportPolicy: {
      allowed: datasets.some(dataset => dataset.exportable),
      includeTechnicalMetadata: policy.includeTechnicalMetadata,
    },
    accessPolicy: {
      role,
      technicalLevel: policy.technicalLevel,
    },
    technicalMetadata: role === 'ADMIN' ? {
      executorVersion: executor?.executor_version ?? null,
      plannerVersion: contract.contract.extensions.comparison_planner?.planner_version ?? null,
      normalizerVersion: contract.contract.extensions.temporal?.normalizer_version ?? null,
      strategy: executor?.strategy ?? null,
      cacheStatus: executor?.cache_status ?? null,
      adaptationDurationMs: 0,
      fallbackUsed: false,
    } : null,
  }
}

function legacyVisualizations(response: QueryResponse): VisualizationItem[] {
  if (response.visualizations?.length) return response.visualizations
  return response.chart_type && response.chart_data
    ? [{ chart_type: response.chart_type, chart_data: response.chart_data }]
    : []
}

function isBarData(value: AnyChartData): value is ChartDataBar {
  return 'labels' in value && 'datasets' in value && Array.isArray(value.labels)
}

function buildLegacyOperands(
  visualizations: VisualizationItem[],
): ComparisonOperandPresentation[] {
  const first = visualizations[0]
  if (!first || !isBarData(first.chart_data)) return []
  const dataset = first.chart_data.datasets[0]
  if (!dataset) return []
  return first.chart_data.labels.map((label, index) => {
    const rawValue = dataset.data[index] ?? null
    const state = classifyRawValue(rawValue)
    const formattedValue = formatComparisonValue(rawValue, 'DECIMAL', state)
    return {
      operandId: `legacy_operand_${index + 1}`,
      label,
      shortLabel: label.length > 34 ? `${label.slice(0, 31)}...` : label,
      metricId: 'legacy_metric',
      metricLabel: dataset.label,
      unit: 'DECIMAL',
      periodLabel: null,
      entityLabel: label,
      rawValue,
      formattedValue,
      valueState: state,
      status: 'READY',
      isBaseline: index === 0,
      isTarget: index > 0,
      isMissing: false,
      isNull: rawValue === null,
      isPartial: false,
      warnings: [],
      accessibilityLabel: `${label}: ${formattedValue}.`,
    }
  })
}

function buildV1Presentation(
  response: QueryResponse,
  role: ComparisonUserRole,
): ComparisonPresentationModel {
  const visuals = legacyVisualizations(response)
  const operands = buildLegacyOperands(visuals)
  const policy = rolePolicy(role)
  const status = statusFromResponse(response, null, operands.length, false)
  return {
    presentationVersion: COMPARISON_PRESENTATION_VERSION,
    comparisonId: response.query_id,
    comparisonKind: 'LEGACY_COMPARISON',
    title: response.view_name?.replace(/^VW_/i, '').replace(/_/g, ' ') ?? 'Comparacao',
    subtitle: response.mensagem ?? 'Resposta comparativa legada.',
    status,
    partial: false,
    truncated: visuals.some(item =>
      'total_rows' in item.chart_data &&
      'rows' in item.chart_data &&
      item.chart_data.rows.length < item.chart_data.total_rows,
    ),
    baselineOperandId: operands[0]?.operandId ?? null,
    targetOperandIds: operands.slice(1).map(item => item.operandId),
    operands,
    calculations: [],
    datasets: [],
    visualizations: visuals.map((item, index) => ({
      id: `legacy-visual-${index + 1}`,
      kind: item.chart_type,
      title: response.view_name ?? 'Comparacao',
      dataReference: null,
      isPrimary: index === 0,
      priority: index,
      compatible: true,
      incompatibilityReason: null,
      source: 'LEGACY',
    })),
    alignment: { dimensions: [], missingBucketCount: 0, nullBucketCount: 0 },
    validation: {
      status: response.validation_summary?.status === 'PASSED' ? 'PASSED' : 'NOT_EXECUTED',
      label: response.validation_summary?.status === 'PASSED' ? 'Validado' : 'Validacao nao executada',
      validatorVersion: null,
      validatedAt: response.validation_summary?.validated_at ?? null,
      checks: [],
    },
    provenance: role === 'CONSULTA' ? null : {
      sourceLabel: response.data_status?.source_label ?? 'Fonte analitica',
      updatedAt: response.data_status?.synced_at ?? null,
      periods: [],
      metrics: [],
      executorVersion: null,
      plannerVersion: null,
      normalizerVersion: null,
      cacheStatus: null,
      validationStatus: response.validation_summary?.status === 'PASSED' ? 'PASSED' : 'NOT_EXECUTED',
      tenantIsolationVerified: null,
    },
    warnings: [],
    errors: status === 'ERROR' ? [response.mensagem ?? 'Erro de execucao.'] : [],
    displayPolicy: {
      dense: operands.length > 8,
      showTechnicalDetails: policy.showTechnicalDetails,
      showProvenance: policy.showProvenance,
      volumeWarning: operands.length > 10,
    },
    exportPolicy: {
      allowed: visuals.length > 0,
      includeTechnicalMetadata: policy.includeTechnicalMetadata,
    },
    accessPolicy: { role, technicalLevel: policy.technicalLevel },
    technicalMetadata: role === 'ADMIN' ? {
      executorVersion: null,
      plannerVersion: null,
      normalizerVersion: null,
      strategy: null,
      cacheStatus: null,
      adaptationDurationMs: 0,
      fallbackUsed: true,
    } : null,
  }
}

export function isComparisonQueryResponse(response: QueryResponse): boolean {
  if (response.analytical_contract?.intent.comparison) return true
  const extracted = Object.values(response.parametros_extraidos ?? {})
    .join(' ')
    .toLocaleLowerCase('pt-BR')
  const question = response.pergunta_original.toLocaleLowerCase('pt-BR')
  return extracted.includes('compar') ||
    /\b(compare|comparar|comparacao|versus|vs\.?|ranking)\b/i.test(question)
}

export function buildComparisonPresentationModel(
  response: QueryResponse,
  options?: { role?: ComparisonUserRole },
): ComparisonPresentationModel {
  const role = options?.role ??
    normalizeRole(response.analytical_contract?.scope_summary.user_role)
  if (response.analytical_contract?.intent.comparison) {
    return buildV2Presentation(response, response.analytical_contract, role)
  }
  if (!isComparisonQueryResponse(response)) {
    throw new ComparisonPresentationContractError(
      'NOT_A_COMPARISON',
      'A resposta nao representa uma comparacao.',
    )
  }
  return buildV1Presentation(response, role)
}
