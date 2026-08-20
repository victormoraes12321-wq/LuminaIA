from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from database import Base


CONTRACT_VERSION = "lumina.supervised-feedback/1.0"


class GovernedFeedbackRecord(Base):
    __tablename__ = "governed_feedback_records"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_feedback_tenant"),
        UniqueConstraint("id", "tenant_id", "user_id", name="uq_feedback_owner"),
        UniqueConstraint(
            "tenant_id", "user_id", "idempotency_key_hash",
            name="uq_feedback_idempotency",
        ),
        ForeignKeyConstraint(
            ["user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_feedback_author_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["response_node_id", "tenant_id", "user_id"],
            ["conversation_nodes.id", "conversation_nodes.tenant_id", "conversation_nodes.user_id"],
            name="fk_feedback_response_owner",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["reviewer_user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_feedback_reviewer_tenant",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "lifecycle IN ('RECEIVED','VALIDATED','TRIAGED','IN_REVIEW','APPROVED',"
            "'REJECTED','NEEDS_INFORMATION','WITHDRAWN','EXPIRED','ARCHIVED')",
            name="ck_feedback_lifecycle",
        ),
        CheckConstraint("lock_version >= 0", name="ck_feedback_lock"),
        CheckConstraint("checksum ~ '^[a-f0-9]{64}$'", name="ck_feedback_checksum"),
        CheckConstraint(
            "response_checksum ~ '^[a-f0-9]{64}$'", name="ck_feedback_response_checksum"
        ),
        CheckConstraint(
            "idempotency_key_hash ~ '^[a-f0-9]{64}$'", name="ck_feedback_idempotency"
        ),
        CheckConstraint(
            "reviewer_user_id IS NULL OR reviewer_user_id <> user_id",
            name="ck_feedback_no_self_review",
        ),
        CheckConstraint(
            "updated_at >= created_at", name="ck_feedback_timestamps"
        ),
        Index(
            "idx_feedback_owner_created",
            "tenant_id", "user_id", text("created_at DESC"), text("id DESC"),
        ),
        Index("idx_feedback_lifecycle", "tenant_id", "lifecycle", "created_at"),
        Index("idx_feedback_category", "tenant_id", "category", "created_at"),
        Index("idx_feedback_severity", "tenant_id", "severity", "created_at"),
        Index("idx_feedback_target", "tenant_id", "response_node_id"),
        Index("idx_feedback_duplicate", "tenant_id", "duplicate_fingerprint"),
        Index("idx_feedback_review_queue", "tenant_id", "review_queue", "lifecycle"),
        Index("idx_feedback_reviewer", "tenant_id", "reviewer_user_id", "lifecycle"),
        Index("idx_feedback_retention", "tenant_id", "retention_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    response_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    public_session_id: Mapped[str] = mapped_column(String(128), nullable=False)
    query_node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    response_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    response_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)
    lifecycle: Mapped[str] = mapped_column(String(32), nullable=False, default="RECEIVED")
    severity: Mapped[str | None] = mapped_column(String(16))
    priority: Mapped[str | None] = mapped_column(String(8))
    review_queue: Mapped[str | None] = mapped_column(String(32))
    triage_data: Mapped[dict | None] = mapped_column(JSONB)
    duplicate_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    redaction_manifest_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    review_decision: Mapped[str | None] = mapped_column(String(32))
    idempotency_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    lock_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False, default=CONTRACT_VERSION)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    retention_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    withdrawn_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class GovernedFeedbackCorrection(Base):
    __tablename__ = "governed_feedback_corrections"
    __table_args__ = (
        UniqueConstraint("feedback_id", "tenant_id", "user_id", name="uq_feedback_correction"),
        ForeignKeyConstraint(
            ["feedback_id", "tenant_id", "user_id"],
            ["governed_feedback_records.id", "governed_feedback_records.tenant_id",
             "governed_feedback_records.user_id"],
            name="fk_feedback_correction_owner",
            ondelete="CASCADE",
        ),
        CheckConstraint("jsonb_typeof(correction) = 'object'", name="ck_feedback_correction_json"),
        CheckConstraint("checksum ~ '^[a-f0-9]{64}$'", name="ck_feedback_correction_checksum"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    feedback_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    correction: Mapped[dict] = mapped_column(JSONB, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )


class GovernedFeedbackRedaction(Base):
    __tablename__ = "governed_feedback_redactions"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_feedback_redaction_tenant"),
        ForeignKeyConstraint(
            ["feedback_id", "tenant_id", "user_id"],
            ["governed_feedback_records.id", "governed_feedback_records.tenant_id",
             "governed_feedback_records.user_id"],
            name="fk_feedback_redaction_owner",
            ondelete="CASCADE",
        ),
        CheckConstraint("jsonb_typeof(manifest) = 'object'", name="ck_feedback_redaction_json"),
        CheckConstraint("checksum ~ '^[a-f0-9]{64}$'", name="ck_feedback_redaction_checksum"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    feedback_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest: Mapped[dict] = mapped_column(JSONB, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )


class GovernedFeedbackReview(Base):
    __tablename__ = "governed_feedback_reviews"
    __table_args__ = (
        UniqueConstraint("id", "feedback_id", "tenant_id", name="uq_feedback_review_scope"),
        ForeignKeyConstraint(
            ["feedback_id", "tenant_id"],
            ["governed_feedback_records.id", "governed_feedback_records.tenant_id"],
            name="fk_feedback_review_record",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["reviewer_user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_feedback_review_reviewer",
            ondelete="RESTRICT",
        ),
        CheckConstraint("checksum ~ '^[a-f0-9]{64}$'", name="ck_feedback_review_checksum"),
        CheckConstraint("jsonb_typeof(evidence) = 'array'", name="ck_feedback_review_evidence"),
        Index("idx_feedback_reviews_reviewer", "tenant_id", "reviewer_user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    feedback_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )


class GovernedFeedbackEvent(Base):
    __tablename__ = "governed_feedback_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["actor_user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_feedback_event_actor",
            ondelete="RESTRICT",
        ),
        CheckConstraint("jsonb_typeof(event_metadata) = 'object'", name="ck_feedback_event_json"),
        CheckConstraint("checksum ~ '^[a-f0-9]{64}$'", name="ck_feedback_event_checksum"),
        Index("idx_feedback_events_tenant_time", "tenant_id", text("created_at DESC"), text("id DESC")),
        Index("idx_feedback_events_record", "tenant_id", "feedback_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    feedback_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(128))
    event_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )


class SupervisedTrainingCandidate(Base):
    __tablename__ = "supervised_training_candidates"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_training_candidate_tenant"),
        UniqueConstraint("feedback_id", "tenant_id", name="uq_training_candidate_feedback"),
        ForeignKeyConstraint(
            ["feedback_id", "tenant_id"],
            ["governed_feedback_records.id", "governed_feedback_records.tenant_id"],
            name="fk_training_candidate_feedback",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["created_by_user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_training_candidate_creator",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('CANDIDATE','VALIDATED','APPROVED','REJECTED','IN_DATASET',"
            "'DEPRECATED','ARCHIVED')",
            name="ck_training_candidate_status",
        ),
        CheckConstraint("lock_version >= 0", name="ck_training_candidate_lock"),
        CheckConstraint("checksum ~ '^[a-f0-9]{64}$'", name="ck_training_candidate_checksum"),
        CheckConstraint("jsonb_typeof(input_data) = 'object'", name="ck_training_candidate_input"),
        CheckConstraint(
            "jsonb_typeof(expected_output) = 'object'", name="ck_training_candidate_output"
        ),
        Index("idx_training_candidates_status", "tenant_id", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    feedback_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="CANDIDATE")
    input_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    expected_output: Mapped[dict] = mapped_column(JSONB, nullable=False)
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False)
    quality_rule_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    lock_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SupervisedTrainingExample(Base):
    __tablename__ = "supervised_training_examples"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_training_example_tenant"),
        UniqueConstraint("candidate_id", "tenant_id", name="uq_training_example_candidate"),
        ForeignKeyConstraint(
            ["candidate_id", "tenant_id"],
            ["supervised_training_candidates.id", "supervised_training_candidates.tenant_id"],
            name="fk_training_example_candidate",
            ondelete="RESTRICT",
        ),
        CheckConstraint("checksum ~ '^[a-f0-9]{64}$'", name="ck_training_example_checksum"),
        CheckConstraint("quality_score BETWEEN 0 AND 100", name="ck_training_example_quality"),
        Index("idx_training_examples_tenant", "tenant_id", "created_at", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    candidate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    curator_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    example_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    quality_score: Mapped[int] = mapped_column(Integer, nullable=False)
    restrictions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    deprecated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )


class TrainingDatasetSnapshot(Base):
    __tablename__ = "training_dataset_snapshots"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_dataset_snapshot_tenant"),
        UniqueConstraint("dataset_id", "tenant_id", "version", name="uq_dataset_version"),
        ForeignKeyConstraint(
            ["created_by_user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_dataset_creator",
            ondelete="RESTRICT",
        ),
        CheckConstraint("version >= 1", name="ck_dataset_version"),
        CheckConstraint("lock_version >= 0", name="ck_dataset_lock"),
        CheckConstraint("checksum ~ '^[a-f0-9]{64}$'", name="ck_dataset_checksum"),
        CheckConstraint(
            "status IN ('DRAFT','IN_REVIEW','APPROVED','PUBLISHED','REJECTED',"
            "'DEPRECATED','ARCHIVED')",
            name="ck_dataset_status",
        ),
        CheckConstraint(
            "(status = 'PUBLISHED' AND published_at IS NOT NULL) OR status <> 'PUBLISHED'",
            name="ck_dataset_published_at",
        ),
        Index("idx_dataset_versions", "tenant_id", "dataset_id", text("version DESC")),
        Index("idx_dataset_status", "tenant_id", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT")
    manifest: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    lock_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class TrainingDatasetMember(Base):
    __tablename__ = "training_dataset_members"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "example_id", "tenant_id", name="uq_dataset_member"),
        ForeignKeyConstraint(
            ["snapshot_id", "tenant_id"],
            ["training_dataset_snapshots.id", "training_dataset_snapshots.tenant_id"],
            name="fk_dataset_member_snapshot",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["example_id", "tenant_id"],
            ["supervised_training_examples.id", "supervised_training_examples.tenant_id"],
            name="fk_dataset_member_example",
            ondelete="RESTRICT",
        ),
        Index("idx_dataset_members_snapshot", "tenant_id", "snapshot_id", "position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    example_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    example_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )


class TrainingDatasetExport(Base):
    __tablename__ = "training_dataset_exports"
    __table_args__ = (
        ForeignKeyConstraint(
            ["snapshot_id", "tenant_id"],
            ["training_dataset_snapshots.id", "training_dataset_snapshots.tenant_id"],
            name="fk_dataset_export_snapshot",
            ondelete="RESTRICT",
        ),
        CheckConstraint("content_checksum ~ '^[a-f0-9]{64}$'", name="ck_dataset_export_checksum"),
        Index("idx_dataset_exports_tenant", "tenant_id", "created_at", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    purpose: Mapped[str] = mapped_column(String(500), nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_size: Mapped[int] = mapped_column(Integer, nullable=False)
    manifest_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    content_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )


class FeedbackDeletionRequest(Base):
    __tablename__ = "feedback_deletion_requests"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "user_id", "idempotency_key_hash",
            name="uq_feedback_deletion_idempotency",
        ),
        ForeignKeyConstraint(
            ["feedback_id", "tenant_id", "user_id"],
            ["governed_feedback_records.id", "governed_feedback_records.tenant_id",
             "governed_feedback_records.user_id"],
            name="fk_feedback_deletion_owner",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('PENDING','COMPLETED','REJECTED')",
            name="ck_feedback_deletion_status",
        ),
        Index(
            "idx_feedback_deletions_status",
            "tenant_id", "status", "requested_at", "id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    feedback_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    reason: Mapped[str | None] = mapped_column(Text)
    idempotency_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
