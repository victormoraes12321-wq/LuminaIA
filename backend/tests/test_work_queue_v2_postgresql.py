"""PostgreSQL integration tests for V2 Governed Work Queue, Leases, Reclaim, Race Conditions, and Fairness."""
from __future__ import annotations

import asyncio
import uuid
import pytest
from datetime import datetime, timedelta, timezone
from database import engine, AsyncSessionLocal
from models.work_queue_v2 import WorkQueueJobModelV2, WorkQueueDeadLetterModelV2
from contracts.work_queue_v2.enums import WorkQueueJobPriorityV2, WorkQueueJobTypeV2, WorkQueueErrorClassV2
from services.work_queue_v2.lease import WorkQueueLeaseReclaimerV2
from services.work_queue_v2.queue_service import WorkQueueServiceV2
from testing.database_guard import guard_engine_before_write


@pytest.mark.asyncio
async def test_enqueue_claim_finish_flow() -> None:
    await guard_engine_before_write(engine)
    svc = WorkQueueServiceV2()
    tenant_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as session:
        job, is_new = await svc.enqueue_job(
            session=session,
            tenant_id=tenant_id,
            job_type=WorkQueueJobTypeV2.POST_SYNC_INSIGHT_RUN,
            canonical_reference_id="ref_100",
            parameters={"env": "test"},
            idempotency_key="ik_flow_100",
        )
        assert is_new is True
        assert job.status == "QUEUED"

        # Duplicate enqueue returns same job
        dup_job, dup_is_new = await svc.enqueue_job(
            session=session,
            tenant_id=tenant_id,
            job_type=WorkQueueJobTypeV2.POST_SYNC_INSIGHT_RUN,
            canonical_reference_id="ref_100",
            parameters={"env": "test"},
            idempotency_key="ik_flow_100",
        )
        assert dup_is_new is False
        assert dup_job.id == job.id

        # Claim job
        claimed = await svc.claim_job(session=session, worker_id="w-100")
        assert claimed is not None
        assert claimed.id == job.id
        assert claimed.assigned_worker_id == "w-100"
        assert claimed.status == "CLAIMED"

        # Finish job
        finished = await svc.finish_job(
            session=session,
            job_id=str(job.id),
            worker_id="w-100",
            lease_version=claimed.lease_version,
            result=None,  # Handled in finish_job
        )
        assert finished is True


@pytest.mark.asyncio
async def test_two_worker_race_condition() -> None:
    await guard_engine_before_write(engine)
    svc = WorkQueueServiceV2()
    tenant_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as session:
        for i in range(10):
            await svc.enqueue_job(
                session=session,
                tenant_id=tenant_id,
                job_type=WorkQueueJobTypeV2.MATERIALIZATION_BUILD,
                canonical_reference_id=f"mat_{i}",
                parameters={},
                idempotency_key=f"ik_race_{i}",
            )

    claimed_worker_1 = []
    claimed_worker_2 = []

    async def _claim_worker(worker_id: str, dest_list: list[str]):
        while True:
            async with AsyncSessionLocal() as session:
                j = await svc.claim_job(session=session, worker_id=worker_id, per_tenant_limit=20)
                if not j:
                    break
                dest_list.append(str(j.id))
                await asyncio.sleep(0.005)

    await asyncio.gather(
        _claim_worker("worker_a", claimed_worker_1),
        _claim_worker("worker_b", claimed_worker_2),
    )

    # Combined claims must not overlap
    set_a = set(claimed_worker_1)
    set_b = set(claimed_worker_2)
    assert len(set_a.intersection(set_b)) == 0
    assert len(set_a) + len(set_b) == 10


@pytest.mark.asyncio
async def test_expired_lease_reclaim() -> None:
    await guard_engine_before_write(engine)
    svc = WorkQueueServiceV2()
    tenant_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as session:
        job, _ = await svc.enqueue_job(
            session=session,
            tenant_id=tenant_id,
            job_type=WorkQueueJobTypeV2.EVALUATION_RUN,
            canonical_reference_id="eval_rec",
            parameters={},
            idempotency_key="ik_rec_001",
        )
        claimed = await svc.claim_job(session=session, worker_id="worker_dead")
        assert claimed is not None

        # Manually backdate updated_at to simulate worker crash
        claimed.updated_at = datetime.now(timezone.utc) - timedelta(seconds=120)
        await session.commit()

        # Reclaim expired leases
        reclaimed = await WorkQueueLeaseReclaimerV2.reclaim_expired_leases(session, lease_duration_seconds=60)
        assert reclaimed >= 1

        # Check job is back in RETRY_WAIT
        await session.refresh(claimed)
        assert claimed.status == "RETRY_WAIT"
        assert claimed.attempts_count == 1


@pytest.mark.asyncio
async def test_stale_worker_finish_rejection() -> None:
    await guard_engine_before_write(engine)
    svc = WorkQueueServiceV2()
    tenant_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as session:
        job, _ = await svc.enqueue_job(
            session=session,
            tenant_id=tenant_id,
            job_type=WorkQueueJobTypeV2.CACHE_REFRESH,
            canonical_reference_id="cr_001",
            parameters={},
            idempotency_key="ik_stale_001",
        )
        claimed = await svc.claim_job(session=session, worker_id="worker_orig")
        orig_version = claimed.lease_version

        # Simulate lease increment from reclaim
        claimed.lease_version += 1
        claimed.assigned_worker_id = "worker_new"
        await session.commit()

        # Original worker attempts finish with old version -> fails
        finished = await svc.finish_job(
            session=session,
            job_id=str(job.id),
            worker_id="worker_orig",
            lease_version=orig_version,
            result=None,
        )
        assert finished is False


@pytest.mark.asyncio
async def test_multi_tenant_fairness() -> None:
    await guard_engine_before_write(engine)
    svc = WorkQueueServiceV2()
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())

    async with AsyncSessionLocal() as session:
        # Tenant A enqueues 10 jobs
        for i in range(10):
            await svc.enqueue_job(
                session=session,
                tenant_id=tenant_a,
                job_type=WorkQueueJobTypeV2.DASHBOARD_BACKGROUND_REFRESH,
                canonical_reference_id=f"dash_a_{i}",
                parameters={},
                idempotency_key=f"ik_fair_a_{i}",
            )
        # Tenant B enqueues 1 job
        await svc.enqueue_job(
            session=session,
            tenant_id=tenant_b,
            job_type=WorkQueueJobTypeV2.DASHBOARD_BACKGROUND_REFRESH,
            canonical_reference_id="dash_b_0",
            parameters={},
            idempotency_key="ik_fair_b_0",
        )

        # Claim with per_tenant_limit=2
        # Tenant A gets max 2 active jobs; Tenant B gets 1 job
        claims = []
        for _ in range(5):
            c = await svc.claim_job(session=session, worker_id="w-fair", per_tenant_limit=2)
            if c:
                claims.append(str(c.tenant_id))

        # Tenant B must have been claimed despite Tenant A having 10 jobs queued
        assert tenant_b in claims
