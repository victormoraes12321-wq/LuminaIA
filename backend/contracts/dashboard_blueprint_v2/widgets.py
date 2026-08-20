"""Discriminated widget contracts for Dashboard Blueprint V2."""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field, model_validator

from .bindings import DashboardResultShapeV2
from .identity import CANONICAL_ID_PATTERN, StrictDashboardModel
from .presentation import (
    DashboardFormattingV2,
    DashboardThemeTokenV2,
    DashboardWidgetAccessibilityV2,
    DashboardWidgetStatesV2,
)


class DashboardWidgetIdentityV2(StrictDashboardModel):
    widget_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    canonical_name: str = Field(pattern=CANONICAL_ID_PATTERN)


class DashboardWidgetTitleV2(StrictDashboardModel):
    title: str = Field(min_length=1, max_length=160)
    subtitle: str | None = Field(default=None, max_length=320)
    visible: bool = True


class DashboardWidgetBaseV2(StrictDashboardModel):
    identity: DashboardWidgetIdentityV2
    title: DashboardWidgetTitleV2
    binding_id: str | None = Field(default=None, pattern=CANONICAL_ID_PATTERN)
    formatting: DashboardFormattingV2 = Field(default_factory=DashboardFormattingV2)
    accessibility: DashboardWidgetAccessibilityV2
    states: DashboardWidgetStatesV2
    theme_token: DashboardThemeTokenV2 = DashboardThemeTokenV2.PRIMARY
    visible: bool = True


class DashboardKpiWidgetV2(DashboardWidgetBaseV2):
    widget_type: Literal["KPI"]
    binding_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    expected_result_shape: Literal[
        DashboardResultShapeV2.SCALAR,
        DashboardResultShapeV2.COMPARISON,
    ]
    unit_display: Literal["AUTO", "SHOW", "HIDE"] = "AUTO"
    trend_display: Literal["NONE", "DIRECTION", "SPARKLINE_REFERENCE"] = "NONE"


class DashboardComparisonKpiWidgetV2(DashboardWidgetBaseV2):
    widget_type: Literal["COMPARISON_KPI"]
    binding_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    expected_result_shape: Literal[DashboardResultShapeV2.COMPARISON]
    delta_absolute_display: bool = True
    percentage_display: bool = True
    zero_denominator_presentation: Literal["NOT_APPLICABLE", "ABSOLUTE_ONLY", "ERROR"]
    direction_semantics_visible: bool = True


class DashboardChartSeriesV2(StrictDashboardModel):
    series_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    metric_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    label: str = Field(min_length=1, max_length=120)
    theme_token: DashboardThemeTokenV2


class DashboardChartAxisV2(StrictDashboardModel):
    binding_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    label: str = Field(min_length=1, max_length=120)
    scale: Literal["LINEAR", "TIME", "CATEGORY"]


class DashboardChartWidgetBaseV2(DashboardWidgetBaseV2):
    binding_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    series: tuple[DashboardChartSeriesV2, ...] = Field(min_length=1, max_length=12)
    category_axis: DashboardChartAxisV2
    value_axis: DashboardChartAxisV2
    sorting: Literal["SOURCE", "ASC", "DESC", "CHRONOLOGICAL"] = "SOURCE"
    maximum_series: int = Field(default=8, ge=1, le=12)
    maximum_points: int = Field(default=500, ge=1, le=2_000)
    legend: Literal["AUTO", "SHOW", "HIDE"] = "AUTO"
    labels: Literal["AUTO", "SHOW", "HIDE"] = "AUTO"
    tooltip_policy: Literal["GOVERNED_SUMMARY", "VALUES_AND_LABELS"] = (
        "VALUES_AND_LABELS"
    )

    @model_validator(mode="after")
    def validate_series_limit(self) -> "DashboardChartWidgetBaseV2":
        if len(self.series) > self.maximum_series:
            raise ValueError("chart series exceed the declared governed maximum")
        return self


class DashboardLineChartWidgetV2(DashboardChartWidgetBaseV2):
    widget_type: Literal["LINE_CHART"]
    expected_result_shape: Literal[
        DashboardResultShapeV2.TIME_SERIES,
        DashboardResultShapeV2.GROUPED_SERIES,
    ]


class DashboardBarChartWidgetV2(DashboardChartWidgetBaseV2):
    widget_type: Literal["BAR_CHART"]
    expected_result_shape: Literal[
        DashboardResultShapeV2.GROUPED_SERIES,
        DashboardResultShapeV2.TIME_SERIES,
    ]


class DashboardStackedBarChartWidgetV2(DashboardChartWidgetBaseV2):
    widget_type: Literal["STACKED_BAR_CHART"]
    expected_result_shape: Literal[DashboardResultShapeV2.GROUPED_SERIES]


class DashboardAreaChartWidgetV2(DashboardChartWidgetBaseV2):
    widget_type: Literal["AREA_CHART"]
    expected_result_shape: Literal[
        DashboardResultShapeV2.TIME_SERIES,
        DashboardResultShapeV2.GROUPED_SERIES,
    ]


class DashboardPieChartWidgetV2(DashboardChartWidgetBaseV2):
    widget_type: Literal["PIE_CHART"]
    expected_result_shape: Literal[DashboardResultShapeV2.GROUPED_SERIES]
    maximum_slices: int = Field(default=8, ge=2, le=12)
    other_slice_policy: Literal["DISABLED", "BACKEND_PROVIDED"] = "BACKEND_PROVIDED"
    complete_result_required: bool = True


class DashboardDonutChartWidgetV2(DashboardPieChartWidgetV2):
    widget_type: Literal["DONUT_CHART"]


class DashboardTableColumnV2(StrictDashboardModel):
    column_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    source_binding_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    column_kind: Literal["METRIC", "DIMENSION", "STATUS"]
    label: str = Field(min_length=1, max_length=120)
    sortable: bool = True
    visible: bool = True


class DashboardTableWidgetV2(DashboardWidgetBaseV2):
    widget_type: Literal["TABLE"]
    binding_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    expected_result_shape: Literal[
        DashboardResultShapeV2.TABLE,
        DashboardResultShapeV2.FACT_SET,
    ]
    columns: tuple[DashboardTableColumnV2, ...] = Field(min_length=1, max_length=32)
    ordering: tuple[str, ...] = Field(default=(), max_length=12)
    maximum_visual_rows: int = Field(default=100, ge=1, le=500)
    pagination_presentation: Literal["PAGED", "VIRTUALIZED", "NONE"] = "PAGED"
    totals_display: bool = False
    subtotals_display: bool = False
    truncation_indicator: Literal["REQUIRED", "NOT_APPLICABLE"] = "REQUIRED"
    responsive_mode: Literal["SCROLL", "STACKED_CARDS", "PRIORITY_COLUMNS"] = "SCROLL"


class DashboardRankingWidgetV2(DashboardWidgetBaseV2):
    widget_type: Literal["RANKING"]
    binding_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    expected_result_shape: Literal[DashboardResultShapeV2.RANKING]
    metric_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    ranking_dimension_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    order_direction: Literal["ASC", "DESC"] = "DESC"
    top_n: int = Field(default=10, ge=1, le=100)
    tie_policy: Literal["INCLUDE_TIES", "STABLE_LIMIT"] = "INCLUDE_TIES"
    other_policy: Literal["DISABLED", "BACKEND_PROVIDED"] = "DISABLED"
    completeness_indicator: bool = True
    rank_display: bool = True


class DashboardStatusSummaryWidgetV2(DashboardWidgetBaseV2):
    widget_type: Literal["STATUS_SUMMARY"]
    binding_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    expected_result_shape: Literal[DashboardResultShapeV2.STATUS_SUMMARY]


class DashboardProgressWidgetV2(DashboardWidgetBaseV2):
    widget_type: Literal["PROGRESS"]
    binding_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    expected_result_shape: Literal[DashboardResultShapeV2.COMPARISON]
    target_source: Literal["BACKEND_CERTIFIED"] = "BACKEND_CERTIFIED"


class DashboardFilterPanelWidgetV2(DashboardWidgetBaseV2):
    widget_type: Literal["FILTER_PANEL"]
    filter_ids: tuple[str, ...] = Field(min_length=1, max_length=32)
    orientation: Literal["HORIZONTAL", "VERTICAL", "RESPONSIVE"] = "RESPONSIVE"


class DashboardInternalLinkV2(StrictDashboardModel):
    label: str = Field(min_length=1, max_length=120)
    route_id: str = Field(pattern=CANONICAL_ID_PATTERN)


class DashboardTextBlockWidgetV2(DashboardWidgetBaseV2):
    widget_type: Literal["TEXT_BLOCK"]
    content_format: Literal["PLAIN_TEXT", "LIMITED_MARKDOWN"] = "PLAIN_TEXT"
    content: str = Field(min_length=1, max_length=4_000)
    internal_links: tuple[DashboardInternalLinkV2, ...] = Field(default=(), max_length=12)


class DashboardDividerWidgetV2(DashboardWidgetBaseV2):
    widget_type: Literal["DIVIDER"]
    orientation: Literal["HORIZONTAL", "VERTICAL"] = "HORIZONTAL"


class DashboardProvenanceSummaryWidgetV2(DashboardWidgetBaseV2):
    widget_type: Literal["PROVENANCE_SUMMARY"]
    display: tuple[
        Literal[
            "SOURCE_FRESHNESS",
            "FILTERS_APPLIED",
            "METRIC_DEFINITION",
            "VALIDATION_STATUS",
            "WARNINGS",
        ],
        ...,
    ] = Field(min_length=1, max_length=5)


DashboardWidgetV2 = Annotated[
    Union[
        DashboardKpiWidgetV2,
        DashboardComparisonKpiWidgetV2,
        DashboardLineChartWidgetV2,
        DashboardBarChartWidgetV2,
        DashboardStackedBarChartWidgetV2,
        DashboardAreaChartWidgetV2,
        DashboardPieChartWidgetV2,
        DashboardDonutChartWidgetV2,
        DashboardTableWidgetV2,
        DashboardRankingWidgetV2,
        DashboardStatusSummaryWidgetV2,
        DashboardProgressWidgetV2,
        DashboardFilterPanelWidgetV2,
        DashboardTextBlockWidgetV2,
        DashboardDividerWidgetV2,
        DashboardProvenanceSummaryWidgetV2,
    ],
    Field(discriminator="widget_type"),
]

