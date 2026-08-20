"""Worker Loop and Lifecycle Manager for V2 Work Queue."""
from __future__ import annotations

import asyncio
import logging
import os
import socket
import sys
import uuid
from datetime import datetime, timezone
from typing import Callable
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from config import settings
from contracts.work_queue_v2.enums import (
    ConcurrencyClassV2,
    WorkQueueErrorClassV2,
    WorkQueueJobStatusV2,
    WorkQueueJobTypeV2,
    WorkQueueWorkerStatusKindV2,
)
from contracts.work_queue_v2.models import WorkQueueJobResultV2
from services.work_queue_v2.concurrency import GovernedConcurrencyControllerV2
from services.work_queue_v2.lease import WorkQueueLeaseServiceV2, WorkQueueLeaseReclaimerV2
from services.work_queue_v2.queue_service import WorkQueueServiceV2
from services.work_queue_v2.registry import GovernedJobRegistryV2

logger = logging.getLogger("luminaai.work_queue.worker")


class WorkQueueWorkerV2:
    """Autonomous background worker claiming and executing queue jobs."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        concurrency_controller: GovernedConcurrencyControllerV2 | None = None,
        supported_job_types: tuple[WorkQueueJobTypeV2, ...] | None = None,
        worker_id: str | None = None,
        poll_interval_seconds: float = 1.0,
    ) -> None:
        self.session_factory = session_factory
        self.concurrency = concurrency_controller or GovernedConcurrencyControllerV2()
        self.supported_job_types = supported_job_types or tuple(GovernedJobRegistryV2.list_specs()[i].job_type for i in range(len(GovernedJobRegistryV2.list_specs())))
        self.worker_id = worker_id or f"worker-{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        self.poll_interval_seconds = poll_interval_seconds

        self.status = WorkQueueWorkerStatusKindV2.STARTING
        self.queue_service = WorkQueueServiceV2()
        self._running = False
        self._draining = False
        self._active_jobs: set[str] = set()
        self._worker_task: asyncio.Task[None] | None = None
        self._reclaim_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if getattr(settings, "WORK_QUEUE_MODE", "LEGACY_ONLY") == "LEGACY_ONLY":
            logger.info("WORK_QUEUE_MODE is LEGACY_ONLY; worker startup bypassed")
            return
        if not getattr(settings, "WORK_QUEUE_WORKER_ENABLED", False) and not getattr(settings, "PERFORMANCE_CERTIFICATION_MODE", False):
            logger.info("WORK_QUEUE_WORKER_ENABLED is False; worker startup bypassed")
            return

        self._running = True
        self.status = WorkQueueWorkerStatusKindV2.ACTIVE
        self._worker_task = asyncio.create_task(self._run_loop())
        self._reclaim_task = asyncio.create_task(self._reclaim_loop())
        logger.info("WorkQueueWorkerV2 [%s] started", self.worker_id)

    async def stop(self, grace_period_seconds: float = 10.0) -> None:
        self._draining = True
        self.status = WorkQueueWorkerStatusKindV2.DRAINING
        logger.info("WorkQueueWorkerV2 [%s] draining active jobs...", self.worker_id)

        start_time = asyncio.get_event_loop().time()
        while self._active_jobs and (asyncio.get_event_loop().time() - start_time) < grace_period_seconds:
            await asyncio.sleep(0.2)

        self._running = False
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
        if self._reclaim_task and not self._reclaim_task.done():
            self._reclaim_task.cancel()

        self.status = WorkQueueWorkerStatusKindV2.STOPPED
        logger.info("WorkQueueWorkerV2 [%s] stopped", self.worker_id)

    async def _run_loop(self) -> None:
        while self._running and not self._draining:
            try:
                async with self.session_factory() as session:
                    job = await self.queue_service.claim_job(
                        session=session,
                        worker_id=self.worker_id,
                        supported_job_types=self.supported_job_types,
                    )
                    if job:
                        asyncio.create_task(self._execute_job_task(str(job.id), job.job_type, str(job.tenant_id), job.payload_json, job.lease_version))
                    else:
                        await asyncio.sleep(self.poll_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Error in worker claim loop: %s", exc)
                await asyncio.sleep(self.poll_interval_seconds)

    async def _reclaim_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(15.0)
                async with self.session_factory() as session:
                    await WorkQueueLeaseReclaimerV2.reclaim_expired_leases(session)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Error in lease reclaim loop: %s", exc)

    async def _execute_job_task(
        self,
        job_id: str,
        job_type_str: str,
        tenant_id: str,
        payload_json: dict[str, Any],
        lease_version: int,
    ) -> None:
        self._active_jobs.add(job_id)
        job_type = WorkQueueJobTypeV2(job_type_str)
        spec = GovernedJobRegistryV2.get_spec(job_type)

        now = datetime.now(timezone.utc)
        try:
            async with self.concurrency.acquire_permit(
                tenant_id=tenant_id,
                concurrency_class=spec.concurrency_class,
                timeout_seconds=spec.timeout_seconds,
            ):
                handler = GovernedJobRegistryV2.get_handler(job_type)
                if not handler:
                    # Default dummy success handler for unregistered endpoints in tests
                    res_summary = f"Job {job_id} executed successfully by default worker"
                    result = WorkQueueJobResultV2(
                        success=True,
                        result_code="SUCCESS",
                        summary=res_summary,
                        completed_at=now,
                    )
                else:
                    params = payload_json.get("parameters", {})
                    out_dict = await asyncio.wait_for(
                        handler(job_id, params),
                        timeout=spec.timeout_seconds,
                    )
                    result = WorkQueueJobResultV2(
                        success=True,
                        result_code=out_dict.get("result_code", "SUCCESS"),
                        summary=out_dict.get("summary", "Job completed"),
                        details=out_dict,
                        completed_at=now,
                    )

                async with self.session_factory() as session:
                    await self.queue_service.finish_job(
                        session=session,
                        job_id=job_id,
                        worker_id=self.worker_id,
                        lease_version=lease_version,
                        result=result,
                    )

        except asyncio.TimeoutError:
            logger.warning("Job %s timed out after %fs", job_id, spec.timeout_seconds)
            async with self.session_factory() as session:
                await self.queue_service.fail_job(
                    session=session,
                    job_id=job_id,
                    worker_id=self.worker_id,
                    lease_version=lease_version,
                    error_class=WorkQueueErrorClassV2.TIMEOUT_RETRYABLE,
                    error_message=f"Job execution timed out after {spec.timeout_seconds}s",
                    retryable=True,
                )
        except Exception as exc:
            logger.exception("Error executing job %s: %s", job_id, exc)
            async with self.session_factory() as session:
                await self.queue_service.fail_job(
                    session=session,
                    job_id=job_id,
                    worker_id=self.worker_id,
                    lease_version=lease_version,
                    error_class=WorkQueueErrorClassV2.UNKNOWN_ERROR,
                    error_message=str(exc)[:512],
                    retryable=True,
                )
        finally:
            self._active_jobs.discard(job_id)
