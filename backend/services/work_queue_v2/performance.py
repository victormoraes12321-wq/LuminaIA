"""Performance Certification Service V2 for Synthetic Benchmark Testing."""
from __future__ import annotations

import asyncio
import hashlib
import time
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from contracts.work_queue_v2.enums import (
    PerformanceLoadLevelV2,
    WorkQueueJobPriorityV2,
    WorkQueueJobTypeV2,
)
from contracts.work_queue_v2.models import (
    WorkQueuePerformanceBaselineV2,
    WorkQueuePerformanceResultV2,
)
from models.work_queue_v2 import PerformanceBaselineModelV2, PerformanceRunModelV2
from services.work_queue_v2.concurrency import GovernedConcurrencyControllerV2
from services.work_queue_v2.queue_service import WorkQueueServiceV2
from services.work_queue_v2.single_flight import WorkQueueSingleFlightServiceV2
from services.work_queue_v2.worker import WorkQueueWorkerV2


class PerformanceCertificationServiceV2:
    """Synthetic load and performance certification harness."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory
        self.queue_service = WorkQueueServiceV2()
        self.single_flight = WorkQueueSingleFlightServiceV2()

    @staticmethod
    def _percentile(values: list[float], pct: float) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        k = (len(sorted_vals) - 1) * (pct / 100.0)
        f = int(k)
        c = f + 1
        if c < len(sorted_vals):
            return sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f])
        return sorted_vals[f]

    async def run_benchmark(
        self,
        load_level: PerformanceLoadLevelV2 = PerformanceLoadLevelV2.SMALL,
        total_jobs: int = 100,
        concurrency_level: int = 4,
    ) -> WorkQueuePerformanceResultV2:
        run_id = f"perf-{uuid.uuid4().hex[:12]}"
        tenant_id = str(uuid.uuid4())
        latencies_ms: list[float] = []
        success_count = 0
        error_count = 0
        dead_letter_count = 0
        coalesced_count = 0

        self.queue_service.backpressure.max_queue_depth = max(1000, total_jobs * 2)
        self.queue_service.backpressure.max_tenant_depth = max(1000, total_jobs * 2)

        concurrency_ctrl = GovernedConcurrencyControllerV2(global_limit=concurrency_level)
        workers = [
            WorkQueueWorkerV2(
                session_factory=self.session_factory,
                concurrency_controller=concurrency_ctrl,
                worker_id=f"perf-worker-{i}",
                poll_interval_seconds=0.01,
            )
            for i in range(concurrency_level)
        ]

        for w in workers:
            w._running = True
            w.status = "ACTIVE"

        start_ns = time.perf_counter_ns()

        # Enqueue jobs
        async with self.session_factory() as session:
            for i in range(total_jobs):
                ik = f"perf-ik-{i}"
                await self.queue_service.enqueue_job(
                    session=session,
                    tenant_id=tenant_id,
                    job_type=WorkQueueJobTypeV2.POST_SYNC_INSIGHT_RUN,
                    canonical_reference_id=f"ref_{i}",
                    parameters={"idx": str(i)},
                    idempotency_key=ik,
                    priority=WorkQueueJobPriorityV2.NORMAL,
                )

        # Execute jobs using workers concurrently
        async def _worker_process_jobs(worker: WorkQueueWorkerV2):
            nonlocal success_count, error_count
            while True:
                async with self.session_factory() as session:
                    job = await self.queue_service.claim_job(
                        session=session,
                        worker_id=worker.worker_id,
                        supported_job_types=(WorkQueueJobTypeV2.POST_SYNC_INSIGHT_RUN,),
                    )
                    if not job:
                        break
                    t0 = time.perf_counter_ns()
                    try:
                        # Finish job directly in benchmark
                        res_ok = await self.queue_service.finish_job(
                            session=session,
                            job_id=str(job.id),
                            worker_id=worker.worker_id,
                            lease_version=job.lease_version,
                            result=None,  # Handled in finish_job
                        )
                        t1 = time.perf_counter_ns()
                        if res_ok:
                            success_count += 1
                            latencies_ms.append((t1 - t0) / 1e6)
                        else:
                            error_count += 1
                    except Exception:
                        error_count += 1

        tasks = [asyncio.create_task(_worker_process_jobs(w)) for w in workers]
        await asyncio.gather(*tasks)

        end_ns = time.perf_counter_ns()
        duration_s = max(0.001, (end_ns - start_ns) / 1e9)
        rps = total_jobs / duration_s

        p50 = self._percentile(latencies_ms, 50.0)
        p95 = self._percentile(latencies_ms, 95.0)
        p99 = self._percentile(latencies_ms, 99.0)
        min_lat = min(latencies_ms) if latencies_ms else 0.0
        max_lat = max(latencies_ms) if latencies_ms else 0.0

        now = datetime.now(timezone.utc)
        result = WorkQueuePerformanceResultV2(
            run_id=run_id,
            load_level=load_level,
            total_jobs_processed=total_jobs,
            duration_seconds=round(duration_s, 4),
            throughput_jobs_per_second=round(rps, 2),
            p50_latency_ms=round(p50, 2),
            p95_latency_ms=round(p95, 2),
            p99_latency_ms=round(p99, 2),
            min_latency_ms=round(min_lat, 2),
            max_latency_ms=round(max_lat, 2),
            success_count=success_count,
            error_count=error_count,
            dead_letter_count=dead_letter_count,
            singleflight_coalesced_count=coalesced_count,
            executed_at=now,
        )

        # Save to DB
        async with self.session_factory() as session:
            model = PerformanceRunModelV2(
                run_id=result.run_id,
                load_level=result.load_level.value,
                total_jobs_processed=result.total_jobs_processed,
                duration_seconds=result.duration_seconds,
                throughput_jobs_per_second=result.throughput_jobs_per_second,
                p50_latency_ms=result.p50_latency_ms,
                p95_latency_ms=result.p95_latency_ms,
                p99_latency_ms=result.p99_latency_ms,
                min_latency_ms=result.min_latency_ms,
                max_latency_ms=result.max_latency_ms,
                success_count=result.success_count,
                error_count=result.error_count,
                dead_letter_count=result.dead_letter_count,
                singleflight_coalesced_count=result.singleflight_coalesced_count,
                executed_at=now,
            )
            session.add(model)
            await session.commit()

        return result

    async def get_or_create_provisional_baseline(self) -> WorkQueuePerformanceBaselineV2:
        now = datetime.now(timezone.utc)
        baseline_id = "provisional-baseline-v1"
        checksum = hashlib.sha256(f"{baseline_id}:PROVISIONAL:880477a".encode()).hexdigest()

        async with self.session_factory() as session:
            stmt = select(PerformanceBaselineModelV2).where(PerformanceBaselineModelV2.baseline_id == baseline_id)
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing:
                return WorkQueuePerformanceBaselineV2(
                    baseline_id=existing.baseline_id,
                    contract_version=existing.contract_version,
                    origin_commit=existing.origin_commit,
                    status=existing.status,
                    small_throughput_rps=existing.small_throughput_rps,
                    small_p95_latency_ms=existing.small_p95_latency_ms,
                    medium_throughput_rps=existing.medium_throughput_rps,
                    medium_p95_latency_ms=existing.medium_p95_latency_ms,
                    baseline_checksum=existing.baseline_checksum,
                    created_at=existing.created_at,
                )

            model = PerformanceBaselineModelV2(
                id=uuid.uuid4(),
                baseline_id=baseline_id,
                contract_version="lumina.scale-queues-performance/1.0",
                origin_commit="880477a",
                status="PROVISIONAL",
                small_throughput_rps=50.0,
                small_p95_latency_ms=25.0,
                medium_throughput_rps=40.0,
                medium_p95_latency_ms=35.0,
                baseline_checksum=checksum,
                created_at=now,
            )
            session.add(model)
            await session.commit()

        return WorkQueuePerformanceBaselineV2(
            baseline_id=baseline_id,
            contract_version="lumina.scale-queues-performance/1.0",
            origin_commit="880477a",
            status="PROVISIONAL",
            small_throughput_rps=50.0,
            small_p95_latency_ms=25.0,
            medium_throughput_rps=40.0,
            medium_p95_latency_ms=35.0,
            baseline_checksum=checksum,
            created_at=now,
        )
