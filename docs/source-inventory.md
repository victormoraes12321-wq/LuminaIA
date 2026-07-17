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
| `backend/models/new_pipeline_contracts.py` | ExecutionStatus, IntentType, VisualizationType, ComparisonOperator, QueryCost, EmptyDatasetPolicy, TrackedModel, SemanticFilter, SemanticPlan, CanonicalFilter, CanonicalPlan, ResolvedEntity, ResolvedEntities, ExecutionPlan, ExecutionResult, QueryContext, DashboardState, ConversationNode, ConversationGraph | validate_tracked_model_inheritance |
| `backend/models/package_dashboard_instance.py` | PackageDashboardInstance | - |
| `backend/models/search_history.py` | SearchHistory | - |
| `backend/models/semantic_catalog.py` | SemanticCatalog | - |
| `backend/models/semantic_memory.py` | SemanticMemory | - |
| `backend/models/svr.py` | SVRConcept, SVRVersion, SVRCompatibilityMatrix, SVRAuditLog | - |
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
| `backend/schemas/roqg.py` | ComponentStatus, ComponentPriority, DeliveryDecision, ComponentRenderItem, RenderPlan, ROQGResponse | - |
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
| `backend/routers/svr.py` | ConceptRegisterRequest, ConceptDeprecateRequest, MigrationEvaluateRequest | get_version_center, get_concept_history, register_concept, deprecate_concept_version, evaluate_migration |
| `backend/routers/tenant.py` | - | get_tenant_settings, update_tenant_settings, test_oracle_connection, test_ai_connection, get_ai_credential_status, get_ai_invocation_status, get_tenant_audit_logs, test_postgres_clone_connection, trigger_tenant_sync, get_tenant_sync_progress |
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
| `backend/services/ai/csie.py` | CorporateConceptRef, CorporateFilterRef, SemanticScores, SemanticHypothesis, CorporateIntentPlan, CorporateSemanticIntelligenceEngine | - |
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
| `backend/services/ai_credential_manager.py` | AICMError, AICMCredentialUnavailableError, AICMProviderUnavailableError, AICMAuthenticationError, ProviderProfile, CredentialCandidate, CredentialState, AIClientLease, AICredentialManager | - |
| `backend/services/ai_invocation_manager.py` | AIMDecisionScores, AIMDecision, AIMInvocationResult, AIMPolicyViolationError, AIInvocationManager | - |
| `backend/services/ai_service.py` | - | _is_probably_invalid_openai_key, _is_openai_auth_error, _normalize_fallback_text, _find_catalog_view_for_fallback, _extract_limit_for_fallback, _extract_date_range_for_fallback, _extract_city_for_fallback, _extract_registry_params_for_fallback, _first_fallback_match, _extract_entity_registry_params_for_fallback, _build_deterministic_fallback_intention, validate_authorized_model |
| `backend/services/aqd_service.py` | AnalyticalTask, MasterBlueprint, CandidateStrategy, IntencaoAnalitica, AnalyticalResolutionPlan, AQDDecompositionResult, AnalyticalQueryDecomposer | _is_visual_only_fragment, record_strategy_success |
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
| `backend/services/corporate_abstraction_layer.py` | CorporateAbstractionLayer | - |
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
| `backend/services/data_platform/analytical_storage.py` | AnalyticalStorage | _safe_identifier, _parse_internal_list, _safe_order_direction |
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
| `backend/services/data_platform/integrity_service.py` | IntegrityService | _get_catalog_api |
| `backend/services/data_platform/intent_fingerprint.py` | IntentFingerprintGenerator | - |
| `backend/services/data_platform/lineage_service.py` | LineageService | - |
| `backend/services/data_platform/live_dashboard_runtime.py` | LiveDashboardRuntime | - |
| `backend/services/data_platform/metadata_catalog.py` | MetadataCatalogService | - |
| `backend/services/data_platform/package_cache.py` | _CacheEntry, PackageCacheIntelligence | - |
| `backend/services/data_platform/package_compatibility.py` | PackageCompatibilityEngine | _coerce_fingerprint |
| `backend/services/data_platform/package_version_manager.py` | PackageVersionManager | - |
| `backend/services/data_platform/performance_layer.py` | PerformanceLayer | - |
| `backend/services/data_platform/query_resolver.py` | QueryResolver | - |
| `backend/services/data_platform/semantic_catalog.py` | SemanticCatalogService | - |
| `backend/services/data_platform/sync_engine.py` | SyncEngine | _split_oracle_identifier, _oracle_identifier, _local_table_name, _close_oracle_resource, _maybe_await, _serialize_dataset_value, get_tenant_sync_lock |
| `backend/services/data_platform/sync_scheduler.py` | SyncOrchestrator | get_orchestrator_lock |
| `backend/services/data_platform/trend_engine.py` | TrendEngine | - |
| `backend/services/data_platform/trust_center_engine.py` | TrustCenterEngine | - |
| `backend/services/data_platform/view_manager.py` | ViewManager | _get_catalog_api |
| `backend/services/data_transformer.py` | - | is_numeric_value, to_float, _humanize_key, _is_metric_key, _preferred_numeric_keys, _preferred_label_key, clean_row_data, transform_data, transform_chart_data, transform_pie_data, transform_table_data, transform_kpi_data |
| `backend/services/enterprise_audit_engine.py` | AuditQuestion, AuditScenario, AuditEvidence, AuditFinding, AuditReport, EnterpriseAuditEngine | run_enterprise_audit |
| `backend/services/iar_service.py` | IARAuditorItem, IntelligentAnalyticalResolver | - |
| `backend/services/metadata_catalog/__init__.py` | - | - |
| `backend/services/metadata_catalog/canonicalizer.py` | SemanticCanonicalizer | - |
| `backend/services/metadata_catalog/catalog.py` | - | get_corporate_catalog, set_corporate_catalog |
| `backend/services/metadata_catalog/conversation_graph.py` | ConversationGraphManager | - |
| `backend/services/metadata_catalog/executor.py` | QueryPlanner, QueryOptimizer, SQLGenerator, SecurityValidator, DatabaseExecutor | - |
| `backend/services/metadata_catalog/explainability.py` | ExplainabilityEngine | - |
| `backend/services/metadata_catalog/intent_engine.py` | SemanticPatch, IntentEngineOutput, CorporateIntentEngine | - |
| `backend/services/metadata_catalog/loader.py` | - | load_corporate_catalog |
| `backend/services/metadata_catalog/models.py` | ColumnDataType, ViewType, AggregationType, ColumnMetadata, RelationshipMetadata, ViewMetadata, BusinessEntityMetadata, MetricMetadata, DimensionMetadata, AliasMetadata, CorporateCatalog | - |
| `backend/services/metadata_catalog/repository.py` | CorporateCatalogRepository | - |
| `backend/services/metadata_catalog/resolver.py` | MetadataResolver | - |
| `backend/services/metadata_catalog/self_healing.py` | SelfHealingEngine | - |
| `backend/services/metadata_catalog/validator.py` | CatalogValidationError | validate_catalog |
| `backend/services/mock_service.py` | - | _labels_mensais, gerar_raw_rows_mock, gerar_dados_mock_oracle |
| `backend/services/new_query_orchestrator.py` | ExecutiveExplanation, NewQueryOrchestrator | - |
| `backend/services/oracle_service.py` | OracleConnectionValidationError, MockOracleCursor, MockOracleConnection | _safe_oracle_identifier, _close_oracle_resource, validate_oracle_listener, classify_oracle_connection_error, decrypt_connection_details, close_oracle_pool, get_oracle_connection, get_view_columns, execute_view |
| `backend/services/performance/performance_optimization_platform.py` | PerformanceOptimizationPlatform | - |
| `backend/services/postgresql_clone_service.py` | - | _clone_table_name, _normalize_search_value, _text_search_clause, _text_search_pattern, _parse_internal_list, _first_present, _enrich_semantic_aliases, _resolve_existing_column, _metric_select_expression, _normalize_metric_key, _order_alias_from_metrics, _safe_order_direction |
| `backend/services/query_history_service.py` | - | persist_query_history |
| `backend/services/query_intelligence_engine.py` | BlueprintVersionamento, BlueprintModel, _PreliminaryIntention, QueryIntelligenceEngine | _catalog_names, _catalog_has_family, _catalog_gap_for_query, _requires_fresh_ai_interpretation, _is_reusable_blueprint_candidate, _entity_from_blueprint, _resolve_blueprint_catalog_view, _extract_explicit_row_limit, _apply_explicit_row_limit, _sanitize_intention_params, _safe_int, _month_range_from_params |
| `backend/services/query_optimizer_engine.py` | QueryOptimizer, SQLGenerator | translate_expression |
| `backend/services/query_planner.py` | QueryPlanItem, QueryPlan | _suggest_visualizacao, _find_view_by_keyword, _intention_domain, _domain_keywords, _is_registry_catalog_view, _is_registry_intention, _score_view_for_domain, _guard_primary_view_domain, _requires_daily_view, _attach_structured_execution_hints, _score_daily_view, _guard_temporal_granularity |
| `backend/services/ris_service.py` | FreshnessResult, SufficiencyResult, EvidenceTrail, ConsistencyResult, ContradictionResult, BusinessContextResult, ExplainabilityResult, InsightResult, HypothesisAssumptionResult, AmbiguityResult, ReasoningGovernanceResult, RecommendationItem, ResponseQualityResult, TrustAnalyzerResult, QualitySLAResult, ResponseIntelligencePackage, RISResult, ResponseIntelligenceSuite | - |
| `backend/services/roqg_service.py` | ResponseOrchestratorQualityGate | _utc_timestamp |
| `backend/services/scheduler.py` | - | run_sync_task, _scheduler_loop, start_scheduler, stop_scheduler |
| `backend/services/security/enterprise_security_platform.py` | EnterpriseSecurityPlatform | - |
| `backend/services/security_and_normalization_engine.py` | SecurityValidationError, EmptyDatasetAnomalyError, SecurityValidator, ResultNormalizer | - |
| `backend/services/semantic_layer.py` | - | _normalize_alias_key, _singularize_token, _metric_key_variants, _build_metric_alias_index, _resolve_metric_by_safe_similarity, canonicalize_metric_name, get_metric_info, resolve_metric_for_view, validate_metrics_and_sources, register_custom_metric, sync_from_semantic_catalog |
| `backend/services/semantic_memory_repo.py` | - | get_semantic_memory_record, increment_memory_frequencia, create_semantic_memory_record |
| `backend/services/svr_migration.py` | SVRMigrationEngine | - |
| `backend/services/svr_service.py` | SemanticVersionRegistryService | - |
| `backend/services/sync_service.py` | - | _now_iso, _set_sync_progress, get_sync_progress, _close_oracle_resource, _get_sync_config, sync_tenant_database |

## frontend/app

- `frontend/app/api/auth/clear-session/route.ts`
- `frontend/app/auth/first-access/page.tsx`
- `frontend/app/dashboard/admin/catalog/page.tsx`
- `frontend/app/dashboard/admin/settings/page.tsx`
- `frontend/app/dashboard/admin/users/page.tsx`
- `frontend/app/dashboard/inspector/page.tsx`
- `frontend/app/dashboard/page.tsx`
- `frontend/app/dashboard/studio/page.tsx`
- `frontend/app/dashboard/svr/page.tsx`
- `frontend/app/globals.css`
- `frontend/app/layout.tsx`
- `frontend/app/login/page.tsx`
- `frontend/app/page.tsx`

## frontend/components

- `frontend/components/charts/AreaChartComponent.tsx`
- `frontend/components/charts/BarChartComponent.tsx`
- `frontend/components/charts/chartTheme.ts`
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
- `frontend/components/chat/ClarificationPanel.tsx`
- `frontend/components/chat/ConversationGraphNavigator.tsx`
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
- `frontend/lib/textEncoding.ts`
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
- `semantic_memory`
- `tenants`
- `users`
- `view_catalog`
