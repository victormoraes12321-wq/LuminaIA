# Runbook de Security, Migration e Rollout V2

Versão: `lumina.security-migration-rollout/1.0`. Este runbook não autoriza rollout real.

## Pré-condições

1. confirmar branch/HEAD/index e preservar alterações locais;
2. confirmar produção `LEGACY_ONLY`, worker/performance/rollout desligados e canary zero;
3. usar somente PostgreSQL descartável protegido, nunca porta 5432, Oracle ou banco operacional;
4. verificar threat model, findings, tenant isolation, auth matrix e redaction;
5. comprovar schemas/goldens/OpenAPI em duas execuções limpas;
6. exigir rollback documentado antes de qualquer avanço.

## Ordem dos gates

Emergency disable → feature kill switch → ambiente → schema/migration → segurança
crítica → tenant isolation → OpenAPI/evaluations → observability/error budget →
performance/queue → rollback/dependências → eligibility/capability.

Qualquer leak de tenant/secret/SQL, bypass de autenticação ou privilege escalation
exige: ativar emergency disable, bloquear readiness, preservar evidência sanitizada,
cancelar nova execução e iniciar resposta a incidente. Não continuar por compensação.

## Migration

Adquirir advisory lock antes de DDL, verificar target guard e compatibility manifest,
executar `up` idempotente em banco descartável, comparar manifests, testar aplicação
anterior/schema atual e aplicação atual/schema anterior, e liberar o lock no `finally`.
Não executar `down` em produção; restauração usa backup aprovado e janela operacional.

## Verificação pós-ação

Validar health do processo separadamente de readiness; confirmar nenhum job novo,
nenhum tenant habilitado, nenhum side effect shadow, histórico imutável preservado,
rotas legadas disponíveis e métricas sem labels de alta cardinalidade.
