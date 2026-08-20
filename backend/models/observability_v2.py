"""SQLAlchemy models for V2 Observability, Metrics, SLOs, and Evaluations (Migration v25)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class OperationalMetricRollupModelV2(Base):
    __tablename__ = "operational_metric_rollups_v2"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_id = Column(String(128), nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    count = Column(Integer, nullable=False, default=0)
    sum_value = Column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"))
    min_value = Column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"))
    max_value = Column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"))
    avg_value = Column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"))
    labels = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_op_metric_rollups_metric_window", "metric_id", "window_start"),
    )


class TraceSummaryModelV2(Base):
    __tablename__ = "observability_trace_summaries_v2"

    trace_id = Column(String(128), primary_key=True)
    root_span_id = Column(String(128), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), nullable=True)
    route_template = Column(String(256), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    total_duration_ms = Column(Numeric(12, 2), nullable=False)
    status = Column(String(32), nullable=False)
    span_count = Column(Integer, nullable=False, default=1)
    spans_payload = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_trace_summaries_tenant_started", "tenant_id", "started_at"),
    )


class SloDefinitionModelV2(Base):
    __tablename__ = "observability_slo_definitions_v2"

    slo_id = Column(String(128), primary_key=True)
    sli_id = Column(String(128), nullable=False)
    target_percentage = Column(Numeric(5, 2), nullable=False)
    window_days = Column(Integer, nullable=False, default=30)
    is_provisional = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class SloEvaluationModelV2(Base):
    __tablename__ = "observability_slo_evaluations_v2"

    evaluation_id = Column(String(128), primary_key=True)
    slo_id = Column(String(128), ForeignKey("observability_slo_definitions_v2.slo_id"), nullable=False)
    evaluated_at = Column(DateTime(timezone=True), nullable=False)
    current_percentage = Column(Numeric(5, 2), nullable=False)
    target_percentage = Column(Numeric(5, 2), nullable=False)
    consumed_budget_percentage = Column(Numeric(5, 2), nullable=False)
    remaining_budget_percentage = Column(Numeric(5, 2), nullable=False)
    status = Column(String(32), nullable=False)
    error_budget_payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_slo_evaluations_slo_time", "slo_id", "evaluated_at"),
    )


class EvaluationSuiteModelV2(Base):
    __tablename__ = "evaluation_suites_v2"

    suite_id = Column(String(128), primary_key=True)
    kind = Column(String(64), nullable=False, unique=True)
    title = Column(String(128), nullable=False)
    description = Column(String(256), nullable=False)
    case_count = Column(Integer, nullable=False)
    deterministic_only = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class EvaluationRunModelV2(Base):
    __tablename__ = "evaluation_runs_v2"

    run_id = Column(String(128), primary_key=True)
    suite = Column(String(64), nullable=False)
    executed_at = Column(DateTime(timezone=True), nullable=False)
    total_cases = Column(Integer, nullable=False)
    passed_cases = Column(Integer, nullable=False)
    failed_cases = Column(Integer, nullable=False)
    blocked_cases = Column(Integer, nullable=False)
    error_cases = Column(Integer, nullable=False)
    duration_ms = Column(Numeric(12, 2), nullable=False)
    results_payload = Column(JSONB, nullable=False, default=list)
    regressions_payload = Column(JSONB, nullable=False, default=list)
    checksum = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_eval_runs_suite_time", "suite", "executed_at"),
    )


class EvaluationRegressionModelV2(Base):
    __tablename__ = "evaluation_regressions_v2"

    regression_id = Column(String(128), primary_key=True)
    run_id = Column(String(128), ForeignKey("evaluation_runs_v2.run_id"), nullable=True)
    case_id = Column(String(128), nullable=False)
    suite = Column(String(64), nullable=False)
    regression_type = Column(String(64), nullable=False)
    description = Column(String(256), nullable=False)
    detected_at = Column(DateTime(timezone=True), nullable=False)
    baseline_checksum = Column(String(128), nullable=False)
    current_checksum = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class ObservabilityAuditEventModelV2(Base):
    __tablename__ = "observability_audit_events_v2"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(64), nullable=False)
    classification = Column(String(32), nullable=False)
    trace_id = Column(String(128), nullable=False)
    span_id = Column(String(128), nullable=False)
    reason = Column(String(128), nullable=False)
    details = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_obs_audit_event_type_time", "event_type", "created_at"),
    )
