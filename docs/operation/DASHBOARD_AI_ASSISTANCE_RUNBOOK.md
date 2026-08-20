# Runbook — Dashboard AI Assistance V2

## Estado seguro

O estado operacional obrigatório é:

```text
DASHBOARD_AI_ASSISTANCE_MODE=LEGACY_ONLY
DASHBOARD_AI_APIS_ENABLED=false
DASHBOARD_AI_FRONTEND_ENABLED=false
DASHBOARD_AI_FAKE_PROVIDER_ENABLED=false
DASHBOARD_AI_TENANT_ALLOWLIST=
```

Nesse estado o router não entra no OpenAPI, as páginas permanecem server-guarded e o browser não faz requests Prompt 22.

## Pré-condições para ensaio isolado

Use somente PostgreSQL descartável na porta 55432, `ENVIRONMENT=test`, `LUMINA_TESTING=true`, mocks de OpenAI e Oracle e guarda de rede externa. A migration v22 deve preceder a v23. Não use `DATABASE_URL`, porta 5432 ou banco operacional.

Para validar:

```powershell
docker compose -f docker-compose.test.yml up -d --wait
.\scripts\run-backend-tests-safe.ps1 --selection all -q
cd frontend
npm run lint
npx tsc --noEmit
npm run build
npm run test:visual
```

Ao final, execute `docker compose -f docker-compose.test.yml down -v` e remova apenas artefatos temporários do Playwright não versionados.

## Rollout futuro

Avance um modo por mudança aprovada, com allowlist explícita de tenant, backup aprovado, v23 aplicada e verificada, métricas/evals revisadas e rollback ensaiado. `SHADOW_ANALYZE` não persiste nem aplica. `AI_PROPOSAL_PREVIEW` permite apenas revisão. `AI_DRAFT_CREATE` habilita criação DRAFT. `AI_ASSISTED_EDIT` habilita patches DRAFT. Nenhum modo autoriza publicação por IA.

## Incidentes e rollback

Em conflito CAS, recarregue a proposta; nunca force versão. Em checksum divergente, bloqueie aplicação e preserve auditoria. Em ambiguidade, responda a clarificação tipada. Em tentativa proibida, mantenha fail-closed. Para rollback operacional, volte flags a `LEGACY_ONLY`; não apague histórico. O down da v23 é permitido somente em PostgreSQL descartável de teste.
