from __future__ import annotations

import json

import pytest

from contracts.dashboard_blueprint_v2 import DashboardBlueprintV2
from services.dashboard_blueprint_v2.canonicalizer import DashboardBlueprintCanonicalizer
from services.dashboard_blueprint_v2.fixtures import build_executive_dashboard, build_minimal_dashboard


pytestmark = [pytest.mark.unit, pytest.mark.no_database]


def canonical(payload: dict[str, object]):
    return DashboardBlueprintCanonicalizer.canonicalize(
        DashboardBlueprintV2.model_validate_json(json.dumps(payload, ensure_ascii=False))
    )


def test_canonicalization_is_idempotent() -> None:
    blueprint = build_executive_dashboard()
    first = DashboardBlueprintCanonicalizer.canonicalize(blueprint)
    second = canonical(json.loads(first.canonical_json))
    assert first == second


def test_mapping_key_order_does_not_change_checksum() -> None:
    payload = build_minimal_dashboard().model_dump(mode="json")
    reversed_root = dict(reversed(list(payload.items())))
    assert canonical(payload).checksums == canonical(reversed_root).checksums


def test_unicode_nfc_and_whitespace_are_normalized() -> None:
    first = build_minimal_dashboard().model_dump(mode="json")
    second = build_minimal_dashboard().model_dump(mode="json")
    first["identity"]["title"] = "Receita líquida"
    second["identity"]["title"] = "  Receita   li\u0301quida  "
    assert canonical(first).checksums.blueprint_checksum == canonical(second).checksums.blueprint_checksum


def test_visual_title_change_preserves_semantic_checksum() -> None:
    original = build_minimal_dashboard().model_dump(mode="json")
    changed = build_minimal_dashboard().model_dump(mode="json")
    changed["identity"]["title"] = "Título visual alternativo"
    before = canonical(original).checksums
    after = canonical(changed).checksums
    assert before.semantic_checksum == after.semantic_checksum
    assert before.visual_checksum != after.visual_checksum
    assert before.blueprint_checksum != after.blueprint_checksum


def test_metric_change_changes_semantic_and_blueprint_checksums() -> None:
    original = build_minimal_dashboard().model_dump(mode="json")
    changed = build_minimal_dashboard().model_dump(mode="json")
    changed["data_bindings"][0]["metrics"][0]["metric_id"] = "metric.net.revenue"
    before = canonical(original).checksums
    after = canonical(changed).checksums
    assert before.semantic_checksum != after.semantic_checksum
    assert before.blueprint_checksum != after.blueprint_checksum


def test_list_order_is_semantic_and_is_not_sorted() -> None:
    original = build_executive_dashboard().model_dump(mode="json")
    changed = build_executive_dashboard().model_dump(mode="json")
    original["purpose"]["analytical_domains"] = ["sales", "finance"]
    changed["purpose"]["analytical_domains"] = ["finance", "sales"]
    assert canonical(original).checksums.semantic_checksum != canonical(changed).checksums.semantic_checksum


@pytest.mark.parametrize(
    "checksum_field",
    [
        "blueprint_checksum",
        "semantic_checksum",
        "visual_checksum",
        "layout_checksum",
        "widgets_checksum",
        "bindings_checksum",
        "filters_checksum",
        "interactions_checksum",
        "accessibility_checksum",
    ],
)
def test_every_checksum_is_lowercase_sha256(checksum_field: str) -> None:
    checksums = DashboardBlueprintCanonicalizer.canonicalize(build_minimal_dashboard()).checksums
    value = getattr(checksums, checksum_field)
    assert len(value) == 64
    assert value == value.lower()
    assert set(value) <= set("0123456789abcdef")
