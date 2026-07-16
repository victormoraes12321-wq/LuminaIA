# Documentacao Dos Modulos

Este documento descreve os modulos principais. Para inventario completo de arquivos/classes/funcoes, consulte [source-inventory.md](source-inventory.md).

## Query Intelligence Engine

- Localizacao: `backend/services/query_intelligence_engine.py`.
- Objetivo: orquestrar consulta inteligente, matching/evolucao de blueprints, planner, validator, execucao e resposta.
- Entradas: pergunta, usuario, tenant, contexto, historico e catalogo.
- Saidas: `QueryResponse`, chart data, visualizations, BI intelligence, telemetria e blueprint/runtime quando disponivel.
- Dependencias: `ai_service`, `query_planner`, `plan_validator`, Data Platform, transformers e routers.
- Limitacoes: ainda mantem compatibilidade com fluxo legado e arquivo `services/blueprints.json`.

## Corporate Intelligence Engine

- Localizacao: `backend/services/ai/`.
- Objetivo: estruturar a IA em engines de intencao, semantica, contexto, negocio, KPIs, visual strategy, blueprint, package matching, confianca, memoria, analise executiva e resposta.
- Entradas: pergunta, contexto CIE, catalogos e pacotes disponiveis.
- Saidas: Business Intent, blueprint, visual strategy, resposta executiva/natural.
- Dependencias: schemas em `services/ai/schemas.py`, Business Layer, Metadata/Semantic Catalog e Analytical Packages.
- Limitacoes: nao deve consultar banco nem calcular metricas finais.

## Backend Routers

- Localizacao: `backend/routers/`.
- Objetivo: expor contratos HTTP.
- Entradas: requests HTTP, JWT/cookies, parametros e payloads Pydantic.
- Saidas: JSON padronizado e codigos HTTP.
- Dependencias: services, schemas, models e dependencias de autenticacao.

## Business Layer

- Localizacao: `backend/services/business/` e `backend/services/data_platform/business_layer.py`.
- Objetivo: dicionario de negocio, KPIs, formulas, validacoes, governanca, dependencias e relacionamentos.
- Entradas: metricas, conceitos, formulas, blueprints e requisicoes administrativas.
- Saidas: validacoes, registros de KPI/conceito/formula, impacto e observabilidade.
- Limitacoes: nao deve renderizar dashboards.

## Data Platform

- Localizacao: `backend/services/data_platform/`.
- Objetivo: camada de catalogo, execucao analitica, blueprints, packages, sync, runtime, lineage, performance e trust center.
- Entradas: planos validados, metadados, views, pacotes, tenant e runtime requests.
- Saidas: datasets, dashboards payload, analytics, metadata, health, lineage e telemetria.
- Dependencias: modelos SQLAlchemy, CatalogAPI, Metadata Catalog, Sync Engine e Business Layer.

## Dashboard Studio

- Localizacao: `backend/services/dashboard_studio_service.py`, `backend/routers/dashboard_studio.py`, `frontend/app/dashboard/studio/page.tsx`.
- Objetivo: editar template/instance visual sem alterar blueprint, formulas ou KPIs.
- Entradas: templates, instances, layout grid, componentes, versoes, import/export.
- Saidas: template/instance versionados e validacao de layout.
- Restricao: nao altera regra analitica.

## Frontend Runtime

- Localizacao: `frontend/components/dashboard-runtime/`, `frontend/hooks/useDashboardRuntime.ts`, `frontend/lib/dashboardRuntimeAdapter.ts`.
- Objetivo: renderizar payloads ADE/ECE ou adaptar respostas legadas.
- Entradas: `DashboardRuntimePayload` ou `QueryResponse` legado.
- Saidas: dashboard responsivo, trust center, grid, cross-filter e fullscreen.
- Limitacoes: nao calcula regra de negocio.

## Cache

- Localizacao: `backend/services/cache_service.py`, `backend/services/data_platform/package_cache.py`.
- Objetivo: cache em memoria para intencoes, planos, pacotes e diagnosticos de eficiencia.
- Entradas: chaves de tenant/pergunta/fingerprint/pacote.
- Saidas: hits/misses, estatisticas e relatorios.
- Limitacoes: cache local em memoria, nao substitui consulta de dados quando a politica exigir atualizacao.

## Scheduler E Sync

- Localizacao: `backend/services/scheduler.py`, `backend/services/sync_service.py`, `backend/services/data_platform/sync_engine.py`, `backend/services/data_platform/sync_scheduler.py`.
- Objetivo: sincronizar views/dados por tenant e orquestrar atualizacoes.
- Entradas: configuracao de tenant, conexoes Oracle/PostgreSQL, catalogo.
- Saidas: views clonadas/atualizadas, historico, status e alertas.
- Limitacoes: depende de credenciais e ambiente real para Oracle/PostgreSQL externo.

## Observabilidade, Performance E Seguranca

- Performance: `backend/services/performance/performance_optimization_platform.py`, `frontend/engines/performanceMonitor.ts`.
- Seguranca: `backend/services/security/enterprise_security_platform.py`, `backend/services/context_guard.py`, `frontend/proxy.ts`.
- Trust/Health: `backend/services/data_platform/trust_center_engine.py`, `health_monitor.py`, `frontend/components/dashboard-runtime/TrustCenterPanel.tsx`.
