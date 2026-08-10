"""Tests for Observability V2 router endpoints and feature mode guards."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from config import settings
from main import include_observability_v2_router_if_enabled
from models.user import User, UserRole
from routers.auth import get_current_user
from testing.test_database import ADMIN_A, CONSULTA_A, TENANT_A

pytestmark = pytest.mark.no_database


def test_legacy_only_router_not_mounted():
    app = FastAPI()
    mounted = include_observability_v2_router_if_enabled(app)
    assert not mounted

    client = TestClient(app)
    res = client.get("/api/v2/observability/summary")
    assert res.status_code == 404


def test_enabled_router_endpoints_work(monkeypatch):
    monkeypatch.setattr(settings, "OBSERVABILITY_MODE", "V2_EVALUATIONS")
    monkeypatch.setattr(settings, "OBSERVABILITY_APIS_ENABLED", True)

    app = FastAPI()
    mounted = include_observability_v2_router_if_enabled(app)
    assert mounted

    admin_user = User(id=ADMIN_A, email="admin@lumina.test", role=UserRole.ADMIN, tenant_id=TENANT_A)
    consulta_user = User(id=CONSULTA_A, email="consulta@lumina.test", role=UserRole.CONSULTA, tenant_id=TENANT_A)

    app.dependency_overrides[get_current_user] = lambda: admin_user

    client = TestClient(app)

    res_admin = client.get("/api/v2/observability/summary")
    assert res_admin.status_code == 200
    data = res_admin.json()
    assert data["contract_version"] == "lumina.observability-metrics-evaluations/1.0"
    assert data["mode"] == "V2_EVALUATIONS"

    # Override dependency with consulta user -> 403
    app.dependency_overrides[get_current_user] = lambda: consulta_user
    res_user = client.get("/api/v2/observability/summary")
    assert res_user.status_code == 403


def test_openapi_default_vs_experimental_isolation(monkeypatch):
    import hashlib
    import json

    # Default application: Observability V2 disabled
    app_default = FastAPI()
    include_observability_v2_router_if_enabled(app_default)
    openapi_default = app_default.openapi()
    default_p24_routes = [
        path for path in openapi_default.get("paths", {})
        if path.startswith("/api/v2/observability/") or path.startswith("/api/v2/evaluations/")
    ]
    assert len(default_p24_routes) == 0

    # Experimental application: Observability V2 enabled explicitly
    monkeypatch.setattr(settings, "OBSERVABILITY_MODE", "V2_EVALUATIONS")
    monkeypatch.setattr(settings, "OBSERVABILITY_APIS_ENABLED", True)

    app_experimental = FastAPI()
    mounted = include_observability_v2_router_if_enabled(app_experimental)
    assert mounted is True

    openapi_experimental = app_experimental.openapi()
    experimental_p24_routes = [
        path for path in openapi_experimental.get("paths", {})
        if path.startswith("/api/v2/observability/") or path.startswith("/api/v2/evaluations/")
    ]
    assert len(experimental_p24_routes) > 0
    assert len(experimental_p24_routes) == 10

    default_hash = hashlib.sha256(json.dumps(openapi_default, sort_keys=True).encode()).hexdigest()
    experimental_hash = hashlib.sha256(json.dumps(openapi_experimental, sort_keys=True).encode()).hexdigest()

    assert openapi_default != openapi_experimental
    assert default_hash != experimental_hash
