# LuminaAI

LuminaAI e uma plataforma Enterprise de Business Intelligence com IA, backend FastAPI, frontend Next.js e Data Platform analitica para catalogo, blueprints, pacotes analiticos, runtime de dashboards e governanca multi-tenant.

Esta documentacao representa o estado atual do sistema apos as auditorias e correcoes executadas ate 2026-07-09.

## Estado Atual

- Backend: FastAPI, SQLAlchemy async, PostgreSQL, integracao Oracle/mock, OpenAI, JWT com PyJWT.
- Frontend: Next.js 16, React 19, dashboard runtime, Dashboard Studio, componentes ECharts/Recharts e testes visuais Playwright.
- IA: Corporate Intelligence Engine modular, Query Intelligence Engine, planner, validator, blueprint builder, package matcher, visual strategy e response builder.
- Data Platform: Metadata Catalog, Semantic Catalog, Blueprint Repository, Analytical Packages, Sync Engine, Scheduler, Live Dashboard Runtime, Trust Center e engines de performance/seguranca.
- Validacao final local: backend `303 passed`, certificacao Enterprise `7 passed`, frontend lint/build OK, Playwright `16 passed`, load smoke `50 ok`, `runtime_cycles=0`.

## Arquitetura Oficial

```text
IA
-> Planner
-> Validator
-> Business Layer
-> Enterprise Knowledge Layer
-> Backend
-> Data Engine
-> Frontend
-> Insight Layer
-> Cache Layer
-> Security Layer
```

## Documentacao Oficial

- [Indice da documentacao](docs/README.md)
- [Arquitetura](docs/architecture.md)
- [Modulos](docs/modules.md)
- [APIs](docs/api-reference.md)
- [Guia de instalacao](docs/installation.md)
- [Guia de deploy](docs/deploy.md)
- [Guia de operacao](docs/operation.md)
- [Guia de manutencao](docs/maintenance.md)
- [Guia do desenvolvedor](docs/developer-guide.md)
- [Relatorio de certificacao por testes](docs/production_test_certification_report.md)
- [Parecer final de producao](docs/final_production_readiness_review.md)

## Execucao Local

Sistema completo:

```powershell
.\start-luminaai.ps1
```

O script sobe o backend em `0.0.0.0:8000` e o frontend em `0.0.0.0:3000`, validando acesso local e pela rede.

Parar:

```powershell
.\stop-luminaai.ps1
```

## Validacao

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q

cd ..\frontend
npm run lint
npm run build
npm run test:visual
npm run test:load
```

## Limites Conhecidos

- Validacao Docker nao foi executada localmente porque o binario `docker` nao esta instalado no ambiente usado na revisao.
- RLS nativo de banco nao foi identificado; o isolamento multi-tenant ocorre principalmente por JWT, filtros `tenant_id` e dependencias de routers.
- Testes de carga com massa produtiva e `EXPLAIN ANALYZE` real dependem do ambiente final.
