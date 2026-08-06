"""Seed and verify the synthetic Prompt 22 backup/restore rehearsal target."""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import sys
from pathlib import Path

from sqlalchemy import inspect, text


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from contracts.dashboard_ai_assistance_v2 import DashboardAiAssistanceContextV2, DashboardAiAssistanceRequestV2, DashboardAiOperationV2, DashboardAiRequestOriginV2
from database import AsyncSessionLocal, engine
from services.dashboard_ai_assistance_v2.integrity import checksum
from services.dashboard_ai_assistance_v2.service import DashboardAiAssistanceServiceV2
from services.dashboard_backend_v2 import DashboardActorContextV2
from testing.database_guard import guard_engine_before_write
from testing.test_database import GESTOR_A, TENANT_A


def _migration(version: int):
    path = BACKEND / "database" / f"migration_v{version}_0.py"
    spec = importlib.util.spec_from_file_location(f"migration_v{version}_backup_rehearsal", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def seed() -> None:
    await guard_engine_before_write(engine)
    v22, v23 = _migration(22), _migration(23)
    await v22.run_up()
    await v23.run_up()
    async with engine.begin() as connection:
        names = ", ".join(f'"{name}"' for name in reversed(v23.TABLES))
        await connection.execute(text(f"TRUNCATE TABLE {names} CASCADE"))
    actor = DashboardActorContextV2(tenant_id=str(TENANT_A), user_id=str(GESTOR_A), global_role="GESTOR")
    request = DashboardAiAssistanceRequestV2(
        operation=DashboardAiOperationV2.CREATE_DASHBOARD,
        origin=DashboardAiRequestOriginV2.API,
        instruction="Painel sintético de ticket médio em julho",
        context=DashboardAiAssistanceContextV2(),
        client_request_id="request.backup.v23.001",
    )
    async with AsyncSessionLocal() as session:
        await DashboardAiAssistanceServiceV2(session).create(
            actor=actor, request=request, idempotency_key="backup-v23-create-0001"
        )
        await session.commit()


async def manifest() -> dict[str, object]:
    v23 = _migration(23)
    result: dict[str, object] = {"contract_version": "lumina.dashboard-ai-assistance/1.0", "tables": {}}
    async with engine.connect() as connection:
        for table_name in v23.TABLES:
            rows = [dict(row) for row in (await connection.execute(text(f'SELECT * FROM "{table_name}" ORDER BY 1'))).mappings().all()]
            result["tables"][table_name] = {"row_count": len(rows), "checksum": checksum(rows)}
        result["indexes_valid"] = await connection.run_sync(
            lambda sync: all(inspect(sync).get_indexes(name) for name in v23.TABLES)
        )
    result["required_fixture_valid"] = all(
        result["tables"][name]["row_count"] >= 1
        for name in ("dashboard_ai_proposals_v2", "dashboard_ai_proposal_versions_v2", "dashboard_ai_evidence_v2", "dashboard_ai_runs_v2", "dashboard_ai_audit_events_v2")
    )
    result["manifest_checksum"] = checksum(result)
    return result


async def main(seed_requested: bool) -> None:
    if seed_requested:
        await seed()
    print(json.dumps(await manifest(), sort_keys=True, separators=(",", ":"), default=str))
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.seed))
