# Auditoria Do Estado Atual - LuminaAI

Data da auditoria: 2026-07-27.

Escopo: inspecao estatica completa do repositorio, validacoes locais
nao destrutivas e documentacao do estado as-is. Nenhuma funcionalidade foi
alterada.

Atualizacoes posteriores: o Prompt 03 implementou os Contratos Analiticos V2,
o Prompt 04 implementou `lumina.temporal.pt-BR/1.0`, o Prompt 05 implementou
`lumina.comparison-planner/1.0` e o Prompt 06 implementou
`lumina.comparison-executor/1.0`. Consulte os relatorios correspondentes em
`docs/audit/`. O baseline atual coleta 970 testes e preserva 4 xfails
estritos; esta fotografia inicial permanece preservada para rastreabilidade.

## 1. Metodo e classificacao de evidencias

Precedencia usada:

1. Codigo executado e entrypoints.
2. Configuracao de runtime.
3. Models, SQL e scripts de migracao.
4. Testes.
5. Scripts operacionais.
6. Documentacao existente.

Classificacoes:

- **Confirmado pelo codigo**: simbolo e caminho inspecionados.
- **Confirmado por configuracao**: script, Dockerfile ou config executavel.
- **Confirmado por teste**: teste existe ou validacao foi executada.
- **Documentado, nao confirmado**: afirmacao sem evidencia executavel suficiente.
- **Parcial**: existe, mas nao cobre integralmente o contrato descrito.
- **Necessita runtime**: nao foi validado sem acessar servicos ou dados externos.

## 2. Estado inicial do Git

O worktree ja possuia alteracoes antes da auditoria:

```text
M backend/.env
M backend/config.py
M runtime-logs/backend-network.err.log
M runtime-logs/backend-network.out.log
M runtime-logs/frontend-network.err.log
M runtime-logs/frontend-network.out.log
M start-luminaai.ps1
M stop-luminaai.ps1
?? .env.local
?? LUMINA_AI_SYSTEM_SPECIFICATION_FOR_AI.md
?? LUMINA_AI_ULTIMATE_ENTERPRISE_SPECIFICATION.md
?? docs/LUMINA_AI_SYSTEM_SPECIFICATION_FOR_AI.md
?? docs/LUMINA_AI_ULTIMATE_ENTERPRISE_SPECIFICATION.md
?? iniciar_luminaai_servidor.bat
?? instalar_luminaai_servidor.bat
?? monitor_luminaai_servidor.bat
?? parar_luminaai_servidor.bat
?? scripts/deploy_helper.ps1
?? scripts/setup_env_keys.py
```

Esses arquivos foram tratados como trabalho preexistente e preservados.

## 3. Inventario confiavel

### 3.1 Organizacao

O repositorio e um monorepo sem ferramenta formal de workspace:

- Backend Python em `backend/`.
- Frontend Node/TypeScript em `frontend/`.
- Documentacao em `docs/`.
- Scripts operacionais em `scripts/` e raiz.
- Logs e payloads em `runtime-logs/`.

Foram encontrados 289 arquivos Python proprios fora de ambientes virtuais, 52
arquivos TSX, 27 TS, 52 Markdown e 77 JSON no inventario fisico.

### 3.2 Runtimes e dependencias

| Item | Evidencia | Estado |
| --- | --- | --- |
| Python local | `python --version` | 3.12.10 |
| Python backend | `backend/Dockerfile` | 3.12 |
| Node local | `node --version` | 24.15.0 |
| Node container | `frontend/Dockerfile` | 20 Alpine |
| npm local | `npm --version` | 11.12.1 |
| Backend deps | `backend/requirements.txt` | versoes fixas |
| Frontend deps | `frontend/package.json` | Next 16.2.10, React 19.2.4 |
| Lock Python | busca no repositorio | ausente |
| Lock frontend | `frontend/package-lock.json` | presente |

### 3.3 Entry points

- FastAPI: `backend/main.py:154`, objeto `app`.
- Lifespan: `backend/main.py:80`.
- Backend Docker: Gunicorn + Uvicorn em `0.0.0.0:8000`.
- Next App Router: `frontend/app/layout.tsx` e rotas sob `frontend/app/`.
- Operacao Windows: `start-luminaai.ps1`, frontend 3002/backend 8000.
- Docker operacional: frontend 3000; Playwright isolado: frontend 3100.

### 3.4 Banco e schema

- ORM: SQLAlchemy async em `backend/database.py`.
- Banco corporativo: `settings.DATABASE_URL`, PostgreSQL/asyncpg.
- Clone analitico: PostgreSQL, resolvido por tenant.
- Oracle: origem ERP em `backend/services/oracle_service.py`.
- SQLite: nao foi encontrado em codigo proprio de runtime.
- Schema inicial: `backend/database/init.sql`.
- Evolucao: `backend/database/migration_v4_1.py` ate `migration_v11_0.py`.
- Alembic: ausente.
- Startup chama `Base.metadata.create_all` em `backend/main.py:104`.

Tabelas ORM confirmadas incluem tenants, users, view catalog, historico,
favoritos, blueprints, metadata/semantic catalogs, datasets, sync queue,
memoria semantica, pacotes, preferencias e estruturas do Dashboard Studio/SVR.

### 3.5 Variaveis de ambiente identificadas

Somente nomes, sem valores:

- Aplicacao: `APP_NAME`, `APP_DESCRIPTION`, `APP_VERSION`, `ENVIRONMENT`,
  `DEBUG`.
- Banco: `DATABASE_URL`, `DB_ECHO`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`,
  `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE`.
- Auth/criptografia: `SECRET_KEY`, `ALGORITHM`,
  `ACCESS_TOKEN_EXPIRE_MINUTES`, `ENCRYPTION_KEY`.
- IA: `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_TEMPERATURE`,
  `OPENAI_MAX_TOKENS`, `OPENAI_TIMEOUT`.
- Pipeline: `NEW_PIPELINE_ACTIVE`, `ENABLE_DETERMINISTIC_PIPELINE`.
- ERP: `MOCK_ORACLE`.
- CORS: `CORS_ORIGINS`, `CORS_ALLOW_ORIGIN_REGEX`,
  `CORS_ALLOW_CREDENTIALS`, `CORS_ALLOW_METHODS`, `CORS_ALLOW_HEADERS`.
- Frontend: `NEXT_PUBLIC_API_URL`.
- Testes/carga: `PLAYWRIGHT_BASE_URL`, `LUMINA_BASE_URL`,
  `LUMINA_LOAD_PATH`, `LUMINA_LOAD_REQUESTS`, `LUMINA_LOAD_CONCURRENCY`,
  `LUMINA_LOAD_TIMEOUT_MS`.

## 4. Backend as-is

### 4.1 Routers

| Dominio | Caminho | Protecao principal |
| --- | --- | --- |
| Auth | `backend/routers/auth.py` | login publico; sessao JWT |
| Query | `backend/routers/query.py` | usuario + troca de senha |
| Usuarios | `backend/routers/users.py` | ADMIN |
| Tenant/sync/config | `backend/routers/tenant.py` | ADMIN |
| Catalogo de views | `backend/routers/catalog.py` | ADMIN/GESTOR |
| Metadata Catalog | `backend/routers/metadata_catalog.py` | autenticado |
| Dashboard | `backend/routers/dashboard.py` | autenticado |
| Preferencias | `backend/routers/dashboard_preferences.py` | autenticado |
| Dashboard Studio | `backend/routers/dashboard_studio.py` | ADMIN/GESTOR |
| SVR | `backend/routers/svr.py` | ADMIN |
| Business Knowledge | `backend/routers/business_knowledge.py` | autenticado |
| Analytical Packages | `backend/routers/analytical_packages.py` | autenticado |

O backend registra uma rota duplicada de compatibilidade em
`/api/v1/api/v1/query` (`backend/main.py:374-380`).

### 4.2 Autenticacao e RBAC

- JWT PyJWT e hash bcrypt/passlib: `backend/services/auth_service.py`.
- Token aceito via OAuth2 bearer/cookie conforme `authSession` e dependencias.
- Cookie de auth e HttpOnly em `backend/routers/auth.py`.
- JWT inclui `sub`, `tenant_id`, role e requisito de troca de senha.
- `get_current_user` carrega usuario por `id` e `tenant_id`.
- Roles reais: `ADMIN`, `GESTOR`, `CONSULTA` em `backend/models/user.py`.
- O frontend decodifica o JWT para navegacao, mas a API e a autoridade final.

### 4.3 Consulta

Fronteira HTTP: `processar_consulta` em `backend/routers/query.py:187`.

O endpoint:

1. Compara tenant autenticado e tenant do payload.
2. Carrega views ativas do tenant.
3. Carrega configuracao nao sensivel do tenant.
4. Seleciona pipeline novo ou legado por flags/payload.
5. Aplica governanca de resposta.

Pipeline novo:

- `NewQueryOrchestrator.run_pipeline`, linha 2251.
- Caminho deterministico para perguntas comerciais criticas. Esse caminho usa
  `get_db_context()` e consulta `vw_vendas_lm` pela `DATABASE_URL` principal;
  nao abre explicitamente o clone configurado no tenant.
- Intent engine para perguntas genericas.
- `SemanticCanonicalizer`.
- `MetadataResolver`.
- `QueryOptimizer` e `SQLGenerator`.
- `SecurityValidator`.
- `DatabaseExecutor` no clone PostgreSQL.
- Explainability via IA.
- `transform_data`.
- persistencia do grafo e payload visual.

Pipeline legado:

- `QueryIntelligenceEngine.process_query` em
  `backend/services/query_intelligence_engine.py:1436`.
- Mantido por compatibilidade quando as flags do novo pipeline estao desligadas.

### 4.4 IA

Pontos confirmados:

- Intent novo: `backend/services/metadata_catalog/intent_engine.py:143`.
- Explainability: `backend/services/metadata_catalog/explainability.py:51`.
- Explicacao de dataset local: mesmo arquivo, linha 114.
- Engines legadas/modulares em `backend/services/ai/`.
- Credenciais/clientes: `ai_credential_manager.py`.
- Governanca/retries/circuit breaker: `ai_invocation_manager.py`.

Dados enviados:

- Intent recebe catalogo conceitual, pergunta e ate seis mensagens recentes.
- Explainability recebe pergunta, objetivo e ate 50 linhas do dataset.
- O prompt novo de intent nao recebe schema fisico nem SQL.
- A IA pode redigir numeros presentes no dataset; a fonte numerica e o executor.

### 4.5 Contexto conversacional

- Frontend mantem `sessionId`, mensagens e `parent_id` em
  `frontend/hooks/useLuminaQuery.ts`.
- Backend herda periodo/metrica/dimensao/filial pelo historico no orquestrador.
- Grafo e persistido em memoria e JSON local por
  `metadata_catalog/conversation_graph.py`.
- `SearchHistory` persiste pergunta e parametros no PostgreSQL.
- `SemanticMemory` persiste resolucoes semanticas por tenant.

O grafo JSON nao e um estado distribuido; nao ha evidencia de lock
interprocesso, TTL, criptografia ou escopo de usuario embutido no nome da sessao.

### 4.6 Cache

- Cache global por tenant/namespace: `backend/services/cache_service.py`.
- Cache de executor usa `plan.cache_key + tenant_id`.
- Live dashboard e packages possuem caches proprios.
- Invalidacao ocorre no sync por padrao e view.
- Nao foi confirmada coordenacao distribuida entre multiplos workers.

## 5. Dados, sync e reconciliacao

### 5.1 Fronteiras

```text
Oracle ERP
  -> SyncEngine / sync_service
  -> staging PostgreSQL
  -> validacao e troca da tabela
  -> clone analitico PostgreSQL do tenant
  -> query/executor
  -> API/frontend
```

O `SyncEngine` declara ser o componente autorizado a acessar Oracle. Na pratica,
`daily_reconciliation.py`, scripts administrativos e `oracle_service.py` tambem
podem abrir Oracle para funcoes tecnicas. O caminho de consulta novo executa no
PostgreSQL, mas ha duas conexoes: o caminho generico abre o banco clone do
tenant; core summaries usam a sessao corporativa principal.

### 5.2 Incremental

`backend/services/data_platform/sync_engine.py`:

- lock por tenant;
- descoberta de coluna incremental;
- overlap temporal;
- copia base para staging;
- remocao do intervalo sobreposto;
- leitura Oracle em lotes;
- insercao com retry;
- validacao;
- substituicao da tabela;
- persistencia de versao e eventos.

Necessita runtime: atomicidade completa da troca, privilegios reais, volume,
indices no clone e resultado com dados produtivos.

### 5.3 Reconciliacao e scheduler

- Scheduler em `backend/services/scheduler.py`.
- Orquestrador em `data_platform/sync_scheduler.py`.
- Reconciliacao diaria em `daily_reconciliation.py`.
- Comparacao ERP/clone em `erp_reconciliation.py`.
- Scheduler reinicia apos falha inesperada.
- `/health/deep` reporta API, IA, PostgreSQL e scheduler.

## 6. Frontend as-is

### 6.1 Rotas

- `/login`
- `/auth/first-access`
- `/dashboard`
- `/dashboard/admin/catalog`
- `/dashboard/admin/settings`
- `/dashboard/admin/users`
- `/dashboard/inspector`
- `/dashboard/studio`
- `/dashboard/svr`
- `/healthz`

`frontend/proxy.ts` protege navegacao por cookie, expiracao, troca de senha e
role. Isso nao valida assinatura JWT; serve como guarda de UX. O backend valida.

### 6.2 Estado e transporte

- `AuthContext`: sessao por cookie e `/auth/session`.
- `useLuminaQuery`: mensagens, historico, favoritos, preferencias, grafo e modo.
- Requisicoes usam `credentials: 'include'`.
- `getApiBase()` preserva loopback e resolve host LAN para porta 8000.
- Nao ha React Query ou SWR.
- Estado principal usa hooks/context e reducers locais.
- Tema claro/escuro persiste em localStorage.

### 6.3 Renderizacao

- `DynamicRenderer.tsx` e o dispatcher principal.
- ECharts: KPI, bar, line, area, pie, scatter, heatmap, treemap e funnel.
- Tabelas com exportacao CSV.
- Recharts permanece declarado e componentes antigos ainda existem.
- Payload aceita visualizacoes multiplas.
- Runtime de dashboard adapta resposta legada para contrato mais rico.
- Ha filtros cruzados, fullscreen, virtualizacao e Trust Center.

### 6.4 Testes frontend

Playwright possui um arquivo de especificacao com quatro testes executados em
quatro projetos/viewports, resultando em ate 16 casos. A API e simulada por
`page.route`; nao e E2E real com backend ou banco.

## 7. Infraestrutura

| Contexto | Frontend | Backend | Evidencia |
| --- | ---: | ---: | --- |
| Windows operacional | 3002 | 8000 | scripts raiz/BAT |
| Docker interno | 3000 | 8000 | Dockerfiles/Compose |
| Playwright | 3100 | API simulada | config/teste |
| npm dev sem argumento | 3000 | n/a | Next default |

Portas 3000, 3001, 3002, 3333 e 8000 sao recusadas pelo Playwright. O Docker
operacional continua com seu contexto interno proprio.

- CORS inclui loopback/LAN e portas 3000/3001/3002/5173.
- Nginx expoe 80/443 e encaminha frontend:3000/backend:8000.
- Docker Compose nao publica frontend/backend diretamente; usa `expose`.
- Logs Windows ficam em `runtime-logs/`.
- Nao foi encontrada CI/CD versionada.
- Backup shell existe em `scripts/backup-db.sh`.
- Rollback de deploy e descrito, mas nao ha pipeline automatizado confirmado.

## 8. Validacoes executadas

| Comando | Resultado |
| --- | --- |
| `git status --short` | worktree preexistente sujo registrado |
| inventario com `rg --files` | estrutura e extensoes levantadas |
| versoes Python/Node/npm | executado |
| parsing AST proprio | 289 arquivos, 0 erros |
| `npm run lint` | aprovado: 0 erros, 0 avisos |
| `npx tsc --noEmit` | aprovado |
| `npm run build` | aprovado; 15 paginas geradas |
| pytest seguro | 497 passed, 13 xfailed estritos |
| Playwright visual | 16 passed na porta 3100 |
| varredura de segredos sem imprimir conteudo | 43 arquivos candidatos |

Nao executados:

- load smoke: requer servico na porta 8000.
- health scripts: acessam OpenAI, Oracle e PostgreSQL.
- sync/reconciliation: acessam Oracle e escrevem no clone.
- migrations/init: escrevem schema.
- Docker: nao necessario para auditoria estatica.

## 9. Riscos

### Criticos

1. **Segredos e logs versionados.** `backend/.env`, um arquivo de credenciais de
   clone e 69 arquivos em `runtime-logs/` estao rastreados. A varredura
   encontrou 43 arquivos candidatos a conter segredos/credenciais hardcoded.
2. **Potencial mistura entre tenants no caminho deterministico.** Core summaries
   usam `get_db_context()` e SQL sobre `vw_vendas_lm` sem `tenant_id`. O codigo
   nao comprova que essa view/base e exclusiva do tenant autenticado. Necessita
   validacao imediata do deployment e bloqueio por arquitetura.

O risco anterior de pytest escrever em `DATABASE_URL` foi corrigido por guarda
fail-closed, `TEST_DATABASE_URL` obrigatoria e PostgreSQL descartavel. Evidencia:
`docs/audit/TEST_BASELINE.md`.

### Altos

1. **Dados empresariais enviados ao provedor de IA.** Ate 50 linhas entram no
   prompt de explicabilidade.
2. **RBAC insuficiente em governanca.** Usuarios autenticados podem registrar
   conceitos/KPIs, executar rollback/seed e deprecar packages.
3. **Schema alterado no startup.** `create_all` roda ao iniciar a API.
4. **Persistencia conversacional local.** JSON/RAM nao suporta replicas, TTL,
   criptografia ou coordenacao.
5. **Fallback semantico perigoso.** Falha da IA pode virar listagem de Cliente,
   mudando silenciosamente a entidade.

### Medios

1. Dois pipelines coexistem e aumentam divergencia comportamental.
2. Bloco de inicializacao/debug esta duplicado em `run_pipeline`.
3. Logs de debug gravam payload final, SQL, binds e amostras de linhas.
4. Cache em memoria nao e compartilhado entre workers.
5. SQLGenerator concatena identificadores; binds protegem valores, nao nomes.
6. `EXPLAIN ANALYZE` reexecuta consultas apos a execucao normal.
7. Nao ha Alembic nem historico central de migrations.
8. `backend/venv` e artefatos/relatorios amplificam o repositorio.

### Baixos/informativos

1. Comentarios e strings possuem mojibake em varios arquivos.
2. Recharts e ECharts coexistem.
3. Nao ha CI/CD versionada.
4. Nao foi encontrada logica de precificacao comercial/SaaS no runtime; valores
   monetarios encontrados representam dados de BI.

## 10. Limites da auditoria

- Nenhuma conexao externa foi aberta.
- Nenhum dado real foi consultado.
- Nenhum schema/indice/permissao foi confirmado no servidor PostgreSQL/Oracle.
- Nao foi possivel confirmar RLS nativo, usuario read-only ou atomicidade sob
  falha sem runtime.
- Logs versionados foram inventariados, mas o conteudo integral nao foi
  incorporado a auditoria para evitar nova exposicao de tokens, payloads e
  dados empresariais.
- O repositorio contem arquivos nao rastreados de especificacao; foram lidos
  apenas como documentacao secundaria.

Proxima etapa recomendada: executar o Prompt 07, renderizacao de resultados
comparativos, consumindo o resultado validado sem mover calculo numerico para
o frontend.
