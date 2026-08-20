# Backend Governado de Dashboards V2

- Contrato: `lumina.dashboard-backend/1.0`
- Blueprint aceito: `lumina.dashboard-blueprint/2.0`
- Estado: implementado e certificado somente para rollout controlado
- Default produtivo: `LEGACY_ONLY`

## Escopo e autoridades

Este contrato governa identidade, ownership, revisões, review, approval,
publicações imutáveis, ponteiro ativo, rollback, colaboração, auditoria e
execução analítica de dashboards. O tenant, usuário, role e permissões vêm
exclusivamente da autenticação. Nenhum payload pode conceder autoridade.

O Blueprint V2 continua sendo a linguagem declarativa. MetricRegistry continua
autoridade de fórmulas; Safe Analytical PostgreSQL compila e executa consultas;
Validation & Provenance certifica os resultados; Smart Cache e materializações
publicadas podem ser reutilizados. O backend de dashboards não aceita SQL,
identificadores físicos, connection strings, JavaScript, HTML executável ou
credenciais, não consulta Oracle e não produz números por IA.

## Lifecycle

Transições aceitas:

```text
DRAFT -> IN_REVIEW
IN_REVIEW -> DRAFT | APPROVED | REJECTED
APPROVED -> PUBLISHED | DRAFT
PUBLISHED -> SUPERSEDED | DEPRECATED
SUPERSEDED -> ARCHIVED
DEPRECATED -> ARCHIVED
REJECTED -> DRAFT
ARCHIVED -> (nenhuma)
```

Um dashboard publicado pode manter uma publicação ativa enquanto uma nova
revisão de head percorre review. Por isso `lifecycle` representa a exposição
ativa e `head_lifecycle` representa a revisão em elaboração. Só uma publicação
é ativa; sua troca usa CAS por `generation`.

## Integridade e imutabilidade

- revisões recebem checksums independentes de blueprint, semântica e visual;
- visual patch deve preservar o checksum semântico;
- semantic patch deve mudar o checksum semântico e passar por revalidação;
- review e approval referenciam revisão e checksum específicos;
- autor da revisão não pode aprová-la;
- publicação é explícita, posterior à aprovação e imutável;
- supersession é derivada do ponteiro ativo, sem mutar a publicação histórica;
- rollback cria nova publicação e preserva toda a cadeia;
- revisions, reviews, approvals, publications e audit events têm triggers de
  imutabilidade no PostgreSQL;
- metadata, head, review, ponteiro ativo, archive e colaboradores usam CAS;
- idempotência é escopada por tenant, usuário, operação, recurso, chave e
  checksum do payload.

## Ownership, colaboração e RBAC

Ownership é controlado pelo servidor. Clones criam novo owner e não copiam
grants, approvals nem autoridade. Roles de colaborador (`VIEWER`,
`EDITOR_VISUAL`, `EDITOR_SEMANTIC`, `REVIEWER`, `PUBLISHER`,
`ADMINISTRATOR`) são sempre tenant-scoped e apenas restringem o RBAC global;
nunca o elevam.

- `CONSULTA`: leitura/execução de publicação autorizada e proveniência pública;
- `GESTOR`: criação, edição governada, review, clone e auditoria limitada;
- `ADMIN`: approval, publicação, rollback, archive, colaboradores e auditoria.

Dashboards em draft são visíveis somente ao owner, colaboradores autorizados e
ADMIN. A policy tenant-wide de view/execute só é aplicada quando existe
publicação ativa. Mudanças de grant e policy são consultadas a cada operação.

## Runtime

`DashboardRuntimePlanV2` e `DashboardWidgetRuntimePlanV2` contêm somente IDs
canônicos, períodos, filtros efetivos, limites, fingerprints, grupos e decisões
de cache. O plano nunca contém SQL ou nomes físicos. Filtros e interações são
aceitos apenas quando declarados no blueprint publicado; valores são
normalizados e enviados como binds pela autoridade Safe PostgreSQL.

Widgets semanticamente equivalentes podem compartilhar um execution group.
Isso não altera fact references, certificação ou proveniência. Valores
financeiros permanecem `Decimal`. Falha parcial não sintetiza zero nem dados e
é devolvida como `PARTIAL`/`UNAVAILABLE`, com warning explícito.

O fingerprint analítico exclui identidade puramente visual, mas inclui tenant,
permission scope, classificação, dataset/binding, métricas, dimensões, período,
filtros e checksum semântico. Cache hit mantém certification. Materialização só
é aceita quando publicada, `FRESH`, `VALID` e com checksum íntegro.

## Persistência V22

A migration aditiva `migration_v22_0.py` cria 13 tabelas explícitas:

1. `dashboards_v2`;
2. `dashboard_revisions_v2`;
3. `dashboard_reviews_v2`;
4. `dashboard_approvals_v2`;
5. `dashboard_publications_v2`;
6. `dashboard_active_publications_v2`;
7. `dashboard_collaborators_v2`;
8. `dashboard_access_policies_v2`;
9. `dashboard_audit_events_v2`;
10. `dashboard_runtime_executions_v2`;
11. `dashboard_widget_executions_v2`;
12. `dashboard_evaluation_cases_v2`;
13. `dashboard_evaluation_results_v2`.

O startup e o bootstrap genérico de testes excluem essas tabelas: V22 só pode
ser criada pela migration explícita. `run_down` exige confirmação e destino de
teste descartável. Não há Alembic nem migration automática de legado.

## Rollout

- `LEGACY_ONLY`: default; router V2 ausente e zero persistência V2 produtiva;
- `SHADOW_VALIDATE`: adapter e validação em memória, sem persistir/publicar;
- `V2_AUTHORING`: drafts somente para tenants allowlisted;
- `V2_PUBLISHED_READ`: leitura governada, runtime analítico ainda controlado;
- `V2_RUNTIME`: execução somente com aprovação operacional.

Todas as flags complementares começam desligadas: admin APIs, runtime APIs,
publishing, rollback, collaborators, runtime cache, materialization, audit e
legacy import dry-run. Não existe frontend V2 nesta etapa.

## Artefatos

- schemas: `docs/contracts/dashboard_backend_v2/schemas.json`;
- goldens sintéticos: `backend/tests/golden/dashboard_backend_v2.json`;
- operação: `docs/operation/GOVERNED_DASHBOARD_BACKEND_RUNBOOK.md`;
- decisão: ADR 0023.

