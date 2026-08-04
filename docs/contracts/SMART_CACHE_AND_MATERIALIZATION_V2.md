# Smart Cache e Materialização Governada V2

Versão canônica: `lumina.smart-cache-materialization/1.0`.

## Escopo e autoridades

O Smart Cache reutiliza apenas resultados analíticos completos, frescos e
certificados. Ele não cria métricas, não recalcula valores, não certifica e não
executa SQL. `MetricRegistry` continua autoridade de fórmulas e fingerprints;
Safe Analytical PostgreSQL compila e executa a query canônica com prova de
tenant; Validation & Provenance valida fatos, claims, completude e freshness.

Materializações são snapshots imutáveis construídos pelo mesmo caminho
analítico e publicados por troca explícita e atômica de ponteiro. Oracle,
OpenAI, SQL livre, connection strings, binds abertos e resultados produzidos
pelo modelo são proibidos.

## Contratos

Os contratos Pydantic v2 ficam em
`backend/contracts/smart_cache_materialization_v2/`, usam `extra="forbid"` e
incluem políticas, eligibility, scope/key, entries, lookup/write, invalidação,
generations, leases, auditoria, GC, definitions, builds, snapshots,
publications, refresh e rollback. Requests administrativos não aceitam tenant
como autoridade, raw cache key, TTL livre, SQL, conexão ou rows.

## Eligibility e TTL

O motor é puro, determinístico e fail-closed. Por padrão, somente
certificação `VALID`, prova de tenant e fingerprints válidas, fonte `FRESH`,
resultado completo, não parcial, não truncado e classificação permitida podem
ser cacheados. `VALID_WITH_WARNINGS` requer política explícita. PII, secret,
row-level, ambiguity, stale, timeout, cancellation, error, invalid e
unverifiable resultam em bypass. TTL vem exclusivamente da política governada,
dentro de limites mínimos e máximos.

## Scope e cache key

A key é construída no servidor a partir de versão/namespace, tipo, fingerprint
de tenant e usuário quando aplicável, permission fingerprint, query e metric
fingerprints, catálogo, filtros, período, estratégia do tenant, source sync,
watermark, políticas de validação/certificação, compilador, snapshot de tools,
locale quando semântico e generation counters. Pergunta, prompt, SQL, binds,
credenciais, nome de usuário e chain of thought não entram na key.

## Materializações

Lifecycle: `DRAFT`, `IN_REVIEW`, `APPROVED`, `BUILDING`, `VALIDATING`, `READY`,
`PUBLISHED`, `STALE`, `FAILED`, `DISABLED`, `DEPRECATED` e `ARCHIVED`.
Build usa uma query spec canônica no Safe Analytical PostgreSQL, passa o
resultado por Validation & Provenance e cria um snapshot `READY`; nunca publica
automaticamente. Publicação e rollback exigem permission, snapshot válido e
fresco, checksum, certificação e CAS. Refresh cria outro snapshot sem substituir
o ativo. Somente o snapshot apontado pela publicação é legível.

## Persistência e isolamento

A migration explícita V21 cria 14 tabelas tenant-scoped para cache,
materializações e avaliações. FKs compostas impedem dependências e ponteiros
cross-tenant. Leases têm owner token interno armazenado apenas como checksum,
expiração e CAS. Invalidation usa dependency tags e generations. GC é limitado,
tenant-scoped, suporta dry-run/keyset para entries, remove leases expiradas e
artefatos antigos, preservando snapshots ativo e anterior.

## Modos e API

Modos permitidos: `LEGACY_ONLY`, `SHADOW_OBSERVE`, `V2_CACHE_READ`,
`V2_CACHE_READ_WRITE` e `V2_MATERIALIZATION`. O default é `LEGACY_ONLY` e
`SMART_CACHE_ADMIN_ENABLED=false`; nesse estado não há router, models globais,
services, tabelas, migration ou tasks do Prompt 18 no bootstrap.

A API experimental só é montada quando as duas flags server-controlled
permitem. Ela expõe estatísticas, invalidação, GC, publicação e rollback
limitados. Tenant vem do token. `CONSULTA` não administra cache; operações
mutáveis exigem permissions específicas e CAS quando aplicável.

Schemas, goldens e OpenAPI reproduzíveis ficam em
`docs/contracts/smart_cache_materialization_v2/`.
