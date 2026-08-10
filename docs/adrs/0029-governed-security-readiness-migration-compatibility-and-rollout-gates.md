# ADR 0029 — Security readiness, migration compatibility e rollout gates governados

Status: Accepted. Data: 2026-08-10.

## Contexto

Prompts 23–25 adicionaram insights pós-sync, observability/evaluations e queue/performance,
todos desligados por padrão. Faltava uma autoridade comum, pura e auditável para impedir
configuração incoerente, schema incompatível e avanço sem rollback.

## Decisão

Adotar `lumina.security-migration-rollout/1.0` com contratos estritos, inventário estático,
deny-by-default, tenant server-derived, compatibility window 12–26, drift checks, advisory
lock futuro, kill switches com precedência global, canary determinístico e gates ordenados.
Migrations permanecem aditivas; v27 é `NOT_REQUIRED`. Rollback de feature precede aplicação
e banco. `FULL` exige evidência produtiva futura e permanece bloqueado.

Não criar API/frontend Prompt 26, não executar rollout/canary/migration/worker real e não
remover legado. Readiness pode ser `READY_FOR_CANARY` apenas como preparo técnico.

## Consequências

A plataforma ganha evidência reproduzível, configuração produtiva fail-closed e plano de
incidente/rollback. O custo é manter matrizes e manifests sincronizados. Canary real, SLO
approval, WAF/proxy, secret manager externo, load/penetration/DR produtivos continuam fora
do escopo e exigem aprovação operacional separada.
