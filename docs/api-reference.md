# API Reference - LuminaAI

Fonte: gerado a partir do schema OpenAPI exposto por `backend/main.py`.

Observacoes:

- A autenticacao principal usa JWT emitido pelo backend e enviado por cookie HttpOnly e/ou Bearer token conforme fluxo atual.
- Rotas sob `/api/v1/api/v1/query` existem por compatibilidade com clientes antigos que duplicavam o prefixo no `base_url`.
- Campos exatos de payload/resposta seguem os DTOs em `backend/schemas` e o schema OpenAPI.

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
| `GET` | `/api/v1/conversations` | Conversation State | List Conversations | JWT/Depends |
| `POST` | `/api/v1/conversations` | Conversation State | Create Conversation | JWT/Depends |
| `DELETE` | `/api/v1/conversations/{session_id}` | Conversation State | Delete Conversation | JWT/Depends |
| `GET` | `/api/v1/conversations/{session_id}` | Conversation State | Get Conversation | JWT/Depends |
| `POST` | `/api/v1/conversations/{session_id}/archive` | Conversation State | Archive Conversation | JWT/Depends |
| `GET` | `/api/v1/conversations/{session_id}/nodes` | Conversation State | List Conversation Nodes | JWT/Depends |
| `POST` | `/api/v1/conversations/{session_id}/reopen` | Conversation State | Reopen Conversation | JWT/Depends |
| `POST` | `/api/v1/conversations/{session_id}/reset` | Conversation State | Reset Conversation | JWT/Depends |
| `GET` | `/api/v1/dashboard-preferences/{scope}` | Dashboard Preferences | Carregar preferencia de dashboard do usuario | JWT/Depends |
| `PUT` | `/api/v1/dashboard-preferences/{scope}` | Dashboard Preferences | Salvar preferencia de dashboard do usuario | JWT/Depends |
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
| `GET` | `/api/v2/admin/tools` | Governed AI Tool Registry Admin V2 | List Admin Tools | Publica ou sessao |
| `POST` | `/api/v2/admin/tools` | Governed AI Tool Registry Admin V2 | Register Admin Tool | Publica ou sessao |
| `POST` | `/api/v2/admin/tools/inspector/test` | Governed AI Tool Registry Admin V2 | Test Tool Synthetic | Publica ou sessao |
| `GET` | `/api/v2/admin/tools/snapshots` | Governed AI Tool Registry Admin V2 | List Snapshots | Publica ou sessao |
| `POST` | `/api/v2/admin/tools/{tool_id}/versions/{version}/disable` | Governed AI Tool Registry Admin V2 | Disable Tool Version | Publica ou sessao |
| `POST` | `/api/v2/admin/tools/{tool_id}/versions/{version}/publish` | Governed AI Tool Registry Admin V2 | Publish Tool Version | Publica ou sessao |
| `POST` | `/api/v2/admin/tools/{tool_id}/versions/{version}/review` | Governed AI Tool Registry Admin V2 | Review Tool Version | Publica ou sessao |
| `POST` | `/api/v2/ai-orchestration/inspector/simulate` | AI Orchestration V2 | Simulate Inspection | Publica ou sessao |
| `GET` | `/api/v2/ai-orchestration/models` | AI Orchestration V2 | List Model Definitions | Publica ou sessao |
| `GET` | `/api/v2/ai-orchestration/policies` | AI Orchestration V2 | Get Orchestration Policies | Publica ou sessao |
| `GET` | `/api/v2/ai-orchestration/prompts` | AI Orchestration V2 | List Prompt Templates | Publica ou sessao |
| `GET` | `/api/v2/ai-orchestration/providers` | AI Orchestration V2 | List Provider Definitions | Publica ou sessao |
| `POST` | `/api/v2/ai-orchestration/run` | AI Orchestration V2 | Run Ai Orchestration | Publica ou sessao |
| `GET` | `/api/v2/analytical-postgresql/catalog` | Safe Analytical PostgreSQL | Get Analytical Catalog | Publica ou sessao |
| `POST` | `/api/v2/analytical-postgresql/compile` | Safe Analytical PostgreSQL | Compile Analytical Query | Publica ou sessao |
| `POST` | `/api/v2/analytical-postgresql/execute` | Safe Analytical PostgreSQL | Execute Analytical Query | Publica ou sessao |
| `GET` | `/api/v2/enterprise-knowledge/assets` | Enterprise Knowledge V2 | List Assets | Publica ou sessao |
| `POST` | `/api/v2/enterprise-knowledge/assets` | Enterprise Knowledge V2 | Create Asset | Publica ou sessao |
| `DELETE` | `/api/v2/enterprise-knowledge/assets/{asset_id}` | Enterprise Knowledge V2 | Soft Delete Asset | Publica ou sessao |
| `GET` | `/api/v2/enterprise-knowledge/assets/{asset_id}` | Enterprise Knowledge V2 | Get Asset | Publica ou sessao |
| `POST` | `/api/v2/enterprise-knowledge/assets/{asset_id}/archive` | Enterprise Knowledge V2 | Archive Asset | Publica ou sessao |
| `GET` | `/api/v2/enterprise-knowledge/assets/{asset_id}/audit` | Enterprise Knowledge V2 | Asset Audit | Publica ou sessao |
| `POST` | `/api/v2/enterprise-knowledge/assets/{asset_id}/diff` | Enterprise Knowledge V2 | Version Diff | Publica ou sessao |
| `POST` | `/api/v2/enterprise-knowledge/assets/{asset_id}/drafts` | Enterprise Knowledge V2 | Create Draft | Publica ou sessao |
| `POST` | `/api/v2/enterprise-knowledge/assets/{asset_id}/ownership` | Enterprise Knowledge V2 | Transfer Ownership | Publica ou sessao |
| `POST` | `/api/v2/enterprise-knowledge/assets/{asset_id}/rollback` | Enterprise Knowledge V2 | Rollback Asset | Publica ou sessao |
| `GET` | `/api/v2/enterprise-knowledge/assets/{asset_id}/versions` | Enterprise Knowledge V2 | List Versions | Publica ou sessao |
| `PUT` | `/api/v2/enterprise-knowledge/assets/{asset_id}/versions/{version_id}` | Enterprise Knowledge V2 | Update Draft | Publica ou sessao |
| `POST` | `/api/v2/enterprise-knowledge/assets/{asset_id}/versions/{version_id}/deprecate` | Enterprise Knowledge V2 | Deprecate Version | Publica ou sessao |
| `POST` | `/api/v2/enterprise-knowledge/assets/{asset_id}/versions/{version_id}/publish` | Enterprise Knowledge V2 | Publish Version | Publica ou sessao |
| `POST` | `/api/v2/enterprise-knowledge/assets/{asset_id}/versions/{version_id}/review` | Enterprise Knowledge V2 | Review Version | Publica ou sessao |
| `POST` | `/api/v2/enterprise-knowledge/assets/{asset_id}/versions/{version_id}/submit` | Enterprise Knowledge V2 | Submit Review | Publica ou sessao |
| `GET` | `/api/v2/enterprise-knowledge/exports/{export_format}` | Enterprise Knowledge V2 | Export Knowledge | Publica ou sessao |
| `GET` | `/api/v2/enterprise-knowledge/glossary` | Enterprise Knowledge V2 | Search Glossary | Publica ou sessao |
| `POST` | `/api/v2/enterprise-knowledge/imports` | Enterprise Knowledge V2 | Import Knowledge | Publica ou sessao |
| `GET` | `/api/v2/enterprise-knowledge/metrics/{canonical_metric_id}` | Enterprise Knowledge V2 | Get Metric Definition | Publica ou sessao |
| `GET` | `/api/v2/enterprise-knowledge/published/{canonical_key}` | Enterprise Knowledge V2 | Get Published Asset | Publica ou sessao |
| `GET` | `/api/v2/enterprise-knowledge/review-queue` | Enterprise Knowledge V2 | Review Queue | Publica ou sessao |
| `POST` | `/api/v2/enterprise-knowledge/search` | Enterprise Knowledge V2 | Search Published Knowledge | Publica ou sessao |
| `GET` | `/api/v2/feedback/capabilities` | Governed Feedback V2 | Capabilities | Publica ou sessao |
| `GET` | `/api/v2/feedback/datasets` | Governed Feedback V2 | List Datasets | Publica ou sessao |
| `POST` | `/api/v2/feedback/datasets` | Governed Feedback V2 | Create Dataset | Publica ou sessao |
| `GET` | `/api/v2/feedback/datasets/snapshots/{snapshot_id}` | Governed Feedback V2 | Get Dataset Snapshot | Publica ou sessao |
| `POST` | `/api/v2/feedback/datasets/{snapshot_id}/export` | Governed Feedback V2 | Export Dataset | Publica ou sessao |
| `POST` | `/api/v2/feedback/datasets/{snapshot_id}/publish` | Governed Feedback V2 | Publish Dataset | Publica ou sessao |
| `POST` | `/api/v2/feedback/datasets/{snapshot_id}/transition` | Governed Feedback V2 | Transition Dataset | Publica ou sessao |
| `GET` | `/api/v2/feedback/duplicate-groups/{duplicate_fingerprint}` | Governed Feedback V2 | Duplicate Group | Publica ou sessao |
| `POST` | `/api/v2/feedback/import/dry-run` | Governed Feedback V2 | Dry Run Governed Import | Publica ou sessao |
| `POST` | `/api/v2/feedback/retention/expire` | Governed Feedback V2 | Expire Feedback By Retention | Publica ou sessao |
| `GET` | `/api/v2/feedback/review/queue` | Governed Feedback V2 | Review Queue | Publica ou sessao |
| `POST` | `/api/v2/feedback/shadow-evaluate` | Governed Feedback V2 | Shadow Evaluate Feedback | Publica ou sessao |
| `GET` | `/api/v2/feedback/training-candidates` | Governed Feedback V2 | List Training Candidates | Publica ou sessao |
| `POST` | `/api/v2/feedback/training-candidates/{candidate_id}/approve` | Governed Feedback V2 | Approve Training Candidate | Publica ou sessao |
| `POST` | `/api/v2/feedback/training-candidates/{candidate_id}/reject` | Governed Feedback V2 | Reject Training Candidate | Publica ou sessao |
| `POST` | `/api/v2/feedback/training-candidates/{candidate_id}/validate` | Governed Feedback V2 | Validate Training Candidate | Publica ou sessao |
| `GET` | `/api/v2/feedback/training-examples` | Governed Feedback V2 | List Training Examples | Publica ou sessao |
| `GET` | `/api/v2/feedback/{feedback_id}` | Governed Feedback V2 | Get Feedback For Review | Publica ou sessao |
| `POST` | `/api/v2/feedback/{feedback_id}/approve` | Governed Feedback V2 | Approve Feedback | Publica ou sessao |
| `POST` | `/api/v2/feedback/{feedback_id}/reject` | Governed Feedback V2 | Reject Feedback | Publica ou sessao |
| `POST` | `/api/v2/feedback/{feedback_id}/request-information` | Governed Feedback V2 | Request Information | Publica ou sessao |
| `POST` | `/api/v2/feedback/{feedback_id}/review` | Governed Feedback V2 | Review Feedback | Publica ou sessao |
| `POST` | `/api/v2/feedback/{feedback_id}/reviewer` | Governed Feedback V2 | Assign Reviewer | Publica ou sessao |
| `POST` | `/api/v2/feedback/{feedback_id}/training-candidate` | Governed Feedback V2 | Create Training Candidate | Publica ou sessao |
| `GET` | `/api/v2/me/analytical-profile` | User Analytical Profile V2 | Get Profile | Publica ou sessao |
| `GET` | `/api/v2/me/analytical-profile/capabilities` | User Analytical Profile V2 | Capabilities | Publica ou sessao |
| `POST` | `/api/v2/me/analytical-profile/deletion-requests` | User Analytical Profile V2 | Request Deletion | Publica ou sessao |
| `POST` | `/api/v2/me/analytical-profile/disable` | User Analytical Profile V2 | Disable Profile | Publica ou sessao |
| `POST` | `/api/v2/me/analytical-profile/import/confirm` | User Analytical Profile V2 | Import Confirm | Publica ou sessao |
| `POST` | `/api/v2/me/analytical-profile/import/dry-run` | User Analytical Profile V2 | Import Dry Run | Publica ou sessao |
| `POST` | `/api/v2/me/analytical-profile/reactivate` | User Analytical Profile V2 | Reactivate Profile | Publica ou sessao |
| `GET` | `/api/v2/me/analytical-profile/summary` | User Analytical Profile V2 | Get Summary | Publica ou sessao |
| `GET` | `/api/v2/me/feedback` | Governed Feedback V2 | List Own Feedback | Publica ou sessao |
| `POST` | `/api/v2/me/feedback` | Governed Feedback V2 | Submit Feedback | Publica ou sessao |
| `GET` | `/api/v2/me/feedback-export` | Governed Feedback V2 | Export Own Feedback | Publica ou sessao |
| `GET` | `/api/v2/me/feedback/{feedback_id}` | Governed Feedback V2 | Get Own Feedback | Publica ou sessao |
| `PATCH` | `/api/v2/me/feedback/{feedback_id}` | Governed Feedback V2 | Update Feedback Explanation | Publica ou sessao |
| `POST` | `/api/v2/me/feedback/{feedback_id}/deletion-request` | Governed Feedback V2 | Request Feedback Deletion | Publica ou sessao |
| `POST` | `/api/v2/me/feedback/{feedback_id}/information-response` | Governed Feedback V2 | Respond To Information Request | Publica ou sessao |
| `POST` | `/api/v2/me/feedback/{feedback_id}/withdraw` | Governed Feedback V2 | Withdraw Feedback | Publica ou sessao |
| `GET` | `/api/v2/me/preferences` | User Analytical Profile V2 | List Preferences | Publica ou sessao |
| `POST` | `/api/v2/me/preferences` | User Analytical Profile V2 | Create Preference | Publica ou sessao |
| `GET` | `/api/v2/me/preferences/applicable` | User Analytical Profile V2 | Applicable Preferences | Publica ou sessao |
| `DELETE` | `/api/v2/me/preferences/{preference_id}` | User Analytical Profile V2 | Delete Preference | Publica ou sessao |
| `GET` | `/api/v2/me/preferences/{preference_id}` | User Analytical Profile V2 | Get Preference | Publica ou sessao |
| `PUT` | `/api/v2/me/preferences/{preference_id}` | User Analytical Profile V2 | Update Preference | Publica ou sessao |
| `DELETE` | `/api/v2/me/preferences/{preference_id}/consent` | User Analytical Profile V2 | Revoke Consent | Publica ou sessao |
| `POST` | `/api/v2/me/preferences/{preference_id}/consent` | User Analytical Profile V2 | Grant Consent | Publica ou sessao |
| `POST` | `/api/v2/me/preferences/{preference_id}/disable` | User Analytical Profile V2 | Disable Preference | Publica ou sessao |
| `POST` | `/api/v2/me/preferences/{preference_id}/reactivate` | User Analytical Profile V2 | Reactivate Preference | Publica ou sessao |
| `POST` | `/api/v2/me/preferences/{preference_id}/revoke` | User Analytical Profile V2 | Revoke Preference | Publica ou sessao |
| `GET` | `/api/v2/me/profile/export` | User Analytical Profile V2 | Export Profile | Publica ou sessao |
| `POST` | `/api/v2/me/profile/export` | User Analytical Profile V2 | Export Profile | Publica ou sessao |
| `GET` | `/api/v2/semantic/admin/audit` | Governed Semantic Retrieval V2 | Audit Events | Publica ou sessao |
| `GET` | `/api/v2/semantic/admin/indexes` | Governed Semantic Retrieval V2 | List Indexes | Publica ou sessao |
| `POST` | `/api/v2/semantic/admin/indexes/default` | Governed Semantic Retrieval V2 | Create Default Index | Publica ou sessao |
| `PATCH` | `/api/v2/semantic/admin/indexes/{index_id}` | Governed Semantic Retrieval V2 | Update Index Definition | Publica ou sessao |
| `POST` | `/api/v2/semantic/admin/indexes/{index_id}/build` | Governed Semantic Retrieval V2 | Build Index | Publica ou sessao |
| `GET` | `/api/v2/semantic/admin/indexes/{index_id}/evaluations` | Governed Semantic Retrieval V2 | List Evaluations | Publica ou sessao |
| `POST` | `/api/v2/semantic/admin/indexes/{index_id}/evaluations` | Governed Semantic Retrieval V2 | Run Evaluation | Publica ou sessao |
| `POST` | `/api/v2/semantic/admin/indexes/{index_id}/publish` | Governed Semantic Retrieval V2 | Publish Index | Publica ou sessao |
| `POST` | `/api/v2/semantic/admin/indexes/{index_id}/rollback` | Governed Semantic Retrieval V2 | Rollback Index | Publica ou sessao |
| `GET` | `/api/v2/semantic/admin/indexes/{index_id}/stale-sources` | Governed Semantic Retrieval V2 | List Stale Sources | Publica ou sessao |
| `GET` | `/api/v2/semantic/admin/indexes/{index_id}/versions` | Governed Semantic Retrieval V2 | List Versions | Publica ou sessao |
| `GET` | `/api/v2/semantic/admin/indexes/{index_id}/versions/{version_id}` | Governed Semantic Retrieval V2 | Inspect Version | Publica ou sessao |
| `POST` | `/api/v2/semantic/admin/indexes/{index_id}/versions/{version_id}/deprecate` | Governed Semantic Retrieval V2 | Deprecate Index Version | Publica ou sessao |
| `GET` | `/api/v2/semantic/admin/indexes/{index_id}/versions/{version_id}/manifest` | Governed Semantic Retrieval V2 | Export Index Manifest | Publica ou sessao |
| `GET` | `/api/v2/semantic/admin/observability` | Governed Semantic Retrieval V2 | Observability | Publica ou sessao |
| `POST` | `/api/v2/semantic/admin/search` | Governed Semantic Retrieval V2 | Inspect Search | Publica ou sessao |
| `GET` | `/api/v2/semantic/candidates/{document_id}` | Governed Semantic Retrieval V2 | Public Candidate Detail | Publica ou sessao |
| `GET` | `/api/v2/semantic/capabilities` | Governed Semantic Retrieval V2 | Capabilities | Publica ou sessao |
| `POST` | `/api/v2/semantic/clarifications/{clarification_id}/resolve` | Governed Semantic Retrieval V2 | Resolve Clarification | Publica ou sessao |
| `POST` | `/api/v2/semantic/entities/resolve` | Governed Semantic Retrieval V2 | Resolve Entity | Publica ou sessao |
| `POST` | `/api/v2/semantic/resolve` | Governed Semantic Retrieval V2 | Resolve | Publica ou sessao |
| `POST` | `/api/v2/semantic/search` | Governed Semantic Retrieval V2 | Search | Publica ou sessao |
| `GET` | `/api/v2/tools/catalog` | Governed AI Tool Registry V2 | Get Tool Catalog | Publica ou sessao |
| `POST` | `/api/v2/tools/invoke` | Governed AI Tool Registry V2 | Invoke Governed Tool | Publica ou sessao |
| `POST` | `/api/v2/tools/validate-proposal` | Governed AI Tool Registry V2 | Validate Tool Proposal | Publica ou sessao |
| `GET` | `/api/v2/validation/policy/default` | Validation & Provenance V2 | Get Default Policy | Publica ou sessao |
| `POST` | `/api/v2/validation/run` | Validation & Provenance V2 | Run Validation Pipeline | Publica ou sessao |
| `GET` | `/health` | Sistema | Verificacao de saude da API | Publica ou sessao |
| `GET` | `/health/deep` | Sistema | Verificacao profunda de saude da API | Publica ou sessao |

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

### `GET /api/v1/conversations`

- Nome: `list_conversations_api_v1_conversations_get`
- Objetivo: List Conversations
- Tags: Conversation State
- Parametros:
  - `limit` em `query` (opcional)
  - `cursor_activity` em `query` (opcional)
  - `cursor_id` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/conversations`

- Nome: `create_conversation_api_v1_conversations_post`
- Objetivo: Create Conversation
- Tags: Conversation State
- Parametros: nenhum parametro explicito no schema.
- Payload: ConversationCreateRequest
- Codigos HTTP documentados: 201, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `DELETE /api/v1/conversations/{session_id}`

- Nome: `delete_conversation_api_v1_conversations__session_id__delete`
- Objetivo: Delete Conversation
- Tags: Conversation State
- Parametros:
  - `session_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/conversations/{session_id}`

- Nome: `get_conversation_api_v1_conversations__session_id__get`
- Objetivo: Get Conversation
- Tags: Conversation State
- Parametros:
  - `session_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/conversations/{session_id}/archive`

- Nome: `archive_conversation_api_v1_conversations__session_id__archive_post`
- Objetivo: Archive Conversation
- Tags: Conversation State
- Parametros:
  - `session_id` em `path` (obrigatorio)
- Payload: ConversationMutationRequest
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/conversations/{session_id}/nodes`

- Nome: `list_conversation_nodes_api_v1_conversations__session_id__nodes_get`
- Objetivo: List Conversation Nodes
- Tags: Conversation State
- Parametros:
  - `session_id` em `path` (obrigatorio)
  - `after_sequence` em `query` (opcional)
  - `limit` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/conversations/{session_id}/reopen`

- Nome: `reopen_conversation_api_v1_conversations__session_id__reopen_post`
- Objetivo: Reopen Conversation
- Tags: Conversation State
- Parametros:
  - `session_id` em `path` (obrigatorio)
- Payload: ConversationMutationRequest
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v1/conversations/{session_id}/reset`

- Nome: `reset_conversation_api_v1_conversations__session_id__reset_post`
- Objetivo: Reset Conversation
- Tags: Conversation State
- Parametros:
  - `session_id` em `path` (obrigatorio)
- Payload: ConversationMutationRequest
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v1/dashboard-preferences/{scope}`

- Nome: `get_dashboard_preference_api_v1_dashboard_preferences__scope__get`
- Objetivo: Carregar preferencia de dashboard do usuario
- Tags: Dashboard Preferences
- Parametros:
  - `scope` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `PUT /api/v1/dashboard-preferences/{scope}`

- Nome: `put_dashboard_preference_api_v1_dashboard_preferences__scope__put`
- Objetivo: Salvar preferencia de dashboard do usuario
- Tags: Dashboard Preferences
- Parametros:
  - `scope` em `path` (obrigatorio)
- Payload: DashboardPreferenceUpdate
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
- Parametros:
  - `force_full` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
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

### `GET /api/v2/admin/tools`

- Nome: `list_admin_tools_api_v2_admin_tools_get`
- Objetivo: List Admin Tools
- Tags: Governed AI Tool Registry Admin V2
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/admin/tools`

- Nome: `register_admin_tool_api_v2_admin_tools_post`
- Objetivo: Register Admin Tool
- Tags: Governed AI Tool Registry Admin V2
- Parametros: nenhum parametro explicito no schema.
- Payload: AIToolRegistrationRequestV2
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/admin/tools/inspector/test`

- Nome: `test_tool_synthetic_api_v2_admin_tools_inspector_test_post`
- Objetivo: Test Tool Synthetic
- Tags: Governed AI Tool Registry Admin V2
- Parametros: nenhum parametro explicito no schema.
- Payload: AIToolInvocationRequestV2
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/admin/tools/snapshots`

- Nome: `list_snapshots_api_v2_admin_tools_snapshots_get`
- Objetivo: List Snapshots
- Tags: Governed AI Tool Registry Admin V2
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/admin/tools/{tool_id}/versions/{version}/disable`

- Nome: `disable_tool_version_api_v2_admin_tools__tool_id__versions__version__disable_post`
- Objetivo: Disable Tool Version
- Tags: Governed AI Tool Registry Admin V2
- Parametros:
  - `tool_id` em `path` (obrigatorio)
  - `version` em `path` (obrigatorio)
  - `reason` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/admin/tools/{tool_id}/versions/{version}/publish`

- Nome: `publish_tool_version_api_v2_admin_tools__tool_id__versions__version__publish_post`
- Objetivo: Publish Tool Version
- Tags: Governed AI Tool Registry Admin V2
- Parametros:
  - `tool_id` em `path` (obrigatorio)
  - `version` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/admin/tools/{tool_id}/versions/{version}/review`

- Nome: `review_tool_version_api_v2_admin_tools__tool_id__versions__version__review_post`
- Objetivo: Review Tool Version
- Tags: Governed AI Tool Registry Admin V2
- Parametros:
  - `tool_id` em `path` (obrigatorio)
  - `version` em `path` (obrigatorio)
- Payload: ReviewPayload
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/ai-orchestration/inspector/simulate`

- Nome: `simulate_inspection_api_v2_ai_orchestration_inspector_simulate_post`
- Objetivo: Simulate Inspection
- Tags: AI Orchestration V2
- Parametros: nenhum parametro explicito no schema.
- Payload: AIOrchestrationRequestV2
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/ai-orchestration/models`

- Nome: `list_model_definitions_api_v2_ai_orchestration_models_get`
- Objetivo: List Model Definitions
- Tags: AI Orchestration V2
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/ai-orchestration/policies`

- Nome: `get_orchestration_policies_api_v2_ai_orchestration_policies_get`
- Objetivo: Get Orchestration Policies
- Tags: AI Orchestration V2
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/ai-orchestration/prompts`

- Nome: `list_prompt_templates_api_v2_ai_orchestration_prompts_get`
- Objetivo: List Prompt Templates
- Tags: AI Orchestration V2
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/ai-orchestration/providers`

- Nome: `list_provider_definitions_api_v2_ai_orchestration_providers_get`
- Objetivo: List Provider Definitions
- Tags: AI Orchestration V2
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/ai-orchestration/run`

- Nome: `run_ai_orchestration_api_v2_ai_orchestration_run_post`
- Objetivo: Run Ai Orchestration
- Tags: AI Orchestration V2
- Parametros: nenhum parametro explicito no schema.
- Payload: AIOrchestrationRequestV2
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/analytical-postgresql/catalog`

- Nome: `get_analytical_catalog_api_v2_analytical_postgresql_catalog_get`
- Objetivo: Get Analytical Catalog
- Tags: Safe Analytical PostgreSQL
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/analytical-postgresql/compile`

- Nome: `compile_analytical_query_api_v2_analytical_postgresql_compile_post`
- Objetivo: Compile Analytical Query
- Tags: Safe Analytical PostgreSQL
- Parametros: nenhum parametro explicito no schema.
- Payload: CompileRequest
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/analytical-postgresql/execute`

- Nome: `execute_analytical_query_api_v2_analytical_postgresql_execute_post`
- Objetivo: Execute Analytical Query
- Tags: Safe Analytical PostgreSQL
- Parametros: nenhum parametro explicito no schema.
- Payload: ExecuteRequest
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/enterprise-knowledge/assets`

- Nome: `list_assets_api_v2_enterprise_knowledge_assets_get`
- Objetivo: List Assets
- Tags: Enterprise Knowledge V2
- Parametros:
  - `limit` em `query` (opcional)
  - `lifecycle` em `query` (opcional)
  - `asset_type` em `query` (opcional)
  - `domain` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/enterprise-knowledge/assets`

- Nome: `create_asset_api_v2_enterprise_knowledge_assets_post`
- Objetivo: Create Asset
- Tags: Enterprise Knowledge V2
- Parametros: nenhum parametro explicito no schema.
- Payload: KnowledgeAssetCreateV2
- Codigos HTTP documentados: 201, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `DELETE /api/v2/enterprise-knowledge/assets/{asset_id}`

- Nome: `soft_delete_asset_api_v2_enterprise_knowledge_assets__asset_id__delete`
- Objetivo: Soft Delete Asset
- Tags: Enterprise Knowledge V2
- Parametros:
  - `asset_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/enterprise-knowledge/assets/{asset_id}`

- Nome: `get_asset_api_v2_enterprise_knowledge_assets__asset_id__get`
- Objetivo: Get Asset
- Tags: Enterprise Knowledge V2
- Parametros:
  - `asset_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/enterprise-knowledge/assets/{asset_id}/archive`

- Nome: `archive_asset_api_v2_enterprise_knowledge_assets__asset_id__archive_post`
- Objetivo: Archive Asset
- Tags: Enterprise Knowledge V2
- Parametros:
  - `asset_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/enterprise-knowledge/assets/{asset_id}/audit`

- Nome: `asset_audit_api_v2_enterprise_knowledge_assets__asset_id__audit_get`
- Objetivo: Asset Audit
- Tags: Enterprise Knowledge V2
- Parametros:
  - `asset_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/enterprise-knowledge/assets/{asset_id}/diff`

- Nome: `version_diff_api_v2_enterprise_knowledge_assets__asset_id__diff_post`
- Objetivo: Version Diff
- Tags: Enterprise Knowledge V2
- Parametros:
  - `asset_id` em `path` (obrigatorio)
- Payload: DiffQuery
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/enterprise-knowledge/assets/{asset_id}/drafts`

- Nome: `create_draft_api_v2_enterprise_knowledge_assets__asset_id__drafts_post`
- Objetivo: Create Draft
- Tags: Enterprise Knowledge V2
- Parametros:
  - `asset_id` em `path` (obrigatorio)
- Payload: DraftAction
- Codigos HTTP documentados: 201, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/enterprise-knowledge/assets/{asset_id}/ownership`

- Nome: `transfer_ownership_api_v2_enterprise_knowledge_assets__asset_id__ownership_post`
- Objetivo: Transfer Ownership
- Tags: Enterprise Knowledge V2
- Parametros:
  - `asset_id` em `path` (obrigatorio)
- Payload: OwnershipAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/enterprise-knowledge/assets/{asset_id}/rollback`

- Nome: `rollback_asset_api_v2_enterprise_knowledge_assets__asset_id__rollback_post`
- Objetivo: Rollback Asset
- Tags: Enterprise Knowledge V2
- Parametros:
  - `asset_id` em `path` (obrigatorio)
- Payload: RollbackAction
- Codigos HTTP documentados: 201, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/enterprise-knowledge/assets/{asset_id}/versions`

- Nome: `list_versions_api_v2_enterprise_knowledge_assets__asset_id__versions_get`
- Objetivo: List Versions
- Tags: Enterprise Knowledge V2
- Parametros:
  - `asset_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `PUT /api/v2/enterprise-knowledge/assets/{asset_id}/versions/{version_id}`

- Nome: `update_draft_api_v2_enterprise_knowledge_assets__asset_id__versions__version_id__put`
- Objetivo: Update Draft
- Tags: Enterprise Knowledge V2
- Parametros:
  - `asset_id` em `path` (obrigatorio)
  - `version_id` em `path` (obrigatorio)
- Payload: KnowledgeVersionUpdateV2
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/enterprise-knowledge/assets/{asset_id}/versions/{version_id}/deprecate`

- Nome: `deprecate_version_api_v2_enterprise_knowledge_assets__asset_id__versions__version_id__deprecate_post`
- Objetivo: Deprecate Version
- Tags: Enterprise Knowledge V2
- Parametros:
  - `asset_id` em `path` (obrigatorio)
  - `version_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/enterprise-knowledge/assets/{asset_id}/versions/{version_id}/publish`

- Nome: `publish_version_api_v2_enterprise_knowledge_assets__asset_id__versions__version_id__publish_post`
- Objetivo: Publish Version
- Tags: Enterprise Knowledge V2
- Parametros:
  - `asset_id` em `path` (obrigatorio)
  - `version_id` em `path` (obrigatorio)
- Payload: routers__enterprise_knowledge__PublishAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/enterprise-knowledge/assets/{asset_id}/versions/{version_id}/review`

- Nome: `review_version_api_v2_enterprise_knowledge_assets__asset_id__versions__version_id__review_post`
- Objetivo: Review Version
- Tags: Enterprise Knowledge V2
- Parametros:
  - `asset_id` em `path` (obrigatorio)
  - `version_id` em `path` (obrigatorio)
- Payload: routers__enterprise_knowledge__ReviewAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/enterprise-knowledge/assets/{asset_id}/versions/{version_id}/submit`

- Nome: `submit_review_api_v2_enterprise_knowledge_assets__asset_id__versions__version_id__submit_post`
- Objetivo: Submit Review
- Tags: Enterprise Knowledge V2
- Parametros:
  - `asset_id` em `path` (obrigatorio)
  - `version_id` em `path` (obrigatorio)
- Payload: LockAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/enterprise-knowledge/exports/{export_format}`

- Nome: `export_knowledge_api_v2_enterprise_knowledge_exports__export_format__get`
- Objetivo: Export Knowledge
- Tags: Enterprise Knowledge V2
- Parametros:
  - `export_format` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/enterprise-knowledge/glossary`

- Nome: `search_glossary_api_v2_enterprise_knowledge_glossary_get`
- Objetivo: Search Glossary
- Tags: Enterprise Knowledge V2
- Parametros:
  - `query` em `query` (obrigatorio)
  - `locale` em `query` (opcional)
  - `limit` em `query` (opcional)
  - `cursor` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/enterprise-knowledge/imports`

- Nome: `import_knowledge_api_v2_enterprise_knowledge_imports_post`
- Objetivo: Import Knowledge
- Tags: Enterprise Knowledge V2
- Parametros: nenhum parametro explicito no schema.
- Payload: KnowledgeImportRequestV2
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/enterprise-knowledge/metrics/{canonical_metric_id}`

- Nome: `get_metric_definition_api_v2_enterprise_knowledge_metrics__canonical_metric_id__get`
- Objetivo: Get Metric Definition
- Tags: Enterprise Knowledge V2
- Parametros:
  - `canonical_metric_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/enterprise-knowledge/published/{canonical_key}`

- Nome: `get_published_asset_api_v2_enterprise_knowledge_published__canonical_key__get`
- Objetivo: Get Published Asset
- Tags: Enterprise Knowledge V2
- Parametros:
  - `canonical_key` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/enterprise-knowledge/review-queue`

- Nome: `review_queue_api_v2_enterprise_knowledge_review_queue_get`
- Objetivo: Review Queue
- Tags: Enterprise Knowledge V2
- Parametros:
  - `limit` em `query` (opcional)
  - `asset_type` em `query` (opcional)
  - `domain` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/enterprise-knowledge/search`

- Nome: `search_published_knowledge_api_v2_enterprise_knowledge_search_post`
- Objetivo: Search Published Knowledge
- Tags: Enterprise Knowledge V2
- Parametros: nenhum parametro explicito no schema.
- Payload: KnowledgeSearchRequestV2
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/feedback/capabilities`

- Nome: `capabilities_api_v2_feedback_capabilities_get`
- Objetivo: Capabilities
- Tags: Governed Feedback V2
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/feedback/datasets`

- Nome: `list_datasets_api_v2_feedback_datasets_get`
- Objetivo: List Datasets
- Tags: Governed Feedback V2
- Parametros:
  - `dataset_id` em `query` (opcional)
  - `limit` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/feedback/datasets`

- Nome: `create_dataset_api_v2_feedback_datasets_post`
- Objetivo: Create Dataset
- Tags: Governed Feedback V2
- Parametros: nenhum parametro explicito no schema.
- Payload: DatasetCreate
- Codigos HTTP documentados: 201, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/feedback/datasets/snapshots/{snapshot_id}`

- Nome: `get_dataset_snapshot_api_v2_feedback_datasets_snapshots__snapshot_id__get`
- Objetivo: Get Dataset Snapshot
- Tags: Governed Feedback V2
- Parametros:
  - `snapshot_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/feedback/datasets/{snapshot_id}/export`

- Nome: `export_dataset_api_v2_feedback_datasets__snapshot_id__export_post`
- Objetivo: Export Dataset
- Tags: Governed Feedback V2
- Parametros:
  - `snapshot_id` em `path` (obrigatorio)
- Payload: DatasetExportAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/feedback/datasets/{snapshot_id}/publish`

- Nome: `publish_dataset_api_v2_feedback_datasets__snapshot_id__publish_post`
- Objetivo: Publish Dataset
- Tags: Governed Feedback V2
- Parametros:
  - `snapshot_id` em `path` (obrigatorio)
- Payload: LockAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/feedback/datasets/{snapshot_id}/transition`

- Nome: `transition_dataset_api_v2_feedback_datasets__snapshot_id__transition_post`
- Objetivo: Transition Dataset
- Tags: Governed Feedback V2
- Parametros:
  - `snapshot_id` em `path` (obrigatorio)
- Payload: DatasetTransition
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/feedback/duplicate-groups/{duplicate_fingerprint}`

- Nome: `duplicate_group_api_v2_feedback_duplicate_groups__duplicate_fingerprint__get`
- Objetivo: Duplicate Group
- Tags: Governed Feedback V2
- Parametros:
  - `duplicate_fingerprint` em `path` (obrigatorio)
  - `limit` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/feedback/import/dry-run`

- Nome: `dry_run_governed_import_api_v2_feedback_import_dry_run_post`
- Objetivo: Dry Run Governed Import
- Tags: Governed Feedback V2
- Parametros: nenhum parametro explicito no schema.
- Payload: GovernedImportDryRunRequestV2
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/feedback/retention/expire`

- Nome: `expire_feedback_by_retention_api_v2_feedback_retention_expire_post`
- Objetivo: Expire Feedback By Retention
- Tags: Governed Feedback V2
- Parametros: nenhum parametro explicito no schema.
- Payload: RetentionAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/feedback/review/queue`

- Nome: `review_queue_api_v2_feedback_review_queue_get`
- Objetivo: Review Queue
- Tags: Governed Feedback V2
- Parametros:
  - `lifecycle` em `query` (opcional)
  - `review_queue_name` em `query` (opcional)
  - `limit` em `query` (opcional)
  - `after_created_at` em `query` (opcional)
  - `after_id` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/feedback/shadow-evaluate`

- Nome: `shadow_evaluate_feedback_api_v2_feedback_shadow_evaluate_post`
- Objetivo: Shadow Evaluate Feedback
- Tags: Governed Feedback V2
- Parametros: nenhum parametro explicito no schema.
- Payload: FeedbackSubmissionV2
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/feedback/training-candidates`

- Nome: `list_training_candidates_api_v2_feedback_training_candidates_get`
- Objetivo: List Training Candidates
- Tags: Governed Feedback V2
- Parametros:
  - `candidate_status` em `query` (opcional)
  - `limit` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/feedback/training-candidates/{candidate_id}/approve`

- Nome: `approve_training_candidate_api_v2_feedback_training_candidates__candidate_id__approve_post`
- Objetivo: Approve Training Candidate
- Tags: Governed Feedback V2
- Parametros:
  - `candidate_id` em `path` (obrigatorio)
- Payload: CandidateApproval
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/feedback/training-candidates/{candidate_id}/reject`

- Nome: `reject_training_candidate_api_v2_feedback_training_candidates__candidate_id__reject_post`
- Objetivo: Reject Training Candidate
- Tags: Governed Feedback V2
- Parametros:
  - `candidate_id` em `path` (obrigatorio)
- Payload: LockAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/feedback/training-candidates/{candidate_id}/validate`

- Nome: `validate_training_candidate_api_v2_feedback_training_candidates__candidate_id__validate_post`
- Objetivo: Validate Training Candidate
- Tags: Governed Feedback V2
- Parametros:
  - `candidate_id` em `path` (obrigatorio)
- Payload: LockAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/feedback/training-examples`

- Nome: `list_training_examples_api_v2_feedback_training_examples_get`
- Objetivo: List Training Examples
- Tags: Governed Feedback V2
- Parametros:
  - `limit` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/feedback/{feedback_id}`

- Nome: `get_feedback_for_review_api_v2_feedback__feedback_id__get`
- Objetivo: Get Feedback For Review
- Tags: Governed Feedback V2
- Parametros:
  - `feedback_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/feedback/{feedback_id}/approve`

- Nome: `approve_feedback_api_v2_feedback__feedback_id__approve_post`
- Objetivo: Approve Feedback
- Tags: Governed Feedback V2
- Parametros:
  - `feedback_id` em `path` (obrigatorio)
- Payload: LockAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/feedback/{feedback_id}/reject`

- Nome: `reject_feedback_api_v2_feedback__feedback_id__reject_post`
- Objetivo: Reject Feedback
- Tags: Governed Feedback V2
- Parametros:
  - `feedback_id` em `path` (obrigatorio)
- Payload: LockAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/feedback/{feedback_id}/request-information`

- Nome: `request_information_api_v2_feedback__feedback_id__request_information_post`
- Objetivo: Request Information
- Tags: Governed Feedback V2
- Parametros:
  - `feedback_id` em `path` (obrigatorio)
- Payload: LockAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/feedback/{feedback_id}/review`

- Nome: `review_feedback_api_v2_feedback__feedback_id__review_post`
- Objetivo: Review Feedback
- Tags: Governed Feedback V2
- Parametros:
  - `feedback_id` em `path` (obrigatorio)
- Payload: routers__supervised_feedback__ReviewAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/feedback/{feedback_id}/reviewer`

- Nome: `assign_reviewer_api_v2_feedback__feedback_id__reviewer_post`
- Objetivo: Assign Reviewer
- Tags: Governed Feedback V2
- Parametros:
  - `feedback_id` em `path` (obrigatorio)
- Payload: ReviewerAssignment
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/feedback/{feedback_id}/training-candidate`

- Nome: `create_training_candidate_api_v2_feedback__feedback_id__training_candidate_post`
- Objetivo: Create Training Candidate
- Tags: Governed Feedback V2
- Parametros:
  - `feedback_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 201, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/me/analytical-profile`

- Nome: `get_profile_api_v2_me_analytical_profile_get`
- Objetivo: Get Profile
- Tags: User Analytical Profile V2
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/me/analytical-profile/capabilities`

- Nome: `capabilities_api_v2_me_analytical_profile_capabilities_get`
- Objetivo: Capabilities
- Tags: User Analytical Profile V2
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/me/analytical-profile/deletion-requests`

- Nome: `request_deletion_api_v2_me_analytical_profile_deletion_requests_post`
- Objetivo: Request Deletion
- Tags: User Analytical Profile V2
- Parametros:
  - `Idempotency-Key` em `header` (obrigatorio)
- Payload: routers__user_analytical_profile__DeletionAction
- Codigos HTTP documentados: 202, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/me/analytical-profile/disable`

- Nome: `disable_profile_api_v2_me_analytical_profile_disable_post`
- Objetivo: Disable Profile
- Tags: User Analytical Profile V2
- Parametros: nenhum parametro explicito no schema.
- Payload: LockAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/me/analytical-profile/import/confirm`

- Nome: `import_confirm_api_v2_me_analytical_profile_import_confirm_post`
- Objetivo: Import Confirm
- Tags: User Analytical Profile V2
- Parametros: nenhum parametro explicito no schema.
- Payload: ProfileImportV2
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/me/analytical-profile/import/dry-run`

- Nome: `import_dry_run_api_v2_me_analytical_profile_import_dry_run_post`
- Objetivo: Import Dry Run
- Tags: User Analytical Profile V2
- Parametros: nenhum parametro explicito no schema.
- Payload: ProfileImportV2
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/me/analytical-profile/reactivate`

- Nome: `reactivate_profile_api_v2_me_analytical_profile_reactivate_post`
- Objetivo: Reactivate Profile
- Tags: User Analytical Profile V2
- Parametros: nenhum parametro explicito no schema.
- Payload: LockAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/me/analytical-profile/summary`

- Nome: `get_summary_api_v2_me_analytical_profile_summary_get`
- Objetivo: Get Summary
- Tags: User Analytical Profile V2
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/me/feedback`

- Nome: `list_own_feedback_api_v2_me_feedback_get`
- Objetivo: List Own Feedback
- Tags: Governed Feedback V2
- Parametros:
  - `limit` em `query` (opcional)
  - `after_created_at` em `query` (opcional)
  - `after_id` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/me/feedback`

- Nome: `submit_feedback_api_v2_me_feedback_post`
- Objetivo: Submit Feedback
- Tags: Governed Feedback V2
- Parametros: nenhum parametro explicito no schema.
- Payload: FeedbackSubmissionV2
- Codigos HTTP documentados: 201, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/me/feedback-export`

- Nome: `export_own_feedback_api_v2_me_feedback_export_get`
- Objetivo: Export Own Feedback
- Tags: Governed Feedback V2
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/me/feedback/{feedback_id}`

- Nome: `get_own_feedback_api_v2_me_feedback__feedback_id__get`
- Objetivo: Get Own Feedback
- Tags: Governed Feedback V2
- Parametros:
  - `feedback_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `PATCH /api/v2/me/feedback/{feedback_id}`

- Nome: `update_feedback_explanation_api_v2_me_feedback__feedback_id__patch`
- Objetivo: Update Feedback Explanation
- Tags: Governed Feedback V2
- Parametros:
  - `feedback_id` em `path` (obrigatorio)
- Payload: ExplanationUpdate
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/me/feedback/{feedback_id}/deletion-request`

- Nome: `request_feedback_deletion_api_v2_me_feedback__feedback_id__deletion_request_post`
- Objetivo: Request Feedback Deletion
- Tags: Governed Feedback V2
- Parametros:
  - `feedback_id` em `path` (obrigatorio)
- Payload: routers__supervised_feedback__DeletionAction
- Codigos HTTP documentados: 202, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/me/feedback/{feedback_id}/information-response`

- Nome: `respond_to_information_request_api_v2_me_feedback__feedback_id__information_response_post`
- Objetivo: Respond To Information Request
- Tags: Governed Feedback V2
- Parametros:
  - `feedback_id` em `path` (obrigatorio)
- Payload: ExplanationUpdate
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/me/feedback/{feedback_id}/withdraw`

- Nome: `withdraw_feedback_api_v2_me_feedback__feedback_id__withdraw_post`
- Objetivo: Withdraw Feedback
- Tags: Governed Feedback V2
- Parametros:
  - `feedback_id` em `path` (obrigatorio)
- Payload: LockAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/me/preferences`

- Nome: `list_preferences_api_v2_me_preferences_get`
- Objetivo: List Preferences
- Tags: User Analytical Profile V2
- Parametros:
  - `include_inactive` em `query` (opcional)
  - `limit` em `query` (opcional)
  - `after_id` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/me/preferences`

- Nome: `create_preference_api_v2_me_preferences_post`
- Objetivo: Create Preference
- Tags: User Analytical Profile V2
- Parametros: nenhum parametro explicito no schema.
- Payload: PreferenceCreateV2
- Codigos HTTP documentados: 201, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/me/preferences/applicable`

- Nome: `applicable_preferences_api_v2_me_preferences_applicable_get`
- Objetivo: Applicable Preferences
- Tags: User Analytical Profile V2
- Parametros:
  - `limit` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `DELETE /api/v2/me/preferences/{preference_id}`

- Nome: `delete_preference_api_v2_me_preferences__preference_id__delete`
- Objetivo: Delete Preference
- Tags: User Analytical Profile V2
- Parametros:
  - `preference_id` em `path` (obrigatorio)
- Payload: LockAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/me/preferences/{preference_id}`

- Nome: `get_preference_api_v2_me_preferences__preference_id__get`
- Objetivo: Get Preference
- Tags: User Analytical Profile V2
- Parametros:
  - `preference_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `PUT /api/v2/me/preferences/{preference_id}`

- Nome: `update_preference_api_v2_me_preferences__preference_id__put`
- Objetivo: Update Preference
- Tags: User Analytical Profile V2
- Parametros:
  - `preference_id` em `path` (obrigatorio)
- Payload: PreferenceUpdateV2
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `DELETE /api/v2/me/preferences/{preference_id}/consent`

- Nome: `revoke_consent_api_v2_me_preferences__preference_id__consent_delete`
- Objetivo: Revoke Consent
- Tags: User Analytical Profile V2
- Parametros:
  - `preference_id` em `path` (obrigatorio)
- Payload: ConsentRevokeV2
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/me/preferences/{preference_id}/consent`

- Nome: `grant_consent_api_v2_me_preferences__preference_id__consent_post`
- Objetivo: Grant Consent
- Tags: User Analytical Profile V2
- Parametros:
  - `preference_id` em `path` (obrigatorio)
- Payload: ConsentGrantV2
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/me/preferences/{preference_id}/disable`

- Nome: `disable_preference_api_v2_me_preferences__preference_id__disable_post`
- Objetivo: Disable Preference
- Tags: User Analytical Profile V2
- Parametros:
  - `preference_id` em `path` (obrigatorio)
- Payload: LockAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/me/preferences/{preference_id}/reactivate`

- Nome: `reactivate_preference_api_v2_me_preferences__preference_id__reactivate_post`
- Objetivo: Reactivate Preference
- Tags: User Analytical Profile V2
- Parametros:
  - `preference_id` em `path` (obrigatorio)
- Payload: LockAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/me/preferences/{preference_id}/revoke`

- Nome: `revoke_preference_api_v2_me_preferences__preference_id__revoke_post`
- Objetivo: Revoke Preference
- Tags: User Analytical Profile V2
- Parametros:
  - `preference_id` em `path` (obrigatorio)
- Payload: LockAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/me/profile/export`

- Nome: `export_profile_api_v2_me_profile_export_get`
- Objetivo: Export Profile
- Tags: User Analytical Profile V2
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/me/profile/export`

- Nome: `export_profile_api_v2_me_profile_export_post`
- Objetivo: Export Profile
- Tags: User Analytical Profile V2
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/semantic/admin/audit`

- Nome: `audit_events_api_v2_semantic_admin_audit_get`
- Objetivo: Audit Events
- Tags: Governed Semantic Retrieval V2
- Parametros:
  - `index_id` em `query` (opcional)
  - `limit` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/semantic/admin/indexes`

- Nome: `list_indexes_api_v2_semantic_admin_indexes_get`
- Objetivo: List Indexes
- Tags: Governed Semantic Retrieval V2
- Parametros:
  - `limit` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/semantic/admin/indexes/default`

- Nome: `create_default_index_api_v2_semantic_admin_indexes_default_post`
- Objetivo: Create Default Index
- Tags: Governed Semantic Retrieval V2
- Parametros: nenhum parametro explicito no schema.
- Payload: DefinitionCreateAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `PATCH /api/v2/semantic/admin/indexes/{index_id}`

- Nome: `update_index_definition_api_v2_semantic_admin_indexes__index_id__patch`
- Objetivo: Update Index Definition
- Tags: Governed Semantic Retrieval V2
- Parametros:
  - `index_id` em `path` (obrigatorio)
- Payload: DefinitionUpdateAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/semantic/admin/indexes/{index_id}/build`

- Nome: `build_index_api_v2_semantic_admin_indexes__index_id__build_post`
- Objetivo: Build Index
- Tags: Governed Semantic Retrieval V2
- Parametros:
  - `index_id` em `path` (obrigatorio)
- Payload: IndexBuildRequestV2
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/semantic/admin/indexes/{index_id}/evaluations`

- Nome: `list_evaluations_api_v2_semantic_admin_indexes__index_id__evaluations_get`
- Objetivo: List Evaluations
- Tags: Governed Semantic Retrieval V2
- Parametros:
  - `index_id` em `path` (obrigatorio)
  - `before` em `query` (opcional)
  - `limit` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/semantic/admin/indexes/{index_id}/evaluations`

- Nome: `run_evaluation_api_v2_semantic_admin_indexes__index_id__evaluations_post`
- Objetivo: Run Evaluation
- Tags: Governed Semantic Retrieval V2
- Parametros:
  - `index_id` em `path` (obrigatorio)
- Payload: EvaluationAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/semantic/admin/indexes/{index_id}/publish`

- Nome: `publish_index_api_v2_semantic_admin_indexes__index_id__publish_post`
- Objetivo: Publish Index
- Tags: Governed Semantic Retrieval V2
- Parametros:
  - `index_id` em `path` (obrigatorio)
- Payload: routers__semantic_retrieval__PublishAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/semantic/admin/indexes/{index_id}/rollback`

- Nome: `rollback_index_api_v2_semantic_admin_indexes__index_id__rollback_post`
- Objetivo: Rollback Index
- Tags: Governed Semantic Retrieval V2
- Parametros:
  - `index_id` em `path` (obrigatorio)
- Payload: IndexRollbackV2
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/semantic/admin/indexes/{index_id}/stale-sources`

- Nome: `list_stale_sources_api_v2_semantic_admin_indexes__index_id__stale_sources_get`
- Objetivo: List Stale Sources
- Tags: Governed Semantic Retrieval V2
- Parametros:
  - `index_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/semantic/admin/indexes/{index_id}/versions`

- Nome: `list_versions_api_v2_semantic_admin_indexes__index_id__versions_get`
- Objetivo: List Versions
- Tags: Governed Semantic Retrieval V2
- Parametros:
  - `index_id` em `path` (obrigatorio)
  - `limit` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/semantic/admin/indexes/{index_id}/versions/{version_id}`

- Nome: `inspect_version_api_v2_semantic_admin_indexes__index_id__versions__version_id__get`
- Objetivo: Inspect Version
- Tags: Governed Semantic Retrieval V2
- Parametros:
  - `index_id` em `path` (obrigatorio)
  - `version_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/semantic/admin/indexes/{index_id}/versions/{version_id}/deprecate`

- Nome: `deprecate_index_version_api_v2_semantic_admin_indexes__index_id__versions__version_id__deprecate_post`
- Objetivo: Deprecate Index Version
- Tags: Governed Semantic Retrieval V2
- Parametros:
  - `index_id` em `path` (obrigatorio)
  - `version_id` em `path` (obrigatorio)
- Payload: DeprecateAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/semantic/admin/indexes/{index_id}/versions/{version_id}/manifest`

- Nome: `export_index_manifest_api_v2_semantic_admin_indexes__index_id__versions__version_id__manifest_get`
- Objetivo: Export Index Manifest
- Tags: Governed Semantic Retrieval V2
- Parametros:
  - `index_id` em `path` (obrigatorio)
  - `version_id` em `path` (obrigatorio)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/semantic/admin/observability`

- Nome: `observability_api_v2_semantic_admin_observability_get`
- Objetivo: Observability
- Tags: Governed Semantic Retrieval V2
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/semantic/admin/search`

- Nome: `inspect_search_api_v2_semantic_admin_search_post`
- Objetivo: Inspect Search
- Tags: Governed Semantic Retrieval V2
- Parametros: nenhum parametro explicito no schema.
- Payload: SemanticSearchRequestV2
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/semantic/candidates/{document_id}`

- Nome: `public_candidate_detail_api_v2_semantic_candidates__document_id__get`
- Objetivo: Public Candidate Detail
- Tags: Governed Semantic Retrieval V2
- Parametros:
  - `document_id` em `path` (obrigatorio)
  - `index_id` em `query` (opcional)
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/semantic/capabilities`

- Nome: `capabilities_api_v2_semantic_capabilities_get`
- Objetivo: Capabilities
- Tags: Governed Semantic Retrieval V2
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/semantic/clarifications/{clarification_id}/resolve`

- Nome: `resolve_clarification_api_v2_semantic_clarifications__clarification_id__resolve_post`
- Objetivo: Resolve Clarification
- Tags: Governed Semantic Retrieval V2
- Parametros:
  - `clarification_id` em `path` (obrigatorio)
- Payload: ClarificationResolveAction
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/semantic/entities/resolve`

- Nome: `resolve_entity_api_v2_semantic_entities_resolve_post`
- Objetivo: Resolve Entity
- Tags: Governed Semantic Retrieval V2
- Parametros: nenhum parametro explicito no schema.
- Payload: EntityResolutionRequestV2
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/semantic/resolve`

- Nome: `resolve_api_v2_semantic_resolve_post`
- Objetivo: Resolve
- Tags: Governed Semantic Retrieval V2
- Parametros: nenhum parametro explicito no schema.
- Payload: EntityResolutionRequestV2
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/semantic/search`

- Nome: `search_api_v2_semantic_search_post`
- Objetivo: Search
- Tags: Governed Semantic Retrieval V2
- Parametros: nenhum parametro explicito no schema.
- Payload: SemanticSearchRequestV2
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/tools/catalog`

- Nome: `get_tool_catalog_api_v2_tools_catalog_get`
- Objetivo: Get Tool Catalog
- Tags: Governed AI Tool Registry V2
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/tools/invoke`

- Nome: `invoke_governed_tool_api_v2_tools_invoke_post`
- Objetivo: Invoke Governed Tool
- Tags: Governed AI Tool Registry V2
- Parametros: nenhum parametro explicito no schema.
- Payload: AIToolInvocationRequestV2
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/tools/validate-proposal`

- Nome: `validate_tool_proposal_api_v2_tools_validate_proposal_post`
- Objetivo: Validate Tool Proposal
- Tags: Governed AI Tool Registry V2
- Parametros: nenhum parametro explicito no schema.
- Payload: ProposalValidationRequest
- Codigos HTTP documentados: 200, 422
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `GET /api/v2/validation/policy/default`

- Nome: `get_default_policy_api_v2_validation_policy_default_get`
- Objetivo: Get Default Policy
- Tags: Validation & Provenance V2
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.

### `POST /api/v2/validation/run`

- Nome: `run_validation_pipeline_api_v2_validation_run_post`
- Objetivo: Run Validation Pipeline
- Tags: Validation & Provenance V2
- Parametros: nenhum parametro explicito no schema.
- Payload: ValidationRunRequestBody
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

### `GET /health/deep`

- Nome: `deep_health_check_health_deep_get`
- Objetivo: Verificacao profunda de saude da API
- Tags: Sistema
- Parametros: nenhum parametro explicito no schema.
- Payload: sem corpo de requisicao.
- Codigos HTTP documentados: 200
- Permissoes: aplicadas por dependencias FastAPI e regras do router quando existentes.
- Exemplo minimo: chamar com `Authorization: Bearer <token>` quando autenticado.
