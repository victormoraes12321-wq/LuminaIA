from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from contracts.analytical_v2 import (
    ClarificationRequest,
    ComparisonCalculation,
    ComparisonSpecification,
    ConfidenceAssessment,
    DimensionReference,
    ExecutionReadiness,
    FieldOrigin,
    FilterSpecification,
    MetricReference,
    OrderingSpecification,
    QueryPlanV2,
    TemporalGranularity,
    TimeWindow,
)


COMPARISON_PLANNER_VERSION = "lumina.comparison-planner/1.0"


class ComparisonStrategyHint(str, Enum):
    SINGLE_AGGREGATION = "SINGLE_AGGREGATION"
    CONDITIONAL_AGGREGATION = "CONDITIONAL_AGGREGATION"
    MULTI_QUERY = "MULTI_QUERY"
    GROUPED_SERIES = "GROUPED_SERIES"
    PIVOT = "PIVOT"
    TARGET_JOIN = "TARGET_JOIN"
    LEGACY_COMPATIBILITY = "LEGACY_COMPATIBILITY"
    UNDECIDED = "UNDECIDED"


class PlanComplexityClassification(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    REJECTED = "REJECTED"


class PlanningIssueSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AlignmentCompatibility(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    COMPATIBLE_WITH_WARNINGS = "COMPATIBLE_WITH_WARNINGS"
    INCOMPATIBLE = "INCOMPATIBLE"


class MissingBucketPolicy(str, Enum):
    PRESERVE_NULL = "PRESERVE_NULL"
    ZERO_FILL = "ZERO_FILL"
    OMIT = "OMIT"


class NullValuePolicy(str, Enum):
    PRESERVE = "PRESERVE"
    ZERO_IF_ADDITIVE = "ZERO_IF_ADDITIVE"
    OMIT = "OMIT"


class StrictPlanningModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        str_strip_whitespace=True,
    )


class ComparisonPlanningContext(StrictPlanningModel):
    tenant_id: UUID | None
    user_id: UUID | None = None
    user_role: str = Field(min_length=1, max_length=32)
    session_id: str | None = Field(default=None, max_length=128)
    timezone: str = Field(default="America/Sao_Paulo", min_length=1, max_length=64)
    locale: str = Field(default="pt-BR", pattern=r"^pt-BR$")
    allowed_metric_ids: tuple[str, ...] = ()
    allowed_dimension_ids: tuple[str, ...] = ()
    allowed_entity_types: tuple[str, ...] = ()
    allowed_source_ids: tuple[str, ...] = ()
    permission_fingerprint: str = Field(min_length=8, max_length=128)
    maximum_operands: int = Field(default=20, ge=2, le=200)
    maximum_metrics: int = Field(default=10, ge=1, le=100)
    maximum_dimensions: int = Field(default=5, ge=0, le=50)
    maximum_plan_complexity: int = Field(default=500, ge=1, le=100_000)
    maximum_series: int = Field(default=250, ge=1, le=100_000)
    maximum_text_length: int = Field(default=4000, ge=100, le=100_000)
    reference_datetime: datetime
    feature_flags: dict[str, bool] = Field(default_factory=dict)
    source: str = Field(default="trusted_backend", min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_context(self) -> "ComparisonPlanningContext":
        if (
            self.reference_datetime.tzinfo is None
            or self.reference_datetime.utcoffset() is None
        ):
            raise ValueError("reference_datetime must be timezone-aware")
        for values, label in (
            (self.allowed_metric_ids, "allowed_metric_ids"),
            (self.allowed_dimension_ids, "allowed_dimension_ids"),
            (self.allowed_entity_types, "allowed_entity_types"),
            (self.allowed_source_ids, "allowed_source_ids"),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{label} must not contain duplicates")
        return self


class ComparisonPlanningIssue(StrictPlanningModel):
    issue_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_.:-]*$")
    code: str = Field(min_length=1, max_length=80)
    severity: PlanningIssueSeverity
    message: str = Field(min_length=1, max_length=320)
    field_path: str | None = Field(default=None, max_length=160)
    operand_id: str | None = Field(default=None, max_length=100)
    requires_clarification: bool = False
    blocks_execution: bool = False


class ComparisonPlanComplexity(StrictPlanningModel):
    operand_count: int = Field(ge=0)
    metric_count: int = Field(ge=0)
    dimension_count: int = Field(ge=0)
    estimated_series_count: int = Field(ge=0)
    estimated_query_count: int = Field(ge=0)
    complexity_score: int = Field(ge=0)
    classification: PlanComplexityClassification
    limit_exceeded: bool


class ComparisonFilterPartition(StrictPlanningModel):
    shared_filters: tuple[FilterSpecification, ...] = ()
    operand_specific_filters: dict[str, tuple[FilterSpecification, ...]] = Field(
        default_factory=dict
    )
    conflicting_filters: tuple[str, ...] = ()
    unresolved_filters: tuple[str, ...] = ()
    partition_rule_ids: tuple[str, ...] = ()


class ComparisonAlignmentSpecification(StrictPlanningModel):
    alignment_dimensions: tuple[DimensionReference, ...] = ()
    temporal_granularity: TemporalGranularity | None = None
    entity_granularity: str | None = Field(default=None, max_length=80)
    missing_bucket_policy: MissingBucketPolicy = MissingBucketPolicy.PRESERVE_NULL
    null_policy: NullValuePolicy = NullValuePolicy.PRESERVE
    ordering: tuple[OrderingSpecification, ...] = ()
    series_identity: tuple[str, ...] = ()
    compatibility_status: AlignmentCompatibility
    warnings: tuple[str, ...] = ()


class ComparisonOperandPlan(StrictPlanningModel):
    operand_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_.:-]*$")
    label: str = Field(min_length=1, max_length=200)
    metric_refs: tuple[MetricReference, ...] = ()
    time_windows: tuple[TimeWindow, ...] = ()
    entity_filters: tuple[FilterSpecification, ...] = ()
    specific_filters: tuple[FilterSpecification, ...] = ()
    inherited_filters: tuple[FilterSpecification, ...] = ()
    dimension_refs: tuple[DimensionReference, ...] = ()
    source_refs: tuple[str, ...] = ()
    origin: FieldOrigin
    confidence: ConfidenceAssessment
    validation_requirements: tuple[str, ...] = ()


class ComparisonExecutionPlanDefinition(StrictPlanningModel):
    comparison: ComparisonSpecification
    shared_metric_refs: tuple[MetricReference, ...] = ()
    shared_dimensions: tuple[DimensionReference, ...] = ()
    shared_filters: tuple[FilterSpecification, ...] = ()
    operand_plans: tuple[ComparisonOperandPlan, ...]
    filter_partition: ComparisonFilterPartition
    alignment: ComparisonAlignmentSpecification
    calculations: tuple[ComparisonCalculation, ...]
    baseline_operand_id: str | None = None
    ordering: tuple[OrderingSpecification, ...] = ()
    limit: int | None = Field(default=None, ge=1, le=10_000)
    strategy_hint: ComparisonStrategyHint
    validation_requirements: tuple[str, ...] = ()
    complexity: ComparisonPlanComplexity
    readiness: ExecutionReadiness


class ComparisonPlanningResult(StrictPlanningModel):
    plan: QueryPlanV2 | None = None
    definition: ComparisonExecutionPlanDefinition | None = None
    readiness: ExecutionReadiness
    confidence: ConfidenceAssessment
    clarification: ClarificationRequest | None = None
    issues: tuple[ComparisonPlanningIssue, ...] = ()
    warnings: tuple[str, ...] = ()
    strategy_hint: ComparisonStrategyHint
    complexity: ComparisonPlanComplexity
    planner_version: str = COMPARISON_PLANNER_VERSION
    rule_ids: tuple[str, ...] = ()
    shadow_divergence: dict[str, JsonValue] | None = None
    cache_identity: str | None = Field(
        default=None,
        max_length=128,
        pattern=r"^[A-Za-z0-9:_-]+$",
    )
    duration_ms: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_result(self) -> "ComparisonPlanningResult":
        if self.readiness == ExecutionReadiness.READY:
            if self.plan is None or self.definition is None:
                raise ValueError("READY comparison planning requires a complete plan")
            if any(issue.blocks_execution for issue in self.issues):
                raise ValueError("READY comparison planning cannot contain blocking issues")
        if (
            self.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED
            and self.clarification is None
        ):
            raise ValueError("clarification readiness requires an objective question")
        if (
            self.clarification is not None
            and self.readiness != ExecutionReadiness.CLARIFICATION_REQUIRED
        ):
            raise ValueError("clarification is only valid for clarification readiness")
        return self
