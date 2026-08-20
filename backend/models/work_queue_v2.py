"""SQLAlchemy 2 async models for V2 Governed Work Queue and Performance platform."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import (
    CheckConstraint,
    Index,
    String,
    Table,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION, JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class WorkQueueJobModelV2(Base):
    __tablename__ = "governed_work_queue_jobs_v2"
    __table_args__ = (
        UniqueConstraint("tenant_id", "job_type", "idempotency_key", name="uq_wq_job_idempotency"),
        CheckConstraint(text("attempts_count >= 0"), name="ck_wq_job_attempts"),
        CheckConstraint(text("max_attempts > 0"), name="ck_wq_job_max_attempts"),
        CheckConstraint(
            text("status IN ('QUEUED','CLAIMED','RUNNING','RETRY_WAIT','SUCCEEDED','BLOCKED','CANCEL_REQUESTED','CANCELLED','FAILED','DEAD_LETTER','EXPIRED')"),
            name="ck_wq_job_status",
        ),
        CheckConstraint(
            text("priority IN ('CRITICAL','HIGH','NORMAL','LOW','BACKGROUND')"),
            name="ck_wq_job_priority",
        ),
        Index("ix_wq_jobs_claim", "status", "available_at", "priority"),
        Index("ix_wq_jobs_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="QUEUED")
    priority: Mapped[str] = mapped_column(String(32), nullable=False, server_default="NORMAL")
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    payload_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    attempts_count: Mapped[int] = mapped_column(nullable=False, server_default="0")
    max_attempts: Mapped[int] = mapped_column(nullable=False, server_default="3")
    assigned_worker_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_version: Mapped[int] = mapped_column(nullable=False, server_default="0")
    available_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    claimed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    last_error_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)


class WorkQueueAttemptModelV2(Base):
    __tablename__ = "governed_work_queue_attempts_v2"
    __table_args__ = (
        Index("ix_wq_attempts_job", "job_id"),
        Index("ix_wq_attempts_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    attempt_number: Mapped[int] = mapped_column(nullable=False)
    worker_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    ended_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    error_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    context_data_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class WorkQueueWorkerModelV2(Base):
    __tablename__ = "governed_work_queue_workers_v2"
    __table_args__ = (
        CheckConstraint(text("active_jobs_count >= 0"), name="ck_wq_worker_active_jobs"),
    )

    worker_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    hostname: Mapped[str] = mapped_column(String(128), nullable=False)
    process_id: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="STARTING")
    supported_job_types_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    active_jobs_count: Mapped[int] = mapped_column(nullable=False, server_default="0")
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    last_heartbeat_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))


class WorkQueueDeadLetterModelV2(Base):
    __tablename__ = "governed_work_queue_dead_letters_v2"
    __table_args__ = (
        Index("ix_wq_dead_letters_tenant", "tenant_id"),
        Index("ix_wq_dead_letters_job", "job_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    total_attempts: Mapped[int] = mapped_column(nullable=False)
    last_error_class: Mapped[str] = mapped_column(String(64), nullable=False)
    sanitized_error_message: Mapped[str] = mapped_column(String(512), nullable=False)
    moved_to_dead_letter_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))


class WorkQueueAuditEventModelV2(Base):
    __tablename__ = "governed_work_queue_audit_events_v2"
    __table_args__ = (
        Index("ix_wq_audit_tenant", "tenant_id"),
        Index("ix_wq_audit_occurred", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    details_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))


class PerformanceBaselineModelV2(Base):
    __tablename__ = "performance_baselines_v2"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    baseline_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    origin_commit: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="PROVISIONAL")
    small_throughput_rps: Mapped[float] = mapped_column(DOUBLE_PRECISION, nullable=False)
    small_p95_latency_ms: Mapped[float] = mapped_column(DOUBLE_PRECISION, nullable=False)
    medium_throughput_rps: Mapped[float] = mapped_column(DOUBLE_PRECISION, nullable=False)
    medium_p95_latency_ms: Mapped[float] = mapped_column(DOUBLE_PRECISION, nullable=False)
    baseline_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))


class PerformanceRunModelV2(Base):
    __tablename__ = "performance_runs_v2"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    load_level: Mapped[str] = mapped_column(String(32), nullable=False)
    total_jobs_processed: Mapped[int] = mapped_column(nullable=False)
    duration_seconds: Mapped[float] = mapped_column(DOUBLE_PRECISION, nullable=False)
    throughput_jobs_per_second: Mapped[float] = mapped_column(DOUBLE_PRECISION, nullable=False)
    p50_latency_ms: Mapped[float] = mapped_column(DOUBLE_PRECISION, nullable=False)
    p95_latency_ms: Mapped[float] = mapped_column(DOUBLE_PRECISION, nullable=False)
    p99_latency_ms: Mapped[float] = mapped_column(DOUBLE_PRECISION, nullable=False)
    min_latency_ms: Mapped[float] = mapped_column(DOUBLE_PRECISION, nullable=False)
    max_latency_ms: Mapped[float] = mapped_column(DOUBLE_PRECISION, nullable=False)
    success_count: Mapped[int] = mapped_column(nullable=False)
    error_count: Mapped[int] = mapped_column(nullable=False)
    dead_letter_count: Mapped[int] = mapped_column(nullable=False)
    singleflight_coalesced_count: Mapped[int] = mapped_column(nullable=False, server_default="0")
    executed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
