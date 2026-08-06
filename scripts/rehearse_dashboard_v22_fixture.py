"""Seed or verify the synthetic v22 backup/restore rehearsal target."""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import sys
import uuid
from pathlib import Path

from sqlalchemy import inspect, text


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from contracts.dashboard_backend_v2 import DashboardCollaboratorCreateRequestV2, DashboardCollaboratorRoleV2, DashboardCreateRequestV2, DashboardPublicationRequestV2
from contracts.dashboard_blueprint_v2 import DashboardOriginV2
from database import AsyncSessionLocal, engine
from services.dashboard_backend_v2.application import DashboardActorContextV2, DashboardAuthoringServiceV2, DashboardPublicationServiceV2, DashboardReviewServiceV2
from services.dashboard_backend_v2.collaboration import DashboardAccessServiceV2
from services.dashboard_backend_v2.integrity import checksum
from services.dashboard_blueprint_v2.fixtures import build_executive_dashboard
from testing.database_guard import guard_engine_before_write
from testing.test_database import ADMIN_A, CONSULTA_A, GESTOR_A, TENANT_A, TECH_ADMIN_A


def _migration():
    spec = importlib.util.spec_from_file_location("migration_v22_backup_rehearsal", BACKEND / "database" / "migration_v22_0.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def _actor(user_id: uuid.UUID, role: str) -> DashboardActorContextV2:
    return DashboardActorContextV2(tenant_id=str(TENANT_A), user_id=str(user_id), global_role=role)


async def _create(session, suffix: str):
    blueprint = build_executive_dashboard()
    identity = blueprint.identity.model_copy(update={"blueprint_id": f"dashboard.backup.{suffix}", "canonical_name": f"dashboard.backup.{suffix}", "title": f"Backup sintético {suffix}"})
    blueprint = blueprint.model_copy(update={"identity": identity})
    return await DashboardAuthoringServiceV2(session).create(actor=_actor(GESTOR_A, "GESTOR"), request=DashboardCreateRequestV2(canonical_name=identity.canonical_name, title=identity.title, description=identity.description, blueprint=blueprint, origin=DashboardOriginV2.HUMAN_AUTHORED, reason="Ensaio sintético de backup v22"), idempotency_key=f"backup-create-{suffix}-0001")


async def seed() -> None:
    await guard_engine_before_write(engine)
    migration = _migration(); await migration.run_up()
    async with engine.begin() as connection:
        names = ", ".join(f'"{name}"' for name in reversed(migration.TABLES))
        await connection.execute(text(f"TRUNCATE TABLE {names} CASCADE"))
    async with AsyncSessionLocal() as session:
        published = await _create(session, "published")
        owner = _actor(GESTOR_A, "GESTOR"); reviewer = _actor(TECH_ADMIN_A, "ADMIN")
        await DashboardReviewServiceV2(session).decide(actor=owner, dashboard_id=published.dashboard.identity.dashboard_id, revision_id=published.revision.revision_id, expected_lock=published.dashboard.lock_version, action="SUBMITTED", comment="Review do ensaio de backup", idempotency_key="backup-review-0001")
        await DashboardReviewServiceV2(session).decide(actor=reviewer, dashboard_id=published.dashboard.identity.dashboard_id, revision_id=published.revision.revision_id, expected_lock=published.dashboard.lock_version + 1, action="APPROVED", comment="Approval do ensaio de backup", idempotency_key="backup-approve-0001")
        await DashboardPublicationServiceV2(session).publish(actor=reviewer, dashboard_id=published.dashboard.identity.dashboard_id, request=DashboardPublicationRequestV2(revision_id=published.revision.revision_id, expected_dashboard_lock_version=published.dashboard.lock_version + 2, expected_active_generation=0, publication_version="1.0.0", confirmation="PUBLISH_APPROVED_REVISION"), idempotency_key="backup-publish-0001")
        await DashboardAccessServiceV2(session).add(actor=_actor(ADMIN_A, "ADMIN"), dashboard_id=published.dashboard.identity.dashboard_id, request=DashboardCollaboratorCreateRequestV2(user_reference=str(CONSULTA_A), role=DashboardCollaboratorRoleV2.VIEWER))
        await _create(session, "draft")
        await session.commit()


async def manifest() -> dict[str, object]:
    migration = _migration()
    result: dict[str, object] = {"tables": {}, "contract_version": "lumina.dashboard-backend/1.0"}
    async with engine.connect() as connection:
        for table_name in migration.TABLES:
            rows = [dict(row) for row in (await connection.execute(text(f'SELECT * FROM "{table_name}" ORDER BY 1'))).mappings().all()]
            result["tables"][table_name] = {"row_count": len(rows), "checksum": checksum(rows)}
        active = (await connection.execute(text("SELECT dashboard_id, publication_id, generation FROM dashboard_active_publications_v2 ORDER BY dashboard_id"))).mappings().all()
        result["active_publications_checksum"] = checksum([dict(row) for row in active])
        result["indexes_valid"] = await connection.run_sync(lambda sync: all(inspect(sync).get_indexes(name) or name == "dashboard_access_policies_v2" for name in migration.TABLES))
    tables = result["tables"]
    result["required_fixture_valid"] = all(tables[name]["row_count"] >= 1 for name in ("dashboards_v2", "dashboard_revisions_v2", "dashboard_approvals_v2", "dashboard_publications_v2", "dashboard_active_publications_v2", "dashboard_collaborators_v2", "dashboard_audit_events_v2"))
    result["manifest_checksum"] = checksum(result)
    return result


async def main(seed_requested: bool) -> None:
    if seed_requested:
        await seed()
    print(json.dumps(await manifest(), sort_keys=True, separators=(",", ":")))
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.seed))
