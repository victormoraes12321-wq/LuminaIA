# Runbook — Backend Governado de Dashboards V2

Este runbook não autoriza rollout produtivo. O modo aprovado continua
`LEGACY_ONLY`, todas as flags V2 permanecem desligadas e a migration V22 não
deve ser executada em produção.

## Pré-condições

1. Confirme branch, HEAD, worktree e índice sem mutá-los.
2. Confirme o hash de `backend/services/blueprints.json`.
3. Use apenas `127.0.0.1:55432/luminaai_test` com `ENVIRONMENT=test`,
   `LUMINA_TESTING=true` e `TEST_DATABASE_URL` explícita.
4. Remova `DATABASE_URL` do processo de teste.
5. Suba somente `docker-compose.test.yml` e aguarde healthcheck.
6. Nunca use porta 5432, banco operacional, Oracle, OpenAI real ou rede externa.

## Migration descartável

V22 não é criada por `Base.metadata.create_all`. Carregue
`backend/database/migration_v22_0.py` e execute `run_up()` somente após a guarda
de banco. O segundo `run_up()` deve ser idempotente. `run_down()` só aceita
`confirm_test_only=True` e derruba apenas os objetos V22.

A certificação de cadeia executa V13…V22 up, V22…V13 down e V13…V22 up, deixando
V12 como baseline. Migrations V12–V21 não são editadas pela etapa.

## Backup e restore de ensaio

O ensaio certificado usa fixtures sintéticas contendo draft, revisão, review,
approval, publicação, active publication, colaborador e auditoria.

1. Gere o manifesto sanitizado com
   `scripts/rehearse_dashboard_v22_fixture.py --seed`.
2. Execute `pg_dump` dentro do container, custom format, `--data-only`,
   `--no-owner`, `--no-privileges` e `--table` para cada uma das 13 tabelas.
3. Armazene o dump somente em `/tmp` dentro do container.
4. Execute V22 down e up no banco descartável.
5. Como `dashboards_v2.head_revision_id` e revisions formam um ciclo de FKs,
   restaure como o superusuário local `lumina_test` com `--disable-triggers`.
   Esse privilégio é restrito ao container descartável.
6. Confirme que todas as constraints estão `convalidated`, os triggers voltaram
   a `tgenabled='O'`, os índices existem e o active pointer referencia a mesma
   publicação.
7. Compare row counts, checksums por tabela e checksum global dos manifestos.
8. Remova o dump e confirme sua ausência.

O procedimento não é uma política de backup produtivo. Backup de produção,
retenção, criptografia, restore drill operacional e aprovação de DBA continuam
bloqueados e exigem tarefa própria.

## Validação

Execute, nessa ordem:

```powershell
docker compose -f docker-compose.test.yml up -d --wait
.\scripts\run-backend-tests-safe.ps1 --selection all -q --tb=short
cd frontend
npm run lint
npx tsc --noEmit
npm run build
npm run test:visual
cd ..
docker compose -f docker-compose.test.yml config
docker compose -f docker-compose.test.yml down -v
```

`test:load` não faz parte desta etapa porque acessa o backend na porta 8000 e
requer ambiente de carga explicitamente isolado.

## Incidentes e rollback de feature

- erro de migration: interrompa; não use create_all como fallback;
- conflito CAS: recarregue lock/generation e reapresente a decisão ao usuário;
- checksum divergente: bloqueie review/publicação/restore;
- classification ou permission insuficiente: responda fail-closed sem revelar
  existência cross-tenant;
- cache/materialização stale: trate como miss ou warning explícito;
- falha de widget: preserve widgets certificados e marque partial somente se a
  policy permitir;
- incidente de rollout: retorne `DASHBOARD_BACKEND_MODE=LEGACY_ONLY` e desligue
  todas as flags; não apague dados ou histórico.

## Checklist para qualquer rollout futuro

- backup produtivo aprovado e restore drill concluído;
- migration V22 aprovada por DBA;
- tenant allowlist explícita;
- métricas e alertas estruturais ativos;
- auditoria e retenção aprovadas;
- runbook de incidente e rollback ensaiado;
- Prompt 21 certificado antes de expor interface;
- Prompt 22 certificado antes de permitir propostas por IA;
- aprovação humana formal de segurança, dados e operação.

