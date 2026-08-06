from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


pytestmark = pytest.mark.no_database
ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "export_dashboard_ai_assistance_v2_contracts.py"


def _module():
    spec = importlib.util.spec_from_file_location("prompt22_exporter", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_schema_and_golden_exports_are_reproducible_and_complete(tmp_path: Path) -> None:
    exporter = _module()
    exporter.SCHEMAS = tmp_path / "schemas.json"
    exporter.GOLDENS = tmp_path / "goldens.json"
    first = exporter.export()
    first_schema = exporter.SCHEMAS.read_bytes()
    first_golden = exporter.GOLDENS.read_bytes()
    second = exporter.export()
    assert first == second
    assert first_schema == exporter.SCHEMAS.read_bytes()
    assert first_golden == exporter.GOLDENS.read_bytes()
    schemas = json.loads(first_schema)
    goldens = json.loads(first_golden)
    assert schemas["contract_version"] == "lumina.dashboard-ai-assistance/1.0"
    assert schemas["schema_count"] >= 35
    assert len(goldens) == 23
    assert set(goldens) == set(exporter.golden_cases())
    lowered = first_golden.decode("utf-8").lower()
    for forbidden in ("select *", "postgresql://", "oracle://", "password", "credential"):
        assert forbidden not in lowered
