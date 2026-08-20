# Runbook — Smart Cache e Materialização Governada

## Estado operacional

Produção deve permanecer com:

```text
SMART_CACHE_MATERIALIZATION_MODE=LEGACY_ONLY
SMART_CACHE_ADMIN_ENABLED=false
```

Certificação não autoriza rollout, execução da V21 fora de PostgreSQL
descartável, escrita de cache ou publicação de materializações.

## Validação isolada

Use exclusivamente `127.0.0.1:55432/luminaai_test`, com `ENVIRONMENT=test`,
`LUMINA_TESTING=true`, `TEST_DATABASE_URL` explícita e sem fallback de
`DATABASE_URL`. Execute primeiro os testes estáticos da V21. Depois:

```powershell
docker compose -f docker-compose.test.yml up -d --wait
.\scripts\run-backend-tests-safe.ps1 --selection all -q --tb=short
docker compose -f docker-compose.test.yml down -v
```

Nunca use porta 5432, Oracle, banco operacional, instalador ou scripts que
encerrem portas operacionais para essa validação.

## Invalidation

Eventos de sync/watermark, catálogo, MetricRegistry, permissions, policy,
certificação, publicação e rollback devem incrementar a generation governada
e/ou invalidar dependency tags apenas no tenant autenticado. Não aceite tenant,
key ou path enviados pelo cliente como autoridade.

## Lease e incidente de stampede

Leases são por tenant+key, possuem TTL máximo, token interno e checksum do
owner. Em contenção, aguarde somente até o timeout governado. Falha ou
cancellation deve liberar a lease; após restart, lease expirada pode ser
adquirida novamente. Nunca conceda permission por posse de lease.

## Build, publicação e rollback

1. Confirme definition `APPROVED`, permission e lock version.
2. Execute build via Safe Analytical PostgreSQL e Validation & Provenance.
3. Inspecione snapshot `READY`, certificação `VALID`, freshness e checksums.
4. Publique por CAS explícito; não há auto-publicação.
5. Refresh cria snapshot novo e mantém o ativo.
6. Rollback exige snapshot anterior compatível e válido, CAS e auditoria.

Em validation failure, watermark não verificável, row-level, PII, stale ou
checksum inválido, falhe fechado e preserve o snapshot publicado.

## Garbage collection

Comece sempre com dry-run e lote pequeno. GC remove entries e leases expiradas,
snapshots expirados não publicados e builds `FAILED`/`CANCELLED` fora da
retenção. O ponteiro ativo, o snapshot anterior mínimo e histórico de
publicação/rollback são preservados. Nunca faça delete sem tenant e limite.

## Rollback do subsistema

Desligue primeiro as flags e volte a `LEGACY_ONLY`. O `run_down` da V21 requer
confirmação test-only e destina-se somente a banco descartável. Em produção,
rollback funcional é por flags e ponteiro de snapshot; migration depende de
plano, backup e aprovação operacional separados.
