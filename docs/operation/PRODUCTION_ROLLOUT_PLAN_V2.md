# Plano futuro de rollout produtivo V2

Estado atual: `NOT_EXECUTED`. Versão: `lumina.security-migration-rollout/1.0`.

| Estágio | Entrada mínima | Saída/abort |
| --- | --- | --- |
| AUDIT_ONLY | config e schema compatíveis | abortar em drift/finding crítico |
| SHADOW | segurança e tenant isolation verdes | zero publicação, write, worker ou efeito de negócio |
| INTERNAL | regressão completa e usuários internos autorizados | abortar em SLO/security/tenant breach |
| CANARY | cohort server-side determinístico, rollback e incident runbook | pausar em error budget, queue/performance ou finding alto |
| EXPANDED | canary produtivo aprovado externamente | voltar a canary/disable se SLO degradar |
| FULL | evidência produtiva e aprovação humana futura | não certificável pelo Prompt 26 |

O cliente não seleciona tenant, bucket, percentage ou stage. A política usa identificador
confiável do tenant e hash estável versionado. A configuração atual mantém percentage 0,
allowlist vazia e emergency/feature kill switches ativos. Não há tenants reais em canary.

Abort imediato: tenant disclosure/mutation, auth bypass, privilege escalation, secret ou
raw SQL leak, migration incompatível, critical evaluation, error budget esgotado,
duplicate effect, lease inconsistente, indisponibilidade de rollback ou observability de
segurança. A ação inicial é feature/global disable; DDL down não é automático.
