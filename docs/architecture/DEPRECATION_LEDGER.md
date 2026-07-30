# Deprecation Ledger

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
