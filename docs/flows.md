# Fluxos Do Sistema

## Usuario -> IA

```text
Usuario digita pergunta
-> ChatInterface
-> useLuminaQuery (session_id + history + parent_id)
-> POST /api/v1/query/
-> Query Intelligence Engine
-> AI Service / Corporate Intelligence Engine
```

## Usuario -> Caminho Deterministico

```text
Pergunta critica com periodo claro
-> useLuminaQuery
-> NewQueryOrchestrator
-> SQL deterministico em view de vendas
-> data_transformer
-> QueryResponse
-> Dashboard runtime/tabela
```

## IA -> Planner

```text
Pergunta + contexto
-> Intent/Semantic/Context engines
-> IntentionResponse / BusinessIntent
-> Query Planner
```

## Planner -> Validator

```text
Plano proposto
-> plan_validator.validate_and_normalize_plan
-> filtros/datas/metricas normalizados
-> erro HTTP quando plano e invalido
```

## Validator -> Backend/Data Platform

```text
Plano validado
-> Business Layer
-> Data Platform / Execution Engine
-> Clone PostgreSQL ou Oracle/mock
```

## Backend -> Frontend

```text
Dados executados
-> data_transformer
-> bi_engine
-> dashboard_payload_builder/trust center
-> QueryResponse JSON
-> reparo de encoding no frontend
-> AssistantResponseBlock/DashboardRuntimeEngine
```

## Scheduler -> Sync Engine

```text
FastAPI startup
-> start_scheduler
-> run_sync_task
-> sync_tenant_database / SyncEngine
-> catalogo/views/historico/health
```

## Sync Engine -> Views -> Banco Analitico

```text
Tenant config
-> origem Oracle/mock
-> clone PostgreSQL
-> ViewCatalog/MetadataCatalog
-> historico e health
```

## Blueprint -> Dashboard

```text
Business Intent
-> Blueprint Builder/Repository
-> Visual Strategy
-> DashboardPayloadBuilder
-> Frontend Runtime
-> Grid/Components/Trust Center
```

## Dashboard -> Usuario

```text
Runtime payload
-> GridEngine
-> RuntimeRenderer
-> Charts/KPIs/Tables
-> CrossFilter/Fullscreen/Trust Center
-> Usuario
```
