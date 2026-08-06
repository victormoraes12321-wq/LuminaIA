# Runbook — Dashboard UI e Side Chat V2

## Estado seguro

O estado seguro é:

```text
DASHBOARD_UI_MODE=LEGACY_ONLY
NEXT_PUBLIC_DASHBOARD_UI_MODE=LEGACY_ONLY
DASHBOARD_BACKEND_MODE=LEGACY_ONLY
```

Nesse estado `/dashboard/v2` responde 404 pelo servidor, a Sidebar não consulta
V2 e o side chat não monta.

## Pré-requisitos de piloto

- migration v22 aplicada e validada em ambiente aprovado;
- backup/restore e rollback operacional ensaiados;
- flags do backend Prompt 20 compatíveis com o modo frontend;
- tenant allowlisted e capabilities confirmadas no backend;
- cookies HttpOnly, CORS/CSRF e proxy revisados;
- SLO de runtime, cache, freshness, partial e cancelamento aceitos;
- OpenAI e Oracle reais desativados nas suítes.

## Progressão

1. `V2_PREVIEW`: desenvolvimento/teste allowlisted; sem mutações.
2. `V2_READ`: publicados, filtros, interações e proveniência.
3. `V2_AUTHORING`: criação manual, patches e lifecycle humano.
4. `V2_SIDE_CHAT`: contexto mínimo e ações locais/visuais tipadas.

Uma flag frontend nunca supera um backend desligado. Faça rollout por tenant,
monitore 403/404, conflitos CAS, cancelamentos, stale responses, widgets
indisponíveis e UI_MODIFIED. Telemetria não pode incluir pergunta ou fatos.

No side chat, valide a sequência `CONNECTING -> RECEIVING -> COMPLETE`. Ações
locais acrescentam `ACTION_PENDING -> ACTION_CONFIRMED`; patch visual permanece
em `ACTION_PENDING` até confirmação humana e persistência backend. `CANCELLED`
não pode aplicar ação. `RETRYABLE` oferece repetição explícita; `FAILED` não
repete automaticamente. O comando de reinício deve abortar a request, trocar a
sessão e limpar mensagens/propostas.

## Verificação

```powershell
cd frontend
npm run lint
npx tsc --noEmit
npm run build
npm run test:visual
```

Backend descartável:

```powershell
docker compose -f docker-compose.test.yml up -d --wait
.\scripts\run-backend-tests-safe.ps1 --selection all -q --tb=short
docker compose -f docker-compose.test.yml down -v
```

Confirme zero failed/errors/skipped/xfailed/XPASS, quatro viewports, Sidebar
oculta em LEGACY_ONLY e nenhum acesso a banco operacional, Oracle ou OpenAI.

## Incidentes

- 409: não repetir com key nova; exibir conflito e recarregar/comparar.
- 401/logout ou tenant switch: abortar tudo e desmontar contexto/chat.
- widget inválido: manter os demais, abrir proveniência pública.
- stale/partial/truncated: manter banner explícito; nunca sintetizar zero.
- ação desconhecida/injection: INVALID_ACTION/BLOCKED; nenhuma mutação.
- backend failure após preview: reverter preview; nunca emitir UI_MODIFIED.
- publicação mudou ou major contract mudou: recarga governada completa.

## Rollback

Retorne primeiro ambos os modos frontend a `LEGACY_ONLY`; depois aplique o
procedimento do runbook Prompt 20. Não apague revisões/publications e não execute
down v22 em produção. Limpe apenas recursos descartáveis de teste. O runtime e
Dashboard Studio legados permanecem autoridade operacional.
