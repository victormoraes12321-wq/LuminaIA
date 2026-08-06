"""Strict side-chat envelopes for lumina.dashboard-ui-sidechat/1.0.

This module extends the existing query surface; it does not create an endpoint,
authority, persistence model, SQL path or AI dashboard generator.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from contracts.dashboard_blueprint_v2 import DashboardPatchOperationV2


DASHBOARD_UI_SIDECHAT_CONTRACT_VERSION = "lumina.dashboard-ui-sidechat/1.0"
ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.:-]{2,127}$"
CHECKSUM_PATTERN = r"^[a-f0-9]{64}$"


class StrictDashboardSideChatModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


DashboardContextValue = str | int | float | bool


class DashboardSideChatFilterContextV2(StrictDashboardSideChatModel):
    filter_id: str = Field(pattern=ID_PATTERN)
    values: tuple[DashboardContextValue, ...] = Field(default=(), max_length=100)


class DashboardSideChatSelectionContextV2(StrictDashboardSideChatModel):
    dimension_id: str = Field(pattern=ID_PATTERN)
    canonical_value: str = Field(min_length=1, max_length=240)


class DashboardSideChatContextV2(StrictDashboardSideChatModel):
    contract_version: Literal["lumina.dashboard-ui-sidechat/1.0"] = DASHBOARD_UI_SIDECHAT_CONTRACT_VERSION
    dashboard_id: str = Field(pattern=ID_PATTERN)
    publication_id: str | None = Field(default=None, pattern=ID_PATTERN)
    revision_id: str = Field(pattern=ID_PATTERN)
    blueprint_semantic_checksum: str = Field(pattern=CHECKSUM_PATTERN)
    visible_widget_ids: tuple[str, ...] = Field(default=(), max_length=64)
    selected_widget_id: str | None = Field(default=None, pattern=ID_PATTERN)
    binding_ids: tuple[str, ...] = Field(default=(), max_length=64)
    metric_ids: tuple[str, ...] = Field(default=(), max_length=64)
    dimension_ids: tuple[str, ...] = Field(default=(), max_length=64)
    effective_period: str | None = Field(default=None, max_length=240)
    filters: tuple[DashboardSideChatFilterContextV2, ...] = Field(default=(), max_length=32)
    selection: DashboardSideChatSelectionContextV2 | None = None
    public_provenance_references: tuple[str, ...] = Field(default=(), max_length=64)
    certification_references: tuple[str, ...] = Field(default=(), max_length=64)
    conversation_session_id: str = Field(pattern=ID_PATTERN)
    context_version: int = Field(ge=0)


class DashboardNoActionV2(StrictDashboardSideChatModel):
    action_type: Literal["NO_ACTION"]


class DashboardFocusWidgetActionV2(StrictDashboardSideChatModel):
    action_type: Literal["FOCUS_WIDGET"]
    widget_id: str = Field(pattern=ID_PATTERN)


class DashboardOpenProvenanceActionV2(StrictDashboardSideChatModel):
    action_type: Literal["OPEN_PROVENANCE"]
    widget_id: str | None = Field(default=None, pattern=ID_PATTERN)


class DashboardApplyFilterActionV2(StrictDashboardSideChatModel):
    action_type: Literal["APPLY_FILTER"]
    filter_id: str = Field(pattern=ID_PATTERN)
    values: tuple[DashboardContextValue, ...] = Field(min_length=1, max_length=100)


class DashboardResetFiltersActionV2(StrictDashboardSideChatModel):
    action_type: Literal["RESET_FILTERS"]


class DashboardDrilldownActionV2(StrictDashboardSideChatModel):
    action_type: Literal["DRILLDOWN"]
    interaction_id: str = Field(pattern=ID_PATTERN)
    source_widget_id: str = Field(pattern=ID_PATTERN)
    canonical_value: str = Field(min_length=1, max_length=240)


class DashboardVisualActionV2(StrictDashboardSideChatModel):
    action_type: Literal["VISUAL_PATCH_PROPOSAL", "VISUAL_PATCH_APPLY"]
    dashboard_id: str = Field(pattern=ID_PATTERN)
    revision_id: str = Field(pattern=ID_PATTERN)
    semantic_checksum: str = Field(pattern=CHECKSUM_PATTERN)
    operations: tuple[DashboardPatchOperationV2, ...] = Field(min_length=1, max_length=64)
    summary: str = Field(min_length=3, max_length=500)


class DashboardBlockedActionV2(StrictDashboardSideChatModel):
    action_type: Literal["BLOCKED"]
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{2,63}$")
    message: str = Field(min_length=3, max_length=500)


DashboardSideChatActionV2 = Annotated[
    DashboardNoActionV2
    | DashboardFocusWidgetActionV2
    | DashboardOpenProvenanceActionV2
    | DashboardApplyFilterActionV2
    | DashboardResetFiltersActionV2
    | DashboardDrilldownActionV2
    | DashboardVisualActionV2
    | DashboardBlockedActionV2,
    Field(discriminator="action_type"),
]
