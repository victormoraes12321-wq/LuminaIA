from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from contracts.analytical_v2 import PipelineKind, build_intent_v2
from contracts.conversation_state_v2 import ConversationRolloutMode, ConversationStateV2
from services.context_resolution import (
    ContextResolutionContext,
    ContextResolutionEngine,
    ContextResolutionResult,
)
from services.temporal import default_temporal_context


TENANT_ID = UUID("10000000-0000-0000-0000-000000000001")
USER_ID = UUID("20000000-0000-0000-0000-000000000001")
SESSION_ID = UUID("30000000-0000-0000-0000-000000000001")
REFERENCE = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)


def resolve_turn(
    question: str,
    *,
    state: ConversationStateV2 | None = None,
    turn: int = 1,
    parent_node_id: UUID | None = None,
    active_head_node_id: UUID | None = None,
    tenant_id: UUID = TENANT_ID,
    user_id: UUID = USER_ID,
    maximum_inherited_fields: int = 50,
) -> ContextResolutionResult:
    state = state or ConversationStateV2(updated_at=REFERENCE)
    temporal_context = default_temporal_context(reference_datetime=REFERENCE)
    intent = build_intent_v2(
        question,
        pipeline=PipelineKind.NEW,
        temporal_context=temporal_context,
    )
    node_id = UUID(f"40000000-0000-0000-0000-{turn:012d}")
    context = ContextResolutionContext(
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=SESSION_ID,
        current_node_id=node_id,
        parent_node_id=parent_node_id,
        active_head_node_id=active_head_node_id,
        context_epoch=state.context_epoch,
        context_version=state.context_version,
        expected_context_version=state.context_version,
        branch_path=[],
        user_role="CONSULTA",
        locale="pt-BR",
        timezone="America/Sao_Paulo",
        reference_datetime=REFERENCE,
        rollout_mode=ConversationRolloutMode.POSTGRES_READ_WRITE,
        feature_flags={"context_resolution_v2": True},
        maximum_context_depth=20,
        maximum_inherited_fields=maximum_inherited_fields,
        source="TEST",
    )
    return ContextResolutionEngine().resolve(
        current_intent=intent,
        current_question=question,
        persisted_state=state,
        context=context,
    )


def persisted(result: ContextResolutionResult) -> ConversationStateV2:
    return result.resolved_state.model_copy(
        update={"context_version": result.resolved_state.context_version + 1}
    )
