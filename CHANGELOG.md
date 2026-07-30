# Changelog

## 2026-07-30 - Semantic Retrieval E Entity Resolution V2

- Adicionado `lumina.semantic-retrieval/1.0` com indice PostgreSQL
  tenant-scoped, versionado, publicado e imutavel.
- Adicionados normalizador pt-BR, busca lexical, feature hash local sem rede,
  ranking/thresholds deterministas, ambiguity e clarification assinada.
- Enterprise Knowledge publicada e `MetricRegistry` alimentam o indice sem
  transferir autoridade semantica ou numerica.
- Integracao apos contexto/perfil aplica patch canonico somente em
  `V2_AUTHORITATIVE`; filtro field/value permanece separado e o executor nao
  consulta o indice.
- Adicionadas migration v16, APIs runtime/admin, cache, RBAC, auditoria,
  avaliacao sintetica, schemas, goldens, frontend administrativo e Playwright.
- Producao permanece `LEGACY_ONLY`; nenhuma dependencia, lockfile, Oracle,
  OpenAI, banco operacional ou download de modelo foi introduzido.

## 2026-07-29 - Feedback Governado e Aprendizado Supervisionado

- Adicionado `lumina.supervised-feedback/1.0`, tenant/user-scoped, com target
  persistido, redacao, triagem, review humano, CAS e idempotencia.
- Candidates exigem validacao explicita antes da aprovacao; exemplos e
  snapshots permanecem separados e publicados sao imutaveis.
- Adicionados import dry-run, retencao `EXPIRED`, cache apenas de manifest,
  observabilidade estrutural e exportacao JSONL incremental.
- Adicionadas APIs de usuario, review e curadoria, telas correspondentes,
  schemas, goldens, testes PostgreSQL e Playwright.
- Producao permanece `LEGACY_ONLY`; nenhuma chamada OpenAI/Oracle, treinamento,
  embedding, dependencia ou alteracao de lockfile foi introduzida.

## 2026-07-29 - Perfil Analitico Governado V2

- Adicionado `lumina.user-analytical-profile/1.0`, isolado por tenant e
  usuario, com contratos, policies, consentimento, checksum e CAS.
- O motor deterministico foi integrado depois do contexto e antes do planner;
  pedido atual, remocao, reset e contexto vencem preferencias pessoais.
- Adicionados repository/service PostgreSQL, migration v14, eventos, cache,
  exportacao, exclusao e importacao legada governada.
- Adicionadas rotas `/api/v2/me`, pagina Meu perfil e transparencia de
  preferencias aplicadas no chat.
- Adicionados schemas, goldens, testes backend e Playwright responsivo.
- Producao permanece `LEGACY_ONLY`; todas as flags iniciam desligadas.

## 2026-07-29 - Enterprise Knowledge V2

- Adicionada a autoridade semantica `lumina.enterprise-knowledge/1.0`.
- Criados assets estaveis, versoes imutaveis, review, approval, publication,
  rollback por nova versao, ownership, aliases, relations e eventos.
- Metric/KPI knowledge agora valida binding sem alterar o `MetricRegistry`.
- Busca lexical publicada preserva ambiguidade e isolamento de tenant.
- Adicionadas API `/api/v2/enterprise-knowledge`, migration v13, interface de
  glossario/governanca, schemas, goldens, testes e runbook.
- Rollout permanece `LEGACY_ONLY`; frontend, import, export e cache ficam
  desligados por padrao.

## 2026-07-28 - Context Resolution Engine V2

- Adicionado `lumina.context-resolution/1.0` com contratos Pydantic estritos,
  policies por campo, relacionamentos tipados e patches discriminados.
- Follow-up temporal, comparacao de periodos recentes, drill-down, correcao,
  remocao, negacao, clarification, branch e reset foram integrados ao estado
  PostgreSQL com CAS e idempotencia.
- O caminho V2 nao concatena contexto no texto; `SemanticPatch` legado passou
  a usar allowlist.
- Adicionados resumo publico no chat e diagnostico estrutural somente para
  `ADMIN`.
- Nenhuma migration, dependencia ou lockfile foi alterado; producao permanece
  `LEGACY_ONLY` e todas as novas flags iniciam desligadas.

## 2026-07-28 - Conversation State V2

- Adicionados contratos estritos `lumina.conversation-state/1.0`.
- Adicionadas sessoes PostgreSQL, nos/eventos append-only, snapshots e ledger
  de importacao pela migration v12 explicita.
- Adicionados criptografia Fernet, idempotencia, CAS, epochs de reset,
  retention/purge e APIs com escopo de dono.
- Adicionados metadados de conversa na query e persistencia web escopada.
- Removido `_last_semantic_plans` como autoridade em RAM.
- Producao permanece `LEGACY_ONLY`; migration operacional nao foi executada.

## 2026-07-28 - Apresentacao Comparativa V2

- Criada a camada `lumina.comparison-presentation/1.0` com tipos estritos,
  adapters V2/V1, estados explicitos e preservacao de operandos e visualizacoes.
- Integrado renderer especializado ao `DynamicRenderer`, chat e runtime inline,
  com fallback legado, feature flag e shadow mode desligados por padrao.
- Adicionados cards, tabela, ECharts, realizado versus meta, Trust Center,
  exportacao CSV, RBAC, acessibilidade, fullscreen e responsividade.
- Confirmado por testes que null, missing, zero, denominador zero, partial,
  truncated, timeout e blocked nao sao confundidos.
- Nenhuma formula financeira, migration, dependencia ou lockfile foi alterado.

## 2026-07-28 - Executor Universal De Comparacoes V2

- Adicionado `lumina.comparison-executor/1.0` para executar `QueryPlanV2`
  comparativo `READY` no clone PostgreSQL tenant-scoped.
- Compilacao SQL governada por catalogo, identifiers allowlisted, valores em
  binds e bloqueio de Oracle, OpenAI e SQL livre.
- Grafo de execucao, concorrencia limitada, timeout por operando/total, retry
  transitorio, budgets, cache local opt-in e resultados parciais explicitos.
- Alinhamento canonico, missing/null policies, `Decimal`, delta assinado,
  percentual, zero denominator, ranking, participacao e meta oficial.
- Validacao matematica e proveniencia com fingerprints e evidencia de
  isolamento.
- Adapters V2/V1, sidecar, tipos frontend e integracao aditiva no orquestrador
  atras de flags desligadas por padrao.
- Credenciais de conexao foram desacopladas de `oracle_service`, permitindo ao
  runtime do clone PostgreSQL carregar sem importar o driver Oracle.
- Adicionados mais de 200 testes dedicados, golden results e ADR 0009.

## 2026-07-27 - Planner Generico De Comparacoes V2

- Adicionado `lumina.comparison-planner/1.0`, deterministico e sem acesso a
  SQL, banco, Oracle ou OpenAI.
- Planejamento de comparacoes por periodo, entidade, metrica e meta oficial,
  preservando N operandos, ordem, filtros especificos, baseline e alinhamento.
- Validacao de tenant, permissoes, catalogos, granularidade e complexidade sem
  fallback silencioso ou truncamento.
- Integracao aditiva com QueryIntentV2, QueryPlanV2, normalizador temporal,
  sidecar, adapters legados, feature flags e shadow mode sanitizado.
- Adicionados golden plans e testes unitarios, de seguranca, multitenancy,
  propriedades, compatibilidade e rollout.

## 2026-07-27 - Normalizador Temporal V2

- Adicionado `lumina.temporal.pt-BR/1.0`, deterministico e com contexto
  injetavel.
- Datas civis, relativas, moveis, fechadas, acumuladas e fiscais.
- Distincao entre range, lista e comparacao sem perda de operandos.
- Integracao aditiva com contratos V2, intent, orquestrador e legado.
- Rollout por flags, shadow mode sem texto sensivel e corpus pt-BR.

## 2026-07-27 - Contratos Analiticos V2

- Criado `lumina.analytics/2.0` com Pydantic estrito para intencao, plano,
  periodos, comparacao, visualizacoes, proveniencia, validacao e resposta.
- Adicionados adaptadores V1/V2, sidecar opcional, shadow mode e feature flags
  para rollout reversivel nos pipelines novo e legado.
- Parser plural passou a preservar todos os meses reconhecidos; tabela e grafico
  permanecem como duas visualizacoes na ordem solicitada.
- Fora de escopo, esclarecimento, unsupported e erro tecnico foram separados;
  falha da IA nao cria mais fallback Cliente.
- Frontend ganhou tipos V2 e adaptador central sem alterar o dashboard atual.
- Cinco JSON Schemas e oito goldens V2 foram versionados.
- Validacao: 572 coletados, 568 passed, 4 xfailed, lint/TypeScript/build
  aprovados e Playwright 16/16.

## 2026-07-22 - Auto-Cura Do Catálogo, Expansão De Consultas Determinísticas E Testes Massivos De Estresse

- Adicionados tópicos determinísticos `produto_mais_vendido`, `estoque_produto` e `financeiro_aberto` no `NewQueryOrchestrator`, evitando despachos indesejados ao LLM que retornavam `UNSUPPORTED`.
- Criadas as rotinas `fetch_product_ranking` e `fetch_financial_open` no `SalesValueBreakdownService` (`sales_value_breakdown.py`), permitindo consultar ranking de produtos mais vendidos cruzados com saldo de estoque (`VW_PRODUTOS_CAD_LM` x `VW_VENDAS_LM`) e contas financeiras em aberto (`VW_FINANCEIRO_LM`).
- `Canonicalizer` reforçado com auto-cura semântica de entidades e métricas desconhecidas, redirecionando aliases conceituais (ex: `item`, `mercadoria`, `estoque`, `parcela`, `cobranca`, `comissao`) para entidades canônicas (`Produto`, `Financeiro`, `Venda`, `Vendedor`, `Cliente`, `Cidade`, `Estado`, `Categoria`).
- Filtros desconhecidos no `Canonicalizer` passam a ser descartados com log de aviso (auto-cura graciosa) em vez de interromper o fluxo com erro `UNSUPPORTED`.
- Parser de período (`_month_range_from_text`) expandido para suportar menções a anos isolados de 4 dígitos (ex: `no ano de 2026`, `em 2026`, `ano 2026`, `2026`), gerando o intervalo `YYYY-01-01` a `YYYY-12-31` em vez de recair no fallback do mês corrente.
- Adicionada tolerância para typos e variações gramaticais de usuários (ex: `mais vendidoa`, `mais vendida`, `top produtos`).
- Preenchimento do campo `sample_rows` no payload principal do orquestrador para garantir que a Tabela Detalhada com Colunas e os componentes de gráficos do frontend renderizem todas as linhas extraídas.
- Executada suíte massiva de testes de estresse e mineração de falhas com **164 cenários automatizados (incluindo multi-turn e interatividade)** obtendo **100% de taxa de aprovação (0 falhas)**.

## 2026-07-21 - Governanca De Resposta, Rastreabilidade E Operacao

- Consultas da IA passaram a declarar explicitamente `POSTGRESQL_ANALYTICAL_CLONE` como fonte; Oracle permanece restrito a sincronizacao e reconciliacao tecnica.
- Toda resposta recebe `data_status` com horario real da ultima sincronizacao, idade, estado de frescor e status do job, sem horarios ou metricas simuladas no frontend.
- Adicionada validacao matematica de total bruto sem transferencias, total de movimentos, soma das filiais, duplicidade de dimensoes e soma de rankings pivotados.
- Respostas de `ADMIN` recebem `admin_diagnostics`; perfis comuns nao recebem trace, plano ou telemetria.
- A dashboard ganhou acoes de continuidade e rastreabilidade. `Ver documentos` consulta o PostgreSQL e detalha pedido, nota, filial, cliente, vendedor, CFOP, operacao e valor.
- Continuidade estruturada passou a herdar filial em perguntas curtas, com limpeza explicita ao pedir todas as filiais.
- Rotas tecnicas foram restringidas por perfil no frontend e no backend.
- Sincronizacao agendada passou a executar reconciliacao tecnica diaria; scheduler ganhou reinicio automatico e estado no `/health/deep`.
- Frontend ganhou `/healthz` e nova tentativa automatica para falhas transitorias 502/503/504.
- Validacoes: 49 testes focados, `py_compile`, build de producao, TypeScript e lint dos arquivos alterados. Fluxo real validou faturamento 07/2026 e 500 documentos de rastreabilidade.

## 2026-07-20 - Separacao RB, Devolucao E Transferencias Fora Do Total

- `sales_value_breakdown` passou a classificar `saida_rb` e `devolucao` em categorias separadas. RB usa `tp_ = 9` ou descricao `SAIDA RB`; devolucao usa descricao contendo `DEVOL`.
- `total_bruto` agora exclui `transferencias`; transferencias continuam em coluna propria e `total_movimentos_view` guarda o total operacional completo apenas para auditoria.
- Rankings, resumo por periodo, ticket bruto e auditoria ERP x clone passaram a usar os mesmos pedidos/valores sem transferencias quando a metrica for faturamento/bruto.
- Perguntas de RB e devolucao nao compartilham mais a mesma intencao: `Vendas RB por vendedor` ranqueia RB; `Devolucao por vendedor` ranqueia devolucao e retorna zero quando a view nao tiver linhas desse tipo.
- Corrigida a tipagem de colunas de contagem pivotadas, evitando formatar `pedidos_saida_rb` como moeda.
- Validacoes executadas: sync incremental de `VW_VENDAS_LM` com 1.012 e depois 1.019 linhas recentes; `pytest tests/test_sales_value_breakdown.py tests/test_core_summary_output_intents.py tests/test_metric_registry.py tests/test_erp_reconciliation.py -q` com 44 testes.
- Reconciliacao ERP x clone: 06/2026 fechou 100%; 07/2026 e periodo corrente vivo e recebeu novas vendas durante a auditoria, gerando delta movel de R$ 1.650,00 apos sync. Para fechamento exato de 07/2026, usar periodo fechado ou sincronizar imediatamente antes da leitura final.

## 2026-07-20 - Hardening De Metricas, Preferencias E Auditoria Final

- Criado `services/erp_reconciliation.py` e `backend/scripts/run_erp_reconciliation.py` para bater faturamento 06/2026 e 07/2026, ranking vendedores, filial por filial, RB, devolucao, ticket medio, top clientes e filtros oficiais contra o ERP Oracle quando a conexao estiver acessivel.
- Criado `services/financial_source_discovery.py` e `backend/scripts/run_financial_source_discovery.py` para mapear fontes candidatas de lucro bruto/liquido e vendas ainda nao faturadas sem inventar valores.
- Corrigida compatibilidade do pool Oracle assíncrono e resolucao automatica de owner das views (`DONWMS.VW_VENDAS_LM`, `DONWMS.VW_VENDEDOR_CAD_LM`, `DONWMS.VW_CLIENTES_CAD_LM`) na reconciliacao.
- A sync da Data Platform ganhou `force_full` e incremental com janela de sobreposicao por `dtemissao_`, evitando perder vendas tardias no mesmo dia.
- Criado `backend/scripts/run_lm_view_resync.py` para ressincronizar views LM com staging e troca atomica.
- Perguntas de lucro e vendas ainda nao faturadas passaram a anexar o diagnostico de fonte em `bi_intelligence.financial_source_discovery` e `trust_center.financial_source_discovery`.
- Gerados `backend/reports/erp_reconciliation_2026-07-20.json` e `backend/reports/financial_source_discovery_2026-07-20.json`; apos full sync e incremental de sobreposicao, a batida ERP x clone fechou com `overall_status=ok`.
- Validacoes adicionais: `py_compile` dos novos modulos/scripts e `pytest tests/test_financial_source_discovery.py tests/test_erp_reconciliation.py tests/test_metric_registry.py tests/test_sales_value_breakdown.py tests/test_core_summary_output_intents.py -q` com 46 testes.
- Criado `services/metric_registry.py` como dicionario oficial de metricas criticas, com fonte, formula, filtros, granularidade, confianca e limites conhecidos.
- Respostas deterministicas de vendas passaram a incluir `bi_intelligence.metric_definitions`, `calculation_steps` e `trust_center.metric_registry`, permitindo auditoria de "como calculei" sem mudar o contrato principal.
- Criado model/rota/schemas de preferencias de dashboard (`dashboard_preferences`) para persistir por usuario/tenant a base de valor, formato de resposta e instrucoes opcionais.
- Frontend passou a carregar/salvar preferencias de dashboard no backend, mantendo `localStorage` apenas como fallback defensivo.
- Adicionado `GET /health/deep` para diagnostico de API, PostgreSQL e status de IA/invocacao, e o frontend passou a consultar esse endpoint para enriquecer mensagens de erro de conexao/servidor.
- Parser de periodo passou a aceitar mes por extenso com barra e abreviacoes (`julho/2026`, `jul/2026`), alem de continuidade com termos como `mesmo`/`mesma`.
- Perguntas leigas do tipo `qnt vendeu rb vendedor jul/2026 tabela` passaram a ser interpretadas como ranking de RB por vendedor.
- Criado `backend/scripts/run_core_sales_redteam.py`, bateria oficial reproduzivel de 461 perguntas para faturamento, filiais, bases liquida/bruta, graficos, rankings, RB, desconto, ticket, unsupported, continuidade e entradas adversariais.
- Auditoria final gerou `backend/reports/core_sales_redteam_2026-07-20.json`, `backend/reports/final_metric_audit_2026-07-20.json`, `backend/reports/final_metric_audit_summary_2026-07-20.json` e `docs/reports/2026-07-20-hardening-final-audit.md`.
- Validacoes executadas: `py_compile`, `pytest` focado com 38 testes, `npm run build`, redteam completo 461/461 e auditoria numerica por metrica/filial para 06/2026 e 07/2026.

## 2026-07-20 - QA Massiva Do Chat Analitico, RB E Visualizacoes

- Ranking de vendas por vendedor passou a sair enxuto por padrao: uma linha por vendedor, colunas por filial, total no fim e somente dados essenciais.
- Detalhes operacionais como saida RB, devolucao, bonificacao, transferencias e demais movimentos so sao abertos quando solicitados explicitamente ou quando a pergunta pede saida detalhada/completa.
- Perguntas de `vendas RB` passaram a ter intencao propria, incluindo ranking/top por vendedor e resumo por filial com total geral; devolucao fica em metrica propria.
- Perguntas de faturamento entendem base liquida/comercial, bruta ou ambas; perguntas de lucro e vendas ainda nao faturadas retornam aviso de fonte indisponivel quando a view nao possui campos para calculo confiavel.
- Perguntas que pedem grafico, pizza, linha ou tabela+grafico agora alteram o `chart_type`/`visualizations` do payload deterministico em vez de sempre retornar tabela.
- O seletor de modo de resposta passou a afetar respostas deterministicas: operacional encurta, analitico mantem o detalhamento padrao e executivo adiciona leitura executiva/alertas.
- Frontend passou a abrir configuracao de resposta para perguntas analiticas ambiguas, com base do valor, formato do dashboard e instrucoes opcionais salvas como padrao local.
- A configuracao de resposta foi ampliada para outros temas analiticos de BI, como produtos, estoque, pedidos, compras, fornecedores, financeiro, metas, filiais e regioes.
- Campo vazio do chat passou a exibir atalhos de consulta para orientar usuarios leigos sem exigir que conhecam os termos tecnicos do sistema.
- Continuidade passou a herdar tambem metrica e dimensao quando a pergunta usa referencias como `esse dado`, `esse ranking` ou `agora separa por vendedor`; respostas com periodo ISO (`2026-07-01 a 2026-07-31`) tambem passam a alimentar a heranca de periodo.
- Ranking de clientes sem `todos`/`sem limite` passou a retornar top 50 por padrao para evitar planilhas gigantes; `top N` e `todos os clientes` continuam respeitados.
- Normalizacao de texto no backend foi reforcada para perguntas com mojibake ou `?` no lugar de acentos (`m?s`, `gr?fico`, `l?quido`).
- Validacoes executadas: `py_compile`, `pytest tests/test_core_summary_output_intents.py tests/test_sales_value_breakdown.py -q` com 31 testes, `npm run build`, conversa real sequencial com 12 turnos/0 falhas e bateria agressiva real com 374 perguntas/0 falhas cobrindo formatos, filiais, modos, RB, desconto, ranking de clientes, unsupported, acentos quebrados e continuidade.

## 2026-07-18 - Auditoria Da Fonte De Desconto

- Confirmado que a tabela local `vw_vendas_lm` nao possui coluna explicita de desconto; os campos disponiveis sao venda, quantidade, preco unitario, total, cliente, vendedor, filial, produto, CFOP, NCM, plano, pedido e nota.
- Validado que a derivacao anterior `qtde_ * p_unit_ - ptotal_` retorna `R$ 0,00` de desconto positivo no clone atual, indicando que `p_unit_` ja chega liquido ou que o desconto real nao foi exposto pela view.
- O modulo `sales_value_breakdown` passou a detectar automaticamente colunas reais de desconto quando forem adicionadas a `vw_vendas_lm` (`desconto_total`, `valor_desconto`, `vl_desconto`, `vldesconto`, `vldesc` ou `desconto`).
- Respostas de desconto agora incluem aviso, baixa confianca e metadados de fonte quando a view nao traz desconto real, evitando afirmar `R$ 0,00` como ausencia comprovada de desconto no ERP.
- Acesso direto ao Oracle real para confirmar a view de origem nao foi concluido nesta maquina porque `10.253.7.2:1521` nao respondeu ao teste TCP.

## 2026-07-18 - Filiais Como Dimensao Padrao De Vendas

- Perguntas criticas de faturamento, ticket, desconto, maior vendedor, ranking de vendedores e ranking/top clientes passaram a tratar `filial_` como dimensao padrao.
- Quando o usuario pede faturamento total, o sistema retorna o total de todas as filiais e tambem detalha cada filial na tabela.
- Quando o usuario informa uma filial especifica (`filial`, `loja` ou `unidade`), o filtro comercial restringe aquela filial sem alterar as demais regras de movimento.
- Rankings de vendedores/clientes exibem uma linha por vendedor/cliente, com colunas por filial e colunas de total no fim da linha.
- Faturamento por filial exibe as filiais e uma linha final `Total geral` somando todas elas.
- Ticket medio e desconto incluem linhas por filial, com total geral quando a pergunta nao restringe uma filial.
- O transformer de tabelas preserva a uniao das colunas de todas as linhas, evitando que detalhes adicionados depois da primeira linha fiquem ocultos no dashboard.

## 2026-07-18 - Decomposicao De Valores De Venda

- Criado modulo central `sales_value_breakdown` para decompor valores de vendas por categoria operacional.
- Perguntas criticas de faturamento, ranking de vendedores, maior vendedor, ticket e desconto passaram a expor valores separados: faturamento comercial, saida RB, devolucao, venda bonificada, transferencias, outras vendas, remessa/uso e consumo, outros movimentos, total bruto sem transferencias e total geral de movimentos para auditoria.
- O valor principal continua sendo o faturamento comercial (`tp_ IN (2, 61)`), com todas as filiais por padrao ou filial especifica quando solicitada; os demais movimentos aparecem em linhas ou colunas proprias.
- Ranking de vendedores manteve ordenacao pelo faturamento comercial e passou a exibir filial, total bruto e categorias de movimento de cada vendedor.
- Colunas monetarias da decomposicao passaram a ser tipadas como moeda no payload de tabela.

## 2026-07-17 - Correcao De Perguntas Criticas, Sessao E Encoding

- Adicionado caminho deterministico no orquestrador para perguntas prioritarias de faturamento, ticket medio, desconto, maior vendedor e maior cliente.
- Separada a intencao de saida entre `maior/top` e `ranking/lista/todos`, evitando que perguntas como "ranking com todos os vendedores" retornem apenas o mesmo resultado de "qual vendedor mais vendeu".
- Perguntas criticas de faturamento e ranking passaram a aplicar o filtro comercial do ERP (`tp_ IN (2, 61)`), evitando somar saidas como `SAIDA RB`, bonificacoes e transferencias como faturamento padrao.
- Corrigida continuidade de conversa com `session_id`, historico recente e `parent_id`, incluindo heranca de periodo quando a pergunta seguinte nao informa nova data.
- Ranking de vendedores passou a ignorar o cadastro tecnico `PADRAO`; ranking/top clientes passou a ignorar `LAGES E LOPES LTDA` quando representa a loja interna.
- Desconto total e desconto medio passaram a usar derivacao deterministica por item sobre a view de vendas.
- Clique na logo do sistema passou a limpar a conversa atual.
- Criada camada defensiva de reparo de encoding no frontend para textos de API, historico, favoritos, dashboard runtime, tabelas e mensagens de autenticacao.
- Labels tecnicos de tabelas passaram por humanizacao centralizada no `data_transformer`, incluindo `Observacao`, `Ticket medio` e `Valor formatado`.
- Corrigida a base da API em ambiente local para preservar `localhost` ou `127.0.0.1`, evitando perda de cookie HttpOnly entre hosts loopback diferentes.
- Regeneradas referencias automaticas de API e inventario de codigo.
- Validacoes executadas: `python -m py_compile` nos arquivos alterados, `npm run build`, E2E Playwright em `http://127.0.0.1:3000/login` com login, pergunta real e verificacao de ausencia de mojibake renderizado.

## 2026-07-17 - Documentacao Atualizada

- Criado `docs/current-status.md` como fonte curta do estado atual pos-correcoes.
- READMEs, guias operacionais, arquitetura, IA, frontend, backend, Data Platform, performance, seguranca, manutencao e relatorios receberam addenda ou referencias ao estado atual.
- A certificacao de 2026-07-09 foi mantida como baseline historico; validacoes de 2026-07-17 foram registradas como validacao incremental.

## 2026-07-09 - Documentacao Enterprise Oficial

- Gerada documentacao tecnica oficial do LuminaAI.
- Criados guias de arquitetura, APIs, IA, backend, frontend, Data Platform, banco analitico, cache, scheduler, seguranca, performance, instalacao, deploy, operacao, manutencao, desenvolvimento e governanca.
- Criados ADRs iniciais para decisoes arquiteturais centrais.
- Documentacao alinhada ao estado validado: backend `303 passed`, certificacao Enterprise `7 passed`, frontend lint/build OK, Playwright `16 passed`, load smoke `50 ok` e import cycles runtime `0`.

## 2026-07-09 - Hardening Semantico Corporativo

- Centralizada a canonicalizacao de metricas no Semantic Layer para aliases, sinonimos dinamicos, variacoes com espaco/underscore, plural/singular e similaridade segura.
- Business Layer, Semantic Engine, KPI Discovery e Plan Validator passaram a compartilhar a mesma fonte semantica corporativa.
- Adicionados testes de regressao para `total_vendas`, `valor das vendas`, `pedidos_totais`, `ticket medio`, `churn`, `LTV`, `CAC`, conversao e typo leve.
- Regressao backend completa reexecutada com `303 passed`.

## 2026-07-09 - Certificacao Automatizada Por Testes

- Criada suite `backend/tests/test_enterprise_production_certification.py` para validar contratos criticos, separacao arquitetural, seguranca JWT, Dashboard Studio, documentacao e gates operacionais.
- Cobertura Playwright ampliada com projeto mobile alem de desktop, tablet e ultrawide.
- Reexecutadas validacoes completas: backend `303 passed`, certificacao Enterprise `7 passed`, frontend lint/build OK, Playwright `16 passed`, import cycles `0`, `npm audit` sem vulnerabilidades, `pip check` OK e load smoke local `50 ok`.

## 2026-07-09 - Revisao Final De Producao

- Score Enterprise final documentado: 98/100.
- Removidas supressoes ESLint/TS restantes.
- Dockerfile frontend ajustado para `npm ci`.
- Artefatos gerados de lint removidos.
- Encoding reparado em arquivos de codigo/UI/logs sem alterar dados persistidos.

## 2026-07-08 - Hardening Enterprise

- JWT migrado para PyJWT.
- Frontend lint zerado.
- Build/testes visuais/load smoke validados.
- Import cycles runtime zerados.
- Scorecard e auditoria arquitetural atualizados.
## 2026-07-29 - Feedback Governado E Aprendizado Supervisionado

- Adicionado `lumina.supervised-feedback/1.0` com contratos estritos, redacao e triagem deterministicas.
- Implementadas ownership de resposta, idempotencia, CAS, revisao humana e RBAC.
- Adicionadas migration v15 e 11 tabelas tenant-scoped para feedback, candidatos, exemplos, snapshots e exportacoes.
- Implementados controles de feedback no chat, historico proprio e fila administrativa por flags.
- Datasets publicados sao imutaveis, versionados e exportados somente offline; nao existe treinamento automatico.
- Producao permanece `LEGACY_ONLY` com todas as flags desligadas.
