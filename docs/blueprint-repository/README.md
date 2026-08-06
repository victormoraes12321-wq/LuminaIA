# Blueprint Repository

## Objetivo

Guardar e reutilizar inteligencia analitica estruturada sem guardar respostas de dados como verdade permanente. Blueprints descrevem intencao, KPIs, filtros, comparacoes, visual strategy e dependencias sem SQL bruto e sem dados finais.

## Implementacao

- `backend/services/query_intelligence_engine.py`: matching/evolucao legado e arquivo `services/blueprints.json`.
- `backend/services/data_platform/blueprint_repository.py`: repositorio Enterprise com profiles de performance/quality/health.
- `backend/models/blueprint.py`: persistencia SQLAlchemy.
- `backend/services/data_platform/intent_fingerprint.py`: fingerprint de intencao.

## Fluxo De Reutilizacao

```text
Pergunta -> Intent fingerprint -> busca blueprint/package compativel
-> se match alto: reutiliza blueprint/package
-> se match medio: evolui blueprint
-> se novo: cria blueprint
-> backend consulta dados atuais conforme plano/cache
```

## Versionamento

Blueprints possuem historico, versao e metadados de qualidade. A evolucao deve preservar compatibilidade com dashboards e packages existentes.

## Restricoes

- Blueprint nao deve conter SQL final de execucao.
- Blueprint nao deve armazenar dados de resposta.
- Mudancas devem passar pelo Validator/Business Layer.

## Dashboard Blueprint V2 (fundação isolada)

O contrato `lumina.dashboard-blueprint/2.0` está em
`docs/contracts/DASHBOARD_BLUEPRINT_V2.md`. É estrito, versionado e separa
revisões visuais de semânticas, mas permanece `CONTRACT_ONLY` no Prompt 19.

Os repositórios, modelos e `backend/services/blueprints.json` continuam legados
e não foram migrados. O adapter V2 apenas gera proposta sintética sem escrever
ou alterar a origem. Persistência depende do Prompt 20; renderer/editor e side
chat do Prompt 21; proposta por IA do Prompt 22.

## Backend governado V2

O Prompt 20 adiciona storage PostgreSQL separado para
`lumina.dashboard-backend/1.0`. Revisions, approvals e publications são
imutáveis; active publication usa CAS; clone não copia authority; runtime só
aceita publicação ativa e delega execução/certificação às autoridades existentes.

Isso não migra nem escreve `backend/services/blueprints.json`. O adapter legado
continua somente dry-run. `LEGACY_ONLY` mantém este repositório e runtime legados
como autoridade produtiva até rollout futuro formalmente aprovado.

## Consumo da interface V2

O Prompt 21 passou a consumir somente revisions validadas e publications ativas
do backend governado. Renderer, editor e side chat nunca escrevem neste
repositório legado nem em `backend/services/blueprints.json`. Visual updates
viram `DashboardVisualPatchV2`; semantic updates manuais permanecem separadas e
voltam a DRAFT/revalidação. Geração assistida continua reservada ao Prompt 22.

O Prompt 22 agora implementa essa reserva por propostas governadas. A síntese
consome exclusivamente Blueprint V2 validado e nunca grava neste repositório
legado ou em `backend/services/blueprints.json`. Aplicar uma proposta aceita
delega ao Prompt 20 e cria somente DRAFT ou nova revisão DRAFT.
