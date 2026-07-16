# Performance

## Estrategias Implementadas

- Backend async com FastAPI/SQLAlchemy async.
- Pool de conexoes configurado em `backend/config.py`.
- Scheduler em background para sync.
- Cache em memoria para interpretacoes/packages quando aplicavel.
- Frontend com lazy/runtime rendering, virtualizacao parcial e Playwright visual.
- Client-side performance monitor para FPS, memoria e tempo de render.
- Load smoke local via `scripts/load-smoke.mjs`.

## Pontos De Medicao

- Middleware de timing no FastAPI adiciona diagnostico de latencia.
- Query Intelligence Engine registra tempos de pipeline.
- Performance Center/Trust Center podem expor tempos de blueprint/backend/runtime.
- `frontend/engines/performanceMonitor.ts` mede FPS/memoria quando habilitado.

## Validacao Atual

- Load smoke local: 50 requests, 0 falhas, media 20ms, p95 58ms contra `/health`.
- Testes visuais: 16 passed.
- Backend tests: 303 passed.

## Recomendacoes Para Producao

- Executar load test com dados reais e usuarios concorrentes.
- Rodar `backend/scripts/explain_analyze_core.sql` e EXPLAIN ANALYZE nas queries principais.
- Monitorar pool de conexoes, latencia de OpenAI, latencia Oracle e tempo de render frontend.
