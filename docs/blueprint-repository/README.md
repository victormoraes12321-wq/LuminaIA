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
