"""Integration tests for post-sync insights v2 in disposable PostgreSQL database."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import uuid
import pytest

from database import engine, get_db_context
from contracts.post_sync_insights_v2 import (
    PostSyncInsightRunRequestV2,
)
from services.post_sync_insights_v2 import (
    post_sync_insights_service,
    user_state_service,
)
from testing.database_guard import guard_engine_before_write

from testing.test_database import ADMIN_A, TENANT_A

ROOT = Path(__file__).resolve().parents[1]


def _load_v24():
    path = ROOT / "database" / "migration_v24_0.py"
    spec = importlib.util.spec_from_file_location("mig_v24_postgresql_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_full_pipeline_and_user_state():
    await guard_engine_before_write(engine)

    # Ensure v24 tables exist
    v24 = _load_v24()
    await v24.run_up()

    tenant_id = str(TENANT_A)
    sync_run_id = str(uuid.uuid4())
    user_id = str(ADMIN_A)

    async with get_db_context() as db:
        # 1. Run pipeline
        req = PostSyncInsightRunRequestV2(
            tenant_id=tenant_id,
            sync_run_id=sync_run_id,
            watermark="2026-08-06T12:00:00Z",
            reconciliation_status="SUCCESS",
        )
        res = await post_sync_insights_service.run_post_sync_pipeline(
            db, req, {"current_value": "400.00", "baseline_value": "300.00"}
        )
        assert res.run.status == "PUBLISHED" or res.run.status.value == "PUBLISHED"
        assert len(res.published_insights) > 0

        first_insight = res.published_insights[0]

        # 2. Acknowledge
        ack = await user_state_service.acknowledge_insight(
            db, tenant_id=tenant_id, user_id=user_id,
            insight_id=first_insight.insight_id, note="Ciente do aumento"
        )
        assert ack.insight_id == first_insight.insight_id

        # 3. Dismiss
        dsm = await user_state_service.dismiss_insight(
            db, tenant_id=tenant_id, user_id=user_id,
            insight_id=first_insight.insight_id, reason="NOT_RELEVANT"
        )
        assert dsm.insight_id == first_insight.insight_id

        # 4. Detail check
        detail = await post_sync_insights_service.get_insight_detail(
            db, tenant_id=tenant_id, insight_id=first_insight.insight_id, user_id=user_id
        )
        assert detail.user_acknowledgement is not None
        assert detail.user_dismissal is not None
