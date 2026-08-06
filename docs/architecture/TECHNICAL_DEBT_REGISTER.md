# Technical Debt Register

## Reconciliação Prompt 21 — 2026-08-05

As linhas históricas abaixo permanecem intactas. Para o estado atual, esta
reconciliação prevalece sobre itens que ainda descrevem o frontend como ausente.

| ID | Estado após Prompt 21 | Risco/limitação remanescente | Status |
|---|---|---|---|
| TD-DASH-UI-001 | Renderer, editor manual e side chat implementados | Coexistência com renderer/página legados até rollout formal | ACTIVE |
| TD-DASH-UI-002 | `LUMINA-GAP-DASH-001` resolvido com teste regular | Nenhum xfail/XPASS remanescente | RESOLVED |
| TD-DASH-UI-003 | IA de criação e semantic edit por chat ausentes | Dependem do Prompt 22; não autorizados aqui | PLANNED |
| TD-DASH-UI-004 | Publish/rollback por chat proibidos | Permanecem decisões humanas fora do chat | BY_DESIGN |
| TD-DASH-UI-005 | Rollout produtivo bloqueado | Backup, migration V22, allowlist, SLO e aprovação formal | BLOCKED |
| TD-DASH-UI-006 | Load test e benchmark visual não executados | Exigem ambiente dedicado e baseline aprovada | PLANNED |
| TD-DASH-UI-007 | Colaboração em tempo real ausente | CRUD governado existe; coedição/live presence é futura | FUTURE |
| TD-DASH-UI-008 | Offline mode ausente | Não armazenar dataset ou lista autoritativa no navegador | FUTURE |
| TD-DASH-UI-009 | Export de dashboard futuro | CSV existente não foi ampliado sem contrato | FUTURE |
| TD-DASH-UI-010 | Navegação cross-dashboard futura | Drilldown atual permanece declarado e local | FUTURE |
| TD-DASH-UI-011 | Editor mobile usa controles numéricos/teclado | Drag-and-drop touch avançado não foi introduzido | ACTIVE |
| TD-DASH-UI-012 | Mudança persistente de chart type é semântica no Blueprint 2.0 | Side chat visual não pode alterar `widget_type` sem nova versão contratual | BLOCKED_BY_CONTRACT |

## Backend Governado de Dashboards V2

| ID | Dívida/adiamento | Mitigação atual | Saída exigida | Status |
|---|---|---|---|---|
| TD-DASH-BE-001 | Frontend V2 ausente | Router default ausente e tipos apenas contratuais | Prompt 21 certificado | PLANNED |
| TD-DASH-BE-002 | Renderer visual adiado | Backend retorna dados tipados, não HTML | Renderer sem recálculo no Prompt 21 | PLANNED |
| TD-DASH-BE-003 | Editor e drag-and-drop adiados | Patches strict e allowlisted | Editor com CAS e acessibilidade | PLANNED |
| TD-DASH-BE-004 | Side chat adiado | Nenhum texto conversacional no blueprint | Prompt 21 com contexto governado | PLANNED |
| TD-DASH-BE-005 | Geração/edição por IA adiada | Zero chamada OpenAI no backend V2 | Prompt 22 com proposta e revisão humana | PLANNED |
| TD-DASH-BE-006 | Migração efetiva do legado adiada | Adapter somente dry-run, sem persistência | Tarefa explícita de inventário/reconciliação | BLOCKED |
| TD-DASH-BE-007 | Rollout produtivo bloqueado | `LEGACY_ONLY`, flags off, allowlist vazia | Change approval, piloto e rollback operacional | BLOCKED |
| TD-DASH-BE-008 | Backup produtivo não executado | Restore drill apenas descartável | Política, criptografia e ensaio aprovados por DBA | BLOCKED |
| TD-DASH-BE-009 | Load test não executado | Budgets e limites fechados | Ambiente dedicado e SLO aprovados | PLANNED |
| TD-DASH-BE-010 | `LUMINA-GAP-DASH-001` aberto | Único xfail estrito, sem mascaramento | Integração visual-only no Prompt 21 | OPEN |
| TD-DASH-BE-011 | Runtime V2 desativado | Autoridades reutilizadas e guards fail-closed | Piloto allowlisted com telemetria | BLOCKED |
| TD-DASH-BE-012 | Data export de dashboard | Resultado completo não é persistido por default | Contrato de export/retention futuro | FUTURE |
| TD-DASH-BE-013 | Colaboração avançada | Roles fechadas e CAS básico | Teams, ownership transfer e revogação em massa governados | FUTURE |
| TD-DASH-BE-014 | Scheduled refresh | Materialização somente publicada/fresh | Scheduler tenant-scoped com lease/SLO | FUTURE |

## Dashboard Blueprint V2

| ID | Dívida | Risco | Mitigação atual | Saída planejada | Status |
|---|---|---|---|---|---|
| TD-DASH-001 | Runtime e persistência V2 implementados, porém desativados | Ativação prematura sem operação aprovada | `LEGACY_ONLY`; legado preservado | Rollout controlado após Prompt 21 e aprovações | BLOCKED |
| TD-DASH-002 | Renderer visual, editor e side chat ausentes | Sem experiência V2/capabilities | Nenhuma página, Sidebar ou request criada | Prompt 21 | PLANNED |
| TD-DASH-003 | Geração por IA ausente | Automação não disponível | Origem de IA é somente enum; zero chamada | Prompt 22 | PLANNED |
| TD-DASH-004 | `LUMINA-GAP-DASH-001` continua aberto | Estado não preserva `UI_MODIFIED` | Único xfail estrito mantido | Resolver sem mascarar assertion | OPEN |
| TD-DASH-005 | Adapter parcial e widgets legados não suportados | Revisão manual de parte do corpus | Warnings e status PARTIAL/UNSUPPORTED | Corpus e adapters versionados | ACTIVE |
| TD-DASH-006 | Limites contratuais provisórios | Volume real pode requerer ajuste | Limites fechados/testes de abuso | Benchmark isolado e versão compatível | ACTIVE |
| TD-DASH-007 | Navegação cross-dashboard futura | Drill paths ficam locais | Somente navegação interna allowlisted | Capability autenticada anti-IDOR | FUTURE |

Ausências deliberadas adicionais: frontend, editor, side chat, renderer,
migração efetiva do legado e rollout. Esta dívida não autoriza ativação parcial.

## Smart Cache e Materialização V2

| ID | Dívida | Risco | Mitigação atual | Saída |
|---|---|---|---|---|
| TD-CACHE-001 | Worker/scheduler distribuído de refresh não implementado | Refresh operacional depende de comando explícito | Build/refresh síncronos, lease, timeout e flags desligadas | Implementar job queue tenant-scoped com resume e SLO antes do rollout |
| TD-CACHE-002 | Inspector frontend existe apenas como componentes inertes | Não há visão operacional no modo experimental | Nenhuma página/link/request em produção; API limitada e admin-gated | Criar página apenas em rollout separado com testes Next/Playwright e RBAC |
| TD-CACHE-003 | Incremental limitado a watermark previamente verificado | Delta incompleto poderia parecer atual | Fail-closed; full build continua disponível | Certificar tombstones, monotonicidade, replay e equivalência full/incremental |
| TD-CACHE-004 | Coordenação cross-replica usa lease PostgreSQL sem broker | Contenção pode resultar em retry limitado | TTL, CAS, timeout, recovery e single-flight local | Medir SLO com múltiplas réplicas e adicionar polling governado antes de escala |

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

## AI Orchestration V2

| ID | Simbolo Ou Arquivo | Motivo | Substituto Planejado | Consumidores | Flag | Condicao Objetiva De Saida | Risco | Etapa | Status |
|---|---|---|---|---|---|---|---|---|---|
| TD-ORCH-001 | Execucao sequencial limitada de ferramentas | Chamadas paralelas adiadas nesta fase | Execucao paralela governada com sincronizacao | AI Tool Invocation | `AI_PARALLEL_TOOL_CALLS_ENABLED` | Infraestrutura formal com barreira de seguranca e timeout coletivo | Race condition | Fase futura | BLOCKED |
| TD-ORCH-002 | Token Estimator conservador | Tokenizador baseado em ratio | Tokenizer neural isolado | Context Assembler | `AI_EXACT_TOKENIZER_ENABLED` | Tokenizer local sem rede validado | Ligeira variacao de estimativa | Fase futura | ACTIVE |
| TD-ORCH-003 | Fallback de modelo desligado em producao | Feature flag default LEGACY_ONLY | Fallback allowlisted ativo | Orchestrator | `AI_MODEL_FALLBACK_ENABLED` | Certificacao de modelo secundario e teste de falha de provedor | Falha silenciosa de modelo principal | Rollout | ACTIVE |

## Dashboard AI Assistance V2

| ID | Item | Estado e condição de saída |
|---|---|---|
| TD-DAI-001 | Provider real, benchmark e avaliação humana produtiva ausentes | Bloqueado até certificação e aprovação operacional |
| TD-DAI-002 | Rollout, load test e backup produtivo não executados | Produção permanece `LEGACY_ONLY`; executar somente em fase autorizada |
| TD-DAI-003 | Somente pt-BR e templates iniciais | Outros locales/templates e cross-dashboard generation ficam para evolução governada |
| TD-DAI-004 | Monitoramento de qualidade semântica e retention operacional futuros | Definir SLO, painel e política antes do rollout |
| TD-DAI-005 | Geração baseada em sample de dataset | Proibida; exige nova decisão arquitetural para qualquer mudança |

A migration v23 foi criada e certificada apenas em PostgreSQL descartável; sua
aplicação produtiva e backup real continuam fora de escopo.
