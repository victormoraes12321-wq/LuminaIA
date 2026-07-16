# Data Platform

## Objetivo

A Data Platform organiza catalogos, blueprints, packages, runtime, sync, lineage, performance e trust center. Ela conecta planejamento analitico com execucao backend sem transferir responsabilidade de regra visual para o banco ou frontend.

## Modulos

- `CatalogAPI`: fachada para catalogo, lineage, health e dependencias.
- `MetadataCatalogService`: metadados de views/estruturas.
- `SemanticCatalogService`: sinonimos e semantica de negocio.
- `BlueprintRepository`: persistencia e reuso de blueprints.
- `AnalyticsEngine`: processamento analitico corporativo.
- `ExecutionEngine`: execucao de blueprint validado.
- `DatasetBuilder`: construcao de dataset runtime.
- `DashboardPayloadBuilder`: payload para dashboard runtime.
- `LiveDashboardRuntime`: runtime vivo e telemetria.
- `SyncEngine`/`SyncOrchestrator`: sincronizacao de views/dados.
- `TrustCenterEngine`: confianca, lineage, versoes, health e auditoria.
- `PerformanceLayer`: estrategias de performance.

## Fluxo

```text
Plano validado -> Business Layer -> Data Platform
-> Metadata/Semantic Catalog -> Blueprint Repository
-> Execution/Dataset/Runtime -> Trust/Performance/Cache
```

## Boas Praticas

- Registrar metadados via CatalogAPI quando possivel.
- Nao escrever SQL em blueprints.
- Usar tenant em todas as operacoes persistidas.
- Manter packages versionados e auditaveis.
