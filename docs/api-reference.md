# API Reference - LuminaAI

Fonte: gerado a partir do schema OpenAPI exposto por `backend/main.py`.

## Estado Conversacional V2

`QueryRequest` aceita `client_message_id` e `expected_context_version`.
`QueryResponse` devolve sessao, nos, parent, versao, epoch, status e replay
quando a persistencia PostgreSQL esta habilitada.

As rotas autenticadas `/api/v1/conversations` criam, listam, consultam,
resetam, arquivam, reabrem e excluem sessoes do proprio usuario. Tenant e
usuario sempre vem do token. Listagens usam cursor keyset e limites fixos.

Importacao JSON e uma operacao offline. Ela permanece em dry-run por padrao e
o apply exige `CONVERSATION_LEGACY_IMPORT_ENABLED=true`.

## Execucao Comparativa V2

O Prompt 06 nao adiciona rota publica. Perguntas comparativas continuam pela
rota de consulta existente. Quando o planner produz `QueryPlanV2` `READY` e
`COMPARISON_EXECUTOR_V2_ENABLED=true`, o orquestrador chama
`lumina.comparison-executor/1.0`.

O payload V1 permanece compativel e recebe `analytical_contract`. No contrato
V2, `contract.extensions.comparison_executor` informa versao, estrategia,
cache, partial, summaries de alinhamento, contagem de calculos, denominadores
zero, nao aplicaveis, validacao e proveniencia. SQL e binds nunca fazem parte
da API.

Observacoes:

- A autenticacao principal usa JWT emitido pelo backend e enviado por cookie HttpOnly e/ou Bearer token conforme fluxo atual.
- Rotas sob `/api/v1/api/v1/query` existem por compatibilidade com clientes antigos que duplicavam o prefixo no `base_url`.
- Campos exatos de payload/resposta seguem os DTOs em `backend/schemas` e o schema OpenAPI.
- `POST /api/v1/query/` retorna `data_status`, `validation_summary` e `interaction_options`. `admin_diagnostics` e preenchido somente para `ADMIN`.
- `POST /api/v1/query/` pode retornar o campo opcional
  `analytical_contract` com schema `lumina.analytics/2.0`. O campo e aditivo,
  controlado por feature flags e nao e obrigatorio para clientes V1.
- O sidecar distingue `READY`, `CLARIFICATION_REQUIRED`, `OUT_OF_SCOPE`,
  `UNSUPPORTED`, `BLOCKED` e `ERROR`, preserva listas de periodos e
  visualizacoes e deriva tenant do contexto autenticado.
- Rotas de Inspector, SVR, cache, performance e seguranca exigem `ADMIN`. Dashboard Studio exige `ADMIN` ou `GESTOR`.
- A fonte de consulta da IA e o PostgreSQL analitico; referencias ao Oracle na linhagem representam somente o processo tecnico anterior de sincronizacao.

| Metodo | Endpoint | Tag | Objetivo | Autenticacao |
| --- | --- | --- | --- | --- |
| `GET` | `/api/v1/analytical-packages` | Analytical Packages | Listar Analytical Packages | JWT/Depends |
| `GET` | `/api/v1/analytical-packages/stats` | Analytical Packages | Metricas globais de Analytical Packages | JWT/Depends |
| `GET` | `/api/v1/analytical-packages/{package_id}` | Analytical Packages | Detalhe de um Analytical Package | JWT/Depends |
| `POST` | `/api/v1/analytical-packages/{package_id}/deprecate` | Analytical Packages | Deprecar um Analytical Package manualmente | JWT/Depends |
| `GET` | `/api/v1/analytical-packages/{package_id}/instances` | Analytical Packages | Historico de execucoes de um Package | JWT/Depends |
| `POST` | `/api/v1/auth/change-password` |  Autenticacao | Alteracao de Senha Obrigatoria | JWT/Depends |
| `POST` | `/api/v1/auth/login` |  Autenticacao | Login de Usuario | Publica ou sessao |
| `POST` | `/api/v1/auth/logout` |  Autenticacao | Encerrar sessao | JWT/Depends |
| `GET` | `/api/v1/auth/session` |  Autenticacao | Sessao autenticada | JWT/Depends |
| `GET` | `/api/v1/business-knowledge/dictionary` | Business Knowledge Engine | Listar conceitos do dicionario | JWT/Depends |
| `POST` | `/api/v1/business-knowledge/dictionary` | Business Knowledge Engine | Registrar/Atualizar conceito de negocio | JWT/Depends |
| `GET` | `/api/v1/business-knowledge/formulas` | Business Knowledge Engine | Listar formulas de BI | JWT/Depends |
| `GET` | `/api/v1/business-knowledge/impact` | Business Knowledge Engine | Analise de impacto de dependencia | JWT/Depends |
| `GET` | `/api/v1/business-knowledge/kpis` | Business Knowledge Engine | Listar KPIs registrados | JWT/Depends |
| `POST` | `/api/v1/business-knowledge/kpis` | Business Knowledge Engine | Registrar/Atualizar KPI oficial | JWT/Depends |
| `GET` | `/api/v1/business-knowledge/observability` | Business Knowledge Engine | Metricas de observabilidade do BKE | JWT/Depends |
| `POST` | `/api/v1/business-knowledge/rollback` | Business Knowledge Engine | Executar rollback de versao | JWT/Depends |
| `POST` | `/api/v1/business-knowledge/seed` | Business Knowledge Engine | Semear formulas e relacoes de BI padrao | JWT/Depends |
| `GET` | `/api/v1/catalog/` |  Catalogo de Views | Listar Todas as Views do Catalogo (Admin/Gestor-Only) | JWT/Depends |
| `POST` | `/api/v1/catalog/` |  Catalogo de Views | Cadastrar Nova View no Catalogo (Admin/Gestor-Only) | JWT/Depends |
| `DELETE` | `/api/v1/catalog/{view_id}` |  Catalogo de Views | Deletar View do Catalogo (Admin/Gestor-Only) | JWT/Depends |
| `PUT` | `/api/v1/catalog/{view_id}` |  Catalogo de Views | Atualizar View do Catalogo (Admin/Gestor-Only) | JWT/Depends |
| `POST` | `/api/v1/dashboard-studio/import` | Dashboard Studio | Import Layout | JWT/Depends |
| `GET` | `/api/v1/dashboard-studio/instances` | Dashboard Studio | List Instances | JWT/Depends |
| `POST` | `/api/v1/dashboard-studio/instances` | Dashboard Studio | Create Instance | JWT/Depends |
| `GET` | `/api/v1/dashboard-studio/instances/{instance_id}` | Dashboard Studio | Get Instance | JWT/Depends |
| `PATCH` | `/api/v1/dashboard-studio/instances/{instance_id}` | Dashboard Studio | Update Instance | JWT/Depends |
| `POST` | `/api/v1/dashboard-studio/instances/{instance_id}/duplicate` | Dashboard Studio | Duplicate Instance | JWT/Depends |
| `GET` | `/api/v1/dashboard-studio/instances/{instance_id}/export` | Dashboard Studio | Export Instance | JWT/Depends |
| `POST` | `/api/v1/dashboard-studio/instances/{instance_id}/favorite` | Dashboard Studio | Set Favorite | JWT/Depends |
| `GET` | `/api/v1/dashboard-studio/instances/{instance_id}/versions` | Dashboard Studio | List Instance Versions | JWT/Depends |
| `POST` | `/api/v1/dashboard-studio/instances/{instance_id}/versions/{version}/rollback` | Dashboard Studio | Rollback Instance | JWT/Depends |
| `GET` | `/api/v1/dashboard-studio/templates` | Dashboard Studio | List Templates | JWT/Depends |
| `POST` | `/api/v1/dashboard-studio/templates` | Dashboard Studio | Create Template | JWT/Depends |
| `GET` | `/api/v1/dashboard-studio/templates/{template_id}` | Dashboard Studio | Get Template | JWT/Depends |
| `PATCH` | `/api/v1/dashboard-studio/templates/{template_id}` | Dashboard Studio | Update Template | JWT/Depends |
| `GET` | `/api/v1/dashboard-studio/templates/{template_id}/export` | Dashboard Studio | Export Template | JWT/Depends |
| `GET` | `/api/v1/dashboard-studio/templates/{template_id}/versions` | Dashboard Studio | List Template Versions | JWT/Depends |
| `POST` | `/api/v1/dashboard-studio/templates/{template_id}/versions/{version}/rollback` | Dashboard Studio | Rollback Template | JWT/Depends |
| `POST` | `/api/v1/dashboard-studio/validate-layout` | Dashboard Studio | Validate Layout | JWT/Depends |
| `GET` | `/api/v1/dashboard/events` |  Live Dashboard Runtime | Assinatura Server-Sent Events (SSE) para Live Updates | JWT/Depends |
| `GET` | `/api/v1/dashboard-preferences/{scope}` | Dashboard Preferences | Carregar preferencia de dashboard do usuario | JWT/Depends |
| `PUT` | `/api/v1/dashboard-preferences/{scope}` | Dashboard Preferences | Salvar preferencia de dashboard do usuario | JWT/Depends |
| `POST` | `/api/v1/dashboard/refresh` |  Live Dashboard Runtime | Forcar Smart Refresh de um Painel Analitico | JWT/Depends |
| `GET` | `/api/v1/dashboard/telemetry` |  Live Dashboard Runtime | Relatorio de Observabilidade de Renderizacao | JWT/Depends |
| `GET` | `/api/v1/metadata-catalog/` | Metadata Catalog | Pesquisar estruturas no Metadata Catalog | JWT/Depends |
| `GET` | `/api/v1/metadata-catalog/health` | Metadata Catalog | Relatorio de saude do Metadata Catalog | JWT/Depends |
| `GET` | `/api/v1/metadata-catalog/summary` | Metadata Catalog | Resumo executivo do Metadata Catalog | JWT/Depends |
| `GET` | `/api/v1/metadata-catalog/{estrutura_id}` | Metadata Catalog | Obter metadados de uma estrutura | JWT/Depends |
| `GET` | `/api/v1/metadata-catalog/{estrutura_id}/dependency-graph` | Metadata Catalog | Obter grafo de dependencias de uma estrutura | JWT/Depends |
| `GET` | `/api/v1/metadata-catalog/{estrutura_id}/impact` | Metadata Catalog | Obter impacto de alteracao de uma estrutura | JWT/Depends |
| `GET` | `/api/v1/metadata-catalog/{estrutura_id}/lineage` | Metadata Catalog | Obter Data Lineage de uma estrutura | JWT/Depends |
| `GET` | `/api/v1/metadata-catalog/{estrutura_id}/versions` | Metadata Catalog | Obter historico de versoes de uma estrutura | JWT/Depends |
| `POST` | `/api/v1/query/` |  Query Engine | Consulta Inteligente via Motor de Intencao | JWT/Depends |
| `POST` | `/api/v1/query/cache/clear` |  Query Engine | Limpar Cache Plataforma | JWT/Depends |
| `GET` | `/api/v1/query/cache/stats` |  Query Engine | Obter Estatisticas Cache | JWT/Depends |
| `GET` | `/api/v1/query/favorites` |  Query Engine | Listar consultas favoritadas (Hidratacao) | JWT/Depends |
| `GET` | `/api/v1/query/history` |  Query Engine | Listar historico de pesquisas (Hidratacao) | JWT/Depends |
| `POST` | `/api/v1/query/inspector/replay` |  Query Engine | Run Inspector Replay | JWT/Depends |
| `GET` | `/api/v1/query/inspector/trace/{trace_id}` |  Query Engine | Get Inspector Trace Detail | JWT/Depends |
| `GET` | `/api/v1/query/inspector/traces` |  Query Engine | Get Inspector Traces | JWT/Depends |
| `GET` | `/api/v1/query/intelligence` |  Query Engine | Obter Metricas Inteligencia | JWT/Depends |
| `GET` | `/api/v1/query/performance/center` |  Query Engine | Obter Relatorio Performance | JWT/Depends |
| `POST` | `/api/v1/query/performance/optimize` |  Query Engine | Otimizar Recursos Sistema | JWT/Depends |
| `POST` | `/api/v1/query/security/backup` |  Query Engine | Criar Backup Seguro | JWT/Depends |
| `GET` | `/api/v1/query/security/center` |  Query Engine | Obter Relatorio Seguranca | JWT/Depends |
| `POST` | `/api/v1/query/security/restore` |  Query Engine | Restaurar Backup Seguro | JWT/Depends |
| `GET` | `/api/v1/svr/` |  Semantic Version Registry | Get Version Center | JWT/Depends |
| `POST` | `/api/v1/svr/concepts/deprecate` |  Semantic Version Registry | Deprecate Concept Version | JWT/Depends |
| `POST` | `/api/v1/svr/concepts/register` |  Semantic Version Registry | Register Concept | JWT/Depends |
| `GET` | `/api/v1/svr/concepts/{concept_id}/history` |  Semantic Version Registry | Get Concept History | JWT/Depends |
| `POST` | `/api/v1/svr/migration/evaluate` |  Semantic Version Registry | Evaluate Migration | JWT/Depends |
| `GET` | `/api/v1/tenant/ai-status` |  Configuracoes do Tenant | Status do AI Credential Manager (Admin-Only) | JWT/Depends |
| `GET` | `/api/v1/tenant/aim-status` |  Configuracoes do Tenant | Status do AI Invocation Manager (Admin-Only) | JWT/Depends |
| `GET` | `/api/v1/tenant/audit-logs` |  Configuracoes do Tenant | Obter logs de auditoria de consultas (Admin-Only) | JWT/Depends |
| `GET` | `/api/v1/tenant/settings` |  Configuracoes do Tenant | Obter Configuracoes Atuais (Admin-Only) | JWT/Depends |
| `PUT` | `/api/v1/tenant/settings` |  Configuracoes do Tenant | Atualizar Configuracoes do Tenant (Admin-Only) | JWT/Depends |
| `POST` | `/api/v1/tenant/sync-now` |  Configuracoes do Tenant | Forcar Sincronizacao Imediata (Admin-Only) | JWT/Depends |
| `GET` | `/api/v1/tenant/sync-progress` |  Configuracoes do Tenant | Consultar Progresso da Sincronizacao (Admin-Only) | JWT/Depends |
| `POST` | `/api/v1/tenant/test-ai` |  Configuracoes do Tenant | Testar Conexao de IA (Admin-Only) | JWT/Depends |
| `POST` | `/api/v1/tenant/test-oracle` |  Configuracoes do Tenant | Testar Conexao Oracle (Admin-Only) | JWT/Depends |
| `POST` | `/api/v1/tenant/test-postgres-clone` |  Configuracoes do Tenant | Testar Conexao PostgreSQL do Clone (Admin-Only) | JWT/Depends |
| `GET` | `/api/v1/users/` |  Usuarios | Listar Todos os Usuarios do Tenant (Admin-Only) | JWT/Depends |
| `POST` | `/api/v1/users/` |  Usuarios | Cadastrar Novo Usuario (Admin-Only) | JWT/Depends |
| `DELETE` | `/api/v1/users/{user_id}` |  Usuarios | Deletar Usuario (Admin-Only) | JWT/Depends |
| `PATCH` | `/api/v1/users/{user_id}` |  Usuarios | Editar Usuario (Admin-Only) | JWT/Depends |
| `PUT` | `/api/v1/users/{user_id}/toggle-active` |  Usuarios | Ativar/Desativar Usuario (Admin-Only) | JWT/Depends |
| `GET` | `/health` | Sistema | Verificacao de saude da API | Publica ou sessao |
| `GET` | `/health/deep` | Sistema | Verificacao profunda de saude da API, PostgreSQL e IA | Publica ou sessao |

## Detalhamento Por Endpoint

### `GET /api/v1/analytical-packages`

- Nome: `list_packages_api_v1_analytical_packages_get`
- Objetivo: Listar Analytical Packages
- Tags: Analytical Packages
- Parametros:
  - `status` em `query` (opcional)
  - `limit` em `query` (opcional)
  - `offset` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/analytical-packages/stats`

- Nome: `get_package_stats_api_v1_analytical_packages_stats_get`
- Objetivo: Metricas globais de Analytical Packages
- Tags: Analytical Packages
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/analytical-packages/{package_id}`

- Nome: `get_package_api_v1_analytical_packages__package_id__get`
- Objetivo: Detalhe de um Analytical Package
- Tags: Analytical Packages
- Parametros:
  - `package_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/analytical-packages/{package_id}/deprecate`

- Nome: `deprecate_package_api_v1_analytical_packages__package_id__deprecate_post`
- Objetivo: Deprecar um Analytical Package manualmente
- Tags: Analytical Packages
- Parametros:
  - `package_id` em `path` (obrigatorio)
- Payload: DeprecateRequest
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/analytical-packages/{package_id}/instances`

- Nome: `list_package_instances_api_v1_analytical_packages__package_id__instances_get`
- Objetivo: Historico de execucoes de um Package
- Tags: Analytical Packages
- Parametros:
  - `package_id` em `path` (obrigatorio)
  - `limit` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/auth/change-password`

- Nome: `change_password_api_v1_auth_change_password_post`
- Objetivo: Alteracao de Senha Obrigatoria
- Tags:  Autenticacao
- Parametros: nenhum parametro explicito no schema.
- Payload: ChangePasswordRequest
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/auth/login`

- Nome: `login_api_v1_auth_login_post`
- Objetivo: Login de Usuario
- Tags:  Autenticacao
- Parametros: nenhum parametro explicito no schema.
- Payload: LoginRequest
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/auth/logout`

- Nome: `logout_api_v1_auth_logout_post`
- Objetivo: Encerrar sessao
- Tags:  Autenticacao
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/auth/session`

- Nome: `get_session_api_v1_auth_session_get`
- Objetivo: Sessao autenticada
- Tags:  Autenticacao
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/business-knowledge/dictionary`

- Nome: `list_dictionary_concepts_api_v1_business_knowledge_dictionary_get`
- Objetivo: Listar conceitos do dicionario
- Tags: Business Knowledge Engine
- Parametros:
  - `categoria` em `query` (opcional)
  - `area` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/business-knowledge/dictionary`

- Nome: `register_concept_api_v1_business_knowledge_dictionary_post`
- Objetivo: Registrar/Atualizar conceito de negocio
- Tags: Business Knowledge Engine
- Parametros: nenhum parametro explicito no schema.
- Payload: RegisterConceptRequest
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/business-knowledge/formulas`

- Nome: `list_formulas_api_v1_business_knowledge_formulas_get`
- Objetivo: Listar formulas de BI
- Tags: Business Knowledge Engine
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/business-knowledge/impact`

- Nome: `get_impact_analysis_api_v1_business_knowledge_impact_get`
- Objetivo: Analise de impacto de dependencia
- Tags: Business Knowledge Engine
- Parametros:
  - `target` em `query` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/business-knowledge/kpis`

- Nome: `list_registered_kpis_api_v1_business_knowledge_kpis_get`
- Objetivo: Listar KPIs registrados
- Tags: Business Knowledge Engine
- Parametros:
  - `categoria` em `query` (opcional)
  - `area` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/business-knowledge/kpis`

- Nome: `register_kpi_api_v1_business_knowledge_kpis_post`
- Objetivo: Registrar/Atualizar KPI oficial
- Tags: Business Knowledge Engine
- Parametros: nenhum parametro explicito no schema.
- Payload: RegisterKPIRequest
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/business-knowledge/observability`

- Nome: `get_observability_api_v1_business_knowledge_observability_get`
- Objetivo: Metricas de observabilidade do BKE
- Tags: Business Knowledge Engine
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/business-knowledge/rollback`

- Nome: `execute_rollback_api_v1_business_knowledge_rollback_post`
- Objetivo: Executar rollback de versao
- Tags: Business Knowledge Engine
- Parametros: nenhum parametro explicito no schema.
- Payload: RollbackRequest
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/business-knowledge/seed`

- Nome: `seed_bke_api_v1_business_knowledge_seed_post`
- Objetivo: Semear formulas e relacoes de BI padrao
- Tags: Business Knowledge Engine
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/catalog/`

- Nome: `list_catalog_views_api_v1_catalog__get`
- Objetivo: Listar Todas as Views do Catalogo (Admin/Gestor-Only)
- Tags:  Catalogo de Views
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/catalog/`

- Nome: `create_catalog_view_api_v1_catalog__post`
- Objetivo: Cadastrar Nova View no Catalogo (Admin/Gestor-Only)
- Tags:  Catalogo de Views
- Parametros: nenhum parametro explicito no schema.
- Payload: ViewCatalogCreate
- Codigos HTTP documentados: 201, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `DELETE /api/v1/catalog/{view_id}`

- Nome: `delete_catalog_view_api_v1_catalog__view_id__delete`
- Objetivo: Deletar View do Catalogo (Admin/Gestor-Only)
- Tags:  Catalogo de Views
- Parametros:
  - `view_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 204, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `PUT /api/v1/catalog/{view_id}`

- Nome: `update_catalog_view_api_v1_catalog__view_id__put`
- Objetivo: Atualizar View do Catalogo (Admin/Gestor-Only)
- Tags:  Catalogo de Views
- Parametros:
  - `view_id` em `path` (obrigatorio)
- Payload: ViewCatalogUpdate
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/dashboard-studio/import`

- Nome: `import_layout_api_v1_dashboard_studio_import_post`
- Objetivo: Import Layout
- Tags: Dashboard Studio
- Parametros: nenhum parametro explicito no schema.
- Payload: DashboardImportRequest
- Codigos HTTP documentados: 201, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/dashboard-studio/instances`

- Nome: `list_instances_api_v1_dashboard_studio_instances_get`
- Objetivo: List Instances
- Tags: Dashboard Studio
- Parametros:
  - `include_archived` em `query` (opcional)
  - `favorites_only` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/dashboard-studio/instances`

- Nome: `create_instance_api_v1_dashboard_studio_instances_post`
- Objetivo: Create Instance
- Tags: Dashboard Studio
- Parametros: nenhum parametro explicito no schema.
- Payload: DashboardInstanceCreate
- Codigos HTTP documentados: 201, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/dashboard-studio/instances/{instance_id}`

- Nome: `get_instance_api_v1_dashboard_studio_instances__instance_id__get`
- Objetivo: Get Instance
- Tags: Dashboard Studio
- Parametros:
  - `instance_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `PATCH /api/v1/dashboard-studio/instances/{instance_id}`

- Nome: `update_instance_api_v1_dashboard_studio_instances__instance_id__patch`
- Objetivo: Update Instance
- Tags: Dashboard Studio
- Parametros:
  - `instance_id` em `path` (obrigatorio)
- Payload: DashboardInstanceUpdate
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/dashboard-studio/instances/{instance_id}/duplicate`

- Nome: `duplicate_instance_api_v1_dashboard_studio_instances__instance_id__duplicate_post`
- Objetivo: Duplicate Instance
- Tags: Dashboard Studio
- Parametros:
  - `instance_id` em `path` (obrigatorio)
- Payload: DashboardDuplicateRequest
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/dashboard-studio/instances/{instance_id}/export`

- Nome: `export_instance_api_v1_dashboard_studio_instances__instance_id__export_get`
- Objetivo: Export Instance
- Tags: Dashboard Studio
- Parametros:
  - `instance_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/dashboard-studio/instances/{instance_id}/favorite`

- Nome: `set_favorite_api_v1_dashboard_studio_instances__instance_id__favorite_post`
- Objetivo: Set Favorite
- Tags: Dashboard Studio
- Parametros:
  - `instance_id` em `path` (obrigatorio)
- Payload: DashboardFavoriteRequest
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/dashboard-studio/instances/{instance_id}/versions`

- Nome: `list_instance_versions_api_v1_dashboard_studio_instances__instance_id__versions_get`
- Objetivo: List Instance Versions
- Tags: Dashboard Studio
- Parametros:
  - `instance_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/dashboard-studio/instances/{instance_id}/versions/{version}/rollback`

- Nome: `rollback_instance_api_v1_dashboard_studio_instances__instance_id__versions__version__rollback_post`
- Objetivo: Rollback Instance
- Tags: Dashboard Studio
- Parametros:
  - `instance_id` em `path` (obrigatorio)
  - `version` em `path` (obrigatorio)
- Payload: DashboardRollbackRequest
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/dashboard-studio/templates`

- Nome: `list_templates_api_v1_dashboard_studio_templates_get`
- Objetivo: List Templates
- Tags: Dashboard Studio
- Parametros:
  - `include_archived` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/dashboard-studio/templates`

- Nome: `create_template_api_v1_dashboard_studio_templates_post`
- Objetivo: Create Template
- Tags: Dashboard Studio
- Parametros: nenhum parametro explicito no schema.
- Payload: DashboardTemplateCreate
- Codigos HTTP documentados: 201, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/dashboard-studio/templates/{template_id}`

- Nome: `get_template_api_v1_dashboard_studio_templates__template_id__get`
- Objetivo: Get Template
- Tags: Dashboard Studio
- Parametros:
  - `template_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `PATCH /api/v1/dashboard-studio/templates/{template_id}`

- Nome: `update_template_api_v1_dashboard_studio_templates__template_id__patch`
- Objetivo: Update Template
- Tags: Dashboard Studio
- Parametros:
  - `template_id` em `path` (obrigatorio)
- Payload: DashboardTemplateUpdate
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/dashboard-studio/templates/{template_id}/export`

- Nome: `export_template_api_v1_dashboard_studio_templates__template_id__export_get`
- Objetivo: Export Template
- Tags: Dashboard Studio
- Parametros:
  - `template_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/dashboard-studio/templates/{template_id}/versions`

- Nome: `list_template_versions_api_v1_dashboard_studio_templates__template_id__versions_get`
- Objetivo: List Template Versions
- Tags: Dashboard Studio
- Parametros:
  - `template_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/dashboard-studio/templates/{template_id}/versions/{version}/rollback`

- Nome: `rollback_template_api_v1_dashboard_studio_templates__template_id__versions__version__rollback_post`
- Objetivo: Rollback Template
- Tags: Dashboard Studio
- Parametros:
  - `template_id` em `path` (obrigatorio)
  - `version` em `path` (obrigatorio)
- Payload: DashboardRollbackRequest
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/dashboard-studio/validate-layout`

- Nome: `validate_layout_api_v1_dashboard_studio_validate_layout_post`
- Objetivo: Validate Layout
- Tags: Dashboard Studio
- Parametros: nenhum parametro explicito no schema.
- Payload: DashboardLayoutValidationRequest
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/dashboard/events`

- Nome: `listen_dashboard_events_api_v1_dashboard_events_get`
- Objetivo: Assinatura Server-Sent Events (SSE) para Live Updates
- Tags:  Live Dashboard Runtime
- Parametros:
  - `tenant_id` em `query` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/dashboard/refresh`

- Nome: `force_dashboard_refresh_api_v1_dashboard_refresh_post`
- Objetivo: Forcar Smart Refresh de um Painel Analitico
- Tags:  Live Dashboard Runtime
- Parametros:
  - `package_id` em `query` (obrigatorio)
  - `tenant_id` em `query` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/dashboard/telemetry`

- Nome: `get_dashboard_telemetry_api_v1_dashboard_telemetry_get`
- Objetivo: Relatorio de Observabilidade de Renderizacao
- Tags:  Live Dashboard Runtime
- Parametros:
  - `tenant_id` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/metadata-catalog/`

- Nome: `search_metadata_catalog_api_v1_metadata_catalog__get`
- Objetivo: Pesquisar estruturas no Metadata Catalog
- Tags: Metadata Catalog
- Parametros:
  - `q` em `query` (opcional)
  - `tipo` em `query` (opcional)
  - `tags` em `query` (opcional)
  - `categoria` em `query` (opcional)
  - `limit` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/metadata-catalog/health`

- Nome: `get_metadata_health_api_v1_metadata_catalog_health_get`
- Objetivo: Relatorio de saude do Metadata Catalog
- Tags: Metadata Catalog
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/metadata-catalog/summary`

- Nome: `get_metadata_summary_api_v1_metadata_catalog_summary_get`
- Objetivo: Resumo executivo do Metadata Catalog
- Tags: Metadata Catalog
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/metadata-catalog/{estrutura_id}`

- Nome: `get_metadata_entity_api_v1_metadata_catalog__estrutura_id__get`
- Objetivo: Obter metadados de uma estrutura
- Tags: Metadata Catalog
- Parametros:
  - `estrutura_id` em `path` (obrigatorio)
  - `tipo` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/metadata-catalog/{estrutura_id}/dependency-graph`

- Nome: `get_metadata_dependency_graph_api_v1_metadata_catalog__estrutura_id__dependency_graph_get`
- Objetivo: Obter grafo de dependencias de uma estrutura
- Tags: Metadata Catalog
- Parametros:
  - `estrutura_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/metadata-catalog/{estrutura_id}/impact`

- Nome: `get_metadata_impact_api_v1_metadata_catalog__estrutura_id__impact_get`
- Objetivo: Obter impacto de alteracao de uma estrutura
- Tags: Metadata Catalog
- Parametros:
  - `estrutura_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/metadata-catalog/{estrutura_id}/lineage`

- Nome: `get_metadata_lineage_api_v1_metadata_catalog__estrutura_id__lineage_get`
- Objetivo: Obter Data Lineage de uma estrutura
- Tags: Metadata Catalog
- Parametros:
  - `estrutura_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/metadata-catalog/{estrutura_id}/versions`

- Nome: `get_metadata_versions_api_v1_metadata_catalog__estrutura_id__versions_get`
- Objetivo: Obter historico de versoes de uma estrutura
- Tags: Metadata Catalog
- Parametros:
  - `estrutura_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/query/`

- Nome: `processar_consulta_api_v1_query__post`
- Objetivo: Consulta Inteligente via Motor de Intencao
- Tags:  Query Engine
- Parametros: nenhum parametro explicito no schema.
- Payload: QueryRequest
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/query/cache/clear`

- Nome: `limpar_cache_plataforma_api_v1_query_cache_clear_post`
- Objetivo: Limpar Cache Plataforma
- Tags:  Query Engine
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/query/cache/stats`

- Nome: `obter_estatisticas_cache_api_v1_query_cache_stats_get`
- Objetivo: Obter Estatisticas Cache
- Tags:  Query Engine
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/query/favorites`

- Nome: `get_query_favorites_api_v1_query_favorites_get`
- Objetivo: Listar consultas favoritadas (Hidratacao)
- Tags:  Query Engine
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/query/history`

- Nome: `get_query_history_api_v1_query_history_get`
- Objetivo: Listar historico de pesquisas (Hidratacao)
- Tags:  Query Engine
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/query/inspector/replay`

- Nome: `run_inspector_replay_api_v1_query_inspector_replay_post`
- Objetivo: Run Inspector Replay
- Tags:  Query Engine
- Parametros: nenhum parametro explicito no schema.
- Payload: object
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/query/inspector/trace/{trace_id}`

- Nome: `get_inspector_trace_detail_api_v1_query_inspector_trace__trace_id__get`
- Objetivo: Get Inspector Trace Detail
- Tags:  Query Engine
- Parametros:
  - `trace_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/query/inspector/traces`

- Nome: `get_inspector_traces_api_v1_query_inspector_traces_get`
- Objetivo: Get Inspector Traces
- Tags:  Query Engine
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/query/intelligence`

- Nome: `obter_metricas_inteligencia_api_v1_query_intelligence_get`
- Objetivo: Obter Metricas Inteligencia
- Tags:  Query Engine
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/query/performance/center`

- Nome: `obter_relatorio_performance_api_v1_query_performance_center_get`
- Objetivo: Obter Relatorio Performance
- Tags:  Query Engine
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/query/performance/optimize`

- Nome: `otimizar_recursos_sistema_api_v1_query_performance_optimize_post`
- Objetivo: Otimizar Recursos Sistema
- Tags:  Query Engine
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/query/security/backup`

- Nome: `criar_backup_seguro_api_v1_query_security_backup_post`
- Objetivo: Criar Backup Seguro
- Tags:  Query Engine
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/query/security/center`

- Nome: `obter_relatorio_seguranca_api_v1_query_security_center_get`
- Objetivo: Obter Relatorio Seguranca
- Tags:  Query Engine
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/query/security/restore`

- Nome: `restaurar_backup_seguro_api_v1_query_security_restore_post`
- Objetivo: Restaurar Backup Seguro
- Tags:  Query Engine
- Parametros: nenhum parametro explicito no schema.
- Payload: object
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/svr/`

- Nome: `get_version_center_api_v1_svr__get`
- Objetivo: Get Version Center
- Tags:  Semantic Version Registry
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/svr/concepts/deprecate`

- Nome: `deprecate_concept_version_api_v1_svr_concepts_deprecate_post`
- Objetivo: Deprecate Concept Version
- Tags:  Semantic Version Registry
- Parametros: nenhum parametro explicito no schema.
- Payload: ConceptDeprecateRequest
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/svr/concepts/register`

- Nome: `register_concept_api_v1_svr_concepts_register_post`
- Objetivo: Register Concept
- Tags:  Semantic Version Registry
- Parametros: nenhum parametro explicito no schema.
- Payload: ConceptRegisterRequest
- Codigos HTTP documentados: 201, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/svr/concepts/{concept_id}/history`

- Nome: `get_concept_history_api_v1_svr_concepts__concept_id__history_get`
- Objetivo: Get Concept History
- Tags:  Semantic Version Registry
- Parametros:
  - `concept_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/svr/migration/evaluate`

- Nome: `evaluate_migration_api_v1_svr_migration_evaluate_post`
- Objetivo: Evaluate Migration
- Tags:  Semantic Version Registry
- Parametros: nenhum parametro explicito no schema.
- Payload: MigrationEvaluateRequest
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/tenant/ai-status`

- Nome: `get_ai_credential_status_api_v1_tenant_ai_status_get`
- Objetivo: Status do AI Credential Manager (Admin-Only)
- Tags:  Configuracoes do Tenant
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/tenant/aim-status`

- Nome: `get_ai_invocation_status_api_v1_tenant_aim_status_get`
- Objetivo: Status do AI Invocation Manager (Admin-Only)
- Tags:  Configuracoes do Tenant
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/tenant/audit-logs`

- Nome: `get_tenant_audit_logs_api_v1_tenant_audit_logs_get`
- Objetivo: Obter logs de auditoria de consultas (Admin-Only)
- Tags:  Configuracoes do Tenant
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/tenant/settings`

- Nome: `get_tenant_settings_api_v1_tenant_settings_get`
- Objetivo: Obter Configuracoes Atuais (Admin-Only)
- Tags:  Configuracoes do Tenant
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `PUT /api/v1/tenant/settings`

- Nome: `update_tenant_settings_api_v1_tenant_settings_put`
- Objetivo: Atualizar Configuracoes do Tenant (Admin-Only)
- Tags:  Configuracoes do Tenant
- Parametros: nenhum parametro explicito no schema.
- Payload: TenantSettingsUpdate
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/tenant/sync-now`

- Nome: `trigger_tenant_sync_api_v1_tenant_sync_now_post`
- Objetivo: Forcar Sincronizacao Imediata (Admin-Only)
- Tags:  Configuracoes do Tenant
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/tenant/sync-progress`

- Nome: `get_tenant_sync_progress_api_v1_tenant_sync_progress_get`
- Objetivo: Consultar Progresso da Sincronizacao (Admin-Only)
- Tags:  Configuracoes do Tenant
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/tenant/test-ai`

- Nome: `test_ai_connection_api_v1_tenant_test_ai_post`
- Objetivo: Testar Conexao de IA (Admin-Only)
- Tags:  Configuracoes do Tenant
- Parametros: nenhum parametro explicito no schema.
- Payload: object
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/tenant/test-oracle`

- Nome: `test_oracle_connection_api_v1_tenant_test_oracle_post`
- Objetivo: Testar Conexao Oracle (Admin-Only)
- Tags:  Configuracoes do Tenant
- Parametros: nenhum parametro explicito no schema.
- Payload: object
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/tenant/test-postgres-clone`

- Nome: `test_postgres_clone_connection_api_v1_tenant_test_postgres_clone_post`
- Objetivo: Testar Conexao PostgreSQL do Clone (Admin-Only)
- Tags:  Configuracoes do Tenant
- Parametros: nenhum parametro explicito no schema.
- Payload: object
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/users/`

- Nome: `list_users_api_v1_users__get`
- Objetivo: Listar Todos os Usuarios do Tenant (Admin-Only)
- Tags:  Usuarios
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/users/`

- Nome: `create_user_by_admin_api_v1_users__post`
- Objetivo: Cadastrar Novo Usuario (Admin-Only)
- Tags:  Usuarios
- Parametros: nenhum parametro explicito no schema.
- Payload: UserCreateAdmin
- Codigos HTTP documentados: 201, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `DELETE /api/v1/users/{user_id}`

- Nome: `delete_user_api_v1_users__user_id__delete`
- Objetivo: Deletar Usuario (Admin-Only)
- Tags:  Usuarios
- Parametros:
  - `user_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 204, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `PATCH /api/v1/users/{user_id}`

- Nome: `update_user_api_v1_users__user_id__patch`
- Objetivo: Editar Usuario (Admin-Only)
- Tags:  Usuarios
- Parametros:
  - `user_id` em `path` (obrigatorio)
- Payload: UserUpdate
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `PUT /api/v1/users/{user_id}/toggle-active`

- Nome: `toggle_user_active_api_v1_users__user_id__toggle_active_put`
- Objetivo: Ativar/Desativar Usuario (Admin-Only)
- Tags:  Usuarios
- Parametros:
  - `user_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /health`

- Nome: `health_check_health_get`
- Objetivo: Verificacao de saude da API
- Tags: Sistema
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

## Metadados Temporais V2

Quando o sidecar V2 estiver presente,
`analytical_contract.intent.contract.extensions.temporal` pode conter:

- `normalizer_version`;
- `timezone`;
- `relation` (`NONE`, `SINGLE`, `RANGE`, `PERIOD_LIST`, `COMPARISON`);
- `rule_ids`;
- `warnings`;
- `readiness`.

As janelas canonicas ficam em `analytical_contract.intent.time_windows`, com
fim inclusivo. Adapters de timestamp calculam o dia seguinte como limite
exclusivo.

## Metadados Do Planner Comparativo V2

Quando uma pergunta comparativa produz sidecar V2,
`analytical_contract.plan.contract.extensions.comparison_planner` e
`analytical_contract.comparison_planner` podem conter:

- `version` (`lumina.comparison-planner/1.0`);
- `readiness`;
- `strategy_hint`;
- `rule_ids`;
- `issue_codes`;
- `complexity`;
- `cache_identity`;
- `shadow_divergence`.

Esses metadados descrevem planejamento, nao resultados. Eles nao incluem SQL,
binds, credenciais, pergunta integral ou valores financeiros.

## Apresentacao Comparativa V2

Nao existe endpoint novo. Quando `POST /api/v1/query/` retorna uma comparacao
com sidecar `lumina.analytics/2.0`, o frontend pode adapta-la localmente para
`lumina.comparison-presentation/1.0`.

O renderer preserva o payload recebido e aplica RBAC de apresentacao:
`CONSULTA` nao recebe diagnostico administrativo, `GESTOR` pode receber
proveniencia resumida e `ADMIN` pode inspecionar checks e metadados sanitizados.
SQL, binds e credenciais nao fazem parte da apresentacao nem da exportacao.
