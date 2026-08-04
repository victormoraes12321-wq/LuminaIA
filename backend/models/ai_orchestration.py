from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from database import Base


class AIOrchestrationPolicyModel(Base):
    __tablename__ = "ai_orchestration_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id = Column(String(128), nullable=False)
    tenant_id = Column(String(128), nullable=False, default="system")
    policy_data = Column(JSONB, nullable=False)
    version = Column(String(32), nullable=False, default="lumina.ai-orchestration/1.0")
    is_active = Column(Boolean, nullable=False, default=True)
    checksum = Column(String(64), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "policy_id", name="uq_ai_orchestration_policy"),
    )


class AIModelDefinitionModel(Base):
    __tablename__ = "ai_model_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_model_id = Column(String(128), nullable=False, unique=True)
    provider_id = Column(String(64), nullable=False)
    internal_provider_model_name = Column(String(128), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    definition_data = Column(JSONB, nullable=False)
    checksum = Column(String(64), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class AIProviderDefinitionModel(Base):
    __tablename__ = "ai_provider_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(String(64), nullable=False, unique=True)
    display_name = Column(String(128), nullable=False)
    adapter_class = Column(String(256), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    definition_data = Column(JSONB, nullable=False)
    checksum = Column(String(64), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class AIPromptTemplateVersionModel(Base):
    __tablename__ = "ai_prompt_template_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(String(128), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    purpose = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="ACTIVE")
    system_policy_text = Column(Text, nullable=False)
    template_data = Column(JSONB, nullable=False)
    checksum = Column(String(64), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("template_id", "version", name="uq_ai_prompt_template_ver"),
    )


class AIOrchestrationRunModel(Base):
    __tablename__ = "ai_orchestration_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(String(128), nullable=False)
    tenant_id = Column(String(128), nullable=False)
    user_id = Column(String(128), nullable=False)
    session_id = Column(String(128), nullable=False)
    status = Column(String(32), nullable=False, default="RECEIVED")
    strategy = Column(String(32), nullable=False, default="SINGLE_MODEL_CALL")
    model_id = Column(String(128), nullable=True)
    provider_id = Column(String(64), nullable=True)
    idempotency_key = Column(String(128), nullable=True)
    run_data = Column(JSONB, nullable=False)
    lock_version = Column(BigInteger, nullable=False, default=0)
    checksum = Column(String(64), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "run_id", name="uq_ai_orch_run_id"),
        UniqueConstraint("tenant_id", "user_id", "idempotency_key", name="uq_ai_orch_idempotency"),
    )


class AIOrchestrationStepModel(Base):
    __tablename__ = "ai_orchestration_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(String(128), nullable=False)
    tenant_id = Column(String(128), nullable=False)
    step_sequence = Column(Integer, nullable=False)
    state_from = Column(String(32), nullable=False)
    state_to = Column(String(32), nullable=False)
    transition_reason = Column(Text, nullable=False)
    duration_ms = Column(Float, nullable=False, default=0.0)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "run_id", "step_sequence", name="uq_ai_orch_step_seq"),
    )


class AIModelInvocationRecordModel(Base):
    __tablename__ = "ai_model_invocations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invocation_id = Column(String(128), nullable=False)
    run_id = Column(String(128), nullable=False)
    tenant_id = Column(String(128), nullable=False)
    model_id = Column(String(128), nullable=False)
    provider_id = Column(String(64), nullable=False)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    duration_ms = Column(Float, nullable=False, default=0.0)
    status = Column(String(32), nullable=False, default="SUCCESS")
    checksum = Column(String(64), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "invocation_id", name="uq_ai_model_inv_id"),
    )


class AIToolCallRecordModel(Base):
    __tablename__ = "ai_orchestration_tool_calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tool_call_id = Column(String(128), nullable=False)
    run_id = Column(String(128), nullable=False)
    tenant_id = Column(String(128), nullable=False)
    sequence = Column(Integer, nullable=False)
    tool_id = Column(String(128), nullable=False)
    tool_version = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default="SUCCESS")
    args_checksum = Column(String(64), nullable=False)
    result_checksum = Column(String(64), nullable=False)
    duration_ms = Column(Float, nullable=False, default=0.0)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "run_id", "sequence", name="uq_ai_orch_tool_seq"),
    )


class AIUsageRecordModel(Base):
    __tablename__ = "ai_orchestration_usage_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id = Column(String(128), nullable=False)
    tenant_id = Column(String(128), nullable=False)
    user_id = Column(String(128), nullable=False)
    run_id = Column(String(128), nullable=False)
    model_id = Column(String(128), nullable=False)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    cost_estimate = Column(Float, nullable=False, default=0.0)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "record_id", name="uq_ai_orch_usage_id"),
    )


class AIEvaluationCaseModel(Base):
    __tablename__ = "ai_orchestration_evaluation_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(String(128), nullable=False)
    tenant_id = Column(String(128), nullable=False, default="system")
    title = Column(String(256), nullable=False)
    user_query = Column(Text, nullable=False)
    case_data = Column(JSONB, nullable=False)
    checksum = Column(String(64), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "case_id", name="uq_ai_orch_eval_case"),
    )


class AIEvaluationResultModel(Base):
    __tablename__ = "ai_orchestration_evaluation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_id = Column(String(128), nullable=False)
    case_id = Column(String(128), nullable=False)
    tenant_id = Column(String(128), nullable=False)
    passed = Column(Boolean, nullable=False, default=False)
    result_data = Column(JSONB, nullable=False)
    checksum = Column(String(64), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "evaluation_id", name="uq_ai_orch_eval_res"),
    )
