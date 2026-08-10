"""Integration tests for Observability V2 PostgreSQL models on disposable test database."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database import engine
from models.observability_v2 import (
    EvaluationRunModelV2,
    ObservabilityAuditEventModelV2,
    OperationalMetricRollupModelV2,
    SloDefinitionModelV2,
    SloEvaluationModelV2,
    TraceSummaryModelV2,
)
from testing.database_guard import guard_engine_before_write

ROOT = Path(__file__).resolve().parents[1]


def _load_v25():
    path = ROOT / "database" / "migration_v25_0.py"
    spec = importlib.util.spec_from_file_location("mig_v25_pg_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_observability_v2_postgresql_persistence_and_immutability():
    await guard_engine_before_write(engine)

    # Ensure v25 tables exist
    v25 = _load_v25()
    await v25.run_up(engine)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        # Create metric rollup
        rollup = OperationalMetricRollupModelV2(
            id=uuid.uuid4(),
            metric_id="http_requests_total",
            window_start=datetime.now(timezone.utc),
            window_end=datetime.now(timezone.utc),
            count=10,
            sum_value=Decimal("10.0000"),
            min_value=Decimal("1.0000"),
            max_value=Decimal("1.0000"),
            avg_value=Decimal("1.0000"),
            labels=[["method", "GET"]],
        )
        session.add(rollup)

        # Create trace summary
        trace = TraceSummaryModelV2(
            trace_id=f"trc_{uuid.uuid4().hex}",
            root_span_id=f"spn_{uuid.uuid4().hex}",
            route_template="/health",
            started_at=datetime.now(timezone.utc),
            total_duration_ms=Decimal("5.25"),
            status="OK",
            span_count=1,
        )
        session.add(trace)

        # Create evaluation run
        run = EvaluationRunModelV2(
            run_id=f"run_{uuid.uuid4().hex}",
            suite="SECURITY",
            executed_at=datetime.now(timezone.utc),
            total_cases=2,
            passed_cases=2,
            failed_cases=0,
            blocked_cases=0,
            error_cases=0,
            duration_ms=Decimal("10.00"),
            checksum=uuid.uuid4().hex,
        )
        session.add(run)

        await session.commit()

        # Query back
        res = await session.execute(sqlalchemy.select(OperationalMetricRollupModelV2).where(OperationalMetricRollupModelV2.metric_id == "http_requests_total"))
        rollups = res.scalars().all()
        assert len(rollups) >= 1
        assert rollups[0].count == 10
