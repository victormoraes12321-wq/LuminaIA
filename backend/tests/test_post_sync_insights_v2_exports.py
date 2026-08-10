"""Test for post-sync insights v2 schema exports and goldens reproducibility.

This test is purely in-process and does not require a database connection.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load_exporter():
    path = ROOT / "scripts" / "export_post_sync_insights_v2_contracts.py"
    spec = importlib.util.spec_from_file_location("export_script", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.no_database
def test_schema_exports_reproducibility():
    exporter = _load_exporter()
    exporter.export_schemas_and_goldens()

    schemas_dir = ROOT / "docs" / "contracts" / "post_sync_insights_v2" / "schemas"
    goldens_dir = ROOT / "docs" / "contracts" / "post_sync_insights_v2" / "goldens"

    assert schemas_dir.exists()
    assert goldens_dir.exists()

    schema_files = list(schemas_dir.glob("*.json"))
    assert len(schema_files) == 9

    hashes_1 = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in schema_files}

    # Re-run export
    exporter.export_schemas_and_goldens()
    hashes_2 = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in schema_files}

    assert hashes_1 == hashes_2


@pytest.mark.no_database
def test_schema_exports_have_expected_models():
    exporter = _load_exporter()
    exporter.export_schemas_and_goldens()

    schemas_dir = ROOT / "docs" / "contracts" / "post_sync_insights_v2" / "schemas"
    schema_names = {f.stem for f in schemas_dir.glob("*.json")}

    expected_models = {
        "PostSyncInsightPolicyV2",
        "PostSyncInsightRunRequestV2",
        "PostSyncInsightCandidateV2",
        "PostSyncInsightV2",
        "PostSyncInsightEvidenceV2",
        "PostSyncInsightRunV2",
        "PostSyncInsightRunResultV2",
        "PostSyncInsightListItemV2",
        "PostSyncInsightDetailV2",
    }
    assert schema_names == expected_models


@pytest.mark.no_database
def test_golden_default_policy_exists():
    exporter = _load_exporter()
    exporter.export_schemas_and_goldens()

    goldens_dir = ROOT / "docs" / "contracts" / "post_sync_insights_v2" / "goldens"
    golden_policy = goldens_dir / "DefaultPolicyGoldenV2.json"
    assert golden_policy.exists()

    import json
    data = json.loads(golden_policy.read_text(encoding="utf-8"))
    assert data.get("contract_version") == "lumina.post-sync-insights/1.0"
    assert data.get("enabled") is True
