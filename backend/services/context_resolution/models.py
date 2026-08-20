from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from contracts.analytical_v2 import (
    ClarificationRequest,
    ComparisonSpecification,
    ConfidenceAssessment,
    DimensionReference,
    ExecutionReadiness,
    FieldOrigin,
    FilterSpecification,
    MetricReference,
    OrderingSpecification,
    QueryIntentV2,
    TimeWindow,
    VisualizationSpecification,
)
from contracts.conversation_state_v2 import ConversationRolloutMode, ConversationStateV2


CONTEXT_RESOLUTION_VERSION = "lumina.context-resolution/1.0"


class StrictContextModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )


class ContextRelationship(str, Enum):
    NEW_TOPIC = "NEW_TOPIC"
    FOLLOW_UP = "FOLLOW_UP"
    REFINEMENT = "REFINEMENT"
    CORRECTION = "CORRECTION"
    REMOVAL = "REMOVAL"
    COMPARISON_EXTENSION = "COMPARISON_EXTENSION"
    DRILL_DOWN = "DRILL_DOWN"
    ROLL_UP = "ROLL_UP"
    CLARIFICATION_ANSWER = "CLARIFICATION_ANSWER"
    BACKTRACK = "BACKTRACK"
    BRANCH_CONTINUATION = "BRANCH_CONTINUATION"
    RESET = "RESET"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    UNRESOLVED = "UNRESOLVED"


class FieldDecisionAction(str, Enum):
    SET = "SET"
    REPLACE = "REPLACE"
    APPEND = "APPEND"
    INHERIT = "INHERIT"
    KEEP = "KEEP"
    REMOVE = "REMOVE"
    CLEAR = "CLEAR"
    RESET = "RESET"
    CLARIFY = "CLARIFY"


class ConflictSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class ContextResolutionContext(StrictContextModel):
    tenant_id: UUID
    user_id: UUID
    session_id: UUID
    current_node_id: UUID
    parent_node_id: UUID | None = None
    active_head_node_id: UUID | None = None
    context_epoch: int = Field(ge=0)
    context_version: int = Field(ge=0)
    expected_context_version: int | None = Field(default=None, ge=0)
    branch_path: list[UUID] = Field(default_factory=list, max_length=50)
    user_role: str = Field(min_length=1, max_length=32, pattern=r"^[A-Z_]+$")
    locale: str = Field(default="pt-BR", min_length=2, max_length=16)
    timezone: str = Field(min_length=1, max_length=64)
    reference_datetime: datetime
    rollout_mode: ConversationRolloutMode
    feature_flags: dict[str, bool] = Field(default_factory=dict, max_length=20)
    maximum_context_depth: int = Field(default=20, ge=1, le=100)
    maximum_inherited_fields: int = Field(default=50, ge=1, le=200)
    source: Literal["HTTP_QUERY", "TEST", "LEGACY_ADAPTER", "REPLAY"] = "HTTP_QUERY"

    @model_validator(mode="after")
    def validate_context(self) -> "ContextResolutionContext":
        if self.reference_datetime.tzinfo is None:
            raise ValueError("reference_datetime must be timezone-aware")
        if len(self.branch_path) > self.maximum_context_depth:
            raise ValueError("branch_path exceeds maximum_context_depth")
        if self.parent_node_id and self.branch_path and self.parent_node_id not in self.branch_path:
            raise ValueError("parent_node_id must belong to branch_path")
        if (
            self.expected_context_version is not None
            and self.expected_context_version != self.context_version
        ):
            raise ValueError("expected_context_version does not match current context")
        return self


class ContextSubjectSignature(StrictContextModel):
    domain: str = Field(min_length=1, max_length=64)
    metric_ids: list[str] = Field(default_factory=list, max_length=20)
    entity_types: list[str] = Field(default_factory=list, max_length=20)
    dimension_ids: list[str] = Field(default_factory=list, max_length=20)
    comparison_kind: str | None = Field(default=None, max_length=64)
    intent_kind: str = Field(min_length=1, max_length=64)
    fingerprint: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")


PatchFieldValue = (
    MetricReference
    | DimensionReference
    | FilterSpecification
    | TimeWindow
    | VisualizationSpecification
    | ComparisonSpecification
    | ClarificationRequest
    | OrderingSpecification
    | ContextSubjectSignature
    | str
    | int
    | bool
)


class PatchOperationBase(StrictContextModel):
    operation_id: str = Field(min_length=16, max_length=64)
    field_path: str = Field(min_length=1, max_length=128)
    origin: FieldOrigin
    source_node_id: UUID
    reason_code: str = Field(min_length=1, max_length=100)
    confidence: ConfidenceAssessment
    value_fingerprint: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")


class SetFieldOperation(PatchOperationBase):
    operation: Literal["SET_FIELD"] = "SET_FIELD"
    value: PatchFieldValue


class ReplaceFieldOperation(PatchOperationBase):
    operation: Literal["REPLACE_FIELD"] = "REPLACE_FIELD"
    value: PatchFieldValue


class AppendFieldOperation(PatchOperationBase):
    operation: Literal["APPEND_FIELD"] = "APPEND_FIELD"
    value: PatchFieldValue


class RemoveFieldOperation(PatchOperationBase):
    operation: Literal["REMOVE_FIELD"] = "REMOVE_FIELD"
    target_key: str = Field(min_length=1, max_length=256)


class ClearFieldOperation(PatchOperationBase):
    operation: Literal["CLEAR_FIELD"] = "CLEAR_FIELD"


class ResetContextOperation(PatchOperationBase):
    operation: Literal["RESET_CONTEXT"] = "RESET_CONTEXT"
    reset_scope: Literal["TOTAL", "ANALYSIS"] = "TOTAL"


class SetPendingClarificationOperation(PatchOperationBase):
    operation: Literal["SET_PENDING_CLARIFICATION"] = "SET_PENDING_CLARIFICATION"
    clarification: ClarificationRequest


class ResolvePendingClarificationOperation(PatchOperationBase):
    operation: Literal["RESOLVE_PENDING_CLARIFICATION"] = "RESOLVE_PENDING_CLARIFICATION"


class SetActiveSubjectOperation(PatchOperationBase):
    operation: Literal["SET_ACTIVE_SUBJECT"] = "SET_ACTIVE_SUBJECT"
    subject: ContextSubjectSignature


class SetActiveComparisonOperation(PatchOperationBase):
    operation: Literal["SET_ACTIVE_COMPARISON"] = "SET_ACTIVE_COMPARISON"
    comparison: ComparisonSpecification


class ClearActiveComparisonOperation(PatchOperationBase):
    operation: Literal["CLEAR_ACTIVE_COMPARISON"] = "CLEAR_ACTIVE_COMPARISON"


class SetActiveHeadReferenceOperation(PatchOperationBase):
    operation: Literal["SET_ACTIVE_HEAD_REFERENCE"] = "SET_ACTIVE_HEAD_REFERENCE"
    head_node_id: UUID


ContextPatchOperation = Annotated[
    SetFieldOperation
    | ReplaceFieldOperation
    | AppendFieldOperation
    | RemoveFieldOperation
    | ClearFieldOperation
    | ResetContextOperation
    | SetPendingClarificationOperation
    | ResolvePendingClarificationOperation
    | SetActiveSubjectOperation
    | SetActiveComparisonOperation
    | ClearActiveComparisonOperation
    | SetActiveHeadReferenceOperation,
    Field(discriminator="operation"),
]


class ContextPatchV2(StrictContextModel):
    patch_id: str = Field(min_length=16, max_length=64)
    base_context_epoch: int = Field(ge=0)
    base_context_version: int = Field(ge=0)
    base_node_id: UUID | None = None
    operations: list[ContextPatchOperation] = Field(default_factory=list, max_length=200)
    resolved_at: datetime
    resolution_version: str = CONTEXT_RESOLUTION_VERSION
    checksum: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")
    idempotency_fingerprint: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_patch(self) -> "ContextPatchV2":
        if self.resolution_version != CONTEXT_RESOLUTION_VERSION:
            raise ValueError("unsupported context resolution version")
        ids = [operation.operation_id for operation in self.operations]
        if len(ids) != len(set(ids)):
            raise ValueError("patch operation IDs must be unique")
        return self


class ContextFieldDecision(StrictContextModel):
    field_path: str = Field(min_length=1, max_length=128)
    action: FieldDecisionAction
    previous_value: JsonValue | None = None
    current_value: JsonValue | None = None
    resolved_value: JsonValue | None = None
    previous_origin: FieldOrigin | None = None
    current_origin: FieldOrigin | None = None
    resolved_origin: FieldOrigin | None = None
    source_node_id: UUID
    rule_id: str = Field(min_length=1, max_length=100)
    confidence: ConfidenceAssessment
    visible_to_user: bool = True
    inherited: bool = False
    overridden: bool = False
    removed: bool = False
    conflict: bool = False


class ContextConflict(StrictContextModel):
    conflict_id: str = Field(min_length=16, max_length=64)
    field_path: str = Field(min_length=1, max_length=128)
    previous_candidates: list[JsonValue] = Field(default_factory=list, max_length=20)
    current_candidates: list[JsonValue] = Field(default_factory=list, max_length=20)
    severity: ConflictSeverity
    reason: str = Field(min_length=1, max_length=500)
    candidate_options: list[str] = Field(default_factory=list, max_length=20)
    blocks_execution: bool
    requires_clarification: bool


class PublicContextSummary(StrictContextModel):
    active_metrics: list[str] = Field(default_factory=list)
    active_periods: list[str] = Field(default_factory=list)
    inherited_filters: list[str] = Field(default_factory=list)
    active_dimensions: list[str] = Field(default_factory=list)
    active_comparison: str | None = None
    replaced_fields: list[str] = Field(default_factory=list)
    removed_fields: list[str] = Field(default_factory=list)
    reset: bool = False
    clarification_required: bool = False


class ContextResolutionResult(StrictContextModel):
    resolved_intent: QueryIntentV2
    resolved_state: ConversationStateV2
    patch: ContextPatchV2
    readiness: ExecutionReadiness
    confidence: ConfidenceAssessment
    relationship: ContextRelationship
    field_decisions: list[ContextFieldDecision] = Field(default_factory=list)
    conflicts: list[ContextConflict] = Field(default_factory=list)
    clarification: ClarificationRequest | None = None
    warnings: list[str] = Field(default_factory=list, max_length=30)
    public_context_summary: PublicContextSummary
    resolution_version: str = CONTEXT_RESOLUTION_VERSION
    rule_ids: list[str] = Field(default_factory=list, max_length=100)
    state_checksum_before: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")
    state_checksum_after: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")
    expected_context_version: int = Field(ge=0)
    base_node_id: UUID | None = None


def stable_fingerprint(value: object) -> str:
    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json")
    else:
        payload = value
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=lambda item: str(item) if isinstance(item, (UUID, datetime, Decimal)) else repr(item),
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
