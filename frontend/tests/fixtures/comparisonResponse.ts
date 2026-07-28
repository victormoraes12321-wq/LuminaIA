import type {
  AnalyticalComparison,
  AnalyticalMetricReference,
  AnalyticalResponseV2,
  AnalyticalTimeWindow,
  AnalyticalVisualization,
  JsonValue,
  QueryResponse,
} from '../../types/lumina'

const contractMetadata: AnalyticalResponseV2['contract'] = {
  schema_name: 'lumina.analytics',
  schema_version: '2.0',
  created_at: '2026-07-28T12:00:00.000Z',
  request_id: 'request-comparison-1',
  trace_id: 'trace-comparison-1',
  pipeline: 'NEW',
  adapter_used: 'comparison_execution_v2',
  extensions: {
    temporal: {
      normalizer_version: 'lumina.temporal.pt-BR/1.0',
      timezone: 'America/Sao_Paulo',
      relation: 'COMPARISON',
      rule_ids: ['explicit_month_year'],
      warnings: [],
      readiness: 'READY',
    },
    comparison_planner: {
      planner_version: 'lumina.comparison-planner/1.0',
      kind: 'PERIOD_VS_PERIOD',
      operand_count: 2,
      metric_count: 1,
      dimension_count: 0,
      complexity: 'LOW',
      complexity_score: 2,
      readiness: 'READY',
      issue_codes: [],
      strategy_hint: 'MULTI_QUERY',
      rule_ids: ['period_vs_period'],
      cache_identity: 'sha256:planner-fixture',
    },
    comparison_executor: {
      executor_version: 'lumina.comparison-executor/1.0',
      strategy: 'MULTI_QUERY',
      cache_status: 'MISS',
      partial: false,
      aligned_datasets: [{
        dataset_id: 'comparison_result',
        metric_id: 'faturamento_comercial',
        alignment_keys: [],
        series: ['junho_2026', 'julho_2026'],
        row_count: 4,
        truncated: false,
        missing_bucket_count: 0,
        null_bucket_count: 0,
        alignment_policy: 'PRESERVE_NULL',
      }],
      calculation_count: 4,
      zero_denominator_count: 0,
      not_applicable_count: 0,
      validation_status: 'PASSED',
      provenance_count: 2,
    },
  },
}

function confidence() {
  return {
    level: 'HIGH' as const,
    score: '1.0',
    reasons: ['deterministic_fixture'],
    requires_confirmation: false,
  }
}

function metric(metricId = 'faturamento_comercial', label = 'Faturamento', unit = 'BRL') {
  return {
    metric_id: metricId,
    metric_version: '1.0',
    display_name: label,
    unit,
    aggregation: 'SUM',
    origin: 'EXPLICIT_USER' as const,
    confidence: confidence(),
  }
}

function period(
  id: string,
  label: string,
  start: string,
  end: string,
) {
  return {
    window_id: id,
    label,
    start,
    end,
    end_inclusive: true,
    granularity: 'MONTH' as const,
    timezone: 'America/Sao_Paulo',
    origin: 'EXPLICIT_USER' as const,
    confidence: confidence(),
    raw_expression: label,
  }
}

function operand(
  id: string,
  label: string,
  metricReference: AnalyticalMetricReference = metric(),
  timeWindow: AnalyticalTimeWindow = period(`${id}_period`, label, '2026-06-01', '2026-06-30'),
  entityRefs: JsonValue[] = [],
) {
  return {
    operand_id: id,
    label,
    metric_refs: [metricReference],
    time_windows: [timeWindow],
    filters: [],
    entity_refs: entityRefs,
    origin: 'EXPLICIT_USER' as const,
  }
}

function visualization(
  id: string,
  kind: AnalyticalVisualization['kind'],
  title: string,
  priority: number,
  primary: boolean,
): AnalyticalVisualization {
  return {
    visualization_id: id,
    kind,
    title,
    metric_ids: ['faturamento_comercial'],
    dimension_ids: [],
    data_reference: 'comparison_result',
    priority,
    is_primary: primary,
    origin: 'EXPLICIT_USER',
    options: {},
  }
}

function calculationRow(
  calculation: AnalyticalComparison['calculations'][number],
  targetOperandId: string,
  baselineValue: string | null,
  targetValue: string | null,
  resultValue: string | null,
  direction: 'INCREASE' | 'DECREASE' | 'STABLE' | 'NOT_APPLICABLE',
  status = 'READY',
) {
  return {
    metric_id: 'faturamento_comercial',
    alignment_key: '',
    calculation,
    baseline_operand_id: 'junho_2026',
    target_operand_id: targetOperandId,
    baseline_value: baselineValue,
    target_value: targetValue,
    result_value: resultValue,
    direction,
    status,
  }
}

function baseComparison(): AnalyticalComparison {
  return {
    comparison_id: 'comparison-june-july',
    kind: 'PERIOD_VS_PERIOD',
    operands: [
      operand(
        'junho_2026',
        'Junho de 2026',
        metric(),
        period('june', 'Junho de 2026', '2026-06-01', '2026-06-30'),
      ),
      operand(
        'julho_2026',
        'Julho de 2026',
        metric(),
        period('july', 'Julho de 2026', '2026-07-01', '2026-07-31'),
      ),
    ],
    calculations: ['VALUE', 'ABSOLUTE_DIFFERENCE', 'PERCENTAGE_DIFFERENCE', 'DIRECTION'],
    baseline_operand_id: 'junho_2026',
    alignment_dimensions: [],
    requested_sort: null,
    origin: 'EXPLICIT_USER',
    confidence: confidence(),
  }
}

function baseAnalyticalContract(role: 'ADMIN' | 'GESTOR' | 'CONSULTA'): AnalyticalResponseV2 {
  const comparison = baseComparison()
  const visualizations = [
    visualization('comparison-bar', 'BAR_CHART', 'Faturamento por periodo', 1, true),
    visualization('comparison-table', 'DATA_TABLE', 'Detalhamento comparativo', 2, false),
  ]
  return {
    contract: structuredClone(contractMetadata),
    scope_summary: {
      tenant_id: 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
      user_role: role,
      session_id: 'comparison-session',
    },
    intent: {
      contract: structuredClone(contractMetadata),
      intent_kind: 'COMPARISON',
      readiness: 'READY',
      raw_question: 'Compare o faturamento do Mes 06/2026 e 07/2026',
      normalized_question: 'comparar faturamento junho 2026 julho 2026',
      metric_refs: [metric()],
      dimension_refs: [],
      filters: [],
      time_windows: comparison.operands.flatMap(item => item.time_windows),
      comparison,
      requested_visualizations: visualizations,
      confidence: confidence(),
      clarification: null,
      out_of_scope_reason: null,
      field_origins: {},
    },
    plan_summary: {
      operation: 'COMPARISON',
      metric_ids: ['faturamento_comercial'],
      dimension_ids: [],
      source_ids: ['vw_vendas_lm'],
    },
    datasets: [{
      dataset_id: 'comparison_result',
      columns: [
        { column_id: 'metric_id', label: 'Metrica', data_type: 'STRING' },
        { column_id: 'calculation', label: 'Calculo', data_type: 'STRING' },
        { column_id: 'baseline_value', label: 'Valor base', data_type: 'DECIMAL' },
        { column_id: 'target_value', label: 'Valor comparado', data_type: 'DECIMAL' },
        { column_id: 'result_value', label: 'Resultado', data_type: 'DECIMAL' },
      ],
      rows: [
        calculationRow('VALUE', 'julho_2026', '300.00', '400.00', '400.00', 'INCREASE'),
        calculationRow('ABSOLUTE_DIFFERENCE', 'julho_2026', '300.00', '400.00', '100.00', 'INCREASE'),
        calculationRow('PERCENTAGE_DIFFERENCE', 'julho_2026', '300.00', '400.00', '33.33', 'INCREASE'),
        calculationRow('DIRECTION', 'julho_2026', '300.00', '400.00', null, 'INCREASE'),
      ],
      row_count: 4,
      truncated: false,
      numeric_metadata: {},
      data_classification: 'INTERNAL',
    }],
    visualizations,
    provenance: [{
      source_id: 'sales_clone',
      source_label: 'PostgreSQL analitico',
      synced_at: '2026-07-28T11:45:00.000Z',
      tenant_isolation_verified: true,
      metric_version: '1.0',
    }],
    validation: {
      status: 'PASSED',
      checks: [
        {
          code: 'signed_delta',
          status: 'PASSED',
          public_message: 'Diferenca assinada conferida.',
          required: true,
        },
        {
          code: 'tenant_isolation',
          status: 'PASSED',
          public_message: 'Isolamento do tenant conferido.',
          required: true,
        },
      ],
      validated_at: '2026-07-28T12:00:00.000Z',
      validator_version: 'comparison-validator/1.0',
    },
    summary: 'Julho aumentou R$ 100,00 em relacao a junho.',
    insights: [],
    warnings: [],
    errors: [],
    clarification: null,
    legacy_compatibility: {
      compatible: true,
      primary_chart_type: 'BAR',
      warnings: [],
    },
  }
}

export type ComparisonFixtureScenario =
  | 'period'
  | 'multi_period'
  | 'entity'
  | 'multi_entity'
  | 'metric_incompatible'
  | 'actual_target'
  | 'actual_target_missing'
  | 'area'
  | 'pie'
  | 'partial'
  | 'zero_denominator'
  | 'null_missing'
  | 'multiple_visualizations'
  | 'timeout'
  | 'blocked'

export function buildComparisonResponse(
  scenario: ComparisonFixtureScenario = 'period',
  role: 'ADMIN' | 'GESTOR' | 'CONSULTA' = 'ADMIN',
): QueryResponse {
  const analytical = baseAnalyticalContract(role)
  const response: QueryResponse = {
    query_id: `query-${scenario}`,
    request_id: `query-${scenario}`,
    view_catalog_id: 'view-sales',
    view_name: 'VW_VENDAS_LM',
    chart_type: 'BAR',
    chart_data: {
      labels: ['Junho de 2026', 'Julho de 2026'],
      datasets: [{
        label: 'Faturamento',
        data: [300, 400],
        backgroundColor: '#625bf6',
        borderColor: '#4f46e5',
      }],
      resumo: {},
    },
    visualizations: [
      {
        chart_type: 'BAR',
        chart_data: {
          labels: ['Junho de 2026', 'Julho de 2026'],
          datasets: [{
            label: 'Faturamento',
            data: [300, 400],
            backgroundColor: '#625bf6',
            borderColor: '#4f46e5',
          }],
          resumo: {},
        },
      },
    ],
    analytical_contract: analytical,
    parametros_extraidos: { tipo: 'comparacao' },
    ia_confianca: 1,
    ia_justificativa: 'Resultado deterministico.',
    ia_analise: null,
    pergunta_original: 'Compare o faturamento do Mes 06/2026 e 07/2026',
    pode_favoritar: true,
    mensagem: 'Comparacao concluida.',
    resposta_direta: null,
    data_status: {
      query_source: 'POSTGRESQL_ANALYTICAL_CLONE',
      source_label: 'PostgreSQL analitico',
      view_name: 'VW_VENDAS_LM',
      synced_at: '2026-07-28T11:45:00.000Z',
      checked_at: '2026-07-28T12:00:00.000Z',
      age_minutes: 15,
      freshness: 'CURRENT',
      sync_status: 'SUCCESS',
      records_last_sync: 100,
      freshness_warning_minutes: 60,
    },
    status: 'READY',
  }

  const comparison = analytical.intent.comparison
  const executor = analytical.contract.extensions.comparison_executor
  if (!comparison || !executor) return response

  if (scenario === 'multi_period' || scenario === 'area') {
    comparison.kind = 'MULTI_PERIOD'
    comparison.operands.push(
      operand(
        'agosto_2026',
        'Agosto de 2026',
        metric(),
        period('august', 'Agosto de 2026', '2026-08-01', '2026-08-31'),
      ),
    )
    analytical.intent.time_windows = comparison.operands.flatMap(item => item.time_windows)
    analytical.datasets[0].rows.push(
      calculationRow('VALUE', 'agosto_2026', '300.00', '500.00', '500.00', 'INCREASE'),
    )
    analytical.datasets[0].row_count = 5
    analytical.visualizations = [
      visualization(
        scenario === 'area' ? 'comparison-area' : 'comparison-line',
        scenario === 'area' ? 'AREA_CHART' : 'LINE_CHART',
        scenario === 'area' ? 'Evolucao acumulada por periodo' : 'Evolucao por periodo',
        1,
        true,
      ),
      visualization('comparison-table', 'DATA_TABLE', 'Detalhamento comparativo', 2, false),
    ]
    executor.aligned_datasets[0].series.push('agosto_2026')
  }

  if (scenario === 'entity' || scenario === 'multi_entity') {
    comparison.kind = scenario === 'multi_entity' ? 'MULTI_ENTITY' : 'ENTITY_VS_ENTITY'
    comparison.operands = [
      operand('filial_centro', 'Filial Centro', metric(), comparison.operands[0].time_windows[0], [{ entity_id: 'branch-1', label: 'Filial Centro' }]),
      operand('filial_sul', 'Filial Sul com nome empresarial extenso', metric(), comparison.operands[0].time_windows[0], [{ entity_id: 'branch-2', label: 'Filial Sul com nome empresarial extenso' }]),
    ]
    if (scenario === 'multi_entity') {
      comparison.operands.push(
        operand('filial_norte', 'Filial Norte', metric(), comparison.operands[0].time_windows[0], [{ entity_id: 'branch-3', label: 'Filial Norte' }]),
      )
    }
    comparison.baseline_operand_id = 'filial_centro'
    analytical.datasets[0].rows = [
      {
        ...calculationRow('ABSOLUTE_DIFFERENCE', 'filial_sul', '120.00', '200.00', '80.00', 'INCREASE'),
        baseline_operand_id: 'filial_centro',
      },
    ]
    if (scenario === 'multi_entity') {
      analytical.datasets[0].rows.push({
        ...calculationRow('ABSOLUTE_DIFFERENCE', 'filial_norte', '120.00', '160.00', '40.00', 'INCREASE'),
        baseline_operand_id: 'filial_centro',
      })
    }
    analytical.datasets[0].row_count = analytical.datasets[0].rows.length
  }

  if (scenario === 'metric_incompatible') {
    comparison.kind = 'METRIC_VS_METRIC'
    comparison.operands = [
      operand('faturamento', 'Faturamento', metric(), comparison.operands[0].time_windows[0]),
      operand('quantidade', 'Quantidade vendida', metric('quantidade_vendida', 'Quantidade vendida', 'COUNT'), comparison.operands[0].time_windows[0]),
    ]
    comparison.baseline_operand_id = 'faturamento'
    analytical.datasets[0].rows = [{
      ...calculationRow('VALUE', 'quantidade', '300.00', '24', '24', 'NOT_APPLICABLE'),
      baseline_operand_id: 'faturamento',
      metric_id: 'quantidade_vendida',
    }]
    analytical.datasets[0].row_count = 1
    analytical.warnings.push('Unidades diferentes: BRL e COUNT.')
  }

  if (scenario === 'actual_target' || scenario === 'actual_target_missing') {
    comparison.kind = 'ACTUAL_VS_TARGET'
    comparison.operands = [
      operand('realizado', 'Realizado', metric(), comparison.operands[0].time_windows[0]),
      operand('meta', 'Meta oficial', metric(), comparison.operands[0].time_windows[0]),
    ]
    comparison.baseline_operand_id = 'realizado'
    analytical.datasets[0].rows = [{
      ...calculationRow(
        'ABSOLUTE_DIFFERENCE',
        'meta',
        '400.00',
        scenario === 'actual_target_missing' ? null : '500.00',
        scenario === 'actual_target_missing' ? null : '100.00',
        scenario === 'actual_target_missing' ? 'NOT_APPLICABLE' : 'INCREASE',
        scenario === 'actual_target_missing' ? 'NOT_APPLICABLE' : 'READY',
      ),
      baseline_operand_id: 'realizado',
    }]
    analytical.datasets[0].row_count = 1
    if (scenario === 'actual_target_missing') {
      executor.aligned_datasets[0].missing_bucket_count = 1
      analytical.warnings.push('Meta oficial ausente para o periodo.')
    }
  }

  if (scenario === 'pie') {
    comparison.calculations = ['VALUE', 'SHARE']
    analytical.datasets[0].rows = [
      calculationRow('SHARE', 'junho_2026', '300.00', '300.00', '42.86', 'NOT_APPLICABLE'),
      calculationRow('SHARE', 'julho_2026', '300.00', '400.00', '57.14', 'NOT_APPLICABLE'),
    ]
    analytical.datasets[0].row_count = 2
    analytical.visualizations = [
      visualization('comparison-pie', 'PIE_CHART', 'Participacao por periodo', 1, true),
      visualization('comparison-table', 'DATA_TABLE', 'Detalhamento de participacao', 2, false),
    ]
  }

  if (scenario === 'partial') {
    executor.partial = true
    executor.aligned_datasets[0].truncated = true
    analytical.datasets[0].truncated = true
    analytical.warnings.push('Um operando excedeu o limite de linhas.')
    response.status = 'PARTIAL'
  }

  if (scenario === 'zero_denominator') {
    executor.zero_denominator_count = 1
    executor.not_applicable_count = 1
    analytical.datasets[0].rows = [
      calculationRow('PERCENTAGE_DIFFERENCE', 'julho_2026', '0.00', '400.00', null, 'NOT_APPLICABLE', 'NOT_APPLICABLE'),
      calculationRow('ABSOLUTE_DIFFERENCE', 'julho_2026', '0.00', '400.00', '400.00', 'INCREASE'),
    ]
    analytical.datasets[0].row_count = 2
  }

  if (scenario === 'null_missing') {
    comparison.operands.push(
      operand(
        'agosto_2026',
        'Agosto sem registro',
        metric(),
        period('august', 'Agosto de 2026', '2026-08-01', '2026-08-31'),
      ),
    )
    analytical.datasets[0].rows = [
      calculationRow('VALUE', 'julho_2026', '300.00', null, null, 'NOT_APPLICABLE', 'NOT_APPLICABLE'),
    ]
    analytical.datasets[0].row_count = 1
    executor.aligned_datasets[0].missing_bucket_count = 1
    executor.aligned_datasets[0].null_bucket_count = 1
  }

  if (scenario === 'multiple_visualizations') {
    analytical.visualizations = [
      visualization('comparison-table', 'DATA_TABLE', 'Primeiro: tabela', 1, true),
      visualization('comparison-bar', 'BAR_CHART', 'Segundo: barras', 2, false),
      visualization('comparison-kpi', 'KPI_CARD', 'Terceiro: indicadores', 3, false),
    ]
  }

  if (scenario === 'timeout') response.status = 'TIMEOUT'
  if (scenario === 'blocked') {
    response.status = 'BLOCKED'
    analytical.intent.readiness = 'BLOCKED'
  }

  return response
}

export function buildLegacyComparisonResponse(): QueryResponse {
  const response = buildComparisonResponse('period', 'CONSULTA')
  delete response.analytical_contract
  return response
}
