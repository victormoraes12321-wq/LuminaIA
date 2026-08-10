"""Unit and domain tests for V2 Governed Work Queue Services."""
from __future__ import annotations

import asyncio
import pytest
from datetime import datetime, timezone

from contracts.work_queue_v2.enums import (
    ConcurrencyClassV2,
    WorkQueueAdmissionDecisionKindV2,
    WorkQueueBackpressureStateKindV2,
    WorkQueueJobPriorityV2,
    WorkQueueJobTypeV2,
)

from services.work_queue_v2.backpressure import WorkQueueBackpressureServiceV2
from services.work_queue_v2.concurrency import GovernedConcurrencyControllerV2
from services.work_queue_v2.registry import GovernedJobRegistryV2
from services.work_queue_v2.single_flight import WorkQueueSingleFlightServiceV2


def test_job_registry_specs() -> None:
    spec = GovernedJobRegistryV2.get_spec(WorkQueueJobTypeV2.POST_SYNC_INSIGHT_RUN)
    assert spec.job_type == WorkQueueJobTypeV2.POST_SYNC_INSIGHT_RUN
    assert spec.default_priority == WorkQueueJobPriorityV2.HIGH
    assert spec.cancellation_supported is True

    specs = GovernedJobRegistryV2.list_specs()
    assert len(specs) >= 8


@pytest.mark.asyncio
async def test_concurrency_controller_limits() -> None:
    controller = GovernedConcurrencyControllerV2(global_limit=2, tenant_limit=1)

    async with controller.acquire_permit("tenant_a", ConcurrencyClassV2.DB_BOUND):
        assert controller.get_active_permit_count() == 1
        assert controller.get_tenant_active_count("tenant_a") == 1

        # Second request from same tenant should timeout due to tenant_limit=1
        with pytest.raises(asyncio.TimeoutError):
            async with controller.acquire_permit("tenant_a", ConcurrencyClassV2.DB_BOUND, timeout_seconds=0.1):
                pass

    assert controller.get_active_permit_count() == 0


def test_backpressure_evaluations() -> None:
    service = WorkQueueBackpressureServiceV2(max_queue_depth=10, max_tenant_depth=5)

    # Normal state
    st_normal = service.evaluate_state(queue_depth=2, oldest_job_age_seconds=10.0, active_workers=1, db_pool_utilization=0.2)
    assert st_normal.state == WorkQueueBackpressureStateKindV2.NORMAL

    admission = service.evaluate_admission(WorkQueueJobTypeV2.CACHE_REFRESH, "t1", WorkQueueJobPriorityV2.NORMAL, st_normal)
    assert admission.decision == WorkQueueAdmissionDecisionKindV2.ACCEPT

    # Saturated state
    st_sat = service.evaluate_state(queue_depth=10, oldest_job_age_seconds=10.0, active_workers=1, db_pool_utilization=0.96)
    assert st_sat.state == WorkQueueBackpressureStateKindV2.REJECTING

    admission_rejected = service.evaluate_admission(WorkQueueJobTypeV2.CACHE_REFRESH, "t1", WorkQueueJobPriorityV2.NORMAL, st_sat)
    assert admission_rejected.decision == WorkQueueAdmissionDecisionKindV2.REJECT_RETRYABLE


@pytest.mark.asyncio
async def test_singleflight_coalescing() -> None:
    sf = WorkQueueSingleFlightServiceV2()
    execution_counter = 0

    async def _heavy_task() -> str:
        nonlocal execution_counter
        execution_counter += 1
        await asyncio.sleep(0.1)
        return f"result-{execution_counter}"

    # Fire 5 concurrent calls with the same key
    tasks = [asyncio.create_task(sf.execute_or_coalesce("same_key", _heavy_task)) for _ in range(5)]
    results = await asyncio.gather(*tasks)

    # Exactly 1 origin execution, 4 coalesced
    assert execution_counter == 1
    for res, is_coalesced in results:
        assert res == "result-1"
