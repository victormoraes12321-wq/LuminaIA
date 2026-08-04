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

SAFE_ANALYTICAL_CONTRACT_VERSION = "lumina.safe-analytical-postgresql/1.0"


class AnalyticalCatalogDefinition(Base):
    __tablename__ = "analytical_catalog_definitions"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_analytical_catalog_def_tenant"),
        UniqueConstraint("tenant_id", "catalog_id", name="uq_analytical_catalog_id"),
        Index("idx_analytical_catalog_tenant", "tenant_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalog_id: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="Governed Analytical Catalog")
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class AnalyticalCatalogSnapshot(Base):
    __tablename__ = "analytical_catalog_snapshots"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_analytical_catalog_snap_tenant"),
        UniqueConstraint("tenant_id", "snapshot_id", name="uq_analytical_catalog_snap_id"),
        CheckConstraint(
            "lifecycle IN ('DRAFT','VALIDATING','READY','PUBLISHED','DEPRECATED','DISABLED','ARCHIVED')",
            name="ck_analytical_catalog_lifecycle",
        ),
        Index("idx_analytical_catalog_snap_lifecycle", "tenant_id", "lifecycle"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_id: Mapped[str] = mapped_column(String(128), nullable=False)
    catalog_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    lifecycle: Mapped[str] = mapped_column(String(32), nullable=False, default="PUBLISHED")
    snapshot_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    published_by: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    published_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class AnalyticalDatasetDefinition(Base):
    __tablename__ = "analytical_dataset_definitions"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_analytical_dataset_tenant"),
        UniqueConstraint("tenant_id", "canonical_dataset_id", name="uq_analytical_dataset_canonical"),
        CheckConstraint(
            "tenant_strategy IN ('TENANT_COLUMN_REQUIRED','DEDICATED_TENANT_DATABASE','CERTIFIED_ROW_LEVEL_SECURITY','CERTIFIED_TENANT_VIEW','SYSTEM_GLOBAL_METADATA','BLOCKED')",
            name="ck_analytical_dataset_tenant_strat",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_dataset_id: Mapped[str] = mapped_column(String(128), nullable=False)
    domain: Mapped[str] = mapped_column(String(64), nullable=False, default="sales")
    tenant_strategy: Mapped[str] = mapped_column(String(32), nullable=False, default="TENANT_COLUMN_REQUIRED")
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class AnalyticalExecutionRecord(Base):
    __tablename__ = "analytical_execution_records"
    __table_args__ = (
        Index("idx_analytical_exec_tenant_time", "tenant_id", "created_at"),
        Index("idx_analytical_exec_fingerprint", "query_fingerprint"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[str] = mapped_column(String(128), nullable=False)
    query_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(128), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    execution_time_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="SUCCESS")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
