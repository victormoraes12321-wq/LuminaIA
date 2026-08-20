from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import delete

from database import AsyncSessionLocal
from models.blueprint import Blueprint
from models.tenant import Tenant
from services.data_platform.blueprint_repository import BlueprintRepository


def _model(
    *,
    intent_id: str,
    view_name: str = "VW_TEST_BLUEPRINT_ENTERPRISE",
    metrics: list[str] | None = None,
    group_by: list[str] | None = None,
    filters: dict | None = None,
    visual: str = "BAR",
):
    return SimpleNamespace(
        intent_id=intent_id,
        version=1,
        nome_consulta="Blueprint Enterprise Test",
        objetivo="Analisar faturamento comercial",
        tipo_analise="AGGREGATION",
        view_catalog_id=None,
        view_name=view_name,
        metrics=metrics or ["receita_total"],
        group_by=group_by or [],
        filters=filters or {"periodo": "MES_ATUAL"},
        visualization_type=visual,
        layout={"components": ["KPI", visual, "TABLE"], "template": "Sales Overview"},
        exemplos_perguntas=["Como foram as vendas do mes?"],
        versionamento=SimpleNamespace(
            dependencias=["receita_total"],
            permissoes=["sales.read"],
            quantidade_utilizacoes=0,
            tempo_acumulado_ms=0.0,
            tempo_ia_acumulado_ms=0.0,
            tokens_economizados=0,
            ultima_utilizacao=None,
        ),
    )


@pytest.fixture
def tenant_ids():
    return uuid.uuid4(), uuid.uuid4()


@pytest.mark.asyncio
async def test_blueprint_repository_creates_enterprise_modules(tenant_ids):
    tenant_id, _ = tenant_ids
    repo = BlueprintRepository()
    intent_id = "TEST_BP_ENTERPRISE_CREATE"

    async with AsyncSessionLocal() as db:
        db.add(Tenant(id=tenant_id, nome="Tenant Blueprint Enterprise"))
        await db.commit()

        try:
            bp = await repo.save_blueprint(tenant_id, _model(intent_id=intent_id), db)
            await db.commit()

            assert bp.version == 1
            assert bp.status == "ACTIVE"
            assert len(bp.fingerprint_hash) == 64
            assert bp.identity["intent_id"] == intent_id
            assert bp.business_intent["indicadores"] == ["receita_total"]
            assert bp.metadata_info["structural_only"] is True
            assert bp.quality_profile["quality_score"] > 0
            assert bp.health_profile["health_score"] > 0
        finally:
            await db.execute(delete(Blueprint).where(Blueprint.tenant_id == tenant_id))
            await db.execute(delete(Tenant).where(Tenant.id == tenant_id))
            await db.commit()


@pytest.mark.asyncio
async def test_blueprint_repository_reuses_same_fingerprint_without_new_version(tenant_ids):
    tenant_id, _ = tenant_ids
    repo = BlueprintRepository()
    intent_id = "TEST_BP_ENTERPRISE_REUSE"

    async with AsyncSessionLocal() as db:
        db.add(Tenant(id=tenant_id, nome="Tenant Blueprint Reuse"))
        await db.commit()
        try:
            bp1 = await repo.save_blueprint(tenant_id, _model(intent_id=intent_id), db)
            bp2 = await repo.save_blueprint(tenant_id, _model(intent_id=intent_id), db)
            await db.commit()

            assert bp1.id == bp2.id
            versions = await repo.get_blueprint_versions(tenant_id, intent_id, db)
            assert len(versions) == 1
            assert versions[0].version == 1
        finally:
            await db.execute(delete(Blueprint).where(Blueprint.tenant_id == tenant_id))
            await db.execute(delete(Tenant).where(Tenant.id == tenant_id))
            await db.commit()


@pytest.mark.asyncio
async def test_blueprint_repository_versions_structural_changes_and_rolls_back(tenant_ids):
    tenant_id, _ = tenant_ids
    repo = BlueprintRepository()
    intent_id = "TEST_BP_ENTERPRISE_VERSION"

    async with AsyncSessionLocal() as db:
        db.add(Tenant(id=tenant_id, nome="Tenant Blueprint Versioning"))
        await db.commit()
        try:
            await repo.save_blueprint(tenant_id, _model(intent_id=intent_id), db)
            changed = _model(intent_id=intent_id, group_by=["vendedor"], visual="BAR")
            bp2 = await repo.save_blueprint(tenant_id, changed, db, reason="add_grouping")
            await db.commit()

            assert bp2.version == 2
            versions = await repo.get_blueprint_versions(tenant_id, intent_id, db)
            assert [bp.version for bp in versions] == [1, 2]
            assert versions[0].status == "SUPERSEDED"
            assert versions[1].status == "ACTIVE"

            rollback = await repo.rollback_blueprint(
                tenant_id,
                intent_id,
                target_version=1,
                db_session=db,
                author="QA",
                reason="restore_previous_strategy",
            )
            await db.commit()

            assert rollback.version == 3
            assert rollback.status == "ACTIVE"
            assert rollback.version_info["rollback_from_version"] == 1
            assert rollback.group_by == []
        finally:
            await db.execute(delete(Blueprint).where(Blueprint.tenant_id == tenant_id))
            await db.execute(delete(Tenant).where(Tenant.id == tenant_id))
            await db.commit()


@pytest.mark.asyncio
async def test_blueprint_repository_marketplace_reuses_structure_cross_tenant(tenant_ids):
    tenant_a, tenant_b = tenant_ids
    repo = BlueprintRepository()
    intent_id = "TEST_BP_ENTERPRISE_MARKETPLACE"

    async with AsyncSessionLocal() as db:
        db.add_all([
            Tenant(id=tenant_a, nome="Tenant Marketplace A"),
            Tenant(id=tenant_b, nome="Tenant Marketplace B"),
        ])
        await db.commit()
        try:
            bp = await repo.save_blueprint(tenant_a, _model(intent_id=intent_id), db)
            await repo.publish_to_marketplace(tenant_a, intent_id, db)
            compatible, score = await repo.find_compatible_blueprint(
                tenant_b,
                _model(intent_id="TEST_BP_ENTERPRISE_MARKETPLACE_B"),
                db,
            )
            await db.commit()

            assert compatible is not None
            assert compatible.id == bp.id
            assert score >= 0.85
            assert compatible.tenant_id == tenant_a
            assert compatible.metadata_info["contains_erp_data"] is False
        finally:
            await db.execute(delete(Blueprint).where(Blueprint.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(Tenant).where(Tenant.id.in_([tenant_a, tenant_b])))
            await db.commit()


@pytest.mark.asyncio
async def test_blueprint_repository_registers_usage_and_observability(tenant_ids):
    tenant_id, _ = tenant_ids
    repo = BlueprintRepository()
    intent_id = "TEST_BP_ENTERPRISE_USAGE"

    async with AsyncSessionLocal() as db:
        db.add(Tenant(id=tenant_id, nome="Tenant Blueprint Usage"))
        await db.commit()
        try:
            await repo.save_blueprint(tenant_id, _model(intent_id=intent_id), db)
            used = await repo.register_usage(
                tenant_id,
                intent_id,
                db,
                execution_time_ms=250.0,
                render_time_ms=80.0,
                tokens_saved=1200,
            )
            metrics = await repo.get_observability_metrics(tenant_id, db)
            await db.commit()

            assert used is not None
            assert used.performance_profile["reuse_count"] == 1
            assert used.performance_profile["tokens_saved"] == 1200
            assert metrics["quantidade_blueprints"] == 1
            assert metrics["quantidade_reutilizacoes"] == 1
            assert metrics["health_score"] > 0
        finally:
            await db.execute(delete(Blueprint).where(Blueprint.tenant_id == tenant_id))
            await db.execute(delete(Tenant).where(Tenant.id == tenant_id))
            await db.commit()
