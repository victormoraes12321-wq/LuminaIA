# Relatorio Prompt 03 - Contratos Analiticos V2

Data: 2026-07-27.

1. **Resumo.** Implementado `lumina.analytics/2.0` com modelos estritos,
   adaptadores V1/V2, sidecar controlado, parser plural, roteamento fail-closed,
   tipos frontend, schemas, goldens, testes e documentacao.
2. **Arquitetura final.** `contracts/analytical_v2` e a camada canonica; os
   pipelines continuam produzindo V1 e a governanca anexa V2 quando habilitado.
3. **Arquivos criados.** Pacote V2, adaptador frontend, exportador, cinco
   schemas, dois testes, golden V2, dois guias, ADR 0006 e este relatorio.
4. **Arquivos alterados.** Configuracao, schema/router/query governance,
   orquestrador, cinco testes existentes, tipos/hook frontend e indices de docs.
5. **Modelos.** Metadata, scope, confidence, metric, dimension, filter, time
   window, entity, comparison operand/specification, visualization, intent,
   source, ordering, plan, provenance, validation, dataset, response e erros.
6. **Enums.** Intent, readiness, origin, confidence, granularity, operator,
   comparison, calculation, visualization, validation, source, role, operation,
   pipeline, classification, column type, error e out-of-scope.
7. **Validators.** Implementados os 20 invariantes obrigatorios, incluindo
   operandos, baseline, periodos, referencias, tenant, Oracle, versao e checks.
8. **Versionamento.** Todo envelope informa `lumina.analytics/2.0`; outra versao
   falha na validacao e nao recai para V1.
9. **V1 para V2.** `legacy_payload_to_v2` converte ambos os pipelines sem banco,
   IA ou formula duplicada.
10. **V2 para V1.** `v2_response_to_legacy` preserva o payload e escolhe somente
    o formato primario para os campos singulares V1.
11. **Sidecar.** Campo opcional `analytical_contract` em `QueryResponse`; linhas
    nao sao incorporadas por padrao.
12. **Flags.** Enabled, shadow, frontend e comparison executor; todas conservam
    defaults reversiveis e execucao comparativa universal desligada.
13. **Pipeline novo.** Router informa `PipelineKind.NEW` e a governanca gera V2
    com tenant autenticado.
14. **Pipeline legado.** O mesmo ponto gera V2 com `PipelineKind.LEGACY`.
15. **Frontend.** Tipos estritos e `normalizeQueryResponse`; V1 puro e sidecar V2
    sao aceitos sem alterar `DynamicRenderer`.
16. **Multiplos periodos.** `_month_ranges_from_text` e
    `extract_time_windows` preservam todas as ocorrencias reconhecidas.
17. **Multiplas visualizacoes.** Ordem e deduplicacao estavel; V1 materializado e
    pedido textual sao mesclados sem descartar o segundo formato.
18. **Comparacao.** Dois ou mais operandos, baseline valido e periodos distintos;
    o modelo nao calcula numeros.
19. **Ambiguidade.** Popup de formato ocorre apenas em pedido explicito de
    escolha sem formato concreto.
20. **Fora de escopo.** `OUT_OF_SCOPE` e distinto, possui motivo e nao gera
    dataset.
21. **Falha da IA.** Retorna `INTENT_ENGINE_ERROR`; nao cria Cliente, metrica,
    plano pronto ou dataset.
22. **Tenant.** Derivado do tenant e usuario autenticados na fronteira HTTP.
23. **Core summary.** Isolamento definitivo ainda nao comprovado; proveniencia
    declara `tenant_isolation_verified=false`.
24. **JSON Schemas.** Cinco arquivos em `docs/contracts/schemas`.
25. **Determinismo.** Duas exportacoes consecutivas mantiveram 5/5 hashes.
26. **Testes criados.** 62 novos casos contratuais/adapters/governanca, incluindo
    oito goldens sem campos volateis.
27. **Testes alterados.** Comparacao, visualizacoes, roteamento, erro da IA,
    unsupported, sidecar e classificacao de testes sem banco.
28. **Coleta.** 572 testes backend.
29. **Aprovados.** 568.
30. **Falhas.** 0.
31. **Xfails.** 4, todos `strict=True`.
32. **XPASS.** 0.
33. **Xfails removidos.** VIS-001, VIS-002, COMP-001, quatro COMP-002,
    ORCH-001 e ORCH-002; todos possuem teste regular aprovado.
34. **Xfails mantidos.** DASH-001 para dashboard V2; CONTEXT-001/002 para
    memoria distribuida; TENANT-001 para gateway analitico isolado.
35. **Pergunta exata.** `Compare o faturamento do Mes 06/2026 e 07/2026`
    produz `COMPARISON`, faturamento e dois periodos em ordem.
36. **Contrato junho/julho.** Janelas 2026-06-01..30 e 2026-07-01..31, dois
    operandos, baseline junho e quatro calculos solicitados.
37. **Variacoes.** Junho/julho por extenso, `com`, `versus` e ordem invertida
    passaram; tres periodos tambem sao preservados.
38. **Tabela e grafico.** `DATA_TABLE` seguida de `BAR_CHART`; pedido invertido
    preserva a ordem inversa.
39. **Roteamento simples.** Listagem cadastral chega ao intent engine e nao e
    capturada como ranking comercial.
40. **Fora de escopo.** Teste do Excel retorna `OUT_OF_SCOPE`, nao `AMBIGUOUS`.
41. **Multitenant.** 6 passed, 1 xfailed conhecido; tenant autenticado prevalece
    no contrato V2.
42. **Lint.** ESLint aprovado sem erros ou warnings.
43. **TypeScript.** `npx tsc --noEmit` aprovado.
44. **Build.** Next.js 16.2.10 aprovado, 15 paginas geradas.
45. **Playwright.** 16/16 aprovados em desktop, tablet, mobile e ultrawide.
46. **Oracle.** Nao acessado; mock e guarda de rede ativos.
47. **OpenAI.** Nao acessada; provider de teste e guarda de rede ativos.
48. **Banco operacional.** Nao acessado; testes usaram somente
    `127.0.0.1:55432/luminaai_test`.
49. **Migrations.** Nenhuma criada ou executada.
50. **Dependencias.** Nenhuma adicionada; requirements e lockfiles inalterados.
51. **Comandos.** Exportador duas vezes; pytest contratual; runners baseline,
    security, multitenant e all; lint, TypeScript, build, Playwright,
    `git diff --check`, compilacao e verificacoes de porta.
52. **Comandos nao executados.** Docker nao estava disponivel; foi usado o
    PostgreSQL 17 descartavel documentado. A primeira suite all expirou no
    limite externo de 120 s e foi repetida integralmente com 20 minutos.
53. **Limitacoes.** Normalizador temporal universal, executor comparativo,
    dashboard comparativo, memoria distribuida e gateway definitivo permanecem
    fora desta etapa.
54. **Git.** Worktree ja estava suja e foi preservada; nenhum commit, reset,
    clean ou checkout foi executado.
55. **Diff.** O stat final inclui alteracoes preexistentes dos Prompts anteriores;
    os arquivos deste Prompt estao listados nos itens 3 e 4.
56. **Proxima etapa.** `Prompt 04 - Normalizador temporal universal`.

## Evidencias Principais

```text
Suite backend: 568 passed, 4 xfailed, 0 failed, 0 xpassed em 575,51 s
Baseline: 12 passed, 2 xfailed
Security: 20 passed
Multitenant: 6 passed, 1 xfailed
Schemas: 5/5 hashes identicos na segunda geracao
Frontend: lint OK, TypeScript OK, build OK, Playwright 16 passed
```
