"""Static registry of governed deterministic evaluation suites in LuminaAI."""
from __future__ import annotations

from contracts.observability_v2 import EvaluationSuiteKindV2, EvaluationSuiteV2

_EVALUATION_SUITES: tuple[EvaluationSuiteV2, ...] = (
    EvaluationSuiteV2(
        suite_id="suite_temporal",
        kind=EvaluationSuiteKindV2.TEMPORAL_NORMALIZATION,
        title="Temporal Normalization Suite",
        description="Validates deterministic date window parsing and relative date resolution",
        case_count=5,
        deterministic_only=True,
    ),
    EvaluationSuiteV2(
        suite_id="suite_comparison_planner",
        kind=EvaluationSuiteKindV2.COMPARISON_PLANNER,
        title="Comparison Planner Suite",
        description="Validates multi-operand period and entity comparison query planning",
        case_count=5,
        deterministic_only=True,
    ),
    EvaluationSuiteV2(
        suite_id="suite_comparison_executor",
        kind=EvaluationSuiteKindV2.COMPARISON_EXECUTOR,
        title="Comparison Executor Suite",
        description="Validates Decimal math, delta, percentage, and alignment in SQL compilation",
        case_count=5,
        deterministic_only=True,
    ),
    EvaluationSuiteV2(
        suite_id="suite_context_resolution",
        kind=EvaluationSuiteKindV2.CONTEXT_RESOLUTION,
        title="Context Resolution Engine Suite",
        description="Validates conversational inheritance, branch continuation, and SemanticPatch rules",
        case_count=5,
        deterministic_only=True,
    ),
    EvaluationSuiteV2(
        suite_id="suite_enterprise_knowledge",
        kind=EvaluationSuiteKindV2.ENTERPRISE_KNOWLEDGE,
        title="Enterprise Knowledge Base Suite",
        description="Validates published business terms, metric bindings, and governance rules",
        case_count=5,
        deterministic_only=True,
    ),
    EvaluationSuiteV2(
        suite_id="suite_semantic_retrieval",
        kind=EvaluationSuiteKindV2.SEMANTIC_RETRIEVAL,
        title="Semantic Retrieval & Entity Resolution Suite",
        description="Validates candidate ranking, entity mention resolution, and ambiguity detection",
        case_count=5,
        deterministic_only=True,
    ),
    EvaluationSuiteV2(
        suite_id="suite_ai_tool_registry",
        kind=EvaluationSuiteKindV2.AI_TOOL_REGISTRY,
        title="AI Tool Registry Suite",
        description="Validates allowlisted tool schemas, parameter validation, and execution guards",
        case_count=5,
        deterministic_only=True,
    ),
    EvaluationSuiteV2(
        suite_id="suite_safe_postgresql",
        kind=EvaluationSuiteKindV2.SAFE_ANALYTICAL_POSTGRESQL,
        title="Safe Analytical PostgreSQL Source Suite",
        description="Validates tenant isolation, bind parameters, and analytical SQL generation",
        case_count=5,
        deterministic_only=True,
    ),
    EvaluationSuiteV2(
        suite_id="suite_ai_orchestration",
        kind=EvaluationSuiteKindV2.AI_ORCHESTRATION,
        title="AI Orchestration & Token Budgeting Suite",
        description="Validates state machine transitions, max tokens, and deterministic fake provider",
        case_count=5,
        deterministic_only=True,
    ),
    EvaluationSuiteV2(
        suite_id="suite_validation_provenance",
        kind=EvaluationSuiteKindV2.VALIDATION_PROVENANCE,
        title="Validation & Provenance Engine Suite",
        description="Validates claims, facts, mathematical integrity, and provenance certification",
        case_count=5,
        deterministic_only=True,
    ),
    EvaluationSuiteV2(
        suite_id="suite_smart_cache",
        kind=EvaluationSuiteKindV2.SMART_CACHE,
        title="Smart Cache & Materialization Suite",
        description="Validates cache key generation, TTL, corruption protection, and materialization",
        case_count=5,
        deterministic_only=True,
    ),
    EvaluationSuiteV2(
        suite_id="suite_dashboard_blueprint",
        kind=EvaluationSuiteKindV2.DASHBOARD_BLUEPRINT,
        title="Dashboard Blueprint V2 Suite",
        description="Validates V2 blueprint schema parsing, widget unions, and layout serialization",
        case_count=5,
        deterministic_only=True,
    ),
    EvaluationSuiteV2(
        suite_id="suite_dashboard_backend",
        kind=EvaluationSuiteKindV2.DASHBOARD_BACKEND,
        title="Governed Dashboard Backend Suite",
        description="Validates revisions, CAS conflicts, publications, rollbacks, and collaborator RBAC",
        case_count=5,
        deterministic_only=True,
    ),
    EvaluationSuiteV2(
        suite_id="suite_dashboard_ui",
        kind=EvaluationSuiteKindV2.DASHBOARD_UI,
        title="Dashboard UI & Side Chat Suite",
        description="Validates presentation adapter, visual patches, and side-chat lifecycle",
        case_count=5,
        deterministic_only=True,
    ),
    EvaluationSuiteV2(
        suite_id="suite_dashboard_ai",
        kind=EvaluationSuiteKindV2.DASHBOARD_AI,
        title="AI Dashboard Assistance Suite",
        description="Validates visual proposals, clarification questions, and human approval steps",
        case_count=5,
        deterministic_only=True,
    ),
    EvaluationSuiteV2(
        suite_id="suite_post_sync_insights",
        kind=EvaluationSuiteKindV2.POST_SYNC_INSIGHTS,
        title="Post-Sync Insights V2 Suite",
        description="Validates 10 static detectors, evidence certification, and outbox idempotency",
        case_count=5,
        deterministic_only=True,
    ),
    EvaluationSuiteV2(
        suite_id="suite_tenant_isolation",
        kind=EvaluationSuiteKindV2.TENANT_ISOLATION,
        title="Cross-Tenant Security Suite",
        description="Validates fail-closed tenant boundary enforcement across all V2 subsystems",
        case_count=5,
        deterministic_only=True,
    ),
    EvaluationSuiteV2(
        suite_id="suite_security",
        kind=EvaluationSuiteKindV2.SECURITY,
        title="Security & Vulnerability Suite",
        description="Validates prompt injection blocks, secret redaction, and unsafe action prevention",
        case_count=5,
        deterministic_only=True,
    ),
    EvaluationSuiteV2(
        suite_id="suite_reproducibility",
        kind=EvaluationSuiteKindV2.REPRODUCIBILITY,
        title="Deterministic Reproducibility Suite",
        description="Validates logical OpenAPI, schema digests, and golden result reproducibility",
        case_count=5,
        deterministic_only=True,
    ),
    EvaluationSuiteV2(suite_id="suite_authorization_security", kind=EvaluationSuiteKindV2.AUTHORIZATION_SECURITY, title="Authorization Security Suite", description="Validates role and capability decisions from server authority", case_count=2, deterministic_only=True),
    EvaluationSuiteV2(suite_id="suite_tenant_isolation_security", kind=EvaluationSuiteKindV2.TENANT_ISOLATION_SECURITY, title="Tenant Isolation Security Suite", description="Validates concealment and zero cross-tenant effects", case_count=2, deterministic_only=True),
    EvaluationSuiteV2(suite_id="suite_api_input_security", kind=EvaluationSuiteKindV2.API_INPUT_SECURITY, title="API Input Security Suite", description="Validates bounded injection and path traversal inputs", case_count=2, deterministic_only=True),
    EvaluationSuiteV2(suite_id="suite_secret_leakage_security", kind=EvaluationSuiteKindV2.SECRET_LEAKAGE_SECURITY, title="Secret Leakage Security Suite", description="Validates structured redaction of secrets and SQL", case_count=2, deterministic_only=True),
    EvaluationSuiteV2(suite_id="suite_error_sanitization_security", kind=EvaluationSuiteKindV2.ERROR_SANITIZATION_SECURITY, title="Error Sanitization Security Suite", description="Validates non-disclosing public errors", case_count=2, deterministic_only=True),
    EvaluationSuiteV2(suite_id="suite_rollout_guard_security", kind=EvaluationSuiteKindV2.ROLLOUT_GUARD_SECURITY, title="Rollout Guard Security Suite", description="Validates critical gates and kill-switch precedence", case_count=2, deterministic_only=True),
    EvaluationSuiteV2(suite_id="suite_migration_compatibility_security", kind=EvaluationSuiteKindV2.MIGRATION_COMPATIBILITY_SECURITY, title="Migration Compatibility Security Suite", description="Validates schema windows, drift, and future-version blocks", case_count=2, deterministic_only=True),
)


class EvaluationSuiteRegistryV2:
    @staticmethod
    def list_suites() -> tuple[EvaluationSuiteV2, ...]:
        return _EVALUATION_SUITES

    @staticmethod
    def get_suite(kind: EvaluationSuiteKindV2) -> EvaluationSuiteV2 | None:
        return next((s for s in _EVALUATION_SUITES if s.kind == kind), None)
