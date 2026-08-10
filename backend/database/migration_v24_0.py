"""Migration v24: certified post-sync insights and immutable history."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import text

from database import engine
from models.post_sync_insights_v2 import (
    PostSyncInsightAuditEventModelV2,
    PostSyncInsightCandidateModelV2,
    PostSyncInsightDetectorExecutionModelV2,
    PostSyncInsightEvaluationCaseModelV2,
    PostSyncInsightEvaluationResultModelV2,
    PostSyncInsightEvidenceModelV2,
    PostSyncInsightModelV2,
    PostSyncInsightOutboxModelV2,
    PostSyncInsightPolicyModelV2,
    PostSyncInsightRunModelV2,
    PostSyncInsightUserStateModelV2,
)
from models.user import User as _RegisteredUserModel
from testing.database_guard import guard_engine_before_write

MIGRATION_NAME = "v24_0_post_sync_insights"
TABLES = [
    "post_sync_insight_policies_v2", "post_sync_insight_outbox_v2",
    "post_sync_insight_runs_v2", "post_sync_insight_detector_executions_v2",
    "post_sync_insight_candidates_v2", "post_sync_insights_v2",
    "post_sync_insight_evidence_v2", "post_sync_insight_user_states_v2",
    "post_sync_insight_audit_events_v2", "post_sync_insight_evaluation_cases_v2",
    "post_sync_insight_evaluation_results_v2",
]
MODEL_TABLES = [
    PostSyncInsightPolicyModelV2.__table__, PostSyncInsightOutboxModelV2.__table__,
    PostSyncInsightRunModelV2.__table__, PostSyncInsightDetectorExecutionModelV2.__table__,
    PostSyncInsightCandidateModelV2.__table__, PostSyncInsightModelV2.__table__,
    PostSyncInsightEvidenceModelV2.__table__, PostSyncInsightUserStateModelV2.__table__,
    PostSyncInsightAuditEventModelV2.__table__, PostSyncInsightEvaluationCaseModelV2.__table__,
    PostSyncInsightEvaluationResultModelV2.__table__,
]
IMMUTABLE_TABLES = (
    "post_sync_insights_v2", "post_sync_insight_evidence_v2",
    "post_sync_insight_audit_events_v2", "post_sync_insight_evaluation_results_v2",
)
IMMUTABILITY_STATEMENTS = (
    """
    CREATE OR REPLACE FUNCTION post_sync_insights_v2_reject_mutation()
    RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION 'governed post sync insight published history is immutable';
    END;
    $$;
    """,
    *(statement for table_name in IMMUTABLE_TABLES for statement in (
        f"DROP TRIGGER IF EXISTS trg_{table_name}_immutable ON {table_name}",
        f"CREATE TRIGGER trg_{table_name}_immutable BEFORE UPDATE OR DELETE ON {table_name} FOR EACH ROW EXECUTE FUNCTION post_sync_insights_v2_reject_mutation()",
    )),
)


async def run_up(bind=engine, *, tables_to_create: Sequence[Any] | None = None) -> None:
    await guard_engine_before_write(bind)
    async with bind.begin() as conn:
        for table in (MODEL_TABLES if tables_to_create is None else tables_to_create):
            await conn.run_sync(table.create, checkfirst=True)
        for statement in IMMUTABILITY_STATEMENTS:
            await conn.execute(text(statement))


async def run_down(bind=engine, *, tables_to_drop: Sequence[str] | None = None) -> None:
    await guard_engine_before_write(bind)
    async with bind.begin() as conn:
        for table_name in (TABLES if tables_to_drop is None else tables_to_drop):
            await conn.execute(text(f"DROP TRIGGER IF EXISTS trg_{table_name}_immutable ON {table_name}"))
            await conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
        await conn.execute(text("DROP FUNCTION IF EXISTS post_sync_insights_v2_reject_mutation() CASCADE"))
