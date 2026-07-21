# Relatorio 2026-07-20 - Reconciliacao ERP E Fontes Financeiras

## Escopo

- Bater relatorios criticos do clone contra o ERP Oracle: faturamento 06/2026 e 07/2026, ranking vendedores, filial por filial, RB, devolucao, ticket medio e top clientes.
- Registrar filtros oficiais usados nas perguntas criticas: periodo, tipo de venda, filial, RB, devolucao, bonificados, transferencias, exclusoes de ranking, CFOP e status/cancelamento quando disponiveis.
- Mapear fonte para lucro bruto/liquido e vendas ainda nao faturadas sem inventar valores.

## Implementacao

- `backend/services/erp_reconciliation.py`
- `backend/scripts/run_erp_reconciliation.py`
- `backend/services/financial_source_discovery.py`
- `backend/scripts/run_financial_source_discovery.py`
- `backend/scripts/run_lm_view_resync.py`
- Integracao no chat para anexar `bi_intelligence.financial_source_discovery` e `trust_center.financial_source_discovery` em perguntas de lucro e vendas nao faturadas.
- Reconciliacao Oracle resolve automaticamente as views LM no owner `DONWMS`.

## Resultados Do Clone

| Periodo | Faturamento Comercial | Total Bruto Sem Transferencias | Total Geral De Movimentos | RB | Devolucao | Pedidos RB | Ticket Medio | Top Vendedor | Top Cliente |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 06/2026 | R$ 3.132.057,02 | R$ 3.555.591,16 | R$ 4.327.746,77 | R$ 384.108,29 | R$ 0,00 | 650 | R$ 425,20 | WANESSA FERREIRA DA SILVA - R$ 516.373,63 | CONSUMIDOR FINAL NFCE - R$ 270.801,71 |
| 07/2026 | R$ 1.923.862,12 | R$ 2.126.824,34 | R$ 3.358.591,59 | R$ 177.150,97 | R$ 0,00 | 429 | R$ 425,54 | MARCOS EMANUEL GONCALVES SOUZA - R$ 267.836,36 | CONSUMIDOR FINAL NFCE - R$ 190.956,08 |

## Status ERP

O relatorio `backend/reports/erp_reconciliation_2026-07-20.json` foi gerado contra o Oracle real apos a maquina voltar a alcancar o banco.

Fontes Oracle resolvidas:

- `DONWMS.VW_VENDAS_LM`
- `DONWMS.VW_VENDEDOR_CAD_LM`
- `DONWMS.VW_CLIENTES_CAD_LM`

Durante a primeira batida, julho divergiu porque o clone estava defasado no dia 20/07/2026. Foi executado full sync controlado de `VW_VENDAS_LM` e depois incremental com janela de sobreposicao por `dtemissao_`.

Adendo de regra atual: RB e devolucao sao metricas separadas. Transferencias continuam visiveis, mas nao entram em faturamento, lucro ou `total_bruto`; o campo `total_movimentos_view` existe apenas para auditoria operacional completa.

Comando final validado:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\run_erp_reconciliation.py --period 2026-06 --period 2026-07 --json-report reports\erp_reconciliation_2026-07-20.json --require-oracle --fail-on-mismatch
```

Resultado atual: 06/2026 fechado com 0 checks divergentes. 07/2026 e mes corrente vivo; apos sync incremental de 1.012 e depois 1.019 linhas recentes, o Oracle recebeu novas vendas durante a auditoria e ficou com delta movel de R$ 1.650,00 no faturamento comercial da filial 1.

## Fonte De Lucro E Vendas Nao Faturadas

O relatorio `backend/reports/financial_source_discovery_2026-07-20.json` inspecionou 10 fontes candidatas.

Resultado:

- Lucro bruto: `partial`, sem mapeamento ativo homologado.
- Lucro liquido: `partial`, sem mapeamento ativo homologado.
- Vendas ainda nao faturadas: `partial`, sem mapeamento ativo homologado.

Principais lacunas:

- `vw_vendas_lm` tem faturamento, pedido, nota, filial, vendedor, cliente, CFOP e data, mas nao tem custo/CMV, impostos, despesas, margem ou lucro.
- `vw_vendas_lm` contem pedidos/notas ja emitidos; falta status operacional de pedido pendente/carteira para separar vendas nao faturadas.
- `vw_financeiro_lm` possui status de pagamento, valor de parcela e vencimento, mas status financeiro nao substitui status operacional de faturamento do pedido.

Conclusao: o sistema deve continuar bloqueando calculo de lucro e vendas nao faturadas ate uma view/tabela homologada ser adicionada ao clone ou exposta pelo ERP.

## Validacoes

- `python -m py_compile` nos novos modulos/scripts e integracoes: OK.
- `python -m py_compile services/data_platform/sync_engine.py scripts/run_lm_view_resync.py`: OK.
- `pytest tests/test_financial_source_discovery.py tests/test_erp_reconciliation.py tests/test_metric_registry.py tests/test_sales_value_breakdown.py tests/test_core_summary_output_intents.py -q`: 46 passed.
- `run_erp_reconciliation.py --require-oracle --fail-on-mismatch`: OK para 06/2026 fechado; 07/2026 requer janela fechada ou sync imediatamente anterior para congelar o numero final enquanto o ERP esta em uso.
