"""Work Queue Backpressure & Admission Control Service V2."""
from __future__ import annotations

from datetime import datetime, timezone
from contracts.work_queue_v2.enums import (
    WorkQueueAdmissionDecisionKindV2,
    WorkQueueBackpressureStateKindV2,
    WorkQueueJobPriorityV2,
    WorkQueueJobTypeV2,
)
from contracts.work_queue_v2.models import (
    WorkQueueAdmissionDecisionV2,
    WorkQueueBackpressureStateV2,
)


class WorkQueueBackpressureServiceV2:
    """Monitors queue health metrics and performs admission control."""

    def __init__(
        self,
        max_queue_depth: int = 500,
        max_tenant_depth: int = 50,
        oldest_job_threshold_seconds: float = 300.0,
    ) -> None:
        self.max_queue_depth = max_queue_depth
        self.max_tenant_depth = max_tenant_depth
        self.oldest_job_threshold_seconds = oldest_job_threshold_seconds

    def evaluate_state(
        self,
        queue_depth: int,
        oldest_job_age_seconds: float,
        active_workers: int,
        db_pool_utilization: float,
        is_draining: bool = False,
    ) -> WorkQueueBackpressureStateV2:
        now = datetime.now(timezone.utc)
        if is_draining:
            kind = WorkQueueBackpressureStateKindV2.DRAINING
        elif queue_depth >= self.max_queue_depth or db_pool_utilization >= 0.95:
            kind = WorkQueueBackpressureStateKindV2.REJECTING
        elif queue_depth >= self.max_queue_depth * 0.8 or db_pool_utilization >= 0.85:
            kind = WorkQueueBackpressureStateKindV2.SATURATED
        elif queue_depth >= self.max_queue_depth * 0.5 or oldest_job_age_seconds >= self.oldest_job_threshold_seconds:
            kind = WorkQueueBackpressureStateKindV2.ELEVATED
        else:
            kind = WorkQueueBackpressureStateKindV2.NORMAL

        return WorkQueueBackpressureStateV2(
            state=kind,
            queue_depth=queue_depth,
            oldest_job_age_seconds=oldest_job_age_seconds,
            active_workers=active_workers,
            db_pool_utilization_ratio=min(1.0, max(0.0, db_pool_utilization)),
            evaluated_at=now,
        )

    def evaluate_admission(
        self,
        job_type: WorkQueueJobTypeV2,
        tenant_id: str,
        priority: WorkQueueJobPriorityV2,
        current_state: WorkQueueBackpressureStateV2,
        tenant_current_queued_jobs: int = 0,
    ) -> WorkQueueAdmissionDecisionV2:
        if current_state.state == WorkQueueBackpressureStateKindV2.DRAINING:
            return WorkQueueAdmissionDecisionV2(
                decision=WorkQueueAdmissionDecisionKindV2.BLOCK,
                job_type=job_type,
                tenant_id=tenant_id,
                reason="Work queue is currently draining for shutdown",
            )

        if tenant_current_queued_jobs >= self.max_tenant_depth and priority != WorkQueueJobPriorityV2.CRITICAL:
            return WorkQueueAdmissionDecisionV2(
                decision=WorkQueueAdmissionDecisionKindV2.REJECT_RETRYABLE,
                job_type=job_type,
                tenant_id=tenant_id,
                reason=f"Tenant queued jobs limit ({self.max_tenant_depth}) reached",
                suggested_retry_delay_seconds=10.0,
            )

        if current_state.state == WorkQueueBackpressureStateKindV2.REJECTING:
            if priority == WorkQueueJobPriorityV2.CRITICAL:
                return WorkQueueAdmissionDecisionV2(
                    decision=WorkQueueAdmissionDecisionKindV2.ACCEPT_DELAYED,
                    job_type=job_type,
                    tenant_id=tenant_id,
                    reason="Queue rejecting non-critical traffic; accepting critical job with delay",
                    suggested_retry_delay_seconds=2.0,
                )
            return WorkQueueAdmissionDecisionV2(
                decision=WorkQueueAdmissionDecisionKindV2.REJECT_RETRYABLE,
                job_type=job_type,
                tenant_id=tenant_id,
                reason="Queue capacity saturated; non-critical jobs rejected with backpressure",
                suggested_retry_delay_seconds=15.0,
            )

        if current_state.state == WorkQueueBackpressureStateKindV2.SATURATED and priority in (WorkQueueJobPriorityV2.LOW, WorkQueueJobPriorityV2.BACKGROUND):
            return WorkQueueAdmissionDecisionV2(
                decision=WorkQueueAdmissionDecisionKindV2.DEFER,
                job_type=job_type,
                tenant_id=tenant_id,
                reason="Queue elevated pressure; low-priority job deferred",
                suggested_retry_delay_seconds=5.0,
            )

        return WorkQueueAdmissionDecisionV2(
            decision=WorkQueueAdmissionDecisionKindV2.ACCEPT,
            job_type=job_type,
            tenant_id=tenant_id,
            reason="Admission approved",
        )
