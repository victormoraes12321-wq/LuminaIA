# ADR 0023 — Revisões, publicação e runtime governados de dashboards

- Status: Accepted for controlled rollout, disabled by default
- Data: 2026-08-04
- Contrato: `lumina.dashboard-backend/1.0`

## Contexto

O Blueprint V2 do Prompt 19 definiu linguagem declarativa, mas permaneceu
`CONTRACT_ONLY`. O legado não oferece uma autoridade única para revisionamento
imutável, review, approval, publicação atômica, rollback e execução certificada
com isolamento multi-tenant.

## Decisão

Adotar um backend V2 isolado, tenant-scoped e explicitamente migrado:

- revisão imutável com checksums visual, semântico e integral;
- review/approval humanos ligados à revisão e ao checksum;
- active publication trocada por CAS e histórico nunca reescrito;
- rollback como nova publicação;
- RBAC global intersectado com ownership, grants e policy de recurso;
- runtime somente de publicação ativa, compilado pela autoridade Safe
  Analytical PostgreSQL e certificado por Validation & Provenance;
- reutilização transparente de Smart Cache/materializações publicadas;
- auditoria append-only e telemetria somente estrutural;
- migration V22 aditiva e excluída de qualquer `create_all` genérico;
- router condicional, ausente em `LEGACY_ONLY`.

## Consequências

Há duas superfícies de dashboard durante a transição. O storage e runtime
legados permanecem autoridade produtiva. V22 aumenta custo operacional e exige
backup/restore, CAS e monitoramento próprios. O ciclo entre dashboard head e
revision requer cuidado no restore descartável.

O frontend não é implementado por esta decisão. Também não há criação por IA,
migração automática de legado, SQL no blueprint, mudança de fórmulas ou acesso
Oracle no runtime.

## Alternativas rejeitadas

- mutar uma linha publicada no lugar;
- publicar automaticamente após approval;
- tratar rollback como mudança do ponteiro para uma linha histórica;
- confiar em tenant, owner, role ou permission enviados pelo cliente;
- criar compilador SQL, cache ou fórmula paralelos;
- usar `Base.metadata.create_all` como migration V22;
- migrar dashboards legados automaticamente;
- ativar rotas ou frontend V2 por default.

## Rollout e reversibilidade

O default é `LEGACY_ONLY`, com todas as flags desligadas e allowlist vazia.
Progressão possível: `SHADOW_VALIDATE`, `V2_AUTHORING`, `V2_PUBLISHED_READ` e
`V2_RUNTIME`, cada uma sujeita a aprovação operacional. Reversão de feature
retorna ao modo legado sem apagar V22. Down migration existe somente para banco
PostgreSQL descartável de teste.

Prompt 21 pode consumir os contratos após esta certificação, mas não recebe
autorização automática de rollout. Prompt 22 permanece dependente de revisão
humana e não poderá publicar diretamente.

