"""Migration v22: governed dashboard persistence and immutable history.

The module has no import-time writes.  Both directions are guarded and only
certified against the disposable PostgreSQL test target. It intentionally
uses explicit individual-table DDL rather than the application metadata bootstrap.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import text

from database import engine
from models.dashboard_backend_v2 import (
    DashboardAccessPolicyModelV2,
    DashboardActivePublicationModelV2,
    DashboardApprovalModelV2,
    DashboardAuditEventModelV2,
    DashboardCollaboratorModelV2,
    DashboardEvaluationCaseModelV2,
    DashboardEvaluationResultModelV2,
    DashboardModelV2,
    DashboardPublicationModelV2,
    DashboardRevisionModelV2,
    DashboardReviewModelV2,
    DashboardRuntimeExecutionModelV2,
    DashboardWidgetExecutionModelV2,
)
from models.user import User as _RegisteredUserModel
from testing.database_guard import guard_engine_before_write


MIGRATION_NAME = "v22_0_governed_dashboard_backend"
TABLES = [
    "dashboards_v2",
    "dashboard_revisions_v2",
    "dashboard_reviews_v2",
    "dashboard_approvals_v2",
    "dashboard_publications_v2",
    "dashboard_active_publications_v2",
    "dashboard_collaborators_v2",
    "dashboard_access_policies_v2",
    "dashboard_audit_events_v2",
    "dashboard_runtime_executions_v2",
    "dashboard_widget_executions_v2",
    "dashboard_evaluation_cases_v2",
    "dashboard_evaluation_results_v2",
]
MODEL_TABLES = [
    DashboardModelV2.__table__,
    DashboardRevisionModelV2.__table__,
    DashboardReviewModelV2.__table__,
    DashboardApprovalModelV2.__table__,
    DashboardPublicationModelV2.__table__,
    DashboardActivePublicationModelV2.__table__,
    DashboardCollaboratorModelV2.__table__,
    DashboardAccessPolicyModelV2.__table__,
    DashboardAuditEventModelV2.__table__,
    DashboardRuntimeExecutionModelV2.__table__,
    DashboardWidgetExecutionModelV2.__table__,
    DashboardEvaluationCaseModelV2.__table__,
    DashboardEvaluationResultModelV2.__table__,
]

IMMUTABLE_TABLES = (
    "dashboard_revisions_v2",
    "dashboard_reviews_v2",
    "dashboard_approvals_v2",
    "dashboard_publications_v2",
    "dashboard_audit_events_v2",
)

TRIGGER_STATEMENTS = tuple(
    statement
    for table_name in IMMUTABLE_TABLES
    for statement in (
        f"DROP TRIGGER IF EXISTS trg_{table_name}_immutable ON {table_name}",
        f"""
        CREATE TRIGGER trg_{table_name}_immutable
        BEFORE UPDATE OR DELETE ON {table_name}
        FOR EACH ROW EXECUTE FUNCTION dashboard_v2_reject_mutation()
        """,
    )
)

IMMUTABILITY_STATEMENTS = (
    """
    DO $$ BEGIN
        ALTER TABLE dashboards_v2
        ADD CONSTRAINT fk_dashboards_v2_head_revision
        FOREIGN KEY (head_revision_id, id, tenant_id)
        REFERENCES dashboard_revisions_v2(id, dashboard_id, tenant_id)
        ON DELETE RESTRICT;
    EXCEPTION WHEN duplicate_object THEN NULL;
    END $$;
    """,
    """
    CREATE OR REPLACE FUNCTION dashboard_v2_reject_mutation()
    RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION 'governed dashboard history is immutable';
    END;
    $$;
    """,
    *TRIGGER_STATEMENTS,
)


async def run_up(*, statements: Sequence[str] | None = None) -> dict[str, Any]:
    """Create the additive schema on the guarded connected test target."""
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
    """Drop only v22 objects after explicit disposable-test confirmation."""
    if not confirm_test_only:
        raise RuntimeError("v22 down is restricted to a disposable test database")
    await guard_engine_before_write(engine)
    async with engine.begin() as connection:
        await connection.execute(text("ALTER TABLE IF EXISTS dashboards_v2 DROP CONSTRAINT IF EXISTS fk_dashboards_v2_head_revision"))
        for table in reversed(MODEL_TABLES):
            await connection.run_sync(lambda sync_connection, target=table: target.drop(sync_connection, checkfirst=True))
        await connection.execute(text("DROP FUNCTION IF EXISTS dashboard_v2_reject_mutation()"))
    return {"status": "SUCCESS", "migration": f"{MIGRATION_NAME}_down", "tables_dropped": TABLES}
