from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from database import Base


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "user_id", "public_session_id",
            name="uq_conversation_session_public_owner",
        ),
        UniqueConstraint("public_session_id", name="uq_conversation_session_public_global"),
        UniqueConstraint("id", "tenant_id", "user_id", name="uq_conversation_session_owner"),
        ForeignKeyConstraint(
            ["user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_conversation_session_user_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["active_head_node_id", "id"],
            ["conversation_nodes.id", "conversation_nodes.session_id"],
            name="fk_conversation_session_head",
            ondelete="RESTRICT",
            use_alter=True,
        ),
        CheckConstraint("context_epoch >= 0", name="ck_conversation_session_epoch"),
        CheckConstraint("context_version >= 0", name="ck_conversation_session_context_version"),
        CheckConstraint("lock_version >= 0", name="ck_conversation_session_lock_version"),
        CheckConstraint("next_sequence >= 1", name="ck_conversation_session_next_sequence"),
        CheckConstraint(
            "status IN ('ACTIVE','ARCHIVED','EXPIRED','DELETED')",
            name="ck_conversation_session_status",
        ),
        CheckConstraint("expires_at >= created_at", name="ck_conversation_session_expiry"),
        Index(
            "idx_conversation_sessions_owner_status_activity",
            "tenant_id", "user_id", "status", text("last_activity_at DESC"), "id",
        ),
        Index("idx_conversation_sessions_expires_at", "expires_at"),
        Index("idx_conversation_sessions_deleted_at", "deleted_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    public_session_id: Mapped[str] = mapped_column(String(128), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    schema_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default="lumina.conversation-state/1.0",
    )
    context_epoch: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    context_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    lock_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    next_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    active_head_node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class ConversationNodeRecord(Base):
    __tablename__ = "conversation_nodes"
    __table_args__ = (
        UniqueConstraint("id", "session_id", name="uq_conversation_node_session"),
        UniqueConstraint("session_id", "sequence_number", name="uq_conversation_node_sequence"),
        ForeignKeyConstraint(
            ["session_id", "tenant_id", "user_id"],
            ["conversation_sessions.id", "conversation_sessions.tenant_id", "conversation_sessions.user_id"],
            name="fk_conversation_node_session_owner",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["parent_node_id", "session_id"],
            ["conversation_nodes.id", "conversation_nodes.session_id"],
            name="fk_conversation_node_parent_session",
            ondelete="RESTRICT",
        ),
        CheckConstraint("sequence_number >= 1", name="ck_conversation_node_sequence"),
        CheckConstraint("role IN ('user','assistant','system')", name="ck_conversation_node_role"),
        CheckConstraint(
            "node_type IN ('USER_QUERY','ASSISTANT_RESPONSE','CLARIFICATION_REQUEST',"
            "'CLARIFICATION_RESPONSE','ERROR','CANCELLED','RESET','SYSTEM_EVENT')",
            name="ck_conversation_node_type",
        ),
        CheckConstraint(
            "status IN ('IN_PROGRESS','COMPLETED','FAILED','CANCELLED','SUPERSEDED')",
            name="ck_conversation_node_status",
        ),
        CheckConstraint(
            "(completed_at IS NULL OR completed_at >= created_at) "
            "AND (failed_at IS NULL OR failed_at >= created_at)",
            name="ck_conversation_node_timestamps",
        ),
        Index("idx_conversation_nodes_session_sequence", "session_id", "sequence_number"),
        Index("idx_conversation_nodes_session_parent", "session_id", "parent_node_id"),
        Index(
            "uq_conversation_nodes_client_message",
            "session_id", "client_message_id",
            unique=True,
            postgresql_where=text("client_message_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sequence_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    parent_node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    node_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    client_message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    idempotency_key_hash: Mapped[str | None] = mapped_column(String(64))
    content_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    content_key_version: Mapped[str | None] = mapped_column(String(32))
    content_fingerprint: Mapped[str | None] = mapped_column(String(64))
    search_history_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("search_history.id", ondelete="SET NULL"),
    )
    plan_fingerprint: Mapped[str | None] = mapped_column(String(128))
    response_fingerprint: Mapped[str | None] = mapped_column(String(128))
    base_context_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class ConversationStateSnapshot(Base):
    __tablename__ = "conversation_state_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "context_epoch", "context_version",
            name="uq_conversation_snapshot_version",
        ),
        ForeignKeyConstraint(
            ["session_id", "tenant_id", "user_id"],
            ["conversation_sessions.id", "conversation_sessions.tenant_id", "conversation_sessions.user_id"],
            name="fk_conversation_snapshot_session_owner",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["head_node_id", "session_id"],
            ["conversation_nodes.id", "conversation_nodes.session_id"],
            name="fk_conversation_snapshot_head_session",
            ondelete="RESTRICT",
        ),
        CheckConstraint("context_epoch >= 0", name="ck_conversation_snapshot_epoch"),
        CheckConstraint("context_version >= 0", name="ck_conversation_snapshot_version"),
        Index(
            "idx_conversation_snapshots_current",
            "session_id", "context_epoch", text("context_version DESC"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    context_epoch: Mapped[int] = mapped_column(Integer, nullable=False)
    context_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    head_node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    state_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    state_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False,
    )


class ConversationEvent(Base):
    __tablename__ = "conversation_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["session_id", "tenant_id", "user_id"],
            ["conversation_sessions.id", "conversation_sessions.tenant_id", "conversation_sessions.user_id"],
            name="fk_conversation_event_session_owner",
            ondelete="CASCADE",
        ),
        CheckConstraint("context_epoch >= 0", name="ck_conversation_event_epoch"),
        CheckConstraint("context_version >= 0", name="ck_conversation_event_version"),
        Index("idx_conversation_events_session_time", "session_id", "created_at", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    context_epoch: Mapped[int] = mapped_column(Integer, nullable=False)
    context_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    fingerprint: Mapped[str | None] = mapped_column(String(128))
    event_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False,
    )


class ConversationLegacyImport(Base):
    __tablename__ = "conversation_legacy_imports"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "user_id", "source_checksum",
            name="uq_conversation_legacy_import_checksum",
        ),
        Index("idx_conversation_legacy_import_owner", "tenant_id", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversation_sessions.id", ondelete="SET NULL"),
    )
    source_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_format: Mapped[str] = mapped_column(String(40), nullable=False)
    imported_nodes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False,
    )
