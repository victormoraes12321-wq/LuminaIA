"""FastAPI Pydantic v2 schemas for V2 Governed Work Queue and Performance management."""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from contracts.work_queue_v2.enums import (
    PerformanceLoadLevelV2,
    WorkQueueBackpressureStateKindV2,
    WorkQueueErrorClassV2,
    WorkQueueJobPriorityV2,
    WorkQueueJobStatusV2,
    WorkQueueJobTypeV2,
    WorkQueueWorkerStatusKindV2,
)


class WorkQueueJobResponseV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    job_id: str = Field(..., min_length=1, max_length=128)
    tenant_id: str = Field(..., min_length=1, max_length=128)
    job_type: WorkQueueJobTypeV2 = Field(...)
    priority: WorkQueueJobPriorityV2 = Field(...)
    status: WorkQueueJobStatusV2 = Field(...)
    attempts_count: int = Field(..., ge=0)
    max_attempts: int = Field(..., ge=1)
    assigned_worker_id: str | None = Field(default=None, max_length=128)
    available_at: datetime = Field(...)
    created_at: datetime = Field(...)
    claimed_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    last_error_class: WorkQueueErrorClassV2 | None = Field(default=None)
    last_error_message: str | None = Field(default=None, max_length=512)


class WorkQueueJobListResponseV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    jobs: tuple[WorkQueueJobResponseV2, ...] = Field(...)
    total_count: int = Field(..., ge=0)


class WorkQueueCancelRequestV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    reason: str = Field(default="Administrative cancellation", min_length=1, max_length=256)


class WorkQueueReplayRequestV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    override_priority: WorkQueueJobPriorityV2 | None = Field(default=None)


class WorkQueueWorkerResponseV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    worker_id: str = Field(..., min_length=1, max_length=128)
    hostname: str = Field(..., min_length=1, max_length=128)
    process_id: int = Field(..., ge=1)
    status: WorkQueueWorkerStatusKindV2 = Field(...)
    active_jobs_count: int = Field(..., ge=0)
    started_at: datetime = Field(...)
    last_heartbeat_at: datetime = Field(...)


class WorkQueueWorkerListResponseV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    workers: tuple[WorkQueueWorkerResponseV2, ...] = Field(...)
    total_count: int = Field(..., ge=0)


class WorkQueueDeadLetterResponseV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    dead_letter_id: str = Field(..., min_length=1, max_length=128)
    job_id: str = Field(..., min_length=1, max_length=128)
    tenant_id: str = Field(..., min_length=1, max_length=128)
    job_type: WorkQueueJobTypeV2 = Field(...)
    total_attempts: int = Field(..., ge=1)
    last_error_class: WorkQueueErrorClassV2 = Field(...)
    sanitized_error_message: str = Field(..., min_length=1, max_length=512)
    moved_to_dead_letter_at: datetime = Field(...)


class WorkQueueDeadLetterListResponseV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    dead_letters: tuple[WorkQueueDeadLetterResponseV2, ...] = Field(...)
    total_count: int = Field(..., ge=0)


class WorkQueueStatsResponseV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

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


class PerformanceRunRequestV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    load_level: PerformanceLoadLevelV2 = Field(default=PerformanceLoadLevelV2.SMALL)
    total_jobs: int = Field(default=100, ge=1, le=10000)
    concurrency_level: int = Field(default=4, ge=1, le=16)


class PerformanceRunResponseV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    run_id: str = Field(..., min_length=1, max_length=128)
    load_level: PerformanceLoadLevelV2 = Field(...)
    total_jobs_processed: int = Field(..., ge=1)
    duration_seconds: float = Field(..., ge=0.0)
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


class PerformanceBaselineResponseV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    baseline_id: str = Field(..., min_length=1, max_length=128)
    contract_version: str = Field(..., min_length=1, max_length=64)
    origin_commit: str = Field(..., min_length=7, max_length=64)
    status: str = Field(..., min_length=1, max_length=32)
    small_throughput_rps: float = Field(..., ge=0.0)
    small_p95_latency_ms: float = Field(..., ge=0.0)
    medium_throughput_rps: float = Field(..., ge=0.0)
    medium_p95_latency_ms: float = Field(..., ge=0.0)
    baseline_checksum: str = Field(..., min_length=64, max_length=64)
    created_at: datetime = Field(...)
