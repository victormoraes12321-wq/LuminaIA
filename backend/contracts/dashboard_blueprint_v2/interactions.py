"""Closed dashboard interaction, cross-filter, drilldown, and navigation contracts."""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from .identity import CANONICAL_ID_PATTERN, DashboardCapabilityV2, StrictDashboardModel


class DashboardInteractionBaseV2(StrictDashboardModel):
    interaction_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    source_widget_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    enabled: bool = True


class DashboardCrossFilterV2(DashboardInteractionBaseV2):
    interaction_type: Literal["CROSS_FILTER"]
    source_dimension_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    target_widget_ids: tuple[str, ...] = Field(min_length=1, max_length=32)
    target_filter_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    propagation_mode: Literal["DIRECT", "DASHBOARD_GLOBAL"] = "DIRECT"
    clear_behavior: Literal["CLEAR_ON_DESELECT", "PERSIST_UNTIL_RESET"] = (
        "CLEAR_ON_DESELECT"
    )


class DashboardDrilldownV2(DashboardInteractionBaseV2):
    interaction_type: Literal["DRILLDOWN"]
    source_dimension_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    target_dimension_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    hierarchy_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    target_dashboard_id: str | None = Field(default=None, pattern=CANONICAL_ID_PATTERN)
    permission_requirement: DashboardCapabilityV2 = DashboardCapabilityV2.DRILLDOWN
    fallback: Literal["DISABLE", "SHOW_MESSAGE", "OPEN_TABLE"] = "SHOW_MESSAGE"


class DashboardResetFiltersV2(DashboardInteractionBaseV2):
    interaction_type: Literal["RESET_FILTERS"]
    target_filter_ids: tuple[str, ...] = Field(default=(), max_length=32)


class DashboardOpenProvenanceV2(DashboardInteractionBaseV2):
    interaction_type: Literal["OPEN_PROVENANCE"]
    permission_requirement: DashboardCapabilityV2 = DashboardCapabilityV2.VIEW_PROVENANCE


class DashboardNavigationParameterV2(StrictDashboardModel):
    parameter_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    source_binding_id: str = Field(pattern=CANONICAL_ID_PATTERN)


class DashboardInternalNavigationV2(DashboardInteractionBaseV2):
    interaction_type: Literal["INTERNAL_NAVIGATION"]
    route_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    dashboard_reference: str = Field(pattern=CANONICAL_ID_PATTERN)
    parameters: tuple[DashboardNavigationParameterV2, ...] = Field(default=(), max_length=12)


class DashboardExpandWidgetV2(DashboardInteractionBaseV2):
    interaction_type: Literal["EXPAND_WIDGET"]
    mode: Literal["FULLSCREEN", "DETAIL_PANEL"] = "FULLSCREEN"


class DashboardSortInteractionV2(DashboardInteractionBaseV2):
    interaction_type: Literal["SORT"]
    allowed_sort_ids: tuple[str, ...] = Field(min_length=1, max_length=12)


class DashboardPaginateInteractionV2(DashboardInteractionBaseV2):
    interaction_type: Literal["PAGINATE"]
    page_size_options: tuple[int, ...] = Field(default=(10, 25, 50), min_length=1, max_length=5)


DashboardInteractionV2 = Annotated[
    Union[
        DashboardCrossFilterV2,
        DashboardDrilldownV2,
        DashboardResetFiltersV2,
        DashboardOpenProvenanceV2,
        DashboardInternalNavigationV2,
        DashboardExpandWidgetV2,
        DashboardSortInteractionV2,
        DashboardPaginateInteractionV2,
    ],
    Field(discriminator="interaction_type"),
]

