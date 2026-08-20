from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Float,
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

from database import Base

CONTRACT_VERSION = "lumina.ai-tool-registry/1.0"


class AIToolIdentity(Base):
    __tablename__ = "ai_tool_identities"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_ai_tool_identity_tenant"),
        UniqueConstraint("tenant_id", "canonical_name", name="uq_ai_tool_canonical_name"),
        CheckConstraint("risk_class IN ('LOW','MODERATE','HIGH','CRITICAL','FORBIDDEN')", name="ck_ai_tool_risk"),
        CheckConstraint("side_effect IN ('NONE','READ_ONLY','CACHE_ONLY','STATEFUL_IDEMPOTENT','STATEFUL_NON_IDEMPOTENT','ADMINISTRATIVE','DESTRUCTIVE','FORBIDDEN')", name="ck_ai_tool_side_effect"),
        CheckConstraint("network_class IN ('NO_NETWORK','INTERNAL_SERVICE_ONLY','ALLOWLISTED_EXTERNAL','ARBITRARY_EXTERNAL','FORBIDDEN')", name="ck_ai_tool_network"),
        CheckConstraint("data_class IN ('PUBLIC_METADATA','TENANT_METADATA','TENANT_BUSINESS_DATA','RESTRICTED_BUSINESS_DATA','PERSONAL_DATA','SENSITIVE_PERSONAL_DATA','SECRET','FORBIDDEN')", name="ck_ai_tool_data_class"),
        Index("idx_ai_tool_canonical_name", "tenant_id", "canonical_name"),
        Index("idx_ai_tool_risk_side_effect", "risk_class", "side_effect"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tool_id: Mapped[str] = mapped_column(String(128), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(64), nullable=False, default="business_intelligence")
    tool_type: Mapped[str] = mapped_column(String(64), nullable=False, default="DOMAIN_READ")
    capabilities: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    risk_class: Mapped[str] = mapped_column(String(32), nullable=False, default="LOW")
    side_effect: Mapped[str] = mapped_column(String(32), nullable=False, default="READ_ONLY")
    network_class: Mapped[str] = mapped_column(String(32), nullable=False, default="INTERNAL_SERVICE_ONLY")
    data_class: Mapped[str] = mapped_column(String(32), nullable=False, default="TENANT_BUSINESS_DATA")
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    scope: Mapped[str] = mapped_column(String(32), nullable=False, default="SYSTEM")
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False, default=CONTRACT_VERSION)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class AIToolVersion(Base):
    __tablename__ = "ai_tool_versions"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_ai_tool_version_tenant"),
        UniqueConstraint("tool_identity_id", "version", name="uq_ai_tool_version_identity"),
        ForeignKeyConstraint(
            ["tool_identity_id", "tenant_id"],
            ["ai_tool_identities.id", "ai_tool_identities.tenant_id"],
            name="fk_ai_tool_version_identity",
            ondelete="CASCADE",
        ),
        CheckConstraint("lifecycle IN ('DRAFT','IN_REVIEW','APPROVED','ACTIVE','DEPRECATED','DISABLED','RETIRED','REJECTED')", name="ck_ai_tool_lifecycle"),
        CheckConstraint("lock_version >= 1", name="ck_ai_tool_version_lock"),
        Index("idx_ai_tool_version_lifecycle", "tool_id", "lifecycle"),
        Index("idx_ai_tool_version_adapter", "adapter_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tool_identity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tool_id: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    adapter_id: Mapped[str] = mapped_column(String(128), nullable=False)
    input_contract: Mapped[dict] = mapped_column(JSONB, nullable=False)
    output_contract: Mapped[dict] = mapped_column(JSONB, nullable=False)
    execution_policy: Mapped[dict] = mapped_column(JSONB, nullable=False)
    dependencies: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    lifecycle: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    author_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reviewer_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    published_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    effective_from: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    effective_to: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    lock_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False, default=CONTRACT_VERSION)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class AIToolReview(Base):
    __tablename__ = "ai_tool_reviews"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tool_version_id", "tenant_id"],
            ["ai_tool_versions.id", "ai_tool_versions.tenant_id"],
            name="fk_ai_tool_review_version",
            ondelete="CASCADE",
        ),
        Index("idx_ai_tool_review_version", "tool_version_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tool_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reviewer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    review_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class AIToolPublication(Base):
    __tablename__ = "ai_tool_publications"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tool_version_id", "tenant_id"],
            ["ai_tool_versions.id", "ai_tool_versions.tenant_id"],
            name="fk_ai_tool_pub_version",
            ondelete="CASCADE",
        ),
        Index("idx_ai_tool_pub_version", "tool_version_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tool_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    published_by: Mapped[str] = mapped_column(String(128), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    publication_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    published_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class AIToolRegistrySnapshot(Base):
    __tablename__ = "ai_tool_registry_snapshots"
    __table_args__ = (
        UniqueConstraint("snapshot_id", name="uq_ai_tool_snapshot_id"),
        CheckConstraint("status IN ('DRAFT','VALIDATING','READY','PUBLISHED','REJECTED','DEPRECATED','ARCHIVED')", name="ck_ai_tool_snapshot_status"),
        Index("idx_ai_tool_snapshot_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_id: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="READY")
    active_tool_versions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    disabled_tool_ids: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    dependency_graph_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    published_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    previous_snapshot_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    published_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)


class AIToolRegistryMember(Base):
    __tablename__ = "ai_tool_registry_members"
    __table_args__ = (
        ForeignKeyConstraint(["snapshot_id"], ["ai_tool_registry_snapshots.id"], name="fk_ai_tool_member_snapshot", ondelete="CASCADE"),
        ForeignKeyConstraint(["tool_version_id"], ["ai_tool_versions.id"], name="fk_ai_tool_member_version", ondelete="CASCADE"),
        Index("idx_ai_tool_member_snapshot", "snapshot_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tool_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)


class AIToolDependency(Base):
    __tablename__ = "ai_tool_dependencies"
    __table_args__ = (
        ForeignKeyConstraint(["tool_version_id"], ["ai_tool_versions.id"], name="fk_ai_tool_dep_version", ondelete="CASCADE"),
        Index("idx_ai_tool_dep_version", "tool_version_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tool_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target_tool_id: Mapped[str] = mapped_column(String(128), nullable=False)
    min_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    max_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    dependency_type: Mapped[str] = mapped_column(String(32), nullable=False, default="REQUIRED")
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)


class AIToolEvent(Base):
    __tablename__ = "ai_tool_events"
    __table_args__ = (
        Index("idx_ai_tool_event_tenant_type", "tenant_id", "event_type"),
        Index("idx_ai_tool_event_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    tool_id: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class AIToolInvocationRecord(Base):
    __tablename__ = "ai_tool_invocation_records"
    __table_args__ = (
        Index("idx_ai_tool_inv_tenant_tool", "tenant_id", "tool_id", "created_at"),
        Index("idx_ai_tool_inv_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_id: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    snapshot_id: Mapped[str] = mapped_column(String(128), nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    input_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    output_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    circuit_state: Mapped[str] = mapped_column(String(32), nullable=False, default="CLOSED")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class AIToolCircuitStateRecord(Base):
    __tablename__ = "ai_tool_circuit_states"
    __table_args__ = (
        UniqueConstraint("tool_id", "version", "adapter_id", name="uq_ai_tool_circuit_state"),
        CheckConstraint("state IN ('CLOSED','OPEN','HALF_OPEN')", name="ck_ai_tool_circuit_state"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tool_id: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    adapter_id: Mapped[str] = mapped_column(String(128), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="CLOSED")
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_failure_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    last_state_change: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class AIToolEvaluationCaseRecord(Base):
    __tablename__ = "ai_tool_evaluation_cases"
    __table_args__ = (
        UniqueConstraint("case_id", name="uq_ai_tool_eval_case_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_id: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    input_fixture: Mapped[dict] = mapped_column(JSONB, nullable=False)
    expected_output_fixture: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    expected_error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class AIToolEvaluationResultRecord(Base):
    __tablename__ = "ai_tool_evaluation_results"
    __table_args__ = (
        Index("idx_ai_tool_eval_result_case", "case_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    case_id: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_id: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    execution_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False, default="")
    executed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
