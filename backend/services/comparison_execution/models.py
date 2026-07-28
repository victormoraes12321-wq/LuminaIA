from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from contracts.analytical_v2 import (
    ComparisonCalculation,
    ComparisonKind,
    ExecutionProvenance,
    FilterSpecification,
    TimeWindow,
    ValidationReport,
)
from services.comparison_planning import MissingBucketPolicy, NullValuePolicy


COMPARISON_EXECUTOR_VERSION = "lumina.comparison-executor/1.0"


class StrictExecutionModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        str_strip_whitespace=True,
        arbitrary_types_allowed=True,
    )


class ComparisonExecutionStatus(str, Enum):
    READY = "READY"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


class OperandExecutionStatus(str, Enum):
    READY = "READY"
    EMPTY = "EMPTY"
    TRUNCATED = "TRUNCATED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    BLOCKED = "BLOCKED"


class ExecutionNodeStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ExecutionNodeType(str, Enum):
    OPERAND_QUERY = "OPERAND_QUERY"
    TARGET_QUERY = "TARGET_QUERY"
    ALIGNMENT = "ALIGNMENT"
    CALCULATION = "CALCULATION"
    VALIDATION = "VALIDATION"
    RESPONSE_ASSEMBLY = "RESPONSE_ASSEMBLY"


class ComparisonExecutionStrategy(str, Enum):
    SINGLE_AGGREGATION = "SINGLE_AGGREGATION"
    CONDITIONAL_AGGREGATION = "CONDITIONAL_AGGREGATION"
    MULTI_QUERY = "MULTI_QUERY"
    GROUPED_SERIES = "GROUPED_SERIES"
    PIVOT = "PIVOT"
    TARGET_JOIN = "TARGET_JOIN"
    LEGACY_COMPATIBILITY = "LEGACY_COMPATIBILITY"


class ComparisonDirection(str, Enum):
    INCREASE = "INCREASE"
    DECREASE = "DECREASE"
    STABLE = "STABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ZeroDenominatorPolicy(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    ZERO_WHEN_BOTH_ZERO = "ZERO_WHEN_BOTH_ZERO"
    EXPLICIT_INFINITY_UNSUPPORTED = "EXPLICIT_INFINITY_UNSUPPORTED"
    ERROR = "ERROR"


class RoundingPolicy(str, Enum):
    ROUND_HALF_UP = "ROUND_HALF_UP"


class FailurePolicy(str, Enum):
    FAIL_COMPARISON = "FAIL_COMPARISON"
    ALLOW_PARTIAL = "ALLOW_PARTIAL"


class RetryPolicy(StrictExecutionModel):
    maximum_attempts: int = Field(default=2, ge=1, le=3)
    transient_only: bool = True


class ComparisonExecutionContext(StrictExecutionModel):
    tenant_id: UUID
    user_id: UUID | None = None
    user_role: str = Field(min_length=1, max_length=32)
    session_id: str | None = Field(default=None, max_length=128)
    permission_fingerprint: str = Field(min_length=8, max_length=128)
    allowed_source_ids: tuple[str, ...]
    allowed_metric_ids: tuple[str, ...]
    allowed_dimension_ids: tuple[str, ...]
    query_timeout_seconds: Decimal = Field(default=Decimal("5"), gt=0, le=Decimal("120"))
    total_timeout_seconds: Decimal = Field(default=Decimal("20"), gt=0, le=Decimal("300"))
    maximum_rows_per_operand: int = Field(default=1000, ge=1, le=10000)
    maximum_total_rows: int = Field(default=5000, ge=1, le=50000)
    maximum_operands: int = Field(default=20, ge=2, le=200)
    maximum_queries: int = Field(default=20, ge=1, le=200)
    maximum_concurrency: int = Field(default=4, ge=1, le=16)
    maximum_payload_bytes: int = Field(default=2_000_000, ge=1024, le=20_000_000)
    decimal_precision: int = Field(default=2, ge=0, le=12)
    rounding_policy: RoundingPolicy = RoundingPolicy.ROUND_HALF_UP
    zero_denominator_policy: ZeroDenominatorPolicy = ZeroDenominatorPolicy.NOT_APPLICABLE
    missing_bucket_policy: MissingBucketPolicy = MissingBucketPolicy.PRESERVE_NULL
    null_policy: NullValuePolicy = NullValuePolicy.PRESERVE
    failure_policy: FailurePolicy = FailurePolicy.FAIL_COMPARISON
    request_id: UUID | None = None
    trace_id: UUID | None = None
    feature_flags: dict[str, bool] = Field(default_factory=dict)
    source_version: str = Field(min_length=1, max_length=128)
    sync_version: str | None = Field(default=None, max_length=128)
    source: str = Field(
        default="postgresql_analytical_clone",
        pattern=r"^postgresql_analytical_clone$",
    )
    entity_values: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_context(self) -> "ComparisonExecutionContext":
        for values, label in (
            (self.allowed_source_ids, "allowed_source_ids"),
            (self.allowed_metric_ids, "allowed_metric_ids"),
            (self.allowed_dimension_ids, "allowed_dimension_ids"),
        ):
            if not values:
                raise ValueError(f"{label} cannot be empty")
            if len(values) != len(set(values)):
                raise ValueError(f"{label} cannot contain duplicates")
        if self.maximum_total_rows < self.maximum_rows_per_operand:
            raise ValueError("maximum_total_rows cannot be smaller than maximum_rows_per_operand")
        return self


class ComparisonExecutionNode(StrictExecutionModel):
    node_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_.:-]*$")
    node_type: ExecutionNodeType
    dependencies: tuple[str, ...] = ()
    operand_id: str | None = None
    status: ExecutionNodeStatus = ExecutionNodeStatus.PENDING
    timeout_seconds: Decimal = Field(gt=0)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    failure_policy: FailurePolicy = FailurePolicy.FAIL_COMPARISON


class ComparisonExecutionGraph(StrictExecutionModel):
    nodes: tuple[ComparisonExecutionNode, ...]
    dependencies: dict[str, tuple[str, ...]]
    execution_order: tuple[str, ...]
    parallel_groups: tuple[tuple[str, ...], ...]
    maximum_concurrency: int = Field(ge=1)
    estimated_queries: int = Field(ge=0)
    estimated_rows: int = Field(ge=0)
    strategy: ComparisonExecutionStrategy
    graph_fingerprint: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")


class CompiledOperandQuery(StrictExecutionModel):
    operand_id: str
    source_id: str
    metric_ids: tuple[str, ...]
    dimension_ids: tuple[str, ...]
    logical_filters: tuple[FilterSpecification, ...]
    time_windows: tuple[TimeWindow, ...]
    statement: str = Field(min_length=1)
    binds: dict[str, Any]
    expected_columns: tuple[str, ...]
    query_fingerprint: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")
    timeout_seconds: Decimal = Field(gt=0)
    row_limit: int = Field(ge=1)
    strategy: ComparisonExecutionStrategy


class ComparisonExecutionProvenance(StrictExecutionModel):
    public: ExecutionProvenance
    plan_fingerprint: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")
    graph_fingerprint: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")
    operand_fingerprints: dict[str, str]
    executor_version: str = COMPARISON_EXECUTOR_VERSION
    planner_version: str
    temporal_version: str | None = None
    validation_version: str
    source_version: str
    source_isolation: str


class OperandExecutionResult(StrictExecutionModel):
    operand_id: str
    status: OperandExecutionStatus
    dataset: tuple[dict[str, Any], ...] = ()
    row_count: int = Field(ge=0)
    truncated: bool = False
    duration_ms: Decimal = Field(ge=0)
    query_fingerprint: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")
    source_version: str
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    provenance: ComparisonExecutionProvenance | None = None
    validation: ValidationReport | None = None


class AlignedComparisonRow(StrictExecutionModel):
    alignment_key: tuple[str, ...]
    dimensions: dict[str, str | None]
    values: dict[str, Decimal | None]


class AlignedComparisonDataset(StrictExecutionModel):
    dataset_id: str
    metric_id: str
    alignment_keys: tuple[str, ...]
    series: tuple[str, ...]
    rows: tuple[AlignedComparisonRow, ...]
    missing_buckets: tuple[tuple[str, ...], ...] = ()
    null_buckets: tuple[tuple[str, ...], ...] = ()
    alignment_policy: str
    row_count: int = Field(ge=0)
    truncated: bool = False
    data_types: dict[str, str]
    units: dict[str, str]


class ComparisonCalculationResult(StrictExecutionModel):
    calculation: ComparisonCalculation
    baseline_operand_id: str | None
    target_operand_id: str
    metric_id: str
    alignment_key: tuple[str, ...]
    baseline_value: Decimal | None
    target_value: Decimal | None
    raw_result_value: Decimal | None
    result_value: Decimal | None
    direction: ComparisonDirection
    status: str
    zero_denominator: bool = False
    not_applicable_reason: str | None = None
    rounding_applied: bool = False
    validation_checks: tuple[str, ...] = ()


class ComparisonExecutionIssue(StrictExecutionModel):
    issue_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_.:-]*$")
    code: str = Field(min_length=1, max_length=80)
    severity: str = Field(pattern=r"^(INFO|WARNING|ERROR|CRITICAL)$")
    message: str = Field(min_length=1, max_length=500)
    node_id: str | None = None
    operand_id: str | None = None
    metric_id: str | None = None
    blocks_result: bool
    public_message: str = Field(min_length=1, max_length=500)
    evidence_reference: str | None = Field(default=None, max_length=256)


class ComparisonExecutionResult(StrictExecutionModel):
    status: ComparisonExecutionStatus
    plan_id: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")
    execution_id: UUID
    comparison_kind: ComparisonKind
    operands: tuple[OperandExecutionResult, ...]
    aligned_datasets: tuple[AlignedComparisonDataset, ...]
    calculations: tuple[ComparisonCalculationResult, ...]
    summary_values: dict[str, Decimal | str | None]
    provenance: tuple[ComparisonExecutionProvenance, ...]
    validation: ValidationReport
    warnings: tuple[str, ...] = ()
    errors: tuple[ComparisonExecutionIssue, ...] = ()
    partial: bool = False
    executor_version: str = COMPARISON_EXECUTOR_VERSION
    duration_ms: Decimal = Field(ge=0)
    strategy_used: ComparisonExecutionStrategy
    cache_status: str = Field(pattern=r"^(HIT|MISS|BYPASS)$")

    @model_validator(mode="after")
    def validate_result(self) -> "ComparisonExecutionResult":
        if self.status == ComparisonExecutionStatus.READY:
            if self.partial or self.errors:
                raise ValueError("READY result cannot be partial or contain errors")
            if any(item.status not in {OperandExecutionStatus.READY, OperandExecutionStatus.EMPTY} for item in self.operands):
                raise ValueError("READY result requires all mandatory operands")
        if self.partial != (self.status == ComparisonExecutionStatus.PARTIAL):
            raise ValueError("partial flag must match PARTIAL status")
        return self
