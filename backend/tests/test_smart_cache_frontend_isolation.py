from __future__ import annotations

from pathlib import Path

import pytest


pytestmark = pytest.mark.no_database
ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


def test_legacy_frontend_has_no_prompt18_page_or_sidebar_link() -> None:
    app_files = list((FRONTEND / "app").rglob("*.tsx")) + list(
        (FRONTEND / "app").rglob("*.ts")
    )
    assert not any(
        "smart_cache" in path.as_posix().lower()
        or "materialization" in path.as_posix().lower()
        for path in app_files
    )
    sidebar = (FRONTEND / "components" / "Sidebar.tsx").read_text(encoding="utf-8")
    assert "smart_cache_materialization" not in sidebar
    assert "MaterializationInspector" not in sidebar
    assert "CacheInspector" not in sidebar


def test_experimental_components_are_inert_and_do_not_fetch() -> None:
    component_dir = FRONTEND / "components" / "cache"
    sources = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(component_dir.glob("*.tsx"))
    )
    assert "fetch(" not in sources
    assert "getApiBase" not in sources
    assert "/api/v2/cache" not in sources
    for forbidden in ("raw_cache_key", "connection_string", "credentials", "binds", "sql_text"):
        assert forbidden not in sources.lower()


def test_frontend_contract_does_not_expose_restricted_payload_fields() -> None:
    source = (FRONTEND / "types" / "smart_cache_materialization.ts").read_text(
        encoding="utf-8"
    ).lower()
    for forbidden in ("raw_cache_key", "connection_string", "sql:", "binds:", "payload_json"):
        assert forbidden not in source
