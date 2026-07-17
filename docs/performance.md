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

- Baseline completo de 2026-07-09: load smoke local com 50 requests, 0 falhas, media 20ms, p95 58ms contra `/health`; testes visuais 16 passed; backend tests 303 passed.
- Validacao incremental de 2026-07-17: `npm run build` OK e E2E Playwright de login/pergunta/renderizacao OK em `http://127.0.0.1:3000`.
- Perguntas criticas com periodo claro usam caminho deterministico, reduzindo custo/variacao de IA em cenarios operacionais frequentes.

## Recomendacoes Para Producao

- Executar load test com dados reais e usuarios concorrentes.
- Rodar `backend/scripts/explain_analyze_core.sql` e EXPLAIN ANALYZE nas queries principais.
- Monitorar pool de conexoes, latencia de OpenAI, latencia Oracle e tempo de render frontend.
- Medir separadamente perguntas deterministicas e perguntas que passam por IA completa.
