"""Migration v23: governed dashboard AI proposals and immutable history."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import text

from database import engine
from models.dashboard_ai_assistance_v2 import (
    DashboardAiAuditEventModelV2,
    DashboardAiClarificationModelV2,
    DashboardAiDecisionModelV2,
    DashboardAiEvaluationCaseModelV2,
    DashboardAiEvaluationResultModelV2,
    DashboardAiEvidenceModelV2,
    DashboardAiProposalModelV2,
    DashboardAiProposalVersionModelV2,
    DashboardAiRunModelV2,
)
from models.dashboard_backend_v2 import DashboardModelV2 as _RegisteredDashboardModel
from models.user import User as _RegisteredUserModel
from testing.database_guard import guard_engine_before_write

MIGRATION_NAME = "v23_0_dashboard_ai_assistance"
TABLES = [
    "dashboard_ai_proposals_v2", "dashboard_ai_proposal_versions_v2",
    "dashboard_ai_clarifications_v2", "dashboard_ai_evidence_v2",
    "dashboard_ai_decisions_v2", "dashboard_ai_runs_v2",
    "dashboard_ai_audit_events_v2", "dashboard_ai_evaluation_cases_v2",
    "dashboard_ai_evaluation_results_v2",
]
MODEL_TABLES = [
    DashboardAiProposalModelV2.__table__, DashboardAiProposalVersionModelV2.__table__,
    DashboardAiClarificationModelV2.__table__, DashboardAiEvidenceModelV2.__table__,
    DashboardAiDecisionModelV2.__table__, DashboardAiRunModelV2.__table__,
    DashboardAiAuditEventModelV2.__table__, DashboardAiEvaluationCaseModelV2.__table__,
    DashboardAiEvaluationResultModelV2.__table__,
]
IMMUTABLE_TABLES = (
    "dashboard_ai_proposal_versions_v2", "dashboard_ai_evidence_v2",
    "dashboard_ai_decisions_v2", "dashboard_ai_audit_events_v2",
    "dashboard_ai_evaluation_results_v2",
)
IMMUTABILITY_STATEMENTS = (
    """
    CREATE OR REPLACE FUNCTION dashboard_ai_v2_reject_mutation()
    RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION 'governed dashboard AI history is immutable';
    END;
    $$;
    """,
    *(statement for table_name in IMMUTABLE_TABLES for statement in (
        f"DROP TRIGGER IF EXISTS trg_{table_name}_immutable ON {table_name}",
        f"CREATE TRIGGER trg_{table_name}_immutable BEFORE UPDATE OR DELETE ON {table_name} FOR EACH ROW EXECUTE FUNCTION dashboard_ai_v2_reject_mutation()",
    )),
)


async def run_up(*, statements: Sequence[str] | None = None) -> dict[str, Any]:
    await guard_engine_before_write(engine)
    async with engine.begin() as connection:
        if statements is not None:
            for statement in statements:
                await connection.execute(text(statement))
        else:
            for table in MODEL_TABLES:
                await connection.run_sync(lambda sync_connection, target=table: target.create(sync_connection, checkfirst=True))
            for statement in IMMUTABILITY_STATEMENTS:
                await connection.execute(text(statement))
    return {"status": "SUCCESS", "migration": MIGRATION_NAME, "tables_affected": TABLES}


async def run_down(*, confirm_test_only: bool = False) -> dict[str, Any]:
    if not confirm_test_only:
        raise RuntimeError("v23 down is restricted to a disposable test database")
    await guard_engine_before_write(engine)
    async with engine.begin() as connection:
        for table in reversed(MODEL_TABLES):
            await connection.run_sync(lambda sync_connection, target=table: target.drop(sync_connection, checkfirst=True))
        await connection.execute(text("DROP FUNCTION IF EXISTS dashboard_ai_v2_reject_mutation()"))
    return {"status": "SUCCESS", "migration": f"{MIGRATION_NAME}_down", "tables_dropped": TABLES}
