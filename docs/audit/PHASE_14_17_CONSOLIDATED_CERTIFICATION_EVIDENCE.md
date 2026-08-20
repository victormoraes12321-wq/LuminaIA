# Evidência de Certificação Consolidada — Prompts 14–17

Data: 2026-08-04T10:29:46-03:00

Classificação: `CONSOLIDATED_REVALIDATION`

## Identidade do worktree

- Branch: `codex/phase-ai-orchestration-prompts-14-18`.
- HEAD: `c5d7621f2b7b3c4c0138a704685ac048515f49db`.
- Arquivos rastreados modificados: 21.
- Arquivos não rastreados: 195.
- Arquivos não rastreados no manifesto permitido: 182.
- Hash Git do diff rastreado: `c1195ce3e0cf3be9a28f0e1f4d6baeb529ee91b1`.
- SHA-256 agregado do manifesto não rastreado permitido:
  `598d95dd1a2bfe3127d649b14ff497e9c030cffacd4e43cb232c7a730cf2c617`.
- Índice Git vazio; nenhum commit, tag ou push foi criado.

O fingerprint acima foi coletado imediatamente antes da reconciliação
documental desta certificação; por definição, não inclui a própria escrita dos
relatórios e ledgers. Ele não certifica isoladamente os artefatos funcionais
preexistentes do Prompt 18.

## Reparo de bootstrap do Prompt 18

A falha original era `database.connection`, package inexistente porque a
autoridade ORM real é `backend/database.py`. O padrão certificado dos models é
`from database import Base`.

Reparos mínimos:

- import de `Base` corrigido no model preexistente;
- import de `get_db` corrigido no router preexistente;
- imports de typing ausentes corrigidos em dois services;
- model Prompt 18 removido do export global de `models`, sem apagar o arquivo;
- router removido do import global de `main`;
- inclusão condicionada a modo diferente de `LEGACY_ONLY` e
  `SMART_CACHE_ADMIN_ENABLED=true`;
- modo validado contra allowlist server-controlled;
- migration v21 nunca importada ou executada.

Em `LEGACY_ONLY`, nenhum módulo, tabela, rota, service ou task do Prompt 18 é
carregado. Quatro testes subprocessados de bootstrap passaram em 18,91 s.

## Inventário preexistente do Prompt 18

Nenhum item abaixo é certificado funcionalmente.

### `PROMPT18_GLOBAL_INTEGRATION`

- `backend/config.py` — flags fail-closed; validação de modo adicionada.
- `backend/main.py` — integração global; convertida em inclusão condicional.
- `backend/models/__init__.py` — export global prematuro removido.

### `PROMPT18_BOOTSTRAP_BLOCKER`

- `backend/models/smart_cache_materialization.py` — import ORM corrigido.
- `backend/routers/smart_cache_materialization.py` — import de sessão corrigido;
  rotas continuam experimentais e desativadas.
- `backend/services/smart_cache_materialization/repository.py` — `Tuple`
  ausente corrigido apenas para importabilidade.
- `backend/services/smart_cache_materialization/materialization_build_service.py`
  — `Tuple` ausente corrigido apenas para importabilidade.

### `PREEXISTING_PROMPT18_CANDIDATE`

- Contracts: `backend/contracts/smart_cache_materialization_v2/__init__.py`,
  `entries.py`, `evaluations.py`, `execution_audit.py`, `identity.py`,
  `materialization.py`, `policy.py` e `scope_key.py`.
- Services: `backend/services/smart_cache_materialization/__init__.py`,
  `audit_service.py`, `eligibility_engine.py`, `garbage_collection_service.py`,
  `invalidation_service.py`, `key_builder.py`, `lookup_service.py`,
  `materialization_publication_service.py`,
  `materialization_refresh_service.py`, `materialization_rollback_service.py`,
  `pipeline.py`, `policy_service.py`, `single_flight.py`,
  `statistics_service.py` e `write_service.py`.
- Frontend: `frontend/types/smart_cache_materialization.ts`,
  `frontend/components/cache/CacheInspector.tsx` e
  `frontend/components/cache/MaterializationInspector.tsx`.

### `NEEDS_MANUAL_REVIEW`

- `backend/database/migration_v21_0.py` — não importada, não executada e não
  certificada; ainda referencia infraestrutura inexistente.
- Todos os contracts, services, router e componentes acima requerem auditoria
  funcional integral no Prompt 18 retomado.

Não havia documentação, ADR 0021, página frontend ou testes funcionais
preexistentes do Prompt 18. O teste de isolamento criado nesta certificação é
`backend/tests/test_prompt18_bootstrap_isolation.py`.

## Pytest

- Coleta: 1.349 testes, zero erros, 2 warnings, 6,40 s.
- Bootstrap Prompt 18: 4 passed, 18,91 s.
- TENANT-001: 1 passed, 2,74 s; teste regular
  `test_core_summary_breakdown_does_not_mix_tenants`.
- Prompt 14: 17 passed, 2 warnings, 34,90 s.
- Prompt 15: 250 passed, 2 warnings, 13,93 s.
- Prompt 16: 20 passed, 2 warnings, 26,90 s.
- Prompt 17: 17 passed, 18,61 s.
- Backend completo: 1.348 passed, 1 xfailed, 0 failed, 0 XPASS,
  2 warnings, 1.248,40 s.
- Único xfail: `LUMINA-GAP-DASH-001`.
- Não há marker xfail ou skip para `LUMINA-GAP-TENANT-001`.

## Migrations

- Cadeia down: v20, v19, v18, v17, v16, v15, v14, v13 — sucesso.
- Cadeia up: v13, v14, v15, v16, v17, v18, v19, v20 — sucesso.
- v17, v18, v19 e v20 executadas duas vezes após a cadeia: idempotentes.
- Schema final: 33 tabelas da fase, 488 constraints e 379 índices públicos no
  banco sintético completo.
- Tabelas `smart_cache_*`/`materialization_*`: zero.
- Migration v21: não executada.
- `create_all` não substituiu a cadeia de migrations.

## AST e artefatos reproduzíveis

- Python descobertos por `rg`: 2.794.
- Analisados como código próprio: 641.
- Excluídos: 2.153 em `.venv`, `venv`, dependências, caches e builds.
- `ast.parse` sobre bytes, respeitando BOM/coding cookie: zero erros.
- Schemas JSON existentes: 93; Prompt 17 exporta 6 oficialmente.
- SHA-256 agregado dos schemas existentes:
  `f2561ac639e85ed21e13c74f56d1ad93ec90cbcccad87c9d8f540cb789094ada`.
- Goldens JSON existentes: 13; Prompt 17 exporta 2 oficialmente.
- SHA-256 agregado dos goldens:
  `3058d508844c15796d8d3316a983675f1ea6afeea229ca7780e1ece332034ba9`.
- Exporter oficial executou schemas, goldens e OpenAPI duas vezes, com zero
  diferenças.
- OpenAPI: 190 paths e 216 operações.
- Paths 14/15/16/17: 9/3/6/2; Prompt 18 em `LEGACY_ONLY`: zero.
- OpenAPI SHA-256 lógico:
  `cec948f1b6a9ddcec538eea7a6fd5615905dc03967752aa70cdd351431c02552`.

Não existe exporter global por componente para schemas/goldens dos Prompts
14–16. A limitação é preservada; contratos foram cobertos pelos testes
direcionados e os manifestos globais existentes ficaram estáveis.

## Frontend

- ESLint: exit code 0, zero erros e 8 warnings preexistentes.
- TypeScript `--noEmit`: aprovado.
- Next.js 16.2.10 build: aprovado; 23 páginas geradas e 21 rotas listadas.
- Nenhuma página/rota de cache ou materialização foi publicada.
- Playwright: 260 passed, zero failed/skipped, quatro viewports, 15,6 min,
  exit code 0, porta isolada 3100.

## Segurança e ambiente

- Runner: `ENVIRONMENT=test`, `LUMINA_TESTING=true`, mocks de Oracle/OpenAI e
  bloqueio de rede externa.
- Banco: PostgreSQL 16 descartável em `127.0.0.1:55432/luminaai_test`.
- OpenAI real: zero acessos.
- Oracle runtime: zero acessos.
- Banco operacional/porta 5432: zero acessos.
- Dependências e `frontend/package-lock.json`: sem diff contra HEAD.
- Varredura de 195 arquivos permitidos: zero segredo real; somente
  placeholders sintéticos, exemplo documental e teste negativo.
- Docker Compose test config: válido; único service `lumina-test-postgres`.

### Integridade dos arquivos protegidos

Os hashes finais coincidem com os hashes registrados antes da execução:

- `backend/.env`: `01FF60D7E15E1EF7A9A18BF0C01CC4B9798BCD8A1517C43108EF2D6A770E7AE5`;
- `backend/services/blueprints.json`: `407D5C65B7A38A805C073F064A0C1CD9AF6290C8BCBE18809CA645CD81042596`;
- `runtime-logs/backend-network.err.log`: `C0E72D3674D6512C49AC4FA6B88F09B02F6531A401A76BDFE04573E977B4B3D0`;
- `start-luminaai.ps1`: `2794010E8062A4F52EFB2BF2DB174A20B7573FB698DE8479B1892CB96E51FFA1`;
- `stop-luminaai.ps1`: `BED91DF197F12C9CF1D7DEA13E8A25378ACEAF3FDDFCE4E1544C7A77B2FF620F`;
- `scripts/deploy_helper.ps1`: `EF798AB74F38C98574CB34438C4C2C03DE8870FF28E02C6120EB18D9244909F3`;
- `scripts/setup_env_keys.py`: `85F23189853D6064382F97C203DC4EF0E3916AE934A1322F61F5AFB4AAD704EA`.

A suíte legada completa gravou temporariamente métricas e seis blueprints
sintéticos em `blueprints.json`. O efeito foi detectado pela comparação de
hashes e removido mecanicamente; o arquivo terminou byte a byte no hash
inicial. Isso evidencia uma dívida de isolamento dos testes legados, sem
alteração residual no arquivo protegido.

## Comandos principais

- coleta pytest e busca estática de markers;
- runner seguro para TENANT-001, Prompts 14–17 e backend completo;
- cadeia de migrations e idempotência;
- AST com exclusões explícitas;
- exporter v20 em dupla execução;
- `npm run lint`, `npx tsc --noEmit`, `npm run build`, `npm run test:visual`;
- auditorias Git, dependências, lockfiles, segredos, guards e OpenAPI.

## Limitações

- Artefatos funcionais do Prompt 18 permanecem não certificados.
- Migration v21 permanece bloqueada e requer reparo próprio futuro.
- Warnings ESLint e Pydantic foram preservados e não mascarados.
- O `git diff --check` global continua afetado exclusivamente por whitespace
  preexistente no log protegido; o escopo autorizado é validado separadamente.
