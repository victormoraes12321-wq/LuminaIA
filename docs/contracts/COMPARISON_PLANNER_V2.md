# Planner Generico De Comparacoes V2

## Contrato E Fronteira

`lumina.comparison-planner/1.0` transforma uma `QueryIntentV2` comparativa,
ja normalizada, em `QueryPlanV2`. O servico principal e
`ComparisonPlanner.plan(intent, context)`.

O planner e deterministico, stateless e independente de FastAPI, SQLAlchemy,
PostgreSQL, Oracle e OpenAI. Ele nao consulta valores, nao executa SQL e nao
calcula resultados financeiros. Catalogos governados entram por
`ComparisonCatalogProvider`; tenant, permissoes, limites e relogio entram por
`ComparisonPlanningContext`.

Fluxo:

```text
QueryIntentV2
  -> TimeWindow V2 ja normalizada
  -> catalogos e permissoes confiaveis
  -> ComparisonPlanner
  -> ComparisonPlanningResult
  -> QueryPlanV2
  -> lumina.comparison-executor/1.0
```

## Modelos Internos

- `ComparisonPlanningContext`: tenant autenticado, usuario, permissoes,
  fontes autorizadas, limites, timezone e referencia temporal.
- `ComparisonExecutionPlanDefinition`: comparacao publica e detalhes
  estruturais necessarios a execucao futura.
- `ComparisonOperandPlan`: metricas, janelas, filtros, dimensoes, fontes,
  origem, confianca e validacoes de um operando.
- `ComparisonFilterPartition`: filtros compartilhados, especificos,
  conflitantes e nao resolvidos.
- `ComparisonAlignmentSpecification`: dimensoes, granularidades, politicas de
  bucket/nulo, ordenacao e compatibilidade.
- `ComparisonPlanComplexity`: contagens, estimativa estrutural, score,
  classificacao e limite.
- `ComparisonPlanningIssue`: codigo estavel, severidade, campo, operando e
  efeito sobre esclarecimento ou execucao.
- `ComparisonPlanningResult`: plano, readiness, confidence, issues, warnings,
  strategy hint, complexidade, regras e divergencia de shadow mode.

Todos os modelos sao Pydantic v2 estritos, imutaveis e `extra="forbid"`.

## Tipos De Comparacao

O kind e inferido da estrutura resolvida, nao apenas da palavra usada:

- dois periodos: `PERIOD_VS_PERIOD`;
- tres ou mais periodos: `MULTI_PERIOD`;
- duas entidades: `ENTITY_VS_ENTITY`;
- tres ou mais entidades: `MULTI_ENTITY`;
- duas ou mais metricas compativeis: `METRIC_VS_METRIC`;
- realizado e meta oficial: `ACTUAL_VS_TARGET`.

Combinacoes multidimensionais preservam o kind primario e registram dimensoes
de alinhamento. Todos os operandos validos e sua ordem original sao
preservados.

## Operandos, Filtros E Baseline

Cada operando recebe ID deterministico, metricas explicitas, janelas
canonicas, filtros especificos e herdados, dimensoes, fontes e origem.
Operandos duplicados sao bloqueados; comparacoes prontas exigem ao menos dois.

Filtros da intencao sao compartilhados. Filtros declarados no operando
permanecem especificos. Um conflito explicito nao e promovido para o escopo
global e gera issue. Campos sao identificadores logicos governados; conteudo
com SQL, comentarios, tenant ou campos desconhecidos e rejeitado.

O baseline explicito e respeitado quando aponta para um operando existente.
Na ausencia dele, o primeiro operando valido e escolhido de forma estavel. O
planner apenas declara os calculos permitidos pelo contrato, como valor,
diferenca absoluta e percentual; nao os executa. Metricas com unidades
incompativeis preservam somente o valor e geram warning.

## Alinhamento E Complexidade

O alinhamento registra dimensoes compartilhadas, granularidade temporal,
granularidade de entidade, identidade da serie, ordenacao e politicas
explicitas para buckets ausentes e nulos. Granularidades incompativeis impedem
readiness `READY`.

A complexidade considera operandos, metricas, dimensoes, series e consultas
estimadas. Os limites do contexto impedem explosao combinatoria sem truncar
silenciosamente operandos. As classificacoes sao `LOW`, `MEDIUM`, `HIGH` e
`REJECTED`.

Strategy hints atuais:

- `SINGLE_AGGREGATION`;
- `CONDITIONAL_AGGREGATION`;
- `GROUPED_SERIES`;
- `PIVOT`;
- `TARGET_JOIN`;
- `UNDECIDED`.

Hints sao recomendacoes estruturais. Nao contem SQL e nao obrigam o executor.

## Readiness, Confidence E Origem

O resultado usa os estados canonicos `READY`, `CLARIFICATION_REQUIRED`,
`UNSUPPORTED`, `BLOCKED` e `ERROR`. Falha de resolucao nunca produz plano
parcialmente executavel.

Confidence agrega confianca da intencao, catalogos, operandos e warnings.
`FieldOrigin` permanece no contrato e nos operandos para distinguir valores
explicitos, herdados e derivados por regra.

## Seguranca Multi-Tenant

- tenant vem exclusivamente do contexto autenticado;
- plano sem tenant e bloqueado;
- fontes, metricas, dimensoes, entidades e metas respeitam allowlists;
- entidade ou meta de outro tenant e bloqueada;
- Oracle e proibido como fonte de consulta;
- metrica desconhecida nao vira faturamento;
- entidade desconhecida nao vira Cliente;
- meta ausente nao vira zero nem media historica;
- plano, logs e sidecar nao contem SQL, binds, credenciais ou pergunta
  integral.

## Rollout, Sidecar E Compatibilidade

| Flag | Padrao | Efeito |
| --- | --- | --- |
| `COMPARISON_PLANNER_V2_ENABLED` | `true` | Usa o plano comparativo V2 |
| `COMPARISON_PLANNER_V2_SHADOW_MODE` | `true` | Compara estrutura V2 e legado |

Com a flag principal desligada, o builder preserva `_build_plan_v2_legacy`.
Shadow mode registra apenas fingerprints, codigos e diferencas estruturais.
O sidecar `analytical_contract` inclui
`contract.extensions.comparison_planner`, com versao, readiness, regras,
strategy, complexidade e identidade de cache.

O adaptador legado aceita somente estruturas que o payload V1 representa sem
perda. Planos bloqueados nao executam. Planos `READY`, inclusive com N
operandos, sao consumidos por `lumina.comparison-executor/1.0`; o adaptador V1
nunca reduz o resultado canonico.

## Identidade De Cache E Observabilidade

A identidade de cache e derivada de versao, tenant, fingerprint de permissao,
metricas, fontes, filtros, periodos, operandos, dimensoes, calculos, baseline e
ordenacao. Labels humanas, texto integral, confidence e origem nao alteram a
identidade semantica.

Logs registram versao, fingerprint, readiness, kind, contagens, score,
strategy e codigos de issue. Perguntas, valores de filtros, dados e segredos
nao sao registrados.

## Exemplos Estruturais

`junho de 2026 versus julho de 2026` produz dois operandos temporais ordenados,
um baseline e calculos declarados. `compare Centro, Sul e Norte` produz tres
operandos de entidade sem reducao para dois. `realizado versus meta` fica
`UNSUPPORTED` quando o provider oficial nao possui a meta.

Os golden plans usam apenas identificadores e dados sinteticos. Nenhum exemplo
depende de dados reais da empresa.

## Integracao Com O Executor

O executor universal vive em `backend/services/comparison_execution/`. Ele
revalida tenant, permissao, fontes, metricas, dimensoes e limites antes de
compilar SQL governado. O strategy hint continua sendo sugestao.

O planner nao carrega SQL, binds ou valores. O executor nao reinterpreta a
pergunta. Cada etapa permanece com uma autoridade unica.

## Limitacoes E Proxima Etapa

O planner nao executa operandos, nao une datasets, nao calcula deltas, nao
renderiza dashboards e nao substitui a memoria conversacional.

A execucao e calculo agora pertencem a
`lumina.comparison-executor/1.0`. A proxima etapa e o Prompt 07, responsavel
pela renderizacao comparativa especializada.
