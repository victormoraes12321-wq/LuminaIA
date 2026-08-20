from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from contracts.dashboard_blueprint_v2 import (
    DashboardBlueprintV2,
    DashboardSemanticPatchV2,
    DashboardVisualPatchV2,
)
from services.dashboard_blueprint_v2.fixtures import golden_cases
from services.dashboard_blueprint_v2.legacy_adapter import LegacyDashboardBlueprintAdapter
from services.dashboard_blueprint_v2.validation_service import (
    DashboardBlueprintValidationService,
    DashboardPatchValidator,
)


pytestmark = [pytest.mark.unit, pytest.mark.no_database]
ROOT = Path(__file__).resolve().parents[2]
EXPORT_ROOT = ROOT / "docs" / "contracts" / "dashboard_blueprint_v2"


def test_exported_artifact_inventory_is_complete() -> None:
    schemas = sorted((EXPORT_ROOT / "schemas").glob("*.json"))
    goldens = sorted((EXPORT_ROOT / "goldens").glob("*.json"))
    assert len(schemas) == 91
    assert len(goldens) == 20


@pytest.mark.parametrize("path", sorted((EXPORT_ROOT / "schemas").glob("*.json")))
def test_every_exported_schema_is_json_schema(path: Path) -> None:
    schema = json.loads(path.read_text(encoding="utf-8"))
    assert schema.get("title") or schema.get("oneOf")
    assert "type" in schema or "$defs" in schema or "oneOf" in schema


@pytest.mark.parametrize("path", sorted((EXPORT_ROOT / "goldens").glob("*.json")))
def test_every_exported_golden_matches_factory_and_expected_status(path: Path) -> None:
    exported = json.loads(path.read_text(encoding="utf-8"))
    case_name = path.stem
    factory_case = golden_cases()[case_name]
    assert exported == factory_case
    expected = exported["expected"]
    raw = exported["payload"]
    if case_name.startswith("12_"):
        patch = TypeAdapter(DashboardVisualPatchV2).validate_json(json.dumps(raw, ensure_ascii=False))
        actual = "VALID" if not DashboardPatchValidator.validate_visual(patch) else "INVALID"
    elif case_name.startswith("13_"):
        patch = TypeAdapter(DashboardVisualPatchV2).validate_json(json.dumps(raw, ensure_ascii=False))
        actual = "VALID" if not DashboardPatchValidator.validate_visual(patch) else "INVALID"
    elif case_name.startswith("14_"):
        patch = TypeAdapter(DashboardSemanticPatchV2).validate_json(json.dumps(raw, ensure_ascii=False))
        actual = "VALID" if not DashboardPatchValidator.validate_semantic(patch) else "INVALID"
    elif case_name.startswith("19_"):
        actual = LegacyDashboardBlueprintAdapter.adapt(raw).status.value
    else:
        actual = DashboardBlueprintValidationService.validate_payload(raw).status.value
    assert actual == expected


def test_typescript_contract_is_closed_and_runtime_free() -> None:
    source = (ROOT / "frontend" / "types" / "dashboard_blueprint_v2.ts").read_text(encoding="utf-8")
    assert "lumina.dashboard-blueprint/2.0" in source
    assert "export interface DashboardBlueprintV2" in source
    assert " any" not in source
    assert "fetch(" not in source
    assert "axios" not in source
    assert "Record<string" not in source


def test_prompt19_has_no_routes_or_runtime_integration() -> None:
    backend_main = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
    assert "dashboard_blueprint_v2" not in backend_main
    assert not list((ROOT / "backend" / "routers").glob("*dashboard_blueprint_v2*"))
    assert not list((ROOT / "frontend" / "app").rglob("*dashboard-blueprint-v2*"))


def test_root_schema_accepts_minimal_golden() -> None:
    raw = golden_cases()["02_monthly_revenue"]["payload"]
    assert DashboardBlueprintV2.model_validate_json(
        json.dumps(raw, ensure_ascii=False)
    ).contract_state == "CONTRACT_ONLY"
