"""
LuminaAI Governed Validation & Provenance V2 SQLAlchemy Models
Version: lumina.validation-provenance/1.0
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    BIGINT,
    BOOLEAN,
    FLOAT,
    INTEGER,
    JSON,
    NUMERIC,
    TEXT,
    VARCHAR,
    CheckConstraint,
    Column,
    ForeignKey,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class ValidationPolicyModel(Base):
    __tablename__ = "validation_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_name = Column(VARCHAR(255), nullable=False)
    version = Column(VARCHAR(64), nullable=False, default="1.0.0")
    required_stages = Column(JSON, nullable=False, default=list)
    validators_config = Column(JSON, nullable=False, default=list)
    fail_fast = Column(BOOLEAN, nullable=False, default=True)
    allow_partial = Column(BOOLEAN, nullable=False, default=False)
    require_fact_bindings = Column(BOOLEAN, nullable=False, default=True)
    strict_decimal = Column(BOOLEAN, nullable=False, default=True)
    freshness_tolerance_seconds = Column(INTEGER, nullable=False, default=86400)
    is_active = Column(BOOLEAN, nullable=False, default=True)
    lock_version = Column(BIGINT, nullable=False, default=1)
    checksum = Column(VARCHAR(64), nullable=False)
    created_at = Column(VARCHAR(64), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "policy_name", "version", name="uq_validation_policy_tenant_name_version"),
        CheckConstraint("lock_version >= 1", name="ck_validation_policy_lock_version"),
    )


class ValidationRunModel(Base):
    __tablename__ = "validation_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    request_id = Column(VARCHAR(128), nullable=False, index=True)
    orchestration_run_id = Column(VARCHAR(128), nullable=True, index=True)
    overall_status = Column(VARCHAR(32), nullable=False, index=True)
    total_execution_time_ms = Column(FLOAT, nullable=False, default=0.0)
    lock_version = Column(BIGINT, nullable=False, default=1)
    checksum = Column(VARCHAR(64), nullable=False)
    created_at = Column(VARCHAR(64), nullable=False, index=True)

    __table_args__ = (
        CheckConstraint("lock_version >= 1", name="ck_validation_run_lock_version"),
    )


class AnalyticalFactModel(Base):
    __tablename__ = "analytical_facts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    fact_id = Column(VARCHAR(128), nullable=False)
    fact_type = Column(VARCHAR(64), nullable=False, index=True)
    canonical_metric_id = Column(VARCHAR(128), nullable=True, index=True)
    period_start = Column(VARCHAR(64), nullable=True)
    period_end = Column(VARCHAR(64), nullable=True)
    decimal_value = Column(VARCHAR(128), nullable=True)
    int_value = Column(BIGINT, nullable=True)
    string_value = Column(TEXT, nullable=True)
    unit = Column(VARCHAR(64), nullable=True)
    currency = Column(VARCHAR(16), nullable=True)
    completeness = Column(VARCHAR(64), nullable=False, default="COMPLETE")
    source_result_ref = Column(VARCHAR(128), nullable=False)
    metric_fingerprint = Column(VARCHAR(64), nullable=True)
    tenant_proof_checksum = Column(VARCHAR(64), nullable=False)
    validation_status = Column(VARCHAR(32), nullable=False, default="VALID")
    checksum = Column(VARCHAR(64), nullable=False, index=True)
    created_at = Column(VARCHAR(64), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "fact_id", "checksum", name="uq_analytical_fact_tenant_fact_checksum"),
    )


class AnalyticalClaimModel(Base):
    __tablename__ = "analytical_claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id = Column(VARCHAR(128), nullable=False)
    claim_type = Column(VARCHAR(64), nullable=False, index=True)
    text = Column(TEXT, nullable=False)
    origin = Column(VARCHAR(64), nullable=False, default="MODEL_PROPOSED")
    checksum = Column(VARCHAR(64), nullable=False, index=True)
    created_at = Column(VARCHAR(64), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "claim_id", "checksum", name="uq_analytical_claim_tenant_claim_checksum"),
    )


class AnalyticalClaimBindingModel(Base):
    __tablename__ = "analytical_claim_bindings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id = Column(VARCHAR(128), nullable=False, index=True)
    fact_ids = Column(JSON, nullable=False, default=list)
    validation_status = Column(VARCHAR(32), nullable=False, index=True)
    public_display_value = Column(TEXT, nullable=True)
    canonical_value_checksum = Column(VARCHAR(64), nullable=False)
    mismatch_reason = Column(TEXT, nullable=True)
    created_at = Column(VARCHAR(64), nullable=False)


class ProvenanceManifestModel(Base):
    __tablename__ = "provenance_manifests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    request_id = Column(VARCHAR(128), nullable=False, index=True)
    graph_data = Column(JSON, nullable=False)
    graph_checksum = Column(VARCHAR(64), nullable=False)
    fact_count = Column(INTEGER, nullable=False, default=0)
    claim_count = Column(INTEGER, nullable=False, default=0)
    manifest_checksum = Column(VARCHAR(64), nullable=False, index=True)
    created_at = Column(VARCHAR(64), nullable=False)


class ResultCertificationModel(Base):
    __tablename__ = "result_certifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    request_id = Column(VARCHAR(128), nullable=False, index=True)
    result_checksum = Column(VARCHAR(64), nullable=False, index=True)
    query_fingerprint = Column(VARCHAR(64), nullable=True)
    tenant_proof_checksum = Column(VARCHAR(64), nullable=False)
    status = Column(VARCHAR(32), nullable=False, index=True)
    certified_at = Column(VARCHAR(64), nullable=False)
    checksum = Column(VARCHAR(64), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "request_id", "result_checksum", name="uq_result_cert_tenant_request_result"),
    )


class ResponseCertificationModel(Base):
    __tablename__ = "response_certifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    result_certification_id = Column(UUID(as_uuid=True), ForeignKey("result_certifications.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    request_id = Column(VARCHAR(128), nullable=False, index=True)
    response_draft_checksum = Column(VARCHAR(64), nullable=False, index=True)
    claim_validation_data = Column(JSON, nullable=False)
    status = Column(VARCHAR(32), nullable=False, index=True)
    superseded_by_id = Column(UUID(as_uuid=True), nullable=True)
    lock_version = Column(BIGINT, nullable=False, default=1)
    certified_at = Column(VARCHAR(64), nullable=False)
    checksum = Column(VARCHAR(64), nullable=False, index=True)

    __table_args__ = (
        CheckConstraint("lock_version >= 1", name="ck_response_cert_lock_version"),
    )


class ValidationEventModel(Base):
    __tablename__ = "validation_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_type = Column(VARCHAR(64), nullable=False, index=True)
    certification_id = Column(UUID(as_uuid=True), nullable=True)
    severity = Column(VARCHAR(32), nullable=False, default="INFO")
    message = Column(TEXT, nullable=False)
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(VARCHAR(64), nullable=False, index=True)
