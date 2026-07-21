# Relatorio Final - Hardening De Perguntas, Metricas E Auditoria

Data: 2026-07-20

## Escopo

Esta rodada implementou as melhorias aprovadas para o chat analitico do LuminaAI, com foco em:

- perguntas criticas de faturamento, vendedor, cliente, RB, devolucao, desconto e ticket medio;
- continuidade na mesma conversa;
- escolhas de dashboard e modo de resposta;
- auditoria de formulas/metrica por resposta;
- health/recovery para quedas de API/DB;
- documentacao e bateria oficial de regressao.

## Implementacoes

- Dicionario oficial de metricas em `backend/services/metric_registry.py`.
- Auditoria de calculo exposta em `bi_intelligence.metric_definitions`, `bi_intelligence.calculation_steps` e `trust_center.metric_registry`.
- Persistencia de preferencias de dashboard por usuario/tenant em `dashboard_preferences`.
- Endpoints `GET/PUT /api/v1/dashboard-preferences/default`.
- Endpoint `GET /health/deep` com diagnostico de API, PostgreSQL e status de IA/invocacao.
- Frontend carregando/salvando preferencias do popup no backend, com fallback em `localStorage`.
- Parser de periodo aceitando `julho/2026`, `jul/2026` e continuidade com `mesmo`/`mesma`.
- Reconhecimento de pergunta leiga `qnt vendeu rb vendedor jul/2026 tabela` como ranking de RB por vendedor.
- Script oficial `backend/scripts/run_core_sales_redteam.py`.

## Validacoes Executadas

| Validacao | Resultado |
| --- | --- |
| `python -m py_compile` nos arquivos alterados | OK |
| `pytest tests/test_core_summary_output_intents.py tests/test_sales_value_breakdown.py tests/test_metric_registry.py tests/test_core_sales_redteam_script.py -q` | OK, 38 passed |
| `npm run build` no frontend | OK |
| `scripts/run_core_sales_redteam.py` | OK, 461/461 perguntas, 0 falhas |
| Auditoria numerica direta por metrica/filial | OK para 06/2026 e 07/2026 |

Arquivos de evidencia:

- `backend/reports/core_sales_redteam_2026-07-20.json`
- `backend/reports/final_metric_audit_2026-07-20.json`
- `backend/reports/final_metric_audit_summary_2026-07-20.json`

## Auditoria Numerica - 06/2026

| Metrica | Valor |
| --- | ---: |
| Faturamento comercial | R$ 3.132.057,02 |
| Total bruto sem transferencias | R$ 3.555.591,16 |
| Total geral de movimentos | R$ 4.327.746,77 |
| Saida RB | R$ 384.108,29 |
| Devolucao | R$ 0,00 |
| Venda bonificada | R$ 6.054,72 |
| Transferencias | R$ 772.155,61 |
| Desconto comercial | R$ 0,00 |
| Pedidos comerciais | 7.366 |
| Ticket medio comercial | R$ 425,20 |

Conferencia por filial em 06/2026: soma por filial bateu em 2 casas para faturamento comercial, total bruto sem transferencias, RB, devolucao e desconto.

| Filial | Faturamento comercial | Total geral de movimentos | RB |
| --- | ---: | ---: | ---: |
| 1 | R$ 1.591.551,63 | R$ 2.208.599,61 | R$ 91.020,29 |
| 2 | R$ 525.299,71 | R$ 566.466,71 | R$ 15.305,87 |
| 3 | R$ 385.513,18 | R$ 499.956,88 | R$ 13.597,50 |
| 4 | R$ 220.088,54 | R$ 261.754,76 | R$ 26.987,15 |
| 5 | R$ 409.603,96 | R$ 790.968,81 | R$ 237.197,48 |

Principais rankings em 06/2026:

- Maior venda por vendedor: WANESSA FERREIRA DA SILVA, R$ 516.373,63.
- Maior RB por vendedor: ANA PAULA GONCALVES FERNANDES, R$ 103.202,45.
- Maior cliente externo: CONSUMIDOR FINAL NFCE, R$ 270.801,71.

## Auditoria Numerica - 07/2026

| Metrica | Valor |
| --- | ---: |
| Faturamento comercial | R$ 1.923.862,12 |
| Total bruto sem transferencias | R$ 2.126.824,34 |
| Total geral de movimentos | R$ 3.358.591,59 |
| Saida RB | R$ 177.150,97 |
| Devolucao | R$ 0,00 |
| Venda bonificada | R$ 1.992,62 |
| Transferencias | R$ 1.231.767,25 |
| Desconto comercial | R$ 0,00 |
| Pedidos comerciais | 4.521 |
| Ticket medio comercial | R$ 425,54 |

Conferencia por filial em 07/2026: soma por filial bate em 2 casas no clone sincronizado; por ser mes corrente, o Oracle pode receber novas vendas durante a reconciliacao.

| Filial | Faturamento comercial | Total geral de movimentos | RB |
| --- | ---: | ---: | ---: |
| 1 | R$ 820.893,29 | R$ 1.882.749,51 | R$ 47.424,39 |
| 2 | R$ 346.124,91 | R$ 413.095,94 | R$ 30.013,13 |
| 3 | R$ 248.412,44 | R$ 275.108,43 | R$ 3.958,72 |
| 4 | R$ 90.291,29 | R$ 114.840,86 | R$ 8.570,49 |
| 5 | R$ 418.140,19 | R$ 672.796,85 | R$ 87.184,24 |

Principais rankings em 07/2026:

- Maior venda por vendedor: MARCOS EMANUEL GONCALVES SOUZA, R$ 267.836,36.
- Maior RB por vendedor: ANA PAULA GONCALVES FERNANDES, R$ 28.950,91.
- Maior cliente externo: CONSUMIDOR FINAL NFCE, R$ 190.956,08.

## Desconto

O clone atual da `vw_vendas_lm` nao possui coluna explicita de desconto entre os candidatos monitorados: `desconto_total`, `valor_desconto`, `vl_desconto`, `vldesconto`, `vldesc` ou `desconto`.

Por isso, o desconto permanece com fonte `derivado_sem_coluna_explicita` e confianca baixa. A formula defensiva `GREATEST(qtde_ * p_unit_ - ptotal_, 0)` retornou R$ 0,00 nos periodos auditados, mas o sistema agora informa isso como limitacao de fonte, nao como prova de ausencia de desconto no ERP.

## Resultado Critico

- Ranking/top agora nao colapsam a mesma analise em saidas erradas: ranking retorna lista; top/maior retorna uma linha.
- Ranking de vendedores sai pivotado: uma linha por vendedor, colunas por filial e total no fim.
- Faturamento total traz linhas por filial e `Total geral`.
- RB, devolucao, bonificada, transferencias e demais movimentos ficam separados quando o usuario pede detalhe; transferencias nao entram em faturamento, lucro ou total bruto.
- Perguntas em grafico, pizza ou tabela+grafico retornam visualizacao correspondente.
- Continuidade curta na mesma conversa foi validada na bateria (`e quantas vendas foram RB?`, `agora separa esse dado por vendedor`, `me mostra esse ranking em grafico`, `quero o mesmo em tabela e grafico`).

## Limitacoes Restantes

- Lucro bruto/liquido e vendas ainda nao faturadas continuam marcados como indisponiveis porque a `vw_vendas_lm` nao possui custo, impostos, despesas, margem ou status de pedido pendente.
- Desconto real depende de a view trazer coluna explicita ou de uma view especifica de descontos do ERP.
- Os dados foram auditados contra o clone local disponivel neste ambiente; divergencias contra relatorios externos do ERP devem ser tratadas comparando a query/filtro exato do relatorio ERP.
