# Contratos Analiticos V2

## Objetivo

`lumina.analytics/2.0` e a representacao canonica, tipada e versionada da
intencao, plano e resposta analitica. Ela fica entre os pipelines de consulta e
os consumidores, sem substituir o payload V1 durante a migracao.

Os modelos vivem em `backend/contracts/analytical_v2/` e usam Pydantic v2 com:

- `strict=True`, `extra="forbid"` e modelos imutaveis;
- datas internas tipadas e valores decimais sem dependencia de `float`;
- listas para periodos, metricas, dimensoes e visualizacoes;
- origem e confianca para campos interpretados;
- erros, esclarecimento, fora de escopo, proveniencia e validacao tipados;
- metadados obrigatorios `schema_name=lumina.analytics` e
  `schema_version=2.0`.

## Modelos

| Area | Modelos principais |
| --- | --- |
| Envelope | `ContractMetadata`, `ExecutionScope`, `ConfidenceAssessment` |
| Intencao | `QueryIntentV2`, `MetricReference`, `DimensionReference`, `FilterSpecification` |
| Tempo | `TimeWindow` |
| Comparacao | `ComparisonOperand`, `ComparisonSpecification` |
| Visual | `VisualizationSpecification` |
| Plano | `QueryPlanV2`, `SourceReference`, `OrderingSpecification` |
| Resultado | `AnalyticalDataset`, `AnalyticalColumn`, `AnalyticalResponseV2` |
| Governanca | `ExecutionProvenance`, `ValidationCheck`, `ValidationReport` |
| Controle | `ClarificationRequest`, `AnalyticalError`, `LegacyCompatibility` |

## Invariantes

- Comparacao possui pelo menos dois operandos, IDs unicos e baseline existente.
- Comparacao temporal exige periodos distinguiveis em todos os operandos.
- `time_windows` nunca e reduzido a um campo singular no contrato canonico.
- A ordem das visualizacoes e preservada e existe no maximo uma primaria.
- Visualizacao referencia somente metrica do plano e dataset da resposta.
- `READY` exige operacao suportada e escopo autenticado com tenant.
- `OUT_OF_SCOPE` exige motivo e nao pode conter dataset.
- `CLARIFICATION_REQUIRED` exige pergunta objetiva e nao pode simular execucao.
- Validacao `PASSED` exige checks executados e sem falha obrigatoria.
- Isolamento de tenant so pode ser marcado como verificado com evidencia.
- `ORACLE` nao e uma fonte valida para plano de consulta de usuario.
- Segredos, SQL, codigo e chaves sensiveis sao rejeitados em extensoes JSON.

## Periodos E Visualizacoes

`extract_time_windows()` preserva todas as ocorrencias de mes/ano reconhecidas,
incluindo meses numericos e por extenso. O helper legado singular continua como
wrapper no orquestrador; novos contratos comparativos usam a API plural.

`extract_visualizations()` preserva ordem e remove apenas repeticoes exatas.
O pedido `tabela e grafico` gera `DATA_TABLE` e `BAR_CHART`. O parser nao cria
um formato para termos desconhecidos.

O normalizador temporal universal foi implementado como
`lumina.temporal.pt-BR/1.0`. Ele alimenta `time_windows`, comparacoes,
confianca, esclarecimentos e `contract.extensions.temporal`. Consulte
`TEMPORAL_NORMALIZER_V2.md`.

O planner comparativo `lumina.comparison-planner/1.0` recebe essa intencao e
produz `QueryPlanV2` sem executar dados. Metadados estruturais ficam em
`contract.extensions.comparison_planner`. Consulte
`COMPARISON_PLANNER_V2.md`.

O executor `lumina.comparison-executor/1.0` consome somente planos comparativos
`READY`, executa o clone PostgreSQL tenant-scoped, calcula com `Decimal` e
produz `AnalyticalResponseV2`. Metadados sanitizados ficam em
`contract.extensions.comparison_executor`. Consulte
`COMPARISON_EXECUTOR_V2.md`.

## Readiness E Roteamento

Estados V2:

- `READY`;
- `CLARIFICATION_REQUIRED`;
- `OUT_OF_SCOPE`;
- `UNSUPPORTED`;
- `BLOCKED`;
- `ERROR`.

O pre-roteador nao interrompe pergunta simples apenas porque o formato visual
nao foi informado. Estados nao prontos nao sao promovidos automaticamente para
execucao. Falha do intent engine retorna `INTENT_ENGINE_ERROR`; ela nao cria
entidade Cliente, metrica ou dataset.

## Proveniencia E Validacao

O sidecar registra a fonte como clone analitico, resultado materializado, cache
ou pipeline legado. Oracle aparece somente na linhagem tecnica externa ao plano
de consulta. O adaptador nao afirma reconciliacao nem isolamento sem evidencia.

Checks legados reais sao convertidos para `ValidationReport`. Ausencia de checks
gera `NOT_EXECUTED`, nunca `PASSED`.

## Schemas

Schemas versionados ficam em `docs/contracts/schemas/` e sao gerados por:

```powershell
.\backend\.venv\Scripts\python.exe .\scripts\export_analytical_contract_schemas.py
```

O script importa somente os contratos, nao abre banco, nao carrega startup e
nao chama Oracle ou OpenAI. A segunda geracao produziu hashes identicos para os
cinco arquivos.

## Seguranca E Limitacoes

- O sidecar publico nao incorpora linhas por padrao; informa colunas, contagem e
  truncamento sem enviar datasets ao provedor de IA.
- Diagnosticos completos continuam restritos ao perfil `ADMIN`.
- O core summary ainda nao comprova isolamento por tenant; o contrato registra
  `tenant_isolation_verified=false`.
- Planner, executor e a apresentacao comparativa especializada estao
  implementados. O frontend consome o contrato por meio de
  `lumina.comparison-presentation/1.0`, sem recalculo financeiro.
- Memoria conversacional distribuida e gateway analitico definitivo nao fazem
  parte desta etapa.
