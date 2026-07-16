# LuminaAI - Relatorio de Limpeza para Producao

Data/Hora: 2026-07-13T07:33:45
Backup: `C:\Users\wccto11ti1\Desktop\Sistema IA Empresa\backend\backups\production_cleanup_20260713_072639`
Relatorio JSON: `C:\Users\wccto11ti1\Desktop\Sistema IA Empresa\backend\reports\production_cleanup_20260713_072639.json`
Total final de linhas removidas: **92149**

## Escopo Executado
- Somente dados foram removidos ou sanitizados.
- Nenhuma operacao de schema foi executada: sem DROP, TRUNCATE, ALTER, CREATE INDEX, DROP VIEW, procedure ou trigger.
- Estruturas de tabelas, indices, views, procedures e triggers foram preservadas.
- Backup completo das tabelas afetadas/protegidas foi criado antes da limpeza.

## Tabelas Afetadas
- `analytical_packages`: 599 -> 0
- `blueprint_repository`: 144 -> 0
- `dashboard_instances`: 95 -> 0
- `dashboard_studio_versions`: 350 -> 0
- `dashboard_templates`: 127 -> 0
- `data_platform_history`: 1241 -> 0
- `datasets`: 1165 -> 0
- `metadata_catalog`: 1730 -> 0
- `metadata_catalog_versions`: 1139 -> 0
- `mock_oracle_vw_estoque_produtos`: 336 -> 0
- `mock_oracle_vw_faturamento_mensal`: 13 -> 0
- `mock_oracle_vw_historico_clientes`: 15 -> 0
- `mock_oracle_vw_kpi_executivo`: 4 -> 0
- `mock_oracle_vw_lojas_regioes`: 3 -> 0
- `mock_oracle_vw_metas_vendedores`: 130 -> 0
- `mock_oracle_vw_performance_vendedores`: 10 -> 0
- `mock_oracle_vw_ranking_produtos`: 336 -> 0
- `mock_oracle_vw_vendas_mensais`: 40170 -> 0
- `package_dashboard_instances`: 604 -> 0
- `search_history`: 886 -> 0
- `semantic_memory`: 61 -> 0
- `svr_audit_logs`: 24 -> 0
- `svr_compatibility_matrix`: 36 -> 12
- `svr_concepts`: 29 -> 12
- `svr_versions`: 36 -> 12
- `sync_queue`: 193 -> 0
- `tenants`: 2 -> 1
- `users`: 2 -> 1
- `view_catalog`: 20 -> 14
- `vw_clientes_historico`: 35 -> 0
- `vw_detalhe_pedidos`: 191 -> 0
- `vw_estoque_status`: 35 -> 0
- `vw_evolucao_clientes`: 191 -> 0
- `vw_fat_prod_1781608977`: 191 -> 0
- `vw_fat_prod_1781612969`: 191 -> 0
- `vw_fat_prod_1781613201`: 191 -> 0
- `vw_faturamento_mensal`: 35 -> 0
- `vw_faturamento_produtos`: 191 -> 0
- `vw_integrity_test_err`: 1 -> 0
- `vw_integrity_test_ok`: 1 -> 0
- `vw_isolation_test`: 1 -> 0
- `vw_kpi_executivo`: 35 -> 0
- `vw_kpi_executivo_vendas`: 190 -> 0
- `vw_lojas_regioes`: 3 -> 0
- `vw_market_share_produtos`: 191 -> 0
- `vw_metas_atingimento`: 191 -> 0
- `vw_performance_vendedores`: 35 -> 0
- `vw_produtos_mais_vendidos`: 35 -> 0
- `vw_ranking_produtos`: 336 -> 0
- `vw_test_dataplatform`: 191 -> 0
- `vw_test_extended_dataplatform`: 1 -> 0
- `vw_teste_integracao`: 1 -> 0
- `vw_vendas_contexto_geral`: 40205 -> 0
- `vw_vendas_mensais`: 35 -> 0

## Remocoes por Entidade/Operacao
- `analytical_packages`: 599
- `blueprint_repository`: 144
- `business_governance_logs`: 0
- `dashboard_instances`: 95
- `dashboard_studio_versions`: 350
- `dashboard_templates`: 127
- `data_platform_history`: 1241
- `datasets`: 1165
- `favorites`: 0
- `metadata_catalog`: 1730
- `metadata_catalog_versions`: 1139
- `mock_oracle_vw_estoque_produtos`: 336
- `mock_oracle_vw_faturamento_mensal`: 13
- `mock_oracle_vw_historico_clientes`: 15
- `mock_oracle_vw_kpi_executivo`: 4
- `mock_oracle_vw_lojas_regioes`: 3
- `mock_oracle_vw_metas_vendedores`: 130
- `mock_oracle_vw_performance_vendedores`: 10
- `mock_oracle_vw_ranking_produtos`: 336
- `mock_oracle_vw_vendas_mensais`: 40170
- `package_dashboard_instances`: 604
- `search_history`: 886
- `semantic_memory`: 61
- `svr_audit_logs_test_temp_only`: 24
- `svr_compatibility_matrix_test_temp_only`: 24
- `svr_concepts_test_temp_only`: 17
- `svr_versions_test_temp_only`: 24
- `sync_queue`: 193
- `tenants_test_only`: 1
- `users_demo_test_only`: 1
- `view_catalog_test_entries_only`: 4
- `vw_clientes_historico`: 35
- `vw_detalhe_pedidos`: 191
- `vw_estoque_status`: 35
- `vw_evolucao_clientes`: 191
- `vw_fat_prod_1781608977`: 191
- `vw_fat_prod_1781612969`: 191
- `vw_fat_prod_1781613201`: 191
- `vw_faturamento_mensal`: 35
- `vw_faturamento_produtos`: 191
- `vw_integrity_test_err`: 1
- `vw_integrity_test_ok`: 1
- `vw_isolation_test`: 1
- `vw_kpi_executivo`: 35
- `vw_kpi_executivo_vendas`: 190
- `vw_lojas_regioes`: 3
- `vw_market_share_produtos`: 191
- `vw_metas_atingimento`: 191
- `vw_performance_vendedores`: 35
- `vw_produtos_mais_vendidos`: 35
- `vw_ranking_produtos`: 336
- `vw_test_dataplatform`: 191
- `vw_test_extended_dataplatform`: 1
- `vw_teste_integracao`: 1
- `vw_vendas_contexto_geral`: 40205
- `vw_vendas_mensais`: 35
- `tenants_sanitized`: 1

## Dados Preservados
- `tenants`: 1 registro(s) preservado(s)
- `users`: 1 registro(s) preservado(s)
- `view_catalog`: 14 registro(s) preservado(s)
- `semantic_catalog`: 5 registro(s) preservado(s)
- `svr_concepts`: 12 registro(s) preservado(s)
- `svr_versions`: 12 registro(s) preservado(s)
- `svr_compatibility_matrix`: 12 registro(s) preservado(s)
- `svr_audit_logs`: 0 registro(s) preservado(s)
- `business_concepts`: 0 registro(s) preservado(s)
- `business_formulas`: 0 registro(s) preservado(s)
- `business_kpis`: 0 registro(s) preservado(s)
- `business_relationships`: 0 registro(s) preservado(s)

## Sanitizacao do Tenant Operacional
- Tenant principal preservado para nao bloquear autenticacao/setup inicial.
- Nome/logo demo removidos e substituidos por identificacao neutra.
- Chave IA fake/teste removida do `ia_config`; uso volta a depender da credencial global/real configurada no ambiente.
- Conexoes Oracle/clone criptografadas de desenvolvimento foram zeradas.
- `sync_config` foi reiniciado sem historico de sync demo.

## Integridade
- Chaves estrangeiras com orfaos: 0
- Auditoria residual de termos demo/test/mock/fake: sem achado real; unico falso positivo foi alias legitimo `quanto vendemos` contendo a sequencia `demo` dentro de `vendemos`.
- Banco consistente apos limpeza e ajuste residual.

## Validacao Operacional
- Backend `/health`: OK apos limpeza e sanitizacao.
- Scheduler: inicializacao validada no startup do backend.
- Semantic Layer: 5 conceitos carregados em memoria sem gravacao no banco.
- Frontend lint: OK (`npm run lint`).
- IA smoke test: OK, modelo `gpt-4o-mini-2024-07-18`, 25 tokens totais, sem gravacao em banco.

## Observacoes de Producao
- O ambiente ainda esta com `ENVIRONMENT=development` no `.env`; isto nao foi alterado porque variaveis de ambiente estavam fora do escopo permitido.
- As tabelas analiticas e mock_oracle foram esvaziadas, mas mantidas para preservar estrutura/compatibilidade ate a proxima sincronizacao real.
- Catalogos estruturais preservados devem ser revisados com dados reais da empresa antes da operacao final.
