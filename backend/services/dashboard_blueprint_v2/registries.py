"""Static widget, feature, and validator metadata registries."""
from __future__ import annotations

from dataclasses import dataclass

from contracts.dashboard_blueprint_v2.bindings import DashboardResultShapeV2
from contracts.dashboard_blueprint_v2.widgets import (
    DashboardAreaChartWidgetV2,
    DashboardBarChartWidgetV2,
    DashboardComparisonKpiWidgetV2,
    DashboardDividerWidgetV2,
    DashboardDonutChartWidgetV2,
    DashboardFilterPanelWidgetV2,
    DashboardKpiWidgetV2,
    DashboardLineChartWidgetV2,
    DashboardPieChartWidgetV2,
    DashboardProgressWidgetV2,
    DashboardProvenanceSummaryWidgetV2,
    DashboardRankingWidgetV2,
    DashboardStackedBarChartWidgetV2,
    DashboardStatusSummaryWidgetV2,
    DashboardTableWidgetV2,
    DashboardTextBlockWidgetV2,
)


@dataclass(frozen=True, slots=True)
class DashboardWidgetRegistryEntryV2:
    widget_type: str
    contract_type: type
    supported_result_shapes: tuple[DashboardResultShapeV2, ...]
    binding_required: bool
    accessibility_required: bool
    maximum_series: int
    compatibility_version: str = "2.0"


@dataclass(frozen=True, slots=True)
class DashboardFeatureRegistryEntryV2:
    feature_id: str
    minimum_contract_version: str
    supported: bool = True


WIDGET_REGISTRY: dict[str, DashboardWidgetRegistryEntryV2] = {
    "KPI": DashboardWidgetRegistryEntryV2(
        "KPI", DashboardKpiWidgetV2,
        (DashboardResultShapeV2.SCALAR, DashboardResultShapeV2.COMPARISON), True, True, 1,
    ),
    "COMPARISON_KPI": DashboardWidgetRegistryEntryV2(
        "COMPARISON_KPI", DashboardComparisonKpiWidgetV2,
        (DashboardResultShapeV2.COMPARISON,), True, True, 1,
    ),
    "LINE_CHART": DashboardWidgetRegistryEntryV2(
        "LINE_CHART", DashboardLineChartWidgetV2,
        (DashboardResultShapeV2.TIME_SERIES, DashboardResultShapeV2.GROUPED_SERIES), True, True, 12,
    ),
    "BAR_CHART": DashboardWidgetRegistryEntryV2(
        "BAR_CHART", DashboardBarChartWidgetV2,
        (DashboardResultShapeV2.GROUPED_SERIES, DashboardResultShapeV2.TIME_SERIES), True, True, 12,
    ),
    "STACKED_BAR_CHART": DashboardWidgetRegistryEntryV2(
        "STACKED_BAR_CHART", DashboardStackedBarChartWidgetV2,
        (DashboardResultShapeV2.GROUPED_SERIES,), True, True, 12,
    ),
    "AREA_CHART": DashboardWidgetRegistryEntryV2(
        "AREA_CHART", DashboardAreaChartWidgetV2,
        (DashboardResultShapeV2.TIME_SERIES, DashboardResultShapeV2.GROUPED_SERIES), True, True, 12,
    ),
    "PIE_CHART": DashboardWidgetRegistryEntryV2(
        "PIE_CHART", DashboardPieChartWidgetV2,
        (DashboardResultShapeV2.GROUPED_SERIES,), True, True, 12,
    ),
    "DONUT_CHART": DashboardWidgetRegistryEntryV2(
        "DONUT_CHART", DashboardDonutChartWidgetV2,
        (DashboardResultShapeV2.GROUPED_SERIES,), True, True, 12,
    ),
    "TABLE": DashboardWidgetRegistryEntryV2(
        "TABLE", DashboardTableWidgetV2,
        (DashboardResultShapeV2.TABLE, DashboardResultShapeV2.FACT_SET), True, True, 0,
    ),
    "RANKING": DashboardWidgetRegistryEntryV2(
        "RANKING", DashboardRankingWidgetV2,
        (DashboardResultShapeV2.RANKING,), True, True, 1,
    ),
    "STATUS_SUMMARY": DashboardWidgetRegistryEntryV2(
        "STATUS_SUMMARY", DashboardStatusSummaryWidgetV2,
        (DashboardResultShapeV2.STATUS_SUMMARY,), True, True, 1,
    ),
    "PROGRESS": DashboardWidgetRegistryEntryV2(
        "PROGRESS", DashboardProgressWidgetV2,
        (DashboardResultShapeV2.COMPARISON,), True, True, 1,
    ),
    "FILTER_PANEL": DashboardWidgetRegistryEntryV2(
        "FILTER_PANEL", DashboardFilterPanelWidgetV2, (), False, True, 0,
    ),
    "TEXT_BLOCK": DashboardWidgetRegistryEntryV2(
        "TEXT_BLOCK", DashboardTextBlockWidgetV2, (), False, True, 0,
    ),
    "DIVIDER": DashboardWidgetRegistryEntryV2(
        "DIVIDER", DashboardDividerWidgetV2, (), False, True, 0,
    ),
    "PROVENANCE_SUMMARY": DashboardWidgetRegistryEntryV2(
        "PROVENANCE_SUMMARY", DashboardProvenanceSummaryWidgetV2, (), False, True, 0,
    ),
}


FEATURE_REGISTRY: dict[str, DashboardFeatureRegistryEntryV2] = {
    feature_id: DashboardFeatureRegistryEntryV2(feature_id, "2.0")
    for feature_id in (
        "visual_patches",
        "semantic_patches",
        "responsive_grid",
        "cross_filter",
        "drilldown",
        "provenance_panel",
        "comparison_widgets",
        "materialization_preference",
        "user_presentation_preference",
        "accessibility_summary",
    )
}


def get_widget_registry_entry(widget_type: str) -> DashboardWidgetRegistryEntryV2:
    try:
        return WIDGET_REGISTRY[widget_type]
    except KeyError as exc:
        raise KeyError(f"unsupported dashboard widget type: {widget_type}") from exc


def get_feature_registry_entry(feature_id: str) -> DashboardFeatureRegistryEntryV2:
    try:
        return FEATURE_REGISTRY[feature_id]
    except KeyError as exc:
        raise KeyError(f"unsupported dashboard feature: {feature_id}") from exc

