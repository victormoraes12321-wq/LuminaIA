# Technical Debt Register

| ID | Divida | Risco | Mitigacao Atual | Saida |
|---|---|---|---|---|
| TD-001 | Adapter de preferencia de dashboard legado | Duplicacao temporaria de apresentacao | Importa somente campos seguros e marca origem `LEGACY_IMPORT` | Remover depois do rollout integral e janela de rollback. |
| TD-002 | Processamento operacional de pedidos de exclusao | Pedido fica pendente ate job governado | Perfil `DELETION_PENDING` deixa de ser aplicado imediatamente | Implementar worker auditado com SLA e politica legal no ciclo operacional. |
| TD-003 | Politicas administrativas de perfil | Contrato existe, mas rollout inicia desligado | Precedencia e fail-closed centralizados | Definir UI e workflow de politica em etapa futura, sem acesso ao perfil privado. |
| TD-004 | Importacao legada em lote | Risco de origem ou referencia invalida | Dry-run obrigatorio, confirmacao separada e flag desligada | Criar operacao assistida por tenant apos piloto. |
| TD-005 | Execucao operacional de pedidos de exclusao de feedback | Pedido persiste pendente | Nova curadoria ignora itens retirados; auditoria e retencao sao deterministicas | Implementar worker juridicamente aprovado sem mutar snapshots publicados. |
| TD-006 | Benchmark PostgreSQL de feedback com massa operacional anonimizada | Certificacao usa massa sintetica e workloads estruturais de 10.000 itens | Export usa cursor/spool; filas usam keyset e indices tenant-scoped | Executar EXPLAIN ANALYZE em clone isolado depois da homologacao de volume e politica de dados. |
| TD-006 | Promocao para dataset global | Dados reais nao podem perder tenant por conveniencia | Runtime cria somente dataset tenant-scoped | Projetar fluxo separado para fixtures sinteticas ou anonimizacao comprovada. |
| TD-007 | Runner de evals supervisionados | Contratos existem, mas execucao automatica ficaria fora do escopo | Exportacao offline e allowlist documentadas | Implementar runner isolado no Prompt futuro, sem codigo arbitrario. |

Nenhuma divida autoriza persistir SQL, dataset, bind, pergunta, resposta,
credencial ou dado empresarial no perfil.

## Semantic Retrieval V2

| ID | Simbolo Ou Arquivo | Motivo | Substituto Planejado | Consumidores | Flag | Condicao Objetiva De Saida | Risco | Etapa | Status |
|---|---|---|---|---|---|---|---|---|---|
| TD-SR-001 | `SemanticIndexLifecycleService.build` incremental | Provider inicial recompila snapshot completo | Delta por watermark com tombstones tipados | Admin build | `SEMANTIC_INCREMENTAL_BUILD_ENABLED` | Testes de delta, delete, replay e equivalencia FULL/INCREMENTAL | Snapshot incompleto | Fase operacional | BLOCKED |
| TD-SR-002 | Jobs de build/evaluation sincronos | Nao ha worker governado nesta fase | Job queue tenant-scoped com lease e resume | APIs admin | admin inspector | 10k docs dentro do SLO e worker certificado | Timeout de request | Prompt futuro | ACTIVE |
| TD-SR-003 | Entity instance provider | Dados pessoais/restritos exigem politica adicional | Provider analitico curado com minimizacao | Retrieval | `SEMANTIC_ENTITY_INSTANCE_INDEXING_ENABLED` | DPIA, permission tests, retention e corpus aprovados | Exposicao de PII | Fase futura | BLOCKED |
| TD-SR-004 | Fonte de feedback aprovado | Corpus existe, mas nao altera runtime automaticamente | Provider somente de exemplos aprovados e snapshot publicado | Evaluation/index build | `SEMANTIC_APPROVED_FEEDBACK_CORPUS_ENABLED` | Curadoria, checksum e rollback certificados | Poisoning | Fase futura | BLOCKED |
| TD-SR-005 | Feature hash local | Recall semantico limitado | Provider opcional certificado sem vazamento | Retrieval | `SEMANTIC_VECTOR_CHANNEL_ENABLED` | Benchmark sintetico, sem rede e compatibilidade sem extensao | Drift de ranking | Fase futura | ACTIVE |
| TD-SR-006 | Source stale sob demanda | Deteccao ocorre na inspecao/admin | Job governado de staleness e alerta | Admin/observabilidade | admin inspector | Job idempotente, sem mutar published, com SLO | Indice desatualizado entre verificacoes | Operacao | ACTIVE |
| TD-SR-007 | Relation expansion conservadora | Relacoes sao persistidas, mas nao expandem candidatos automaticamente | Expansao limitada e relevance-aware | Retrieval | futura flag especifica | Goldens de relacao sem queda de precision | Falso positivo | Fase futura | ACTIVE |
| TD-SR-008 | Producao `LEGACY_ONLY` | Rollout ainda nao aprovado | SHADOW, HYBRID_READ e V2_AUTHORITATIVE por tenant | Orchestrator e frontend | `SEMANTIC_RETRIEVAL_MODE` | Migration, indice, eval, SLO, rollback e auditoria aprovados | Regressao funcional | Rollout | ACTIVE |

As dividas acima nao permitem persistir pergunta, resposta, dataset, SQL,
bind, credencial ou vetor bruto em telemetria.
