from __future__ import annotations

import json
from pathlib import Path

import pytest


pytestmark = pytest.mark.no_database
GOLDEN = Path(__file__).resolve().parent / "golden" / "enterprise_knowledge_v2.json"


def test_enterprise_knowledge_golden_is_complete_and_deterministic() -> None:
    raw = GOLDEN.read_text(encoding="utf-8")
    payload = json.loads(raw)
    assert sorted(payload) == [
        "approval",
        "asset_draft",
        "binding_conflict",
        "binding_valid",
        "deprecation",
        "export",
        "forbidden_write",
        "import_dry_run",
        "public_read",
        "publication",
        "rejection",
        "rollback",
        "search_alias",
        "search_ambiguous",
        "search_exact",
        "submitted",
        "version_diff",
        "version_history",
    ]
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    assert raw == rendered
    assert payload["asset_draft"]["schema_version"] == "lumina.enterprise-knowledge/1.0"
    assert payload["forbidden_write"]["role"] == "CONSULTA"
    assert payload["search_ambiguous"]["selected"] is None
