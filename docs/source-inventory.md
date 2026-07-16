# Inventario De Codigo

Fonte: varredura local de arquivos Python/TypeScript relevantes.

## backend/models

| Arquivo | Classes | Funcoes |
| --- | --- | --- |
| `backend/models/__init__.py` | - | - |
| `backend/models/analytical_package.py` | PackageStatus, AnalyticalPackage | - |
| `backend/models/blueprint.py` | Blueprint | - |
| `backend/models/business_concept.py` | BusinessConcept | - |
| `backend/models/business_formula.py` | BusinessFormula | - |
| `backend/models/business_governance_log.py` | BusinessGovernanceLog | - |
| `backend/models/business_kpi.py` | BusinessKPI | - |
| `backend/models/business_relationship.py` | BusinessRelationship | - |
| `backend/models/dashboard_instance.py` | DashboardInstance | - |
| `backend/models/dashboard_studio_version.py` | DashboardStudioVersion | - |
| `backend/models/dashboard_template.py` | DashboardTemplate | - |
| `backend/models/data_platform_history.py` | DataPlatformHistory | - |
| `backend/models/dataset.py` | Dataset | - |
| `backend/models/favorite.py` | Favorite | - |
| `backend/models/metadata_catalog.py` | MetadataCatalog | - |
| `backend/models/metadata_catalog_version.py` | MetadataCatalogVersion | - |
| `backend/models/package_dashboard_instance.py` | PackageDashboardInstance | - |
| `backend/models/search_history.py` | SearchHistory | - |
| `backend/models/semantic_catalog.py` | SemanticCatalog | - |
| `backend/models/sync_queue.py` | SyncQueue | - |
| `backend/models/tenant.py` | Tenant | - |
| `backend/models/user.py` | UserRole, User | - |
| `backend/models/view_catalog.py` | ChartType, ViewCatalog | - |

## backend/schemas

| Arquivo | Classes | Funcoes |
| --- | --- | --- |
| `backend/schemas/__init__.py` | - | - |
| `backend/schemas/dashboard_studio.py` | GridItem, ComponentConfig, DashboardTemplateCreate, DashboardTemplateUpdate, DashboardTemplateResponse, DashboardInstanceCreate, DashboardInstanceUpdate, DashboardInstanceResponse, DashboardStudioVersionResponse, DashboardDuplicateRequest, DashboardFavoriteRequest, DashboardRollbackRequest, DashboardLayoutValidationRequest, DashboardLayoutValidationResponse, DashboardExportResponse, DashboardImportRequest | - |
| `backend/schemas/favorite.py` | FavoriteCreate, FavoriteUpdate, FavoriteResponse | - |
| `backend/schemas/metadata_catalog.py` | MetadataCatalogResponse, MetadataCatalogVersionResponse | - |
| `backend/schemas/query.py` | ChatMessageSchema, QueryRequest, DatasetBar, ChartDataBar, DatasetLine, ChartDataLine, ChartDataPie, TableColumn, ChartDataTable, KPIItem, ChartDataKPI, VisualizationItem, IntentionPlanItem, QueryResponse, HistoryListItem, FavoriteListItem | - |
| `backend/schemas/search_history.py` | SearchHistoryCreate, SearchHistoryResponse, SearchHistoryListResponse | - |
| `backend/schemas/tenant.py` | TenantBase, TenantCreate, TenantUpdate, TenantResponse, TenantSettingsUpdate | - |
| `backend/schemas/user.py` | UserBase, UserCreate, UserUpdate, UserResponse, UserPublic, LoginRequest, LoginResponse, ChangePasswordRequest, UserCreateAdmin, UserCreateAdminResponse | - |
| `backend/schemas/view_catalog.py` | ViewCatalogBase, ViewCatalogCreate, ViewCatalogUpdate, ViewCatalogResponse, ViewCatalogSummary | - |

## backend/routers

| Arquivo | Classes | Funcoes |
| --- | --- | --- |
| `backend/routers/__init__.py` | - | - |
| `backend/routers/analytical_packages.py` | PackageSummaryResponse, PackageDetailResponse, PackageInstanceResponse, GlobalStatsResponse, DeprecateRequest | get_package_stats, list_packages, get_package, list_package_instances, deprecate_package, _to_summary_response, _to_detail_response, _to_instance_response |
| `backend/routers/auth.py` | - | _set_auth_cookie, _clear_auth_cookie, login, get_session, logout, change_password |
| `backend/routers/business_knowledge.py` | ConceptResponse, KPIResponse, FormulaResponse, ObservabilityResponse, ImpactResponse, RollbackRequest, RollbackResponse, RegisterConceptRequest, RegisterKPIRequest | list_dictionary_concepts, register_concept, list_registered_kpis, register_kpi, list_formulas, get_observability, get_impact_analysis, execute_rollback, seed_bke |
| `backend/routers/catalog.py` | - | _get_catalog_api, list_catalog_views, create_catalog_view, update_catalog_view, delete_catalog_view |
| `backend/routers/dashboard.py` | - | listen_dashboard_events, force_dashboard_refresh, get_dashboard_telemetry |
| `backend/routers/dashboard_studio.py` | - | create_template, list_templates, get_template, update_template, list_template_versions, rollback_template, export_template, create_instance, list_instances, get_instance, update_instance, duplicate_instance |
| `backend/routers/dependencies.py` | - | get_current_user, check_admin_role, check_admin_or_gestor_role, enforce_password_change |
| `backend/routers/metadata_catalog.py` | - | _normalize_tags, get_metadata_summary, get_metadata_health, search_metadata_catalog, get_metadata_entity, get_metadata_lineage, get_metadata_dependency_graph, get_metadata_impact, get_metadata_versions |
| `backend/routers/query.py` | - | _persistir_historico, get_query_history, get_query_favorites, processar_consulta, obter_metricas_inteligencia, obter_estatisticas_cache, limpar_cache_plataforma, obter_relatorio_performance, otimizar_recursos_sistema, obter_relatorio_seguranca, criar_backup_seguro, restaurar_backup_seguro |
| `backend/routers/tenant.py` | - | get_tenant_settings, update_tenant_settings, test_oracle_connection, test_ai_connection, get_tenant_audit_logs, test_postgres_clone_connection, trigger_tenant_sync |
| `backend/routers/users.py` | - | _generate_secure_password, create_user_by_admin, list_users, delete_user, toggle_user_active, update_user |

## backend/services

| Arquivo | Classes | Funcoes |
| --- | --- | --- |
| `backend/services/__init__.py` | - | - |
| `backend/services/ai/__init__.py` | - | - |
| `backend/services/ai/blueprint_builder.py` | BlueprintBuilder | - |
| `backend/services/ai/business_understanding_engine.py` | BusinessUnderstandingEngine | - |
| `backend/services/ai/confidence_engine.py` | ConfidenceEngine | - |
| `backend/services/ai/context_engine.py` | ContextEngine | - |
| `backend/services/ai/corporate_intelligence_engine.py` | CorporateIntelligenceEngine | - |
| `backend/services/ai/executive_analysis_engine.py` | ExecutiveAnalysisEngine | - |
| `backend/services/ai/intent_engine.py` | IntentEngine | - |
| `backend/services/ai/kpi_discovery_engine.py` | KPIDiscoveryEngine | - |
| `backend/services/ai/legacy_contracts.py` | ModelViolationError, AIServiceError, PlanFiltersSchema, PlanVisualizationSchema, StructuredPlanSchema, IntentionResponse | - |
| `backend/services/ai/memory_context_engine.py` | MemoryContextEngine | - |
| `backend/services/ai/package_matcher.py` | PackageMatcher | - |
| `backend/services/ai/response_builder.py` | ResponseBuilder | - |
| `backend/services/ai/schemas.py` | PlanFiltersSchema, PlanVisualizationSchema, StructuredPlanSchema, ParametroFiltro, IntentionResponseSchema, MultipleIntentionsResponseSchema, BusinessIntentSchema, VisualStrategySchema, BlueprintSchema, CIEContextSchema | - |
| `backend/services/ai/semantic_engine.py` | SemanticEngine | - |
| `backend/services/ai/visualization_strategy_engine.py` | VisualizationStrategyEngine | - |
| `backend/services/ai_service.py` | - | validate_authorized_model, _get_openai_client, _get_tenant_openai_client, close_tenant_openai_client, identify_intention, generate_data_insights, detect_user_session_profile, _build_system_prompt |
| `backend/services/auth_service.py` | - | get_password_hash, verify_password, create_access_token, decode_access_token |
| `backend/services/bi_engine.py` | - | _to_float, process_bi_intelligence |
| `backend/services/business/__init__.py` | - | - |
| `backend/services/business/business_context_engine.py` | BusinessContextEngine | - |
| `backend/services/business/business_dependency_engine.py` | BusinessDependencyEngine | - |
| `backend/services/business/business_dictionary.py` | BusinessDictionary | - |
| `backend/services/business/business_formula_engine.py` | BusinessFormulaEngine | - |
| `backend/services/business/business_governance.py` | BusinessGovernance | - |
| `backend/services/business/business_knowledge_engine.py` | BusinessKnowledgeEngine | - |
| `backend/services/business/business_kpi_registry.py` | BusinessKPIRegistry | - |
| `backend/services/business/business_relationship_engine.py` | BusinessRelationshipEngine | - |
| `backend/services/business/business_validation_engine.py` | BusinessValidationError, BusinessValidationEngine | - |
| `backend/services/business/synonym_cache.py` | - | - |
| `backend/services/cache_service.py` | CacheItem, IntelligentCachingPlatform | - |
| `backend/services/context_guard.py` | ScopeViolationError | validate_user_query, sanitize_history, validate_params, validate_query_intent, apply_row_limit |
| `backend/services/dashboard_studio_service.py` | DashboardStudioService | - |
| `backend/services/data_platform/__init__.py` | - | _export, _build_compat_singleton, __getattr__ |
| `backend/services/data_platform/adaptive_dashboard_engine/__init__.py` | AdaptiveDashboardEngine | - |
| `backend/services/data_platform/adaptive_dashboard_engine/diagnostics.py` | DashboardDiagnostics | - |
| `backend/services/data_platform/adaptive_dashboard_engine/grid_engine.py` | AdaptiveGridEngine | - |
| `backend/services/data_platform/adaptive_dashboard_engine/interpreter.py` | BlueprintInterpreter | - |
| `backend/services/data_platform/adaptive_dashboard_engine/optimizer.py` | RenderingOptimizer | - |
| `backend/services/data_platform/adaptive_dashboard_engine/personalization.py` | PersonalizationEngine | - |
| `backend/services/data_platform/adaptive_dashboard_engine/schemas.py` | GridPosition, BreakpointLayout, DashboardLayoutSchema | - |
| `backend/services/data_platform/adaptive_dashboard_engine/security.py` | DashboardSecurity | - |
| `backend/services/data_platform/analytical_package_service.py` | AnalyticalPackageService | - |
| `backend/services/data_platform/analytical_storage.py` | AnalyticalStorage | - |
| `backend/services/data_platform/analytics_engine.py` | AnalyticsEngine | - |
| `backend/services/data_platform/blueprint_repository.py` | BlueprintRepository | _get_catalog_api |
| `backend/services/data_platform/blueprint_resolver.py` | BlueprintResolver | resolve_blueprint |
| `backend/services/data_platform/business_rules_engine.py` | BusinessRulesEngine | - |
| `backend/services/data_platform/calculation_engine.py` | CalculationEngine | - |
| `backend/services/data_platform/catalog_api.py` | CatalogAPI | - |
| `backend/services/data_platform/comparison_engine.py` | ComparisonEngine | - |
| `backend/services/data_platform/dashboard_builder.py` | DashboardBuilder | build_dashboard_schema |
| `backend/services/data_platform/dashboard_payload_builder.py` | DashboardPayloadBuilder | - |
| `backend/services/data_platform/data_access_layer.py` | DataAccessLayer | _get_catalog_api |
| `backend/services/data_platform/dataset_builder.py` | DatasetBuilder | - |
| `backend/services/data_platform/dependency_graph.py` | DependencyGraph | - |
| `backend/services/data_platform/enterprise_component_engine/__init__.py` | EnterpriseComponentEngine | - |
| `backend/services/data_platform/enterprise_component_engine/cache.py` | ComponentCache | - |
| `backend/services/data_platform/enterprise_component_engine/diagnostics.py` | ComponentDiagnostics | - |
| `backend/services/data_platform/enterprise_component_engine/events.py` | ComponentEvents | - |
| `backend/services/data_platform/enterprise_component_engine/factory.py` | ComponentFactory | - |
| `backend/services/data_platform/enterprise_component_engine/lifecycle.py` | ComponentLifecycle | - |
| `backend/services/data_platform/enterprise_component_engine/registry.py` | ComponentRegistry | - |
| `backend/services/data_platform/enterprise_component_engine/renderer.py` | ComponentRenderer | - |
| `backend/services/data_platform/enterprise_component_engine/schemas.py` | ComponentSchema | - |
| `backend/services/data_platform/enterprise_component_engine/security.py` | ComponentSecurity | - |
| `backend/services/data_platform/enterprise_component_engine/state_manager.py` | ComponentStateManager | - |
| `backend/services/data_platform/event_engine.py` | EventEngine | - |
| `backend/services/data_platform/execution_engine.py` | ExecutionEngine | _get_catalog_api, _get_analytics_engines, execute_blueprint |
| `backend/services/data_platform/health_monitor.py` | HealthMonitor | - |
| `backend/services/data_platform/history_service.py` | HistoryService | - |
| `backend/services/data_platform/insight_layer.py` | InsightLayer | generate_insights |
| `backend/services/data_platform/integrity_service.py` | IntegrityService | _get_catalog_api |
| `backend/services/data_platform/intent_fingerprint.py` | IntentFingerprintGenerator | - |
| `backend/services/data_platform/lineage_service.py` | LineageService | - |
| `backend/services/data_platform/live_dashboard_runtime.py` | LiveDashboardRuntime | - |
| `backend/services/data_platform/metadata_catalog.py` | MetadataCatalogService | - |
| `backend/services/data_platform/package_cache.py` | _CacheEntry, PackageCacheIntelligence | - |
| `backend/services/data_platform/package_compatibility.py` | PackageCompatibilityEngine | - |
| `backend/services/data_platform/package_version_manager.py` | PackageVersionManager | - |
| `backend/services/data_platform/performance_layer.py` | PerformanceLayer | - |
| `backend/services/data_platform/query_resolver.py` | QueryResolver | - |
| `backend/services/data_platform/semantic_catalog.py` | SemanticCatalogService | - |
| `backend/services/data_platform/sync_engine.py` | SyncEngine | get_tenant_sync_lock |
| `backend/services/data_platform/sync_scheduler.py` | SyncOrchestrator | get_orchestrator_lock |
| `backend/services/data_platform/trend_engine.py` | TrendEngine | - |
| `backend/services/data_platform/trust_center_engine.py` | TrustCenterEngine | - |
| `backend/services/data_platform/view_manager.py` | ViewManager | _get_catalog_api |
| `backend/services/data_transformer.py` | - | is_numeric_value, to_float, clean_row_data, transform_data, transform_chart_data, transform_pie_data, transform_table_data, transform_kpi_data, transform_scatter_data |
| `backend/services/mock_service.py` | - | _labels_mensais, gerar_raw_rows_mock, gerar_dados_mock_oracle |
| `backend/services/oracle_service.py` | MockOracleCursor, MockOracleConnection | decrypt_connection_details, close_oracle_pool, get_oracle_connection, get_view_columns, execute_view |
| `backend/services/performance/performance_optimization_platform.py` | PerformanceOptimizationPlatform | - |
| `backend/services/plan_validator.py` | ValidatedPlanResponse | normalize_text_key, resolve_relative_date_range, validate_and_normalize_plan |
| `backend/services/postgresql_clone_service.py` | - | _get_pg_lock, close_clone_db_pool, get_clone_db_connection, release_clone_db_connection, get_clone_view_columns, execute_clone_view |
| `backend/services/query_history_service.py` | - | persist_query_history |
| `backend/services/query_intelligence_engine.py` | BlueprintVersionamento, BlueprintModel, _PreliminaryIntention, QueryIntelligenceEngine | - |
| `backend/services/query_planner.py` | QueryPlanItem, QueryPlan | _suggest_visualizacao, _find_view_by_keyword, create_query_plan |
| `backend/services/scheduler.py` | - | run_sync_task, _scheduler_loop, start_scheduler, stop_scheduler |
| `backend/services/security/enterprise_security_platform.py` | EnterpriseSecurityPlatform | - |
| `backend/services/semantic_layer.py` | - | _normalize_alias_key, _singularize_token, _metric_key_variants, _build_metric_alias_index, _resolve_metric_by_safe_similarity, canonicalize_metric_name, get_metric_info, validate_metrics_and_sources, register_custom_metric, sync_from_semantic_catalog |
| `backend/services/sync_service.py` | - | _get_sync_config, sync_tenant_database |

## frontend/app

- `frontend/app/auth/first-access/page.tsx`
- `frontend/app/dashboard/admin/catalog/page.tsx`
- `frontend/app/dashboard/admin/settings/page.tsx`
- `frontend/app/dashboard/admin/users/page.tsx`
- `frontend/app/dashboard/page.tsx`
- `frontend/app/dashboard/studio/page.tsx`
- `frontend/app/globals.css`
- `frontend/app/layout.tsx`
- `frontend/app/login/page.tsx`
- `frontend/app/page.tsx`

## frontend/components

- `frontend/components/charts/AreaChartComponent.tsx`
- `frontend/components/charts/BarChartComponent.tsx`
- `frontend/components/charts/DataTable.tsx`
- `frontend/components/charts/EAreaChart.tsx`
- `frontend/components/charts/EBarChart.tsx`
- `frontend/components/charts/echartsTypes.ts`
- `frontend/components/charts/EFunnelChart.tsx`
- `frontend/components/charts/EHeatmapChart.tsx`
- `frontend/components/charts/EKPICards.tsx`
- `frontend/components/charts/ELineChart.tsx`
- `frontend/components/charts/EPieChart.tsx`
- `frontend/components/charts/EScatterChart.tsx`
- `frontend/components/charts/ETreemapChart.tsx`
- `frontend/components/charts/KPICards.tsx`
- `frontend/components/charts/LineChartComponent.tsx`
- `frontend/components/charts/PieChartComponent.tsx`
- `frontend/components/charts/useEChartsReflow.ts`
- `frontend/components/chat/AssistantResponseBlock.tsx`
- `frontend/components/chat/ChatInterface.tsx`
- `frontend/components/chat/InlineDashboardRuntime.tsx`
- `frontend/components/component-library/controls/AlertBanner.tsx`
- `frontend/components/component-library/index.ts`
- `frontend/components/component-library/kpis/KpiCard.tsx`
- `frontend/components/component-library/status/StatusComponents.tsx`
- `frontend/components/component-library/tables/RankingTable.tsx`
- `frontend/components/dashboard-runtime/DashboardRuntimeEngine.tsx`
- `frontend/components/dashboard-runtime/GridEngine.tsx`
- `frontend/components/dashboard-runtime/RuntimeRenderer.tsx`
- `frontend/components/dashboard-runtime/TrustCenterPanel.tsx`
- `frontend/components/DynamicRenderer.tsx`
- `frontend/components/interaction-engine/CrossFilterManager.tsx`
- `frontend/components/interaction-engine/FullscreenManager.tsx`
- `frontend/components/performance/VirtualizationEngine.tsx`
- `frontend/components/Sidebar.tsx`
- `frontend/components/ThemeToggle.tsx`
- `frontend/components/ui/Badge.tsx`
- `frontend/components/ui/ErrorBoundary.tsx`
- `frontend/components/ui/GlassCard.tsx`
- `frontend/components/ui/SkeletonGrid.tsx`
- `frontend/components/ui/TooltipHelp.tsx`

## frontend/hooks

- `frontend/hooks/useDashboardRuntime.ts`
- `frontend/hooks/useGridLayout.ts`
- `frontend/hooks/useLuminaQuery.ts`
- `frontend/hooks/usePerformanceMonitor.ts`
- `frontend/hooks/useSSEEvents.ts`

## frontend/engines

- `frontend/engines/gridEngine.ts`
- `frontend/engines/layoutIntelligence.ts`
- `frontend/engines/performanceMonitor.ts`
- `frontend/engines/responsivenessEngine.ts`

## frontend/lib

- `frontend/lib/authSession.ts`
- `frontend/lib/dashboardRuntimeAdapter.ts`
- `frontend/lib/exportUtils.ts`
- `frontend/lib/utils.ts`

## frontend/types

- `frontend/types/dashboard-runtime.ts`
- `frontend/types/lumina.ts`

## Tabelas Detectadas Em `backend/database/init.sql`

- `blueprint_repository`
- `dashboard_instances`
- `dashboard_studio_versions`
- `dashboard_templates`
- `data_platform_history`
- `datasets`
- `favorites`
- `metadata_catalog`
- `search_history`
- `semantic_catalog`
- `tenants`
- `users`
- `view_catalog`
