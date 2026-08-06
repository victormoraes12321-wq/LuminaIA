"""Root Dashboard Blueprint V2 contract and cross-contract invariants."""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .bindings import DashboardDataBindingV2
from .filters import DashboardFilterGroupV2, DashboardFilterScopeV2, DashboardFilterV2
from .identity import (
    DashboardAudienceV2,
    DashboardClassificationV2,
    DashboardCompatibilityV2,
    DashboardGovernanceV2,
    DashboardIdentityV2,
    DashboardLifecycleV2,
    DashboardOriginV2,
    DashboardPurposeV2,
    DashboardVersionV2,
    StrictDashboardModel,
)
from .interactions import DashboardCrossFilterV2, DashboardInteractionV2
from .layout import DashboardLayoutV2
from .presentation import (
    DashboardAccessibilityV2,
    DashboardRefreshPolicyV2,
)
from .widgets import DashboardWidgetV2


_CLASSIFICATION_RANK = {
    DashboardClassificationV2.PUBLIC_METADATA: 0,
    DashboardClassificationV2.TENANT_METADATA: 1,
    DashboardClassificationV2.TENANT_BUSINESS_DATA: 2,
    DashboardClassificationV2.RESTRICTED_BUSINESS_DATA: 3,
    DashboardClassificationV2.PERSONAL_DATA: 4,
    DashboardClassificationV2.SENSITIVE_PERSONAL_DATA: 5,
    DashboardClassificationV2.SECRET: 6,
    DashboardClassificationV2.FORBIDDEN: 7,
}


class DashboardBlueprintV2(StrictDashboardModel):
    version: DashboardVersionV2 = Field(default_factory=DashboardVersionV2)
    identity: DashboardIdentityV2
    purpose: DashboardPurposeV2
    lifecycle: DashboardLifecycleV2 = DashboardLifecycleV2.DRAFT
    created_origin: DashboardOriginV2
    audience: DashboardAudienceV2
    governance: DashboardGovernanceV2
    layout: DashboardLayoutV2
    widgets: tuple[DashboardWidgetV2, ...] = Field(min_length=1, max_length=64)
    data_bindings: tuple[DashboardDataBindingV2, ...] = Field(default=(), max_length=64)
    filters: tuple[DashboardFilterV2, ...] = Field(default=(), max_length=32)
    filter_groups: tuple[DashboardFilterGroupV2, ...] = Field(default=(), max_length=16)
    interactions: tuple[DashboardInteractionV2, ...] = Field(default=(), max_length=128)
    accessibility: DashboardAccessibilityV2
    refresh_policy: DashboardRefreshPolicyV2 = DashboardRefreshPolicyV2.MANUAL
    compatibility: DashboardCompatibilityV2 = Field(default_factory=DashboardCompatibilityV2)
    checksum: None = None
    contract_state: Literal["CONTRACT_ONLY"] = "CONTRACT_ONLY"

    @model_validator(mode="after")
    def validate_references_and_authority(self) -> "DashboardBlueprintV2":
        widget_ids = [widget.identity.widget_id for widget in self.widgets]
        binding_ids = [binding.binding_id for binding in self.data_bindings]
        filter_ids = [dashboard_filter.filter_id for dashboard_filter in self.filters]
        interaction_ids = [interaction.interaction_id for interaction in self.interactions]
        for values, label in (
            (widget_ids, "widget"),
            (binding_ids, "data binding"),
            (filter_ids, "filter"),
            (interaction_ids, "interaction"),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {label} IDs are not allowed")

        widget_set = set(widget_ids)
        binding_map = {binding.binding_id: binding for binding in self.data_bindings}
        filter_set = set(filter_ids)
        for widget in self.widgets:
            if widget.binding_id is not None:
                if widget.binding_id not in binding_map:
                    raise ValueError(f"widget {widget.identity.widget_id} references unknown binding")
                expected = getattr(widget, "expected_result_shape", None)
                if expected is not None and binding_map[widget.binding_id].expected_result_shape != expected:
                    raise ValueError(
                        f"widget {widget.identity.widget_id} is incompatible with binding result shape"
                    )
                if not binding_map[widget.binding_id].provenance.public_summary_required:
                    raise ValueError("analytical widgets require public provenance")
            if hasattr(widget, "filter_ids"):
                unknown = set(widget.filter_ids) - filter_set
                if unknown:
                    raise ValueError(f"filter panel references unknown filters: {sorted(unknown)}")

        for binding in self.data_bindings:
            if _CLASSIFICATION_RANK[binding.classification] > _CLASSIFICATION_RANK[
                self.governance.classification
            ]:
                raise ValueError("dashboard classification cannot downgrade a data binding")
            unknown_filters = {item.filter_id for item in binding.filters} - filter_set
            if unknown_filters:
                raise ValueError(f"binding references unknown filters: {sorted(unknown_filters)}")

        for dashboard_filter in self.filters:
            unknown_targets = set(dashboard_filter.target_widget_ids) - widget_set
            if unknown_targets:
                raise ValueError(f"filter references unknown widgets: {sorted(unknown_targets)}")
            if (
                dashboard_filter.scope is DashboardFilterScopeV2.DASHBOARD_GLOBAL
                and not dashboard_filter.target_widget_ids
            ):
                raise ValueError("dashboard-global filter must declare compatible target widgets")

        for group in self.filter_groups:
            if not set(group.filter_ids).issubset(filter_set):
                raise ValueError("filter group references unknown filter")

        cross_filter_graph: dict[str, set[str]] = {widget_id: set() for widget_id in widget_ids}
        for interaction in self.interactions:
            if interaction.source_widget_id not in widget_set:
                raise ValueError("interaction source widget does not exist")
            if isinstance(interaction, DashboardCrossFilterV2):
                targets = set(interaction.target_widget_ids)
                if not targets.issubset(widget_set):
                    raise ValueError("cross-filter target widget does not exist")
                if interaction.target_filter_id not in filter_set:
                    raise ValueError("cross-filter target filter does not exist")
                if interaction.source_widget_id in targets:
                    raise ValueError("cross-filter cannot target its source widget")
                cross_filter_graph[interaction.source_widget_id].update(targets)

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> None:
            if node in visiting:
                raise ValueError("cyclic cross-filter graph is prohibited")
            if node in visited:
                return
            visiting.add(node)
            for target in cross_filter_graph[node]:
                visit(target)
            visiting.remove(node)
            visited.add(node)

        for widget_id in widget_ids:
            visit(widget_id)

        expected_reading_order = tuple(widget_ids)
        if self.accessibility.reading_order != expected_reading_order:
            raise ValueError("accessible reading order must match semantic widget order")
        for breakpoint in self.layout.breakpoints:
            placed_ids = {item.widget_id for item in breakpoint.items if item.visible}
            if placed_ids != widget_set:
                raise ValueError("every widget must be placed visibly in every breakpoint")
            ordered_ids = tuple(
                item.widget_id
                for item in sorted(breakpoint.items, key=lambda item: item.reading_order)
                if item.visible
            )
            if ordered_ids != expected_reading_order:
                raise ValueError("visual layout must preserve accessible reading order")
        return self

