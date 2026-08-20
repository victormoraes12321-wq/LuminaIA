from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from config import settings
from main import app
from services.auth_service import create_access_token
from testing.test_database import CONSULTA_A, CONSULTA_B, TENANT_A, TENANT_B


def token(*, user_id: uuid.UUID, tenant_id: uuid.UUID, role: str = "CONSULTA") -> str:
    return create_access_token(
        {
            "sub": user_id,
            "tenant_id": tenant_id,
            "role": role,
            "must_change_password": False,
        }
    )


def headers(*, user_id=CONSULTA_A, tenant_id=TENANT_A) -> dict[str, str]:
    return {
        "Authorization": "Bearer "
        + token(user_id=user_id, tenant_id=tenant_id)
    }


def presentation_payload() -> dict[str, object]:
    return {
        "preference_key": "display.presentation",
        "content": {
            "kind": "PRESENTATION",
            "preferred_visualization": "BAR_CHART",
            "table_first": True,
            "table_density": "COMPACT",
            "page_size": 50,
            "decimal_places": 2,
            "ordering": "DEFAULT",
            "chart_granularity": "AUTO",
            "theme": "SYSTEM",
        },
        "origin": "USER_EXPLICIT",
    }


@pytest.mark.asyncio
async def test_profile_api_requires_authentication_and_respects_rollout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/api/v2/me/analytical-profile")
        assert response.status_code == 401

        monkeypatch.setattr(settings, "USER_ANALYTICAL_PROFILE_MODE", "LEGACY_ONLY")
        response = await client.get(
            "/api/v2/me/analytical-profile",
            headers=headers(),
        )
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "USER_PROFILE_FEATURE_DISABLED"

        capabilities = await client.get(
            "/api/v2/me/analytical-profile/capabilities",
            headers=headers(),
        )
        assert capabilities.status_code == 200
        assert capabilities.json()["mode"] == "LEGACY_ONLY"


@pytest.mark.asyncio
async def test_own_profile_crud_etag_mass_assignment_and_cross_user_idor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "USER_ANALYTICAL_PROFILE_MODE", "V2_READ_WRITE")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers=headers(),
    ) as client:
        profile = await client.get("/api/v2/me/analytical-profile")
        assert profile.status_code == 200, profile.text
        assert profile.json()["tenant_id"] == str(TENANT_A)
        assert profile.json()["user_id"] == str(CONSULTA_A)
        assert profile.headers["etag"].startswith('W/"profile-')

        created = await client.post("/api/v2/me/preferences", json=presentation_payload())
        assert created.status_code == 201, created.text
        preference_id = created.json()["preference_id"]

        forged = presentation_payload()
        forged["tenant_id"] = str(TENANT_B)
        forged["user_id"] = str(CONSULTA_B)
        forged["checksum"] = "f" * 64
        response = await client.post("/api/v2/me/preferences", json=forged)
        assert response.status_code == 422

        listed = await client.get("/api/v2/me/preferences")
        assert listed.status_code == 200
        assert [item["preference_id"] for item in listed.json()] == [preference_id]

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers=headers(user_id=CONSULTA_B, tenant_id=TENANT_B),
    ) as other:
        hidden = await other.get(f"/api/v2/me/preferences/{preference_id}")
        assert hidden.status_code == 404
        assert hidden.json()["error"]["code"] == "USER_PREFERENCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_profile_api_consent_export_disable_and_deletion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "USER_ANALYTICAL_PROFILE_MODE", "V2_READ_WRITE")
    monkeypatch.setattr(settings, "USER_ANALYTICAL_PROFILE_EXPORT_ENABLED", True)
    monkeypatch.setattr(settings, "USER_ANALYTICAL_PROFILE_DELETION_ENABLED", True)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers=headers(),
    ) as client:
        default = await client.post(
            "/api/v2/me/preferences",
            json={
                "preference_key": "default.limit",
                "content": {
                    "kind": "ANALYTICAL_DEFAULT",
                    "target_field": "limit",
                    "canonical_id": "top_25",
                    "display_label": "25 itens",
                    "limit": 25,
                },
                "origin": "USER_EXPLICIT",
            },
        )
        assert default.status_code == 201, default.text
        item = default.json()
        granted = await client.post(
            f"/api/v2/me/preferences/{item['preference_id']}/consent",
            json={
                "expected_preference_lock_version": item["lock_version"],
                "purpose": "Aplicar limite quando não houver limite explícito.",
                "scope": "limit",
                "policy_version": "user-profile-consent/1.0",
            },
        )
        assert granted.status_code == 200, granted.text
        revoked = await client.request(
            "DELETE",
            f"/api/v2/me/preferences/{item['preference_id']}/consent",
            json={"expected_lock_version": granted.json()["lock_version"]},
        )
        assert revoked.status_code == 200
        assert revoked.json()["status"] == "REVOKED"

        exported = await client.get("/api/v2/me/profile/export")
        assert exported.status_code == 200
        assert exported.json()["profile"]["user_id"] == str(CONSULTA_A)
        assert "password" not in exported.text

        profile = await client.get("/api/v2/me/analytical-profile")
        disabled = await client.post(
            "/api/v2/me/analytical-profile/disable",
            json={"expected_lock_version": profile.json()["lock_version"]},
        )
        assert disabled.status_code == 200
        assert disabled.json()["status"] == "DISABLED"

        deletion = await client.post(
            "/api/v2/me/analytical-profile/deletion-requests",
            headers={"Idempotency-Key": "api-delete-request-001"},
            json={"reason": "Solicitação do titular."},
        )
        assert deletion.status_code == 202, deletion.text
        replay = await client.post(
            "/api/v2/me/analytical-profile/deletion-requests",
            headers={"Idempotency-Key": "api-delete-request-001"},
            json={"reason": "Repetição idempotente."},
        )
        assert replay.status_code == 202
        assert replay.json()["request_id"] == deletion.json()["request_id"]


def test_openapi_contains_additive_profile_routes_without_owner_parameters() -> None:
    paths = app.openapi()["paths"]
    expected = {
        "/api/v2/me/analytical-profile",
        "/api/v2/me/analytical-profile/summary",
        "/api/v2/me/preferences",
        "/api/v2/me/preferences/applicable",
        "/api/v2/me/preferences/{preference_id}",
        "/api/v2/me/profile/export",
        "/api/v2/me/analytical-profile/deletion-requests",
        "/api/v2/me/analytical-profile/import/dry-run",
        "/api/v2/me/analytical-profile/import/confirm",
    }
    assert expected.issubset(paths)
    for path in expected:
        assert "{tenant_id}" not in path
        assert "{user_id}" not in path
