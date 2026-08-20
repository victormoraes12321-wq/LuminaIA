from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from config import settings
from routers.dashboard_backend_v2 import router


pytestmark = pytest.mark.no_database
BACKEND = Path(__file__).resolve().parents[1]


def _logical_hash(schema: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(schema, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def test_router_declares_expected_versioned_surface() -> None:
    methods = {(route.path, method) for route in router.routes for method in route.methods or ()}
    assert len(router.routes) == 27
    assert ("/api/v2/dashboards", "POST") in methods
    assert ("/api/v2/dashboards/{dashboard_id}/runtime/execute", "POST") in methods
    assert ("/api/v2/dashboards/{dashboard_id}/audit", "GET") in methods


def test_default_settings_fail_closed() -> None:
    assert settings.DASHBOARD_BACKEND_MODE == "LEGACY_ONLY"
    assert settings.DASHBOARD_ADMIN_APIS_ENABLED is False
    assert settings.DASHBOARD_RUNTIME_APIS_ENABLED is False
    assert settings.DASHBOARD_PUBLISHING_ENABLED is False
    assert settings.DASHBOARD_ROLLBACK_ENABLED is False


def test_openapi_default_absent_and_explicit_test_mode_reproducible() -> None:
    clean = os.environ.copy()
    clean.update({"DASHBOARD_BACKEND_MODE": "LEGACY_ONLY", "DASHBOARD_ADMIN_APIS_ENABLED": "false", "DASHBOARD_RUNTIME_APIS_ENABLED": "false"})
    default_script = "import json,main; s=main.app.openapi(); print(json.dumps({'paths':len(s['paths']),'dashboard':sum(p.startswith('/api/v2/dashboards') for p in s['paths'])}))"
    default = json.loads(subprocess.check_output([sys.executable, "-c", default_script], cwd=BACKEND, env=clean, text=True).strip())
    assert default["dashboard"] == 0
    enabled = clean | {"DASHBOARD_BACKEND_MODE": "V2_RUNTIME", "DASHBOARD_ADMIN_APIS_ENABLED": "true", "DASHBOARD_RUNTIME_APIS_ENABLED": "true"}
    enabled_script = "import hashlib,json,main; s=main.app.openapi(); d={k:v for k,v in s['paths'].items() if k.startswith('/api/v2/dashboards')}; raw=json.dumps(d,sort_keys=True,separators=(',',':')); print(json.dumps({'paths':len(d),'ops':sum(len([m for m in v if m in {'get','post','patch','delete'}]) for v in d.values()),'hash':hashlib.sha256(raw.encode()).hexdigest()}))"
    first = json.loads(subprocess.check_output([sys.executable, "-c", enabled_script], cwd=BACKEND, env=enabled, text=True).strip())
    second = json.loads(subprocess.check_output([sys.executable, "-c", enabled_script], cwd=BACKEND, env=enabled, text=True).strip())
    assert first == second
    assert first["paths"] == 22 and first["ops"] == 27


def test_router_schema_contains_no_client_tenant_or_sql_authority() -> None:
    from fastapi import FastAPI
    application = FastAPI()
    application.include_router(router)
    schema = application.openapi()
    serialized = json.dumps(schema, sort_keys=True).lower()
    request_schema_names = {name for name in schema["components"]["schemas"] if name.endswith("RequestV2")}
    for name in request_schema_names:
        properties = schema["components"]["schemas"][name].get("properties", {})
        assert "tenant_id" not in properties
        assert "sql" not in properties
    assert "connection_string" not in serialized

