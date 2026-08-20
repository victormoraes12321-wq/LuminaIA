# Threat Model V2 — Segurança, Migração e Rollout

- Versão: `lumina.security-migration-rollout/1.0`
- Estado: `PRE_IMPLEMENTATION_AUDIT_COMPLETED`
- Data da auditoria: 2026-08-10
- Produção observada: `LEGACY_ONLY`; worker V2, performance e rollout desabilitados
- Método: código executado, configuração, routers, services, migrations V1–V26,
  testes e documentação operacional; inferências são marcadas.

## Autoridades e fronteiras

| Superfície | Autoridade confiável | Entrada não confiável | Ameaça principal | Controle/gate |
| --- | --- | --- | --- | --- |
| HTTP | FastAPI após middleware e autenticação | URL, body, query, headers, cookies | abuso de input, spoofing e erro verboso | limites, autenticação, sanitização e rate limit |
| Autenticação | JWT validado e usuário ativo carregado do PostgreSQL | bearer/cookie e claims forjados | auth bypass e sessão stale | assinatura, expiração, lookup composto user+tenant |
| Autorização | papel atual do `User` e policies estáticas | role/capability no payload | privilege escalation | deny-by-default e capability explícita |
| Tenant | `current_user.tenant_id` carregado do banco | tenant em body/query/header | BOLA/IDOR e cross-tenant | filtro composto e concealment 404 |
| API V1/V2 | routers e services governados | IDs e filtros do cliente | mass assignment, replay e enumeração | contratos estritos, RBAC e escopo server-side |
| Dashboard/AI | policies dos Prompts 20–22 | IDs, patches, texto do modelo | publicação por IA e IDOR | CAS, revisão humana, tenant e capability |
| Post-Sync/outbox | sync reconciliado e detector estático | replay/idempotency key | efeito duplicado e publicação indevida | outbox, CAS, fingerprint e feature mode |
| Observability/evals | registry estático e contexto autenticado | trace/run ID e corpus selector | disclosure cross-tenant e cardinalidade | store tenant-scoped, allowlist e redaction |
| Work Queue | job tenant-scoped e worker server-side | job/worker ID, payload e replay | duplicate effect, worker forging e leakage | lease CAS, tenant filter e replay terminal |
| Safe PostgreSQL/cache/materialização | catálogo/compilador e tenant autenticado | spec, filtros, IDs | SQL injection, stale permission e cache poisoning | identificadores allowlisted, binds e scope key |
| Sync/reconciliação | serviço técnico autorizado | configuração, origem e watermark | Oracle no caminho da IA e SSRF | fronteira técnica separada e flags fechadas |
| Migrations/startup | scripts explícitos e DB guard | DSN, versão e concorrência | DB errado, drift e DDL concorrente | target guard, compatibility e advisory lock |
| Background workers | configuração server-side | headers, payload e IDs de worker | ativação acidental e impersonation | worker disabled, static registry e kill switch |
| Frontend/admin | backend autenticado e capabilities efetivas | JWT decodificado no cliente, texto e cache | XSS, UI stale e falsa elevação | React escaping; backend é autoridade final |
| Arquivos/paths | paths constantes resolvidos no servidor | trace/export/dump identifiers | traversal e command injection | validação fechada e containment por `resolve()` |
| Rede externa | adapters registrados e configuração do ambiente | URL/provider/model em payload | SSRF e exfiltração | providers server-side e egress bloqueado em teste |
| Secrets/logs/traces | credential managers e redaction Prompt 24 | exceptions, headers e payloads | segredo, SQL, binds, PII ou CoT em saída | redaction central e payload estrutural |
| OpenAPI/test/shadow | montagem condicional server-side | feature mode forjado | exposição experimental e side effects | default sem rotas experimentais; shadow read-only |
| Rollout | policy estática, evidence e configuração | tenant/cohort/stage do cliente ou LLM | bypass de gate/canary inseguro | precedência global→feature→env→migration→security |

## Findings da auditoria de entrada

| ID | Severidade | Componente | Evidência | Estado requerido |
| --- | --- | --- | --- | --- |
| P26-SEC-001 | CRITICAL | Validation & Provenance V2 | tenant e usuário derivados de `X-Tenant-ID`/`X-User-ID` ou defaults | substituir por usuário autenticado; headers nunca autoridade |
| P26-SEC-002 | HIGH | Safe PG / AI Orchestration | routers tratam `User` SQLAlchemy como `dict`, causando erro e fallbacks inseguros | usar atributos tipados e erros públicos constantes |
| P26-SEC-003 | CRITICAL | Inspector legado | trace ID compõe path e detail/replay devolvem SQL, binds, amostras e traceback | conter path e retornar apenas diagnóstico estrutural sanitizado |
| P26-SEC-004 | CRITICAL | Observability V2 | runs em store global sem tenant no lookup por ID | particionar store por tenant autenticado e concealment 404 |
| P26-SEC-005 | HIGH | Work Queue V2 | stats globais e replay sem estado terminal estrito; erro/reason sem redaction | filtrar stats por tenant, restringir replay e reutilizar redaction |
| P26-SEC-006 | HIGH | configuração/rollout | não existe registry unificado, compatibility gate, kill switch global ou canary policy | adicionar mecânica pura fail-closed, sem endpoint e sem rollout real |
| P26-SEC-007 | MEDIUM | migrations ad hoc | não há runner único nem advisory lock comum | criar wrapper governado para futuras execuções; não editar migrations históricas |
| P26-SEC-008 | MEDIUM | frontend proxy | decode JWT é somente guarda ergonômica, sem verificar assinatura | backend continua autoridade; documentar e manter dados/admin protegidos pela API |

CRITICAL/HIGH devem terminar `REMEDIATED` e cobertos por teste para permitir
checkpoint. O finding P26-SEC-008 não concede acesso backend e permanece risco
de defesa em profundidade documentado, não uma autoridade de autorização.

## Abuso e invariantes

- Tenant A com ID de B recebe `NOT_FOUND` não revelador.
- Role, capability, tenant, user, worker, provider, mode e cohort enviados pelo
  cliente não alteram autoridade.
- SQL, comandos, paths, URLs, prompts, CoT, secrets, binds e datasets não são
  aceitos por contratos de rollout nem retornados por readiness.
- Qualquer tenant leak, auth bypass, secret leak ou rollout bypass é
  `CRITICAL` e bloqueia readiness sem média ou compensação.
- `GLOBAL_EMERGENCY_DISABLE` e kill switch de feature precedem todos os demais
  gates e impedem nova execução.
- `SHADOW` não publica, não muda fatos, não liga worker e não promove estado.
- Downgrade de banco produtivo não é automático; rollback preferencial é
  feature disable e, quando compatível, rollback da aplicação.
- `HEALTH` significa processo vivo; readiness pode estar bloqueada sem crash.

## Escopo de teste

O corpus sintético deve cobrir cross-tenant, IDOR, forged auth/role/tenant/header,
SQL/XSS/SSRF/command/path injection, secret/CoT leakage, queue payload, replay,
kill-switch bypass, migration mismatch, drift, canary determinístico e rollback.
Oracle, OpenAI, provider real, rede externa, banco operacional e porta 5432
permanecem proibidos durante certificação.

## Disposição final dos findings

- `P26-SEC-001` REMEDIATED — tenant/user vêm de `get_current_user`.
- `P26-SEC-002` REMEDIATED — routers usam atributos do model e erro constante.
- `P26-SEC-003` REMEDIATED — path contido, trace redigido e replay fail-closed.
- `P26-SEC-004` REMEDIATED — evaluation runs tenant-scoped; trace sem owner oculto.
- `P26-SEC-005` REMEDIATED — stats tenant-scoped, replay terminal e redaction.
- `P26-SEC-006` REMEDIATED — registry/gates/kill switches/canary estáticos.
- `P26-SEC-007` REMEDIATED_FOR_FUTURE_EXECUTION — advisory lock governado; migrations
  históricas não foram alteradas nem executadas em produção.
- `P26-SEC-008` ACCEPTED_DEFENSE_IN_DEPTH_DEBT — frontend não é autoridade e toda API
  continua protegida pelo backend; migração para guard server-side permanece futura.

CRITICAL/HIGH não resolvidos: `0`.
