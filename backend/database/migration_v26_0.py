"""Migration v26: governed work queue, concurrency, leases, and performance platform."""
from __future__ import annotations

from sqlalchemy import text

from database import engine
from models.work_queue_v2 import (
    PerformanceBaselineModelV2,
    PerformanceRunModelV2,
    WorkQueueAttemptModelV2,
    WorkQueueAuditEventModelV2,
    WorkQueueDeadLetterModelV2,
    WorkQueueJobModelV2,
    WorkQueueWorkerModelV2,
)
from testing.database_guard import guard_engine_before_write

MIGRATION_NAME = "v26_0_work_queue_performance"
TABLES = [
    "governed_work_queue_jobs_v2",
    "governed_work_queue_attempts_v2",
    "governed_work_queue_workers_v2",
    "governed_work_queue_dead_letters_v2",
    "governed_work_queue_audit_events_v2",
    "performance_baselines_v2",
    "performance_runs_v2",
]
MODEL_TABLES = [
    WorkQueueJobModelV2.__table__,
    WorkQueueAttemptModelV2.__table__,
    WorkQueueWorkerModelV2.__table__,
    WorkQueueDeadLetterModelV2.__table__,
    WorkQueueAuditEventModelV2.__table__,
    PerformanceBaselineModelV2.__table__,
    PerformanceRunModelV2.__table__,
]
IMMUTABLE_TABLES = (
    "governed_work_queue_dead_letters_v2",
    "governed_work_queue_audit_events_v2",
    "performance_baselines_v2",
    "performance_runs_v2",
)
IMMUTABILITY_STATEMENTS = (
    """
    CREATE OR REPLACE FUNCTION work_queue_v2_reject_mutation()
    RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION 'governed work queue certified audit history is immutable';
    END;
    $$;
    """,
    *(statement for table_name in IMMUTABLE_TABLES for statement in (
        f"DROP TRIGGER IF EXISTS trg_{table_name}_immutable ON {table_name}",
        f"CREATE TRIGGER trg_{table_name}_immutable BEFORE UPDATE OR DELETE ON {table_name} FOR EACH ROW EXECUTE FUNCTION work_queue_v2_reject_mutation()",
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
        await conn.execute(text("DROP FUNCTION IF EXISTS work_queue_v2_reject_mutation()"))
        for table in reversed(MODEL_TABLES):
            await conn.run_sync(lambda sync_conn, t=table: t.drop(sync_conn, checkfirst=True))


async def execute_migration() -> None:
    await run_up()
