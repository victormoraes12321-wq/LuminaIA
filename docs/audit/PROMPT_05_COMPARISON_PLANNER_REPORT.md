# Relatorio Do Prompt 05 - Planner Generico De Comparacoes

Data: 2026-07-27.

1. **Resumo da implementacao:** foi criada uma autoridade unica, deterministica
   e auditavel para transformar comparacoes V2 normalizadas em planos, sem
   executar ou inventar dados.
2. **Arquitetura:** o pacote `services/comparison_planning` separa modelos,
   providers governados, planner, rollout e adaptacao legada.
3. **Arquivos criados:** seis arquivos no pacote do planner, cinco arquivos de
   testes/fixtures, um golden com 12 planos, contrato documental, ADR 0008 e
   este relatorio.
4. **Arquivos alterados:** config, adapters V2, orquestrador, governanca de
   resposta, tipo frontend, AGENTS, changelog e documentos oficiais.
5. **Versao:** `lumina.comparison-planner/1.0`.
6. **Interface publica:** `ComparisonPlanner.plan(intent, context)` retorna
   `ComparisonPlanningResult`; exports estaveis ficam no `__init__.py`.
7. **Modelos internos:** context, result, execution definition, operand plan,
   filter partition, alignment, complexity e planning issue, todos estritos e
   imutaveis.
8. **Tipos suportados:** period vs period, multi-period, entity vs entity,
   multi-entity, metric vs metric e actual vs target oficial.
9. **Selecao do kind:** usa contagem e estrutura resolvida de periodos,
   entidades, metricas e papeis, nao palavras isoladas.
10. **Operandos:** IDs deterministas, ordem original, N itens, metricas,
    janelas, filtros, dimensoes, fontes, origem e confianca.
11. **Filtros compartilhados:** somente filtros realmente comuns da intencao
    entram no escopo global.
12. **Filtros especificos:** permanecem no operando; conflito explicito gera
    issue e nunca contamina outro operando.
13. **Baseline:** respeita ID explicito valido; caso ausente, usa politica
    estavel adequada ao tipo sem inventar valor.
14. **Calculos:** declara VALUE, diferencas, direcao ou rank permitidos pelo
    contrato; unidade incompativel remove deltas e gera warning.
15. **Alinhamento:** dimensoes canonicas, identidade de serie, politicas de
    bucket/nulo, ordenacao e compatibilidade.
16. **Granularidade:** series incompativeis exigem esclarecimento; comparacoes
    apenas de totais podem seguir com warning explicito.
17. **Complexidade:** estima operandos, metricas, dimensoes, series e consultas;
    excedente vira `REJECTED` sem truncamento.
18. **Strategy hints:** single aggregation, conditional aggregation, grouped
    series, pivot, target join e undecided.
19. **Readiness:** READY, CLARIFICATION_REQUIRED, UNSUPPORTED, BLOCKED e ERROR
    seguem os contratos V2.
20. **Confidence:** agrega evidencia da intencao, catalogos, operandos e issues;
    falhas materiais reduzem a classificacao.
21. **Field origins:** origens explicitas, herdadas e derivadas sao preservadas
    no contrato e nos operandos.
22. **QueryIntentV2:** e a unica entrada analitica; o planner nao reinterpreta
    a frase completa.
23. **TimeWindow V2:** inicio/fim canonicos e ordem plural sao preservados.
24. **ComparisonSpecification:** permanece o modelo publico, sem contrato
    concorrente.
25. **QueryPlanV2:** recebe comparacao validada, readiness, ordenacao, fontes e
    extensao do planner.
26. **Normalizador Temporal:** `build_intent_v2` aceita o resultado ja
    produzido, evitando segunda normalizacao.
27. **Orquestrador:** produz preview estrutural sanitizado para comparacoes,
    reutilizando a mesma normalizacao e sem executar o plano novo.
28. **Resolver:** catalogos entram por `ComparisonCatalogProvider`; o default
    adapta o metric registry oficial sem conexao de banco.
29. **Comparison engine:** fronteira preservada; o planner nao chama o engine
    de valores nem antecipa seus calculos.
30. **Executor atual:** permanece inalterado e recebe apenas casos legados
    representaveis sem perda.
31. **V1/V2:** payload V1 nao muda; sidecar V2 e adapter lossless foram
    preservados.
32. **Feature flags:** `COMPARISON_PLANNER_V2_ENABLED=true` e
    `COMPARISON_PLANNER_V2_SHADOW_MODE=true`.
33. **Shadow mode:** compara estruturas modernas/legadas por fingerprint e
    codigos, sem pergunta, valores, SQL ou dados.
34. **Observabilidade:** versao, readiness, kind, contagens, score, strategy e
    issues sanitizadas.
35. **Cache identity:** inclui tenant, permissao, versoes, fontes, metricas,
    filtros, periodos, operandos, dimensoes, calculos, baseline e ordenacao;
    labels nao alteram a chave.
36. **Seguranca multi-tenant:** tenant autenticado e allowlists sao
    obrigatorios; cross-tenant, Oracle, SQL em filtro e fontes proibidas sao
    bloqueados.
37. **Golden plans:** 12 cenarios revisados em
    `backend/tests/golden/comparison_plans_v2.json`.
38. **Testes criados:** 66 testes de tipos, filtros, alignment, complexidade,
    propriedades, performance, seguranca, multitenancy, rollout, adapters e
    goldens.
39. **Total coletado:** 737.
40. **Total aprovado:** 733.
41. **Falhas finais:** 0. A primeira suite teve uma falha documental por link
    do relatorio ainda inexistente; o link foi criado, o teste isolado passou e
    a suite completa foi repetida.
42. **Xfails:** 4, todos `strict=True` e preexistentes.
43. **XPASS:** 0.
44. **Xfails mantidos:** `LUMINA-GAP-DASH-001` (contrato UI_MODIFIED),
    `LUMINA-GAP-CONTEXT-001` (continuidade de quatro turnos),
    `LUMINA-GAP-CONTEXT-002` (cache semantico legado ausente) e
    `LUMINA-GAP-TENANT-001` (core summary sem tenant na view atual).
45. **Xfails removidos:** nenhum nesta etapa; nenhum teste do planner usa
    xfail.
46. **Pergunta junho/julho:** READY, confidence HIGH, sem issues.
47. **Plano junho/julho:** PERIOD_VS_PERIOD; operandos `june`
    2026-06-01..2026-06-30 e `july` 2026-07-01..2026-07-31; metrica
    `faturamento_comercial`; baseline `june`; conditional aggregation.
48. **Multi-period:** junho, julho e agosto preservados em tres operandos,
    READY.
49. **Entity vs entity:** Centro e Sul permanecem em filtros separados, READY.
50. **Multi-entity:** Centro, Sul e Norte preservados, com VALUE e RANK, READY.
51. **Metric vs metric:** comercial vs bruto na mesma unidade, READY; unidades
    diferentes ficam VALUE-only com warning.
52. **Actual vs target:** READY somente com provider oficial da meta e
    `TARGET_JOIN`.
53. **Meta inexistente:** `UNSUPPORTED` com
    `OFFICIAL_TARGET_NOT_AVAILABLE`; nenhum zero e inventado.
54. **Filtros especificos:** testes confirmam isolamento, precedencia de
    explicito sobre herdado e bloqueio de conflito.
55. **Comparacao composta:** Centro/junho vs Sul/julho por produto preserva
    ambos os escopos e usa grouped series.
56. **Complexidade excessiva:** `REJECTED`,
    `PLAN_COMPLEXITY_EXCEEDED`, sem descartar operandos.
57. **Goldens:** 12/12 aprovados; round-trip e idempotencia aprovados.
58. **Schemas:** cinco arquivos exportados duas vezes com hashes SHA-256
    identicos e sem diff entre geracoes.
59. **Temporais:** matriz conjunta de contratos, temporal e planner fechou em
    226 passed; nenhum xfail temporal.
60. **Seguranca:** 37 passed na selecao dedicada.
61. **Multi-tenant:** 10 passed, 1 xfailed historico.
62. **Lint:** ESLint aprovado, zero erro.
63. **TypeScript:** `npx tsc --noEmit` aprovado.
64. **Build:** Next.js 16.2.10 aprovado, 15 paginas geradas.
65. **Playwright:** 16/16 aprovados em desktop, tablet, mobile e ultrawide.
66. **OpenAI:** nao acessada; planner nao importa SDK e testes usam
    contencao/mocks.
67. **Oracle:** nao acessado; planner bloqueia a fonte e nao importa driver.
68. **Banco operacional:** nao acessado; somente PostgreSQL descartavel em
    `127.0.0.1:55432/luminaai_test`.
69. **Migrations:** nenhuma criada ou executada.
70. **Dependencias:** nenhuma adicionada.
71. **Lockfiles:** nenhum alterado.
72. **Comandos executados:** `git status/diff`, AST em 334 Python do projeto,
    selecoes unit/baseline/security/multitenant, 66 testes do planner, matriz
    de 226, suite completa, exportador de schemas duas vezes, lint, tsc, build
    e Playwright.
73. **Comandos nao executados:** Oracle/OpenAI reais, SQL operacional,
    migrations, sync, reconciliacao produtiva, commit, reset, clean e checkout;
    eram proibidos ou fora da fronteira.
74. **Git final:** worktree continua dirty com alteracoes preexistentes
    preservadas; nenhum arquivo do usuario foi revertido.
75. **Diff stat observado:** 49 arquivos rastreados, 4.931 insercoes e 734
    remocoes no worktree total; inclui trabalho preexistente e nao contabiliza
    arquivos ainda nao rastreados.
76. **Limitacoes:** o planner nao executa operandos, nao calcula deltas, nao
    renderiza comparacoes, nao cria metas e nao resolve os quatro gaps
    historicos. Suites legadas ainda escrevem em `services/blueprints.json`;
    como o arquivo ja estava modificado e sem snapshot seguro, nao foi feita
    limpeza aproximada que pudesse apagar trabalho preexistente.
77. **Proxima etapa:** `Prompt 06 - Executor universal de comparacoes`.
