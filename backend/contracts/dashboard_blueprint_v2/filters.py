"""Closed, discriminated dashboard filter contracts."""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import Field, model_validator

from .identity import CANONICAL_ID_PATTERN, StrictDashboardModel


class DashboardFilterScopeV2(str, Enum):
    DASHBOARD_GLOBAL = "DASHBOARD_GLOBAL"
    WIDGET_LOCAL = "WIDGET_LOCAL"
    SECTION = "SECTION"
    INHERITED_CONTEXT = "INHERITED_CONTEXT"


class DashboardFilterDefaultV2(StrictDashboardModel):
    mode: Literal["EXPLICIT", "ALL_ALLOWED", "INHERITED_CONTEXT", "NONE"] = "NONE"
    canonical_values: tuple[str | int | float | bool, ...] = Field(default=(), max_length=100)

    @model_validator(mode="after")
    def validate_default(self) -> "DashboardFilterDefaultV2":
        if self.mode == "EXPLICIT" and not self.canonical_values:
            raise ValueError("explicit filter default requires canonical values")
        if self.mode != "EXPLICIT" and self.canonical_values:
            raise ValueError("only explicit filter defaults may contain values")
        return self


class DashboardFilterBaseV2(StrictDashboardModel):
    filter_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    canonical_target_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    scope: DashboardFilterScopeV2
    target_widget_ids: tuple[str, ...] = Field(default=(), max_length=64)
    section_id: str | None = Field(default=None, pattern=CANONICAL_ID_PATTERN)
    default: DashboardFilterDefaultV2 = Field(default_factory=DashboardFilterDefaultV2)
    required: bool = False
    visible: bool = True
    allowed_source: Literal["USER_SELECTION", "INHERITED_CONTEXT", "GOVERNED_DEFAULT"]
    maximum_selections: int = Field(default=1, ge=1, le=100)
    interaction_behavior: Literal["APPLY_IMMEDIATELY", "APPLY_ON_CONFIRM"] = (
        "APPLY_IMMEDIATELY"
    )
    accessibility_label: str = Field(min_length=2, max_length=160)

    @model_validator(mode="after")
    def validate_scope(self) -> "DashboardFilterBaseV2":
        if self.scope is DashboardFilterScopeV2.WIDGET_LOCAL and not self.target_widget_ids:
            raise ValueError("widget-local filter requires target widgets")
        if self.scope is DashboardFilterScopeV2.SECTION and self.section_id is None:
            raise ValueError("section filter requires section_id")
        if self.scope not in {
            DashboardFilterScopeV2.WIDGET_LOCAL,
            DashboardFilterScopeV2.DASHBOARD_GLOBAL,
        } and self.target_widget_ids:
            raise ValueError("target widgets are not valid for this filter scope")
        return self


class DashboardDateRangeFilterV2(DashboardFilterBaseV2):
    filter_type: Literal["DATE_RANGE"]


class DashboardRelativePeriodFilterV2(DashboardFilterBaseV2):
    filter_type: Literal["RELATIVE_PERIOD"]
    allowed_period_ids: tuple[str, ...] = Field(min_length=1, max_length=24)


class DashboardSingleSelectFilterV2(DashboardFilterBaseV2):
    filter_type: Literal["SINGLE_SELECT"]
    maximum_selections: Literal[1] = 1


class DashboardMultiSelectFilterV2(DashboardFilterBaseV2):
    filter_type: Literal["MULTI_SELECT"]


class DashboardEntitySelectFilterV2(DashboardFilterBaseV2):
    filter_type: Literal["ENTITY_SELECT"]
    entity_type_id: str = Field(pattern=CANONICAL_ID_PATTERN)


class DashboardBooleanFilterV2(DashboardFilterBaseV2):
    filter_type: Literal["BOOLEAN"]
    maximum_selections: Literal[1] = 1


class DashboardNumberRangeFilterV2(DashboardFilterBaseV2):
    filter_type: Literal["NUMBER_RANGE"]
    minimum_allowed: float | None = None
    maximum_allowed: float | None = None

    @model_validator(mode="after")
    def validate_numeric_range(self) -> "DashboardNumberRangeFilterV2":
        if (
            self.minimum_allowed is not None
            and self.maximum_allowed is not None
            and self.minimum_allowed > self.maximum_allowed
        ):
            raise ValueError("minimum numeric filter bound cannot exceed maximum")
        return self


class DashboardStatusSelectFilterV2(DashboardFilterBaseV2):
    filter_type: Literal["STATUS_SELECT"]
    allowed_status_ids: tuple[str, ...] = Field(min_length=1, max_length=50)


class DashboardSearchFilterV2(DashboardFilterBaseV2):
    filter_type: Literal["SEARCH"]
    minimum_query_length: int = Field(default=2, ge=1, le=20)
    maximum_query_length: int = Field(default=120, ge=20, le=240)


DashboardFilterV2 = Annotated[
    Union[
        DashboardDateRangeFilterV2,
        DashboardRelativePeriodFilterV2,
        DashboardSingleSelectFilterV2,
        DashboardMultiSelectFilterV2,
        DashboardEntitySelectFilterV2,
        DashboardBooleanFilterV2,
        DashboardNumberRangeFilterV2,
        DashboardStatusSelectFilterV2,
        DashboardSearchFilterV2,
    ],
    Field(discriminator="filter_type"),
]


class DashboardFilterGroupV2(StrictDashboardModel):
    group_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    operator: Literal["ALL", "ANY"]
    filter_ids: tuple[str, ...] = Field(min_length=1, max_length=16)
    depth: int = Field(default=1, ge=1, le=3)

