# Backend

## Stack

- FastAPI
- SQLAlchemy async
- Pydantic v2
- PostgreSQL/asyncpg
- Oracle/oracledb ou mock local
- OpenAI SDK
- PyJWT
- pytest

## Entrada Principal

`backend/main.py` configura FastAPI, lifespan, CORS, middlewares, exception handlers, routers e endpoints `/health`, `/health/deep` e `/`.

## Controllers/Routers

- `auth.py`: login, sessao, logout e troca de senha.
- `users.py`: administracao de usuarios por tenant.
- `tenant.py`: configuracoes de tenant, testes de conexao e sync.
- `catalog.py`: catalogo de views.
- `query.py`: consulta inteligente, historico, favoritos, cache, performance e seguranca.
- `metadata_catalog.py`: metadata, lineage, impacto, health e versoes.
- `business_knowledge.py`: conceitos, KPIs, formulas, governanca e rollback.
- `analytical_packages.py`: pacotes analiticos e instancias.
- `dashboard_studio.py`: templates, instances, versoes, import/export e validacao.
- `dashboard.py`: SSE, refresh e telemetria de dashboard.
- `dashboard_preferences.py`: preferencias de resposta/dashboard por usuario e tenant.

## Services

Services centralizam regra de aplicacao. Routers devem ser finos e delegar execucao.

### Consulta Inteligente

- `new_query_orchestrator.py`: orquestra o novo pipeline e possui caminho deterministico para perguntas criticas de vendas.
- `metric_registry.py`: dicionario oficial de metricas, fontes, formulas, filtros, confianca e limites conhecidos.
- `sales_value_breakdown.py`: decomposicao deterministica de faturamento comercial, saida RB, devolucao, bonificacoes, transferencias, remessa, total bruto sem transferencias e total geral de movimentos por periodo/filial.
- `metadata_catalog/resolver.py`: resolve metricas, dimensoes, joins e expressoes canonicas.
- `data_transformer.py`: normaliza linhas, formata moeda/percentuais e humaniza labels para exibicao.

Regras de negocio recentes:

- `PADRAO` e ignorado em ranking de vendedores.
- `LAGES E LOPES LTDA` e ignorado em ranking/top cliente externo.
- Desconto e derivado por item quando a view nao fornece coluna explicita.
- Saida RB e devolucao sao metricas separadas; transferencias ficam em coluna propria e nao entram em faturamento/lucro/total bruto.
- Periodo, metrica e dimensao podem ser herdados do historico da conversa quando a pergunta seguinte e curta ou ambigua.
- Perguntas com base/visualizacao ambigua podem usar preferencia persistida em `dashboard_preferences`.
- Respostas criticas de vendas incluem `bi_intelligence.metric_definitions`, `calculation_steps` e `trust_center.metric_registry`.

## Middlewares E Erros

- CORS configurado por `settings.CORS_ORIGINS`.
- Middleware de timing adiciona diagnostico de latencia.
- Handlers globais padronizam HTTPException e excecoes genericas.
- Em producao, detalhes tecnicos nao devem ser expostos ao cliente.

## Validacao

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\run_core_sales_redteam.py --json-report reports\core_sales_redteam_2026-07-20.json
.\.venv\Scripts\python.exe -m pip check
```
