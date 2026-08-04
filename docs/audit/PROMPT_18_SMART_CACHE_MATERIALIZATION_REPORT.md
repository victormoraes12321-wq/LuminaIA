# Relatório Prompt 18 — Smart Cache e Materialização Governada

Data: 2026-08-04. Contrato: `lumina.smart-cache-materialization/1.0`.

## Estado e trava de entrada

A retomada ocorreu na branch
`codex/phase-ai-orchestration-prompts-14-18`, HEAD
`c5d7621f2b7b3c4c0138a704685ac048515f49db`, com índice vazio e sem novo
commit, tag ou push. A baseline e os cinco documentos obrigatórios foram lidos.
O bootstrap inicial passou com 4 testes. Produção permaneceu
`SMART_CACHE_MATERIALIZATION_MODE=LEGACY_ONLY` e
`SMART_CACHE_ADMIN_ENABLED=false`; OpenAPI default continuou sem rotas Prompt
18. Somente após contratos, imports e auditoria estática passarem a V21 foi
executada em `127.0.0.1:55432/luminaai_test`.

## Blueprints

O caminho oficial continua `backend/services/blueprints.json`. A nova
`BlueprintStoragePolicy` escolhe esse caminho somente no runtime normal e
obriga testes confirmados por `ENVIRONMENT=test` + `LUMINA_TESTING=true` a usar
diretório do sistema operacional, separado por run, PID e worker. A factory não
aceita path de payload/usuário; segmentos são validados; escrita usa arquivo
temporário, fsync e replace atômico sob lock por path; cleanup só alcança a raiz
temporária controlada. O Query Intelligence Engine recebe repository injetável
e usa `RLock` para preservar o bootstrap legado sem deadlock.

SHA-256 inicial de `blueprints.json`:
`407D5C65B7A38A805C073F064A0C1CD9AF6290C8BCBE18809CA645CD81042596`.
SHA-256 final:
`407D5C65B7A38A805C073F064A0C1CD9AF6290C8BCBE18809CA645CD81042596`.
O arquivo terminou byte a byte idêntico ao estado inicial.

## Inventário formal

A busca final encontrou 76 artefatos pelo nome: 38 fontes/testes/docs/tipos e
38 exportados determinísticos (34 schemas, 2 goldens e 2 OpenAPI). Foram também
auditadas 448 referências textuais fora dos exports. A tabela agrupa arquivos
homogêneos; cada arquivo que corresponde a um padrão herda todos os atributos
da respectiva linha.

| Artefato/padrão | Git | Categoria final | Responsabilidade e exports | Consumidores/imports | Tenant/permissions | Cobertura/estado | Risco, duplicação, compatibilidade e ação |
|---|---|---|---|---|---|---|---|
| `backend/contracts/smart_cache_materialization_v2/{identity,policy,eligibility,scope_key,entries,execution_audit,materialization,evaluations,__init__}.py` | novo | `VALID_REUSABLE` | DTOs Pydantic V2 e enums; 34 models públicos | services, router, exporter, testes | tenant apenas em scope/respostas; requests admin sem autoridade; permission fingerprint | contracts/eligibility/key tests verdes | sem contrato paralelo; manter versionado |
| `backend/services/smart_cache_materialization/{policy_service,key_builder,eligibility_engine,lookup_service,write_service,invalidation_service,single_flight,pipeline}.py` | novo | `VALID_REUSABLE` | política, key server-side, decisões, I/O, generations e lease | contratos e repositories | toda operação persistente recebe tenant confiável; key inclui permissions | testes unitários e integração | cache não calcula/certifica; manter atrás das flags |
| `backend/services/smart_cache_materialization/{materialization_build_service,materialization_publication_service,materialization_refresh_service,materialization_rollback_service}.py` | novo | `VALID_REUSABLE` | build Safe PG + Validation, CAS publish/refresh/rollback | Safe Analytical PG, Validation & Provenance, repository | tenant/permission explícitos | lifecycle e integração PostgreSQL | sem SQL/Oracle/OpenAI; nenhuma auto-publicação |
| `backend/services/smart_cache_materialization/{repository,garbage_collection_service,statistics_service,audit_service,__init__}.py` | novo | `VALID_REUSABLE` | persistência tenant-scoped, retenção, métricas e auditoria | ORM V21 e router | trusted tenant em toda operação pública | DB integration, GC e duas sessões | GC limitado; ativo/anterior preservados |
| `backend/models/smart_cache_materialization.py` | novo | `VALID_REQUIRES_TESTS` | 14 models ORM alinhados à V21 | repository; import condicional | tenant/FKs compostas/CAS | imports e migration DB | não carregar em `LEGACY_ONLY`; manter condicional |
| `backend/database/migration_v21_0.py` | novo | `MIGRATION_REVIEW_REQUIRED` → `VALID_REUSABLE` em teste | DDL/DML de 14 tabelas, up/down | operação manual e testes | constraints/FKs compostas | estático, up×2, down, cadeia e rollback sintético | nunca executar em produção nesta fase; sem `materialization_versions` duplicada |
| `backend/routers/smart_cache_materialization.py` | novo | `BOOTSTRAP_SAFE` | 5 operações experimentais limitadas | montagem condicional em `main.py` | JWT tenant; matriz ADMIN/GESTOR; CONSULTA deny | API/RBAC/OpenAPI tests | sem lookup/write/raw key/SQL/rows; manter admin flag false |
| `backend/tests/test_smart_cache_{contracts_and_policy,services,migration_static,migration,repository_and_materialization,router}.py` | novo | `VALID_REUSABLE` | certificação dirigida | pytest, PG descartável/fakes | matriz cross-tenant/permission | sem skip/xfail Prompt 18 | fixtures deixam schema coerente entre casos |
| `backend/tests/test_prompt18_bootstrap_isolation.py` | novo | `BOOTSTRAP_SAFE` | prova zero imports/routes/models/tasks default | subprocess import probe | flags server-side | 4 testes | proteção de regressão obrigatória |
| `backend/services/{blueprint_storage,query_intelligence_engine}.py` e `backend/tests/{conftest,test_blueprint_storage_isolation}.py` | novo/modificado | `BOOTSTRAP_SAFE` | storage/factory/policy e isolamento por worker | loaders/writers de blueprint | path não vem de payload | 11 testes + hash | elimina restore como defesa principal |
| `backend/{config,main.py,models/__init__.py,.env.test.example}` | modificado | `PROMPT18_GLOBAL_INTEGRATION` / `BOOTSTRAP_SAFE` | flags fechadas, montagem/import condicional | bootstrap | admin false/default legacy | bootstrap/OpenAPI | compatibilidade preservada; nenhum rollout |
| `frontend/types/smart_cache_materialization.ts` | novo | `VALID_REQUIRES_TESTS` | tipos de inspector futuro | componentes cache não roteados | sem dados restritos | typecheck/build/Playwright pendentes no momento deste inventário | não há página/link/request produtivo |
| `docs/contracts/smart_cache_materialization_v2/schemas/*.json` | novo gerado | `DOCUMENTATION_ONLY` | 34 JSON Schemas | integradores/testes | refletem DTOs | exporter duplo | não editar manualmente |
| `docs/contracts/smart_cache_materialization_v2/goldens/*.json` | novo gerado | `DOCUMENTATION_ONLY` | 2 cenários canônicos | eval/reprodutibilidade | sem dados empresariais | exporter duplo | somente fixtures sintéticas |
| `docs/contracts/smart_cache_materialization_v2/openapi_{legacy,experimental}.json` | novo gerado | `DOCUMENTATION_ONLY` | contrato default e experimental | integradores | legacy 0 rotas Prompt 18 | hashes idênticos em duas execuções | experimental não autoriza rollout |
| `scripts/export_v21_contracts_and_openapi.py` | novo | `VALID_REUSABLE` | exportação determinística | CI/manual | somente configuração test-only | execução dupla | sem rede, dependência ou segredo real |
| contrato, runbook, ADR 0021 e este relatório | novo | `DOCUMENTATION_ONLY` | decisão, operação e evidência | engenharia/operação | regras tenant/RBAC | revisão + links | não sobrescrevem histórico |
| `backend/services/blueprints.json` | modificado preexistente | `PROTECTED` | repositório operacional legado | runtime normal | compartilhado | hash inicial/final | byte a byte preservado pela tarefa |
| logs, scripts operacionais, `.env`, whitepapers e mudanças locais fora do escopo | preexistente | `PROTECTED` / `UNRELATED_LOCAL` | ativos do usuário | fora do Prompt 18 | n/a | hashes preservados | não incluir, restaurar ou sobrescrever |

Não foi encontrado artefato `REMOVE_BEFORE_CERTIFICATION`. A duplicação
estrutural `materialization_versions` foi removida da proposta V21: version e
lock version pertencem à definition, com snapshots/builds referenciando a
versão. Não houve remoção de arquivo histórico.

## Contratos e políticas

Todos os contratos centrais usam Pydantic v2, `extra="forbid"`, tipos fechados
e `JsonValue` em metadados. Não aceitam SQL, connection string, raw key, TTL
livre ou tenant em comandos administrativos. A eligibility rejeita partial,
truncation, stale, corruption, PII/secret/row-level, ambiguity, timeout,
cancellation e falha. Zero rows completo e certificado é elegível. TTL é
governado e limitado. Key e scope incluem tenant, permission, query/catalog/
metric/filter/period/source/watermark/compiler/tools e generations.

## Migration V21

A V21 possui 14 tabelas: seis de cache, seis de materialização e duas de
avaliação. `materialization_versions` não foi mantida por não possuir consumidor
distinto. DDL é transacional e idempotente; `run_down` exige ambiente de teste e
confirmação. Constraints cobrem tenant, checksums, TTL/lease expiry, counters e
versions não negativos/positivos, status/classification, certificação e FKs
compostas. Índices cobrem lookup, tipo/status/expiração, query/certificação,
dependency, generation, lease expiry, lifecycle/build/snapshot/publication e
eventos. Migrations V12–V20 foram protegidas por hashes estáticos.

Em PostgreSQL descartável foram aprovados: up, segundo up, inspeção de schema,
cross-tenant FK, down, cadeia V21→V12→V21 e rollback transacional em falha
sintética. Nenhuma execução ocorreu em produção, Oracle ou porta 5432.

## Serviços e cenários

Repository e API derivam tenant de contexto confiável. Lookup bloqueia stale,
expiração e checksum corrompido. Write reconstrói a key autoritativa e usa TTL
da policy. Dependency tags e generation counters suportam invalidation seletiva.
Lease por tenant+key usa owner interno, expiração, CAS e release. Single-flight
foi exercitado com 2, 10 e 100 chamadas, keys e tenants distintos e failure
recovery; duas sessões PostgreSQL provaram coordenação entre réplicas.

Build recebe definition aprovada, permission e query spec canônica, executa no
Safe Analytical PostgreSQL, valida no Validation & Provenance e cria snapshot
READY. Validation failure e watermark incremental não confiável falham
fechado. Publicação é explícita/atômica, refresh não muda o ativo, rollback
preserva histórico e cross-tenant não lê snapshot. GC tem dry-run, limite,
keyset para entries, limpa leases/entries expiradas e artefatos antigos, mas
preserva snapshot ativo e anterior.

## API, frontend e rollout

OpenAPI `LEGACY_ONLY` contém 190 paths e zero path Prompt 18. A montagem
experimental contém apenas statistics, invalidate, GC, publish e rollback;
payloads extras sensíveis falham com 422 e `CONSULTA` recebe 403. Componentes e
tipos de frontend existentes não estão ligados a página, Sidebar ou request em
produção. `LEGACY_ONLY` e admin false permanecem defaults; nenhuma migration,
write, materialização ou frontend foi ativado.

## Certificação

- Prompt 18 dirigido: 77 testes aprovados, sem skip/xfail; o lote principal
  registrou 74 passed e os três testes de frontend isolado também passaram na
  suíte completa.
- Isolamento de blueprints: 11 passed e hash inicial/final idêntico.
- API/RBAC: 9 passed; V21/repositories em lote: 9 passed.
- TENANT-001: 1 passed regular.
- Prompts 14–17 dirigidos: 64 passed, 2 warnings.
- Backend completo: 1421 passed, 1 xfailed, 0 failed, 0 errors, 0 XPASS,
  2 warnings, 1113.16 s. Único xfail: `LUMINA-GAP-DASH-001`.
- Reprodutibilidade: 47 exports dos Prompts 17/18, zero hash divergente; total
  do repositório 127 schemas JSON e 17 goldens JSON. OpenAPI default: 190 paths,
  216 operações e zero path Prompt 18.
- Frontend: ESLint exit 0 com 8 warnings preexistentes; TypeScript exit 0;
  Next build exit 0 com 23 páginas; Playwright 260 passed em 8,7 min, quatro
  viewports, exit 0.
- AST: 652 arquivos Python próprios, zero erros. Docker compose config: exit 0.
- Blueprints e todos os demais arquivos protegidos conservaram os hashes
  iniciais.

## Segurança, Git e autorização

O desenho não possui acesso Oracle/OpenAI, SQL livre armazenado, binds
sensíveis, chain of thought, dependência ou lockfile novo. Os scans encontraram
zero segredo real; a única menção a Oracle no runtime é uma docstring que
declara a proibição. O índice permaneceu vazio, sem commit/tag/push produzido
pela tarefa. A certificação técnica autoriza preparar o checkpoint dos Prompts
14–18 em tarefa posterior, após revisão humana do diff; este relatório não cria
checkpoint e não autoriza rollout.
