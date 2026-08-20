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
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from database import Base


CONTRACT_VERSION = "lumina.enterprise-knowledge/1.0"
ASSET_TYPES = (
    "BUSINESS_TERM",
    "METRIC",
    "KPI",
    "DIMENSION",
    "ENTITY",
    "BUSINESS_RULE",
    "ALIAS_SET",
    "CALENDAR_POLICY",
    "DATA_QUALITY_POLICY",
    "SEMANTIC_RELATION",
)
LIFECYCLES = (
    "DRAFT",
    "IN_REVIEW",
    "APPROVED",
    "PUBLISHED",
    "REJECTED",
    "DEPRECATED",
    "ARCHIVED",
)


class EnterpriseKnowledgeAsset(Base):
    __tablename__ = "enterprise_knowledge_assets"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_knowledge_asset_id_tenant"),
        UniqueConstraint(
            "tenant_id",
            "asset_type",
            "canonical_key",
            name="uq_knowledge_asset_canonical",
        ),
        CheckConstraint(
            f"asset_type IN {ASSET_TYPES!r}".replace(",)", ")"),
            name="ck_knowledge_asset_type",
        ),
        CheckConstraint(
            "status IN ('ACTIVE','ARCHIVED','DELETED')",
            name="ck_knowledge_asset_status",
        ),
        CheckConstraint("lock_version >= 0", name="ck_knowledge_asset_lock"),
        CheckConstraint(
            "(status = 'DELETED' AND deleted_at IS NOT NULL) "
            "OR (status <> 'DELETED' AND deleted_at IS NULL)",
            name="ck_knowledge_asset_deleted",
        ),
        ForeignKeyConstraint(
            ["owner_user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_knowledge_asset_owner_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["current_published_version_id", "id", "tenant_id"],
            [
                "enterprise_knowledge_versions.id",
                "enterprise_knowledge_versions.asset_id",
                "enterprise_knowledge_versions.tenant_id",
            ],
            name="fk_knowledge_asset_published_version",
            ondelete="RESTRICT",
            use_alter=True,
        ),
        Index(
            "idx_knowledge_assets_tenant_type_key",
            "tenant_id",
            "asset_type",
            "canonical_key",
        ),
        Index("idx_knowledge_assets_tenant_domain", "tenant_id", "domain", "id"),
        Index("idx_knowledge_assets_tenant_owner", "tenant_id", "owner_user_id", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(128), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(40), nullable=False)
    domain: Mapped[str] = mapped_column(String(128), nullable=False)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    steward_label: Mapped[str] = mapped_column(String(256), nullable=False)
    accountable_area: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    current_published_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    lock_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    schema_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default=CONTRACT_VERSION
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class EnterpriseKnowledgeVersion(Base):
    __tablename__ = "enterprise_knowledge_versions"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "asset_id",
            "tenant_id",
            name="uq_knowledge_version_asset_tenant",
        ),
        UniqueConstraint(
            "asset_id",
            "version_number",
            name="uq_knowledge_version_number",
        ),
        CheckConstraint("version_number >= 1", name="ck_knowledge_version_number"),
        CheckConstraint("lock_version >= 0", name="ck_knowledge_version_lock"),
        CheckConstraint(
            f"lifecycle IN {LIFECYCLES!r}".replace(",)", ")"),
            name="ck_knowledge_version_lifecycle",
        ),
        CheckConstraint(
            "checksum ~ '^[a-f0-9]{64}$'",
            name="ck_knowledge_version_checksum",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from",
            name="ck_knowledge_version_effective_period",
        ),
        ForeignKeyConstraint(
            ["asset_id", "tenant_id"],
            ["enterprise_knowledge_assets.id", "enterprise_knowledge_assets.tenant_id"],
            name="fk_knowledge_version_asset_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["author_user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_knowledge_version_author_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["previous_version_id", "asset_id", "tenant_id"],
            [
                "enterprise_knowledge_versions.id",
                "enterprise_knowledge_versions.asset_id",
                "enterprise_knowledge_versions.tenant_id",
            ],
            name="fk_knowledge_version_previous",
            ondelete="RESTRICT",
        ),
        Index(
            "idx_knowledge_versions_asset_version",
            "tenant_id",
            "asset_id",
            "version_number",
        ),
        Index(
            "idx_knowledge_versions_tenant_lifecycle",
            "tenant_id",
            "lifecycle",
            "updated_at",
            "id",
        ),
        Index(
            "idx_knowledge_versions_effective",
            "tenant_id",
            "effective_from",
            "effective_to",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    lifecycle: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    author_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    previous_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="MANUAL")
    source_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    effective_from: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    lock_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    rejection_comment: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    deprecated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    schema_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default=CONTRACT_VERSION
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class EnterpriseKnowledgeApproval(Base):
    __tablename__ = "enterprise_knowledge_approvals"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "version_id",
            "reviewer_user_id",
            name="uq_knowledge_approval_reviewer",
        ),
        CheckConstraint(
            "decision IN ('APPROVED','REJECTED')",
            name="ck_knowledge_approval_decision",
        ),
        CheckConstraint(
            "version_checksum ~ '^[a-f0-9]{64}$'",
            name="ck_knowledge_approval_checksum",
        ),
        ForeignKeyConstraint(
            ["version_id", "asset_id", "tenant_id"],
            [
                "enterprise_knowledge_versions.id",
                "enterprise_knowledge_versions.asset_id",
                "enterprise_knowledge_versions.tenant_id",
            ],
            name="fk_knowledge_approval_version_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["reviewer_user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_knowledge_approval_reviewer_tenant",
            ondelete="RESTRICT",
        ),
        Index(
            "idx_knowledge_approvals_pending",
            "tenant_id",
            "decision",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    version_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class EnterpriseKnowledgePublication(Base):
    __tablename__ = "enterprise_knowledge_publications"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "version_id",
            name="uq_knowledge_publication_version",
        ),
        ForeignKeyConstraint(
            ["version_id", "asset_id", "tenant_id"],
            [
                "enterprise_knowledge_versions.id",
                "enterprise_knowledge_versions.asset_id",
                "enterprise_knowledge_versions.tenant_id",
            ],
            name="fk_knowledge_publication_version_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["superseded_version_id", "asset_id", "tenant_id"],
            [
                "enterprise_knowledge_versions.id",
                "enterprise_knowledge_versions.asset_id",
                "enterprise_knowledge_versions.tenant_id",
            ],
            name="fk_knowledge_publication_superseded",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["publisher_user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_knowledge_publication_publisher_tenant",
            ondelete="RESTRICT",
        ),
        Index(
            "idx_knowledge_publications_asset_time",
            "tenant_id",
            "asset_id",
            "published_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    publisher_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    effective_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    published_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    superseded_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    schema_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default=CONTRACT_VERSION
    )


class EnterpriseKnowledgeAlias(Base):
    __tablename__ = "enterprise_knowledge_aliases"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "version_id",
            "locale",
            "normalized_alias",
            name="uq_knowledge_alias_version",
        ),
        ForeignKeyConstraint(
            ["version_id", "asset_id", "tenant_id"],
            [
                "enterprise_knowledge_versions.id",
                "enterprise_knowledge_versions.asset_id",
                "enterprise_knowledge_versions.tenant_id",
            ],
            name="fk_knowledge_alias_version_tenant",
            ondelete="CASCADE",
        ),
        Index(
            "idx_knowledge_alias_lookup",
            "tenant_id",
            "locale",
            "normalized_alias",
            "id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    alias: Mapped[str] = mapped_column(String(256), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(256), nullable=False)
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="pt-BR")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class EnterpriseKnowledgeRelation(Base):
    __tablename__ = "enterprise_knowledge_relations"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "source_asset_id",
            "target_asset_id",
            "relation_type",
            "source_version_id",
            name="uq_knowledge_relation_version",
        ),
        ForeignKeyConstraint(
            ["source_asset_id", "tenant_id"],
            ["enterprise_knowledge_assets.id", "enterprise_knowledge_assets.tenant_id"],
            name="fk_knowledge_relation_source_tenant",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "relation_type IN ('SYNONYM_OF','BROADER_THAN','NARROWER_THAN',"
            "'RELATED_TO','CALCULATED_FROM','ALLOWED_DIMENSION',"
            "'INCOMPATIBLE_WITH','OWNED_BY','SUPERSEDES','DEPENDS_ON')",
            name="ck_knowledge_relation_type",
        ),
        CheckConstraint(
            "source_asset_id <> target_asset_id",
            name="ck_knowledge_relation_self",
        ),
        ForeignKeyConstraint(
            ["target_asset_id", "tenant_id"],
            ["enterprise_knowledge_assets.id", "enterprise_knowledge_assets.tenant_id"],
            name="fk_knowledge_relation_target_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["source_version_id", "source_asset_id", "tenant_id"],
            [
                "enterprise_knowledge_versions.id",
                "enterprise_knowledge_versions.asset_id",
                "enterprise_knowledge_versions.tenant_id",
            ],
            name="fk_knowledge_relation_version_tenant",
            ondelete="CASCADE",
        ),
        Index(
            "idx_knowledge_relations_source",
            "tenant_id",
            "source_asset_id",
            "relation_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target_asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class EnterpriseKnowledgeEvent(Base):
    __tablename__ = "enterprise_knowledge_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["actor_user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_knowledge_event_actor_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["asset_id", "tenant_id"],
            ["enterprise_knowledge_assets.id", "enterprise_knowledge_assets.tenant_id"],
            name="fk_knowledge_event_asset_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["version_id", "asset_id", "tenant_id"],
            [
                "enterprise_knowledge_versions.id",
                "enterprise_knowledge_versions.asset_id",
                "enterprise_knowledge_versions.tenant_id",
            ],
            name="fk_knowledge_event_version_tenant",
            ondelete="CASCADE",
        ),
        Index(
            "idx_knowledge_events_asset_time",
            "tenant_id",
            "asset_id",
            "created_at",
            "id",
        ),
        Index(
            "idx_knowledge_events_type_time",
            "tenant_id",
            "event_type",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    asset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    event_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    schema_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default=CONTRACT_VERSION
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class EnterpriseKnowledgeImport(Base):
    __tablename__ = "enterprise_knowledge_imports"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "idempotency_key_hash",
            name="uq_knowledge_import_idempotency",
        ),
        UniqueConstraint(
            "tenant_id",
            "source_checksum",
            "dry_run",
            name="uq_knowledge_import_checksum_mode",
        ),
        CheckConstraint("accepted_count >= 0", name="ck_knowledge_import_accepted"),
        CheckConstraint("rejected_count >= 0", name="ck_knowledge_import_rejected"),
        CheckConstraint(
            "source_format IN ('JSON','CSV','LEGACY')",
            name="ck_knowledge_import_format",
        ),
        CheckConstraint(
            "source_checksum ~ '^[a-f0-9]{64}$'",
            name="ck_knowledge_import_checksum",
        ),
        CheckConstraint(
            "idempotency_key_hash ~ '^[a-f0-9]{64}$'",
            name="ck_knowledge_import_idempotency",
        ),
        ForeignKeyConstraint(
            ["author_user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_knowledge_import_author_tenant",
            ondelete="RESTRICT",
        ),
        Index(
            "idx_knowledge_imports_tenant_time",
            "tenant_id",
            "created_at",
            "id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    author_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_format: Mapped[str] = mapped_column(String(16), nullable=False)
    source_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    accepted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    schema_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default=CONTRACT_VERSION
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
