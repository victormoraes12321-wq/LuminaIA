"""Migration v25: governed operational observability, metrics, SLOs, and evaluations."""
from __future__ import annotations

from sqlalchemy import text

from database import engine
from models.observability_v2 import (
    EvaluationRegressionModelV2,
    EvaluationRunModelV2,
    EvaluationSuiteModelV2,
    ObservabilityAuditEventModelV2,
    OperationalMetricRollupModelV2,
    SloDefinitionModelV2,
    SloEvaluationModelV2,
    TraceSummaryModelV2,
)
from testing.database_guard import guard_engine_before_write

MIGRATION_NAME = "v25_0_observability_metrics_evaluations"
TABLES = [
    "operational_metric_rollups_v2",
    "observability_trace_summaries_v2",
    "observability_slo_definitions_v2",
    "observability_slo_evaluations_v2",
    "evaluation_suites_v2",
    "evaluation_runs_v2",
    "evaluation_regressions_v2",
    "observability_audit_events_v2",
]
MODEL_TABLES = [
    OperationalMetricRollupModelV2.__table__,
    TraceSummaryModelV2.__table__,
    SloDefinitionModelV2.__table__,
    SloEvaluationModelV2.__table__,
    EvaluationSuiteModelV2.__table__,
    EvaluationRunModelV2.__table__,
    EvaluationRegressionModelV2.__table__,
    ObservabilityAuditEventModelV2.__table__,
]
IMMUTABLE_TABLES = (
    "evaluation_runs_v2",
    "evaluation_regressions_v2",
    "observability_audit_events_v2",
)
IMMUTABILITY_STATEMENTS = (
    """
    CREATE OR REPLACE FUNCTION observability_v2_reject_mutation()
    RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION 'governed observability certified history is immutable';
    END;
    $$;
    """,
    *(statement for table_name in IMMUTABLE_TABLES for statement in (
        f"DROP TRIGGER IF EXISTS trg_{table_name}_immutable ON {table_name}",
        f"CREATE TRIGGER trg_{table_name}_immutable BEFORE UPDATE OR DELETE ON {table_name} FOR EACH ROW EXECUTE FUNCTION observability_v2_reject_mutation()",
    )),
)


async def run_up(bind=None) -> None:
    target = bind or engine
    await guard_engine_before_write(target)
    async with target.begin() as conn:
        for table in MODEL_TABLES:
            await conn.run_sync(lambda sync_conn, t=table: t.create(sync_conn, checkfirst=True))
        for stmt in IMMUTABILITY_STATEMENTS:
            await conn.execute(text(stmt))


async def run_down(bind=None) -> None:
    target = bind or engine
    await guard_engine_before_write(target)
    async with target.begin() as conn:
        for table_name in IMMUTABLE_TABLES:
            await conn.execute(text(f"DROP TRIGGER IF EXISTS trg_{table_name}_immutable ON {table_name}"))
        await conn.execute(text("DROP FUNCTION IF EXISTS observability_v2_reject_mutation()"))
        for table in reversed(MODEL_TABLES):
            await conn.run_sync(lambda sync_conn, t=table: t.drop(sync_conn, checkfirst=True))


async def execute_migration() -> None:
    await run_up()
