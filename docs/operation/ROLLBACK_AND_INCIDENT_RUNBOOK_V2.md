# Rollback e incidentes V2

Versão: `lumina.security-migration-rollout/1.0`.

## Precedência

1. ativar `V2_GLOBAL_EMERGENCY_DISABLE` ou kill switch da feature;
2. impedir novos writes/enqueues/proposals/publications;
3. cancelar ou drenar in-flight segundo a feature;
4. preservar histórico, audit, outbox, jobs, revisions e baselines;
5. quando compatível, fazer rollback da aplicação;
6. rollback de banco somente por plano humano aprovado/backup, nunca automático;
7. executar validação estrutural, tenant isolation e regressão antes de reativar.

Queue preserva leases/jobs e interrompe novos enqueues; Post-Sync interrompe consumo e
publicação sem afetar sync/reconciliation; Dashboard AI cancela provider/tools e preserva
drafts/publicações; falha de observability de segurança bloqueia readiness do rollout.

## Incidente

Classificar CRITICAL para cross-tenant, auth bypass, privilege escalation, secret/raw SQL
leak e rollout bypass. Registrar apenas IDs estruturais, classes e reason codes redigidos.
Não registrar pergunta, dataset, SQL, binds, credencial, cookie, bearer ou CoT. Preservar
checksum e timestamps, notificar responsáveis externos e manter o sistema desabilitado
até root cause, correção, teste e aprovação.

Break-glass: `BREAK_GLASS_NOT_IMPLEMENTED`. Não há header, role ou bypass especial.
Uma capacidade futura exigirá identidade forte, dupla aprovação, expiração, escopo mínimo
e audit imutável; ausência atual bloqueia qualquer procedimento que dependa dela.
