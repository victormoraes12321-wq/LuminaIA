# Deprecation Ledger

## Interface de dashboards — Prompt 21

| ID | Legado preservado | Substituto governado | Condição para rollout/remoção | Status |
|---|---|---|---|---|
| DEP-DASH-UI-001 | Renderer visual legado | registry estático V2 com 16 widgets | V2_READ piloto, equivalência e rollback aprovados | ACTIVE_LEGACY |
| DEP-DASH-UI-002 | Página `/dashboard` e Studio legados | rotas `/dashboard/v2` guardadas | Zero consumidor legado, SLO e aprovação formal | ACTIVE_LEGACY |
| DEP-DASH-UI-003 | visual-only handler com `FULL_RENDERING` genérico | patch visual + interceptor + `UI_MODIFIED` confirmado | DASH-001 resolvido; remover apenas após migração dos consumidores | DEPRECATED_NOT_REMOVED |
| DEP-DASH-UI-004 | configs livres de widget | Blueprint union fechada + registry estático | Corpus compatível e adapters certificados | DEPRECATED_NOT_REMOVED |
| DEP-DASH-UI-005 | chat sem action schema | side chat com contexto/ação estritos | V2_SIDE_CHAT piloto e telemetria aprovados | DEPRECATED_NOT_REMOVED |
| DEP-DASH-UI-006 | V2 ausente da leitura | `V2_READ` | Backend Prompt 20, IDOR/RBAC, migration/backup e allowlist | READY_NOT_ENABLED |
| DEP-DASH-UI-007 | authoring legado | `V2_AUTHORING` com CAS/idempotência | Review operacional, conflitos e auditoria aprovados | READY_NOT_ENABLED |
| DEP-DASH-UI-008 | conversa visual livre | `V2_SIDE_CHAT` action-only | V2_AUTHORING aprovado, cancelamento/stale e leakage zero | READY_NOT_ENABLED |
| DEP-DASH-UI-009 | criação manual sem proposta governada | proposta assistida futura | Prompt 22 certificado; review/publicação continuam humanos | FUTURE |

Nenhuma remoção ocorreu. Produção permanece `LEGACY_ONLY` e a remoção
futura depende de piloto, backup/restore, migração reconciliada, observabilidade,
zero consumidor legado, janela de rollback encerrada e aprovação formal.

## Backend Governado de Dashboards V2

| ID | Legado preservado | Substituto governado | Condição de shadow/rollout/remoção | Dependências | Status |
|---|---|---|---|---|---|
| DEP-DASH-BE-001 | `backend/services/blueprints.json` e storage JSON | revisions PostgreSQL V22 | Shadow sem escrita; V2_AUTHORING somente após migration/backup/allowlist; remoção após zero consumidor e rollback expirado | Prompts 21 e 22 | ACTIVE_LEGACY |
| DEP-DASH-BE-002 | models legados de template/instance/studio | models tenant-scoped V22 | Equivalência, migração explícita e reconciliação aprovadas | Prompt 21 | ACTIVE_LEGACY |
| DEP-DASH-BE-003 | APIs legadas de dashboards | `/api/v2/dashboards` condicional | V2_PUBLISHED_READ após IDOR/RBAC/SLO; remoção só após clientes migrados | Prompt 21 | ACTIVE_LEGACY |
| DEP-DASH-BE-004 | publication mutável/implícita legada | approval + publication imutável + active CAS | Publishing flag, backup e rollback operacional aprovados | Operação/DBA | DEPRECATED_NOT_REMOVED |
| DEP-DASH-BE-005 | runtime legado | runtime V2 certificado | V2_RUNTIME após piloto, leakage zero, cache/freshness/SLO e rollback | Prompt 21 | ACTIVE_LEGACY |
| DEP-DASH-BE-006 | patches não tipados | visual/semantic patches V2 | Editor tipado, CAS e `LUMINA-GAP-DASH-001` certificados | Prompt 21 | DEPRECATED_NOT_REMOVED |
| DEP-DASH-BE-007 | permissões antigas dispersas | RBAC global ∩ ownership/grants/policy | Auditoria de todos os consumidores e permission-change imediato | Prompt 21 | ACTIVE_TRANSITION |
| DEP-DASH-BE-008 | criação/configuração manual ou livre | proposta futura governada | Prompt 22 pode apenas propor; review/approval/publication continuam humanos | Prompt 22 | FUTURE |

Progressão autorizável, nunca automática: `LEGACY_ONLY` → `SHADOW_VALIDATE` →
`V2_AUTHORING` → `V2_PUBLISHED_READ` → `V2_RUNTIME`. Nenhum item foi removido.
Remoção futura exige backup/restore produtivo, migração reconciliada, zero
consumidor legado, segurança multi-tenant, observabilidade, janela de rollback
encerrada e aprovação formal.

## Dashboard Blueprint V2

| ID | Símbolo ou formato legado | Motivo | Substituto planejado | Condições para migração/remoção | Dependências | Status |
|---|---|---|---|---|---|---|
| DEP-DASH-001 | Blueprints legados e `backend/services/blueprints.json` como storage operacional | JSON e ciclo de vida não correspondem ao contrato canônico | Backend governado sobre `lumina.dashboard-blueprint/2.0` | Migration aditiva, tenant/RBAC, CAS, publicação, piloto e rollback aprovados | Prompt 20 | ACTIVE_LEGACY |
| DEP-DASH-002 | Schemas antigos de widgets e campos livres em templates/layout/config | Permitem estruturas não tipadas e compatibilidade implícita | Unions discriminadas e widget registry estático V2 | Consumidores adaptados e goldens V1/V2 aprovados | Prompts 20 e 21 | DEPRECATED_NOT_REMOVED |
| DEP-DASH-003 | Visual updates não tipados | Podem misturar apresentação e semântica | Visual e semantic patches V2 | CAS, revision enforcement, auditoria e editor certificados | Prompts 20 e 21 | DEPRECATED_NOT_REMOVED |
| DEP-DASH-004 | Legacy adapters | Necessários durante convivência, com cobertura parcial | Ingestão V2 nativa | Zero consumidor legado, migração verificada e rollback encerrado | Prompts 20, 21 e 22 | ACTIVE_TRANSITION |

Nenhum item está removido. O V2 isolado não muda a autoridade do runtime. A
remoção futura exige equivalência funcional, segurança, acessibilidade, tenant
isolation e rollback comprovados.

## Smart Cache e Materialização V2

| ID | Símbolo ou arquivo | Motivo | Substituto | Flag | Condição objetiva para remoção | Risco | Status |
|---|---|---|---|---|---|---|---|
| DEP-CACHE-001 | Reexecução sem cache certificado | Fallback necessário enquanto rollout não for aprovado | Smart Cache V2 | `SMART_CACHE_MATERIALIZATION_MODE` | Todos os tenants com SLO, leakage zero, invalidation e rollback aprovados | Resultado stale ou incompatível se removido cedo | ACTIVE |
| DEP-CACHE-002 | Blueprints JSON no caminho compartilhado de runtime | Compatibilidade do repositório legado | Storage server-controlled; arquivo temporário em testes | n/a | Migration do repositório de blueprints aprovada separadamente | Corrupção/colisão se testes voltarem a escrever no arquivo real | DEPRECATED_RUNTIME_ONLY |
| DEP-CACHE-003 | `LEGACY_ONLY` do Prompt 18 | Rollout deliberadamente não autorizado | SHADOW/READ/READ_WRITE/MATERIALIZATION graduais | `SMART_CACHE_MATERIALIZATION_MODE` | Migration operacional, piloto por tenant, SLO e janela de rollback aprovados | Ativação prematura | ACTIVE |

| ID | Componente | Estado | Substituto | Regra De Remocao |
|---|---|---|---|---|
| DEP-001 | Preferencia de dashboard legada | DEPRECATED | `lumina.user-analytical-profile/1.0` | Remover somente apos todos os tenants concluirem V2_READ_WRITE e rollback legado expirar. |
| DEP-002 | Defaults pessoais inferidos sem confirmacao | FORBIDDEN | Criacao explicita com consentimento | Nao migrar nem promover automaticamente. |
| DEP-003 | Referencia pessoal a Knowledge asset deprecated | DEPRECATED_REFERENCE | Versao publicada e vigente | Nao aplicar; solicitar escolha valida sem trocar silenciosamente. |
| DEP-004 | Perfil em RAM, JSON local ou historico do cliente | FORBIDDEN_AUTHORITY | PostgreSQL com escopo tenant/usuario | Nao introduzir em fluxo V2. |
| DEP-005 | `AIInvocationManager.register_feedback` como feedback de usuario | LEGACY_INTERNAL_ONLY | `lumina.supervised-feedback/1.0` | Nao conectar a UI nem usar como dataset; remover depois do rollout governado. |
| DEP-006 | `SUPERVISED_FEEDBACK_MODE=LEGACY_ONLY` | ACTIVE | Modos `SHADOW`, `V2_COLLECT`, `V2_REVIEW` e `V2_CURATE` | Remover fallback somente depois da migration v15, piloto, auditoria de tenant e rollback operacional aprovados. |
| DEP-006 | Treino direto por thumbs up/down | FORBIDDEN | Revisao, curadoria e snapshot explicitos | Nunca migrar automaticamente. |
| DEP-007 | Dataset mutavel ou alias `latest` | FORBIDDEN | Snapshot publicado com versao explicita | Toda mudanca cria nova versao. |

Estados deste ledger nao alteram o lifecycle dos ativos da Knowledge Base. Uma
referencia pessoal nunca publica, depreca ou restaura conhecimento.

## Semantic Retrieval V2

| ID | Simbolo Ou Arquivo | Motivo | Substituto | Consumidores | Flag | Condicao Objetiva Para Remocao | Risco | Etapa | Status |
|---|---|---|---|---|---|---|---|---|---|
| DEP-SR-001 | canonicalizer legado em `metadata_catalog` | Mantido para compatibilidade V1 e rollback | `services/semantic_retrieval` + patch V2 | Orchestrator e intent legado | `SEMANTIC_RETRIEVAL_MODE` | Todos os tenants em V2_AUTHORITATIVE, corpus aprovado e duas releases sem rollback | Troca silenciosa de entidade se removido cedo | Pos-Prompt 14 | SHADOW |
| DEP-SR-002 | `SemanticMemory` e mapas em RAM | Nao sao autoridade replicavel | Indice PostgreSQL publicado v16 | Pipeline legado | `SEMANTIC_RETRIEVAL_MODE` | Zero leitura autoritativa por 90 dias e rollback expirado | Divergencia entre replicas | Pos-rollout | DEPRECATED |
| DEP-SR-003 | fallback semantico legado | Necessario em LEGACY_ONLY/SHADOW | Retrieval V2 tenant-scoped | NewQueryOrchestrator | `SEMANTIC_RETRIEVAL_MODE` | SLO, leakage zero e avaliacao aprovados por tenant | Regressao de recall | Pos-rollout | ACTIVE |
| DEP-SR-004 | `_question_with_inherited_context` | Adapter legado de contexto | Context Resolution + Semantic Resolution | Orchestrator | flags de contexto e semantic | Nenhum consumidor V1 e goldens multi-turn aprovados | Perda de continuidade | Fase posterior | DEPRECATED |
| DEP-SR-005 | provider `DETERMINISTIC_FEATURE_HASH` | Fallback local inicial, nao embedding neural | Provider governado futuro, opcional e offline/aprovado | Index builder e retrieval | `SEMANTIC_VECTOR_CHANNEL_ENABLED` | Provider substituto sem rede certificado e migration compativel | Mudanca de score | Etapa futura | ACTIVE |

Nenhum item deste ledger autoriza ativar V2 em producao, consultar Oracle,
afrouxar tenant/RBAC ou remover o fallback antes das condicoes objetivas.

## AI Orchestration V2

| ID | Simbolo Ou Arquivo | Motivo | Substituto | Consumidores | Flag | Condicao Objetiva Para Remocao | Risco | Etapa | Status |
|---|---|---|---|---|---|---|---|---|---|
| DEP-ORCH-001 | Orchestrator legado unconstrained | Falta de orcamentos finitos e state machine | `services/ai_orchestration` V2 | API de consulta | `AI_ORCHESTRATION_MODE` | Rollout V2_GOVERNED aprovado | Divergencia no contrato de resposta | Pos-Prompt 16 | SHADOW |
| DEP-ORCH-002 | Token Estimator conservador local | Estimativa base em ratio, nao tokenizer neural por modelo | Estimador neural provider-aware | Context Assembler | `AI_ORCHESTRATION_MODE` | Biblioteca de tokenizacao exata certificada sem dependencias externas | Ligeira variacao na margem de seguranca | Etapa futura | ACTIVE |

## Dashboard AI Assistance V2

| ID | Símbolo ou fluxo | Motivo | Substituto | Flag | Condição objetiva | Status |
|---|---|---|---|---|---|---|
| DEP-DAI-001 | Criação manual sem assistência | Compatibilidade e fallback obrigatórios | Wizard governado opcional | `DASHBOARD_AI_ASSISTANCE_MODE` | Rollout produtivo aprovado, adoção medida e rollback certificado | ACTIVE |
| DEP-DAI-002 | Propostas livres, geração direta de Blueprint e semantic edit por texto livre | Sem tipos, evidence ou validação suficiente | Proposal/version + builder/patch compiler determinísticos | `DASHBOARD_AI_ASSISTANCE_MODE` | Preview, DRAFT create e assisted edit aprovados em sequência | BLOCKED |
| DEP-DAI-003 | Prompts sem evidence | Racional sem autoridade verificável | Evidence canônica Prompt 22 | `DASHBOARD_AI_APIS_ENABLED` | Cobertura e qualidade aprovadas em avaliação humana | ACTIVE |

`AI_PROPOSAL_PREVIEW`, `AI_DRAFT_CREATE` e `AI_ASSISTED_EDIT` exigem aprovação
operacional separada. O fluxo manual não será removido antes dessas condições.
