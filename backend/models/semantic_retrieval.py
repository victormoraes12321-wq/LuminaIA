from __future__ import annotations

import uuid
from datetime import datetime

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
from sqlalchemy.sql import func

from database import Base


CONTRACT_VERSION = "lumina.semantic-retrieval/1.0"


class SemanticIndexDefinition(Base):
    __tablename__ = "semantic_index_definitions"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_semantic_index_tenant"),
        UniqueConstraint("tenant_id", "name", name="uq_semantic_index_name"),
        ForeignKeyConstraint(
            ["owner_user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_semantic_index_owner",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["active_version_id", "id", "tenant_id"],
            [
                "semantic_index_versions.id",
                "semantic_index_versions.index_id",
                "semantic_index_versions.tenant_id",
            ],
            name="fk_semantic_index_active_version",
            ondelete="RESTRICT",
            use_alter=True,
        ),
        CheckConstraint(
            "status IN ('ACTIVE','DISABLED','ARCHIVED')",
            name="ck_semantic_index_status",
        ),
        CheckConstraint("lock_version >= 0", name="ck_semantic_index_lock"),
        CheckConstraint(
            "representation_dimension BETWEEN 32 AND 4096",
            name="ck_semantic_index_dimension",
        ),
        CheckConstraint(
            "jsonb_typeof(document_types) = 'array' "
            "AND jsonb_typeof(entity_policies) = 'array' "
            "AND jsonb_typeof(source_policies) = 'array' "
            "AND jsonb_typeof(classification_policy) = 'array' "
            "AND jsonb_typeof(ranking_policy) = 'object' "
            "AND jsonb_typeof(threshold_policy) = 'object'",
            name="ck_semantic_index_json",
        ),
        Index("idx_semantic_index_tenant_status", "tenant_id", "status", "id"),
        Index("idx_semantic_index_active", "tenant_id", "active_version_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="pt-BR")
    document_types: Mapped[list] = mapped_column(JSONB, nullable=False)
    entity_policies: Mapped[list] = mapped_column(JSONB, nullable=False)
    source_policies: Mapped[list] = mapped_column(JSONB, nullable=False)
    classification_policy: Mapped[list] = mapped_column(JSONB, nullable=False)
    representation_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    representation_version: Mapped[str] = mapped_column(String(128), nullable=False)
    representation_dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    ranking_policy: Mapped[dict] = mapped_column(JSONB, nullable=False)
    threshold_policy: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    owner_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    active_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
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


class SemanticIndexVersion(Base):
    __tablename__ = "semantic_index_versions"
    __table_args__ = (
        UniqueConstraint("id", "index_id", "tenant_id", name="uq_semantic_version_scope"),
        UniqueConstraint(
            "tenant_id", "index_id", "version", name="uq_semantic_version_number"
        ),
        UniqueConstraint(
            "tenant_id",
            "index_id",
            "idempotency_key_hash",
            name="uq_semantic_version_idempotency",
        ),
        ForeignKeyConstraint(
            ["index_id", "tenant_id"],
            ["semantic_index_definitions.id", "semantic_index_definitions.tenant_id"],
            name="fk_semantic_version_index",
            ondelete="CASCADE",
            use_alter=True,
        ),
        ForeignKeyConstraint(
            ["created_by", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_semantic_version_creator",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["reviewed_by", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_semantic_version_reviewer",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["published_by", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_semantic_version_publisher",
            ondelete="RESTRICT",
        ),
        CheckConstraint("version > 0", name="ck_semantic_version_positive"),
        CheckConstraint("lock_version >= 0", name="ck_semantic_version_lock"),
        CheckConstraint(
            "lifecycle IN ('DRAFT','BUILDING','VALIDATING','READY','PUBLISHED',"
            "'FAILED','DEPRECATED','ARCHIVED')",
            name="ck_semantic_version_lifecycle",
        ),
        CheckConstraint(
            "build_mode IN ('FULL','INCREMENTAL')",
            name="ck_semantic_version_build_mode",
        ),
        CheckConstraint(
            "document_count >= 0 AND entity_count >= 0 "
            "AND alias_count >= 0 AND relation_count >= 0",
            name="ck_semantic_version_counts",
        ),
        CheckConstraint(
            "checksum IS NULL OR checksum ~ '^[a-f0-9]{64}$'",
            name="ck_semantic_version_checksum",
        ),
        CheckConstraint(
            "jsonb_typeof(source_manifest) = 'object'",
            name="ck_semantic_version_manifest",
        ),
        CheckConstraint(
            "build_completed_at IS NULL OR build_completed_at >= build_started_at",
            name="ck_semantic_version_timestamps",
        ),
        Index(
            "idx_semantic_versions_index",
            "tenant_id",
            "index_id",
            text("version DESC"),
        ),
        Index("idx_semantic_versions_lifecycle", "tenant_id", "lifecycle", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    index_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    lifecycle: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT")
    source_manifest: Mapped[dict] = mapped_column(JSONB, nullable=False)
    document_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    entity_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    alias_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    relation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    representation_version: Mapped[str] = mapped_column(String(128), nullable=False)
    build_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="FULL")
    idempotency_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    watermark: Mapped[str | None] = mapped_column(String(256))
    build_started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    build_completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    checksum: Mapped[str | None] = mapped_column(String(64))
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    published_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    superseded_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    failure_summary: Mapped[str | None] = mapped_column(String(256))
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


class SemanticDocument(Base):
    __tablename__ = "semantic_documents"
    __table_args__ = (
        UniqueConstraint(
            "id", "tenant_id", "index_version_id", name="uq_semantic_document_scope"
        ),
        UniqueConstraint(
            "tenant_id",
            "index_version_id",
            "canonical_key",
            "document_type",
            name="uq_semantic_document_canonical",
        ),
        ForeignKeyConstraint(
            ["index_version_id", "index_id", "tenant_id"],
            [
                "semantic_index_versions.id",
                "semantic_index_versions.index_id",
                "semantic_index_versions.tenant_id",
            ],
            name="fk_semantic_document_version",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "document_type IN ('BUSINESS_TERM','METRIC','KPI','DIMENSION','ENTITY_TYPE',"
            "'ENTITY_INSTANCE','BUSINESS_RULE','ALIAS','RELATION','CALENDAR_POLICY',"
            "'APPROVED_TRAINING_EXAMPLE','SYSTEM_CONCEPT')",
            name="ck_semantic_document_type",
        ),
        CheckConstraint(
            "entity_type IN ('METRIC','DIMENSION','BUSINESS_CONCEPT','BRANCH','PRODUCT',"
            "'PRODUCT_GROUP','CUSTOMER','SUPPLIER','SELLER','REGION','CITY','STATE',"
            "'COST_CENTER','WAREHOUSE','PAYMENT_METHOD','RECEIVABLE_STATUS',"
            "'STOCK_LOCATION','UNKNOWN')",
            name="ck_semantic_document_entity_type",
        ),
        CheckConstraint(
            "classification IN ('PUBLIC_BUSINESS_METADATA','TENANT_BUSINESS_METADATA',"
            "'RESTRICTED_BUSINESS_METADATA','PERSONAL_DATA')",
            name="ck_semantic_document_classification",
        ),
        CheckConstraint(
            "lifecycle IN ('ACTIVE','DEPRECATED','TOMBSTONED')",
            name="ck_semantic_document_lifecycle",
        ),
        CheckConstraint("checksum ~ '^[a-f0-9]{64}$'", name="ck_semantic_document_checksum"),
        CheckConstraint(
            "source_checksum ~ '^[a-f0-9]{64}$'",
            name="ck_semantic_document_source_checksum",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to > valid_from",
            name="ck_semantic_document_effective",
        ),
        CheckConstraint(
            "jsonb_typeof(content) = 'object' AND jsonb_typeof(provenance) = 'object'",
            name="ck_semantic_document_json",
        ),
        Index(
            "idx_semantic_document_type",
            "tenant_id",
            "index_version_id",
            "document_type",
        ),
        Index(
            "idx_semantic_document_canonical",
            "tenant_id",
            "index_version_id",
            "canonical_key",
        ),
        Index(
            "idx_semantic_document_label",
            "tenant_id",
            "index_version_id",
            "normalized_label",
        ),
        Index(
            "idx_semantic_document_entity",
            "tenant_id",
            "index_version_id",
            "entity_type",
            "domain",
        ),
        Index(
            "idx_semantic_document_source",
            "tenant_id",
            "source_type",
            "source_id",
            "source_version",
        ),
        Index(
            "idx_semantic_document_effective",
            "tenant_id",
            "lifecycle",
            "valid_from",
            "valid_to",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    index_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    index_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_type: Mapped[str] = mapped_column(String(40), nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(256), nullable=False)
    display_label: Mapped[str] = mapped_column(String(256), nullable=False)
    normalized_label: Mapped[str] = mapped_column(String(256), nullable=False)
    locale: Mapped[str] = mapped_column(String(16), nullable=False)
    domain: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(48), nullable=False)
    source_id: Mapped[str] = mapped_column(String(256), nullable=False)
    source_version: Mapped[str] = mapped_column(String(128), nullable=False)
    source_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    lifecycle: Mapped[str] = mapped_column(String(24), nullable=False, default="ACTIVE")
    valid_from: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    classification: Mapped[str] = mapped_column(String(48), nullable=False)
    permission_requirement: Mapped[str | None] = mapped_column(String(64))
    representation_version: Mapped[str] = mapped_column(String(128), nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    provenance: Mapped[dict] = mapped_column(JSONB, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default=CONTRACT_VERSION
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class SemanticDocumentAlias(Base):
    __tablename__ = "semantic_document_aliases"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_semantic_alias_scope"),
        UniqueConstraint(
            "tenant_id",
            "index_version_id",
            "document_id",
            "normalized_alias",
            name="uq_semantic_alias_document",
        ),
        ForeignKeyConstraint(
            ["document_id", "tenant_id", "index_version_id"],
            ["semantic_documents.id", "semantic_documents.tenant_id", "semantic_documents.index_version_id"],
            name="fk_semantic_alias_document",
            ondelete="CASCADE",
        ),
        CheckConstraint("checksum ~ '^[a-f0-9]{64}$'", name="ck_semantic_alias_checksum"),
        Index(
            "idx_semantic_alias_lookup",
            "tenant_id",
            "index_version_id",
            "normalized_alias",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    index_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    alias: Mapped[str] = mapped_column(String(256), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(256), nullable=False)
    locale: Mapped[str] = mapped_column(String(16), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class SemanticDocumentRelation(Base):
    __tablename__ = "semantic_document_relations"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "index_version_id",
            "source_document_id",
            "target_document_id",
            "relation_type",
            name="uq_semantic_relation",
        ),
        ForeignKeyConstraint(
            ["source_document_id", "tenant_id", "index_version_id"],
            ["semantic_documents.id", "semantic_documents.tenant_id", "semantic_documents.index_version_id"],
            name="fk_semantic_relation_source",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["target_document_id", "tenant_id", "index_version_id"],
            ["semantic_documents.id", "semantic_documents.tenant_id", "semantic_documents.index_version_id"],
            name="fk_semantic_relation_target",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "source_document_id <> target_document_id",
            name="ck_semantic_relation_distinct",
        ),
        Index(
            "idx_semantic_relation_source",
            "tenant_id",
            "index_version_id",
            "source_document_id",
        ),
        Index(
            "idx_semantic_relation_target",
            "tenant_id",
            "index_version_id",
            "target_document_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    index_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target_document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(48), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class SemanticDocumentTerm(Base):
    __tablename__ = "semantic_document_terms"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "index_version_id",
            "document_id",
            "term",
            "term_kind",
            name="uq_semantic_term",
        ),
        ForeignKeyConstraint(
            ["document_id", "tenant_id", "index_version_id"],
            ["semantic_documents.id", "semantic_documents.tenant_id", "semantic_documents.index_version_id"],
            name="fk_semantic_term_document",
            ondelete="CASCADE",
        ),
        CheckConstraint("weight BETWEEN 0 AND 1", name="ck_semantic_term_weight"),
        Index(
            "idx_semantic_term_lookup",
            "tenant_id",
            "index_version_id",
            "term",
            "term_kind",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    index_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    term: Mapped[str] = mapped_column(String(256), nullable=False)
    term_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)


class SemanticDocumentRepresentation(Base):
    __tablename__ = "semantic_document_representations"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "index_version_id",
            "document_id",
            "representation_type",
            "representation_version",
            name="uq_semantic_representation",
        ),
        ForeignKeyConstraint(
            ["document_id", "tenant_id", "index_version_id"],
            ["semantic_documents.id", "semantic_documents.tenant_id", "semantic_documents.index_version_id"],
            name="fk_semantic_representation_document",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "representation_type IN ('LEXICAL','DETERMINISTIC_FEATURE_HASH')",
            name="ck_semantic_representation_type",
        ),
        CheckConstraint(
            "dimension IS NULL OR dimension BETWEEN 32 AND 4096",
            name="ck_semantic_representation_dimension",
        ),
        CheckConstraint(
            "jsonb_typeof(representation) = 'object'",
            name="ck_semantic_representation_json",
        ),
        CheckConstraint(
            "checksum ~ '^[a-f0-9]{64}$'",
            name="ck_semantic_representation_checksum",
        ),
        Index(
            "idx_semantic_representation_lookup",
            "tenant_id",
            "index_version_id",
            "representation_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    index_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    representation_type: Mapped[str] = mapped_column(String(48), nullable=False)
    representation_version: Mapped[str] = mapped_column(String(128), nullable=False)
    dimension: Mapped[int | None] = mapped_column(Integer)
    representation: Mapped[dict] = mapped_column(JSONB, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)


class SemanticIndexPublication(Base):
    __tablename__ = "semantic_index_publications"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_semantic_publication_scope"),
        ForeignKeyConstraint(
            ["version_id", "index_id", "tenant_id"],
            [
                "semantic_index_versions.id",
                "semantic_index_versions.index_id",
                "semantic_index_versions.tenant_id",
            ],
            name="fk_semantic_publication_version",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["published_by", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_semantic_publication_user",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "checksum ~ '^[a-f0-9]{64}$'",
            name="ck_semantic_publication_checksum",
        ),
        Index(
            "idx_semantic_publication_index",
            "tenant_id",
            "index_id",
            text("published_at DESC"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    index_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    previous_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    published_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    published_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    reason: Mapped[str] = mapped_column(String(256), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)


class SemanticIndexEvent(Base):
    __tablename__ = "semantic_index_events"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_semantic_event_scope"),
        ForeignKeyConstraint(
            ["actor_user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_semantic_event_actor",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "structural_fingerprint ~ '^[a-f0-9]{64}$'",
            name="ck_semantic_event_fingerprint",
        ),
        CheckConstraint(
            "jsonb_typeof(event_metadata) = 'object'",
            name="ck_semantic_event_json",
        ),
        Index(
            "idx_semantic_event_timeline",
            "tenant_id",
            "index_id",
            text("created_at DESC"),
            text("id DESC"),
        ),
        Index("idx_semantic_event_type", "tenant_id", "event_type", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    index_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    structural_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    event_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    schema_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default=CONTRACT_VERSION
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class SemanticEvaluationCase(Base):
    __tablename__ = "semantic_evaluation_cases"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "corpus_version", "case_key", name="uq_semantic_evaluation_case"
        ),
        CheckConstraint(
            "jsonb_typeof(case_data) = 'object'",
            name="ck_semantic_evaluation_case_json",
        ),
        CheckConstraint("checksum ~ '^[a-f0-9]{64}$'", name="ck_semantic_case_checksum"),
        Index(
            "idx_semantic_evaluation_corpus",
            "tenant_id",
            "corpus_version",
            "case_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    corpus_version: Mapped[str] = mapped_column(String(128), nullable=False)
    case_key: Mapped[str] = mapped_column(String(256), nullable=False)
    case_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class SemanticEvaluationResult(Base):
    __tablename__ = "semantic_evaluation_results"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_semantic_evaluation_result"),
        ForeignKeyConstraint(
            ["index_version_id", "index_id", "tenant_id"],
            [
                "semantic_index_versions.id",
                "semantic_index_versions.index_id",
                "semantic_index_versions.tenant_id",
            ],
            name="fk_semantic_evaluation_version",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "jsonb_typeof(metrics) = 'array'",
            name="ck_semantic_evaluation_metrics",
        ),
        CheckConstraint(
            "checksum ~ '^[a-f0-9]{64}$'",
            name="ck_semantic_evaluation_checksum",
        ),
        Index(
            "idx_semantic_evaluation_version",
            "tenant_id",
            "index_version_id",
            text("executed_at DESC"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    index_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    index_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    corpus_version: Mapped[str] = mapped_column(String(128), nullable=False)
    case_count: Mapped[int] = mapped_column(Integer, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    metrics: Mapped[list] = mapped_column(JSONB, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class SemanticClarification(Base):
    __tablename__ = "semantic_clarifications"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", "user_id", name="uq_semantic_clarification"),
        ForeignKeyConstraint(
            ["user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_semantic_clarification_user",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "status IN ('PENDING','RESOLVED','EXPIRED','CANCELLED')",
            name="ck_semantic_clarification_status",
        ),
        CheckConstraint(
            "options_checksum ~ '^[a-f0-9]{64}$'",
            name="ck_semantic_clarification_checksum",
        ),
        CheckConstraint(
            "jsonb_typeof(options) = 'array'",
            name="ck_semantic_clarification_options",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="ck_semantic_clarification_expiry",
        ),
        Index(
            "idx_semantic_clarification_pending",
            "tenant_id",
            "user_id",
            "session_id",
            "status",
            "expires_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    mention_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    options: Mapped[list] = mapped_column(JSONB, nullable=False)
    options_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    resolved_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
