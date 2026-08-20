"""Governed Work Queue Core Service V2."""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from sqlalchemy import select, update, func, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession

from contracts.work_queue_v2.enums import (
    WorkQueueAdmissionDecisionKindV2,
    WorkQueueErrorClassV2,
    WorkQueueJobPriorityV2,
    WorkQueueJobStatusV2,
    WorkQueueJobTypeV2,
)
from contracts.work_queue_v2.models import (
    WorkQueueJobPayloadEnvelopeV2,
    WorkQueueJobResultV2,
    WorkQueueJobV2,
    WorkQueueStatsV2,
)
from models.work_queue_v2 import (
    WorkQueueAttemptModelV2,
    WorkQueueAuditEventModelV2,
    WorkQueueDeadLetterModelV2,
    WorkQueueJobModelV2,
)
from services.work_queue_v2.backpressure import WorkQueueBackpressureServiceV2
from services.work_queue_v2.registry import GovernedJobRegistryV2
from services.observability_v2.redaction import ObservabilityRedactionService

logger = logging.getLogger("luminaai.work_queue.service")

PRIORITY_ORDER = {
    "CRITICAL": 1,
    "HIGH": 2,
    "NORMAL": 3,
    "LOW": 4,
    "BACKGROUND": 5,
}


class WorkQueueServiceV2:
    """Core domain service for governed queue operations."""

    def __init__(
        self,
        backpressure_service: WorkQueueBackpressureServiceV2 | None = None,
    ) -> None:
        self.backpressure = backpressure_service or WorkQueueBackpressureServiceV2()

    @staticmethod
    def compute_payload_checksum(payload: dict[str, Any]) -> str:
        canonical_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_idempotency_fingerprint(
        tenant_id: str,
        job_type: str,
        idempotency_key: str,
        payload_checksum: str,
    ) -> str:
        raw = f"{tenant_id}:{job_type}:{idempotency_key}:{payload_checksum}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def enqueue_job(
        self,
        session: AsyncSession,
        tenant_id: str,
        job_type: WorkQueueJobTypeV2,
        canonical_reference_id: str,
        parameters: dict[str, str],
        idempotency_key: str,
        created_by_user_id: str | None = None,
        priority: WorkQueueJobPriorityV2 | None = None,
    ) -> tuple[WorkQueueJobModelV2, bool]:
        """Enqueue a new job or return existing job for idempotency key.

        Returns (job_model, is_new: bool).
        """
        now = datetime.now(timezone.utc)
        spec = GovernedJobRegistryV2.get_spec(job_type)
        effective_priority = priority or spec.default_priority

        payload_dict = {
            "job_type": job_type.value,
            "canonical_reference_id": canonical_reference_id,
            "parameters": parameters,
        }
        payload_checksum = self.compute_payload_checksum(payload_dict)
        fingerprint = self.compute_idempotency_fingerprint(
            tenant_id, job_type.value, idempotency_key, payload_checksum
        )

        # Check existing job for idempotency key
        stmt = select(WorkQueueJobModelV2).where(
            and_(
                WorkQueueJobModelV2.tenant_id == tenant_id,
                WorkQueueJobModelV2.job_type == job_type.value,
                WorkQueueJobModelV2.idempotency_key == idempotency_key,
            )
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            if existing.idempotency_fingerprint != fingerprint:
                raise ValueError(f"Idempotency conflict for key {idempotency_key} with different payload fingerprint")
            return existing, False

        # Admission control & backpressure check
        stats_stmt = select(func.count()).select_from(WorkQueueJobModelV2).where(WorkQueueJobModelV2.status == "QUEUED")
        queued_count = (await session.execute(stats_stmt)).scalar_one()

        tenant_queued_stmt = select(func.count()).select_from(WorkQueueJobModelV2).where(
            and_(WorkQueueJobModelV2.tenant_id == tenant_id, WorkQueueJobModelV2.status == "QUEUED")
        )
        tenant_queued_count = (await session.execute(tenant_queued_stmt)).scalar_one()

        bp_state = self.backpressure.evaluate_state(
            queue_depth=queued_count,
            oldest_job_age_seconds=0.0,
            active_workers=1,
            db_pool_utilization=0.1,
        )
        admission = self.backpressure.evaluate_admission(
            job_type=job_type,
            tenant_id=tenant_id,
            priority=effective_priority,
            current_state=bp_state,
            tenant_current_queued_jobs=tenant_queued_count,
        )
        if admission.decision in (WorkQueueAdmissionDecisionKindV2.BLOCK, WorkQueueAdmissionDecisionKindV2.REJECT_RETRYABLE):
            raise RuntimeError(f"Job admission rejected: {admission.reason}")

        job = WorkQueueJobModelV2(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(tenant_id),
            created_by_user_id=uuid.UUID(created_by_user_id) if created_by_user_id else None,
            job_type=job_type.value,
            status="QUEUED",
            priority=effective_priority.value,
            idempotency_key=idempotency_key,
            idempotency_fingerprint=fingerprint,
            payload_json=payload_dict,
            payload_checksum=payload_checksum,
            attempts_count=0,
            max_attempts=spec.max_attempts,
            assigned_worker_id=None,
            lease_version=1,
            available_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(job)
        await session.commit()
        return job, True

    async def claim_job(
        self,
        session: AsyncSession,
        worker_id: str,
        supported_job_types: tuple[WorkQueueJobTypeV2, ...] | None = None,
        per_tenant_limit: int = 3,
    ) -> WorkQueueJobModelV2 | None:
        """Claim next available job using FOR UPDATE SKIP LOCKED."""
        now = datetime.now(timezone.utc)

        # Base filter
        stmt = select(WorkQueueJobModelV2).where(
            and_(
                WorkQueueJobModelV2.status.in_(["QUEUED", "RETRY_WAIT"]),
                WorkQueueJobModelV2.available_at <= now,
            )
        )
        if supported_job_types:
            stmt = stmt.where(WorkQueueJobModelV2.job_type.in_([jt.value for jt in supported_job_types]))

        stmt = stmt.order_by(
            WorkQueueJobModelV2.priority.asc(),
            WorkQueueJobModelV2.available_at.asc(),
            WorkQueueJobModelV2.created_at.asc(),
        ).with_for_update(skip_locked=True).limit(100)

        candidates = (await session.execute(stmt)).scalars().all()
        if not candidates:
            return None

        # Pick first candidate respecting tenant active limit
        chosen_job: WorkQueueJobModelV2 | None = None
        for cand in candidates:
            tenant_active_stmt = select(func.count()).select_from(WorkQueueJobModelV2).where(
                and_(
                    WorkQueueJobModelV2.tenant_id == cand.tenant_id,
                    WorkQueueJobModelV2.status.in_(["CLAIMED", "RUNNING"]),
                )
            )
            tenant_active_count = (await session.execute(tenant_active_stmt)).scalar_one()
            if tenant_active_count < per_tenant_limit or cand.priority == "CRITICAL":
                chosen_job = cand
                break

        if not chosen_job:
            return None

        chosen_job.status = "CLAIMED"
        chosen_job.assigned_worker_id = worker_id
        chosen_job.claimed_at = now
        chosen_job.updated_at = now
        chosen_job.lease_version += 1

        await session.commit()
        return chosen_job

    async def finish_job(
        self,
        session: AsyncSession,
        job_id: str,
        worker_id: str,
        lease_version: int,
        result: WorkQueueJobResultV2,
    ) -> bool:
        """Record successful job execution via CAS on lease_version."""
        now = datetime.now(timezone.utc)
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
                status="SUCCEEDED",
                completed_at=now,
                updated_at=now,
                last_error_class=None,
                last_error_message=None,
            )
        )
        res = await session.execute(stmt)
        if res.rowcount == 1:
            await session.commit()
            return True
        await session.rollback()
        return False

    async def fail_job(
        self,
        session: AsyncSession,
        job_id: str,
        worker_id: str,
        lease_version: int,
        error_class: WorkQueueErrorClassV2,
        error_message: str,
        retryable: bool,
    ) -> bool:
        """Record job failure, schedule retry or move to dead letter."""
        now = datetime.now(timezone.utc)
        stmt = select(WorkQueueJobModelV2).where(
            and_(
                WorkQueueJobModelV2.id == job_id,
                WorkQueueJobModelV2.assigned_worker_id == worker_id,
                WorkQueueJobModelV2.lease_version == lease_version,
            )
        ).with_for_update()

        job = (await session.execute(stmt)).scalar_one_or_none()
        if not job:
            await session.rollback()
            return False

        sanitized_error = ObservabilityRedactionService().redact_string(error_message)[:512]
        job.attempts_count += 1
        job.last_error_class = error_class.value
        job.last_error_message = sanitized_error
        job.updated_at = now

        # Create attempt record
        attempt = WorkQueueAttemptModelV2(
            id=uuid.uuid4(),
            job_id=job.id,
            tenant_id=job.tenant_id,
            attempt_number=job.attempts_count,
            worker_id=worker_id,
            status="FAILED",
            started_at=job.claimed_at or now,
            ended_at=now,
            error_class=error_class.value,
            error_message=sanitized_error,
        )
        session.add(attempt)

        if retryable and job.attempts_count < job.max_attempts:
            job.status = "RETRY_WAIT"
            job.assigned_worker_id = None
            job.lease_version += 1
            backoff_delay = min(60.0, 2.0 ** job.attempts_count)
            job.available_at = now + timedelta(seconds=backoff_delay)
        else:
            job.status = "DEAD_LETTER"
            job.completed_at = now
            dead_letter = WorkQueueDeadLetterModelV2(
                id=uuid.uuid4(),
                job_id=job.id,
                tenant_id=job.tenant_id,
                job_type=job.job_type,
                total_attempts=job.attempts_count,
                last_error_class=error_class.value,
                sanitized_error_message=sanitized_error,
                moved_to_dead_letter_at=now,
            )
            session.add(dead_letter)

        await session.commit()
        return True

    async def get_stats(self, session: AsyncSession, tenant_id: uuid.UUID | None = None) -> WorkQueueStatsV2:
        now = datetime.now(timezone.utc)
        stmt = select(WorkQueueJobModelV2.status, func.count())
        if tenant_id is not None:
            stmt = stmt.where(WorkQueueJobModelV2.tenant_id == tenant_id)
        stmt = stmt.group_by(WorkQueueJobModelV2.status)
        counts = dict((await session.execute(stmt)).all())

        workers_stmt = select(func.count()).select_from(WorkQueueAuditEventModelV2)
        active_workers = (await session.execute(workers_stmt)).scalar_one()

        bp_state = self.backpressure.evaluate_state(
            queue_depth=counts.get("QUEUED", 0),
            oldest_job_age_seconds=0.0,
            active_workers=max(1, active_workers),
            db_pool_utilization=0.1,
        )

        return WorkQueueStatsV2(
            total_queued=counts.get("QUEUED", 0),
            total_claimed=counts.get("CLAIMED", 0),
            total_running=counts.get("RUNNING", 0),
            total_succeeded=counts.get("SUCCEEDED", 0),
            total_failed=counts.get("FAILED", 0),
            total_dead_letter=counts.get("DEAD_LETTER", 0),
            total_cancelled=counts.get("CANCELLED", 0),
            active_workers_count=active_workers,
            backpressure_state=bp_state.state,
            evaluated_at=now,
        )
