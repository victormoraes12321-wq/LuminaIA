# Security, Migration and Rollout V2

Versão canônica: `lumina.security-migration-rollout/1.0`.

Este contrato encerra tecnicamente a fase 23–26 sem criar domínio de negócio,
API ou frontend. Ele descreve evidência tipada e imutável para segurança,
compatibilidade de schema, readiness, canary e rollback. Nenhum contrato executa
DDL, rollout, worker, chamada externa ou alteração de tenant.

## Autoridades e invariantes

- identidade, role, capability e tenant vêm do usuário autenticado no servidor;
- configuração e estágios são server-controlled; payload, headers e LLM não são autoridade;
- toda decisão desconhecida falha fechada;
- `GLOBAL_EMERGENCY_DISABLE` precede kill switch de feature e todos os demais gates;
- `CRITICAL` inclui cross-tenant, auth bypass, privilege escalation, secret/raw SQL leak e rollout bypass;
- `NOT_APPLICABLE` exige justificativa determinística;
- schemas estritos usam Pydantic 2, `extra=forbid` e instâncias frozen;
- banco futuro desconhecido, drift crítico ou migration ausente bloqueiam readiness;
- rollback de banco nunca é automático; desligamento de feature precede rollback da aplicação;
- `READY_FOR_CANARY` significa preparo técnico, jamais canary executado.

## Inventário estático

As oito features governadas são: leitura e authoring Dashboard V2, Dashboard AI,
Post-Sync Insights, Observability V2, Evaluations V2, Work Queue V2 e Performance
Certification. Cada item declara migration mínima, dependências, ambientes,
kill switch obrigatório e tipos de rollback. Performance só admite ambiente `test`.

Os estágios fechados são `DISABLED`, `AUDIT_ONLY`, `SHADOW`, `INTERNAL`,
`CANARY`, `EXPANDED`, `FULL`, `PAUSED` e `ROLLED_BACK`. Saltos de `DISABLED`
para canary/full são inválidos. `FULL` permanece bloqueado sem evidência produtiva futura.

## Compatibilidade de schema

- aplicação atual: schema 26;
- mínimo suportado: 12;
- máximo testado: 26;
- schema 0/desconhecido: `UNKNOWN`;
- schema 27+: `DATABASE_TOO_NEW`;
- ausência de objeto crítico: `BLOCKED` por drift;
- migration v27: `NOT_REQUIRED`, pois Prompt 26 não persiste novo estado.

O wrapper `PostgresMigrationLockV2` usa advisory lock estável para futuras
execuções governadas. Ele não altera migrations V1–V26 nem é executado em produção.

## Readiness e gates

Os gates verificam, na ordem: emergency disable, feature kill switch, ambiente,
migration, security, tenant isolation, OpenAPI, evaluations, observability, error
budget, performance estrutural, queue health, rollback, dependências, tenant
eligibility e capability. Falha crítica escolhe `ROLLBACK`; demais falhas negam avanço.

## Artefatos reproduzíveis

O script `scripts/export_security_rollout_v2_contracts.py` exporta 26 JSON Schemas,
quatro goldens (inventário, autorização, rollback e security readiness) e um manifest com SHA-256 agregado
em `docs/contracts/security_rollout_v2/`.
