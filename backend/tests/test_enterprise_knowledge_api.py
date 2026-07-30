from __future__ import annotations

from httpx import ASGITransport, AsyncClient
import pytest

from config import settings
from main import app
from services.auth_service import create_access_token
from testing.test_database import (
    ADMIN_B,
    CONSULTA_A,
    TECH_ADMIN_A,
    TENANT_A,
    TENANT_B,
)


def token(*, user_id, tenant_id, role: str) -> str:
    return create_access_token(
        {
            "sub": user_id,
            "tenant_id": tenant_id,
            "role": role,
            "must_change_password": False,
        }
    )


def term_payload(*, owner_id) -> dict[str, object]:
    return {
        "canonical_key": "faturamento",
        "asset_type": "BUSINESS_TERM",
        "domain": "Vendas",
        "owner_user_id": str(owner_id),
        "accountable_area": "Comercial",
        "steward_label": "Gestão comercial",
        "content": {
            "kind": "BUSINESS_TERM",
            "canonical_name": "faturamento",
            "display_name": "Faturamento",
            "definition": "Receita comercial reconhecida.",
            "domain": "Vendas",
            "short_description": "Receita comercial.",
            "full_description": "Receita comercial reconhecida.",
            "aliases": ["receita de vendas"],
        },
    }


@pytest.mark.asyncio
async def test_v2_api_requires_authentication_and_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/api/v2/enterprise-knowledge/assets")
        assert response.status_code == 401

        monkeypatch.setattr(settings, "ENTERPRISE_KNOWLEDGE_MODE", "LEGACY_ONLY")
        response = await client.get(
            "/api/v2/enterprise-knowledge/assets",
            headers={
                "Authorization": "Bearer "
                + token(user_id=CONSULTA_A, tenant_id=TENANT_A, role="CONSULTA")
            },
        )
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "KNOWLEDGE_FEATURE_DISABLED"


@pytest.mark.asyncio
async def test_consulta_cannot_create_through_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ENTERPRISE_KNOWLEDGE_MODE", "V2_READ_WRITE")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={
            "Authorization": "Bearer "
            + token(user_id=CONSULTA_A, tenant_id=TENANT_A, role="CONSULTA")
        },
    ) as client:
        response = await client.post(
            "/api/v2/enterprise-knowledge/assets",
            json=term_payload(owner_id=CONSULTA_A),
        )
        assert response.status_code == 403, response.text
        assert response.json()["error"]["code"] == "KNOWLEDGE_ACCESS_DENIED"
        response = await client.get("/api/v2/enterprise-knowledge/review-queue")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "KNOWLEDGE_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_api_derives_tenant_from_token_and_blocks_idor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ENTERPRISE_KNOWLEDGE_MODE", "V2_READ_WRITE")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={
            "Authorization": "Bearer "
            + token(user_id=TECH_ADMIN_A, tenant_id=TENANT_A, role="ADMIN")
        },
    ) as client:
        created = await client.post(
            "/api/v2/enterprise-knowledge/assets",
            json=term_payload(owner_id=TECH_ADMIN_A),
        )
        assert created.status_code == 201, created.text
        asset_id = created.json()["asset"]["asset_id"]
        assert created.json()["asset"]["tenant_id"] == str(TENANT_A)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={
            "Authorization": "Bearer "
            + token(user_id=ADMIN_B, tenant_id=TENANT_B, role="ADMIN")
        },
    ) as client:
        response = await client.get(f"/api/v2/enterprise-knowledge/assets/{asset_id}")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "KNOWLEDGE_NOT_FOUND"


def test_openapi_contains_additive_enterprise_knowledge_routes() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    assert "/api/v1/query/" in paths
    assert "/api/v2/enterprise-knowledge/search" in paths
    assert "/api/v2/enterprise-knowledge/published/{canonical_key}" in paths
    assert "/api/v2/enterprise-knowledge/metrics/{canonical_metric_id}" in paths
    assert "/api/v2/enterprise-knowledge/review-queue" in paths
    assert "/api/v2/enterprise-knowledge/assets" in paths
    assert "/api/v2/enterprise-knowledge/assets/{asset_id}/rollback" in paths
    assert "/api/v2/enterprise-knowledge/imports" in paths
