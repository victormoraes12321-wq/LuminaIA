"""Synthetic versioned evaluation test cases and fixtures for governed suites."""
from __future__ import annotations

import hashlib
from contracts.observability_v2 import (
    EvaluationCaseV2,
    EvaluationExpectationV2,
    EvaluationOutcomeV2,
    EvaluationSuiteKindV2,
)

_CORPUS_VERSION = "2026.08.01"


def _make_case(
    case_id: str,
    suite: EvaluationSuiteKindV2,
    title: str,
    fixture_ref: str,
    expected_outcome: EvaluationOutcomeV2 = EvaluationOutcomeV2.PASS,
) -> EvaluationCaseV2:
    ck = hashlib.sha256(f"{case_id}:{suite.value}:{expected_outcome.value}:{_CORPUS_VERSION}".encode()).hexdigest()
    exp = EvaluationExpectationV2(
        expected_outcome=expected_outcome,
        checksum=ck,
    )
    return EvaluationCaseV2(
        case_id=case_id,
        suite=suite,
        version=_CORPUS_VERSION,
        title=title,
        input_fixture_reference=fixture_ref,
        expectation=exp,
        severity="HIGH",
        deterministic=True,
    )


SYNTHETIC_EVALUATION_CORPUS: tuple[EvaluationCaseV2, ...] = (
    # Temporal Normalization
    _make_case("tmp_01", EvaluationSuiteKindV2.TEMPORAL_NORMALIZATION, "Relative Month Resolution", "fix_tmp_01"),
    _make_case("tmp_02", EvaluationSuiteKindV2.TEMPORAL_NORMALIZATION, "Explicit Date Range ISO", "fix_tmp_02"),

    # Comparison Planner
    _make_case("cmp_pln_01", EvaluationSuiteKindV2.COMPARISON_PLANNER, "Period Comparison Plan", "fix_cmp_01"),
    _make_case("cmp_pln_02", EvaluationSuiteKindV2.COMPARISON_PLANNER, "Multi-Entity Comparison Plan", "fix_cmp_02"),

    # Comparison Executor
    _make_case("cmp_exe_01", EvaluationSuiteKindV2.COMPARISON_EXECUTOR, "Decimal Delta Calculation", "fix_cmpe_01"),
    _make_case("cmp_exe_02", EvaluationSuiteKindV2.COMPARISON_EXECUTOR, "Zero Denominator Protection", "fix_cmpe_02"),

    # Context Resolution
    _make_case("ctx_01", EvaluationSuiteKindV2.CONTEXT_RESOLUTION, "Inherit Metric and Time Window", "fix_ctx_01"),
    _make_case("ctx_02", EvaluationSuiteKindV2.CONTEXT_RESOLUTION, "Explicit Parameter Precedence", "fix_ctx_02"),

    # Enterprise Knowledge
    _make_case("ek_01", EvaluationSuiteKindV2.ENTERPRISE_KNOWLEDGE, "Published Term Lookup", "fix_ek_01"),
    _make_case("ek_02", EvaluationSuiteKindV2.ENTERPRISE_KNOWLEDGE, "Draft Term Resolution Blocked", "fix_ek_02"),

    # Semantic Retrieval
    _make_case("sem_01", EvaluationSuiteKindV2.SEMANTIC_RETRIEVAL, "Exact Canonical Key Ranking", "fix_sem_01"),
    _make_case("sem_02", EvaluationSuiteKindV2.SEMANTIC_RETRIEVAL, "Ambiguity Detection & Clarification", "fix_sem_02"),

    # AI Tool Registry
    _make_case("tool_01", EvaluationSuiteKindV2.AI_TOOL_REGISTRY, "Allowlisted Tool Execution", "fix_tool_01"),
    _make_case("tool_02", EvaluationSuiteKindV2.AI_TOOL_REGISTRY, "Forbidden Tool Blocked", "fix_tool_02"),

    # Safe PostgreSQL
    _make_case("sql_01", EvaluationSuiteKindV2.SAFE_ANALYTICAL_POSTGRESQL, "Tenant Bound Parameter Query", "fix_sql_01"),
    _make_case("sql_02", EvaluationSuiteKindV2.SAFE_ANALYTICAL_POSTGRESQL, "Raw SQL Injection Prevention", "fix_sql_02"),

    # AI Orchestration
    _make_case("ai_orc_01", EvaluationSuiteKindV2.AI_ORCHESTRATION, "State Machine Normal Execution", "fix_aio_01"),
    _make_case("ai_orc_02", EvaluationSuiteKindV2.AI_ORCHESTRATION, "Token Budget Max Exceeded", "fix_aio_02"),

    # Validation Provenance
    _make_case("val_01", EvaluationSuiteKindV2.VALIDATION_PROVENANCE, "Certified Fact Provenance", "fix_val_01"),
    _make_case("val_02", EvaluationSuiteKindV2.VALIDATION_PROVENANCE, "Uncertified Value Rejection", "fix_val_02"),

    # Smart Cache
    _make_case("cache_01", EvaluationSuiteKindV2.SMART_CACHE, "Cache Hit on Identical Fingerprint", "fix_cch_01"),
    _make_case("cache_02", EvaluationSuiteKindV2.SMART_CACHE, "Stale Cache Rejection", "fix_cch_02"),

    # Dashboard Blueprint
    _make_case("bp_01", EvaluationSuiteKindV2.DASHBOARD_BLUEPRINT, "Valid Blueprint V2 Parsing", "fix_bp_01"),
    _make_case("bp_02", EvaluationSuiteKindV2.DASHBOARD_BLUEPRINT, "Invalid Widget Union Rejection", "fix_bp_02"),

    # Dashboard Backend
    _make_case("dash_be_01", EvaluationSuiteKindV2.DASHBOARD_BACKEND, "CAS Conflict Lock Guard", "fix_dbe_01"),
    _make_case("dash_be_02", EvaluationSuiteKindV2.DASHBOARD_BACKEND, "Collaborator RBAC Protection", "fix_dbe_02"),

    # Dashboard UI
    _make_case("dash_ui_01", EvaluationSuiteKindV2.DASHBOARD_UI, "Visual Patch Application", "fix_dui_01"),
    _make_case("dash_ui_02", EvaluationSuiteKindV2.DASHBOARD_UI, "Side Chat Context Preservation", "fix_dui_02"),

    # Dashboard AI
    _make_case("dash_ai_01", EvaluationSuiteKindV2.DASHBOARD_AI, "Valid Proposal Preview Generation", "fix_dai_01"),
    _make_case("dash_ai_02", EvaluationSuiteKindV2.DASHBOARD_AI, "Unsafe Mutation Blocked", "fix_dai_02"),

    # Post-Sync Insights
    _make_case("psi_01", EvaluationSuiteKindV2.POST_SYNC_INSIGHTS, "Robust Anomaly Detection", "fix_psi_01"),
    _make_case("psi_02", EvaluationSuiteKindV2.POST_SYNC_INSIGHTS, "Outbox Event Idempotency", "fix_psi_02"),

    # Tenant Isolation
    _make_case("iso_01", EvaluationSuiteKindV2.TENANT_ISOLATION, "Cross-Tenant Query Rejection", "fix_iso_01"),
    _make_case("iso_02", EvaluationSuiteKindV2.TENANT_ISOLATION, "Cross-Tenant Memory Access Blocked", "fix_iso_02"),

    # Security
    _make_case("sec_01", EvaluationSuiteKindV2.SECURITY, "Prompt Injection Attack Blocked", "fix_sec_01"),
    _make_case("sec_02", EvaluationSuiteKindV2.SECURITY, "Secret Redaction in Telemetry", "fix_sec_02"),

    # Reproducibility
    _make_case("rep_01", EvaluationSuiteKindV2.REPRODUCIBILITY, "OpenAPI Schema Digest Invariance", "fix_rep_01"),
    _make_case("rep_02", EvaluationSuiteKindV2.REPRODUCIBILITY, "Golden Export Hash Consistency", "fix_rep_02"),
    _make_case("auth_sec_01", EvaluationSuiteKindV2.AUTHORIZATION_SECURITY, "Forged Role Is Not Authority", "fix_auth_sec_01"),
    _make_case("auth_sec_02", EvaluationSuiteKindV2.AUTHORIZATION_SECURITY, "Unknown Capability Denied", "fix_auth_sec_02"),
    _make_case("tenant_sec_01", EvaluationSuiteKindV2.TENANT_ISOLATION_SECURITY, "Foreign Resource Concealed", "fix_tenant_sec_01"),
    _make_case("tenant_sec_02", EvaluationSuiteKindV2.TENANT_ISOLATION_SECURITY, "Foreign Mutation Has Zero Effect", "fix_tenant_sec_02"),
    _make_case("input_sec_01", EvaluationSuiteKindV2.API_INPUT_SECURITY, "SQL Injection Input Inert", "fix_input_sec_01"),
    _make_case("input_sec_02", EvaluationSuiteKindV2.API_INPUT_SECURITY, "Path Traversal Input Rejected", "fix_input_sec_02"),
    _make_case("secret_sec_01", EvaluationSuiteKindV2.SECRET_LEAKAGE_SECURITY, "Bearer Secret Redacted", "fix_secret_sec_01"),
    _make_case("secret_sec_02", EvaluationSuiteKindV2.SECRET_LEAKAGE_SECURITY, "Raw SQL Redacted", "fix_secret_sec_02"),
    _make_case("error_sec_01", EvaluationSuiteKindV2.ERROR_SANITIZATION_SECURITY, "Traceback Not Serialized", "fix_error_sec_01"),
    _make_case("error_sec_02", EvaluationSuiteKindV2.ERROR_SANITIZATION_SECURITY, "Credential Error Redacted", "fix_error_sec_02"),
    _make_case("rollout_sec_01", EvaluationSuiteKindV2.ROLLOUT_GUARD_SECURITY, "Global Kill Switch Precedes All Gates", "fix_rollout_sec_01"),
    _make_case("rollout_sec_02", EvaluationSuiteKindV2.ROLLOUT_GUARD_SECURITY, "Critical Security Failure Rolls Back", "fix_rollout_sec_02"),
    _make_case("migration_sec_01", EvaluationSuiteKindV2.MIGRATION_COMPATIBILITY_SECURITY, "Future Schema Blocked", "fix_migration_sec_01"),
    _make_case("migration_sec_02", EvaluationSuiteKindV2.MIGRATION_COMPATIBILITY_SECURITY, "Critical Drift Blocked", "fix_migration_sec_02"),
)


class EvaluationCorpusServiceV2:
    @staticmethod
    def get_cases_for_suite(suite: EvaluationSuiteKindV2) -> tuple[EvaluationCaseV2, ...]:
        return tuple(c for c in SYNTHETIC_EVALUATION_CORPUS if c.suite == suite)

    @staticmethod
    def get_all_cases() -> tuple[EvaluationCaseV2, ...]:
        return SYNTHETIC_EVALUATION_CORPUS
