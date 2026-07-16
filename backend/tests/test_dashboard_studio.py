from __future__ import annotations

from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio

from main import app


BASE_URL = "http://testserver/api/v1"
ADMIN_EMAIL = "admin@luminaai.demo"
ADMIN_PASSWORD = "AdminLumina@2026"
ADMIN_PASSWORD_READY = "NewAdminLumina@2026"


@pytest_asyncio.fixture
async def studio_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
        login = await client.post(
            "/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        token = login.json()["access_token"]
        await client.post(
            "/auth/change-password",
            json={"old_password": ADMIN_PASSWORD, "new_password": ADMIN_PASSWORD_READY},
            headers={"Authorization": f"Bearer {token}"},
        )
        ready = await client.post(
            "/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD_READY},
        )
        client.headers.update({"Authorization": f"Bearer {ready.json()['access_token']}"})
        yield client


def _overlaps(a: dict, b: dict) -> bool:
    return not (
        a["x"] + a["w"] <= b["x"]
        or b["x"] + b["w"] <= a["x"]
        or a["y"] + a["h"] <= b["y"]
        or b["y"] + b["h"] <= a["y"]
    )


async def _create_template(client: AsyncClient) -> dict:
    payload = {
        "name": "Studio Sales Overview",
        "description": "Visual shell for sales dashboard",
        "category": "COMMERCIAL",
        "grid": {
            "columns": 12,
            "items": [
                {"id": "kpi-revenue", "x": 0, "y": 0, "w": 4, "h": 2},
                {"id": "chart-main", "x": 0, "y": 0, "w": 8, "h": 4},
            ],
        },
        "components": [
            {"id": "kpi-revenue", "type": "KPI", "title": "Revenue"},
            {"id": "chart-main", "type": "BAR", "title": "Main chart"},
        ],
        "theme": {"mode": "corporate", "palette": {"primary": "#14b8a6"}},
    }
    response = await client.post("/dashboard-studio/templates", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio(loop_scope="session")
async def test_dashboard_studio_template_is_visual_only_and_normalizes_grid(studio_client: AsyncClient):
    template = await _create_template(studio_client)
    items = template["grid"]["items"]
    assert template["version"] == 1
    assert template["grid"]["no_overlap"] is True
    assert not _overlaps(items[0], items[1])
    assert template["component_order"] == ["kpi-revenue", "chart-main"]

    bad = await studio_client.patch(
        f"/dashboard-studio/templates/{template['id']}",
        json={"visual_config": {"metrics": ["revenue_total"]}},
    )
    assert bad.status_code == 400
    assert "Campo proibido" in bad.json()["error"]["message"]


@pytest.mark.asyncio(loop_scope="session")
async def test_dashboard_instance_does_not_mutate_template_and_versions_are_created(studio_client: AsyncClient):
    template = await _create_template(studio_client)

    created = await studio_client.post(
        "/dashboard-studio/instances",
        json={
            "template_id": template["id"],
            "name": "My sales cockpit",
            "current_filters": {"data_inicio": "2026-01-01"},
            "panel_positions": {
                "kpi-revenue": {"x": 0, "y": 0, "w": 4, "h": 2},
                "chart-main": {"x": 0, "y": 0, "w": 8, "h": 4},
            },
        },
    )
    assert created.status_code == 201, created.text
    instance = created.json()
    assert instance["version"] == 1
    assert instance["current_filters"]["data_inicio"] == "2026-01-01"

    updated = await studio_client.patch(
        f"/dashboard-studio/instances/{instance['id']}",
        json={
            "layout_override": {
                "grid": {
                    "items": [
                        {"id": "kpi-revenue", "x": 0, "y": 0, "w": 6, "h": 2},
                        {"id": "chart-main", "x": 0, "y": 0, "w": 6, "h": 4},
                    ]
                }
            },
            "description_change": "Resize panels",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["version"] == 2
    override_items = updated.json()["layout_override"]["grid"]["items"]
    assert not _overlaps(override_items[0], override_items[1])

    template_after = await studio_client.get(f"/dashboard-studio/templates/{template['id']}")
    assert template_after.status_code == 200
    assert template_after.json()["version"] == 1
    assert template_after.json()["grid"] == template["grid"]

    versions = await studio_client.get(f"/dashboard-studio/instances/{instance['id']}/versions")
    assert versions.status_code == 200
    assert [row["version"] for row in versions.json()] == [2, 1]


@pytest.mark.asyncio(loop_scope="session")
async def test_dashboard_studio_rollback_duplicate_favorite_export_import(studio_client: AsyncClient):
    template = await _create_template(studio_client)
    update = await studio_client.patch(
        f"/dashboard-studio/templates/{template['id']}",
        json={"theme": {"mode": "dark", "palette": {"primary": "#f59e0b"}}},
    )
    assert update.status_code == 200
    assert update.json()["version"] == 2

    rollback = await studio_client.post(
        f"/dashboard-studio/templates/{template['id']}/versions/1/rollback",
        json={"description": "Restore first layout"},
    )
    assert rollback.status_code == 200, rollback.text
    assert rollback.json()["version"] == 3
    assert rollback.json()["theme"] == template["theme"]

    instance_res = await studio_client.post(
        "/dashboard-studio/instances",
        json={"template_id": template["id"], "name": "Board favorite"},
    )
    assert instance_res.status_code == 201
    instance = instance_res.json()

    favorite = await studio_client.post(
        f"/dashboard-studio/instances/{instance['id']}/favorite",
        json={"is_favorite": True},
    )
    assert favorite.status_code == 200
    assert favorite.json()["is_favorite"] is True
    assert favorite.json()["version"] == 2

    duplicate = await studio_client.post(
        f"/dashboard-studio/instances/{instance['id']}/duplicate",
        json={"name": "Board favorite copy"},
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["name"] == "Board favorite copy"
    assert duplicate.json()["template_id"] == instance["template_id"]
    assert duplicate.json()["is_favorite"] is False

    exported = await studio_client.get(f"/dashboard-studio/templates/{template['id']}/export")
    assert exported.status_code == 200
    assert exported.json()["target_type"] == "TEMPLATE"

    imported = await studio_client.post(
        "/dashboard-studio/import",
        json={
            "target_type": "TEMPLATE",
            "payload": exported.json()["payload"],
            "name_override": "Imported studio layout",
        },
    )
    assert imported.status_code == 201
    assert imported.json()["name"] == "Imported studio layout"


@pytest.mark.asyncio(loop_scope="session")
async def test_dashboard_studio_layout_validation_requires_auth_and_auto_fixes(studio_client: AsyncClient):
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as anonymous:
        blocked = await anonymous.post("/dashboard-studio/validate-layout", json={"grid": {"items": []}})
    assert blocked.status_code == 401

    response = await studio_client.post(
        "/dashboard-studio/validate-layout",
        json={
            "grid": {
                "items": [
                    {"id": "a", "x": 0, "y": 0, "w": 8, "h": 2},
                    {"id": "b", "x": 0, "y": 0, "w": 8, "h": 2},
                ]
            }
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_valid"] is False
    assert body["grid"]["no_overlap"] is True
    assert body["adjustments"]
