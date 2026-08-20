"""Tenant-scoped persistence models for ``lumina.post-sync-insights/1.0``."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKeyConstraint, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from database import Base

TYPES = "('METRIC_INCREASE','METRIC_DECREASE','TARGET_REACHED','TARGET_MISSED','THRESHOLD_BREACH_HIGH','THRESHOLD_BREACH_LOW','RANKING_ENTRY','RANKING_EXIT','RANKING_MOVE_UP','RANKING_MOVE_DOWN','ANOMALY_HIGH','ANOMALY_LOW','FRESHNESS_DEGRADED','COMPLETENESS_DEGRADED','RECONCILIATION_VARIANCE','SOURCE_VOLUME_CHANGE','NEW_DATA_AVAILABLE','INSUFFICIENT_BASELINE','INSIGHT_RUN_BLOCKED')"
CATEGORIES = "('BUSINESS_PERFORMANCE','FINANCIAL','SALES','RECEIVABLES','INVENTORY','DATA_QUALITY','FRESHNESS','RECONCILIATION','OPERATIONAL_METADATA')"
SEVERITIES = "('INFO','LOW','MEDIUM','HIGH','CRITICAL')"
LIFECYCLES = "('REQUESTED','PLANNING','EXECUTING','VALIDATING','DETECTED','CERTIFIED','PUBLISHED','ACKNOWLEDGED','DISMISSED','EXPIRED','BLOCKED','FAILED','CANCELLED','SUPERSEDED')"


class PostSyncInsightPolicyModelV2(Base):
    __tablename__ = "post_sync_insight_policies_v2"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_ps_policies_identity"),
        UniqueConstraint("tenant_id", "policy_version", name="uq_ps_policies_version"),
        CheckConstraint("lock_version >= 1", name="ck_ps_policies_lock"),
        Index("idx_ps_policies_lookup", "tenant_id", "enabled", "updated_at", "id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    policy_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    lock_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False, default="lumina.post-sync-insights/1.0")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class PostSyncInsightOutboxModelV2(Base):
    __tablename__ = "post_sync_insight_outbox_v2"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_ps_outbox_identity"),
        Index("idx_ps_outbox_claim", "status", "next_attempt_at", "created_at", "id"),
        Index("idx_ps_outbox_idempotency", "tenant_id", "idempotency_scope", unique=True),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sync_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    idempotency_scope: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_attempt_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class PostSyncInsightRunModelV2(Base):
    __tablename__ = "post_sync_insight_runs_v2"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_ps_runs_identity"),
        ForeignKeyConstraint(["policy_id", "tenant_id"], ["post_sync_insight_policies_v2.id", "post_sync_insight_policies_v2.tenant_id"], name="fk_ps_runs_policy", ondelete="RESTRICT"),
        CheckConstraint(f"status IN {LIFECYCLES}", name="ck_ps_runs_status"),
        Index("idx_ps_runs_sync", "tenant_id", "sync_run_id", "started_at", "id"),
        Index("idx_ps_runs_status", "tenant_id", "status", "started_at", "id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sync_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    policy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="REQUESTED")
    candidates_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    suppressed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)


class PostSyncInsightDetectorExecutionModelV2(Base):
    __tablename__ = "post_sync_insight_detector_executions_v2"
    __table_args__ = (
        UniqueConstraint("id", "run_id", "tenant_id", name="uq_ps_detector_exec_identity"),
        ForeignKeyConstraint(["run_id", "tenant_id"], ["post_sync_insight_runs_v2.id", "post_sync_insight_runs_v2.tenant_id"], name="fk_ps_detector_exec_run", ondelete="RESTRICT"),
        Index("idx_ps_detector_exec_run", "tenant_id", "run_id", "detector_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    detector_id: Mapped[str] = mapped_column(String(64), nullable=False)
    detector_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="EXECUTING")
    candidates_detected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    executed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class PostSyncInsightCandidateModelV2(Base):
    __tablename__ = "post_sync_insight_candidates_v2"
    __table_args__ = (
        UniqueConstraint("id", "run_id", "tenant_id", name="uq_ps_candidates_identity"),
        ForeignKeyConstraint(["run_id", "tenant_id"], ["post_sync_insight_runs_v2.id", "post_sync_insight_runs_v2.tenant_id"], name="fk_ps_candidates_run", ondelete="RESTRICT"),
        CheckConstraint(f"insight_type IN {TYPES}", name="ck_ps_candidates_type"),
        CheckConstraint(f"category IN {CATEGORIES}", name="ck_ps_candidates_category"),
        CheckConstraint(f"severity IN {SEVERITIES}", name="ck_ps_candidates_severity"),
        Index("idx_ps_candidates_run", "tenant_id", "run_id", "score", "id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    insight_type: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class PostSyncInsightModelV2(Base):
    __tablename__ = "post_sync_insights_v2"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_ps_insights_identity"),
        ForeignKeyConstraint(["run_id", "tenant_id"], ["post_sync_insight_runs_v2.id", "post_sync_insight_runs_v2.tenant_id"], name="fk_ps_insights_run", ondelete="RESTRICT"),
        CheckConstraint(f"insight_type IN {TYPES}", name="ck_ps_insights_type"),
        CheckConstraint(f"category IN {CATEGORIES}", name="ck_ps_insights_category"),
        CheckConstraint(f"severity IN {SEVERITIES}", name="ck_ps_insights_severity"),
        CheckConstraint(f"lifecycle IN {LIFECYCLES}", name="ck_ps_insights_lifecycle"),
        Index("idx_ps_insights_feed", "tenant_id", "lifecycle", "severity", "published_at", "id"),
        Index("idx_ps_insights_fingerprint", "tenant_id", "fingerprint"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sync_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    insight_type: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    lifecycle: Mapped[str] = mapped_column(String(32), nullable=False, default="PUBLISHED")
    headline: Mapped[str] = mapped_column(String(255), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    metric_key: Mapped[str] = mapped_column(String(64), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    insight_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    published_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)


class PostSyncInsightEvidenceModelV2(Base):
    __tablename__ = "post_sync_insight_evidence_v2"
    __table_args__ = (
        UniqueConstraint("id", "insight_id", "tenant_id", name="uq_ps_evidence_identity"),
        ForeignKeyConstraint(["insight_id", "tenant_id"], ["post_sync_insights_v2.id", "post_sync_insights_v2.tenant_id"], name="fk_ps_evidence_insight", ondelete="RESTRICT"),
        Index("idx_ps_evidence_insight", "tenant_id", "insight_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    insight_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sync_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    metric_key: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class PostSyncInsightUserStateModelV2(Base):
    __tablename__ = "post_sync_insight_user_states_v2"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "insight_id", name="uq_ps_user_states"),
        ForeignKeyConstraint(["user_id", "tenant_id"], ["users.id", "users.tenant_id"], name="fk_ps_user_states_user", ondelete="RESTRICT"),
        ForeignKeyConstraint(["insight_id", "tenant_id"], ["post_sync_insights_v2.id", "post_sync_insights_v2.tenant_id"], name="fk_ps_user_states_insight", ondelete="RESTRICT"),
        Index("idx_ps_user_states_feed", "tenant_id", "user_id", "insight_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    insight_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dismissed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    dismiss_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class PostSyncInsightAuditEventModelV2(Base):
    __tablename__ = "post_sync_insight_audit_events_v2"
    __table_args__ = (
        Index("idx_ps_audit_timeline", "tenant_id", "created_at", "id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    insight_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    details_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class PostSyncInsightEvaluationCaseModelV2(Base):
    __tablename__ = "post_sync_insight_evaluation_cases_v2"
    __table_args__ = (
        Index("idx_ps_eval_cases", "tenant_id", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    case_key: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    case_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class PostSyncInsightEvaluationResultModelV2(Base):
    __tablename__ = "post_sync_insight_evaluation_results_v2"
    __table_args__ = (
        Index("idx_ps_eval_results", "tenant_id", "executed_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    case_key: Mapped[str] = mapped_column(String(64), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    result_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    executed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
