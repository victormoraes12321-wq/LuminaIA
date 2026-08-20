from __future__ import annotations

import re
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    field_validator,
    model_validator,
)

from .enums import (
    AnalyticalErrorCode,
    ColumnDataType,
    ComparisonCalculation,
    ComparisonKind,
    ConfidenceLevel,
    DataClassification,
    DataSourceKind,
    DimensionRole,
    ExecutionReadiness,
    FieldOrigin,
    FilterOperator,
    IntentKind,
    OutOfScopeReason,
    PipelineKind,
    PlanOperation,
    TemporalGranularity,
    ValidationSeverity,
    ValidationStatus,
    VisualizationKind,
)


SCHEMA_NAME = "lumina.analytics"
SCHEMA_VERSION = "2.0"

LogicalId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z][A-Za-z0-9_.:-]*$",
    ),
]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]

_FORBIDDEN_PAYLOAD_TERMS = (
    "authorization",
    "api_key",
    "apikey",
    "password",
    "passwd",
    "secret",
    "token",
    "javascript:",
    "<script",
)
_SQL_SNIPPET = re.compile(
    r"(?:^|\s)(?:select|insert|update|delete|drop|alter|create|grant|revoke)\s+",
    re.IGNORECASE,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _assert_safe_json(value: JsonValue, *, path: str) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = str(key).lower()
            if any(term in lowered for term in _FORBIDDEN_PAYLOAD_TERMS):
                raise ValueError(f"{path} contains a forbidden key")
            if lowered in {"sql", "query_sql", "binds", "credentials"}:
                raise ValueError(f"{path} cannot contain executable or sensitive data")
            _assert_safe_json(nested, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _assert_safe_json(nested, path=f"{path}[{index}]")
    elif isinstance(value, str):
        lowered = value.lower()
        if any(term in lowered for term in _FORBIDDEN_PAYLOAD_TERMS):
            raise ValueError(f"{path} contains forbidden content")
        if _SQL_SNIPPET.search(value):
            raise ValueError(f"{path} cannot contain SQL")


def _ensure_unique(values: list[str], *, label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must not contain duplicate IDs")


class StrictContractModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )


class ContractMetadata(StrictContractModel):
    schema_name: str = SCHEMA_NAME
    schema_version: str = SCHEMA_VERSION
    created_at: datetime = Field(default_factory=utc_now)
    request_id: UUID | None = None
    trace_id: UUID | None = None
    pipeline: PipelineKind
    adapter_used: str | None = Field(default=None, max_length=100)
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_contract(self) -> "ContractMetadata":
        if self.schema_name != SCHEMA_NAME or self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported analytical contract version: {self.schema_name}/{self.schema_version}"
            )
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware UTC")
        if self.created_at.utcoffset().total_seconds() != 0:
            raise ValueError("created_at must use UTC")
        reserved = set(type(self).model_fields) - {"extensions"}
        if reserved.intersection(self.extensions):
            raise ValueError("extensions cannot replace official contract fields")
        _assert_safe_json(self.extensions, path="extensions")
        return self


class ExecutionScope(StrictContractModel):
    tenant_id: UUID
    user_id: UUID | None = None
    user_role: str = Field(min_length=1, max_length=32, pattern=r"^[A-Z_]+$")
    session_id: str | None = Field(default=None, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    allowed_source_ids: list[LogicalId] = Field(default_factory=list)
    permission_fingerprint: str = Field(
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9:_-]+$",
    )
    origin: FieldOrigin

    @model_validator(mode="after")
    def validate_scope(self) -> "ExecutionScope":
        _ensure_unique(list(self.allowed_source_ids), label="allowed_source_ids")
        return self


class ConfidenceAssessment(StrictContractModel):
    level: ConfidenceLevel
    score: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    reasons: list[ShortText] = Field(default_factory=list, max_length=10)
    requires_confirmation: bool = False

    @model_validator(mode="after")
    def validate_confidence(self) -> "ConfidenceAssessment":
        if self.level == ConfidenceLevel.LOW and not self.requires_confirmation:
            raise ValueError("LOW confidence requires confirmation")
        return self


class MetricReference(StrictContractModel):
    metric_id: LogicalId
    metric_version: str = Field(min_length=1, max_length=64)
    display_name: ShortText
    unit: str = Field(min_length=1, max_length=32)
    aggregation: str = Field(min_length=1, max_length=32)
    origin: FieldOrigin
    confidence: ConfidenceAssessment

    @model_validator(mode="after")
    def validate_inferred_metric(self) -> "MetricReference":
        if (
            self.origin == FieldOrigin.LLM_INFERENCE
            and self.confidence.level == ConfidenceLevel.HIGH
            and not self.confidence.reasons
        ):
            raise ValueError("HIGH LLM confidence requires a public reason")
        return self


class DimensionReference(StrictContractModel):
    dimension_id: LogicalId
    display_name: ShortText
    role: DimensionRole
    origin: FieldOrigin
    confidence: ConfidenceAssessment


class FilterSpecification(StrictContractModel):
    filter_id: LogicalId
    field_id: LogicalId
    operator: FilterOperator
    value: JsonValue | None = None
    values: list[JsonValue] = Field(default_factory=list)
    origin: FieldOrigin
    confidence: ConfidenceAssessment
    is_explicit: bool

    @model_validator(mode="after")
    def validate_cardinality(self) -> "FilterSpecification":
        if self.operator == FilterOperator.BETWEEN:
            if self.value is not None or len(self.values) != 2:
                raise ValueError("BETWEEN requires exactly two values")
        elif self.operator in {FilterOperator.IN, FilterOperator.NOT_IN}:
            if self.value is not None or not self.values:
                raise ValueError(f"{self.operator.value} requires a non-empty values list")
        elif self.operator in {FilterOperator.IS_NULL, FilterOperator.IS_NOT_NULL}:
            if self.value is not None or self.values:
                raise ValueError(f"{self.operator.value} does not accept values")
        elif self.value is None or self.values:
            raise ValueError(f"{self.operator.value} requires one scalar value")
        _assert_safe_json(self.value, path="filter.value")
        _assert_safe_json(self.values, path="filter.values")
        return self


class TimeWindow(StrictContractModel):
    window_id: LogicalId
    label: ShortText
    start: date
    end: date
    end_inclusive: bool = True
    granularity: TemporalGranularity
    timezone: str = Field(min_length=1, max_length=64)
    origin: FieldOrigin
    confidence: ConfidenceAssessment
    raw_expression: str | None = Field(default=None, max_length=256)

    @model_validator(mode="after")
    def validate_window(self) -> "TimeWindow":
        if self.end < self.start:
            raise ValueError("TimeWindow end cannot precede start")
        if self.timezone != "UTC" and not re.fullmatch(
            r"[A-Za-z]+(?:[_-][A-Za-z]+)*/[A-Za-z]+(?:[_-][A-Za-z]+)*",
            self.timezone,
        ):
            raise ValueError("TimeWindow timezone must be UTC or a controlled IANA identifier")
        return self


class EntityReference(StrictContractModel):
    entity_id: LogicalId
    display_name: ShortText
    origin: FieldOrigin


class ComparisonOperand(StrictContractModel):
    operand_id: LogicalId
    label: ShortText
    metric_refs: list[MetricReference] = Field(default_factory=list)
    time_windows: list[TimeWindow] = Field(default_factory=list)
    filters: list[FilterSpecification] = Field(default_factory=list)
    entity_refs: list[EntityReference] = Field(default_factory=list)
    origin: FieldOrigin

    @model_validator(mode="after")
    def validate_operand(self) -> "ComparisonOperand":
        if not (self.metric_refs or self.time_windows or self.filters or self.entity_refs):
            raise ValueError("Comparison operand must contain distinguishable information")
        _ensure_unique([item.metric_id for item in self.metric_refs], label="operand metric_refs")
        _ensure_unique([item.window_id for item in self.time_windows], label="operand time_windows")
        _ensure_unique([item.filter_id for item in self.filters], label="operand filters")
        _ensure_unique([item.entity_id for item in self.entity_refs], label="operand entity_refs")
        return self


class ComparisonSpecification(StrictContractModel):
    comparison_id: LogicalId
    kind: ComparisonKind
    operands: list[ComparisonOperand] = Field(min_length=2)
    calculations: list[ComparisonCalculation] = Field(min_length=1)
    baseline_operand_id: LogicalId | None = None
    alignment_dimensions: list[LogicalId] = Field(default_factory=list)
    requested_sort: str | None = Field(default=None, max_length=100)
    origin: FieldOrigin
    confidence: ConfidenceAssessment

    @model_validator(mode="after")
    def validate_comparison(self) -> "ComparisonSpecification":
        operand_ids = [operand.operand_id for operand in self.operands]
        _ensure_unique(operand_ids, label="comparison operands")
        if self.baseline_operand_id and self.baseline_operand_id not in operand_ids:
            raise ValueError("baseline_operand_id must reference an existing operand")
        if len(self.calculations) != len(set(self.calculations)):
            raise ValueError("comparison calculations must be unique")
        if self.kind in {ComparisonKind.PERIOD_VS_PERIOD, ComparisonKind.MULTI_PERIOD}:
            windows = [
                (window.start, window.end)
                for operand in self.operands
                for window in operand.time_windows
            ]
            if any(not operand.time_windows for operand in self.operands):
                raise ValueError("temporal comparison requires a period in every operand")
            if len(set(windows)) < 2:
                raise ValueError("temporal comparison requires two distinguishable periods")
        return self


class VisualizationSpecification(StrictContractModel):
    visualization_id: LogicalId
    kind: VisualizationKind
    title: ShortText
    metric_ids: list[LogicalId] = Field(default_factory=list)
    dimension_ids: list[LogicalId] = Field(default_factory=list)
    data_reference: LogicalId
    priority: int = Field(ge=0, le=1000)
    is_primary: bool = False
    origin: FieldOrigin
    options: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_visualization(self) -> "VisualizationSpecification":
        _ensure_unique(list(self.metric_ids), label="visualization metric_ids")
        _ensure_unique(list(self.dimension_ids), label="visualization dimension_ids")
        _assert_safe_json(self.options, path="visualization.options")
        return self


class ClarificationRequest(StrictContractModel):
    question: ShortText
    missing_fields: list[LogicalId] = Field(min_length=1)
    candidate_options: list[ShortText] = Field(default_factory=list, max_length=20)
    reason: ShortText
    confidence: ConfidenceAssessment


class AnalyticalError(StrictContractModel):
    code: AnalyticalErrorCode
    message: ShortText
    field: LogicalId | None = None
    retryable: bool = False


class QueryIntentV2(StrictContractModel):
    contract: ContractMetadata
    intent_kind: IntentKind
    readiness: ExecutionReadiness
    raw_question: str = Field(min_length=3, max_length=1000)
    normalized_question: str = Field(min_length=3, max_length=1000)
    metric_refs: list[MetricReference] = Field(default_factory=list)
    dimension_refs: list[DimensionReference] = Field(default_factory=list)
    filters: list[FilterSpecification] = Field(default_factory=list)
    time_windows: list[TimeWindow] = Field(default_factory=list)
    comparison: ComparisonSpecification | None = None
    requested_visualizations: list[VisualizationSpecification] = Field(default_factory=list)
    confidence: ConfidenceAssessment
    clarification: ClarificationRequest | None = None
    out_of_scope_reason: OutOfScopeReason | None = None
    field_origins: dict[LogicalId, FieldOrigin]

    @model_validator(mode="after")
    def validate_intent(self) -> "QueryIntentV2":
        required_origins = {"raw_question", "intent_kind"}
        if not required_origins.issubset(self.field_origins):
            raise ValueError("critical intent fields require origin metadata")
        _ensure_unique([item.metric_id for item in self.metric_refs], label="intent metric_refs")
        _ensure_unique([item.dimension_id for item in self.dimension_refs], label="intent dimension_refs")
        _ensure_unique([item.filter_id for item in self.filters], label="intent filters")
        _ensure_unique([item.window_id for item in self.time_windows], label="intent time_windows")
        _validate_visualization_list(self.requested_visualizations)

        if self.readiness == ExecutionReadiness.OUT_OF_SCOPE:
            if self.intent_kind != IntentKind.OUT_OF_SCOPE or self.out_of_scope_reason is None:
                raise ValueError("OUT_OF_SCOPE requires a typed reason and matching intent")
        elif self.intent_kind == IntentKind.OUT_OF_SCOPE:
            raise ValueError("OUT_OF_SCOPE intent cannot use another readiness")

        if self.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED and self.clarification is None:
            raise ValueError("CLARIFICATION_REQUIRED requires an objective question")
        if self.clarification is not None and self.readiness != ExecutionReadiness.CLARIFICATION_REQUIRED:
            raise ValueError("clarification is only valid for CLARIFICATION_REQUIRED")

        if self.intent_kind == IntentKind.COMPARISON and self.comparison is None:
            raise ValueError("COMPARISON intent requires a comparison specification")
        if self.comparison is not None and self.intent_kind != IntentKind.COMPARISON:
            raise ValueError("comparison specification requires COMPARISON intent")

        no_metric_intents = {
            IntentKind.DETAIL,
            IntentKind.METADATA,
            IntentKind.FOLLOW_UP,
            IntentKind.CLARIFICATION,
        }
        if (
            self.readiness == ExecutionReadiness.READY
            and not self.metric_refs
            and self.intent_kind not in no_metric_intents
        ):
            raise ValueError("READY analytical intent requires a metric or supported metadata operation")
        return self


class SourceReference(StrictContractModel):
    source_id: LogicalId
    source_kind: DataSourceKind
    origin: FieldOrigin


class OrderingSpecification(StrictContractModel):
    field_id: LogicalId
    direction: str = Field(pattern=r"^(ASC|DESC)$")


class QueryPlanV2(StrictContractModel):
    contract: ContractMetadata
    scope: ExecutionScope | None
    intent: QueryIntentV2
    operation: PlanOperation
    metric_refs: list[MetricReference] = Field(default_factory=list)
    dimension_refs: list[DimensionReference] = Field(default_factory=list)
    filters: list[FilterSpecification] = Field(default_factory=list)
    time_windows: list[TimeWindow] = Field(default_factory=list)
    comparison: ComparisonSpecification | None = None
    visualizations: list[VisualizationSpecification] = Field(default_factory=list)
    source_refs: list[SourceReference] = Field(default_factory=list)
    limit: int | None = Field(default=None, ge=1, le=10000)
    ordering: list[OrderingSpecification] = Field(default_factory=list)
    confidence: ConfidenceAssessment
    validation_requirements: list[LogicalId] = Field(default_factory=list)
    cache_identity: str | None = Field(default=None, max_length=128, pattern=r"^[A-Za-z0-9:_-]+$")
    legacy_context: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_plan(self) -> "QueryPlanV2":
        if self.intent.readiness == ExecutionReadiness.READY:
            if self.scope is None:
                raise ValueError("READY plan requires trusted tenant scope")
            if self.operation == PlanOperation.NONE:
                raise ValueError("READY plan requires a supported operation")
        if self.comparison != self.intent.comparison:
            raise ValueError("plan comparison must preserve the intent comparison")
        _validate_visualization_list(self.visualizations)
        metric_ids = {metric.metric_id for metric in self.metric_refs}
        for visualization in self.visualizations:
            unknown = set(visualization.metric_ids) - metric_ids
            if unknown:
                raise ValueError("visualization references an unknown metric")
        _ensure_unique([source.source_id for source in self.source_refs], label="source_refs")
        _assert_safe_json(self.legacy_context, path="legacy_context")
        return self


class ExecutionProvenance(StrictContractModel):
    tenant_id: UUID
    source_id: LogicalId
    source_kind: DataSourceKind
    view_ids: list[LogicalId] = Field(default_factory=list)
    metric_versions: dict[LogicalId, str] = Field(default_factory=dict)
    filter_fingerprint: str | None = Field(default=None, max_length=128, pattern=r"^[A-Za-z0-9:_-]+$")
    periods: list[TimeWindow] = Field(default_factory=list)
    executed_at: datetime | None = None
    sync_version: str | None = Field(default=None, max_length=128)
    cache_status: str = Field(min_length=1, max_length=32)
    pipeline: PipelineKind
    query_fingerprint: str | None = Field(default=None, max_length=128, pattern=r"^[A-Za-z0-9:_-]+$")
    reconciliation_status: str | None = Field(default=None, max_length=64)
    tenant_isolation_verified: bool | None = None
    tenant_isolation_evidence: str | None = Field(default=None, max_length=256)

    @model_validator(mode="after")
    def validate_provenance(self) -> "ExecutionProvenance":
        if self.tenant_isolation_verified is True and not self.tenant_isolation_evidence:
            raise ValueError("verified tenant isolation requires evidence")
        if self.executed_at is not None and self.executed_at.tzinfo is None:
            raise ValueError("executed_at must be timezone-aware")
        return self


class ValidationCheck(StrictContractModel):
    check_id: LogicalId
    name: ShortText
    status: ValidationStatus
    severity: ValidationSeverity
    message: ShortText
    evidence_reference: str | None = Field(default=None, max_length=256)
    required: bool = True


class ValidationReport(StrictContractModel):
    status: ValidationStatus
    checks: list[ValidationCheck] = Field(default_factory=list)
    validated_at: datetime | None = None
    validator_version: str = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_report(self) -> "ValidationReport":
        required_failures = [
            check
            for check in self.checks
            if check.required and check.status == ValidationStatus.FAILED
        ]
        if self.status == ValidationStatus.PASSED:
            if not self.checks:
                raise ValueError("PASSED validation requires executed checks")
            if required_failures:
                raise ValueError("PASSED validation cannot contain required failures")
            if all(check.status == ValidationStatus.NOT_EXECUTED for check in self.checks):
                raise ValueError("NOT_EXECUTED checks cannot produce PASSED validation")
        if required_failures and self.status != ValidationStatus.FAILED:
            raise ValueError("required validation failure must fail the report")
        if self.validated_at is not None and self.validated_at.tzinfo is None:
            raise ValueError("validated_at must be timezone-aware")
        return self


class AnalyticalColumn(StrictContractModel):
    column_id: LogicalId
    label: ShortText
    data_type: ColumnDataType
    unit: str | None = Field(default=None, max_length=32)
    nullable: bool = True


class AnalyticalDataset(StrictContractModel):
    dataset_id: LogicalId
    columns: list[AnalyticalColumn] = Field(default_factory=list)
    rows: list[dict[str, JsonValue]] = Field(default_factory=list)
    row_count: int = Field(ge=0)
    truncated: bool = False
    numeric_metadata: dict[str, Decimal] = Field(default_factory=dict)
    data_classification: DataClassification

    @model_validator(mode="after")
    def validate_dataset(self) -> "AnalyticalDataset":
        _ensure_unique([column.column_id for column in self.columns], label="dataset columns")
        if self.row_count < len(self.rows):
            raise ValueError("row_count cannot be smaller than the embedded rows")
        for row in self.rows:
            _assert_safe_json(row, path="dataset.rows")
        return self


class ScopeSummary(StrictContractModel):
    tenant_id: UUID
    user_role: str = Field(min_length=1, max_length=32)
    session_id: str | None = Field(default=None, max_length=128)


class PlanSummary(StrictContractModel):
    operation: PlanOperation
    metric_ids: list[LogicalId] = Field(default_factory=list)
    dimension_ids: list[LogicalId] = Field(default_factory=list)
    source_ids: list[LogicalId] = Field(default_factory=list)
    periods: list[TimeWindow] = Field(default_factory=list)


class LegacyCompatibility(StrictContractModel):
    compatible: bool
    primary_chart_type: str | None = Field(default=None, max_length=32)
    warnings: list[ShortText] = Field(default_factory=list)
    sidecar_field: str = "analytical_contract"


class AnalyticalResponseV2(StrictContractModel):
    contract: ContractMetadata
    scope_summary: ScopeSummary
    intent: QueryIntentV2
    plan_summary: PlanSummary | None = None
    datasets: list[AnalyticalDataset] = Field(default_factory=list)
    visualizations: list[VisualizationSpecification] = Field(default_factory=list)
    provenance: list[ExecutionProvenance] = Field(default_factory=list)
    validation: ValidationReport
    summary: str | None = Field(default=None, max_length=4000)
    insights: list[ShortText] = Field(default_factory=list)
    warnings: list[ShortText] = Field(default_factory=list)
    errors: list[AnalyticalError] = Field(default_factory=list)
    clarification: ClarificationRequest | None = None
    legacy_compatibility: LegacyCompatibility

    @model_validator(mode="after")
    def validate_response(self) -> "AnalyticalResponseV2":
        dataset_ids = [dataset.dataset_id for dataset in self.datasets]
        _ensure_unique(dataset_ids, label="response datasets")
        _validate_visualization_list(self.visualizations)
        for visualization in self.visualizations:
            if visualization.data_reference not in dataset_ids:
                raise ValueError("visualization references an unknown dataset")
        if self.intent.readiness == ExecutionReadiness.READY and self.errors:
            raise ValueError("READY response cannot contain analytical errors")
        if self.intent.readiness == ExecutionReadiness.OUT_OF_SCOPE and self.datasets:
            raise ValueError("OUT_OF_SCOPE response cannot contain analytical datasets")
        if (
            self.intent.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED
            and self.datasets
        ):
            raise ValueError("clarification response cannot pretend execution")
        if self.clarification != self.intent.clarification:
            raise ValueError("response clarification must match the intent")
        return self


def _validate_visualization_list(
    visualizations: list[VisualizationSpecification],
) -> None:
    _ensure_unique(
        [visualization.visualization_id for visualization in visualizations],
        label="visualizations",
    )
    primary_count = sum(1 for visualization in visualizations if visualization.is_primary)
    if primary_count > 1:
        raise ValueError("only one visualization can be primary")
