from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from config import settings
from routers.dashboard_ai_assistance_v2 import router

pytestmark = pytest.mark.no_database
BACKEND = Path(__file__).resolve().parents[1]


def _run(env: dict[str, str]) -> dict[str, object]:
    script = "import hashlib,json,main; s=main.app.openapi(); raw=json.dumps(s,sort_keys=True,separators=(',',':')); print(json.dumps({'paths':len(s['paths']),'ops':sum(len([m for m in v if m in {'get','post','put','patch','delete'}]) for v in s['paths'].values()),'ai':sum(p.startswith('/api/v2/dashboard-ai') for p in s['paths']),'hash':hashlib.sha256(raw.encode()).hexdigest()}))"
    return json.loads(subprocess.check_output([sys.executable, "-c", script], cwd=BACKEND, env=env, text=True).strip())


def test_router_surface_contains_only_proposal_workflow() -> None:
    methods = {(route.path, method) for route in router.routes for method in route.methods or ()}
    assert len(router.routes) == 12
    assert ("/api/v2/dashboard-ai/proposals", "POST") in methods
    assert ("/api/v2/dashboard-ai/proposals/{proposal_id}/apply", "POST") in methods
    assert ("/api/v2/dashboard-ai/proposals/{proposal_id}/revise", "POST") in methods
    serialized = " ".join(path for path, _ in methods).lower()
    for forbidden in ("publish", "approve", "rollback", "collaborator", "owner", "permission", "sql"):
        assert forbidden not in serialized


def test_default_mode_is_fail_closed() -> None:
    assert settings.DASHBOARD_AI_ASSISTANCE_MODE == "LEGACY_ONLY"
    assert settings.DASHBOARD_AI_APIS_ENABLED is False
    assert settings.DASHBOARD_AI_FRONTEND_ENABLED is False
    assert settings.DASHBOARD_AI_FAKE_PROVIDER_ENABLED is False
    assert settings.DASHBOARD_AI_TENANT_ALLOWLIST == ()


def test_openapi_default_and_experimental_are_reproducible() -> None:
    clean = os.environ.copy()
    clean.update({
        "DASHBOARD_BACKEND_MODE": "LEGACY_ONLY", "DASHBOARD_ADMIN_APIS_ENABLED": "false", "DASHBOARD_RUNTIME_APIS_ENABLED": "false",
        "DASHBOARD_AI_ASSISTANCE_MODE": "LEGACY_ONLY", "DASHBOARD_AI_APIS_ENABLED": "false",
    })
    default_first, default_second = _run(clean), _run(clean)
    assert default_first == default_second
    assert default_first["paths"] == 190 and default_first["ops"] == 216 and default_first["ai"] == 0
    experimental = clean | {
        "DASHBOARD_BACKEND_MODE": "V2_RUNTIME", "DASHBOARD_ADMIN_APIS_ENABLED": "true", "DASHBOARD_RUNTIME_APIS_ENABLED": "true",
        "DASHBOARD_AI_ASSISTANCE_MODE": "AI_ASSISTED_EDIT", "DASHBOARD_AI_APIS_ENABLED": "true",
    }
    enabled_first, enabled_second = _run(experimental), _run(experimental)
    assert enabled_first == enabled_second
    assert enabled_first["paths"] == 223 and enabled_first["ops"] == 255 and enabled_first["ai"] == 11


def test_openapi_requests_have_no_client_tenant_sql_or_permissions() -> None:
    from fastapi import FastAPI
    application = FastAPI(); application.include_router(router)
    schema = application.openapi()
    for name, contract in schema["components"]["schemas"].items():
        if "Request" not in name and "Response" not in name:
            continue
        properties = contract.get("properties", {})
        assert "tenant_id" not in properties
        assert "user_id" not in properties
        assert "sql" not in properties
        assert "permissions" not in properties
