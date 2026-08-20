"""Lease Manager, Heartbeat Updater, and Reclaimer for V2 Work Queue."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update, text, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.work_queue_v2 import WorkQueueJobModelV2, WorkQueueAttemptModelV2, WorkQueueDeadLetterModelV2

logger = logging.getLogger("luminaai.work_queue.lease")


class WorkQueueLeaseServiceV2:
    """Handles lease heartbeats and atomic lease validation."""

    @staticmethod
    async def heartbeat(
        session: AsyncSession,
        job_id: str,
        worker_id: str,
        lease_version: int,
        extend_duration_seconds: int = 60,
    ) -> bool:
        now = datetime.now(timezone.utc)
        new_expires_at = now + timedelta(seconds=extend_duration_seconds)

        stmt = (
            update(WorkQueueJobModelV2)
            .where(
                and_(
                    WorkQueueJobModelV2.id == job_id,
                    WorkQueueJobModelV2.assigned_worker_id == worker_id,
                    WorkQueueJobModelV2.lease_version == lease_version,
                    WorkQueueJobModelV2.status.in_(["CLAIMED", "RUNNING"]),
                )
            )
            .values(
                updated_at=now,
            )
        )
        res = await session.execute(stmt)
        await session.commit()
        return res.rowcount == 1


class WorkQueueLeaseReclaimerV2:
    """Scans for expired leases and reclaims or dead-letters jobs."""

    @staticmethod
    async def reclaim_expired_leases(
        session: AsyncSession,
        lease_duration_seconds: int = 60,
    ) -> int:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=lease_duration_seconds)

        # Select jobs with expired leases
        stmt = select(WorkQueueJobModelV2).where(
            and_(
                WorkQueueJobModelV2.status.in_(["CLAIMED", "RUNNING"]),
                WorkQueueJobModelV2.updated_at < cutoff,
            )
        ).with_for_update(skip_locked=True)

        res = await session.execute(stmt)
        expired_jobs = res.scalars().all()
        reclaimed_count = 0

        for job in expired_jobs:
            job.attempts_count += 1
            if job.attempts_count >= job.max_attempts:
                job.status = "DEAD_LETTER"
                job.completed_at = now
                job.last_error_class = "LEASE_LOST"
                job.last_error_message = f"Lease expired after {lease_duration_seconds}s; max attempts ({job.max_attempts}) reached"

                # Record dead letter
                dead_letter = WorkQueueDeadLetterModelV2(
                    job_id=job.id,
                    tenant_id=job.tenant_id,
                    job_type=job.job_type,
                    total_attempts=job.attempts_count,
                    last_error_class="LEASE_LOST",
                    sanitized_error_message=f"Lease lost by worker {job.assigned_worker_id}",
                    moved_to_dead_letter_at=now,
                )
                session.add(dead_letter)
            else:
                job.status = "RETRY_WAIT"
                job.assigned_worker_id = None
                job.lease_version += 1
                job.available_at = now + timedelta(seconds=5)
                job.last_error_class = "LEASE_LOST"
                job.last_error_message = f"Lease expired for worker {job.assigned_worker_id}; scheduled for reclaim retry"

            job.updated_at = now
            reclaimed_count += 1

        if reclaimed_count > 0:
            await session.commit()
            logger.info("Reclaimed %d expired work queue leases", reclaimed_count)

        return reclaimed_count
