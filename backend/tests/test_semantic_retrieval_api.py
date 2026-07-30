from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from config import settings
from main import app
from models.user import UserRole
from services.auth_service import create_access_token
from services.semantic_retrieval.permissions import permission_fingerprint
from testing.test_database import (
    CONSULTA_A,
    CONSULTA_B,
    TECH_ADMIN_A,
    TENANT_A,
    TENANT_B,
)


def token(*, user_id: uuid.UUID, tenant_id: uuid.UUID, role: str) -> str:
    return create_access_token(
        {
            "sub": user_id,
            "tenant_id": tenant_id,
            "role": role,
            "must_change_password": False,
        }
    )


def headers(
    *,
    user_id: uuid.UUID = TECH_ADMIN_A,
    tenant_id: uuid.UUID = TENANT_A,
    role: str = "ADMIN",
) -> dict[str, str]:
    return {
        "Authorization": "Bearer "
        + token(user_id=user_id, tenant_id=tenant_id, role=role)
    }


def enable_semantic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SEMANTIC_RETRIEVAL_MODE", "HYBRID_READ")
    monkeypatch.setattr(settings, "SEMANTIC_ADMIN_INSPECTOR_ENABLED", True)
    monkeypatch.setattr(settings, "SEMANTIC_RETRIEVAL_FRONTEND_ENABLED", True)


@pytest.mark.asyncio
async def test_capabilities_requires_auth_and_reports_fail_closed_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        unauthenticated = await client.get("/api/v2/semantic/capabilities")
        assert unauthenticated.status_code == 401
        monkeypatch.setattr(settings, "SEMANTIC_RETRIEVAL_MODE", "LEGACY_ONLY")
        response = await client.get(
            "/api/v2/semantic/capabilities", headers=headers()
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["mode"] == "LEGACY_ONLY"
        assert payload["frontend_enabled"] is False
        assert payload["entity_instance_indexing_enabled"] is False
        assert payload["vector_channel_enabled"] is False


@pytest.mark.asyncio
async def test_admin_build_publish_inspect_and_runtime_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_semantic(monkeypatch)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers=headers(),
    ) as client:
        created = await client.post(
            "/api/v2/semantic/admin/indexes/default",
            json={"name": "Indice corporativo de teste"},
        )
        assert created.status_code == 200, created.text
        definition = created.json()
        index_id = definition["index_id"]
        build = await client.post(
            f"/api/v2/semantic/admin/indexes/{index_id}/build",
            json={
                "schema_version": "lumina.semantic-retrieval/1.0",
                "index_id": index_id,
                "expected_definition_lock_version": definition["lock_version"],
                "build_mode": "FULL",
                "idempotency_key": "api-build-0001",
            },
        )
        assert build.status_code == 200, build.text
        built = build.json()
        assert built["version"]["lifecycle"] == "READY"
        assert built["version"]["document_count"] > 0

        published = await client.post(
            f"/api/v2/semantic/admin/indexes/{index_id}/publish",
            json={
                "version_id": built["version"]["version_id"],
                "expected_definition_lock_version": definition["lock_version"],
                "reason": "Certificacao da API",
            },
        )
        assert published.status_code == 200, published.text

        permission = permission_fingerprint(UserRole.ADMIN)
        search_body = {
            "schema_version": "lumina.semantic-retrieval/1.0",
            "query": "faturamento_comercial",
            "index_id": index_id,
            "context": {
                "expected_entity_types": ["METRIC"],
                "expected_domain": None,
                "active_canonical_ids": [],
                "profile_favorite_ids": [],
                "permission_fingerprint": permission,
                "profile_tie_breaker_enabled": False,
            },
            "top_k": 10,
            "include_public_explanation": True,
        }
        inspected = await client.post(
            "/api/v2/semantic/admin/search", json=search_body
        )
        assert inspected.status_code == 200, inspected.text
        assert inspected.json()["candidates"][0]["breakdown"]["channels"]
        candidate_id = inspected.json()["candidates"][0]["document_id"]
        version_id = built["version"]["version_id"]

        version_detail = await client.get(
            f"/api/v2/semantic/admin/indexes/{index_id}/versions/{version_id}"
        )
        assert version_detail.status_code == 200
        manifest = await client.get(
            f"/api/v2/semantic/admin/indexes/{index_id}/versions/{version_id}/manifest"
        )
        assert manifest.status_code == 200
        assert manifest.json()["checksum"] == built["version"]["checksum"]
        stale = await client.get(
            f"/api/v2/semantic/admin/indexes/{index_id}/stale-sources"
        )
        assert stale.status_code == 200
        assert stale.json() == []

        audit = await client.get(
            "/api/v2/semantic/admin/audit", params={"index_id": index_id}
        )
        assert audit.status_code == 200
        event_types = {item["event_type"] for item in audit.json()}
        assert "INDEX_BUILD_STARTED" in event_types
        assert "INDEX_VERSION_PUBLISHED" in event_types

        versions = await client.get(
            f"/api/v2/semantic/admin/indexes/{index_id}/versions"
        )
        assert versions.status_code == 200
        assert versions.json()[0]["lifecycle"] == "PUBLISHED"

    consulta_headers = headers(
        user_id=CONSULTA_A,
        tenant_id=TENANT_A,
        role="CONSULTA",
    )
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers=consulta_headers,
    ) as client:
        search_body["context"]["permission_fingerprint"] = permission_fingerprint(
            UserRole.CONSULTA
        )
        runtime = await client.post("/api/v2/semantic/search", json=search_body)
        assert runtime.status_code == 200, runtime.text
        payload = runtime.json()
        assert payload["decision"] == "RESOLVED"
        assert payload["selected"]["canonical_reference"]["canonical_id"] == (
            "faturamento_comercial"
        )
        assert payload["selected"]["breakdown"]["channels"] == []
        detail = await client.get(
            f"/api/v2/semantic/candidates/{candidate_id}",
            params={"index_id": index_id},
        )
        assert detail.status_code == 200, detail.text
        assert detail.json()["canonical_id"] == "faturamento_comercial"
        assert "checksum" not in detail.json()
        assert "representation" not in detail.json()
        forbidden = await client.get("/api/v2/semantic/admin/indexes")
        assert forbidden.status_code == 403
        assert forbidden.json()["error"]["code"] == "SEMANTIC_INDEX_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_runtime_does_not_enumerate_other_tenant_index(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_semantic(monkeypatch)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers=headers(),
    ) as client:
        created = await client.post(
            "/api/v2/semantic/admin/indexes/default",
            json={"name": "Indice tenant A"},
        )
        assert created.status_code == 200
        foreign_index = created.json()["index_id"]

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers=headers(
            user_id=CONSULTA_B,
            tenant_id=TENANT_B,
            role="CONSULTA",
        ),
    ) as client:
        result = await client.post(
            "/api/v2/semantic/search",
            json={
                "query": "faturamento",
                "index_id": foreign_index,
                "context": {
                    "permission_fingerprint": permission_fingerprint(
                        UserRole.CONSULTA
                    )
                },
            },
        )
        assert result.status_code == 200
        assert result.json()["decision"] == "NOT_FOUND"
        assert result.json()["candidates"] == []


@pytest.mark.asyncio
async def test_semantic_api_rejects_mass_assignment_and_oversized_top_k(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_semantic(monkeypatch)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers=headers(
            user_id=CONSULTA_A,
            tenant_id=TENANT_A,
            role="CONSULTA",
        ),
    ) as client:
        response = await client.post(
            "/api/v2/semantic/search",
            json={
                "query": "faturamento",
                "tenant_id": str(TENANT_B),
                "top_k": 999,
                "context": {
                    "permission_fingerprint": permission_fingerprint(
                        UserRole.CONSULTA
                    )
                },
            },
        )
        assert response.status_code == 422
