from __future__ import annotations

import json
from pathlib import Path

import pytest


pytestmark = pytest.mark.no_database
GOLDEN = Path(__file__).resolve().parent / "golden" / "dashboard_backend_v2.json"


EXPECTED = {
    "dashboard_record", "draft", "visual_revision", "semantic_revision", "review", "approval",
    "publication", "supersession", "rollback", "collaborator", "access_denied", "runtime_plan",
    "kpi_result", "comparison_result", "ranking_result", "partial_dashboard", "cache_hit",
    "materialization_hit", "stale_warning", "backup_manifest", "restore_validation", "legacy_dry_run",
    "shadow", "legacy_only",
}


def test_twenty_four_synthetic_goldens_are_complete_and_safe() -> None:
    raw = GOLDEN.read_text(encoding="utf-8")
    payload = json.loads(raw)
    assert set(payload) == EXPECTED
    assert len(payload) == 24
    lowered = raw.lower()
    for forbidden in ("select ", "insert ", "postgresql://", "oracle", "password", "credential"):
        assert forbidden not in lowered


def test_financial_golden_uses_decimal_strings_and_existing_authority_values() -> None:
    comparison = json.loads(GOLDEN.read_text(encoding="utf-8"))["comparison_result"]
    assert comparison == {"baseline": "300.00", "target": "400.00", "delta": "100.00", "percentage": "33.33"}

