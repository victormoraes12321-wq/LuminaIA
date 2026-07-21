# LuminaAI Backend

Backend FastAPI responsavel por autenticacao, autorizacao, IA, planner/validator, Business Layer, Data Platform, execucao de dados, catalogos, sync, dashboard runtime e APIs administrativas.

## Estrutura

- `main.py`: aplicacao FastAPI.
- `config.py`: configuracoes via Pydantic Settings.
- `database.py`: engine async SQLAlchemy.
- `routers/`: controllers HTTP.
- `schemas/`: DTOs Pydantic.
- `models/`: modelos SQLAlchemy.
- `services/`: regras, IA, Data Platform, sync, cache e seguranca.
- `database/`: SQL inicial e migrations.
- `tests/`: suite pytest.

## Rodar Localmente

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Para uso normal no Windows, prefira iniciar pela raiz do projeto:

```powershell
.\start-luminaai.ps1
```

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Variaveis Principais

Veja `.env.example`. Variaveis obrigatorias incluem `DATABASE_URL`, `SECRET_KEY`, `ENCRYPTION_KEY` e `OPENAI_API_KEY`.

## Observacoes

- JWT usa PyJWT.
- Health check: `GET /health`.
- Dockerfile usa Gunicorn + Uvicorn Worker.
- Perguntas criticas de vendas possuem caminho deterministico em `services/new_query_orchestrator.py`.
- `services/sales_value_breakdown.py` centraliza faturamento comercial, movimentos nao comerciais e abertura por filial para perguntas criticas.
- `services/data_transformer.py` humaniza labels tecnicos e formata campos financeiros para exibicao.
