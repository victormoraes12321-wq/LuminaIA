# LuminaAI

LuminaAI e uma plataforma Enterprise de Business Intelligence com IA, backend FastAPI, frontend Next.js e Data Platform analitica para catalogo, blueprints, pacotes analiticos, runtime de dashboards e governanca multi-tenant.

Esta documentacao representa o estado atual do sistema apos as auditorias, correcoes e validacoes executadas ate 2026-07-22. O baseline de certificacao completa permanece registrado em 2026-07-09; as correcoes mais recentes estao consolidadas em [Estado atual do sistema](docs/current-status.md).

## Estado Atual

- Backend: FastAPI, SQLAlchemy async, PostgreSQL, integracao Oracle/mock, OpenAI, JWT com PyJWT.
- Frontend: Next.js 16, React 19, dashboard runtime, Dashboard Studio, componentes ECharts/Recharts e testes visuais Playwright.
- IA: Corporate Intelligence Engine modular, Query Intelligence Engine, planner, validator, blueprint builder, package matcher, visual strategy e response builder.
- Data Platform: Metadata Catalog, Semantic Catalog, Blueprint Repository, Analytical Packages, Sync Engine, Scheduler, Live Dashboard Runtime, Trust Center e engines de performance/seguranca.
- Validacao completa historica em 2026-07-09: backend `303 passed`, certificacao Enterprise `7 passed`, frontend lint/build OK, Playwright `16 passed`, load smoke `50 ok`, `runtime_cycles=0`.
- Validacao incremental em 2026-07-20: `python -m py_compile`, testes focados de perguntas criticas com 38 testes, `npm run build`, bateria oficial de 461 perguntas/0 falhas e auditoria numerica por metrica/filial em 06/2026 e 07/2026.
- Validacao incremental em 2026-07-22: suite massiva de mineracao e estresse com **164 cenario analiticos e multi-turn/0 falhas**, auto-cura semantica de entidades/metricas/filtros no `Canonicalizer`, extracao automatica de anos isolados de 4 digitos e integracao direta de consultas de produtos mais vendidos, estoque e titulos em aberto.

## Correcoes Recentes

- Consultas da IA usam somente o PostgreSQL analitico sincronizado; Oracle fica isolado na sincronizacao e reconciliacao tecnica.
- Cada resposta informa a ultima atualizacao real, executa validacoes matematicas e oferece aprofundamento por documentos no mesmo chat.
- O perfil `ADMIN` recebe diagnostico tecnico completo; o perfil `CONSULTA` nao recebe configuracoes SaaS, traces, planos ou telemetria.
- Suporte a consultas deterministicas estendidas de **Produtos mais vendidos**, **Estoque por produto** e **Financeiro / Titulos em aberto** com preenchimento em `sample_rows` para tabelas e graficos do frontend.
- Auto-cura semantica no `Canonicalizer` para entidades desconhecidas (ex: `item`, `mercadoria`, `estoque`, `parcela`, `cobranca`, `comissao`) redirecionando para entidades canonicas.
- Auto-cura graciosa de filtros nao mapeados (descarte com log de aviso em vez de erro `UNSUPPORTED`).
- Suporte a anos isolados de 4 digitos (`no ano de 2026`, `em 2026`, `2026`), gerando o intervalo `YYYY-01-01` a `YYYY-12-31`.
- Tolerancia a typos e erros gramaticais de usuarios (`mais vendidoa`, `mais vendida`, `top produtos`).
- Perguntas criticas de faturamento, ticket medio, desconto, venda por vendedor e rankings possuem caminho deterministico quando ha periodo claro.
- Perguntas de vendas usam `filial_` como dimensao padrao: total geral inclui todas as filiais e a tabela detalha por filial; filial especifica filtra quando o usuario pedir.
- Continuidade de conversa usa `session_id`, historico recente e `parent_id`; perguntas curtas podem herdar periodo, metrica e dimensao anteriores.
- Preferencias de dashboard sao persistidas por usuario/tenant e aplicadas em perguntas ambiguas de BI.
- Respostas criticas de vendas incluem auditoria de calculo em `bi_intelligence` e `trust_center.metric_registry`.
- `GET /health/deep` fornece diagnostico de API, PostgreSQL e status de IA/invocacao.
- Rankings excluem cadastros internos/tecnicos quando a regra de negocio exige: vendedor `PADRAO` e cliente/loja `LAGES E LOPES LTDA`.
- Textos vindos da API e da UI passam por reparo defensivo de encoding antes da renderizacao.
- O frontend preserva o host loopback (`localhost` ou `127.0.0.1`) na API para evitar perda de cookie de sessao.

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
- [Estado atual do sistema](docs/current-status.md)
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
.\.venv\Scripts\python.exe scripts\run_core_sales_redteam.py --json-report reports\core_sales_redteam_2026-07-20.json

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
