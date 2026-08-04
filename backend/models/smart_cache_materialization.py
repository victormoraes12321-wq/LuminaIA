"""ORM models for ``lumina.smart-cache-materialization/1.0``."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SmartCachePolicyModel(Base):
    __tablename__ = "smart_cache_policies"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    policy_id = Column(String(128), nullable=False)
    policy_version = Column(String(64), nullable=False)
    contract_version = Column(String(64), nullable=False, default="lumina.smart-cache-materialization/1.0")
    config_json = Column(JSONB, nullable=False, default=dict)
    checksum = Column(String(64), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    lock_version = Column(BigInteger, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    __table_args__ = (
        UniqueConstraint("tenant_id", "policy_id", "policy_version", name="uq_smart_cache_policy_version"),
        CheckConstraint("lock_version >= 1", name="ck_smart_cache_policy_lock_version"),
        Index("idx_smart_cache_policy_active", "tenant_id", "is_active", "policy_id"),
    )


class SmartCacheGenerationModel(Base):
    __tablename__ = "smart_cache_generations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    target_scope = Column(String(128), nullable=False)
    generation = Column(BigInteger, nullable=False, default=1)
    reason = Column(String(256), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    __table_args__ = (
        UniqueConstraint("tenant_id", "target_scope", name="uq_smart_cache_generation_target"),
        CheckConstraint("generation >= 0", name="ck_smart_cache_generation_counter"),
        Index("idx_smart_cache_generation_lookup", "tenant_id", "target_scope", "generation"),
    )


class SmartCacheEntryModel(Base):
    __tablename__ = "smart_cache_entries"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    cache_type = Column(String(64), nullable=False)
    cache_key_checksum = Column(String(64), nullable=False)
    scope_fingerprint = Column(String(64), nullable=False)
    permission_fingerprint = Column(String(64), nullable=False)
    query_fingerprint = Column(String(64), nullable=False)
    analytical_catalog_version = Column(String(64), nullable=False)
    source_sync_version = Column(String(64), nullable=False)
    source_watermark = Column(String(128), nullable=False)
    validation_policy_version = Column(String(64), nullable=False)
    compiler_version = Column(String(64), nullable=False)
    tool_registry_snapshot = Column(String(128), nullable=False)
    certification_id = Column(String(128))
    tenant_proof_id = Column(String(128))
    status = Column(String(32), nullable=False, default="ACTIVE")
    freshness = Column(String(32), nullable=False, default="FRESH")
    generation = Column(BigInteger, nullable=False, default=1)
    hit_count = Column(BigInteger, nullable=False, default=0)
    payload_size_bytes = Column(Integer, nullable=False, default=0)
    classification = Column(String(64), nullable=False, default="INTERNAL")
    payload_json = Column(JSONB, nullable=False)
    payload_checksum = Column(String(64), nullable=False)
    entry_checksum = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    invalidated_at = Column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("tenant_id", "cache_key_checksum", name="uq_smart_cache_entry_key"),
        UniqueConstraint("id", "tenant_id", name="uq_smart_cache_entry_owner"),
        CheckConstraint("expires_at > created_at", name="ck_smart_cache_entry_ttl"),
        CheckConstraint("payload_size_bytes >= 0", name="ck_smart_cache_entry_payload_size"),
        CheckConstraint("generation >= 0", name="ck_smart_cache_entry_generation"),
        Index("idx_smart_cache_entry_lookup", "tenant_id", "cache_key_checksum", "status", "expires_at"),
        Index("idx_smart_cache_entry_query", "tenant_id", "query_fingerprint"),
    )


class SmartCacheEntryDependencyModel(Base):
    __tablename__ = "smart_cache_entry_dependencies"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    entry_id = Column(UUID(as_uuid=True), nullable=False)
    tag = Column(String(256), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["entry_id", "tenant_id"],
            ["smart_cache_entries.id", "smart_cache_entries.tenant_id"],
            ondelete="CASCADE",
            name="fk_smart_cache_dep_entry_tenant",
        ),
        UniqueConstraint("tenant_id", "entry_id", "tag", name="uq_smart_cache_entry_tag"),
        Index("idx_smart_cache_entry_dep_tag", "tenant_id", "tag", "entry_id"),
    )


class SmartCacheLeaseModel(Base):
    __tablename__ = "smart_cache_leases"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    cache_key_checksum = Column(String(64), nullable=False)
    owner_token_checksum = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="HELD")
    lock_version = Column(BigInteger, nullable=False, default=1)
    acquired_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        UniqueConstraint("tenant_id", "cache_key_checksum", name="uq_smart_cache_lease_key"),
        CheckConstraint("expires_at > acquired_at", name="ck_smart_cache_lease_expiry"),
        Index("idx_smart_cache_lease_expiry", "tenant_id", "expires_at", "status"),
    )


class SmartCacheEventModel(Base):
    __tablename__ = "smart_cache_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(64), nullable=False)
    cache_key_checksum = Column(String(64))
    user_id = Column(UUID(as_uuid=True))
    decision = Column(String(32))
    reason_code = Column(String(128), nullable=False)
    details_json = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    __table_args__ = (Index("idx_smart_cache_event_tenant_type", "tenant_id", "event_type", "created_at"),)


class MaterializationDefinitionModel(Base):
    __tablename__ = "materialization_definitions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    definition_id = Column(String(128), nullable=False)
    canonical_name = Column(String(128), nullable=False)
    materialization_type = Column(String(64), nullable=False)
    classification = Column(String(64), nullable=False, default="INTERNAL")
    lifecycle = Column(String(32), nullable=False, default="DRAFT")
    version = Column(Integer, nullable=False, default=1)
    lock_version = Column(BigInteger, nullable=False, default=1)
    query_json = Column(JSONB, nullable=False)
    source_json = Column(JSONB, nullable=False)
    query_fingerprint = Column(String(64), nullable=False)
    checksum = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    __table_args__ = (
        UniqueConstraint("tenant_id", "definition_id", "version", name="uq_materialization_definition_version"),
        CheckConstraint("version >= 1", name="ck_materialization_definition_version"),
        CheckConstraint("lock_version >= 1", name="ck_materialization_definition_lock_version"),
        Index("idx_materialization_definition_state", "tenant_id", "lifecycle", "definition_id", "version"),
    )


class MaterializationBuildModel(Base):
    __tablename__ = "materialization_builds"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    build_id = Column(String(128), nullable=False)
    definition_id = Column(String(128), nullable=False)
    definition_version = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False, default="BUILDING")
    error_code = Column(String(128))
    build_duration_ms = Column(Float, nullable=False, default=0.0)
    snapshot_id = Column(String(128))
    lock_version = Column(BigInteger, nullable=False, default=1)
    started_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    completed_at = Column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "definition_id", "definition_version"],
            ["materialization_definitions.tenant_id", "materialization_definitions.definition_id", "materialization_definitions.version"],
            ondelete="CASCADE",
            name="fk_materialization_build_definition",
        ),
        UniqueConstraint("tenant_id", "build_id", name="uq_materialization_build_id"),
        Index("idx_materialization_build_state", "tenant_id", "definition_id", "status", "started_at"),
    )


class MaterializationSnapshotModel(Base):
    __tablename__ = "materialization_snapshots"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    snapshot_id = Column(String(128), nullable=False)
    definition_id = Column(String(128), nullable=False)
    definition_version = Column(Integer, nullable=False)
    row_count = Column(Integer, nullable=False, default=0)
    fact_count = Column(Integer, nullable=False, default=0)
    payload_size_bytes = Column(Integer, nullable=False, default=0)
    certification_id = Column(String(128), nullable=False)
    certification_status = Column(String(32), nullable=False)
    tenant_proof_id = Column(String(128), nullable=False)
    watermark = Column(String(128), nullable=False)
    source_sync_version = Column(String(64), nullable=False)
    freshness = Column(String(32), nullable=False, default="FRESH")
    payload_json = Column(JSONB, nullable=False)
    payload_checksum = Column(String(64), nullable=False)
    checksum = Column(String(64), nullable=False)
    built_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at = Column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "definition_id", "definition_version"],
            ["materialization_definitions.tenant_id", "materialization_definitions.definition_id", "materialization_definitions.version"],
            ondelete="RESTRICT",
            name="fk_materialization_snapshot_definition",
        ),
        UniqueConstraint("tenant_id", "snapshot_id", name="uq_materialization_snapshot_id"),
        UniqueConstraint("tenant_id", "definition_id", "snapshot_id", name="uq_materialization_snapshot_definition"),
        Index("idx_materialization_snapshot_state", "tenant_id", "definition_id", "freshness", "built_at"),
    )


class MaterializationPublicationModel(Base):
    __tablename__ = "materialization_publications"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    definition_id = Column(String(128), nullable=False)
    definition_version = Column(Integer, nullable=False)
    active_snapshot_id = Column(String(128), nullable=False)
    previous_snapshot_id = Column(String(128))
    published_by = Column(UUID(as_uuid=True), nullable=False)
    lock_version = Column(BigInteger, nullable=False, default=1)
    published_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "definition_id", "definition_version"],
            ["materialization_definitions.tenant_id", "materialization_definitions.definition_id", "materialization_definitions.version"],
            ondelete="RESTRICT",
            name="fk_materialization_publication_definition",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "definition_id", "active_snapshot_id"],
            ["materialization_snapshots.tenant_id", "materialization_snapshots.definition_id", "materialization_snapshots.snapshot_id"],
            ondelete="RESTRICT",
            name="fk_materialization_publication_active",
        ),
        UniqueConstraint("tenant_id", "definition_id", name="uq_materialization_active_pub"),
    )


class MaterializationDependencyModel(Base):
    __tablename__ = "materialization_dependencies"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    definition_id = Column(String(128), nullable=False)
    definition_version = Column(Integer, nullable=False)
    tag = Column(String(256), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "definition_id", "definition_version"],
            ["materialization_definitions.tenant_id", "materialization_definitions.definition_id", "materialization_definitions.version"],
            ondelete="CASCADE",
            name="fk_materialization_dependency_definition",
        ),
        UniqueConstraint("tenant_id", "definition_id", "definition_version", "tag", name="uq_materialization_dep_tag"),
        Index("idx_materialization_dependency_tag", "tenant_id", "tag", "definition_id"),
    )


class MaterializationEventModel(Base):
    __tablename__ = "materialization_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    definition_id = Column(String(128), nullable=False)
    event_type = Column(String(64), nullable=False)
    user_id = Column(UUID(as_uuid=True))
    details_json = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    __table_args__ = (Index("idx_materialization_event_tenant", "tenant_id", "definition_id", "event_type", "created_at"),)


class SmartCacheEvaluationCaseModel(Base):
    __tablename__ = "smart_cache_evaluation_cases"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    case_id = Column(String(128), nullable=False)
    description = Column(Text, nullable=False)
    scenario_type = Column(String(64), nullable=False)
    canonical_query_fingerprint = Column(String(64), nullable=False)
    expected_decision = Column(String(32), nullable=False)
    expected_freshness = Column(String(32), nullable=False)
    checksum = Column(String(64), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    __table_args__ = (
        UniqueConstraint("tenant_id", "case_id", name="uq_smart_cache_eval_case"),
        UniqueConstraint("tenant_id", "case_id", "checksum", name="uq_smart_cache_eval_owner"),
    )


class SmartCacheEvaluationResultModel(Base):
    __tablename__ = "smart_cache_evaluation_results"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    case_id = Column(String(128), nullable=False)
    case_checksum = Column(String(64), nullable=False)
    actual_decision = Column(String(32), nullable=False)
    actual_freshness = Column(String(32), nullable=False)
    passed = Column(Boolean, nullable=False)
    details_json = Column(JSONB, nullable=False, default=dict)
    evaluated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "case_id", "case_checksum"],
            ["smart_cache_evaluation_cases.tenant_id", "smart_cache_evaluation_cases.case_id", "smart_cache_evaluation_cases.checksum"],
            ondelete="CASCADE",
            name="fk_smart_cache_eval_result_case",
        ),
        Index("idx_smart_cache_eval_result_case", "tenant_id", "case_id", "evaluated_at"),
    )
