# Executor Universal De Comparacoes V2

## Contrato E Autoridade

`lumina.comparison-executor/1.0` e a autoridade deterministica para executar
um `QueryPlanV2` comparativo `READY`, alinhar operandos e calcular resultados.
O servico principal e:

```python
await UniversalComparisonExecutor.execute(plan, context)
```

O executor nao interpreta pergunta, nao chama OpenAI, nao aceita SQL livre e
nao consulta Oracle. A entrada vem de `lumina.comparison-planner/1.0`; datas
ja foram resolvidas por `lumina.temporal.pt-BR/1.0`.

## Fronteira De Seguranca

- tenant, papel e fingerprint de permissao vem do backend autenticado;
- tenant do plano deve ser igual ao contexto autenticado;
- fonte, metrica e dimensao devem existir nas allowlists do contexto;
- relacao, colunas e expressoes SQL vem apenas do catalogo de execucao;
- valores de filtros, periodos, entidades, tenant e limite usam binds;
- a consulta e somente `SELECT`;
- Oracle, fonte desconhecida e plano nao `READY` falham antes da execucao;
- a fonte PostgreSQL deve provar coluna de tenant antes de receber
  `tenant_isolation_verified=true`;
- SQL, binds, connection strings, credenciais e datasets nao entram em logs.

O runner de producao usa o pool asyncpg do clone por tenant. Antes da primeira
consulta de uma relacao ele confirma a coluna `tenant_id` em
`information_schema`. O runner SQLAlchemy e injetavel para testes, mas exige
evidencia explicita de isolamento.

## Modelos

Modelos Pydantic internos sao estritos, congelados e `extra="forbid"`:

- `ComparisonExecutionContext`;
- `ComparisonExecutionGraph` e `ComparisonExecutionNode`;
- `CompiledOperandQuery`;
- `OperandExecutionResult`;
- `AlignedComparisonDataset` e `AlignedComparisonRow`;
- `ComparisonCalculationResult`;
- `ComparisonExecutionIssue`;
- `ComparisonExecutionProvenance`;
- `ComparisonExecutionResult`.

O resultado registra status, plano, execucao, kind, operandos, datasets
alinhados, calculos, resumo deterministico, proveniencia, validacao, warnings,
issues, partial, versao, duracao, estrategia e cache.

## Grafo E Estrategias

O grafo explicita:

1. uma consulta por operando ou meta;
2. alinhamento;
3. calculos;
4. validacao;
5. montagem da resposta.

Tipos de no: `OPERAND_QUERY`, `TARGET_QUERY`, `ALIGNMENT`, `CALCULATION`,
`VALIDATION` e `RESPONSE_ASSEMBLY`.

Estrategias reconhecidas:

- `SINGLE_AGGREGATION`;
- `CONDITIONAL_AGGREGATION`;
- `MULTI_QUERY`;
- `GROUPED_SERIES`;
- `PIVOT`;
- `TARGET_JOIN`;
- `LEGACY_COMPATIBILITY`.

O hint do planner e preservado quando seguro. Fonte multipla cai para
`MULTI_QUERY`; realizado versus meta usa `TARGET_JOIN`. A estrategia nunca
autoriza identificadores fora do catalogo.

## Compilacao Governada

O catalogo padrao possui a fonte `vw_vendas_lm`, coluna temporal
`dtemissao_`, coluna de tenant `tenant_id`, dimensoes fisicas governadas e
expressoes das metricas oficiais do `metric_registry`.

O faturamento comercial usa somente `tp_ IN (2, 61)`. Transferencias ficam
fora de faturamento e total bruto. RB, devolucao e bonificacao sao metricas
separadas. Ticket e desconto usam formulas registradas. Lucro e vendas nao
faturadas permanecem bloqueados enquanto nao houver fonte oficial.

Filtros aceitos: igualdade, desigualdade, comparacoes, `IN`, `NOT_IN`,
`BETWEEN`, contains, starts-with, nulo e nao nulo. Campos sao IDs logicos;
valores nunca sao interpolados no statement.

## Execucao E Limites

`ComparisonExecutionContext` controla:

- timeout por query e total;
- maximo de operandos, queries e concorrencia;
- linhas por operando e total;
- tamanho de payload;
- precisao e arredondamento;
- politica de denominador zero;
- politica de bucket ausente e nulo;
- falha completa ou parcial;
- versao da fonte.

A concorrencia usa `asyncio.Semaphore`. O timeout total cancela o grupo. Retry
ocorre uma vez e somente para falhas transitorias reconhecidas. Erro de
contrato, seguranca, compilacao, metrica ou permissao nao e retentado.

Dataset acima do limite e marcado `TRUNCATED`; o resultado global fica
`PARTIAL`, nunca `READY`. Falha de operando obrigatorio produz `FAILED` ou
`PARTIAL` conforme politica explicita.

## Alinhamento

O alinhamento usa IDs canonicos, nao labels humanas. A chave e composta pelas
dimensoes declaradas no plano. Chave duplicada no mesmo operando e metrica
falha explicitamente.

Politicas:

- bucket ausente: `PRESERVE_NULL`, `ZERO_FILL` ou `OMIT`;
- nulo: `PRESERVE`, `ZERO_IF_ADDITIVE` ou `OMIT`.

Zero fill so e permitido para metrica aditiva. Comparacao metric-vs-metric e
realizado-vs-meta preserva a metrica fisica de cada operando, mas alinha ambas
no mesmo eixo quando unidades sao compativeis.

## Matematica

Valores financeiros permanecem `Decimal`. Nao ha conversao interna para
`float`.

Formulas:

```text
diferenca = target - baseline
percentual = ((target - baseline) / abs(baseline)) * 100
```

Direcoes: `INCREASE`, `DECREASE`, `STABLE` e `NOT_APPLICABLE`.

O arredondamento `ROUND_HALF_UP` ocorre apenas no resultado contratual. O
valor bruto permanece em `raw_result_value`.

Politicas de denominador zero:

- `NOT_APPLICABLE`;
- `ZERO_WHEN_BOTH_ZERO`;
- `EXPLICIT_INFINITY_UNSUPPORTED`;
- `ERROR`.

Participacao usa valor dividido pela soma disponivel. Ranking e denso e
deterministico. Meta ausente nunca vira zero, media ou previsao.

## Validacao E Proveniencia

O `ValidationReport` verifica tenant, permissao, quantidade de operandos,
integridade, orcamento de linhas, contagens, Decimal, delta assinado, formula
percentual e completude. Falha obrigatoria impede `PASSED`.

Cada proveniencia publica contem tenant, fonte, kind, view, versoes de
metrica, fingerprint de filtro, periodos, horario, sync/source version, cache,
pipeline, query fingerprint, reconciliacao e evidencia de isolamento.

A proveniencia interna acrescenta fingerprints de plano, grafo e operando,
versoes do planner, temporal, executor e validator.

## Cache

O cache local e opt-in por
`feature_flags.comparison_executor_local_cache`. A chave inclui tenant,
fingerprint de permissao, fonte e versao, plano, queries, metricas, periodos,
filtros, dimensoes, calculos e politicas matematicas. Nao existe cache
distribuido nesta versao.

## Compatibilidade V2 E V1

`execution_result_to_v2()` cria `AnalyticalResponseV2` validado e inclui
`contract.extensions.comparison_executor`. Os calculos ficam em dataset
deterministico; summaries de alinhamento registram buckets ausentes, nulos e
truncamento.

`execution_result_to_legacy()` usa o adaptador oficial V2 para V1 e inclui o
sidecar completo. Estruturas com mais de dois operandos nao sao reduzidas no
contrato canonico; o V1 recebe tabela de fallback e warning.

## Rollout

| Flag | Padrao | Efeito |
| --- | --- | --- |
| `COMPARISON_EXECUTOR_V2_ENABLED` | `false` | Retorna o resultado V2/V1 do executor |
| `COMPARISON_EXECUTOR_V2_SHADOW_MODE` | `false` | Executa apenas planos pequenos e compara estrutura |

As duas flags iniciam desligadas. O planner e os fluxos simples continuam
inalterados. Se a flag principal estiver ativa e a fonte nao comprovar
isolamento, a resposta e bloqueada em vez de cair silenciosamente para IA.

## Testes

O corpus dedicado cobre mais de 200 cenarios deterministas: periodos,
multi-periodo, entidades, metricas, meta, alinhamento, zero, ranking,
participacao, SQL/binds, timeouts, retries, budgets, cache, propriedades,
goldens e adaptadores.

O teste PostgreSQL obrigatorio usa o banco descartavel e prova:

- junho/2026 `300,00`;
- julho/2026 `400,00`;
- delta `100,00`;
- percentual `33,33`;
- direcao `INCREASE`;
- transferencias excluidas;
- tenant B invisivel.

Esse teste requer o PostgreSQL descartavel em `127.0.0.1:55432`.

## Integracao Com A Apresentacao

O resultado deste executor e consumido pela camada frontend
`lumina.comparison-presentation/1.0`, documentada em
[`COMPARISON_PRESENTATION_V2.md`](COMPARISON_PRESENTATION_V2.md). O adapter
preserva valores, calculos, validacao, proveniencia, ordem e estados. Nenhuma
formula deste executor e duplicada no navegador.

## Limites E Proxima Etapa

O executor nao cria componentes visuais e nao produz narrativa por IA. O
estado conversacional escalavel pertence ao Prompt 08.
