# Inventario De Codigo

Fonte: varredura local de arquivos Python/TypeScript relevantes.

## backend/models

| Arquivo | Classes | Funcoes |
| --- | --- | --- |
| `backend/models/__init__.py` | - | - |
| `backend/models/ai_orchestration.py` | AIOrchestrationPolicyModel, AIModelDefinitionModel, AIProviderDefinitionModel, AIPromptTemplateVersionModel, AIOrchestrationRunModel, AIOrchestrationStepModel, AIModelInvocationRecordModel, AIToolCallRecordModel, AIUsageRecordModel, AIEvaluationCaseModel, AIEvaluationResultModel | - |
| `backend/models/ai_tool_registry.py` | AIToolIdentity, AIToolVersion, AIToolReview, AIToolPublication, AIToolRegistrySnapshot, AIToolRegistryMember, AIToolDependency, AIToolEvent, AIToolInvocationRecord, AIToolCircuitStateRecord, AIToolEvaluationCaseRecord, AIToolEvaluationResultRecord | - |
| `backend/models/analytical_package.py` | PackageStatus, AnalyticalPackage | - |
| `backend/models/blueprint.py` | Blueprint | - |
| `backend/models/business_concept.py` | BusinessConcept | - |
| `backend/models/business_formula.py` | BusinessFormula | - |
| `backend/models/business_governance_log.py` | BusinessGovernanceLog | - |
| `backend/models/business_kpi.py` | BusinessKPI | - |
| `backend/models/business_relationship.py` | BusinessRelationship | - |
| `backend/models/conversation_state.py` | ConversationSession, ConversationNodeRecord, ConversationStateSnapshot, ConversationEvent, ConversationLegacyImport | - |
| `backend/models/dashboard_ai_assistance_v2.py` | DashboardAiProposalModelV2, DashboardAiProposalVersionModelV2, DashboardAiClarificationModelV2, DashboardAiEvidenceModelV2, DashboardAiDecisionModelV2, DashboardAiRunModelV2, DashboardAiAuditEventModelV2, DashboardAiEvaluationCaseModelV2, DashboardAiEvaluationResultModelV2 | - |
| `backend/models/dashboard_backend_v2.py` | DashboardModelV2, DashboardRevisionModelV2, DashboardReviewModelV2, DashboardApprovalModelV2, DashboardPublicationModelV2, DashboardActivePublicationModelV2, DashboardCollaboratorModelV2, DashboardAccessPolicyModelV2, DashboardAuditEventModelV2, DashboardRuntimeExecutionModelV2, DashboardWidgetExecutionModelV2, DashboardEvaluationCaseModelV2, DashboardEvaluationResultModelV2 | - |
| `backend/models/dashboard_instance.py` | DashboardInstance | - |
| `backend/models/dashboard_preference.py` | DashboardPreference | - |
| `backend/models/dashboard_studio_version.py` | DashboardStudioVersion | - |
| `backend/models/dashboard_template.py` | DashboardTemplate | - |
| `backend/models/data_platform_history.py` | DataPlatformHistory | - |
| `backend/models/dataset.py` | Dataset | - |
| `backend/models/enterprise_knowledge.py` | EnterpriseKnowledgeAsset, EnterpriseKnowledgeVersion, EnterpriseKnowledgeApproval, EnterpriseKnowledgePublication, EnterpriseKnowledgeAlias, EnterpriseKnowledgeRelation, EnterpriseKnowledgeEvent, EnterpriseKnowledgeImport | - |
| `backend/models/favorite.py` | Favorite | - |
| `backend/models/metadata_catalog.py` | MetadataCatalog | - |
| `backend/models/metadata_catalog_version.py` | MetadataCatalogVersion | - |
| `backend/models/new_pipeline_contracts.py` | ExecutionStatus, IntentType, VisualizationType, ComparisonOperator, QueryCost, EmptyDatasetPolicy, TrackedModel, SemanticFilter, SemanticPlan, CanonicalFilter, CanonicalPlan, ResolvedEntity, ResolvedEntities, ExecutionPlan, ExecutionResult, QueryContext, DashboardState, ConversationNode, ConversationGraph | validate_tracked_model_inheritance |
| `backend/models/observability_v2.py` | OperationalMetricRollupModelV2, TraceSummaryModelV2, SloDefinitionModelV2, SloEvaluationModelV2, EvaluationSuiteModelV2, EvaluationRunModelV2, EvaluationRegressionModelV2, ObservabilityAuditEventModelV2 | - |
| `backend/models/package_dashboard_instance.py` | PackageDashboardInstance | - |
| `backend/models/post_sync_insights_v2.py` | PostSyncInsightPolicyModelV2, PostSyncInsightOutboxModelV2, PostSyncInsightRunModelV2, PostSyncInsightDetectorExecutionModelV2, PostSyncInsightCandidateModelV2, PostSyncInsightModelV2, PostSyncInsightEvidenceModelV2, PostSyncInsightUserStateModelV2, PostSyncInsightAuditEventModelV2, PostSyncInsightEvaluationCaseModelV2, PostSyncInsightEvaluationResultModelV2 | - |
| `backend/models/safe_analytical_postgresql.py` | AnalyticalCatalogDefinition, AnalyticalCatalogSnapshot, AnalyticalDatasetDefinition, AnalyticalExecutionRecord | - |
| `backend/models/search_history.py` | SearchHistory | - |
| `backend/models/semantic_catalog.py` | SemanticCatalog | - |
| `backend/models/semantic_memory.py` | SemanticMemory | - |
| `backend/models/semantic_retrieval.py` | SemanticIndexDefinition, SemanticIndexVersion, SemanticDocument, SemanticDocumentAlias, SemanticDocumentRelation, SemanticDocumentTerm, SemanticDocumentRepresentation, SemanticIndexPublication, SemanticIndexEvent, SemanticEvaluationCase, SemanticEvaluationResult, SemanticClarification | - |
| `backend/models/smart_cache_materialization.py` | SmartCachePolicyModel, SmartCacheGenerationModel, SmartCacheEntryModel, SmartCacheEntryDependencyModel, SmartCacheLeaseModel, SmartCacheEventModel, MaterializationDefinitionModel, MaterializationBuildModel, MaterializationSnapshotModel, MaterializationPublicationModel, MaterializationDependencyModel, MaterializationEventModel, SmartCacheEvaluationCaseModel, SmartCacheEvaluationResultModel | utc_now |
| `backend/models/supervised_feedback.py` | GovernedFeedbackRecord, GovernedFeedbackCorrection, GovernedFeedbackRedaction, GovernedFeedbackReview, GovernedFeedbackEvent, SupervisedTrainingCandidate, SupervisedTrainingExample, TrainingDatasetSnapshot, TrainingDatasetMember, TrainingDatasetExport, FeedbackDeletionRequest | - |
| `backend/models/svr.py` | SVRConcept, SVRVersion, SVRCompatibilityMatrix, SVRAuditLog | - |
| `backend/models/sync_queue.py` | SyncQueue | - |
| `backend/models/tenant.py` | Tenant | - |
| `backend/models/user.py` | UserRole, User | - |
| `backend/models/user_analytical_profile.py` | UserAnalyticalProfile, UserPreferenceItem, UserPreferenceConsent, UserProfileEvent, UserProfileExport, UserProfileDeletionRequest | - |
| `backend/models/validation_provenance.py` | ValidationPolicyModel, ValidationRunModel, AnalyticalFactModel, AnalyticalClaimModel, AnalyticalClaimBindingModel, ProvenanceManifestModel, ResultCertificationModel, ResponseCertificationModel, ValidationEventModel | - |
| `backend/models/view_catalog.py` | ChartType, ViewCatalog | - |
| `backend/models/work_queue_v2.py` | WorkQueueJobModelV2, WorkQueueAttemptModelV2, WorkQueueWorkerModelV2, WorkQueueDeadLetterModelV2, WorkQueueAuditEventModelV2, PerformanceBaselineModelV2, PerformanceRunModelV2 | - |

## backend/schemas

| Arquivo | Classes | Funcoes |
| --- | --- | --- |
| `backend/schemas/__init__.py` | - | - |
| `backend/schemas/conversation_state.py` | ConversationCreateRequest, ConversationMutationRequest, ConversationSessionPublic, ConversationSessionPage, ConversationNodePublic, ConversationNodePage | - |
| `backend/schemas/dashboard_preferences.py` | DashboardPreferenceUpdate, DashboardPreferenceResponse | - |
| `backend/schemas/dashboard_studio.py` | GridItem, ComponentConfig, DashboardTemplateCreate, DashboardTemplateUpdate, DashboardTemplateResponse, DashboardInstanceCreate, DashboardInstanceUpdate, DashboardInstanceResponse, DashboardStudioVersionResponse, DashboardDuplicateRequest, DashboardFavoriteRequest, DashboardRollbackRequest, DashboardLayoutValidationRequest, DashboardLayoutValidationResponse, DashboardExportResponse, DashboardImportRequest | - |
| `backend/schemas/dashboard_ui_sidechat.py` | StrictDashboardSideChatModel, DashboardSideChatFilterContextV2, DashboardSideChatSelectionContextV2, DashboardSideChatContextV2, DashboardNoActionV2, DashboardFocusWidgetActionV2, DashboardOpenProvenanceActionV2, DashboardApplyFilterActionV2, DashboardResetFiltersActionV2, DashboardDrilldownActionV2, DashboardVisualActionV2, DashboardBlockedActionV2 | - |
| `backend/schemas/favorite.py` | FavoriteCreate, FavoriteUpdate, FavoriteResponse | - |
| `backend/schemas/metadata_catalog.py` | MetadataCatalogResponse, MetadataCatalogVersionResponse | - |
| `backend/schemas/query.py` | ChatMessageSchema, QueryRequest, DatasetBar, ChartDataBar, DatasetLine, ChartDataLine, ChartDataPie, TableColumn, ChartDataTable, KPIItem, ChartDataKPI, VisualizationItem, IntentionPlanItem, QueryResponse, HistoryListItem, FavoriteListItem | - |
| `backend/schemas/roqg.py` | ComponentStatus, ComponentPriority, DeliveryDecision, ComponentRenderItem, RenderPlan, ROQGResponse | - |
| `backend/schemas/search_history.py` | SearchHistoryCreate, SearchHistoryResponse, SearchHistoryListResponse | - |
| `backend/schemas/tenant.py` | TenantBase, TenantCreate, TenantUpdate, TenantResponse, TenantSettingsUpdate | - |
| `backend/schemas/user.py` | UserBase, UserCreate, UserUpdate, UserResponse, UserPublic, LoginRequest, LoginResponse, ChangePasswordRequest, UserCreateAdmin, UserCreateAdminResponse | - |
| `backend/schemas/view_catalog.py` | ViewCatalogBase, ViewCatalogCreate, ViewCatalogUpdate, ViewCatalogResponse, ViewCatalogSummary | - |
| `backend/schemas/work_queue_v2.py` | WorkQueueJobResponseV2, WorkQueueJobListResponseV2, WorkQueueCancelRequestV2, WorkQueueReplayRequestV2, WorkQueueWorkerResponseV2, WorkQueueWorkerListResponseV2, WorkQueueDeadLetterResponseV2, WorkQueueDeadLetterListResponseV2, WorkQueueStatsResponseV2, PerformanceRunRequestV2, PerformanceRunResponseV2, PerformanceBaselineResponseV2 | - |

## backend/routers

| Arquivo | Classes | Funcoes |
| --- | --- | --- |
| `backend/routers/__init__.py` | - | - |
| `backend/routers/ai_orchestration.py` | PolicyUpdatePayload | _require_admin, run_ai_orchestration, list_model_definitions, list_provider_definitions, list_prompt_templates, get_orchestration_policies, simulate_inspection |
| `backend/routers/ai_tool_registry.py` | ProposalValidationRequest, ProposalValidationResponse, ReviewPayload | _ensure_admin, get_tool_catalog, validate_tool_proposal, invoke_governed_tool, list_admin_tools, register_admin_tool, review_tool_version, publish_tool_version, disable_tool_version, list_snapshots, test_tool_synthetic |
| `backend/routers/analytical_packages.py` | PackageSummaryResponse, PackageDetailResponse, PackageInstanceResponse, GlobalStatsResponse, DeprecateRequest | get_package_stats, list_packages, get_package, list_package_instances, deprecate_package, _to_summary_response, _to_detail_response, _to_instance_response |
| `backend/routers/auth.py` | - | _set_auth_cookie, _clear_auth_cookie, login, get_session, logout, change_password |
| `backend/routers/business_knowledge.py` | ConceptResponse, KPIResponse, FormulaResponse, ObservabilityResponse, ImpactResponse, RollbackRequest, RollbackResponse, RegisterConceptRequest, RegisterKPIRequest | _require_legacy_governance, list_dictionary_concepts, register_concept, list_registered_kpis, register_kpi, list_formulas, get_observability, get_impact_analysis, execute_rollback, seed_bke |
| `backend/routers/catalog.py` | - | _get_catalog_api, list_catalog_views, create_catalog_view, update_catalog_view, delete_catalog_view |
| `backend/routers/conversations.py` | - | _session_public, _raise_service_error, create_conversation, list_conversations, get_conversation, list_conversation_nodes, _mutate, reset_conversation, archive_conversation, reopen_conversation, delete_conversation |
| `backend/routers/dashboard.py` | - | listen_dashboard_events, force_dashboard_refresh, get_dashboard_telemetry |
| `backend/routers/dashboard_ai_assistance_v2.py` | DashboardAiDecisionRequestV2, DashboardAiCancelRequestV2 | _actor, _require_enabled, _require_generation, create_proposal, list_proposals, get_proposal, answer_clarification, revise_proposal, _decide, accept_proposal, reject_proposal, cancel_proposal |
| `backend/routers/dashboard_backend_v2.py` | - | _actor, _require_authoring, _require_published_read, _require_runtime, _runtime_service, _authorized_dashboard, create_dashboard, list_dashboards, get_dashboard, update_dashboard, clone_dashboard, archive_dashboard |
| `backend/routers/dashboard_preferences.py` | - | _validate_scope, _response_from_model, get_dashboard_preference, put_dashboard_preference |
| `backend/routers/dashboard_studio.py` | - | create_template, list_templates, get_template, update_template, list_template_versions, rollback_template, export_template, create_instance, list_instances, get_instance, update_instance, duplicate_instance |
| `backend/routers/dependencies.py` | - | get_current_user, check_admin_role, check_admin_or_gestor_role, enforce_password_change |
| `backend/routers/enterprise_knowledge.py` | StrictAction, AssetCreatedResponse, AssetDetailResponse, ReviewAction, ReviewResponse, LockAction, PublishAction, PublicationResponse, DraftAction, RollbackAction, OwnershipAction, DiffQuery | _service, _require_read_mode, _require_write_mode, search_published_knowledge, search_glossary, get_published_asset, get_metric_definition, review_queue, list_assets, create_asset, get_asset, list_versions |
| `backend/routers/metadata_catalog.py` | - | _normalize_tags, get_metadata_summary, get_metadata_health, search_metadata_catalog, get_metadata_entity, get_metadata_lineage, get_metadata_dependency_graph, get_metadata_impact, get_metadata_versions |
| `backend/routers/observability_v2.py` | - | _require_observability_enabled, _require_admin, _require_gestor_or_admin, get_observability_summary, get_observability_metrics, get_observability_trace, get_observability_slos, get_observability_slo_detail, list_evaluation_suites, run_evaluation_suite, list_evaluation_runs, get_evaluation_run |
| `backend/routers/post_sync_insights_v2.py` | StrictPostSyncApiBody, AcknowledgeBodyV2, DismissBodyV2, ReplayBodyV2 | _check_enabled, list_post_sync_insights, get_post_sync_policy, get_post_sync_insight_detail, get_post_sync_insight_evidence, acknowledge_post_sync_insight, dismiss_post_sync_insight, replay_post_sync_insight_run |
| `backend/routers/query.py` | - | _should_use_new_pipeline, _conversation_http_error, _fingerprint_json, _requests_conversation_backtrack, _state_from_governed_response, _complete_conversation_turn, _fail_conversation_turn, _persistir_historico, get_query_history, get_query_favorites, processar_consulta, obter_metricas_inteligencia |
| `backend/routers/safe_analytical_postgresql.py` | CompileRequest, ExecuteRequest | _require_admin_or_gestor, get_analytical_catalog, compile_analytical_query, execute_analytical_query |
| `backend/routers/semantic_retrieval.py` | StrictAction, SemanticCapabilities, DefinitionCreateAction, PublishAction, ClarificationResolveAction, ClarificationResolvedResponse, SemanticObservabilityResponse, EvaluationAction, DefinitionUpdateAction, DeprecateAction, PublicCandidateDetail, IndexManifestResponse | _policy, _retrieval, _lifecycle, _definition_contract, _require_read, _require_admin_feature, capabilities, search, inspect_search, resolve, resolve_entity, public_candidate_detail |
| `backend/routers/smart_cache_materialization.py` | MaterializationPublicationCommandV2, MaterializationRollbackCommandV2 | _permissions, _require, get_cache_statistics, invalidate_cache, execute_garbage_collection, publish_materialization, rollback_materialization |
| `backend/routers/supervised_feedback.py` | StrictAction, FeedbackCapabilities, ExplanationUpdate, LockAction, ReviewerAssignment, ReviewAction, DeletionAction, DeletionResult, CandidateApproval, DatasetCreate, DatasetTransition, DatasetExportAction, RetentionAction, RetentionResult | _service, _require_read, _require_write, _require_review, _require_curate, _require_shadow, capabilities, submit_feedback, shadow_evaluate_feedback, list_own_feedback, get_own_feedback, update_feedback_explanation |
| `backend/routers/svr.py` | ConceptRegisterRequest, ConceptDeprecateRequest, MigrationEvaluateRequest | get_version_center, get_concept_history, register_concept, deprecate_concept_version, evaluate_migration |
| `backend/routers/tenant.py` | - | get_tenant_settings, update_tenant_settings, test_oracle_connection, test_ai_connection, get_ai_credential_status, get_ai_invocation_status, get_tenant_audit_logs, test_postgres_clone_connection, trigger_tenant_sync, get_tenant_sync_progress |
| `backend/routers/user_analytical_profile.py` | StrictAction, LockAction, DeletionAction, ProfileCapabilities | _service, _require_read, _require_write, _etag, capabilities, get_profile, get_summary, list_preferences, applicable_preferences, get_preference, create_preference, update_preference |
| `backend/routers/users.py` | - | _generate_secure_password, create_user_by_admin, list_users, delete_user, toggle_user_active, update_user |
| `backend/routers/validation_provenance.py` | ValidationRunRequestBody | get_current_user_tenant, run_validation_pipeline, get_default_policy |
| `backend/routers/work_queue_v2.py` | - | _require_work_queue_enabled, _require_admin, _require_gestor_or_admin, list_jobs, get_job, cancel_job, replay_job, list_dead_letters, list_workers, get_stats, drain_queue, get_performance_baseline |

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
| `backend/services/ai_orchestration/__init__.py` | - | - |
| `backend/services/ai_orchestration/context_assembler.py` | GovernedAIContextAssembler | - |
| `backend/services/ai_orchestration/model_registry_service.py` | GovernedAIModelRouter | - |
| `backend/services/ai_orchestration/orchestrator.py` | GovernedAIOrchestrator | json_dumps |
| `backend/services/ai_orchestration/policy_service.py` | AIOrchestrationPolicyService | - |
| `backend/services/ai_orchestration/prompt_template_service.py` | AIPromptTemplateService | - |
| `backend/services/ai_orchestration/proposal_validator.py` | AIModelProposalValidator | - |
| `backend/services/ai_orchestration/provider_adapters/__init__.py` | - | - |
| `backend/services/ai_orchestration/provider_adapters/base.py` | GovernedAIProviderAdapter | - |
| `backend/services/ai_orchestration/provider_adapters/deterministic_fake.py` | DeterministicFakeAIProviderAdapter | - |
| `backend/services/ai_orchestration/provider_adapters/openai_adapter.py` | GovernedOpenAIProviderAdapter | - |
| `backend/services/ai_orchestration/response_composer.py` | GovernedAIResponseComposer | - |
| `backend/services/ai_orchestration/state_machine.py` | GovernedAIStateMachine | - |
| `backend/services/ai_orchestration/token_estimator.py` | AITokenEstimator | - |
| `backend/services/ai_service.py` | - | _is_probably_invalid_openai_key, _is_openai_auth_error, _normalize_fallback_text, _find_catalog_view_for_fallback, _extract_limit_for_fallback, _extract_date_range_for_fallback, _extract_city_for_fallback, _extract_registry_params_for_fallback, _first_fallback_match, _extract_entity_registry_params_for_fallback, _build_deterministic_fallback_intention, validate_authorized_model |
| `backend/services/ai_tool_registry/__init__.py` | - | - |
| `backend/services/ai_tool_registry/adapters/__init__.py` | - | - |
| `backend/services/ai_tool_registry/adapters/analytical_postgresql_adapter.py` | AnalyticalPostgreSQLQueryToolAdapter | - |
| `backend/services/ai_tool_registry/adapters/base.py` | GovernedToolAdapter | - |
| `backend/services/ai_tool_registry/adapters/context_adapter.py` | ContextGetPublicSummaryToolAdapter | - |
| `backend/services/ai_tool_registry/adapters/intent_and_planner_adapters.py` | IntentValidateToolAdapter, ComparisonPlanToolAdapter, ComparisonValidatePlanToolAdapter, ClarificationBuildOptionsToolAdapter, ProvenanceGetPublicSummaryToolAdapter | - |
| `backend/services/ai_tool_registry/adapters/knowledge_adapters.py` | EnterpriseKnowledgeSearchToolAdapter, EnterpriseKnowledgeGetMetricDefinitionToolAdapter | - |
| `backend/services/ai_tool_registry/adapters/profile_adapter.py` | ProfileGetApplicationSummaryToolAdapter | - |
| `backend/services/ai_tool_registry/adapters/registry_map.py` | - | get_adapter_class |
| `backend/services/ai_tool_registry/adapters/semantic_adapters.py` | SemanticSearchToolAdapter, SemanticResolveEntityToolAdapter | - |
| `backend/services/ai_tool_registry/adapters/temporal_adapter.py` | TemporalNormalizeToolAdapter | - |
| `backend/services/ai_tool_registry/catalog_builder.py` | AIToolCatalogBuilder | - |
| `backend/services/ai_tool_registry/circuit_breaker.py` | CircuitBreakerManager | - |
| `backend/services/ai_tool_registry/exceptions.py` | AIToolException, AIToolNotFoundException, AIToolAccessDeniedException, AIToolTenantMismatchException, AIToolAdapterNotRegisteredException, AIToolInputInvalidException, AIToolOutputInvalidException, AIToolTimeoutException, AIToolRateLimitedException, AIToolCircuitOpenException, AIToolDisabledException, AIToolDependencyCycleException, AIToolReservedCapabilityUnavailableException | - |
| `backend/services/ai_tool_registry/invocation_service.py` | GovernedAIToolInvocationService | - |
| `backend/services/ai_tool_registry/rate_limiter.py` | RateLimiterManager | - |
| `backend/services/ai_tool_registry/registry_service.py` | GovernedAIToolRegistryService | - |
| `backend/services/ai_tool_registry/repository.py` | AIToolRegistryRepository | - |
| `backend/services/analytical_fact_policy.py` | AnalyticalFactState, NumericalFact | aggregate_fact, ratio_fact, unavailable_fact |
| `backend/services/analytical_parity.py` | ParityStage, ParityFailureCause, ExpectedResolutionPath, StageOutcome, AnalyticalParityTrace | canonical_fingerprint, _sanitize, trace_from_pipeline_payload |
| `backend/services/aqd_service.py` | AnalyticalTask, MasterBlueprint, CandidateStrategy, IntencaoAnalitica, AnalyticalResolutionPlan, AQDDecompositionResult, AnalyticalQueryDecomposer | _is_visual_only_fragment, record_strategy_success |
| `backend/services/auth_service.py` | - | get_password_hash, verify_password, create_access_token, decode_access_token |
| `backend/services/bi_engine.py` | - | _to_float, process_bi_intelligence |
| `backend/services/blueprint_storage.py` | BlueprintStorageMode, BlueprintStorageLocation, BlueprintStoragePolicy, BlueprintJsonRepository, BlueprintRepositoryFactory | _register_cleanup, _repository_lock, _cleanup_test_path |
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
| `backend/services/comparison_execution/__init__.py` | - | - |
| `backend/services/comparison_execution/adapters.py` | - | execution_result_to_v2, execution_result_to_legacy, _deterministic_summary |
| `backend/services/comparison_execution/alignment.py` | ComparisonAlignmentError | align_operand_results, _alignment_key, _decimal_or_none, _string_or_none |
| `backend/services/comparison_execution/calculations.py` | ComparisonMathError | calculate_comparison, _pair_result, _rank_results, _share_results, _zero_denominator, _not_applicable, _direction, _round |
| `backend/services/comparison_execution/catalog.py` | MetricExecutionDefinition, DimensionExecutionDefinition, SourceExecutionDefinition, ComparisonExecutionCatalog, StaticComparisonExecutionCatalog | default_comparison_execution_catalog, _metric, _validate_expression |
| `backend/services/comparison_execution/compiler.py` | ComparisonCompilationError, GovernedComparisonQueryCompiler | select_execution_strategy |
| `backend/services/comparison_execution/executor.py` | ComparisonExecutionRejected, UniversalComparisonExecutor | _normalize_row, _summary_values |
| `backend/services/comparison_execution/feature_flags.py` | ComparisonExecutorFeaturePolicy | - |
| `backend/services/comparison_execution/fingerprints.py` | - | stable_fingerprint |
| `backend/services/comparison_execution/graph.py` | - | build_execution_graph |
| `backend/services/comparison_execution/models.py` | StrictExecutionModel, ComparisonExecutionStatus, OperandExecutionStatus, ExecutionNodeStatus, ExecutionNodeType, ComparisonExecutionStrategy, ComparisonDirection, ZeroDenominatorPolicy, RoundingPolicy, FailurePolicy, RetryPolicy, ComparisonExecutionContext, ComparisonExecutionNode, ComparisonExecutionGraph, CompiledOperandQuery, ComparisonExecutionProvenance, OperandExecutionResult, AlignedComparisonRow, AlignedComparisonDataset, ComparisonCalculationResult, ComparisonExecutionIssue, ComparisonExecutionResult | - |
| `backend/services/comparison_execution/query_runner.py` | ComparisonQueryRunner, TransientComparisonQueryError, SQLAlchemyComparisonQueryRunner, AsyncpgComparisonQueryRunner | _to_asyncpg_statement |
| `backend/services/comparison_execution/runtime.py` | ComparisonRuntimeUnavailable | build_execution_context_from_plan, execute_plan_on_tenant_clone |
| `backend/services/comparison_execution/validation.py` | - | build_validation_report, _validation_check |
| `backend/services/comparison_planning/__init__.py` | - | - |
| `backend/services/comparison_planning/feature_flags.py` | ComparisonPlannerFeaturePolicy, ComparisonPlannerGateway | - |
| `backend/services/comparison_planning/legacy_adapter.py` | ComparisonLegacyAdapterError | build_trusted_planning_context, plan_to_legacy_comparison_input, _reference_from_intent |
| `backend/services/comparison_planning/models.py` | ComparisonStrategyHint, PlanComplexityClassification, PlanningIssueSeverity, AlignmentCompatibility, MissingBucketPolicy, NullValuePolicy, StrictPlanningModel, ComparisonPlanningContext, ComparisonPlanningIssue, ComparisonPlanComplexity, ComparisonFilterPartition, ComparisonAlignmentSpecification, ComparisonOperandPlan, ComparisonExecutionPlanDefinition, ComparisonPlanningResult | - |
| `backend/services/comparison_planning/planner.py` | ComparisonPlanner | - |
| `backend/services/comparison_planning/providers.py` | MetricCatalogEntry, DimensionCatalogEntry, EntityCatalogEntry, TargetCatalogEntry, ComparisonCatalogProvider, StaticComparisonCatalog | default_comparison_catalog, metric_reference_matches_catalog, _metric_semantics, _logical_sources |
| `backend/services/connection_credentials.py` | - | decrypt_connection_details |
| `backend/services/context_guard.py` | ScopeViolationError | validate_user_query, sanitize_history, validate_params, validate_query_intent, apply_row_limit |
| `backend/services/context_resolution/__init__.py` | - | - |
| `backend/services/context_resolution/engine.py` | ContextResolutionError, ContextResolutionEngine | _normalize, _confidence, _inherited, _json, _unique |
| `backend/services/context_resolution/feature_flags.py` | ContextResolutionFeaturePolicy | - |
| `backend/services/context_resolution/legacy_adapter.py` | LegacySemanticPatchError | validate_legacy_semantic_patches |
| `backend/services/context_resolution/models.py` | StrictContextModel, ContextRelationship, FieldDecisionAction, ConflictSeverity, ContextResolutionContext, ContextSubjectSignature, PatchOperationBase, SetFieldOperation, ReplaceFieldOperation, AppendFieldOperation, RemoveFieldOperation, ClearFieldOperation, ResetContextOperation, SetPendingClarificationOperation, ResolvePendingClarificationOperation, SetActiveSubjectOperation, SetActiveComparisonOperation, ClearActiveComparisonOperation, SetActiveHeadReferenceOperation, ContextPatchV2, ContextFieldDecision, ContextConflict, PublicContextSummary, ContextResolutionResult | stable_fingerprint |
| `backend/services/context_resolution/observability.py` | - | safe_resolution_metadata |
| `backend/services/context_resolution/policies.py` | InheritanceMode, ContextFieldPolicy | _policy |
| `backend/services/conversation_state/__init__.py` | - | - |
| `backend/services/conversation_state/content_protector.py` | ConversationContentError, ProtectedContent, ConversationContentProtector | - |
| `backend/services/conversation_state/legacy_adapter.py` | LegacyNode, AdaptedLegacyGraph, LegacyConversationGraphAdapter, LegacyConversationImporter | - |
| `backend/services/conversation_state/repository.py` | ConversationStateRepository | utc_now |
| `backend/services/conversation_state/service.py` | ConversationStateError, StartedTurn, CompletedTurn, ConversationStateService | utc_now |
| `backend/services/corporate_abstraction_layer.py` | CorporateAbstractionLayer | - |
| `backend/services/daily_reconciliation.py` | DailyReconciliationService | - |
| `backend/services/dashboard_ai_assistance_v2/__init__.py` | - | - |
| `backend/services/dashboard_ai_assistance_v2/errors.py` | DashboardAiAssistanceError | - |
| `backend/services/dashboard_ai_assistance_v2/facades.py` | DashboardAiClarificationServiceV2, DashboardAiBlueprintProposalServiceV2, DashboardAiEvidenceServiceV2, DashboardAiAuditServiceV2, DashboardAiFeedbackServiceV2, DashboardAiEvaluationServiceV2 | - |
| `backend/services/dashboard_ai_assistance_v2/fixtures.py` | - | golden_cases |
| `backend/services/dashboard_ai_assistance_v2/integrity.py` | - | normalize_text, normalized_key, _canonical, checksum, assert_safe_untrusted_text |
| `backend/services/dashboard_ai_assistance_v2/intent.py` | DashboardAiIntentExtractionServiceV2 | - |
| `backend/services/dashboard_ai_assistance_v2/lifecycle.py` | DashboardAiProposalStateMachineV2 | - |
| `backend/services/dashboard_ai_assistance_v2/policy.py` | DashboardAiCapabilityV2, DashboardAiPolicyV2 | - |
| `backend/services/dashboard_ai_assistance_v2/rationale.py` | DashboardAiRationaleServiceV2 | - |
| `backend/services/dashboard_ai_assistance_v2/repositories.py` | DashboardAiProposalRepositoryV2, DashboardAiProposalVersionRepositoryV2, DashboardAiClarificationRepositoryV2, DashboardAiEvidenceRepositoryV2, DashboardAiDecisionRepositoryV2, DashboardAiRunRepositoryV2, DashboardAiAuditRepositoryV2, DashboardAiEvaluationRepositoryV2 | - |
| `backend/services/dashboard_ai_assistance_v2/resolution.py` | DashboardDesignResolutionV2, DashboardDesignSpecServiceV2 | _evidence |
| `backend/services/dashboard_ai_assistance_v2/semantic_compiler.py` | DashboardAiSemanticPatchCompilerV2 | - |
| `backend/services/dashboard_ai_assistance_v2/service.py` | DashboardAiAssistanceServiceV2, DashboardAiProposalApplicationServiceV2 | - |
| `backend/services/dashboard_ai_assistance_v2/synthesis.py` | DashboardBlueprintSynthesisService | - |
| `backend/services/dashboard_ai_assistance_v2/tool_registry.py` | DashboardAiToolCapabilityV2, DashboardAiToolPolicyV2 | - |
| `backend/services/dashboard_ai_assistance_v2/validation.py` | DashboardAiProposalValidationServiceV2 | - |
| `backend/services/dashboard_ai_assistance_v2/visual_proposal.py` | DashboardAiVisualProposalServiceV2 | - |
| `backend/services/dashboard_backend_v2/__init__.py` | - | - |
| `backend/services/dashboard_backend_v2/application.py` | DashboardActorContextV2, DashboardCacheInvalidatorV2, NoopDashboardCacheInvalidatorV2, DashboardAuditServiceV2, DashboardRevisionServiceV2, DashboardAuthoringServiceV2, DashboardPatchServiceV2, DashboardReviewServiceV2, DashboardPublicationServiceV2, DashboardRollbackServiceV2, DashboardCloneServiceV2, DashboardEvaluationServiceV2, DashboardBackupValidationServiceV2 | _uuid, _blueprint_from_json, revision_contract, revision_reference, dashboard_contract, publication_contract, _require_resource_access, resolve_resource_capabilities, _resolve_pointer, _apply_operations |
| `backend/services/dashboard_backend_v2/cache_adapter.py` | ExistingSmartCacheDashboardInvalidatorV2 | - |
| `backend/services/dashboard_backend_v2/collaboration.py` | DashboardAccessServiceV2 | _contract |
| `backend/services/dashboard_backend_v2/errors.py` | DashboardBackendError | not_found |
| `backend/services/dashboard_backend_v2/integrity.py` | - | _normalize, canonical_json, checksum, idempotency_fingerprint |
| `backend/services/dashboard_backend_v2/legacy_dry_run.py` | DashboardLegacyDryRunServiceV2 | - |
| `backend/services/dashboard_backend_v2/observability.py` | DashboardMetricPointV2, DashboardObservabilityV2 | - |
| `backend/services/dashboard_backend_v2/policy.py` | DashboardBackendMode, DashboardLifecycleServiceV2, DashboardAccessPolicyServiceV2 | - |
| `backend/services/dashboard_backend_v2/repositories.py` | DashboardRepositoryV2, DashboardRevisionRepositoryV2, DashboardPublicationRepositoryV2, DashboardAccessRepositoryV2, DashboardAuditRepositoryV2, DashboardRuntimeRepositoryV2 | _uuid, _assert_replay |
| `backend/services/dashboard_backend_v2/runtime.py` | DashboardRuntimePlanningServiceV2, ResolvedWidgetQueryV2, DashboardWidgetQueryResolverV2, GovernedCatalogWidgetQueryResolverV2, CertifiedWidgetPayloadV2, DashboardWidgetAuthorityV2, ExistingAnalyticalAuthoritiesWidgetExecutorV2, DashboardWidgetExecutionServiceV2, DashboardRuntimeExecutionServiceV2 | _canonical_value, _validate_filter, _typed_data |
| `backend/services/dashboard_blueprint_v2/__init__.py` | - | - |
| `backend/services/dashboard_blueprint_v2/canonicalizer.py` | DashboardBlueprintCanonicalizer | - |
| `backend/services/dashboard_blueprint_v2/compatibility.py` | DashboardCompatibilityCheckV2, DashboardBlueprintCompatibilityService | - |
| `backend/services/dashboard_blueprint_v2/fixtures.py` | - | widget_states, widget_accessibility, fixed_period, metric_binding, data_binding, kpi_widget, line_widget, ranking_widget, table_widget, _layout, assemble_blueprint, build_executive_dashboard |
| `backend/services/dashboard_blueprint_v2/legacy_adapter.py` | LegacyDashboardBlueprintAdapter | - |
| `backend/services/dashboard_blueprint_v2/registries.py` | DashboardWidgetRegistryEntryV2, DashboardFeatureRegistryEntryV2 | get_widget_registry_entry, get_feature_registry_entry |
| `backend/services/dashboard_blueprint_v2/validation_service.py` | DashboardValidator, DashboardContractValidator, DashboardIdentityValidator, DashboardVersionValidator, DashboardLifecycleValidator, DashboardSecurityValidator, DashboardClassificationValidator, DashboardPermissionValidator, DashboardLayoutValidator, DashboardWidgetValidator, DashboardBindingValidator, DashboardFilterValidator, DashboardInteractionValidator, DashboardFormattingValidator, DashboardAccessibilityValidator, DashboardProvenanceValidator, DashboardCompatibilityValidator, DashboardPatchValidator, DashboardBlueprintValidationService | _issue |
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
| `backend/services/data_platform/business_layer.py` | BusinessLayer | _get_metric_info, apply_business_rules |
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
| `backend/services/data_transformer.py` | - | is_numeric_value, to_float, _is_currency_key, _humanize_key, _is_metric_key, _preferred_numeric_keys, _preferred_label_key, _ordered_union_keys, _first_non_empty_value, clean_row_data, transform_data, transform_chart_data |
| `backend/services/enterprise_audit_engine.py` | AuditQuestion, AuditScenario, AuditEvidence, AuditFinding, AuditReport, EnterpriseAuditEngine | run_enterprise_audit |
| `backend/services/enterprise_knowledge/__init__.py` | - | - |
| `backend/services/enterprise_knowledge/cache.py` | _CacheEntry, EnterpriseKnowledgeCache | - |
| `backend/services/enterprise_knowledge/errors.py` | EnterpriseKnowledgeError, KnowledgeNotFoundError, KnowledgeAccessDeniedError, KnowledgeConflictError, KnowledgeLifecycleError, KnowledgeBindingError, KnowledgeValidationError, KnowledgeFeatureDisabledError | - |
| `backend/services/enterprise_knowledge/legacy_adapter.py` | LegacyKnowledgeConversion, LegacyBusinessKnowledgeAdapter | - |
| `backend/services/enterprise_knowledge/metric_binding.py` | MetricBindingResult | official_formula_fingerprint, validate_metric_binding |
| `backend/services/enterprise_knowledge/normalization.py` | - | normalize_lexical, _canonical_value, canonical_json, compute_checksum, encode_cursor, decode_cursor, csv_safe |
| `backend/services/enterprise_knowledge/observability.py` | KnowledgeCounters | - |
| `backend/services/enterprise_knowledge/permissions.py` | - | access_decision, require_permission |
| `backend/services/enterprise_knowledge/repository.py` | EnterpriseKnowledgeRepository | - |
| `backend/services/enterprise_knowledge/runtime.py` | KnowledgeRuntimeProjection, EnterpriseKnowledgeRuntime | - |
| `backend/services/enterprise_knowledge/service.py` | EnterpriseKnowledgeService | utc_now, _content_from_row, _display_name, _source_references, _content_aliases |
| `backend/services/erp_reconciliation.py` | ReconciliationPeriod, ERPReconciliationService | - |
| `backend/services/financial_source_discovery.py` | ColumnProfile, SourceProfile, SourceAssessment, FinancialSourceDiscoveryService | - |
| `backend/services/iar_service.py` | IARAuditorItem, IntelligentAnalyticalResolver | - |
| `backend/services/metadata_catalog/__init__.py` | - | - |
| `backend/services/metadata_catalog/canonicalizer.py` | SemanticCanonicalizer | - |
| `backend/services/metadata_catalog/catalog.py` | - | get_corporate_catalog, set_corporate_catalog |
| `backend/services/metadata_catalog/conversation_graph.py` | ConversationGraphManager, StatelessConversationGraphAdapter | - |
| `backend/services/metadata_catalog/executor.py` | QueryPlanner, QueryOptimizer, SQLGenerator, SecurityValidator, DatabaseExecutor | - |
| `backend/services/metadata_catalog/explainability.py` | ExplainabilityEngine | - |
| `backend/services/metadata_catalog/intent_engine.py` | SemanticPatch, IntentEngineOutput, CorporateIntentEngine | - |
| `backend/services/metadata_catalog/loader.py` | - | load_corporate_catalog |
| `backend/services/metadata_catalog/models.py` | ColumnDataType, ViewType, AggregationType, ColumnMetadata, RelationshipMetadata, ViewMetadata, BusinessEntityMetadata, MetricMetadata, DimensionMetadata, AliasMetadata, CorporateCatalog | - |
| `backend/services/metadata_catalog/repository.py` | CorporateCatalogRepository | - |
| `backend/services/metadata_catalog/resolver.py` | MetadataResolver | - |
| `backend/services/metadata_catalog/self_healing.py` | SelfHealingEngine | - |
| `backend/services/metadata_catalog/validator.py` | CatalogValidationError | validate_catalog |
| `backend/services/metric_registry.py` | MetricDefinition | _financial_runtime_source, _definition, _add, core_sales_metric_audit |
| `backend/services/mock_service.py` | - | _labels_mensais, gerar_raw_rows_mock, gerar_dados_mock_oracle |
| `backend/services/new_query_orchestrator.py` | ExecutiveExplanation, NewQueryOrchestrator | - |
| `backend/services/observability_v2/__init__.py` | - | - |
| `backend/services/observability_v2/audit_service.py` | ObservabilityAuditService | - |
| `backend/services/observability_v2/cardinality.py` | OperationalMetricCardinalityGuard | - |
| `backend/services/observability_v2/context.py` | ObservabilityContextService | - |
| `backend/services/observability_v2/evaluations/__init__.py` | - | - |
| `backend/services/observability_v2/evaluations/baseline.py` | EvaluationBaselineServiceV2 | - |
| `backend/services/observability_v2/evaluations/corpus.py` | EvaluationCorpusServiceV2 | _make_case |
| `backend/services/observability_v2/evaluations/registry.py` | EvaluationSuiteRegistryV2 | - |
| `backend/services/observability_v2/evaluations/regression.py` | EvaluationRegressionServiceV2 | - |
| `backend/services/observability_v2/evaluations/runner.py` | GovernedEvaluationRunnerV2 | - |
| `backend/services/observability_v2/event_registry.py` | OperationalEventRegistryV2 | - |
| `backend/services/observability_v2/metric_registry.py` | OperationalMetricRegistryV2 | - |
| `backend/services/observability_v2/redaction.py` | ObservabilityRedactionService | - |
| `backend/services/observability_v2/slo_service.py` | SloEvaluationService | - |
| `backend/services/observability_v2/telemetry_service.py` | OperationalTelemetryService | - |
| `backend/services/observability_v2/trace_service.py` | SpanService, TraceService | - |
| `backend/services/oracle_service.py` | OracleConnectionValidationError, MockOracleCursor, MockOracleConnection | _safe_oracle_identifier, _close_oracle_resource, validate_oracle_listener, classify_oracle_connection_error, close_oracle_pool, get_oracle_connection, get_view_columns, execute_view |
| `backend/services/performance/performance_optimization_platform.py` | PerformanceOptimizationPlatform | - |
| `backend/services/plan_validator.py` | ValidatedPlanResponse | normalize_text_key, _is_customer_registry_view, _has_financial_or_sales_context, _is_registry_view, _is_customer_registry_listing_query, _is_registry_listing_query, resolve_relative_date_range, validate_and_normalize_plan |
| `backend/services/post_sync_insights_v2/__init__.py` | - | - |
| `backend/services/post_sync_insights_v2/audit.py` | PostSyncInsightAuditService | - |
| `backend/services/post_sync_insights_v2/certification.py` | PostSyncInsightCertificationService | - |
| `backend/services/post_sync_insights_v2/deduplication.py` | PostSyncInsightDeduplicationService | - |
| `backend/services/post_sync_insights_v2/detector_registry.py` | BasePostSyncDetector, MetricChangeDetector, TargetAttainmentDetector, ThresholdBreachDetector, RankingMovementDetector, RobustAnomalyDetector, FreshnessDegradationDetector, CompletenessDegradationDetector, ReconciliationVarianceDetector, SourceVolumeChangeDetector, NewDataAvailableDetector, PostSyncInsightDetectorRegistry | - |
| `backend/services/post_sync_insights_v2/evaluation.py` | PostSyncInsightEvaluationService | - |
| `backend/services/post_sync_insights_v2/execution.py` | PostSyncInsightExecutionService | - |
| `backend/services/post_sync_insights_v2/outbox.py` | PostSyncInsightOutboxServiceV2 | - |
| `backend/services/post_sync_insights_v2/planning.py` | PostSyncInsightPlanningService | - |
| `backend/services/post_sync_insights_v2/policy.py` | - | get_default_post_sync_policy |
| `backend/services/post_sync_insights_v2/prioritization.py` | PostSyncInsightPrioritizationService | - |
| `backend/services/post_sync_insights_v2/publication.py` | PostSyncInsightPublicationService | _to_uuid |
| `backend/services/post_sync_insights_v2/replay.py` | PostSyncInsightReplayService | - |
| `backend/services/post_sync_insights_v2/service.py` | PostSyncInsightsServiceV2 | _to_uuid, _validate_json_dict |
| `backend/services/post_sync_insights_v2/trigger.py` | PostSyncInsightTriggerServiceV2 | - |
| `backend/services/post_sync_insights_v2/user_state.py` | PostSyncInsightUserStateService | - |
| `backend/services/post_sync_insights_v2/validation.py` | PostSyncInsightValidationService | - |
| `backend/services/postgresql_clone_service.py` | - | _clone_table_name, _normalize_search_value, _text_search_clause, _text_search_pattern, _parse_internal_list, _first_present, _enrich_semantic_aliases, _resolve_existing_column, _metric_select_expression, _normalize_metric_key, _order_alias_from_metrics, _safe_order_direction |
| `backend/services/query_history_service.py` | - | persist_query_history |
| `backend/services/query_intelligence_engine.py` | BlueprintVersionamento, BlueprintModel, _PreliminaryIntention, QueryIntelligenceEngine | _catalog_names, _catalog_has_family, _catalog_gap_for_query, _requires_fresh_ai_interpretation, _is_reusable_blueprint_candidate, _entity_from_blueprint, _resolve_blueprint_catalog_view, _extract_explicit_row_limit, _apply_explicit_row_limit, _sanitize_intention_params, _safe_int, _month_range_from_params |
| `backend/services/query_optimizer_engine.py` | QueryOptimizer, SQLGenerator | translate_expression |
| `backend/services/query_planner.py` | QueryPlanItem, QueryPlan | _suggest_visualizacao, _find_view_by_keyword, _intention_domain, _domain_keywords, _is_registry_catalog_view, _is_registry_intention, _score_view_for_domain, _guard_primary_view_domain, _requires_daily_view, _attach_structured_execution_hints, _score_daily_view, _guard_temporal_granularity |
| `backend/services/query_response_governance.py` | QueryResponseGovernance | - |
| `backend/services/readiness.py` | - | normalized_status, dependency_component, overall_readiness, active_feature_names, migration_readiness_component |
| `backend/services/ris_service.py` | FreshnessResult, SufficiencyResult, EvidenceTrail, ConsistencyResult, ContradictionResult, BusinessContextResult, ExplainabilityResult, InsightResult, HypothesisAssumptionResult, AmbiguityResult, ReasoningGovernanceResult, RecommendationItem, ResponseQualityResult, TrustAnalyzerResult, QualitySLAResult, ResponseIntelligencePackage, RISResult, ResponseIntelligenceSuite | - |
| `backend/services/roqg_service.py` | ResponseOrchestratorQualityGate | _utc_timestamp |
| `backend/services/safe_analytical_postgresql/__init__.py` | - | - |
| `backend/services/safe_analytical_postgresql/catalog_service.py` | AnalyticalCatalogService | _calc_hash |
| `backend/services/safe_analytical_postgresql/compiler.py` | GovernedAnalyticalSQLCompiler | - |
| `backend/services/safe_analytical_postgresql/connection_guard.py` | AnalyticalConnectionGuard | - |
| `backend/services/safe_analytical_postgresql/exceptions.py` | AnalyticalError, AnalyticalCatalogError, AnalyticalCompilationError, AnalyticalSecurityViolationError, AnalyticalBudgetExceededError, AnalyticalConnectionGuardError, AnalyticalExecutionError | - |
| `backend/services/safe_analytical_postgresql/execution_service.py` | SafeAnalyticalPostgreSQLService | - |
| `backend/services/safe_analytical_postgresql/provenance_service.py` | AnalyticalProvenanceService | - |
| `backend/services/safe_analytical_postgresql/result_validator.py` | AnalyticalResultValidator | - |
| `backend/services/sales_value_breakdown.py` | SalesValueBreakdownService | - |
| `backend/services/scheduler.py` | - | run_sync_task, _scheduler_loop, start_scheduler, _restart_scheduler_after_failure, get_scheduler_status, stop_scheduler |
| `backend/services/security/enterprise_security_platform.py` | EnterpriseSecurityPlatform | - |
| `backend/services/security_and_normalization_engine.py` | SecurityValidationError, EmptyDatasetAnomalyError, SecurityValidator, ResultNormalizer | - |
| `backend/services/security_rollout_v2/__init__.py` | - | - |
| `backend/services/security_rollout_v2/authorization.py` | AuthorizationMatrixServiceV2 | - |
| `backend/services/security_rollout_v2/canary.py` | CanaryPolicyServiceV2 | - |
| `backend/services/security_rollout_v2/configuration.py` | ConfigurationReadinessServiceV2 | _control |
| `backend/services/security_rollout_v2/migration.py` | MigrationCompatibilityServiceV2 | - |
| `backend/services/security_rollout_v2/migration_lock.py` | AsyncExecuteTarget, MigrationLockUnavailable, PostgresMigrationLockV2 | - |
| `backend/services/security_rollout_v2/readiness.py` | SecurityControlRegistryV2 | _pass |
| `backend/services/security_rollout_v2/registry.py` | GovernedFeatureRegistryV2 | - |
| `backend/services/security_rollout_v2/rollback.py` | RollbackReadinessServiceV2 | _plan |
| `backend/services/security_rollout_v2/rollout.py` | GovernedRolloutPolicyV2, RolloutReadinessServiceV2 | - |
| `backend/services/security_rollout_v2/sanitization.py` | SecurityPayloadSanitizerV2 | - |
| `backend/services/security_rollout_v2/security.py` | SecurityReadinessServiceV2 | - |
| `backend/services/semantic_layer.py` | - | _normalize_alias_key, _singularize_token, _metric_key_variants, _build_metric_alias_index, _resolve_metric_by_safe_similarity, canonicalize_metric_name, get_metric_info, resolve_metric_for_view, validate_metrics_and_sources, register_custom_metric, sync_from_semantic_catalog |
| `backend/services/semantic_memory_repo.py` | - | get_semantic_memory_record, increment_memory_frequencia, create_semantic_memory_record |
| `backend/services/semantic_retrieval/__init__.py` | - | - |
| `backend/services/semantic_retrieval/cache.py` | _CacheEntry, SemanticRetrievalCache | - |
| `backend/services/semantic_retrieval/checksums.py` | - | _json_value, canonical_json, checksum_for, fingerprint_text |
| `backend/services/semantic_retrieval/clarification.py` | SemanticClarificationService | _b64 |
| `backend/services/semantic_retrieval/errors.py` | SemanticRetrievalError | semantic_error |
| `backend/services/semantic_retrieval/evaluation.py` | SemanticEvaluationService | - |
| `backend/services/semantic_retrieval/feature_flags.py` | SemanticRetrievalFeaturePolicy | - |
| `backend/services/semantic_retrieval/indexing.py` | SemanticIndexLifecycleService | utc_now, _default_entity_policies, _version_contract |
| `backend/services/semantic_retrieval/integration.py` | SemanticPipelineResolution, SemanticResolutionRuntime | apply_resolution_patch |
| `backend/services/semantic_retrieval/mentions.py` | SemanticMentionExtractor | _mention |
| `backend/services/semantic_retrieval/normalization.py` | NormalizedSemanticText | _fold_diacritics, _character_ngrams, normalize_semantic_text, token_overlap, character_similarity |
| `backend/services/semantic_retrieval/observability.py` | SemanticObservability | - |
| `backend/services/semantic_retrieval/permissions.py` | - | permission_fingerprint, access_decision, require_permission |
| `backend/services/semantic_retrieval/policies.py` | - | default_ranking_policy, default_threshold_policy |
| `backend/services/semantic_retrieval/privacy.py` | SemanticContentInspection | inspect_semantic_content |
| `backend/services/semantic_retrieval/ranking.py` | SemanticRankingEvidence, SemanticRankingEngine | - |
| `backend/services/semantic_retrieval/repository.py` | SemanticStoredCandidate, SemanticRetrievalRepository | - |
| `backend/services/semantic_retrieval/representation.py` | SemanticRepresentationProviderInfo, SemanticRepresentationProvider, DeterministicFeatureEmbeddingProvider | - |
| `backend/services/semantic_retrieval/resolution.py` | GovernedEntityResolutionService | _operation_for, resolution_context |
| `backend/services/semantic_retrieval/retrieval.py` | SemanticRetrievalService | _confidence_band, _safe_breakdown |
| `backend/services/semantic_retrieval/sources.py` | SemanticSourceRecord, SemanticSourceSnapshot, SemanticIndexSourceProvider, EnterpriseKnowledgeSemanticSourceProvider, MetricRegistrySemanticSourceProvider, SyntheticAnalyticalEntitySourceProvider | _entity_type, _document_type, _content_label, _content_description |
| `backend/services/smart_cache_materialization/__init__.py` | - | - |
| `backend/services/smart_cache_materialization/audit_service.py` | SmartCacheAuditService | - |
| `backend/services/smart_cache_materialization/eligibility_engine.py` | SmartCacheEligibilityEngine | - |
| `backend/services/smart_cache_materialization/garbage_collection_service.py` | SmartCacheGarbageCollectionService | - |
| `backend/services/smart_cache_materialization/invalidation_service.py` | SmartCacheInvalidationService | - |
| `backend/services/smart_cache_materialization/key_builder.py` | SmartCacheKeyBuilder | - |
| `backend/services/smart_cache_materialization/lookup_service.py` | SmartCacheLookupService | - |
| `backend/services/smart_cache_materialization/materialization_build_service.py` | AnalyticalExecutor, ValidationExecutor, GovernedMaterializationBuildService | - |
| `backend/services/smart_cache_materialization/materialization_publication_service.py` | MaterializationPublicationService | - |
| `backend/services/smart_cache_materialization/materialization_refresh_service.py` | MaterializationRefreshService | - |
| `backend/services/smart_cache_materialization/materialization_rollback_service.py` | MaterializationRollbackService | - |
| `backend/services/smart_cache_materialization/pipeline.py` | SmartCachePipeline | - |
| `backend/services/smart_cache_materialization/policy_service.py` | SmartCachePolicyService | - |
| `backend/services/smart_cache_materialization/repository.py` | SmartCacheRepository, MaterializationRepository | utc_now, trusted_tenant_uuid, _owner_checksum |
| `backend/services/smart_cache_materialization/single_flight.py` | CacheSingleFlightService | - |
| `backend/services/smart_cache_materialization/statistics_service.py` | SmartCacheStatisticsService | - |
| `backend/services/smart_cache_materialization/write_service.py` | SmartCacheWriteService | - |
| `backend/services/supervised_feedback/__init__.py` | - | - |
| `backend/services/supervised_feedback/cache.py` | _ManifestEntry, FeedbackMetadataCache | - |
| `backend/services/supervised_feedback/checksums.py` | - | _canonical, canonical_json, checksum, content_sha256, hash_idempotency_key |
| `backend/services/supervised_feedback/errors.py` | GovernedFeedbackError | _error |
| `backend/services/supervised_feedback/imports.py` | GovernedImportDryRunValidator | _contains_forbidden_key |
| `backend/services/supervised_feedback/lifecycle.py` | - | require_transition, require_candidate_transition |
| `backend/services/supervised_feedback/observability.py` | FeedbackCounters | - |
| `backend/services/supervised_feedback/permissions.py` | - | access_decision, require_permission |
| `backend/services/supervised_feedback/redaction.py` | RedactionResult, FeedbackRedactionEngine | - |
| `backend/services/supervised_feedback/repository.py` | GovernedFeedbackRepository | utc_now |
| `backend/services/supervised_feedback/service.py` | GovernedFeedbackService | utc_now |
| `backend/services/supervised_feedback/triage.py` | FeedbackTriageEngine | - |
| `backend/services/svr_migration.py` | SVRMigrationEngine | - |
| `backend/services/svr_service.py` | SemanticVersionRegistryService | - |
| `backend/services/sync_service.py` | - | _now_iso, _set_sync_progress, get_sync_progress, _close_oracle_resource, _get_sync_config, sync_tenant_database |
| `backend/services/temporal/__init__.py` | - | - |
| `backend/services/temporal/clock.py` | TemporalClock, SystemTemporalClock | - |
| `backend/services/temporal/context.py` | - | build_temporal_context |
| `backend/services/temporal/feature_flags.py` | TemporalFeaturePolicy, TemporalNormalizationGateway | - |
| `backend/services/temporal/legacy_adapter.py` | PluralTemporalResultError, UnresolvedTemporalResultError, LegacyDateBinds | normalize_legacy_date_range, singular_range_from_result, legacy_binds_from_result, context_from_legacy_anchor, envelope_plural_for_deprecated_caller |
| `backend/services/temporal/lexicon_pt_br.py` | BuiltinPtBrLexiconProvider | merged_aliases |
| `backend/services/temporal/models.py` | CurrentPeriodMode, DefaultYearPolicy, TwoDigitYearPolicy, FiscalYearLabelMode, TemporalRelation, EffectiveTemporalScopeKind, TemporalSemanticType, TemporalContextSource, TemporalLexiconProvider, StrictTemporalModel, TemporalContext, TemporalTextSpan, ResolvedTemporalItem, TemporalComparisonGroup, TemporalNormalizationResult, EffectiveTemporalScope | - |
| `backend/services/temporal/normalizer.py` | TemporalInputError, TemporalNormalizer | default_temporal_context, _safe_original_slice, _stable_deduplicate, _aggregate_confidence, _low_confidence, _requests_equivalent_previous_period, _shift_year_clamped |
| `backend/services/temporal/parser.py` | ParsedTemporalExpression, TemporalParseResult | parse_temporal_expressions, _ordinal_number, _propagate_shared_year, _detect_relation |
| `backend/services/temporal/resolver.py` | TemporalResolutionError, TemporalAmbiguityError, FutureTemporalPeriodError | resolve_expression, _resolve_year, _resolve_relative, _resolve_rolling, _resolve_accumulation, _resolve_fiscal, _month_end, _shift_month, _shift_month_clamped |
| `backend/services/temporal/rule_registry.py` | TemporalRule | ensure_known_rule |
| `backend/services/temporal/timezone_support.py` | InvalidTemporalTimezone | resolve_timezone |
| `backend/services/temporal/tokenizer.py` | TemporalToken | normalize_temporal_text, tokenize_temporal_text |
| `backend/services/user_analytical_profile/__init__.py` | - | - |
| `backend/services/user_analytical_profile/application.py` | UserPreferenceApplicationEngine | stable_fingerprint, _confidence, _consent_status |
| `backend/services/user_analytical_profile/cache.py` | _Entry, UserProfileCache | - |
| `backend/services/user_analytical_profile/errors.py` | UserProfileError | _error |
| `backend/services/user_analytical_profile/legacy_adapter.py` | LegacyPreferenceAdaptation, LegacyUserPreferenceAdapter | - |
| `backend/services/user_analytical_profile/observability.py` | UserProfileCounters | - |
| `backend/services/user_analytical_profile/permissions.py` | - | access_decision, require_permission |
| `backend/services/user_analytical_profile/policies.py` | UserProfileFieldPolicy | _policy, classify_preference, policy_for_item |
| `backend/services/user_analytical_profile/repository.py` | UserAnalyticalProfileRepository | - |
| `backend/services/user_analytical_profile/retention.py` | UserProfileRetentionPolicy, UserProfileRetentionService | - |
| `backend/services/user_analytical_profile/runtime.py` | UserProfileShadowMetadata, UserAnalyticalProfileRuntime | - |
| `backend/services/user_analytical_profile/service.py` | UserAnalyticalProfileService | utc_now, canonical_checksum, _assert_safe, _profile_checksum, _item_checksum |
| `backend/services/validation_provenance/__init__.py` | - | - |
| `backend/services/validation_provenance/audit_service.py` | ValidationAuditService | - |
| `backend/services/validation_provenance/certification_service.py` | CertificationService | - |
| `backend/services/validation_provenance/claim_service.py` | AnalyticalClaimValidationService | - |
| `backend/services/validation_provenance/fact_service.py` | AnalyticalFactService | - |
| `backend/services/validation_provenance/pipeline.py` | GovernedValidationPipeline | - |
| `backend/services/validation_provenance/policy_service.py` | ValidationPolicyService | - |
| `backend/services/validation_provenance/provenance_service.py` | ProvenanceGraphService | - |
| `backend/services/validation_provenance/public_provenance_service.py` | PublicProvenanceService | - |
| `backend/services/validation_provenance/repository.py` | ValidationProvenanceRepository | - |
| `backend/services/validation_provenance/validators/__init__.py` | - | - |
| `backend/services/validation_provenance/validators/base.py` | GovernedValidator | - |
| `backend/services/validation_provenance/validators/completeness_validators.py` | CompletenessValidator, TruncationValidator | - |
| `backend/services/validation_provenance/validators/contract_validators.py` | ContractValidator, ResultShapeValidator, DuplicateKeyValidator | - |
| `backend/services/validation_provenance/validators/fact_claim_validators.py` | FactReferenceValidator, ClaimValueConsistencyValidator | - |
| `backend/services/validation_provenance/validators/numeric_validators.py` | DecimalValidator, NumericFiniteValueValidator, ComparisonOperandsValidator, ComparisonDeltaValidator, ComparisonPercentageValidator | - |
| `backend/services/validation_provenance/validators/provenance_validators.py` | ProvenanceGraphValidator | - |
| `backend/services/validation_provenance/validators/registry.py` | - | get_validator |
| `backend/services/validation_provenance/validators/security_validators.py` | TenantIsolationValidator, AuthorizationValidator, PresentationSafetyValidator | - |
| `backend/services/validation_provenance/validators/semantic_validators.py` | AuthorityReferenceValidator, SemanticCanonicalReferenceValidator, MetricFingerprintValidator, MetricUnitValidator | - |
| `backend/services/validation_provenance/validators/temporal_validators.py` | TemporalPeriodValidator, SourceFreshnessValidator | - |
| `backend/services/validation_provenance/validators/tool_orchestration_validators.py` | ToolResultChecksumValidator, OrchestrationRunValidator | - |
| `backend/services/work_queue_v2/backpressure.py` | WorkQueueBackpressureServiceV2 | - |
| `backend/services/work_queue_v2/concurrency.py` | ConcurrencyPermitV2, GovernedConcurrencyControllerV2 | - |
| `backend/services/work_queue_v2/lease.py` | WorkQueueLeaseServiceV2, WorkQueueLeaseReclaimerV2 | - |
| `backend/services/work_queue_v2/performance.py` | PerformanceCertificationServiceV2 | - |
| `backend/services/work_queue_v2/queue_service.py` | WorkQueueServiceV2 | - |
| `backend/services/work_queue_v2/registry.py` | JobTypeSpecV2, GovernedJobRegistryV2 | - |
| `backend/services/work_queue_v2/single_flight.py` | WorkQueueSingleFlightServiceV2 | - |
| `backend/services/work_queue_v2/worker.py` | WorkQueueWorkerV2 | - |

## frontend/app

- `frontend/app/admin/evaluations/page.tsx`
- `frontend/app/admin/observability/page.tsx`
- `frontend/app/api/auth/clear-session/route.ts`
- `frontend/app/auth/first-access/page.tsx`
- `frontend/app/dashboard/admin/catalog/page.tsx`
- `frontend/app/dashboard/admin/feedback/page.tsx`
- `frontend/app/dashboard/admin/orchestration/page.tsx`
- `frontend/app/dashboard/admin/semantic/page.tsx`
- `frontend/app/dashboard/admin/settings/page.tsx`
- `frontend/app/dashboard/admin/tools/page.tsx`
- `frontend/app/dashboard/admin/users/page.tsx`
- `frontend/app/dashboard/admin/validation/page.tsx`
- `frontend/app/dashboard/feedback/page.tsx`
- `frontend/app/dashboard/inspector/page.tsx`
- `frontend/app/dashboard/knowledge/page.tsx`
- `frontend/app/dashboard/page.tsx`
- `frontend/app/dashboard/settings/profile/page.tsx`
- `frontend/app/dashboard/studio/page.tsx`
- `frontend/app/dashboard/svr/page.tsx`
- `frontend/app/dashboard/v2/[dashboardId]/edit/page.tsx`
- `frontend/app/dashboard/v2/[dashboardId]/history/page.tsx`
- `frontend/app/dashboard/v2/[dashboardId]/page.tsx`
- `frontend/app/dashboard/v2/error.tsx`
- `frontend/app/dashboard/v2/layout.tsx`
- `frontend/app/dashboard/v2/loading.tsx`
- `frontend/app/dashboard/v2/new/page.tsx`
- `frontend/app/dashboard/v2/page.tsx`
- `frontend/app/globals.css`
- `frontend/app/healthz/route.ts`
- `frontend/app/insights/page.tsx`
- `frontend/app/layout.tsx`
- `frontend/app/login/page.tsx`
- `frontend/app/page.tsx`

## frontend/components

- `frontend/components/cache/CacheInspector.tsx`
- `frontend/components/cache/MaterializationInspector.tsx`
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
- `frontend/components/chat/FeedbackControls.tsx`
- `frontend/components/chat/InlineDashboardRuntime.tsx`
- `frontend/components/comparison/ComparisonChart.tsx`
- `frontend/components/comparison/comparisonExport.ts`
- `frontend/components/comparison/comparisonFeatureFlags.ts`
- `frontend/components/comparison/comparisonFormatters.ts`
- `frontend/components/comparison/comparisonPresentationAdapter.ts`
- `frontend/components/comparison/comparisonPresentationTypes.ts`
- `frontend/components/comparison/ComparisonRenderer.tsx`
- `frontend/components/comparison/comparisonTelemetry.ts`
- `frontend/components/comparison/index.ts`
- `frontend/components/component-library/controls/AlertBanner.tsx`
- `frontend/components/component-library/index.ts`
- `frontend/components/component-library/kpis/KpiCard.tsx`
- `frontend/components/component-library/status/StatusComponents.tsx`
- `frontend/components/component-library/tables/RankingTable.tsx`
- `frontend/components/dashboard-ai/DashboardAiCreationWizard.tsx`
- `frontend/components/dashboard-runtime/DashboardRuntimeEngine.tsx`
- `frontend/components/dashboard-runtime/GridEngine.tsx`
- `frontend/components/dashboard-runtime/RuntimeRenderer.tsx`
- `frontend/components/dashboard-runtime/TrustCenterPanel.tsx`
- `frontend/components/dashboard-v2/DashboardEditorPage.tsx`
- `frontend/components/dashboard-v2/DashboardHistoryPage.tsx`
- `frontend/components/dashboard-v2/DashboardLibrary.tsx`
- `frontend/components/dashboard-v2/DashboardRuntimePage.tsx`
- `frontend/components/dashboard-v2/DashboardSideChatPanel.tsx`
- `frontend/components/dashboard-v2/DashboardV2Shell.tsx`
- `frontend/components/dashboard-v2/DashboardWidgetRenderer.tsx`
- `frontend/components/DynamicRenderer.tsx`
- `frontend/components/insights/PostSyncInsightCard.tsx`
- `frontend/components/insights/PostSyncInsightLibrary.tsx`
- `frontend/components/interaction-engine/CrossFilterManager.tsx`
- `frontend/components/interaction-engine/FullscreenManager.tsx`
- `frontend/components/observability/ErrorBudgetCard.tsx`
- `frontend/components/observability/EvaluationRunDetail.tsx`
- `frontend/components/observability/EvaluationRunList.tsx`
- `frontend/components/observability/EvaluationSuiteList.tsx`
- `frontend/components/observability/ObservabilityOverview.tsx`
- `frontend/components/observability/OperationalMetricSummary.tsx`
- `frontend/components/observability/RegressionPanel.tsx`
- `frontend/components/observability/SloStatusTable.tsx`
- `frontend/components/observability/TraceSummaryDrawer.tsx`
- `frontend/components/orchestration/OrchestrationInspector.tsx`
- `frontend/components/performance/VirtualizationEngine.tsx`
- `frontend/components/provenance/PublicProvenancePanel.tsx`
- `frontend/components/Sidebar.tsx`
- `frontend/components/ThemeToggle.tsx`
- `frontend/components/ui/Badge.tsx`
- `frontend/components/ui/ErrorBoundary.tsx`
- `frontend/components/ui/GlassCard.tsx`
- `frontend/components/ui/SkeletonGrid.tsx`
- `frontend/components/ui/TooltipHelp.tsx`
- `frontend/components/validation/ValidationInspector.tsx`

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

- `frontend/lib/analyticalContractAdapter.ts`
- `frontend/lib/authSession.ts`
- `frontend/lib/dashboard-ai/client.ts`
- `frontend/lib/dashboard-ai/config.ts`
- `frontend/lib/dashboard-ai/serverConfig.ts`
- `frontend/lib/dashboard-v2/actionValidator.ts`
- `frontend/lib/dashboard-v2/client.ts`
- `frontend/lib/dashboard-v2/config.ts`
- `frontend/lib/dashboard-v2/serverConfig.ts`
- `frontend/lib/dashboard-v2/telemetry.ts`
- `frontend/lib/dashboard-v2/visualUpdateInterceptor.ts`
- `frontend/lib/dashboardRuntimeAdapter.ts`
- `frontend/lib/exportUtils.ts`
- `frontend/lib/insights/client.ts`
- `frontend/lib/insights/config.ts`
- `frontend/lib/observability/api.ts`
- `frontend/lib/observability/config.ts`
- `frontend/lib/textEncoding.ts`
- `frontend/lib/utils.ts`

## frontend/types

- `frontend/types/dashboard-runtime.ts`
- `frontend/types/dashboard_ai_assistance_v2.ts`
- `frontend/types/dashboard_backend_v2.ts`
- `frontend/types/dashboard_blueprint_v2.ts`
- `frontend/types/dashboard_ui_sidechat_v2.ts`
- `frontend/types/enterpriseKnowledge.ts`
- `frontend/types/lumina.ts`
- `frontend/types/observability_v2.ts`
- `frontend/types/post_sync_insights_v2.ts`
- `frontend/types/semanticRetrieval.ts`
- `frontend/types/smart_cache_materialization.ts`
- `frontend/types/supervisedFeedback.ts`
- `frontend/types/userAnalyticalProfile.ts`
- `frontend/types/validation_provenance.ts`

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
