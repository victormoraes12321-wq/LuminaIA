# LuminaAI Backend

## Conversation State V2

O modulo `services/conversation_state/` implementa
`lumina.conversation-state/1.0`. O default e `LEGACY_ONLY`; migration v12 e
rollout produtivo exigem operacao explicita.

Backend FastAPI responsavel por autenticacao, autorizacao, IA, planner/validator, Business Layer, Data Platform, execucao de dados, catalogos, sync, dashboard runtime e APIs administrativas.

## Estrutura

- `main.py`: aplicacao FastAPI.
- `config.py`: configuracoes via Pydantic Settings.
- `database.py`: engine async SQLAlchemy.
- `routers/`: controllers HTTP.
- `schemas/`: DTOs Pydantic.
- `models/`: modelos SQLAlchemy.
- `services/`: regras, IA, Data Platform, sync, cache e seguranca.
- `services/comparison_planning/`: planejamento comparativo V2 sem dados.
- `services/comparison_execution/`: compilacao governada, execucao,
  alinhamento, matematica, validacao e adapters comparativos.
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
docker compose -f ..\docker-compose.test.yml up -d --wait
..\scripts\run-backend-tests-safe.ps1 --selection all -q
docker compose -f ..\docker-compose.test.yml down -v
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
- Comparacoes V2 usam `lumina.comparison-executor/1.0`; Oracle e OpenAI nao
  participam da execucao nem da matematica.
- `COMPARISON_EXECUTOR_V2_ENABLED` e
  `COMPARISON_EXECUTOR_V2_SHADOW_MODE` iniciam desligadas.
