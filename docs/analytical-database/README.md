# Banco Analitico

## Visao Geral

O banco analitico usa PostgreSQL com SQLAlchemy async no backend. Ele armazena tenants, usuarios, catalogos de views, historico, favoritos, metadados, semantic catalog, business knowledge, blueprints, datasets, packages, dashboard templates/instances e fila de sync.

## Arquivos

- `backend/database.py`: engine async e sessao.
- `backend/database/init.sql`: estrutura inicial.
- `backend/database/migration_v*.py`: migracoes incrementais.
- `backend/models/`: modelos SQLAlchemy.

## Tabelas Detectadas No SQL Inicial

- `blueprint_repository`
- `dashboard_instances`
- `dashboard_studio_versions`
- `dashboard_templates`
- `data_platform_history`
- `datasets`
- `favorites`
- `metadata_catalog`
- `search_history`
- `semantic_catalog`
- `tenants`
- `users`
- `view_catalog`

## Modelos Principais

- Tenant/User: multi-tenant e RBAC.
- ViewCatalog: catalogo de views analiticas.
- SearchHistory/Favorite: historico e favoritos.
- MetadataCatalog/Version: catalogo tecnico e versionamento.
- SemanticCatalog: sinonimos/conceitos semanticos.
- BusinessConcept/KPI/Formula/Relationship/GovernanceLog: Business Knowledge.
- Blueprint/Dataset: inteligencia analitica e datasets runtime.
- AnalyticalPackage/PackageDashboardInstance: reuso de packages.
- DashboardTemplate/Instance/StudioVersion: Dashboard Studio.
- SyncQueue/DataPlatformHistory: sincronizacao e historico.

## Estrategia De Atualizacao

O Sync Engine atualiza/clona views conforme configuracao de tenant. O Scheduler dispara tarefas em background. Health e lineage sao recalculados por CatalogAPI/HealthMonitor quando aplicavel.

## Limitacoes

- RLS nativo de PostgreSQL nao foi identificado no codigo; o isolamento ocorre via aplicacao.
- EXPLAIN ANALYZE com dados reais deve ser executado no ambiente final.
