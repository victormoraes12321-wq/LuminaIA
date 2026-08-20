# PROMPT 14 — REGISTRO GOVERNADO DE FERRAMENTAS DA IA DO LUMINAAI

## 1. Visão Geral e Arquitetura

O **Registro Governado de Ferramentas da IA do LuminaAI** foi implementado na versão contratual `lumina.ai-tool-registry/1.0`. Este componente atua como a autoridade central, fail-closed, estaticamente tipada e auditada para a descoberta, validação, publicação e execução de ferramentas disponíveis para a inteligência artificial.

### Princípios de Segurança e Governança
1. **Autoridade Fail-Closed**: Nenhuma ferramenta ou versão não catalogada e não ativa pode ser executada.
2. **Zero Dynamic Code Execution**: Proibição total de `eval`, `exec`, `subprocess`, `shell`, `importlib`, `getattr` ou imports dinâmicos arbitrários. O mapeamento entre `adapter_id` e adaptadores é estático (`REGISTERED_TOOL_ADAPTERS`).
3. **Mapeamento Estático de Adaptadores**: Todos os 12 adaptadores iniciais da aplicação estão estaticamente declarados em `backend/services/ai_tool_registry/adapters/`.
4. **Isolamento de Capabilities**: Ferramentas declaram estritamente suas capabilities. As capabilities reservadas para o Prompt 15 (`ANALYTICAL_POSTGRESQL_READ` e `EXECUTE_GOVERNED_ANALYTICAL_PLAN`) foram implementadas em estado desabilitado/bloqueado.
5. **Auditoria e Provinência**: Toda invocação gera envelope com hash SHA-256 e registro auditável estruturado no PostgreSQL.
6. **Resiliência e Proteção**: Rate limiting por tenant/usuário, Circuit Breaker com estados (`CLOSED`, `HALF_OPEN`, `OPEN`), timeout por deadline (`asyncio.wait_for`) e redação de saída.

---

## 2. Modelagem e Estrutura de Dados (Migration v17.0)

A migração `backend/database/migration_v17_0.py` cria 12 tabelas totalmente aditivas, idempotentes e isoladas por tenant:

1. `ai_tool_identities_v2`: Identidades canônicas de ferramentas.
2. `ai_tool_versions_v2`: Versões e ciclos de vida (`DRAFT`, `IN_REVIEW`, `APPROVED`, `ACTIVE`, `DEPRECATED`, `DISABLED`, `RETIRED`, `REJECTED`).
3. `ai_tool_capabilities_v2`: Relacionamento de capabilities permitidas por versão.
4. `ai_tool_snapshots_v2`: Snapshots imutáveis do catálogo publicado.
5. `ai_tool_snapshot_items_v2`: Itens congelados em cada snapshot.
6. `ai_tool_policy_assignments_v2`: Políticas atreladas por ferramenta e tenant.
7. `ai_tool_tenant_allowlists_v2`: Allowlists de ferramentas autorizadas por tenant.
8. `ai_tool_approvals_v2`: Registro de revisões e aprovações (com guarda contra auto-aprovação do próprio autor).
9. `ai_tool_invocation_records_v2`: Log auditável de invocações com checksums.
10. `ai_tool_circuit_breaker_events_v2`: Eventos de mudança de estado do circuit breaker.
11. `ai_tool_rate_limit_events_v2`: Registros de bloqueio por rate limit.
12. `ai_tool_audit_events_v2`: Trilha de auditoria administrativa.

---

## 3. Catálogo Inicial de Ferramentas Governadas (12 Ferramentas)

| Tool ID | Display Name | Capability | Risco | Side-Effect |
| :--- | :--- | :--- | :--- | :--- |
| `lumina.enterprise_knowledge.search` | Enterprise Knowledge Search | `READ_ENTERPRISE_KNOWLEDGE` | LOW | READ_ONLY |
| `lumina.enterprise_knowledge.get_metric_definition` | Get Metric Definition | `GET_METRIC_DEFINITION` | LOW | READ_ONLY |
| `lumina.temporal.normalize` | Temporal Normalizer | `NORMALIZE_TEMPORAL_EXPRESSION` | LOW | READ_ONLY |
| `lumina.semantic.search` | Semantic Knowledge Search | `SEARCH_SEMANTIC_INDEX` | LOW | READ_ONLY |
| `lumina.semantic.resolve_entity` | Entity Resolver | `RESOLVE_ENTITY` | LOW | READ_ONLY |
| `lumina.context.get_public_summary` | Context Public Summary | `READ_CONTEXT_SUMMARY` | LOW | READ_ONLY |
| `lumina.profile.get_application_summary` | Profile Application Summary | `READ_PROFILE_SUMMARY` | LOW | READ_ONLY |
| `lumina.intent.validate` | Intent Validator | `VALIDATE_QUERY_INTENT` | MEDIUM | READ_ONLY |
| `lumina.comparison.plan` | Comparison Planner | `PLAN_COMPARISON` | MEDIUM | READ_ONLY |
| `lumina.comparison.validate_plan` | Comparison Plan Validator | `VALIDATE_COMPARISON_PLAN` | MEDIUM | READ_ONLY |
| `lumina.clarification.build_options` | Clarification Builder | `BUILD_CLARIFICATION_OPTIONS` | LOW | READ_ONLY |
| `lumina.provenance.get_public_summary` | Provenance Summary | `READ_PROVENANCE_SUMMARY` | LOW | READ_ONLY |

---

## 4. Endpoints de API e Interface Administrativa

### Rotas de Runtime (`/api/v2/tools`)
- `GET /api/v2/tools/catalog`: Retorna catálogo público otimizado e filtrado para o tenant.
- `POST /api/v2/tools/validate-proposal`: Valida propostas de chamadas de ferramenta sem executá-las.
- `POST /api/v2/tools/invoke`: Executa invocações de ferramenta com verificações fail-closed.

### Rotas Administrativas (`/api/v2/admin/tools`)
- `GET /api/v2/admin/tools`: Lista ferramentas e status de governança.
- `POST /api/v2/admin/tools`: Registra novas identidades.
- `POST /api/v2/admin/tools/{tool_id}/versions/{version}/review`: Submete revisão (com validação anti-auto-aprovação).
- `POST /api/v2/admin/tools/{tool_id}/versions/{version}/publish`: Publica versão aprovada.
- `POST /api/v2/admin/tools/{tool_id}/versions/{version}/disable`: Desabilita emergencialmente.
- `POST /api/v2/admin/tools/inspector/test`: Executor e inspector sintético para testes.

### Interface Frontend Next.js
Página administrativa desenvolvida no padrão LuminaAI:
- Arquivo: [page.tsx](../../frontend/app/dashboard/admin/tools/page.tsx)
- Suporte a navegação por abas: **Catálogo Ativo**, **Identidades Registradas**, **Inspector & Testes Sintéticos**.
- Integrado à Sidebar sob a seção de Administração.

---

## 5. Validação de Regras de Segurança e Qualidade

1. **TypeScript e Lint Frontend**:
   - `npm run lint`: 0 erros.
   - `npx tsc --noEmit`: 0 erros.
   - `npm run build`: Sucesso compilado.

2. **Backend e Suíte de Testes**:
   - Cobertura de testes unitários, integração e migração idempotente.
   - Guardas de teste ativas (`ENVIRONMENT=test`, PostgreSQL descartável local).

---

## 6. Estado dos Arquivos e Git

- Branch de Desenvolvimento: `codex/phase-ai-orchestration-prompts-14-18`
- Arquivos de Operação Protegidos: Mantidos intactos e não modificados.
- Commit e Tag: Serão gerados unificados após a conclusão do Prompt 18.

## CERTIFICATION ADDENDUM — CONSOLIDATED REVALIDATION

Data: 2026-08-04. Classificação: `CONSOLIDATED_REVALIDATION`.

O relatório original não preservou uma contagem completa do backend; portanto,
qualquer número histórico externo permanece `HISTORICAL_EVIDENCE_UNAVAILABLE`.
Na revalidação do worktree identificado em
`PHASE_14_17_CONSOLIDATED_CERTIFICATION_EVIDENCE.md`, os cinco arquivos de
teste do AI Tool Registry produziram 17 passed, zero failed/xfail/skip e 2
warnings em 34,90 s. A suíte completa atual produziu 1.348 passed, 1 xfailed,
zero failed e zero XPASS. Migration v17 e idempotência passaram. Frontend,
OpenAPI e segurança passaram conforme a evidência consolidada; nenhum acesso
real a OpenAI, Oracle ou banco operacional ocorreu.
