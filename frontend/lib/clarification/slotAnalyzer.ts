export interface SlotOption {
  id: string
  label: string
  description?: string
}

export type SlotType =
  | 'RANKING_METRIC'
  | 'RANKING_LIMIT'
  | 'FILIAL'
  | 'COMPARISON_BASELINE'
  | 'ENTITY_SCOPE'
  | 'PERIOD'

export interface SlotConfig {
  id: string
  label: string
  slot_type: SlotType
  options: SlotOption[]
  default_id: string
}

export interface ClarificationRequirement {
  required: boolean
  intent: string
  known_slots: Record<string, string>
  missing_slots: string[]
  ambiguous_slots: string[]
  modal_title: string
  modal_description: string
  slot_configs: SlotConfig[]
}

function normalize(str: string): string {
  return str
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[?!.,]/g, '')
    .trim()
}

export function analyzeMissingSlots(question: string): ClarificationRequirement {
  const norm = normalize(question)

  // ── 0. Check if query is fully specified (Zero Missing Slots) ───────────
  const hasSpecificFilial = /\bfilial\s*([1-5]|todas|matriz)\b/.test(norm)
  const hasSpecificLimit = /\btop\s*\d+\b|\branking\s*(?:dos\s*)?\d+\b|\b\d+\s*(?:primeiros|melhores|produtos|vendedores|clientes)\b/.test(norm)
  const hasSpecificMetric = /\b(faturamento total|quantidade vendida|preco medio|preço médio|total faturado|volume de unidades|unidades vendidas|total de pedidos|quantos (vendedores|clientes|produtos|fornecedores))\b/.test(norm)
  const hasSpecificPeriod = /\b(janeiro|fevereiro|marco|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro|2026|1999|01\/2026|02\/2026|mes de janeiro|mês de janeiro|mes de fevereiro|mês de fevereiro|ano de 2026)\b/.test(norm)
  const hasSpecificFormat = /\b(grafico|gráfico|tabela|barras|colunas|linhas|pizza|area|área)\b/.test(norm)

  // If question is detailed and specific, NO popup is required
  if (
    (hasSpecificMetric && (hasSpecificPeriod || hasSpecificFilial || hasSpecificLimit)) ||
    (norm.startsWith('quantos ') || norm.startsWith('listagem dos 10')) ||
    (hasSpecificLimit && hasSpecificMetric)
  ) {
    return {
      required: false,
      intent: 'EXPLICIT_QUERY',
      known_slots: {
        metric: hasSpecificMetric ? 'EXPLICIT' : 'DEFAULT',
        period: hasSpecificPeriod ? 'EXPLICIT' : 'NONE',
        filial: hasSpecificFilial ? 'EXPLICIT' : 'NONE',
        limit: hasSpecificLimit ? 'EXPLICIT' : 'NONE',
        format: hasSpecificFormat ? 'EXPLICIT' : 'DEFAULT',
      },
      missing_slots: [],
      ambiguous_slots: [],
      modal_title: '',
      modal_description: '',
      slot_configs: [],
    }
  }

  // ── 1. RANKING DE VENDEDORES (Melhores / Piores Vendedores) ───────────
  if (
    norm === 'quais os melhores vendedores' ||
    norm === 'melhores vendedores' ||
    norm === 'piores vendedores' ||
    norm === 'ranking de vendedores'
  ) {
    const isPiores = norm.includes('piores')
    return {
      required: true,
      intent: isPiores ? 'SELLER_BOTTOM_RANKING' : 'SELLER_TOP_RANKING',
      known_slots: { entity: 'vendedor' },
      missing_slots: ['RANKING_METRIC', 'RANKING_LIMIT'],
      ambiguous_slots: ['RANKING_METRIC'],
      modal_title: isPiores ? 'Critério para Piores Vendedores' : 'Critério dos Melhores Vendedores',
      modal_description: 'Selecione a métrica de desempenho e a quantidade para compor o ranking:',
      slot_configs: [
        {
          id: 'ranking_metric',
          label: 'Métrica de Classificação',
          slot_type: 'RANKING_METRIC',
          options: [
            { id: 'faturamento', label: 'Maior Faturamento (R$)', description: 'Soma do valor total faturado' },
            { id: 'quantidade', label: 'Quantidade Vendida', description: 'Volume total de itens comercializados' },
            { id: 'pedidos', label: 'Número de Pedidos', description: 'Contagem de notas/pedidos emitidos' },
          ],
          default_id: 'faturamento',
        },
        {
          id: 'ranking_limit',
          label: 'Quantidade',
          slot_type: 'RANKING_LIMIT',
          options: [
            { id: '5', label: 'Top 5' },
            { id: '10', label: 'Top 10' },
            { id: '20', label: 'Top 20' },
          ],
          default_id: '5',
        },
      ],
    }
  }

  // ── 2. RANKING DE PRODUTOS (Melhor / Top / Destaque / Mais Vendidos) ─
  if (
    norm === 'qual foi o melhor produto' ||
    norm === 'melhor produto' ||
    norm === 'mostra os top produtos' ||
    norm === 'top produtos' ||
    norm === 'produtos destaque' ||
    norm === 'produtos que vendem mais' ||
    norm === 'produto campeao' ||
    norm === 'produto campeão'
  ) {
    return {
      required: true,
      intent: 'PRODUCT_TOP_RANKING',
      known_slots: { entity: 'produto' },
      missing_slots: ['RANKING_METRIC', 'RANKING_LIMIT'],
      ambiguous_slots: ['RANKING_METRIC'],
      modal_title: 'Critério de Destaque de Produtos',
      modal_description: 'Por qual indicador você deseja classificar os produtos?',
      slot_configs: [
        {
          id: 'ranking_metric',
          label: 'Métrica de Avaliação',
          slot_type: 'RANKING_METRIC',
          options: [
            { id: 'faturamento', label: 'Maior Receita (R$)', description: 'Faturamento total gerado pelo item' },
            { id: 'quantidade', label: 'Maior Quantidade de Unidades', description: 'Número de peças/unidades vendidas' },
          ],
          default_id: 'faturamento',
        },
        {
          id: 'ranking_limit',
          label: 'Quantidade de Itens',
          slot_type: 'RANKING_LIMIT',
          options: [
            { id: '5', label: 'Top 5 Produtos' },
            { id: '10', label: 'Top 10 Produtos' },
          ],
          default_id: '5',
        },
      ],
    }
  }

  // ── 3. RANKING DE CLIENTES (Clientes Top / Maiores) ───────────────────
  if (
    norm === 'clientes top' ||
    norm === 'top clientes' ||
    norm === 'clientes maiores' ||
    norm === 'melhores clientes'
  ) {
    return {
      required: true,
      intent: 'CLIENT_TOP_RANKING',
      known_slots: { entity: 'cliente' },
      missing_slots: ['RANKING_METRIC', 'RANKING_LIMIT'],
      ambiguous_slots: ['RANKING_METRIC'],
      modal_title: 'Critério dos Principais Clientes',
      modal_description: 'Escolha a base para ordenação dos clientes:',
      slot_configs: [
        {
          id: 'ranking_metric',
          label: 'Critério de Compra',
          slot_type: 'RANKING_METRIC',
          options: [
            { id: 'faturamento', label: 'Valor Total Comprado (R$)' },
            { id: 'pedidos', label: 'Frequência de Compras (Pedidos)' },
          ],
          default_id: 'faturamento',
        },
        {
          id: 'ranking_limit',
          label: 'Tamanho da Lista',
          slot_type: 'RANKING_LIMIT',
          options: [
            { id: '5', label: 'Top 5 Clientes' },
            { id: '10', label: 'Top 10 Clientes' },
          ],
          default_id: '5',
        },
      ],
    }
  }

  // ── 4. FILIAL ESPECÍFICA / MELHOR FILIAL ──────────────────────────────
  if (
    norm === 'venda da filial' ||
    norm === 'vendas da filial' ||
    norm === 'melhor filial' ||
    norm === 'filial mais forte'
  ) {
    const isMelhor = norm.includes('melhor') || norm.includes('mais forte')
    return {
      required: true,
      intent: isMelhor ? 'BRANCH_RANKING' : 'BRANCH_BREAKDOWN',
      known_slots: { entity: 'filial' },
      missing_slots: isMelhor ? ['RANKING_METRIC'] : ['FILIAL'],
      ambiguous_slots: isMelhor ? ['RANKING_METRIC'] : ['FILIAL'],
      modal_title: isMelhor ? 'Critério da Melhor Filial' : 'Identificação da Filial',
      modal_description: isMelhor ? 'Deseja comparar o faturamento ou o volume das filiais?' : 'Qual filial você deseja analisar?',
      slot_configs: isMelhor
        ? [
            {
              id: 'ranking_metric',
              label: 'Indicador Principal',
              slot_type: 'RANKING_METRIC',
              options: [
                { id: 'faturamento', label: 'Faturamento Total (R$)', description: 'Filial com maior receita bruta/líquida' },
                { id: 'quantidade', label: 'Volume de Itens Vendidos', description: 'Filial com maior quantidade de itens' },
              ],
              default_id: 'faturamento',
            },
          ]
        : [
            {
              id: 'filial',
              label: 'Filial Selecionada',
              slot_type: 'FILIAL',
              options: [
                { id: '1', label: 'Filial 1 (Matriz)' },
                { id: '2', label: 'Filial 2' },
                { id: '3', label: 'Filial 3' },
                { id: '4', label: 'Filial 4' },
                { id: '5', label: 'Filial 5' },
                { id: 'todas', label: 'Todas as Filiais (Consolidado)' },
              ],
              default_id: '1',
            },
          ],
    }
  }

  // ── 5. COMPARATIVO / COMPARE AS VENDAS ────────────────────────────────
  if (
    norm === 'compare as vendas' ||
    norm === 'comparativo de vendas' ||
    norm === 'vendas por periodo' ||
    norm === 'vendas por período' ||
    norm === 'ultimos meses' ||
    norm === 'últimos meses' ||
    norm === 'compare filial 1' ||
    norm === 'compare janeiro'
  ) {
    return {
      required: true,
      intent: 'SALES_COMPARISON',
      known_slots: { operation: 'compare' },
      missing_slots: ['COMPARISON_BASELINE'],
      ambiguous_slots: ['COMPARISON_BASELINE'],
      modal_title: 'Definição do Comparativo',
      modal_description: 'Qual base de comparação você gostaria de visualizar?',
      slot_configs: [
        {
          id: 'comparison_baseline',
          label: 'Tipo de Comparação',
          slot_type: 'COMPARISON_BASELINE',
          options: [
            { id: 'mes_a_mes', label: 'Janeiro vs Fevereiro de 2026', description: 'Comparação temporal mês a mês' },
            { id: 'filiais', label: 'Comparativo entre Filiais', description: 'Desempenho comparativo Filial 1 vs Filial 2' },
            { id: 'evolucao_diaria', label: 'Evolução Diária de Vendas', description: 'Série temporal diária do mês' },
          ],
          default_id: 'mes_a_mes',
        },
      ],
    }
  }

  // ── 6. REFERENTE INDEFINIDO (Qual foi o maior? / Qual vende mais?) ─────
  if (
    norm === 'qual foi o maior' ||
    norm === 'qual vende mais' ||
    norm === 'qual vende menos' ||
    norm === 'faz um ranking' ||
    norm === 'top 10'
  ) {
    return {
      required: true,
      intent: 'UNRESOLVED_ENTITY_RANKING',
      known_slots: {},
      missing_slots: ['ENTITY_SCOPE'],
      ambiguous_slots: ['ENTITY_SCOPE'],
      modal_title: 'O que você deseja comparar?',
      modal_description: 'Selecione qual entidade você gostaria de ranquear:',
      slot_configs: [
        {
          id: 'entity_scope',
          label: 'Entidade de Análise',
          slot_type: 'ENTITY_SCOPE',
          options: [
            { id: 'vendedor', label: 'Vendedores (Melhor Vendedor)', description: 'Ranking dos melhores representantes' },
            { id: 'produto', label: 'Produtos (Item Mais Vendido)', description: 'Ranking dos produtos campeões de venda' },
            { id: 'filial', label: 'Filiais (Maior Filial)', description: 'Comparativo de faturamento por filial' },
            { id: 'cliente', label: 'Clientes (Maior Cliente)', description: 'Maiores clientes compradores' },
          ],
          default_id: 'vendedor',
        },
      ],
    }
  }

  // ── 7. VISÃO EXECUTIVA / NÚMEROS DA EMPRESA ───────────────────────────
  if (
    norm === 'como estamos este mes' ||
    norm === 'como estamos este mês' ||
    norm === 'me mostre os numeros da empresa' ||
    norm === 'me mostre os números da empresa' ||
    norm === 'mostra o resultado' ||
    norm === 'me traz vendas' ||
    norm === 'quanto vendeu' ||
    norm === 'receita' ||
    norm === 'volume' ||
    norm === 'ticket' ||
    norm === 'media' ||
    norm === 'média' ||
    norm === 'faturamento' ||
    norm === 'faturamento fevereiro de 2026' ||
    norm === 'faturamento fevereiro'
  ) {
    return {
      required: true,
      intent: 'EXECUTIVE_OVERVIEW',
      known_slots: { period: '2026' },
      missing_slots: ['ENTITY_SCOPE'],
      ambiguous_slots: ['ENTITY_SCOPE'],
      modal_title: 'Visão dos Indicadores',
      modal_description: 'Escolha a perspectiva para visualização dos resultados:',
      slot_configs: [
        {
          id: 'entity_scope',
          label: 'Perspectiva Executiva',
          slot_type: 'ENTITY_SCOPE',
          options: [
            { id: 'visao_geral', label: 'Visão Geral Executiva', description: 'Faturamento consolidado, ticket médio e KPIs' },
            { id: 'por_filial', label: 'Detalhamento por Filial', description: 'Faturamento discriminado por loja/filial' },
            { id: 'por_vendedor', label: 'Desempenho da Equipe Comercial', description: 'Ranking de vendas por vendedor' },
          ],
          default_id: 'visao_geral',
        },
      ],
    }
  }

  // Default fallback: Not ambiguous
  return {
    required: false,
    intent: 'DIRECT_QUERY',
    known_slots: {},
    missing_slots: [],
    ambiguous_slots: [],
    modal_title: '',
    modal_description: '',
    slot_configs: [],
  }
}

export function buildClarifiedPrompt(
  originalQuestion: string,
  requirement: ClarificationRequirement,
  selections: Record<string, string>
): string {
  // 1. Ranking Vendedores
  if (requirement.intent.includes('SELLER')) {
    const isPiores = requirement.intent.includes('BOTTOM')
    const limit = selections['ranking_limit'] || '5'
    const metric = selections['ranking_metric'] || 'faturamento'
    const metricLabel =
      metric === 'quantidade'
        ? 'quantidade de itens vendidos'
        : metric === 'pedidos'
          ? 'número de pedidos'
          : 'faturamento'
    const adj = isPiores ? 'menor' : 'maior'
    return `Ranking dos ${limit} vendedores com ${adj} ${metricLabel} em 2026 em gráfico de barras`
  }

  // 2. Ranking Produtos
  if (requirement.intent === 'PRODUCT_TOP_RANKING') {
    const limit = selections['ranking_limit'] || '5'
    const metric = selections['ranking_metric'] || 'faturamento'
    const metricLabel = metric === 'quantidade' ? 'quantidade vendida' : 'faturamento'
    return `Top ${limit} produtos com maior ${metricLabel} em 2026 em gráfico de barras`
  }

  // 3. Ranking Clientes
  if (requirement.intent === 'CLIENT_TOP_RANKING') {
    const limit = selections['ranking_limit'] || '5'
    const metric = selections['ranking_metric'] || 'faturamento'
    const metricLabel = metric === 'pedidos' ? 'número de pedidos' : 'compras'
    return `Ranking dos ${limit} melhores clientes por ${metricLabel} em 2026 em tabela`
  }

  // 4. Filial
  if (requirement.intent === 'BRANCH_BREAKDOWN') {
    const filial = selections['filial'] || '1'
    if (filial === 'todas') {
      return 'Faturamento por filial em 2026 em gráfico de colunas'
    }
    return `Faturamento total e vendas da filial ${filial} no ano de 2026 em gráfico`
  }
  if (requirement.intent === 'BRANCH_RANKING') {
    const metric = selections['ranking_metric'] || 'faturamento'
    const metricLabel = metric === 'quantidade' ? 'quantidade de itens' : 'faturamento'
    return `Ranking das filiais por ${metricLabel} em 2026 em gráfico de colunas`
  }

  // 5. Comparativo
  if (requirement.intent === 'SALES_COMPARISON') {
    const baseline = selections['comparison_baseline'] || 'mes_a_mes'
    if (baseline === 'filiais') {
      return 'Comparativo de faturamento entre filial 1 e filial 2 em janeiro e fevereiro de 2026'
    }
    if (baseline === 'evolucao_diaria') {
      return 'Evolução diária das vendas na filial 1 em fevereiro de 2026 em gráfico de linha'
    }
    return 'Comparativo de vendas entre janeiro e fevereiro de 2026 na filial 1'
  }

  // 6. Entidade Indefinida
  if (requirement.intent === 'UNRESOLVED_ENTITY_RANKING') {
    const entity = selections['entity_scope'] || 'vendedor'
    if (entity === 'produto') return 'Top 5 produtos mais vendidos por receita em 2026 em gráfico de barras'
    if (entity === 'filial') return 'Faturamento por filial em 2026 em gráfico de colunas'
    if (entity === 'cliente') return 'Ranking dos 10 melhores clientes por compras em fevereiro de 2026 em tabela'
    return 'Top 5 vendedores por faturamento na filial 1 em fevereiro de 2026 em gráfico de barras'
  }

  // 7. Visão Executiva / Indicadores
  if (requirement.intent === 'EXECUTIVE_OVERVIEW') {
    const scope = selections['entity_scope'] || 'visao_geral'
    if (scope === 'por_filial') return 'Faturamento por filial em fevereiro de 2026 em gráfico de colunas'
    if (scope === 'por_vendedor') return 'Ranking dos 5 melhores vendedores por faturamento em janeiro de 2026 em tabela'
    return 'Visão executiva completa do faturamento de 2026 por filial e top vendedores'
  }

  return originalQuestion
}
