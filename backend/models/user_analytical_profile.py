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


CONTRACT_VERSION = "lumina.user-analytical-profile/1.0"
PREFERENCE_TYPES = (
    "PRESENTATION",
    "LOCALE",
    "ACCESSIBILITY",
    "ANALYTICAL_DEFAULT",
    "FAVORITE_METRIC",
    "FAVORITE_DIMENSION",
    "FAVORITE_ENTITY",
    "SAVED_FILTER_REFERENCE",
    "SAVED_QUERY_REFERENCE",
    "SAVED_DASHBOARD_REFERENCE",
    "INTERACTION",
    "PRIVACY",
    "RETENTION",
)
PREFERENCE_STATUSES = (
    "ACTIVE",
    "DISABLED",
    "EXPIRED",
    "REVOKED",
    "DELETED",
    "PENDING_CONFIRMATION",
)


class UserAnalyticalProfile(Base):
    __tablename__ = "user_analytical_profiles"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", "user_id", name="uq_user_profile_identity"),
        UniqueConstraint("tenant_id", "user_id", name="uq_user_profile_owner"),
        ForeignKeyConstraint(
            ["user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_user_profile_owner_tenant",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "status IN ('ACTIVE','DISABLED','DELETION_PENDING','DELETED')",
            name="ck_user_profile_status",
        ),
        CheckConstraint("profile_version >= 1", name="ck_user_profile_version"),
        CheckConstraint("lock_version >= 0", name="ck_user_profile_lock"),
        CheckConstraint("checksum ~ '^[a-f0-9]{64}$'", name="ck_user_profile_checksum"),
        CheckConstraint(
            "(status = 'DISABLED' AND disabled_at IS NOT NULL) "
            "OR (status <> 'DISABLED')",
            name="ck_user_profile_disabled",
        ),
        CheckConstraint(
            "(status = 'DELETED' AND deleted_at IS NOT NULL) "
            "OR (status <> 'DELETED' AND deleted_at IS NULL)",
            name="ck_user_profile_deleted",
        ),
        Index("idx_user_profiles_tenant_user", "tenant_id", "user_id"),
        Index("idx_user_profiles_status", "tenant_id", "status", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="ACTIVE")
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    lock_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
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
    disabled_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class UserPreferenceItem(Base):
    __tablename__ = "user_preference_items"
    __table_args__ = (
        UniqueConstraint(
            "id", "profile_id", "tenant_id", "user_id",
            name="uq_user_preference_identity",
        ),
        UniqueConstraint(
            "profile_id", "preference_type", "preference_key",
            name="uq_user_preference_key",
        ),
        ForeignKeyConstraint(
            ["profile_id", "tenant_id", "user_id"],
            [
                "user_analytical_profiles.id",
                "user_analytical_profiles.tenant_id",
                "user_analytical_profiles.user_id",
            ],
            name="fk_user_preference_profile_owner",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["created_by_user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_user_preference_creator_tenant",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            f"preference_type IN {PREFERENCE_TYPES!r}".replace(",)", ")"),
            name="ck_user_preference_type",
        ),
        CheckConstraint(
            f"status IN {PREFERENCE_STATUSES!r}".replace(",)", ")"),
            name="ck_user_preference_status",
        ),
        CheckConstraint(
            "risk IN ('SAFE_PRESENTATION','VISIBLE_ANALYTICAL_DEFAULT',"
            "'REFERENCE_ONLY','RESTRICTED','FORBIDDEN')",
            name="ck_user_preference_risk",
        ),
        CheckConstraint(
            "origin IN ('USER_EXPLICIT','SYSTEM_DEFAULT','ADMIN_POLICY',"
            "'LEGACY_IMPORT','MIGRATED','FEEDBACK_CANDIDATE','INFERRED_UNCONFIRMED')",
            name="ck_user_preference_origin",
        ),
        CheckConstraint("version >= 1", name="ck_user_preference_version"),
        CheckConstraint("lock_version >= 0", name="ck_user_preference_lock"),
        CheckConstraint(
            "checksum ~ '^[a-f0-9]{64}$'", name="ck_user_preference_checksum"
        ),
        CheckConstraint(
            "jsonb_typeof(content) = 'object'", name="ck_user_preference_content"
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from",
            name="ck_user_preference_effective_period",
        ),
        CheckConstraint(
            "expires_at IS NULL OR effective_from IS NULL OR expires_at > effective_from",
            name="ck_user_preference_expiration",
        ),
        CheckConstraint(
            "(status = 'DELETED' AND deleted_at IS NOT NULL) "
            "OR (status <> 'DELETED' AND deleted_at IS NULL)",
            name="ck_user_preference_deleted",
        ),
        Index(
            "idx_user_preferences_tenant_user_type",
            "tenant_id", "user_id", "preference_type", "id",
        ),
        Index(
            "idx_user_preferences_tenant_user_key",
            "tenant_id", "user_id", "preference_key", "id",
        ),
        Index(
            "idx_user_preferences_active",
            "tenant_id", "user_id", "status", "updated_at",
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        Index("idx_user_preferences_expiration", "tenant_id", "expires_at"),
        Index(
            "idx_user_preferences_saved_reference",
            "tenant_id", "user_id", "preference_type", "preference_key",
            postgresql_where=text(
                "preference_type IN ('SAVED_FILTER_REFERENCE',"
                "'SAVED_QUERY_REFERENCE','SAVED_DASHBOARD_REFERENCE')"
            ),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    preference_type: Mapped[str] = mapped_column(String(40), nullable=False)
    preference_key: Mapped[str] = mapped_column(String(128), nullable=False)
    content: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    risk: Mapped[str] = mapped_column(String(40), nullable=False)
    origin: Mapped[str] = mapped_column(String(40), nullable=False)
    origin_metadata: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="ACTIVE")
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    lock_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_from: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
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


class UserPreferenceConsent(Base):
    __tablename__ = "user_preference_consents"
    __table_args__ = (
        UniqueConstraint(
            "id", "preference_id", "profile_id", "tenant_id", "user_id",
            name="uq_user_preference_consent_identity",
        ),
        ForeignKeyConstraint(
            ["preference_id", "profile_id", "tenant_id", "user_id"],
            [
                "user_preference_items.id",
                "user_preference_items.profile_id",
                "user_preference_items.tenant_id",
                "user_preference_items.user_id",
            ],
            name="fk_user_preference_consent_item",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "status IN ('GRANTED','REVOKED')", name="ck_user_preference_consent_status"
        ),
        CheckConstraint("lock_version >= 0", name="ck_user_preference_consent_lock"),
        CheckConstraint(
            "checksum ~ '^[a-f0-9]{64}$'", name="ck_user_preference_consent_checksum"
        ),
        CheckConstraint(
            "(status = 'GRANTED' AND granted_at IS NOT NULL) "
            "OR (status = 'REVOKED' AND revoked_at IS NOT NULL)",
            name="ck_user_preference_consent_timestamps",
        ),
        CheckConstraint(
            "revoked_at IS NULL OR granted_at IS NULL OR revoked_at >= granted_at",
            name="ck_user_preference_consent_order",
        ),
        Index(
            "idx_user_preference_consents_owner",
            "tenant_id", "user_id", "status", "preference_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    preference_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    purpose: Mapped[str] = mapped_column(String(256), nullable=False)
    scope: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    granted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    lock_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class UserProfileEvent(Base):
    __tablename__ = "user_profile_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["profile_id", "tenant_id", "user_id"],
            [
                "user_analytical_profiles.id",
                "user_analytical_profiles.tenant_id",
                "user_analytical_profiles.user_id",
            ],
            name="fk_user_profile_event_profile",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["actor_user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_user_profile_event_actor",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "jsonb_typeof(event_metadata) = 'object'",
            name="ck_user_profile_event_metadata",
        ),
        Index(
            "idx_user_profile_events_owner_time",
            "tenant_id", "user_id", "created_at", "id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    preference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(128))
    event_metadata: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    schema_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default=CONTRACT_VERSION
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class UserProfileExport(Base):
    __tablename__ = "user_profile_exports"
    __table_args__ = (
        ForeignKeyConstraint(
            ["profile_id", "tenant_id", "user_id"],
            [
                "user_analytical_profiles.id",
                "user_analytical_profiles.tenant_id",
                "user_analytical_profiles.user_id",
            ],
            name="fk_user_profile_export_profile",
            ondelete="CASCADE",
        ),
        CheckConstraint("checksum ~ '^[a-f0-9]{64}$'", name="ck_user_profile_export_checksum"),
        CheckConstraint("payload_size >= 0", name="ck_user_profile_export_size"),
        Index(
            "idx_user_profile_exports_owner_time",
            "tenant_id", "user_id", "created_at", "id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    format: Mapped[str] = mapped_column(String(16), nullable=False, default="JSON")
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="COMPLETED")
    schema_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default=CONTRACT_VERSION
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class UserProfileDeletionRequest(Base):
    __tablename__ = "user_profile_deletion_requests"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "user_id", "idempotency_key_hash",
            name="uq_user_profile_deletion_idempotency",
        ),
        ForeignKeyConstraint(
            ["profile_id", "tenant_id", "user_id"],
            [
                "user_analytical_profiles.id",
                "user_analytical_profiles.tenant_id",
                "user_analytical_profiles.user_id",
            ],
            name="fk_user_profile_deletion_profile",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('PENDING','COMPLETED','REJECTED')",
            name="ck_user_profile_deletion_status",
        ),
        CheckConstraint(
            "idempotency_key_hash ~ '^[a-f0-9]{64}$'",
            name="ck_user_profile_deletion_idempotency",
        ),
        Index(
            "idx_user_profile_deletions_owner_status",
            "tenant_id", "user_id", "status", "requested_at", "id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    reason: Mapped[str | None] = mapped_column(Text)
    idempotency_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    schema_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default=CONTRACT_VERSION
    )
