from __future__ import annotations

import copy
import json

import pytest
from pydantic import ValidationError

from contracts.dashboard_blueprint_v2 import (
    DASHBOARD_BLUEPRINT_CONTRACT_ID,
    DASHBOARD_BLUEPRINT_CONTRACT_VERSION,
    DashboardBlueprintV2,
    DashboardLifecycleV2,
)
from services.dashboard_blueprint_v2.fixtures import (
    build_executive_dashboard,
    build_minimal_dashboard,
)
from services.dashboard_blueprint_v2.registries import (
    FEATURE_REGISTRY,
    WIDGET_REGISTRY,
    get_feature_registry_entry,
    get_widget_registry_entry,
)


pytestmark = [pytest.mark.unit, pytest.mark.no_database]


def payload() -> dict[str, object]:
    return build_minimal_dashboard().model_dump(mode="json")


def parse(candidate: dict[str, object]) -> DashboardBlueprintV2:
    return DashboardBlueprintV2.model_validate_json(json.dumps(candidate, ensure_ascii=False))


def test_contract_identity_and_state_are_explicit() -> None:
    blueprint = build_minimal_dashboard()
    assert blueprint.version.contract_id == DASHBOARD_BLUEPRINT_CONTRACT_ID
    assert blueprint.version.contract_version == DASHBOARD_BLUEPRINT_CONTRACT_VERSION
    assert blueprint.contract_state == "CONTRACT_ONLY"
    assert blueprint.checksum is None


def test_contract_is_deeply_immutable() -> None:
    blueprint = build_minimal_dashboard()
    with pytest.raises(ValidationError):
        blueprint.identity.title = "mutação"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("unknown_root",), True),
        (("tenant_id",), "tenant.client-controlled"),
        (("user_id",), "user.client-controlled"),
        (("permissions",), ["dashboard:publish"]),
        (("cache_key",), "unsafe-client-key"),
    ],
)
def test_root_rejects_unknown_or_server_controlled_fields(path: tuple[str, ...], value: object) -> None:
    candidate = payload()
    candidate[path[0]] = value
    with pytest.raises(ValidationError):
        parse(candidate)


@pytest.mark.parametrize("field", ["identity", "governance", "accessibility", "layout"])
def test_required_governed_sections_cannot_be_omitted(field: str) -> None:
    candidate = payload()
    del candidate[field]
    with pytest.raises(ValidationError):
        parse(candidate)


@pytest.mark.parametrize("lifecycle", [item.value for item in DashboardLifecycleV2])
def test_all_governed_lifecycle_values_are_closed_and_supported(lifecycle: str) -> None:
    candidate = payload()
    candidate["lifecycle"] = lifecycle
    assert parse(candidate).lifecycle.value == lifecycle


def test_unknown_lifecycle_fails_closed() -> None:
    candidate = payload()
    candidate["lifecycle"] = "ACTIVE"
    with pytest.raises(ValidationError):
        parse(candidate)


def test_all_four_breakpoints_and_column_contracts_are_present() -> None:
    blueprint = build_executive_dashboard()
    assert [(item.breakpoint.value, item.grid.columns) for item in blueprint.layout.breakpoints] == [
        ("MOBILE", 4),
        ("TABLET", 8),
        ("DESKTOP", 12),
        ("ULTRAWIDE", 16),
    ]


@pytest.mark.parametrize("breakpoint_index", range(4))
def test_every_widget_is_visible_in_every_breakpoint(breakpoint_index: int) -> None:
    blueprint = build_executive_dashboard()
    widget_ids = {widget.identity.widget_id for widget in blueprint.widgets}
    placed_ids = {
        item.widget_id for item in blueprint.layout.breakpoints[breakpoint_index].items if item.visible
    }
    assert placed_ids == widget_ids


def test_unknown_widget_discriminator_fails_closed() -> None:
    candidate = payload()
    candidate["widgets"][0]["widget_type"] = "PLUGIN_WIDGET"
    with pytest.raises(ValidationError):
        parse(candidate)


def test_widget_binding_result_shape_must_match() -> None:
    candidate = payload()
    candidate["data_bindings"][0]["expected_result_shape"] = "TIME_SERIES"
    with pytest.raises(ValidationError):
        parse(candidate)


def test_duplicate_widget_ids_fail_closed() -> None:
    candidate = build_executive_dashboard().model_dump(mode="json")
    candidate["widgets"][1]["identity"]["widget_id"] = candidate["widgets"][0]["identity"]["widget_id"]
    with pytest.raises(ValidationError):
        parse(candidate)


def test_accessible_reading_order_must_match_semantic_order() -> None:
    candidate = build_executive_dashboard().model_dump(mode="json")
    candidate["accessibility"]["reading_order"] = list(reversed(candidate["accessibility"]["reading_order"]))
    with pytest.raises(ValidationError):
        parse(candidate)


def test_legacy_payload_is_not_mutated_by_contract_construction() -> None:
    candidate = payload()
    original = copy.deepcopy(candidate)
    parse(candidate)
    assert candidate == original


def test_registries_are_closed_static_catalogs() -> None:
    assert len(WIDGET_REGISTRY) == 16
    assert len(FEATURE_REGISTRY) == 10
    assert get_widget_registry_entry("KPI").binding_required is True
    assert get_feature_registry_entry("responsive_grid").supported is True
    with pytest.raises(KeyError):
        get_widget_registry_entry("DYNAMIC_IMPORT")
    with pytest.raises(KeyError):
        get_feature_registry_entry("runtime_plugin")
