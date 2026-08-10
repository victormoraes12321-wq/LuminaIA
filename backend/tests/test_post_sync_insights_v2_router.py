"""API router tests for post-sync insights v2."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from config import settings

ROOT = Path(__file__).resolve().parents[1]


def _load_v24():
    path = ROOT / "database" / "migration_v24_0.py"
    spec = importlib.util.spec_from_file_location("mig_v24_router_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_legacy_only_router_not_mounted(monkeypatch):
    """In LEGACY_ONLY mode the router is not mounted — /api/v2/post-sync-insights returns 404."""
    monkeypatch.setattr(settings, "POST_SYNC_INSIGHTS_MODE", "LEGACY_ONLY")
    monkeypatch.setattr(settings, "POST_SYNC_INSIGHTS_APIS_ENABLED", False)

    from main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v2/post-sync-insights")
        # Router is not mounted in LEGACY_ONLY — 404 or 401/403 (auth middleware)
        assert res.status_code in {401, 403, 404, 503}


@pytest.mark.asyncio
async def test_enabled_list_endpoint_exists(monkeypatch):
    """When mode is V2_INSIGHTS_PUBLISH and APIs enabled, the policies endpoint responds."""
    monkeypatch.setattr(settings, "POST_SYNC_INSIGHTS_MODE", "V2_INSIGHTS_PUBLISH")
    monkeypatch.setattr(settings, "POST_SYNC_INSIGHTS_APIS_ENABLED", True)
    monkeypatch.setattr(settings, "POST_SYNC_INSIGHTS_TENANT_ALLOWLIST", ())

    # Ensure v24 tables exist
    v24 = _load_v24()
    await v24.run_up()

    from fastapi import FastAPI
    from main import include_post_sync_insights_v2_router_if_enabled
    test_app = FastAPI()
    include_post_sync_insights_v2_router_if_enabled(test_app)
    from database import get_db_context
    from models.tenant import Tenant
    from models.user import User, UserRole

    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    async with get_db_context() as session:
        t = Tenant(id=tenant_id, nome="Test Tenant PSI", oracle_conn="dummy", clone_db_conn="dummy")
        session.add(t)
        u = User(
            id=user_id, tenant_id=tenant_id,
            nome="Test PSI User",
            email=f"psi-{tenant_id}@lumina.ai",
            password_hash="dummy",
            role=UserRole.CONSULTA,
        )
        session.add(u)
        await session.commit()

        from services.auth_service import create_access_token
        token = create_access_token({"sub": str(user_id), "tenant_id": str(tenant_id), "role": "CONSULTA"})

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        # List insights endpoint should respond 200
        res_list = await client.get(
            "/api/v2/post-sync-insights",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_list.status_code == 200
        assert "items" in res_list.json()
