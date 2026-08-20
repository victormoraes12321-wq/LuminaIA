from __future__ import annotations

import copy
import json

import pytest

from contracts.dashboard_blueprint_v2 import (
    DashboardSemanticPatchV2,
    DashboardValidationStatusV2,
    DashboardVisualPatchV2,
)
from services.dashboard_blueprint_v2.fixtures import build_minimal_dashboard, golden_cases
from services.dashboard_blueprint_v2.legacy_adapter import LegacyDashboardBlueprintAdapter
from services.dashboard_blueprint_v2.validation_service import (
    DashboardBlueprintValidationService,
    DashboardPatchValidator,
)


pytestmark = [pytest.mark.unit, pytest.mark.no_database, pytest.mark.security]


def payload() -> dict[str, object]:
    return build_minimal_dashboard().model_dump(mode="json")


@pytest.mark.parametrize(
    "unsafe_value",
    [
        "<script>alert(1)</script>",
        "<iframe src='x'>",
        "javascript:alert(1)",
        "data:text/html:payload",
        "onclick=alert(1)",
        "expression(alert(1))",
        "select secret from users",
        "x; drop table users",
        "postgresql://user:secret@host/db",
        "../../etc/passwd",
        "C:\\Windows\\system.ini",
        "{{ unsafe_template }}",
        "${unsafe_template}",
        "import os",
        "eval(payload)",
        "rm -rf workspace",
        "https://untrusted.example.invalid/payload",
        "control\x00character",
    ],
)
def test_untrusted_executable_or_external_content_is_blocked(unsafe_value: str) -> None:
    candidate = payload()
    candidate["identity"]["title"] = unsafe_value
    result = DashboardBlueprintValidationService.validate_payload(candidate)
    assert result.status is DashboardValidationStatusV2.BLOCKED
    assert result.canonicalization is None
    assert any(issue.blocking for issue in result.issues)


def test_non_json_payload_is_blocked() -> None:
    result = DashboardBlueprintValidationService.validate_payload({"value": {object()}})
    assert result.status is DashboardValidationStatusV2.BLOCKED
    assert {issue.code for issue in result.issues} == {"PAYLOAD_NOT_JSON"}


def test_excessive_depth_is_blocked() -> None:
    candidate: dict[str, object] = {}
    cursor = candidate
    for _ in range(22):
        nested: dict[str, object] = {}
        cursor["nested"] = nested
        cursor = nested
    result = DashboardBlueprintValidationService.validate_payload(candidate)
    assert result.status is DashboardValidationStatusV2.BLOCKED
    assert "PAYLOAD_TOO_DEEP" in {issue.code for issue in result.issues}


def test_excessive_size_is_blocked() -> None:
    result = DashboardBlueprintValidationService.validate_payload({"value": "x" * 1_000_001})
    assert result.status is DashboardValidationStatusV2.BLOCKED
    assert "PAYLOAD_TOO_LARGE" in {issue.code for issue in result.issues}


def test_unknown_major_version_is_reported_without_repair() -> None:
    candidate = payload()
    candidate["version"]["contract_version"] = "lumina.dashboard-blueprint/3.0"
    result = DashboardBlueprintValidationService.validate_payload(candidate)
    assert result.status is DashboardValidationStatusV2.UNSUPPORTED_VERSION
    assert result.canonicalization is None


@pytest.mark.parametrize("field", ["accessibility", "layout", "governance", "identity"])
def test_missing_required_section_is_invalid(field: str) -> None:
    candidate = payload()
    del candidate[field]
    result = DashboardBlueprintValidationService.validate_payload(candidate)
    assert result.status is DashboardValidationStatusV2.INVALID
    assert result.canonicalization is None


def test_valid_blueprint_completes_all_stages_and_gets_checksums() -> None:
    result = DashboardBlueprintValidationService.validate_payload(payload())
    assert result.status is DashboardValidationStatusV2.VALID
    assert result.canonicalization is not None
    assert len(result.completed_stages) == 17
    assert len(result.canonicalization.checksums.blueprint_checksum) == 64


def test_visual_patch_accepts_only_visual_paths() -> None:
    cases = golden_cases()
    valid = DashboardVisualPatchV2.model_validate_json(
        json.dumps(cases["12_valid_visual_patch"]["payload"], ensure_ascii=False)
    )
    invalid = DashboardVisualPatchV2.model_validate_json(
        json.dumps(cases["13_visual_patch_metric_blocked"]["payload"], ensure_ascii=False)
    )
    assert DashboardPatchValidator.validate_visual(valid) == ()
    issues = DashboardPatchValidator.validate_visual(invalid)
    assert {issue.code for issue in issues} == {"VISUAL_PATCH_SEMANTIC_MUTATION"}


def test_semantic_patch_accepts_governed_semantic_path() -> None:
    case = golden_cases()["14_valid_semantic_patch"]
    patch = DashboardSemanticPatchV2.model_validate_json(
        json.dumps(case["payload"], ensure_ascii=False)
    )
    assert DashboardPatchValidator.validate_semantic(patch) == ()


def test_legacy_adapter_is_pure_and_never_persists() -> None:
    legacy = {"name": "Legacy synthetic", "components": [{"id": "one", "type": "KPI_CARD"}]}
    original = copy.deepcopy(legacy)
    result = LegacyDashboardBlueprintAdapter.adapt(legacy)
    assert result.status.value == "COMPLETE_WITH_WARNINGS"
    assert result.proposal is not None
    assert result.original_unchanged is True
    assert legacy == original


def test_legacy_adapter_refuses_payload_without_components() -> None:
    result = LegacyDashboardBlueprintAdapter.adapt({"name": "empty"})
    assert result.status.value == "UNSUPPORTED"
    assert result.proposal is None
