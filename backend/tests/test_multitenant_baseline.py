from __future__ import annotations

import pytest
from sqlalchemy import select

from database import AsyncSessionLocal
from models.dashboard_preference import DashboardPreference
from models.view_catalog import ViewCatalog
from services.cache_service import IntelligentCachingPlatform
from testing.test_database import ADMIN_A, ADMIN_B, TENANT_A, TENANT_B


@pytest.mark.unit
@pytest.mark.multitenant
@pytest.mark.no_database
def test_cache_keys_are_isolated_by_tenant() -> None:
    cache = IntelligentCachingPlatform()
    cache.set(TENANT_A, "query", "same-question", {"value": 300})
    cache.set(TENANT_B, "query", "same-question", {"value": 900})
    assert cache.get(TENANT_A, "query", "same-question") == {"value": 300}
    assert cache.get(TENANT_B, "query", "same-question") == {"value": 900}
    cache.clear_tenant(TENANT_A)
    assert cache.get(TENANT_A, "query", "same-question") is None
    assert cache.get(TENANT_B, "query", "same-question") == {"value": 900}


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.multitenant
@pytest.mark.asyncio
async def test_catalog_and_preferences_are_isolated_by_tenant() -> None:
    async with AsyncSessionLocal() as session:
        session.add_all(
            [
                DashboardPreference(
                    tenant_id=TENANT_A,
                    user_id=ADMIN_A,
                    scope="sales",
                    basis="liquido",
                    format="tabela",
                    instructions="tenant-a",
                ),
                DashboardPreference(
                    tenant_id=TENANT_B,
                    user_id=ADMIN_B,
                    scope="sales",
                    basis="bruto",
                    format="grafico",
                    instructions="tenant-b",
                ),
            ]
        )
        await session.commit()

        catalog_a = (
            await session.execute(
                select(ViewCatalog).where(ViewCatalog.tenant_id == TENANT_A)
            )
        ).scalars().all()
        catalog_b = (
            await session.execute(
                select(ViewCatalog).where(ViewCatalog.tenant_id == TENANT_B)
            )
        ).scalars().all()
        preference_a = (
            await session.execute(
                select(DashboardPreference).where(
                    DashboardPreference.tenant_id == TENANT_A,
                    DashboardPreference.user_id == ADMIN_A,
                )
            )
        ).scalar_one()
        preference_b = (
            await session.execute(
                select(DashboardPreference).where(
                    DashboardPreference.tenant_id == TENANT_B,
                    DashboardPreference.user_id == ADMIN_B,
                )
            )
        ).scalar_one()

    assert {item.nome_view_oracle for item in catalog_a} == {
        "VW_VENDAS_LM",
        "VW_PERFORMANCE_VENDEDORES",
    }
    assert {item.nome_view_oracle for item in catalog_b} == {"VW_VENDAS_LM"}
    assert preference_a.instructions == "tenant-a"
    assert preference_b.instructions == "tenant-b"
