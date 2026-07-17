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

`backend/main.py` configura FastAPI, lifespan, CORS, middlewares, exception handlers, routers e endpoints `/health` e `/`.

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

## Services

Services centralizam regra de aplicacao. Routers devem ser finos e delegar execucao.

### Consulta Inteligente

- `new_query_orchestrator.py`: orquestra o novo pipeline e possui caminho deterministico para perguntas criticas de vendas.
- `metadata_catalog/resolver.py`: resolve metricas, dimensoes, joins e expressoes canonicas.
- `data_transformer.py`: normaliza linhas, formata moeda/percentuais e humaniza labels para exibicao.

Regras de negocio recentes:

- `PADRAO` e ignorado em ranking de vendedores.
- `LAGES E LOPES LTDA` e ignorado em ranking/top cliente externo.
- Desconto e derivado por item quando a view nao fornece coluna explicita.
- Periodo pode ser herdado do historico da conversa quando a pergunta seguinte nao informa nova data.

## Middlewares E Erros

- CORS configurado por `settings.CORS_ORIGINS`.
- Middleware de timing adiciona diagnostico de latencia.
- Handlers globais padronizam HTTPException e excecoes genericas.
- Em producao, detalhes tecnicos nao devem ser expostos ao cliente.

## Validacao

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
```
