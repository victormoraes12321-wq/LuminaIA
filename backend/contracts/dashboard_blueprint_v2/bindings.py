"""Canonical analytical references used by dashboard widgets."""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import Field, model_validator

from .identity import (
    CANONICAL_ID_PATTERN,
    DashboardClassificationV2,
    StrictDashboardModel,
)
from .presentation import (
    DashboardCachePreferenceV2,
    DashboardMaterializationPreferenceV2,
    DashboardProvenanceRequirementV2,
)


class DashboardResultShapeV2(str, Enum):
    SCALAR = "SCALAR"
    COMPARISON = "COMPARISON"
    TIME_SERIES = "TIME_SERIES"
    GROUPED_SERIES = "GROUPED_SERIES"
    RANKING = "RANKING"
    TABLE = "TABLE"
    STATUS_SUMMARY = "STATUS_SUMMARY"
    FACT_SET = "FACT_SET"


class DashboardCompletenessRequirementV2(str, Enum):
    COMPLETE = "COMPLETE"
    TRUNCATION_ALLOWED_WITH_NOTICE = "TRUNCATION_ALLOWED_WITH_NOTICE"
    PARTIAL_ALLOWED_WITH_NOTICE = "PARTIAL_ALLOWED_WITH_NOTICE"


class DashboardFreshnessRequirementV2(str, Enum):
    FRESH = "FRESH"
    STALE_WITH_NOTICE = "STALE_WITH_NOTICE"
    BACKEND_POLICY = "BACKEND_POLICY"


class DashboardMetricBindingV2(StrictDashboardModel):
    metric_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    metric_registry_version: str = Field(min_length=1, max_length=64)
    expected_unit: str = Field(min_length=1, max_length=32)
    expected_aggregation: Literal["SUM", "AVERAGE", "COUNT", "MIN", "MAX", "NONE"]
    expected_fingerprint: str | None = Field(default=None, min_length=8, max_length=128)
    display_alias: str | None = Field(default=None, min_length=1, max_length=120)


class DashboardDimensionBindingV2(StrictDashboardModel):
    dimension_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    display_label: str = Field(min_length=1, max_length=120)
    grouping_intent: Literal["CATEGORY", "TIME_BUCKET", "HIERARCHY", "NONE"]
    sorting_intent: Literal["ASC", "DESC", "METRIC_ASC", "METRIC_DESC", "NONE"]
    null_handling: Literal["PRESERVE", "LABEL_UNKNOWN", "OMIT"] = "PRESERVE"
    maximum_visual_cardinality: int = Field(default=20, ge=1, le=250)
    drilldown_eligible: bool = False


class DashboardEntityBindingV2(StrictDashboardModel):
    entity_type_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    canonical_entity_ids: tuple[str, ...] = Field(default=(), max_length=100)


class DashboardFixedPeriodBindingV2(StrictDashboardModel):
    period_type: Literal["FIXED"]
    period_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_range(self) -> "DashboardFixedPeriodBindingV2":
        if self.end_date < self.start_date:
            raise ValueError("fixed period end_date cannot precede start_date")
        return self


class DashboardRelativePeriodBindingV2(StrictDashboardModel):
    period_type: Literal["RELATIVE"]
    canonical_period_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    relation: Literal["CURRENT", "PREVIOUS", "ROLLING", "TO_DATE"]
    offset: int = Field(default=0, ge=-120, le=120)


class DashboardInheritedPeriodBindingV2(StrictDashboardModel):
    period_type: Literal["INHERITED_DASHBOARD"]
    source: Literal["DASHBOARD_CONTEXT"] = "DASHBOARD_CONTEXT"


class DashboardFilterDrivenPeriodBindingV2(StrictDashboardModel):
    period_type: Literal["FILTER_DRIVEN"]
    filter_id: str = Field(pattern=CANONICAL_ID_PATTERN)


DashboardPeriodBindingV2 = Annotated[
    Union[
        DashboardFixedPeriodBindingV2,
        DashboardRelativePeriodBindingV2,
        DashboardInheritedPeriodBindingV2,
        DashboardFilterDrivenPeriodBindingV2,
    ],
    Field(discriminator="period_type"),
]


class DashboardComparisonBindingV2(StrictDashboardModel):
    current_period: DashboardPeriodBindingV2
    baseline_period: DashboardPeriodBindingV2
    relationship: Literal[
        "PERIOD_OVER_PERIOD",
        "YEAR_OVER_YEAR",
        "ACTUAL_VS_TARGET",
        "ENTITY_VS_ENTITY",
    ]
    display_delta_absolute: bool = True
    display_percentage: bool = True
    zero_baseline_policy: Literal["NOT_APPLICABLE", "ABSOLUTE_ONLY", "ERROR"] = (
        "NOT_APPLICABLE"
    )
    direction_semantics: Literal[
        "HIGHER_IS_BETTER",
        "LOWER_IS_BETTER",
        "NEUTRAL",
        "METRIC_REGISTRY",
    ] = "METRIC_REGISTRY"

    @model_validator(mode="after")
    def validate_distinct_periods(self) -> "DashboardComparisonBindingV2":
        if self.current_period == self.baseline_period:
            raise ValueError("comparison current and baseline periods must be distinct")
        return self


class DashboardFilterBindingV2(StrictDashboardModel):
    filter_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    target_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    required: bool = False


class DashboardDataBindingV2(StrictDashboardModel):
    binding_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    analytical_dataset_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    metrics: tuple[DashboardMetricBindingV2, ...] = Field(default=(), max_length=12)
    dimensions: tuple[DashboardDimensionBindingV2, ...] = Field(default=(), max_length=12)
    entities: tuple[DashboardEntityBindingV2, ...] = Field(default=(), max_length=12)
    period: DashboardPeriodBindingV2
    comparison: DashboardComparisonBindingV2 | None = None
    filters: tuple[DashboardFilterBindingV2, ...] = Field(default=(), max_length=32)
    expected_result_shape: DashboardResultShapeV2
    completeness: DashboardCompletenessRequirementV2 = (
        DashboardCompletenessRequirementV2.COMPLETE
    )
    freshness: DashboardFreshnessRequirementV2 = (
        DashboardFreshnessRequirementV2.BACKEND_POLICY
    )
    provenance: DashboardProvenanceRequirementV2 = Field(
        default_factory=DashboardProvenanceRequirementV2
    )
    classification: DashboardClassificationV2 = (
        DashboardClassificationV2.TENANT_BUSINESS_DATA
    )
    cache_preference: DashboardCachePreferenceV2 = (
        DashboardCachePreferenceV2.BACKEND_DECIDES
    )
    materialization_preference: DashboardMaterializationPreferenceV2 = (
        DashboardMaterializationPreferenceV2.BACKEND_DECIDES
    )

    @model_validator(mode="after")
    def validate_binding(self) -> "DashboardDataBindingV2":
        if self.classification in {
            DashboardClassificationV2.SECRET,
            DashboardClassificationV2.FORBIDDEN,
        }:
            raise ValueError("SECRET and FORBIDDEN data bindings are prohibited")
        metric_ids = [item.metric_id for item in self.metrics]
        dimension_ids = [item.dimension_id for item in self.dimensions]
        if len(metric_ids) != len(set(metric_ids)):
            raise ValueError("metric bindings must be unique")
        if len(dimension_ids) != len(set(dimension_ids)):
            raise ValueError("dimension bindings must be unique")
        if self.expected_result_shape in {
            DashboardResultShapeV2.SCALAR,
            DashboardResultShapeV2.COMPARISON,
            DashboardResultShapeV2.TIME_SERIES,
            DashboardResultShapeV2.GROUPED_SERIES,
            DashboardResultShapeV2.RANKING,
        } and not self.metrics:
            raise ValueError("analytical result shape requires at least one metric")
        if self.expected_result_shape is DashboardResultShapeV2.COMPARISON and self.comparison is None:
            raise ValueError("COMPARISON result shape requires comparison binding")
        return self

