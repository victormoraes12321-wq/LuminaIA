from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints, model_validator

from contracts.analytical_v2 import (
    ComparisonSpecification,
    DimensionReference,
    ExecutionReadiness,
    FieldOrigin,
    FilterSpecification,
    IntentKind,
    MetricReference,
    TimeWindow,
    VisualizationSpecification,
)


CONVERSATION_STATE_VERSION = "lumina.conversation-state/1.0"
PublicSessionId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=16,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]+$",
    ),
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StrictConversationModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )


class ConversationRolloutMode(str, Enum):
    LEGACY_ONLY = "LEGACY_ONLY"
    SHADOW_WRITE = "SHADOW_WRITE"
    DUAL_WRITE_LEGACY_READ = "DUAL_WRITE_LEGACY_READ"
    POSTGRES_READ_WRITE = "POSTGRES_READ_WRITE"
    POSTGRES_ONLY = "POSTGRES_ONLY"


class ConversationSessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    EXPIRED = "EXPIRED"
    DELETED = "DELETED"


class ConversationNodeType(str, Enum):
    USER_QUERY = "USER_QUERY"
    ASSISTANT_RESPONSE = "ASSISTANT_RESPONSE"
    CLARIFICATION_REQUEST = "CLARIFICATION_REQUEST"
    CLARIFICATION_RESPONSE = "CLARIFICATION_RESPONSE"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"
    RESET = "RESET"
    SYSTEM_EVENT = "SYSTEM_EVENT"


class ConversationNodeStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SUPERSEDED = "SUPERSEDED"


class ConversationEventType(str, Enum):
    SESSION_CREATED = "SESSION_CREATED"
    TURN_STARTED = "TURN_STARTED"
    TURN_COMPLETED = "TURN_COMPLETED"
    TURN_FAILED = "TURN_FAILED"
    TURN_CANCELLED = "TURN_CANCELLED"
    CONTEXT_UPDATED = "CONTEXT_UPDATED"
    CONTEXT_CONFLICT = "CONTEXT_CONFLICT"
    SESSION_RESET = "SESSION_RESET"
    SESSION_ARCHIVED = "SESSION_ARCHIVED"
    SESSION_REOPENED = "SESSION_REOPENED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    SESSION_DELETED = "SESSION_DELETED"
    SESSION_PURGED = "SESSION_PURGED"
    LEGACY_IMPORTED = "LEGACY_IMPORTED"
    SHADOW_DIVERGENCE = "SHADOW_DIVERGENCE"
    RECOVERY_ISSUE = "RECOVERY_ISSUE"


class ConversationStateV2(StrictConversationModel):
    schema_version: str = CONVERSATION_STATE_VERSION
    context_epoch: int = Field(default=0, ge=0)
    context_version: int = Field(default=0, ge=0)
    active_metric_refs: list[MetricReference] = Field(default_factory=list)
    active_dimension_refs: list[DimensionReference] = Field(default_factory=list)
    active_filters: list[FilterSpecification] = Field(default_factory=list)
    active_time_windows: list[TimeWindow] = Field(default_factory=list)
    active_comparison: ComparisonSpecification | None = None
    active_visualizations: list[VisualizationSpecification] = Field(default_factory=list)
    active_subject: str | None = Field(default=None, max_length=256)
    last_intent_kind: IntentKind | None = None
    last_readiness: ExecutionReadiness | None = None
    last_plan_fingerprint: str | None = Field(default=None, max_length=128)
    last_response_fingerprint: str | None = Field(default=None, max_length=128)
    last_query_node_id: UUID | None = None
    last_response_node_id: UUID | None = None
    pending_clarification: bool = False
    field_origins: dict[str, FieldOrigin] = Field(default_factory=dict)
    context_markers: list[str] = Field(default_factory=list, max_length=100)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_version(self) -> "ConversationStateV2":
        if self.schema_version != CONVERSATION_STATE_VERSION:
            raise ValueError("unsupported conversation state schema version")
        if self.updated_at.tzinfo is None:
            raise ValueError("updated_at must be timezone-aware")
        return self


def compute_state_checksum(state: ConversationStateV2) -> str:
    payload = state.model_dump(mode="json", exclude={"updated_at"})
    normalized = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class ConversationSessionV2(StrictConversationModel):
    id: UUID
    public_session_id: PublicSessionId
    tenant_id: UUID
    user_id: UUID
    status: ConversationSessionStatus
    schema_version: str = CONVERSATION_STATE_VERSION
    context_epoch: int = Field(ge=0)
    context_version: int = Field(ge=0)
    lock_version: int = Field(ge=0)
    next_sequence: int = Field(ge=1)
    active_head_node_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime
    expires_at: datetime
    archived_at: datetime | None = None
    deleted_at: datetime | None = None


class ConversationNodeV2(StrictConversationModel):
    id: UUID
    session_id: UUID
    tenant_id: UUID
    user_id: UUID
    sequence_number: int = Field(ge=1)
    parent_node_id: UUID | None = None
    role: str = Field(pattern=r"^(user|assistant|system)$")
    node_type: ConversationNodeType
    status: ConversationNodeStatus
    client_message_id: UUID | None = None
    search_history_id: UUID | None = None
    plan_fingerprint: str | None = Field(default=None, max_length=128)
    response_fingerprint: str | None = Field(default=None, max_length=128)
    created_at: datetime
    completed_at: datetime | None = None
    failed_at: datetime | None = None


class ConversationStateSnapshotV2(StrictConversationModel):
    id: UUID
    session_id: UUID
    tenant_id: UUID
    user_id: UUID
    context_epoch: int = Field(ge=0)
    context_version: int = Field(ge=0)
    head_node_id: UUID | None = None
    schema_version: str = CONVERSATION_STATE_VERSION
    state: ConversationStateV2
    state_checksum: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")
    created_at: datetime

    @model_validator(mode="after")
    def validate_checksum(self) -> "ConversationStateSnapshotV2":
        if self.context_epoch != self.state.context_epoch:
            raise ValueError("snapshot epoch does not match state")
        if self.context_version != self.state.context_version:
            raise ValueError("snapshot version does not match state")
        if compute_state_checksum(self.state) != self.state_checksum:
            raise ValueError("snapshot checksum mismatch")
        return self


class ConversationEventV2(StrictConversationModel):
    id: UUID
    session_id: UUID
    tenant_id: UUID
    user_id: UUID
    event_type: ConversationEventType
    schema_version: str = CONVERSATION_STATE_VERSION
    context_epoch: int = Field(ge=0)
    context_version: int = Field(ge=0)
    node_id: UUID | None = None
    fingerprint: str | None = Field(default=None, max_length=128)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    created_at: datetime


class ConversationTurnStart(StrictConversationModel):
    public_session_id: PublicSessionId | None = None
    client_message_id: UUID
    parent_node_id: UUID | None = None
    expected_context_version: int | None = Field(default=None, ge=0)
    content: str = Field(min_length=1, max_length=4000)


class ConversationTurnCompletion(StrictConversationModel):
    session_id: UUID
    query_node_id: UUID
    base_context_version: int = Field(ge=0)
    response_content: str = Field(min_length=1, max_length=12000)
    state: ConversationStateV2
    response_fingerprint: str | None = Field(default=None, max_length=128)
    search_history_id: UUID | None = None


class ConversationTurnFailure(StrictConversationModel):
    session_id: UUID
    query_node_id: UUID
    base_context_version: int = Field(ge=0)
    error_code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z0-9_]+$")
    safe_message: str = Field(min_length=1, max_length=500)


class ConversationConflict(StrictConversationModel):
    code: str = Field(min_length=1, max_length=64)
    expected_context_version: int | None = Field(default=None, ge=0)
    actual_context_version: int = Field(ge=0)
    recoverable: bool


class ConversationMutationResult(StrictConversationModel):
    session: ConversationSessionV2
    query_node: ConversationNodeV2 | None = None
    response_node: ConversationNodeV2 | None = None
    snapshot: ConversationStateSnapshotV2 | None = None
    idempotent_replay: bool = False
    conflict: ConversationConflict | None = None


class ConversationLoadResult(StrictConversationModel):
    session: ConversationSessionV2
    state: ConversationStateV2
    nodes: list[ConversationNodeV2] = Field(default_factory=list)
    next_cursor: int | None = Field(default=None, ge=1)
    warning: str | None = Field(default=None, max_length=500)


class ConversationRetentionPolicy(StrictConversationModel):
    active_ttl_hours: int = Field(default=24, ge=1, le=24 * 365)
    archive_after_days: int = Field(default=30, ge=1, le=3650)
    soft_delete_after_days: int = Field(default=180, ge=1, le=3650)
    purge_after_days: int = Field(default=365, ge=1, le=7300)
    preserve_minimal_events: bool = False
    max_content_bytes: int = Field(default=12000, ge=256, le=1_000_000)
    max_nodes: int = Field(default=10000, ge=10, le=1_000_000)
    purge_batch_size: int = Field(default=100, ge=1, le=1000)

    @model_validator(mode="after")
    def validate_order(self) -> "ConversationRetentionPolicy":
        if not (
            self.archive_after_days
            <= self.soft_delete_after_days
            <= self.purge_after_days
        ):
            raise ValueError("retention periods must be ordered")
        return self


class ConversationImportResult(StrictConversationModel):
    source_checksum: str = Field(min_length=64, max_length=64)
    public_session_id: PublicSessionId | None = None
    imported_nodes: int = Field(default=0, ge=0)
    dry_run: bool = True
    duplicate: bool = False
    warnings: list[str] = Field(default_factory=list, max_length=100)
