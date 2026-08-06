"""Tenant-scoped ORM models for ``lumina.dashboard-backend/1.0``."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKeyConstraint, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from database import Base


CONTRACT_VERSION = "lumina.dashboard-backend/1.0"
LIFECYCLES = "('DRAFT','IN_REVIEW','APPROVED','PUBLISHED','SUPERSEDED','DEPRECATED','ARCHIVED','REJECTED')"
CLASSIFICATIONS = "('PUBLIC_METADATA','TENANT_METADATA','TENANT_BUSINESS_DATA','RESTRICTED_BUSINESS_DATA','PERSONAL_DATA','SENSITIVE_PERSONAL_DATA')"


class DashboardModelV2(Base):
    __tablename__ = "dashboards_v2"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_dashboards_v2_id_tenant"),
        UniqueConstraint("tenant_id", "canonical_name", name="uq_dashboards_v2_tenant_name"),
        ForeignKeyConstraint(["owner_user_id", "tenant_id"], ["users.id", "users.tenant_id"], name="fk_dashboards_v2_owner_tenant", ondelete="RESTRICT"),
        ForeignKeyConstraint(["attribution_dashboard_id", "tenant_id"], ["dashboards_v2.id", "dashboards_v2.tenant_id"], name="fk_dashboards_v2_attribution", ondelete="RESTRICT"),
        CheckConstraint(f"lifecycle IN {LIFECYCLES}", name="ck_dashboards_v2_lifecycle"),
        CheckConstraint(f"head_lifecycle IN {LIFECYCLES}", name="ck_dashboards_v2_head_lifecycle"),
        CheckConstraint(f"classification IN {CLASSIFICATIONS}", name="ck_dashboards_v2_classification"),
        CheckConstraint("lock_version >= 1", name="ck_dashboards_v2_lock"),
        CheckConstraint("ownership_type IN ('USER','TEAM','TENANT','SYSTEM_TEMPLATE')", name="ck_dashboards_v2_ownership"),
        Index("idx_dashboards_v2_lifecycle", "tenant_id", "lifecycle", "id"),
        Index("idx_dashboards_v2_owner", "tenant_id", "owner_user_id", "id"),
        Index("idx_dashboards_v2_updated", "tenant_id", "updated_at", "id"),
        Index("idx_dashboards_v2_idempotency", "tenant_id", "create_idempotency_scope", unique=True),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    ownership_type: Mapped[str] = mapped_column(String(24), nullable=False, default="USER")
    origin: Mapped[str] = mapped_column(String(32), nullable=False)
    lifecycle: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT")
    head_lifecycle: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT")
    classification: Mapped[str] = mapped_column(String(48), nullable=False)
    head_revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    attribution_dashboard_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    lock_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    create_idempotency_scope: Mapped[str] = mapped_column(String(64), nullable=False)
    create_request_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False, default=CONTRACT_VERSION)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class DashboardRevisionModelV2(Base):
    __tablename__ = "dashboard_revisions_v2"
    __table_args__ = (
        UniqueConstraint("id", "dashboard_id", "tenant_id", name="uq_dashboard_revisions_v2_identity"),
        UniqueConstraint("tenant_id", "dashboard_id", "revision_number", name="uq_dashboard_revisions_v2_number"),
        ForeignKeyConstraint(["dashboard_id", "tenant_id"], ["dashboards_v2.id", "dashboards_v2.tenant_id"], name="fk_dashboard_revisions_v2_dashboard", ondelete="RESTRICT"),
        ForeignKeyConstraint(["parent_revision_id", "dashboard_id", "tenant_id"], ["dashboard_revisions_v2.id", "dashboard_revisions_v2.dashboard_id", "dashboard_revisions_v2.tenant_id"], name="fk_dashboard_revisions_v2_parent", ondelete="RESTRICT"),
        ForeignKeyConstraint(["author_user_id", "tenant_id"], ["users.id", "users.tenant_id"], name="fk_dashboard_revisions_v2_author", ondelete="RESTRICT"),
        CheckConstraint("revision_number >= 1 AND semantic_revision >= 1 AND visual_revision >= 1 AND lock_version >= 1", name="ck_dashboard_revisions_v2_positive"),
        CheckConstraint("validation_status IN ('VALID','BLOCKED')", name="ck_dashboard_revisions_v2_validation"),
        CheckConstraint("length(blueprint_checksum)=64 AND length(semantic_checksum)=64 AND length(visual_checksum)=64", name="ck_dashboard_revisions_v2_checksums"),
        Index("idx_dashboard_revisions_v2_dashboard", "tenant_id", "dashboard_id", "revision_number"),
        Index("idx_dashboard_revisions_v2_blueprint", "tenant_id", "blueprint_checksum"),
        Index("idx_dashboard_revisions_v2_semantic", "tenant_id", "semantic_checksum"),
        Index("idx_dashboard_revisions_v2_visual", "tenant_id", "visual_checksum"),
        Index("idx_dashboard_revisions_v2_idempotency", "tenant_id", "idempotency_scope", unique=True),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dashboard_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    parent_revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    blueprint_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    blueprint_version: Mapped[str] = mapped_column(String(32), nullable=False)
    semantic_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    visual_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    blueprint_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    blueprint_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    semantic_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    visual_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(16), nullable=False)
    validation_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    author_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    origin: Mapped[str] = mapped_column(String(32), nullable=False)
    lock_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    idempotency_scope: Mapped[str] = mapped_column(String(64), nullable=False)
    request_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class DashboardReviewModelV2(Base):
    __tablename__ = "dashboard_reviews_v2"
    __table_args__ = (
        UniqueConstraint("id", "dashboard_id", "tenant_id", name="uq_dashboard_reviews_v2_identity"),
        ForeignKeyConstraint(["revision_id", "dashboard_id", "tenant_id"], ["dashboard_revisions_v2.id", "dashboard_revisions_v2.dashboard_id", "dashboard_revisions_v2.tenant_id"], name="fk_dashboard_reviews_v2_revision", ondelete="RESTRICT"),
        ForeignKeyConstraint(["actor_user_id", "tenant_id"], ["users.id", "users.tenant_id"], name="fk_dashboard_reviews_v2_actor", ondelete="RESTRICT"),
        CheckConstraint("action IN ('SUBMITTED','CHANGES_REQUESTED','APPROVED','REJECTED')", name="ck_dashboard_reviews_v2_action"),
        Index("idx_dashboard_reviews_v2_timeline", "tenant_id", "dashboard_id", "created_at", "id"),
        Index("idx_dashboard_reviews_v2_idempotency", "tenant_id", "idempotency_scope", unique=True),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dashboard_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    revision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(24), nullable=False)
    comment: Mapped[str] = mapped_column(String(1000), nullable=False)
    dashboard_lock_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    idempotency_scope: Mapped[str] = mapped_column(String(64), nullable=False)
    request_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class DashboardApprovalModelV2(Base):
    __tablename__ = "dashboard_approvals_v2"
    __table_args__ = (
        UniqueConstraint("id", "dashboard_id", "tenant_id", name="uq_dashboard_approvals_v2_identity"),
        UniqueConstraint("id", "dashboard_id", "tenant_id", "revision_id", name="uq_dashboard_approvals_v2_publication_ref"),
        UniqueConstraint("tenant_id", "dashboard_id", "revision_id", "blueprint_checksum", name="uq_dashboard_approvals_v2_revision_checksum"),
        ForeignKeyConstraint(["revision_id", "dashboard_id", "tenant_id"], ["dashboard_revisions_v2.id", "dashboard_revisions_v2.dashboard_id", "dashboard_revisions_v2.tenant_id"], name="fk_dashboard_approvals_v2_revision", ondelete="RESTRICT"),
        ForeignKeyConstraint(["approved_by_user_id", "tenant_id"], ["users.id", "users.tenant_id"], name="fk_dashboard_approvals_v2_actor", ondelete="RESTRICT"),
        Index("idx_dashboard_approvals_v2_revision", "tenant_id", "dashboard_id", "revision_id"),
        Index("idx_dashboard_approvals_v2_idempotency", "tenant_id", "idempotency_scope", unique=True),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dashboard_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    revision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    blueprint_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    semantic_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    visual_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    approved_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    idempotency_scope: Mapped[str] = mapped_column(String(64), nullable=False)
    request_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    approved_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class DashboardPublicationModelV2(Base):
    __tablename__ = "dashboard_publications_v2"
    __table_args__ = (
        UniqueConstraint("id", "dashboard_id", "tenant_id", name="uq_dashboard_publications_v2_identity"),
        UniqueConstraint("tenant_id", "dashboard_id", "publication_version", name="uq_dashboard_publications_v2_version"),
        UniqueConstraint("tenant_id", "dashboard_id", "generation", name="uq_dashboard_publications_v2_generation"),
        ForeignKeyConstraint(["revision_id", "dashboard_id", "tenant_id"], ["dashboard_revisions_v2.id", "dashboard_revisions_v2.dashboard_id", "dashboard_revisions_v2.tenant_id"], name="fk_dashboard_publications_v2_revision", ondelete="RESTRICT"),
        ForeignKeyConstraint(["approval_id", "dashboard_id", "tenant_id", "revision_id"], ["dashboard_approvals_v2.id", "dashboard_approvals_v2.dashboard_id", "dashboard_approvals_v2.tenant_id", "dashboard_approvals_v2.revision_id"], name="fk_dashboard_publications_v2_approval", ondelete="RESTRICT"),
        ForeignKeyConstraint(["supersedes_publication_id", "dashboard_id", "tenant_id"], ["dashboard_publications_v2.id", "dashboard_publications_v2.dashboard_id", "dashboard_publications_v2.tenant_id"], name="fk_dashboard_publications_v2_supersedes", ondelete="RESTRICT"),
        ForeignKeyConstraint(["rollback_source_publication_id", "dashboard_id", "tenant_id"], ["dashboard_publications_v2.id", "dashboard_publications_v2.dashboard_id", "dashboard_publications_v2.tenant_id"], name="fk_dashboard_publications_v2_rollback_source", ondelete="RESTRICT"),
        ForeignKeyConstraint(["published_by_user_id", "tenant_id"], ["users.id", "users.tenant_id"], name="fk_dashboard_publications_v2_actor", ondelete="RESTRICT"),
        CheckConstraint("generation >= 1", name="ck_dashboard_publications_v2_generation"),
        Index("idx_dashboard_publications_v2_history", "tenant_id", "dashboard_id", "generation"),
        Index("idx_dashboard_publications_v2_idempotency", "tenant_id", "idempotency_scope", unique=True),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dashboard_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    revision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    approval_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    supersedes_publication_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    rollback_source_publication_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    publication_version: Mapped[str] = mapped_column(String(32), nullable=False)
    generation: Mapped[int] = mapped_column(BigInteger, nullable=False)
    blueprint_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    semantic_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    visual_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    published_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    idempotency_scope: Mapped[str] = mapped_column(String(64), nullable=False)
    request_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    published_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class DashboardActivePublicationModelV2(Base):
    __tablename__ = "dashboard_active_publications_v2"
    __table_args__ = (
        ForeignKeyConstraint(["dashboard_id", "tenant_id"], ["dashboards_v2.id", "dashboards_v2.tenant_id"], name="fk_dashboard_active_v2_dashboard", ondelete="RESTRICT"),
        ForeignKeyConstraint(["publication_id", "dashboard_id", "tenant_id"], ["dashboard_publications_v2.id", "dashboard_publications_v2.dashboard_id", "dashboard_publications_v2.tenant_id"], name="fk_dashboard_active_v2_publication", ondelete="RESTRICT"),
        CheckConstraint("generation >= 1", name="ck_dashboard_active_v2_generation"),
        Index("idx_dashboard_active_v2_publication", "tenant_id", "publication_id"),
    )
    dashboard_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    publication_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    generation: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class DashboardCollaboratorModelV2(Base):
    __tablename__ = "dashboard_collaborators_v2"
    __table_args__ = (
        UniqueConstraint("id", "dashboard_id", "tenant_id", name="uq_dashboard_collaborators_v2_identity"),
        UniqueConstraint("tenant_id", "dashboard_id", "user_id", name="uq_dashboard_collaborators_v2_user"),
        ForeignKeyConstraint(["dashboard_id", "tenant_id"], ["dashboards_v2.id", "dashboards_v2.tenant_id"], name="fk_dashboard_collaborators_v2_dashboard", ondelete="RESTRICT"),
        ForeignKeyConstraint(["user_id", "tenant_id"], ["users.id", "users.tenant_id"], name="fk_dashboard_collaborators_v2_user", ondelete="RESTRICT"),
        CheckConstraint("role IN ('VIEWER','EDITOR_VISUAL','EDITOR_SEMANTIC','REVIEWER','PUBLISHER','ADMINISTRATOR') AND lock_version >= 1", name="ck_dashboard_collaborators_v2_role_lock"),
        Index("idx_dashboard_collaborators_v2_user", "tenant_id", "user_id", "dashboard_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dashboard_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    lock_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class DashboardAccessPolicyModelV2(Base):
    __tablename__ = "dashboard_access_policies_v2"
    __table_args__ = (
        UniqueConstraint("id", "dashboard_id", "tenant_id", name="uq_dashboard_access_policies_v2_identity"),
        UniqueConstraint("tenant_id", "dashboard_id", name="uq_dashboard_access_policies_v2_dashboard"),
        ForeignKeyConstraint(["dashboard_id", "tenant_id"], ["dashboards_v2.id", "dashboards_v2.tenant_id"], name="fk_dashboard_access_policies_v2_dashboard", ondelete="RESTRICT"),
        CheckConstraint("minimum_role IN ('CONSULTA','GESTOR','ADMIN') AND lock_version >= 1", name="ck_dashboard_access_policies_v2_role_lock"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dashboard_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    minimum_role: Mapped[str] = mapped_column(String(16), nullable=False)
    capabilities_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    classification_ceiling: Mapped[str] = mapped_column(String(48), nullable=False)
    allow_partial_runtime: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    lock_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class DashboardAuditEventModelV2(Base):
    __tablename__ = "dashboard_audit_events_v2"
    __table_args__ = (
        UniqueConstraint("id", "dashboard_id", "tenant_id", name="uq_dashboard_audit_events_v2_identity"),
        ForeignKeyConstraint(["dashboard_id", "tenant_id"], ["dashboards_v2.id", "dashboards_v2.tenant_id"], name="fk_dashboard_audit_events_v2_dashboard", ondelete="RESTRICT"),
        ForeignKeyConstraint(["actor_user_id", "tenant_id"], ["users.id", "users.tenant_id"], name="fk_dashboard_audit_events_v2_actor", ondelete="RESTRICT"),
        CheckConstraint("outcome IN ('SUCCESS','DENIED','CONFLICT','FAILED')", name="ck_dashboard_audit_events_v2_outcome"),
        Index("idx_dashboard_audit_events_v2_timeline", "tenant_id", "dashboard_id", "occurred_at", "id"),
        Index("idx_dashboard_audit_events_v2_idempotency", "tenant_id", "idempotency_scope", unique=True),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dashboard_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    metadata_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_scope: Mapped[str | None] = mapped_column(String(64), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class DashboardRuntimeExecutionModelV2(Base):
    __tablename__ = "dashboard_runtime_executions_v2"
    __table_args__ = (
        UniqueConstraint("id", "dashboard_id", "tenant_id", name="uq_dashboard_runtime_executions_v2_identity"),
        ForeignKeyConstraint(["publication_id", "dashboard_id", "tenant_id"], ["dashboard_publications_v2.id", "dashboard_publications_v2.dashboard_id", "dashboard_publications_v2.tenant_id"], name="fk_dashboard_runtime_executions_v2_publication", ondelete="RESTRICT"),
        ForeignKeyConstraint(["user_id", "tenant_id"], ["users.id", "users.tenant_id"], name="fk_dashboard_runtime_executions_v2_user", ondelete="RESTRICT"),
        CheckConstraint("status IN ('STARTED','COMPLETE','PARTIAL','BLOCKED','UNAVAILABLE','FAILED')", name="ck_dashboard_runtime_executions_v2_status"),
        Index("idx_dashboard_runtime_executions_v2_timeline", "tenant_id", "dashboard_id", "started_at", "id"),
        Index("idx_dashboard_runtime_executions_v2_status", "tenant_id", "status", "started_at"),
        Index("idx_dashboard_runtime_executions_v2_idempotency", "tenant_id", "idempotency_scope", unique=True),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dashboard_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    publication_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    plan_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    widget_count: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_widget_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_widget_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idempotency_scope: Mapped[str] = mapped_column(String(64), nullable=False)
    request_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)


class DashboardWidgetExecutionModelV2(Base):
    __tablename__ = "dashboard_widget_executions_v2"
    __table_args__ = (
        UniqueConstraint("id", "execution_id", "dashboard_id", "tenant_id", name="uq_dashboard_widget_executions_v2_identity"),
        ForeignKeyConstraint(["execution_id", "dashboard_id", "tenant_id"], ["dashboard_runtime_executions_v2.id", "dashboard_runtime_executions_v2.dashboard_id", "dashboard_runtime_executions_v2.tenant_id"], name="fk_dashboard_widget_executions_v2_execution", ondelete="RESTRICT"),
        CheckConstraint("status IN ('COMPLETE','UNAVAILABLE','BLOCKED','FAILED')", name="ck_dashboard_widget_executions_v2_status"),
        Index("idx_dashboard_widget_executions_v2_execution", "tenant_id", "execution_id", "widget_id"),
        Index("idx_dashboard_widget_executions_v2_status", "tenant_id", "status", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    dashboard_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    widget_id: Mapped[str] = mapped_column(String(128), nullable=False)
    binding_id: Mapped[str] = mapped_column(String(128), nullable=False)
    plan_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    cache_indicator: Mapped[str] = mapped_column(String(32), nullable=False)
    certification_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    result_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class DashboardEvaluationCaseModelV2(Base):
    __tablename__ = "dashboard_evaluation_cases_v2"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_dashboard_evaluation_cases_v2_identity"),
        UniqueConstraint("tenant_id", "case_key", name="uq_dashboard_evaluation_cases_v2_key"),
        CheckConstraint("status IN ('ACTIVE','ARCHIVED')", name="ck_dashboard_evaluation_cases_v2_status"),
        Index("idx_dashboard_evaluation_cases_v2_category", "tenant_id", "category", "status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    case_key: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    fixture_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    fixture_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    expected_status: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class DashboardEvaluationResultModelV2(Base):
    __tablename__ = "dashboard_evaluation_results_v2"
    __table_args__ = (
        ForeignKeyConstraint(["case_id", "tenant_id"], ["dashboard_evaluation_cases_v2.id", "dashboard_evaluation_cases_v2.tenant_id"], name="fk_dashboard_evaluation_results_v2_case", ondelete="RESTRICT"),
        Index("idx_dashboard_evaluation_results_v2_case", "tenant_id", "case_id", "executed_at"),
        Index("idx_dashboard_evaluation_results_v2_passed", "tenant_id", "passed", "executed_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    actual_status: Mapped[str] = mapped_column(String(16), nullable=False)
    evidence_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    evidence_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
