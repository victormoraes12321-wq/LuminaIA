"""Strict Pydantic v2 models for LuminaAI Governed Work Queue, Concurrency, and Performance."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from contracts.work_queue_v2.enums import (
    ConcurrencyClassV2,
    PerformanceLoadLevelV2,
    ResourceWorkloadClassV2,
    WorkQueueAdmissionDecisionKindV2,
    WorkQueueBackpressureStateKindV2,
    WorkQueueErrorClassV2,
    WorkQueueJobPriorityV2,
    WorkQueueJobStatusV2,
    WorkQueueJobTypeV2,
    WorkQueueWorkerStatusKindV2,
)


class WorkQueueJobPayloadEnvelopeV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    job_type: WorkQueueJobTypeV2 = Field(...)
    payload_version: str = Field(default="1.0", min_length=1, max_length=16)
    canonical_reference_id: str = Field(..., min_length=1, max_length=128)
    parameters: dict[str, str] = Field(default_factory=dict)
    payload_checksum: str = Field(..., min_length=64, max_length=64)


class WorkQueueJobResultV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    success: bool = Field(...)
    result_code: str = Field(..., min_length=1, max_length=64)
    summary: str = Field(..., min_length=1, max_length=512)
    output_reference_id: str | None = Field(default=None, max_length=128)
    details: dict[str, str] = Field(default_factory=dict)
    completed_at: datetime = Field(...)


class WorkQueueJobErrorV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    error_class: WorkQueueErrorClassV2 = Field(...)
    message: str = Field(..., min_length=1, max_length=512)
    retryable: bool = Field(...)
    failed_at: datetime = Field(...)
    context_data: dict[str, str] = Field(default_factory=dict)


class WorkQueueJobAttemptV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    attempt_number: int = Field(..., ge=1, le=100)
    worker_id: str = Field(..., min_length=1, max_length=128)
    started_at: datetime = Field(...)
    ended_at: datetime | None = Field(default=None)
    status: WorkQueueJobStatusV2 = Field(...)
    error: WorkQueueJobErrorV2 | None = Field(default=None)


class WorkQueueLeaseV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    job_id: str = Field(..., min_length=1, max_length=128)
    worker_id: str = Field(..., min_length=1, max_length=128)
    lease_version: int = Field(..., ge=1)
    claimed_at: datetime = Field(...)
    expires_at: datetime = Field(...)
    last_heartbeat_at: datetime = Field(...)


class WorkQueueHeartbeatV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    job_id: str = Field(..., min_length=1, max_length=128)
    worker_id: str = Field(..., min_length=1, max_length=128)
    lease_version: int = Field(..., ge=1)
    heartbeat_at: datetime = Field(...)
    extended_expires_at: datetime = Field(...)


class WorkQueueRetryPolicyV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    max_attempts: int = Field(default=3, ge=1, le=20)
    initial_backoff_seconds: float = Field(default=1.0, ge=0.1, le=300.0)
    max_backoff_seconds: float = Field(default=60.0, ge=1.0, le=3600.0)
    backoff_multiplier: float = Field(default=2.0, ge=1.0, le=10.0)
    retryable_errors: tuple[WorkQueueErrorClassV2, ...] = Field(
        default=(
            WorkQueueErrorClassV2.DATABASE_TRANSIENT,
            WorkQueueErrorClassV2.TEMPORARY_RESOURCE_EXHAUSTION,
            WorkQueueErrorClassV2.LEASE_LOST,
            WorkQueueErrorClassV2.DEPENDENCY_TEMPORARILY_UNAVAILABLE,
            WorkQueueErrorClassV2.TIMEOUT_RETRYABLE,
        )
    )


class WorkQueueBackoffPolicyV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    base_seconds: float = Field(default=1.0, ge=0.1, le=60.0)
    max_seconds: float = Field(default=60.0, ge=1.0, le=3600.0)
    jitter_factor: float = Field(default=0.1, ge=0.0, le=0.5)


class WorkQueueConcurrencyPolicyV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    concurrency_class: ConcurrencyClassV2 = Field(...)
    global_limit: int = Field(default=10, ge=1, le=100)
    tenant_limit: int = Field(default=3, ge=1, le=50)
    queue_depth_limit: int = Field(default=100, ge=1, le=10000)


class WorkQueueTenantQuotaV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    tenant_id: str = Field(..., min_length=1, max_length=128)
    max_active_jobs: int = Field(default=3, ge=1, le=50)
    max_queued_jobs: int = Field(default=50, ge=1, le=5000)
    current_active_jobs: int = Field(default=0, ge=0)
    current_queued_jobs: int = Field(default=0, ge=0)


class WorkQueueAdmissionDecisionV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    decision: WorkQueueAdmissionDecisionKindV2 = Field(...)
    job_type: WorkQueueJobTypeV2 = Field(...)
    tenant_id: str = Field(..., min_length=1, max_length=128)
    reason: str = Field(..., min_length=1, max_length=256)
    suggested_retry_delay_seconds: float | None = Field(default=None, ge=0.0, le=3600.0)


class WorkQueueBackpressureStateV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    state: WorkQueueBackpressureStateKindV2 = Field(...)
    queue_depth: int = Field(..., ge=0)
    oldest_job_age_seconds: float = Field(..., ge=0.0)
    active_workers: int = Field(..., ge=0)
    db_pool_utilization_ratio: float = Field(..., ge=0.0, le=1.0)
    evaluated_at: datetime = Field(...)


class WorkQueueDeadLetterV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    dead_letter_id: str = Field(..., min_length=1, max_length=128)
    job_id: str = Field(..., min_length=1, max_length=128)
    tenant_id: str = Field(..., min_length=1, max_length=128)
    job_type: WorkQueueJobTypeV2 = Field(...)
    total_attempts: int = Field(..., ge=1)
    last_error_class: WorkQueueErrorClassV2 = Field(...)
    sanitized_error_message: str = Field(..., min_length=1, max_length=512)
    moved_to_dead_letter_at: datetime = Field(...)


class WorkQueueCancellationRequestV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    job_id: str = Field(..., min_length=1, max_length=128)
    tenant_id: str = Field(..., min_length=1, max_length=128)
    requested_by_user_id: str = Field(..., min_length=1, max_length=128)
    reason: str = Field(..., min_length=1, max_length=256)
    requested_at: datetime = Field(...)


class WorkQueueWorkerV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    worker_id: str = Field(..., min_length=1, max_length=128)
    hostname: str = Field(..., min_length=1, max_length=128)
    process_id: int = Field(..., ge=1)
    started_at: datetime = Field(...)
    last_heartbeat_at: datetime = Field(...)
    status: WorkQueueWorkerStatusKindV2 = Field(...)
    supported_job_types: tuple[WorkQueueJobTypeV2, ...] = Field(...)
    active_jobs_count: int = Field(default=0, ge=0)


class WorkQueueWorkerStatusV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    worker_id: str = Field(..., min_length=1, max_length=128)
    status: WorkQueueWorkerStatusKindV2 = Field(...)
    active_jobs_count: int = Field(..., ge=0)
    updated_at: datetime = Field(...)


class WorkQueueBatchV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    batch_id: str = Field(..., min_length=1, max_length=128)
    tenant_id: str = Field(..., min_length=1, max_length=128)
    job_ids: tuple[str, ...] = Field(..., min_length=1, max_length=100)
    created_at: datetime = Field(...)


class WorkQueueStatsV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    contract_version: str = Field(default="lumina.scale-queues-performance/1.0", min_length=1, max_length=64)
    total_queued: int = Field(..., ge=0)
    total_claimed: int = Field(..., ge=0)
    total_running: int = Field(..., ge=0)
    total_succeeded: int = Field(..., ge=0)
    total_failed: int = Field(..., ge=0)
    total_dead_letter: int = Field(..., ge=0)
    total_cancelled: int = Field(..., ge=0)
    active_workers_count: int = Field(..., ge=0)
    backpressure_state: WorkQueueBackpressureStateKindV2 = Field(...)
    oldest_queued_job_age_seconds: float = Field(default=0.0, ge=0.0)
    evaluated_at: datetime = Field(...)


class WorkQueuePerformanceBudgetV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    max_latency_p95_ms: float = Field(default=500.0, ge=1.0)
    min_throughput_rps: float = Field(default=10.0, ge=0.1)
    max_db_connections_percent: float = Field(default=80.0, ge=10.0, le=100.0)
    max_error_rate_percent: float = Field(default=1.0, ge=0.0, le=100.0)


class WorkQueuePerformanceResultV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    run_id: str = Field(..., min_length=1, max_length=128)
    load_level: PerformanceLoadLevelV2 = Field(...)
    total_jobs_processed: int = Field(..., ge=1)
    duration_seconds: float = Field(..., ge=0.001)
    throughput_jobs_per_second: float = Field(..., ge=0.0)
    p50_latency_ms: float = Field(..., ge=0.0)
    p95_latency_ms: float = Field(..., ge=0.0)
    p99_latency_ms: float = Field(..., ge=0.0)
    min_latency_ms: float = Field(..., ge=0.0)
    max_latency_ms: float = Field(..., ge=0.0)
    success_count: int = Field(..., ge=0)
    error_count: int = Field(..., ge=0)
    dead_letter_count: int = Field(..., ge=0)
    singleflight_coalesced_count: int = Field(default=0, ge=0)
    executed_at: datetime = Field(...)


class WorkQueuePerformanceBaselineV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    baseline_id: str = Field(..., min_length=1, max_length=128)
    contract_version: str = Field(default="lumina.scale-queues-performance/1.0", min_length=1, max_length=64)
    origin_commit: str = Field(..., min_length=7, max_length=64)
    status: str = Field(default="PROVISIONAL", min_length=1, max_length=32)
    small_throughput_rps: float = Field(..., ge=0.0)
    small_p95_latency_ms: float = Field(..., ge=0.0)
    medium_throughput_rps: float = Field(..., ge=0.0)
    medium_p95_latency_ms: float = Field(..., ge=0.0)
    baseline_checksum: str = Field(..., min_length=64, max_length=64)
    created_at: datetime = Field(...)


class WorkQueueAuditEventV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    event_id: str = Field(..., min_length=1, max_length=128)
    tenant_id: str = Field(..., min_length=1, max_length=128)
    user_id: str | None = Field(default=None, max_length=128)
    job_id: str | None = Field(default=None, max_length=128)
    action: str = Field(..., min_length=1, max_length=64)
    details_checksum: str = Field(..., min_length=64, max_length=64)
    occurred_at: datetime = Field(...)


class WorkQueueJobV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    contract_version: str = Field(default="lumina.scale-queues-performance/1.0", min_length=1, max_length=64)
    job_id: str = Field(..., min_length=1, max_length=128)
    tenant_id: str = Field(..., min_length=1, max_length=128)
    job_type: WorkQueueJobTypeV2 = Field(...)
    priority: WorkQueueJobPriorityV2 = Field(default=WorkQueueJobPriorityV2.NORMAL)
    status: WorkQueueJobStatusV2 = Field(default=WorkQueueJobStatusV2.QUEUED)
    payload_envelope: WorkQueueJobPayloadEnvelopeV2 = Field(...)
    idempotency_key: str = Field(..., min_length=1, max_length=128)
    idempotency_fingerprint: str = Field(..., min_length=64, max_length=64)
    attempts_count: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=3, ge=1, le=20)
    assigned_worker_id: str | None = Field(default=None, max_length=128)
    lease_version: int = Field(default=0, ge=0)
    available_at: datetime = Field(...)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    claimed_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    last_error: WorkQueueJobErrorV2 | None = Field(default=None)
