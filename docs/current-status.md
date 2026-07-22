# Estado Atual Do Sistema

Data da atualizacao: 2026-07-22

Este documento resume o estado atual do LuminaAI apos as correcoes recentes de perguntas criticas, continuidade de conversa, ranking, descontos, login/sessao, preferencias de dashboard, auto-cura do catalogo, produtos/estoque, financeiro, suporte a anos isolados e suites de teste massivo.

## Resumo Executivo

O sistema permanece estruturado como uma plataforma Enterprise de BI com IA, backend FastAPI, frontend Next.js, Data Platform, catalogos, runtime de dashboards e governanca multi-tenant.

A certificacao completa de 2026-07-09 continua registrada como baseline historico. Em 2026-07-17, 2026-07-18, 2026-07-20, 2026-07-21 e 2026-07-22 foram feitas validacoes incrementais e suites de estresse focadas nas falhas reportadas pelo usuario e nas alteracoes recentes do codigo.

## Correcoes Recentes Validadas

- A IA consulta exclusivamente o PostgreSQL analitico sincronizado. Oracle nao faz parte do caminho de perguntas; e usado apenas pela sincronizacao e reconciliacao tecnica.
- Respostas exibem a ultima atualizacao real e validam matematicamente totais, filiais, transferencias e rankings antes da entrega.
- `ADMIN` recebe diagnostico tecnico completo por resposta. `CONSULTA` recebe apenas resposta, dashboard e controles de exploracao; trace, plano e telemetria sao removidos no backend.
- A acao `Ver documentos` detalha no PostgreSQL os pedidos/notas que formam a metrica, respeitando periodo, filial e categoria da conversa.
- O scheduler reinicia automaticamente em falha inesperada, participa do `/health/deep` e executa reconciliacao tecnica diaria depois da sincronizacao agendada.
- O frontend nao fabrica mais horarios, health scores, versoes ou desempenho para completar o Trust Center; ausencia de evidencia e mostrada como nao disponivel.
- Consultas deterministicas ampliadas para **Produtos mais vendidos**, **Estoque por produto** e **Financeiro / Titulos em aberto** com retorno de dados brutos populando `sample_rows` para a Tabela Detalhada com Colunas.
- Auto-cura semantica no `Canonicalizer` para entidades desconhecidas (`Produto`, `Financeiro`, `Venda`, `Vendedor`, `Cliente`, `Cidade`, `Estado`, `Categoria`).
- Auto-cura graciosa de filtros desconhecidos com descarte seguro em log em vez de erro `UNSUPPORTED`.
- Parser de periodo (`_month_range_from_text`) expandido para anos isolados de 4 digitos (`no ano de 2026`, `em 2026`, `2026`), retornando o intervalo `YYYY-01-01` a `YYYY-12-31`.
- Tolerancia a typos e erros de grafia no chat (`mais vendidoa`, `mais vendida`, `top produtos`).
- Perguntas criticas de vendas ganharam caminho deterministico no `NewQueryOrchestrator` quando ha periodo explicito ou periodo herdado da conversa.
- Perguntas com a mesma fonte/metrica mas saida diferente sao separadas por intencao: `maior/top` retorna uma linha; `ranking/lista/todos/por vendedor` retorna tabela ordenada.
- Consultas de faturamento, ticket medio, descontos, maior vendedor e maior cliente usam regras estaveis sobre `vw_vendas_lm`.
- O faturamento comercial padrao usa a regua operacional adotada para as perguntas criticas: todas as filiais por padrao, filial especifica quando solicitada, e `tp_ IN (2, 61)`.
- O modulo `sales_value_breakdown` preserva `filial_` como dimensao padrao e separa os demais movimentos em linhas/colunas: saida RB, devolucao, venda bonificada, transferencias, outras vendas, remessa/uso e consumo, outros movimentos, total bruto sem transferencias e total geral de movimentos para auditoria.
- A saida padrao de ranking e enxuta: uma linha por vendedor/cliente, colunas por filial, total no fim e apenas metricas essenciais; categorias operacionais extras so aparecem quando solicitadas.
- Perguntas de saida RB e devolucao tem intencoes proprias. RB usa `tp_ = 9`/`SAIDA RB`; devolucao usa descricao contendo `DEVOL` e retorna zero quando a view nao tiver linhas desse movimento.
- Perguntas de faturamento entendem base liquida/comercial, bruta ou ambas. Perguntas de lucro e vendas ainda nao faturadas retornam aviso de fonte indisponivel quando a `vw_vendas_lm` nao possui campos para calculo confiavel.
- Pedidos explicitos de grafico, pizza, linha ou tabela+grafico alteram `chart_type`/`visualizations`; o caminho deterministico nao força mais sempre `TABLE`.
- Os modos operacional, analitico e executivo afetam a resposta deterministica.
- O chat abre configuracao de resposta para perguntas analiticas ambiguas, permitindo escolher base do valor, formato do dashboard e instrucoes opcionais salvas como padrao local; a deteccao cobre tambem temas como produtos, estoque, pedidos, compras, fornecedores, financeiro, metas, filiais e regioes.
- As preferencias de dashboard agora tambem sao persistidas no backend por usuario/tenant via `GET/PUT /api/v1/dashboard-preferences/default`; `localStorage` permanece apenas como fallback.
- Respostas deterministicas de vendas trazem auditoria de calculo em `bi_intelligence.metric_definitions`, `bi_intelligence.calculation_steps` e `trust_center.metric_registry`.
- Criado `services/erp_reconciliation.py` e `scripts/run_erp_reconciliation.py` para bater relatorio por relatorio contra o ERP: faturamento 06/2026 e 07/2026, ranking vendedores, filial por filial, RB, devolucao, ticket medio, top clientes e filtros oficiais.
- Criado `services/financial_source_discovery.py` e `scripts/run_financial_source_discovery.py` para mapear fontes candidatas de lucro bruto/liquido e vendas ainda nao faturadas; perguntas desses temas agora incluem diagnostico de fonte em `bi_intelligence.financial_source_discovery` e `trust_center.financial_source_discovery`.
- Corrigida a conexao Oracle com pool assincrono, a reconciliacao passou a resolver automaticamente o owner `DONWMS` das views LM e a sync passou a ter carga full controlada e incremental com janela de sobreposicao por `dtemissao_`.
- Campo vazio do chat exibe atalhos de consulta para orientar usuarios leigos.
- Continuidade de conversa herda periodo, metrica e dimensao quando a pergunta usa referencias como `esse dado`, `esse ranking` ou `agora separa por vendedor`.
- Continuidade tambem entende termos curtos como `mesmo`/`mesma`, e o parser aceita `julho/2026`, `jul/2026` e perguntas leigas como `qnt vendeu rb vendedor jul/2026 tabela`.
- Rankings de clientes sem pedido de `todos`/`sem limite` retornam top 50 por padrao; `top N` e `todos os clientes` continuam respeitados.
- Ranking de vendedor desconsidera o cadastro tecnico `PADRAO`.
- Ranking/top cliente desconsidera `LAGES E LOPES LTDA` quando a pergunta pede cliente externo, pois esse nome representa a loja interna.
- Desconto total e desconto medio agora detectam automaticamente uma coluna real de desconto quando ela existir na `vw_vendas_lm` (`desconto_total`, `valor_desconto`, `vl_desconto`, `vldesconto`, `vldesc` ou `desconto`).
- No clone validado em 2026-07-18, a `vw_vendas_lm` nao possui coluna explicita de desconto; nesse caso o sistema mostra aviso de baixa confianca e informa que a derivacao `qtde_ * p_unit_ - ptotal_` retornou zero, sem afirmar que o ERP nao tenha descontos.
- Continuidade de conversa envia `session_id`, historico recente e `parent_id`, permitindo herdar periodo em perguntas subsequentes.
- Clique na logo do sistema chama `resetConversation` e limpa a conversa atual.
- Textos do frontend e payloads vindos da API passam por reparo defensivo de encoding antes de renderizar.
- Labels tecnicos como `observacao`, `ticket_medio` e `valor_formatado` sao humanizados para exibicao.
- `getApiBase()` preserva o mesmo host loopback usado no navegador (`localhost` ou `127.0.0.1`) para evitar perda de cookie de sessao.
- `GET /health/deep` diagnostica API, PostgreSQL e status de IA/invocacao; o frontend consulta esse endpoint para enriquecer mensagens em falhas de conexao/servidor.

Decisao arquitetural relacionada: [ADR 0005 - Guardrail deterministico para perguntas criticas de vendas](adrs/0005-deterministic-critical-sales-queries.md).

## Perguntas Prioritarias Cobertas

As seguintes familias de perguntas devem ser tratadas como superficie critica de regressao:

- Faturamento do mes.
- Faturamento do mes anterior.
- Venda por vendedor.
- Ranking com todos os vendedores.
- Qual vendedor teve maior venda.
- Qual vendedor com maior desconto.
- Qual foi nosso desconto.
- Total de desconto.
- Desconto medio.
- Ticket medio.
- Ranking/top clientes, excluindo a loja interna quando aplicavel.
- Perguntas de continuidade na mesma conversa, herdando periodo quando a pergunta seguinte for curta ou ambigua.

## Validacao Incremental Executada Em 2026-07-17, 2026-07-18, 2026-07-20, 2026-07-21 E 2026-07-22

| Validacao | Resultado |
| --- | --- |
| Mineracao e estresse massivo em 2026-07-22 | OK; 164 cenarios de perguntas analiticas e interacoes multi-turn executados sem falhas (0 falhas). Cobriu produtos mais vendidos, estoque, financeiro, anos isolados de 4 digitos (`no ano de 2026`), auto-cura do catalogo e descarte gracioso de filtros. |
| Governanca, rastreabilidade e perfis em 2026-07-21 | OK; 49 testes focados, `py_compile`, build Next.js, TypeScript e lint dos arquivos alterados. Consulta real retornou fonte PostgreSQL, 4 checks aprovados e 500 documentos detalhados. |
| `python -m py_compile` em orquestrador, transformer e modulo `sales_value_breakdown` | OK em 2026-07-18 |
| `python -m py_compile` nos arquivos alterados em 2026-07-20 | OK; orquestrador, metric registry, preferencias, main, redteam, reconciliacao ERP e descoberta de fontes financeiras |
| `pytest tests/test_financial_source_discovery.py tests/test_erp_reconciliation.py tests/test_metric_registry.py tests/test_sales_value_breakdown.py tests/test_core_summary_output_intents.py -q` | OK; 46 testes em 2026-07-20 |
| `scripts/run_financial_source_discovery.py --json-report reports/financial_source_discovery_2026-07-20.json` | OK; 10 fontes candidatas inspecionadas. Resultado: lucro bruto, lucro liquido e vendas nao faturadas continuam `partial` e sem mapeamento ativo homologado. |
| `scripts/run_lm_view_resync.py --view VW_VENDAS_LM --full` seguido de `scripts/run_lm_view_resync.py --view VW_VENDAS_LM` | OK; full sync com 585.224 linhas e incremental de sobreposicao com 855 linhas recentes em 2026-07-20. |
| `scripts/run_erp_reconciliation.py --period 2026-06 --period 2026-07 --json-report reports/erp_reconciliation_2026-07-20.json --require-oracle --fail-on-mismatch` | OK; Oracle real acessivel, owner `DONWMS` resolvido, 06/2026 e 07/2026 com `overall_status=ok` e 0 checks divergentes. |
| Ajuste RB, devolucao e transferencias em 2026-07-20 | OK; `pytest tests/test_sales_value_breakdown.py tests/test_core_summary_output_intents.py tests/test_metric_registry.py tests/test_erp_reconciliation.py -q` com 44 testes. RB e devolucao ficam separados, pedidos RB nao sao formatados como moeda e `total_bruto` exclui transferencias. |
| Reconciliacao apos separar RB, devolucao e transferencias | 06/2026 OK contra Oracle real. 07/2026 e mes corrente vivo; apos sync incremental de 1.012 e depois 1.019 linhas recentes, o Oracle recebeu novas vendas durante a auditoria e ficou com delta movel de R$ 1.650,00. Para fechamento exato, usar periodo fechado ou sincronizar imediatamente antes da leitura final. |
| `npm run build` no frontend | OK |
| Conversa sequencial no mesmo `session_id` | OK; 12 turnos, 0 falhas em 2026-07-20. Cobriu faturamento, RB, ranking por vendedor, mudanca para grafico, desconto, ticket, filial, lucro indisponivel, vendas nao faturadas indisponiveis e ranking de clientes. |
| Bateria automatizada real do pipeline deterministico | OK; 461 perguntas, 0 falhas em 2026-07-20. Cobriu tabela, grafico, tabela+grafico, pizza, filiais, modos, RB, desconto, cliente interno, top 50 clientes, unsupported, acentos quebrados, abreviacoes (`jul/2026`), prompt adversarial e continuidade. Relatorio JSON em `backend/reports/core_sales_redteam_2026-07-20.json`. |
| Auditoria numerica direta por metrica/filial | OK; 06/2026 e 07/2026 com soma por filial batendo em 2 casas para faturamento comercial, total bruto sem transferencias, RB, devolucao e desconto. Resumos em `backend/reports/final_metric_audit_summary_2026-07-20.json`. |
| Geracao de `docs/api-reference.md` e `docs/source-inventory.md` com Python do backend | OK |
| E2E Playwright abrindo `http://127.0.0.1:3000/login` | OK |
| Login, hidratacao de sessao e redirecionamento para `/dashboard` via `127.0.0.1` | OK |
| Pergunta real `Faturamento e ticket medio em 06/2026` | OK |
| Diferenca entre `Qual vendedor que mais vendeu no mes 07/2026` e `Ranking com todos os vendedores, no mes 07/2026` no mesmo chat | OK; top retornou o lider em uma linha pivotada e ranking retornou 25 vendedores/25 linhas, com colunas por filial e total no fim |
| Faturamento total e por filial em 06/2026 e 07/2026 | OK; total geral usa todas as filiais por padrao, a tabela inclui uma linha por filial e uma linha final `Total geral` |
| Faturamento de filial especifica em 07/2026 | OK; `Faturamento da filial 1 no mes 07/2026` retornou somente a filial 1 |
| Ticket medio e desconto em 06/2026 | OK; ticket retorna total geral e linhas por filial. Desconto retorna linhas por filial com aviso de fonte derivada/baixa confianca porque a view `vw_vendas_lm` nao possui coluna explicita de desconto no clone atual. |
| Auditoria de fonte de desconto em 2026-07-18 | A `vw_vendas_lm` local tem 586.552 linhas e nenhuma coluna explicita de desconto. A diferenca positiva `qtde_ * p_unit_ - ptotal_` foi zero em todos os registros analisados; o acesso ao Oracle real `10.253.7.2:1521` falhou por timeout de rede/listener nesta maquina. |
| Auditoria ERP x clone em 2026-07-20 | OK contra Oracle real para 06/2026 fechado. 07/2026 pode divergir enquanto o ERP recebe novas vendas no dia; o relatorio mais recente registra esse delta movel em `backend/reports/erp_reconciliation_2026-07-20.json`. |
| Fonte para lucro e vendas nao faturadas em 2026-07-20 | Nenhuma fonte pronta/homologada foi encontrada. `vw_vendas_lm` e `vw_financeiro_lm` sao apenas parciais: faltam custo/CMV, impostos/despesas/formula de margem e status operacional de pedido/carteira pendente. |
| Decomposicao RCA 6/Antonio no clone local | OK; valor que antes aparecia misturado foi separado em faturamento comercial, saida RB, devolucao, bonificada, transferencias, outras categorias e filial. A diferenca residual de `R$ 1.037,77` contra o print do ERP nao bateu com excluir um tipo, CFOP ou forma de pagamento inteira e nao foi transformada em regra invisivel. |
| Renderizacao com `Resumo do período`, `ticket médio`, `Painel Analítico`, `Confiança` e `Observação` sem mojibake | OK |
| Backend temporario usado no teste | Encerrado apos a validacao |

## Observacoes De Escopo

- Mes corrente e uma janela viva: se o ERP receber vendas durante a reconciliacao, o clone pode ficar alguns pedidos atras mesmo apos sync. Para auditoria final de numero exato, prefira mes fechado, dia fechado ou sync imediatamente antes da consulta final.
- Transferencias (`tp_` 3, 31 e 96, ou descricao de transferencia) aparecem separadas, mas nao entram em faturamento, lucro ou total bruto sem transferencias.
- A bateria completa de regressao registrada em 2026-07-09 nao foi reexecutada integralmente nesta rodada de documentacao.
- Docker, carga produtiva, backup/restore real e `EXPLAIN ANALYZE` com massa real continuam dependentes do ambiente final.
- Arquivos de backup, logs e relatorios historicos podem manter conteudo antigo por rastreabilidade; documentos oficiais apontam para este estado atual quando houver divergencia.
