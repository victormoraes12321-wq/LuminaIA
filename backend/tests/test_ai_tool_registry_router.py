from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from services.auth_service import create_access_token
from testing.test_database import CONSULTA_A, TECH_ADMIN_A, TENANT_A


def headers(user_id=CONSULTA_A, tenant_id=TENANT_A, role: str = "CONSULTA") -> dict[str, str]:
    token = create_access_token(
        data={
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "role": role,
            "must_change_password": False,
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_get_catalog_endpoint() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver", headers=headers()) as client:
        res = await client.get("/api/v2/tools/catalog")
        assert res.status_code == 200
        data = res.json()
        assert "snapshot_version" in data
        assert "items" in data
        assert len(data["items"]) >= 10


@pytest.mark.asyncio
async def test_validate_proposal_endpoint() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver", headers=headers()) as client:
        payload = {
            "tool_id": "lumina.temporal.normalize",
            "arguments": {"expression": "hoje"},
        }
        res = await client.post("/api/v2/tools/validate-proposal", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["is_valid"] is True
        assert data["decision"] == "ALLOWED"


@pytest.mark.asyncio
async def test_invoke_tool_endpoint() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver", headers=headers()) as client:
        payload = {
            "tool_id": "lumina.temporal.normalize",
            "raw_arguments": {"expression": "hoje"},
        }
        res = await client.post("/api/v2/tools/invoke", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["tool_id"] == "lumina.temporal.normalize"
        assert data["result"]["success"] is True


@pytest.mark.asyncio
async def test_admin_list_tools_endpoint() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver", headers=headers(user_id=TECH_ADMIN_A, role="ADMIN")) as client:
        res = await client.get("/api/v2/admin/tools")
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
