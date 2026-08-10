"""Unit tests for V2 Governed Work Queue Pydantic contracts."""
from __future__ import annotations

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from contracts.work_queue_v2 import (
    ConcurrencyClassV2,
    PerformanceLoadLevelV2,
    WorkQueueAdmissionDecisionKindV2,
    WorkQueueAdmissionDecisionV2,
    WorkQueueBackpressureStateKindV2,
    WorkQueueBackpressureStateV2,
    WorkQueueConcurrencyPolicyV2,
    WorkQueueDeadLetterV2,
    WorkQueueErrorClassV2,
    WorkQueueHeartbeatV2,
    WorkQueueJobAttemptV2,
    WorkQueueJobErrorV2,
    WorkQueueJobPayloadEnvelopeV2,
    WorkQueueJobPriorityV2,
    WorkQueueJobResultV2,
    WorkQueueJobStatusV2,
    WorkQueueJobTypeV2,
    WorkQueueJobV2,
    WorkQueueLeaseV2,
    WorkQueuePerformanceBaselineV2,
    WorkQueuePerformanceResultV2,
    WorkQueueRetryPolicyV2,
    WorkQueueStatsV2,
    WorkQueueTenantQuotaV2,
    WorkQueueWorkerStatusKindV2,
    WorkQueueWorkerV2,
)


def test_work_queue_job_envelope_contract_valid() -> None:
    envelope = WorkQueueJobPayloadEnvelopeV2(
        job_type=WorkQueueJobTypeV2.POST_SYNC_INSIGHT_RUN,
        canonical_reference_id="run_123",
        parameters={"sync_id": "sync_abc"},
        payload_checksum="a" * 64,
    )
    assert envelope.job_type == WorkQueueJobTypeV2.POST_SYNC_INSIGHT_RUN
    assert envelope.payload_checksum == "a" * 64
    assert envelope.parameters["sync_id"] == "sync_abc"


def test_work_queue_job_envelope_forbidden_extra_fields() -> None:
    with pytest.raises(ValidationError):
        WorkQueueJobPayloadEnvelopeV2(
            job_type=WorkQueueJobTypeV2.POST_SYNC_INSIGHT_RUN,
            canonical_reference_id="run_123",
            payload_checksum="a" * 64,
            extra_field="unauthorized",
        )


def test_work_queue_job_model_instantiation() -> None:
    now = datetime.now(timezone.utc)
    envelope = WorkQueueJobPayloadEnvelopeV2(
        job_type=WorkQueueJobTypeV2.MATERIALIZATION_BUILD,
        canonical_reference_id="mat_001",
        payload_checksum="b" * 64,
    )
    job = WorkQueueJobV2(
        job_id="job_001",
        tenant_id="tenant_alpha",
        job_type=WorkQueueJobTypeV2.MATERIALIZATION_BUILD,
        priority=WorkQueueJobPriorityV2.HIGH,
        status=WorkQueueJobStatusV2.QUEUED,
        payload_envelope=envelope,
        idempotency_key="ik_001",
        idempotency_fingerprint="c" * 64,
        available_at=now,
        created_at=now,
        updated_at=now,
    )
    assert job.job_id == "job_001"
    assert job.status == WorkQueueJobStatusV2.QUEUED
    assert job.contract_version == "lumina.scale-queues-performance/1.0"


def test_work_queue_job_frozen_immutability() -> None:
    now = datetime.now(timezone.utc)
    envelope = WorkQueueJobPayloadEnvelopeV2(
        job_type=WorkQueueJobTypeV2.EVALUATION_RUN,
        canonical_reference_id="eval_001",
        payload_checksum="d" * 64,
    )
    job = WorkQueueJobV2(
        job_id="job_002",
        tenant_id="tenant_alpha",
        job_type=WorkQueueJobTypeV2.EVALUATION_RUN,
        payload_envelope=envelope,
        idempotency_key="ik_002",
        idempotency_fingerprint="e" * 64,
        available_at=now,
        created_at=now,
        updated_at=now,
    )
    with pytest.raises(ValidationError):
        job.status = WorkQueueJobStatusV2.RUNNING


def test_work_queue_stats_contract() -> None:
    now = datetime.now(timezone.utc)
    stats = WorkQueueStatsV2(
        total_queued=10,
        total_claimed=2,
        total_running=4,
        total_succeeded=100,
        total_failed=1,
        total_dead_letter=0,
        total_cancelled=0,
        active_workers_count=3,
        backpressure_state=WorkQueueBackpressureStateKindV2.NORMAL,
        evaluated_at=now,
    )
    assert stats.total_queued == 10
    assert stats.backpressure_state == WorkQueueBackpressureStateKindV2.NORMAL
    assert stats.contract_version == "lumina.scale-queues-performance/1.0"


def test_work_queue_performance_result_contract() -> None:
    now = datetime.now(timezone.utc)
    res = WorkQueuePerformanceResultV2(
        run_id="run_perf_001",
        load_level=PerformanceLoadLevelV2.SMALL,
        total_jobs_processed=100,
        duration_seconds=2.5,
        throughput_jobs_per_second=40.0,
        p50_latency_ms=12.0,
        p95_latency_ms=25.0,
        p99_latency_ms=45.0,
        min_latency_ms=5.0,
        max_latency_ms=60.0,
        success_count=100,
        error_count=0,
        dead_letter_count=0,
        executed_at=now,
    )
    assert res.run_id == "run_perf_001"
    assert res.throughput_jobs_per_second == 40.0
