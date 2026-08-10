"""Strict Pydantic v2 models for V2 Observability, Operational Metrics, SLOs, and Evaluations."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Sequence
from pydantic import BaseModel, ConfigDict, Field

from contracts.observability_v2.enums import (
    EvaluationOutcomeV2,
    EvaluationSuiteKindV2,
    FeatureModeV2,
    OperationalEventTypeV2,
    OperationalMetricTypeV2,
    RegressionTypeV2,
    SloStatusV2,
    SpanCategoryV2,
    SpanStatusV2,
    TelemetryClassificationV2,
)


class ObservabilityContextV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    contract_version: str = Field(default="lumina.observability-metrics-evaluations/1.0", min_length=1, max_length=64)
    request_id: str = Field(..., min_length=1, max_length=128)
    trace_id: str = Field(..., min_length=1, max_length=128)
    root_span_id: str = Field(..., min_length=1, max_length=128)
    tenant_id: str | None = Field(default=None, max_length=128)
    user_id: str | None = Field(default=None, max_length=128)
    route_template: str = Field(..., max_length=256)
    method: str = Field(..., max_length=16)
    started_at: datetime = Field(...)


class CorrelationContextV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    request_id: str = Field(..., min_length=1, max_length=128)
    trace_id: str = Field(..., min_length=1, max_length=128)
    span_id: str = Field(..., min_length=1, max_length=128)
    external_correlation_reference: str | None = Field(default=None, max_length=128)


class TraceContextV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    trace_id: str = Field(..., min_length=1, max_length=128)
    root_span_id: str = Field(..., min_length=1, max_length=128)
    active_span_id: str = Field(..., min_length=1, max_length=128)



class SpanSummaryV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    span_id: str = Field(..., min_length=1, max_length=128)
    parent_span_id: str | None = Field(default=None, max_length=128)
    name: str = Field(..., min_length=1, max_length=128)
    category: SpanCategoryV2 = Field(...)
    status: SpanStatusV2 = Field(...)
    start_time: datetime = Field(...)
    duration_ms: Decimal = Field(..., ge=Decimal("0.0"))
    sanitized_attributes: tuple[tuple[str, str], ...] = Field(default=())
    error_class: str | None = Field(default=None, max_length=128)


class TraceSummaryV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    trace_id: str = Field(..., min_length=1, max_length=128)
    root_span_id: str = Field(..., min_length=1, max_length=128)
    tenant_id: str | None = Field(default=None, max_length=128)
    route_template: str = Field(..., max_length=256)
    started_at: datetime = Field(...)
    total_duration_ms: Decimal = Field(..., ge=Decimal("0.0"))
    status: SpanStatusV2 = Field(...)
    span_count: int = Field(..., ge=1)
    spans: tuple[SpanSummaryV2, ...] = Field(default=())


class OperationalEventV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    event_id: str = Field(..., min_length=1, max_length=128)
    event_type: OperationalEventTypeV2 = Field(...)
    classification: TelemetryClassificationV2 = Field(...)
    trace_id: str = Field(..., min_length=1, max_length=128)
    span_id: str = Field(..., min_length=1, max_length=128)
    timestamp: datetime = Field(...)
    service: str = Field(..., min_length=1, max_length=64)
    attributes: tuple[tuple[str, str], ...] = Field(default=())


class OperationalMetricDefinitionV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    metric_id: str = Field(..., min_length=1, max_length=128)
    version: str = Field(default="1.0", min_length=1, max_length=32)
    metric_type: OperationalMetricTypeV2 = Field(...)
    description: str = Field(..., max_length=256)
    unit: str = Field(..., max_length=32)
    allowed_labels: tuple[str, ...] = Field(default=())
    max_cardinality: int = Field(default=100, ge=1, le=10000)
    sli_association: str | None = Field(default=None, max_length=128)


class OperationalMetricPointV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    metric_id: str = Field(..., min_length=1, max_length=128)
    value: Decimal = Field(...)
    timestamp: datetime = Field(...)
    labels: tuple[tuple[str, str], ...] = Field(default=())


class OperationalMetricRollupV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    metric_id: str = Field(..., min_length=1, max_length=128)
    window_start: datetime = Field(...)
    window_end: datetime = Field(...)
    count: int = Field(..., ge=0)
    sum_value: Decimal = Field(...)
    min_value: Decimal = Field(...)
    max_value: Decimal = Field(...)
    avg_value: Decimal = Field(...)
    labels: tuple[tuple[str, str], ...] = Field(default=())


class OperationalMetricLabelSetV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    allowed_keys: tuple[str, ...] = Field(default=())
    dropped_count: int = Field(default=0, ge=0)


class RedactionPolicyV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    forbidden_headers: tuple[str, ...] = Field(
        default=("authorization", "cookie", "set-cookie", "x-api-key", "proxy-authorization")
    )
    forbidden_keys: tuple[str, ...] = Field(
        default=("password", "secret", "token", "dsn", "sql", "binds", "prompt", "chain_of_thought", "pii")
    )
    redaction_token: str = Field(default="[REDACTED]", min_length=1, max_length=32)


class CardinalityPolicyV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    max_label_value_length: int = Field(default=64, ge=8, le=256)
    fallback_value: str = Field(default="OTHER", min_length=1, max_length=32)


class SliDefinitionV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    sli_id: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=128)
    description: str = Field(..., max_length=256)
    good_events_metric_id: str = Field(..., min_length=1, max_length=128)
    total_events_metric_id: str = Field(..., min_length=1, max_length=128)


class SloDefinitionV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    slo_id: str = Field(..., min_length=1, max_length=128)
    sli_id: str = Field(..., min_length=1, max_length=128)
    target_percentage: Decimal = Field(..., ge=Decimal("0.0"), le=Decimal("100.00"))
    window_days: int = Field(default=30, ge=1, le=365)
    is_provisional: bool = Field(default=True)


class ErrorBudgetV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    slo_id: str = Field(..., min_length=1, max_length=128)
    total_events: int = Field(..., ge=0)
    good_events: int = Field(..., ge=0)
    bad_events: int = Field(..., ge=0)
    target_percentage: Decimal = Field(..., ge=Decimal("0.0"), le=Decimal("100.00"))
    consumed_budget_percentage: Decimal = Field(..., ge=Decimal("0.0"), le=Decimal("100.00"))
    remaining_budget_percentage: Decimal = Field(..., ge=Decimal("0.0"), le=Decimal("100.00"))
    status: SloStatusV2 = Field(...)


class SloEvaluationV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    evaluation_id: str = Field(..., min_length=1, max_length=128)
    slo_id: str = Field(..., min_length=1, max_length=128)
    evaluated_at: datetime = Field(...)
    current_percentage: Decimal = Field(..., ge=Decimal("0.0"), le=Decimal("100.00"))
    target_percentage: Decimal = Field(..., ge=Decimal("0.0"), le=Decimal("100.00"))
    error_budget: ErrorBudgetV2 = Field(...)
    status: SloStatusV2 = Field(...)


class EvaluationExpectationV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    expected_outcome: EvaluationOutcomeV2 = Field(default=EvaluationOutcomeV2.PASS)
    expected_status: str | None = Field(default=None, max_length=64)
    max_duration_ms: Decimal | None = Field(default=None, ge=Decimal("0.0"))
    required_capabilities: tuple[str, ...] = Field(default=())
    checksum: str = Field(..., min_length=8, max_length=128)


class EvaluationCaseV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    case_id: str = Field(..., min_length=1, max_length=128)
    suite: EvaluationSuiteKindV2 = Field(...)
    version: str = Field(default="1.0", min_length=1, max_length=32)
    title: str = Field(..., min_length=1, max_length=256)
    input_fixture_reference: str = Field(..., min_length=1, max_length=256)
    expectation: EvaluationExpectationV2 = Field(...)
    severity: str = Field(default="HIGH", max_length=32)
    deterministic: bool = Field(default=True)
    classification: TelemetryClassificationV2 = Field(default=TelemetryClassificationV2.INTERNAL_OPERATIONAL)


class EvaluationEvidenceV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    evidence_id: str = Field(..., min_length=1, max_length=128)
    case_id: str = Field(..., min_length=1, max_length=128)
    executed_at: datetime = Field(...)
    duration_ms: Decimal = Field(..., ge=Decimal("0.0"))
    sanitized_output_digest: str = Field(..., min_length=8, max_length=128)
    logs_digest: str = Field(..., min_length=8, max_length=128)
    checksum: str = Field(..., min_length=8, max_length=128)


class EvaluationResultV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    result_id: str = Field(..., min_length=1, max_length=128)
    case_id: str = Field(..., min_length=1, max_length=128)
    suite: EvaluationSuiteKindV2 = Field(...)
    outcome: EvaluationOutcomeV2 = Field(...)
    duration_ms: Decimal = Field(..., ge=Decimal("0.0"))
    evidence: EvaluationEvidenceV2 = Field(...)
    failure_reasons: tuple[str, ...] = Field(default=())
    checksum: str = Field(..., min_length=8, max_length=128)


class EvaluationMetricV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    metric_name: str = Field(..., min_length=1, max_length=128)
    value: Decimal = Field(...)
    unit: str = Field(..., max_length=32)


class EvaluationRegressionV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    regression_id: str = Field(..., min_length=1, max_length=128)
    case_id: str = Field(..., min_length=1, max_length=128)
    suite: EvaluationSuiteKindV2 = Field(...)
    regression_type: RegressionTypeV2 = Field(...)
    description: str = Field(..., max_length=256)
    detected_at: datetime = Field(...)
    baseline_checksum: str = Field(..., min_length=8, max_length=128)
    current_checksum: str = Field(..., min_length=8, max_length=128)


class EvaluationBaselineV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    baseline_id: str = Field(..., min_length=1, max_length=128)
    suite: EvaluationSuiteKindV2 = Field(...)
    version: str = Field(default="1.0", min_length=1, max_length=32)
    source_commit_reference: str = Field(..., min_length=7, max_length=128)
    corpus_version: str = Field(..., min_length=1, max_length=64)
    case_checksums: tuple[tuple[str, str], ...] = Field(default=())
    created_at: datetime = Field(...)
    checksum: str = Field(..., min_length=8, max_length=128)


class EvaluationSuiteV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    suite_id: str = Field(..., min_length=1, max_length=128)
    kind: EvaluationSuiteKindV2 = Field(...)
    title: str = Field(..., min_length=1, max_length=128)
    description: str = Field(..., max_length=256)
    case_count: int = Field(..., ge=1)
    deterministic_only: bool = Field(default=True)


class EvaluationRunV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    run_id: str = Field(..., min_length=1, max_length=128)
    suite: EvaluationSuiteKindV2 = Field(...)
    executed_at: datetime = Field(...)
    total_cases: int = Field(..., ge=0)
    passed_cases: int = Field(..., ge=0)
    failed_cases: int = Field(..., ge=0)
    blocked_cases: int = Field(..., ge=0)
    error_cases: int = Field(..., ge=0)
    duration_ms: Decimal = Field(..., ge=Decimal("0.0"))
    results: tuple[EvaluationResultV2, ...] = Field(default=())
    regressions: tuple[EvaluationRegressionV2, ...] = Field(default=())
    checksum: str = Field(..., min_length=8, max_length=128)


class EvaluationSummaryV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    run_count: int = Field(..., ge=0)
    total_cases_executed: int = Field(..., ge=0)
    overall_pass_rate: Decimal = Field(..., ge=Decimal("0.0"), le=Decimal("100.00"))
    security_pass_rate: Decimal = Field(..., ge=Decimal("0.0"), le=Decimal("100.00"))
    tenant_isolation_pass_rate: Decimal = Field(..., ge=Decimal("0.0"), le=Decimal("100.00"))
    total_regressions: int = Field(..., ge=0)


class ObservabilityHealthV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    status: str = Field(default="healthy", max_length=32)
    uptime_seconds: Decimal = Field(..., ge=Decimal("0.0"))
    events_recorded: int = Field(..., ge=0)
    dropped_telemetry_count: int = Field(..., ge=0)


class ObservabilityReadinessV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    ready: bool = Field(...)
    mode: FeatureModeV2 = Field(...)
    database_allowed: bool = Field(...)
    registries_loaded: bool = Field(...)
    reasons: tuple[str, ...] = Field(default=())


class ObservabilitySnapshotV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    contract_version: str = Field(default="lumina.observability-metrics-evaluations/1.0")
    timestamp: datetime = Field(...)
    mode: FeatureModeV2 = Field(...)
    health: ObservabilityHealthV2 = Field(...)
    readiness: ObservabilityReadinessV2 = Field(...)
    slos: tuple[SloEvaluationV2, ...] = Field(default=())
    evaluation_summary: EvaluationSummaryV2 = Field(...)
