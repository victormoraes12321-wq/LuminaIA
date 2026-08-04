from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from contracts.smart_cache_materialization_v2 import CacheStatisticsV2
from routers import smart_cache_materialization as cache_router
from testing.test_database import ADMIN_A, CONSULTA_A, TENANT_A


pytestmark = pytest.mark.no_database


def _user(role: str):
    return SimpleNamespace(
        id=ADMIN_A if role == "ADMIN" else CONSULTA_A,
        tenant_id=TENANT_A,
        role=SimpleNamespace(value=role),
    )


def _app(role: str) -> FastAPI:
    application = FastAPI()
    application.include_router(cache_router.router)

    async def current_user():
        return _user(role)

    async def database_session():
        yield SimpleNamespace()

    application.dependency_overrides[cache_router.get_current_user] = current_user
    application.dependency_overrides[cache_router.get_db] = database_session
    return application


@pytest.mark.asyncio
async def test_admin_statistics_derives_tenant_from_authenticated_user(monkeypatch) -> None:
    from services.smart_cache_materialization import SmartCacheStatisticsService

    observed: list[str] = []

    async def statistics(self, tenant_id: str):
        observed.append(tenant_id)
        return CacheStatisticsV2(tenant_id=tenant_id)

    monkeypatch.setattr(SmartCacheStatisticsService, "get_cache_statistics", statistics)
    async with AsyncClient(transport=ASGITransport(app=_app("ADMIN")), base_url="http://test") as client:
        response = await client.get("/api/v2/cache/statistics")
    assert response.status_code == 200
    assert observed == [str(TENANT_A)]
    assert response.json()["tenant_id"] == str(TENANT_A)


@pytest.mark.asyncio
async def test_consulta_cannot_administer_cache() -> None:
    async with AsyncClient(transport=ASGITransport(app=_app("CONSULTA")), base_url="http://test") as client:
        response = await client.post(
            "/api/v2/cache/invalidate",
            json={
                "invalidation_scope": "PERMISSION",
                "target_identifier": "permission",
                "reason": "permission changed",
            },
        )
    assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("forbidden_field", ["tenant_id", "sql", "raw_cache_key", "connection_string", "rows"])
async def test_command_payload_rejects_authority_and_sensitive_fields(forbidden_field: str) -> None:
    payload = {
        "invalidation_scope": "PERMISSION",
        "target_identifier": "permission",
        "reason": "permission changed",
        forbidden_field: "forbidden",
    }
    async with AsyncClient(transport=ASGITransport(app=_app("ADMIN")), base_url="http://test") as client:
        response = await client.post("/api/v2/cache/invalidate", json=payload)
    assert response.status_code == 422


def test_experimental_openapi_has_only_bounded_governance_operations() -> None:
    schema = _app("ADMIN").openapi()
    paths = set(schema["paths"])
    assert paths == {
        "/api/v2/cache/statistics",
        "/api/v2/cache/invalidate",
        "/api/v2/cache/gc",
        "/api/v2/cache/materialization/publish",
        "/api/v2/cache/materialization/rollback",
    }
    serialized = str(schema).lower()
    for forbidden in ("raw_cache_key", "connection_string", "result_rows", "force_hit"):
        assert forbidden not in serialized


def test_role_permission_matrix_is_fail_closed() -> None:
    assert cache_router._permissions(_user("CONSULTA")) == set()
    assert "cache:invalidate" in cache_router._permissions(_user("ADMIN"))
    assert "cache:invalidate" not in cache_router._permissions(_user("GESTOR"))
    assert "materialization:publish" not in cache_router._permissions(_user("GESTOR"))
