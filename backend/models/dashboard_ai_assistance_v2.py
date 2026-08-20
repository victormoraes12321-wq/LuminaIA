"""Tenant-scoped persistence for ``lumina.dashboard-ai-assistance/1.0``."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKeyConstraint, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from database import Base

STATUSES = "('RECEIVED','ANALYZING','NEEDS_CLARIFICATION','RESOLVING','SYNTHESIZING','VALIDATING','READY_FOR_REVIEW','REJECTED','ACCEPTED','APPLYING','APPLIED','BLOCKED','FAILED','CANCELLED','SUPERSEDED','EXPIRED')"
OPERATIONS = "('CREATE_DASHBOARD','PROPOSE_VISUAL_CHANGE','PROPOSE_SEMANTIC_CHANGE','REVISE_PROPOSAL','EXPLAIN_PROPOSAL','CANCEL_PROPOSAL')"


class DashboardAiProposalModelV2(Base):
    __tablename__ = "dashboard_ai_proposals_v2"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_dashboard_ai_proposals_identity"),
        ForeignKeyConstraint(["created_by_user_id", "tenant_id"], ["users.id", "users.tenant_id"], name="fk_dashboard_ai_proposals_actor", ondelete="RESTRICT"),
        ForeignKeyConstraint(["target_dashboard_id", "tenant_id"], ["dashboards_v2.id", "dashboards_v2.tenant_id"], name="fk_dashboard_ai_proposals_target", ondelete="RESTRICT"),
        ForeignKeyConstraint(["target_revision_id", "target_dashboard_id", "tenant_id"], ["dashboard_revisions_v2.id", "dashboard_revisions_v2.dashboard_id", "dashboard_revisions_v2.tenant_id"], name="fk_dashboard_ai_proposals_target_revision", ondelete="RESTRICT"),
        ForeignKeyConstraint(["applied_dashboard_id", "tenant_id"], ["dashboards_v2.id", "dashboards_v2.tenant_id"], name="fk_dashboard_ai_proposals_applied_dashboard", ondelete="RESTRICT"),
        ForeignKeyConstraint(["applied_revision_id", "applied_dashboard_id", "tenant_id"], ["dashboard_revisions_v2.id", "dashboard_revisions_v2.dashboard_id", "dashboard_revisions_v2.tenant_id"], name="fk_dashboard_ai_proposals_applied_revision", ondelete="RESTRICT"),
        CheckConstraint(f"operation IN {OPERATIONS}", name="ck_dashboard_ai_proposals_operation"),
        CheckConstraint(f"status IN {STATUSES} AND current_version >= 1 AND lock_version >= 1", name="ck_dashboard_ai_proposals_state"),
        Index("idx_dashboard_ai_proposals_owner", "tenant_id", "created_by_user_id", "updated_at", "id"),
        Index("idx_dashboard_ai_proposals_status", "tenant_id", "status", "updated_at", "id"),
        Index("idx_dashboard_ai_proposals_idempotency", "tenant_id", "idempotency_scope", unique=True),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    operation: Mapped[str] = mapped_column(String(40), nullable=False)
    origin: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    lock_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    target_dashboard_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    target_revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    applied_dashboard_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    applied_revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    intent_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    instruction_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_scope: Mapped[str] = mapped_column(String(64), nullable=False)
    request_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False, default="lumina.dashboard-ai-assistance/1.0")
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class DashboardAiProposalVersionModelV2(Base):
    __tablename__ = "dashboard_ai_proposal_versions_v2"
    __table_args__ = (
        UniqueConstraint("id", "proposal_id", "tenant_id", name="uq_dashboard_ai_versions_identity"),
        UniqueConstraint("tenant_id", "proposal_id", "version", name="uq_dashboard_ai_versions_number"),
        ForeignKeyConstraint(["proposal_id", "tenant_id"], ["dashboard_ai_proposals_v2.id", "dashboard_ai_proposals_v2.tenant_id"], name="fk_dashboard_ai_versions_proposal", ondelete="RESTRICT"),
        ForeignKeyConstraint(["created_by_user_id", "tenant_id"], ["users.id", "users.tenant_id"], name="fk_dashboard_ai_versions_actor", ondelete="RESTRICT"),
        CheckConstraint(f"status IN {STATUSES} AND version >= 1", name="ck_dashboard_ai_versions_state"),
        CheckConstraint("length(content_checksum)=64", name="ck_dashboard_ai_versions_checksum"),
        Index("idx_dashboard_ai_versions_proposal", "tenant_id", "proposal_id", "version"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    content_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    content_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class DashboardAiClarificationModelV2(Base):
    __tablename__ = "dashboard_ai_clarifications_v2"
    __table_args__ = (
        UniqueConstraint("id", "proposal_id", "tenant_id", name="uq_dashboard_ai_clarifications_identity"),
        ForeignKeyConstraint(["proposal_id", "tenant_id"], ["dashboard_ai_proposals_v2.id", "dashboard_ai_proposals_v2.tenant_id"], name="fk_dashboard_ai_clarifications_proposal", ondelete="RESTRICT"),
        ForeignKeyConstraint(["answered_by_user_id", "tenant_id"], ["users.id", "users.tenant_id"], name="fk_dashboard_ai_clarifications_actor", ondelete="RESTRICT"),
        CheckConstraint("proposal_version >= 1 AND lock_version >= 1 AND status IN ('OPEN','ANSWERED','EXPIRED','SUPERSEDED')", name="ck_dashboard_ai_clarifications_state"),
        Index("idx_dashboard_ai_clarifications_open", "tenant_id", "proposal_id", "status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    proposal_version: Mapped[int] = mapped_column(Integer, nullable=False)
    question_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    response_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")
    lock_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    answered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    answered_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)


class DashboardAiEvidenceModelV2(Base):
    __tablename__ = "dashboard_ai_evidence_v2"
    __table_args__ = (
        UniqueConstraint("id", "proposal_id", "tenant_id", name="uq_dashboard_ai_evidence_identity"),
        UniqueConstraint("tenant_id", "proposal_id", "proposal_version", "evidence_checksum", name="uq_dashboard_ai_evidence_checksum"),
        ForeignKeyConstraint(["proposal_id", "tenant_id"], ["dashboard_ai_proposals_v2.id", "dashboard_ai_proposals_v2.tenant_id"], name="fk_dashboard_ai_evidence_proposal", ondelete="RESTRICT"),
        Index("idx_dashboard_ai_evidence_proposal", "tenant_id", "proposal_id", "proposal_version"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    proposal_version: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False)
    canonical_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    public_label: Mapped[str] = mapped_column(String(160), nullable=False)
    authority_version: Mapped[str] = mapped_column(String(96), nullable=False)
    evidence_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class DashboardAiDecisionModelV2(Base):
    __tablename__ = "dashboard_ai_decisions_v2"
    __table_args__ = (
        UniqueConstraint("id", "proposal_id", "tenant_id", name="uq_dashboard_ai_decisions_identity"),
        UniqueConstraint("tenant_id", "proposal_id", "proposal_version", name="uq_dashboard_ai_decisions_version"),
        ForeignKeyConstraint(["proposal_id", "tenant_id"], ["dashboard_ai_proposals_v2.id", "dashboard_ai_proposals_v2.tenant_id"], name="fk_dashboard_ai_decisions_proposal", ondelete="RESTRICT"),
        ForeignKeyConstraint(["decided_by_user_id", "tenant_id"], ["users.id", "users.tenant_id"], name="fk_dashboard_ai_decisions_actor", ondelete="RESTRICT"),
        CheckConstraint("decision IN ('ACCEPT','REJECT') AND proposal_version >= 1", name="ck_dashboard_ai_decisions_value"),
        Index("idx_dashboard_ai_decisions_proposal", "tenant_id", "proposal_id", "decided_at"),
        Index("idx_dashboard_ai_decisions_idempotency", "tenant_id", "idempotency_scope", unique=True),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    proposal_version: Mapped[int] = mapped_column(Integer, nullable=False)
    decision: Mapped[str] = mapped_column(String(12), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    decided_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    idempotency_scope: Mapped[str] = mapped_column(String(64), nullable=False)
    request_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class DashboardAiRunModelV2(Base):
    __tablename__ = "dashboard_ai_runs_v2"
    __table_args__ = (
        UniqueConstraint("id", "proposal_id", "tenant_id", name="uq_dashboard_ai_runs_identity"),
        ForeignKeyConstraint(["proposal_id", "tenant_id"], ["dashboard_ai_proposals_v2.id", "dashboard_ai_proposals_v2.tenant_id"], name="fk_dashboard_ai_runs_proposal", ondelete="RESTRICT"),
        CheckConstraint("status IN ('RUNNING','SUCCEEDED','FAILED','CANCELLED','BLOCKED')", name="ck_dashboard_ai_runs_status"),
        Index("idx_dashboard_ai_runs_proposal", "tenant_id", "proposal_id", "started_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    orchestration_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    budget_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    input_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    usage_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)


class DashboardAiAuditEventModelV2(Base):
    __tablename__ = "dashboard_ai_audit_events_v2"
    __table_args__ = (
        UniqueConstraint("id", "proposal_id", "tenant_id", name="uq_dashboard_ai_audit_identity"),
        ForeignKeyConstraint(["proposal_id", "tenant_id"], ["dashboard_ai_proposals_v2.id", "dashboard_ai_proposals_v2.tenant_id"], name="fk_dashboard_ai_audit_proposal", ondelete="RESTRICT"),
        ForeignKeyConstraint(["actor_user_id", "tenant_id"], ["users.id", "users.tenant_id"], name="fk_dashboard_ai_audit_actor", ondelete="RESTRICT"),
        CheckConstraint("outcome IN ('SUCCESS','DENIED','CONFLICT','FAILED')", name="ck_dashboard_ai_audit_outcome"),
        Index("idx_dashboard_ai_audit_timeline", "tenant_id", "proposal_id", "occurred_at", "id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    metadata_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class DashboardAiEvaluationCaseModelV2(Base):
    __tablename__ = "dashboard_ai_evaluation_cases_v2"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_dashboard_ai_eval_cases_identity"),
        UniqueConstraint("tenant_id", "case_key", name="uq_dashboard_ai_eval_cases_key"),
        CheckConstraint("status IN ('ACTIVE','ARCHIVED')", name="ck_dashboard_ai_eval_cases_status"),
        Index("idx_dashboard_ai_eval_cases_category", "tenant_id", "category", "status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    case_key: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    input_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    expected_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    fixture_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class DashboardAiEvaluationResultModelV2(Base):
    __tablename__ = "dashboard_ai_evaluation_results_v2"
    __table_args__ = (
        ForeignKeyConstraint(["case_id", "tenant_id"], ["dashboard_ai_evaluation_cases_v2.id", "dashboard_ai_evaluation_cases_v2.tenant_id"], name="fk_dashboard_ai_eval_results_case", ondelete="RESTRICT"),
        Index("idx_dashboard_ai_eval_results_case", "tenant_id", "case_id", "executed_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    actual_status: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    result_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
