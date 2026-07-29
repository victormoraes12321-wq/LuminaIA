from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from config import settings
from contracts.analytical_v2 import FieldOrigin, PipelineKind, build_intent_v2
from contracts.conversation_state_v2 import (
    ConversationRolloutMode,
    ConversationStateV2,
    ConversationTurnCompletion,
    ConversationTurnStart,
)
from database import AsyncSessionLocal
from services.conversation_state.content_protector import ConversationContentProtector
from services.conversation_state.service import ConversationStateService
from services.context_resolution import (
    ContextRelationship,
    ContextResolutionContext,
    ContextResolutionEngine,
)
from services.temporal import TemporalNormalizer, default_temporal_context
from testing.test_database import CONSULTA_A, TENANT_A


pytestmark = [pytest.mark.integration, pytest.mark.database, pytest.mark.security]


def _service() -> ConversationStateService:
    return ConversationStateService(
        AsyncSessionLocal,
        protector=ConversationContentProtector(
            key=settings.ENCRYPTION_KEY,
            key_version="test-v1",
        ),
        mode=ConversationRolloutMode.POSTGRES_READ_WRITE,
    )


async def _start(
    service: ConversationStateService,
    public_id: str,
    question: str,
    *,
    parent_node_id: uuid.UUID | None = None,
    version: int | None = None,
):
    return await service.start_turn(
        tenant_id=TENANT_A,
        user_id=CONSULTA_A,
        turn=ConversationTurnStart(
            public_session_id=public_id,
            client_message_id=uuid.uuid4(),
            parent_node_id=parent_node_id,
            expected_context_version=version,
            content=question,
        ),
    )


async def _complete(
    service: ConversationStateService,
    started,
    state: ConversationStateV2,
    *,
    reset: bool = False,
):
    return await service.complete_turn(
        tenant_id=TENANT_A,
        user_id=CONSULTA_A,
        completion=ConversationTurnCompletion(
            session_id=started.session_id,
            query_node_id=started.query_node_id,
            base_context_version=started.base_context_version,
            response_content="Resposta deterministica.",
            state=state,
            reset_context_epoch=reset,
            context_resolution_metadata={
                "resolution_version": "lumina.context-resolution/1.0",
                "relationship": "RESET" if reset else "FOLLOW_UP",
            },
        ),
    )


@pytest.mark.asyncio
async def test_required_four_turn_resolution_persists_real_snapshots_and_versions() -> None:
    public_id = f"lumina-{uuid.uuid4()}"
    questions = [
        "Qual foi o faturamento de junho de 2026 da filial Centro?",
        "E em julho?",
        "Agora compare os dois meses.",
        "Separe por produto.",
    ]
    reference = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
    temporal_context = default_temporal_context(reference_datetime=reference)
    temporal_normalizer = TemporalNormalizer()
    parent = None
    version = 0
    results = []

    for question in questions:
        service = _service()
        started = await _start(
            service,
            public_id,
            question,
            parent_node_id=parent,
            version=version,
        )
        row, state = await service.load_state(
            tenant_id=TENANT_A,
            user_id=CONSULTA_A,
            public_session_id=public_id,
            head_node_id=started.parent_node_id,
        )
        temporal_result = temporal_normalizer.normalize(question, temporal_context)
        intent = build_intent_v2(
            question,
            pipeline=PipelineKind.NEW,
            temporal_context=temporal_context,
            temporal_result=temporal_result,
        )
        result = ContextResolutionEngine().resolve(
            current_intent=intent,
            current_question=question,
            persisted_state=state,
            context=ContextResolutionContext(
                tenant_id=TENANT_A,
                user_id=CONSULTA_A,
                session_id=started.session_id,
                current_node_id=started.query_node_id,
                parent_node_id=started.parent_node_id,
                active_head_node_id=row.active_head_node_id,
                context_epoch=started.context_epoch,
                context_version=started.base_context_version,
                expected_context_version=version,
                branch_path=[],
                user_role="CONSULTA",
                locale="pt-BR",
                timezone="America/Sao_Paulo",
                reference_datetime=reference,
                rollout_mode=ConversationRolloutMode.POSTGRES_READ_WRITE,
                feature_flags={"context_resolution_v2": True},
                source="TEST",
            ),
        )
        assert result.readiness.value == "READY"
        completed = await _complete(service, started, result.resolved_state)
        parent = completed.response_node_id
        version = completed.context_version
        results.append(result)

    assert results[1].resolved_intent.metric_refs[0].origin == (
        FieldOrigin.INHERITED_CONVERSATION
    )
    assert results[1].resolved_intent.filters[0].origin == (
        FieldOrigin.INHERITED_CONVERSATION
    )
    assert results[2].relationship == ContextRelationship.COMPARISON_EXTENSION
    assert [
        window.start.isoformat()
        for window in results[2].resolved_intent.time_windows
    ] == ["2026-06-01", "2026-07-01"]
    assert results[2].resolved_intent.comparison is not None
    assert results[3].relationship == ContextRelationship.DRILL_DOWN
    assert [
        dimension.dimension_id
        for dimension in results[3].resolved_intent.dimension_refs
    ] == ["produto"]

    _, restored = await _service().load_state(
        tenant_id=TENANT_A,
        user_id=CONSULTA_A,
        public_session_id=public_id,
    )
    assert restored.context_version == 4
    assert restored.context_epoch == 0
    assert restored.active_metric_refs[0].metric_id == "faturamento_comercial"
    assert restored.active_filters[0].value == "centro"
    assert restored.active_comparison is not None
    assert [
        dimension.dimension_id for dimension in restored.active_dimension_refs
    ] == ["produto"]


@pytest.mark.asyncio
async def test_sibling_branch_loads_parent_snapshot_without_latest_branch_leakage() -> None:
    service = _service()
    public_id = f"lumina-{uuid.uuid4()}"
    first = await _start(service, public_id, "Faturamento de junho")
    first_done = await _complete(
        service,
        first,
        ConversationStateV2(active_subject="branch-a", context_markers=["A"]),
    )
    second = await _start(
        service,
        public_id,
        "E julho?",
        parent_node_id=first_done.response_node_id,
        version=1,
    )
    second_done = await _complete(
        service,
        second,
        ConversationStateV2(active_subject="branch-b", context_markers=["B"]),
    )
    assert second_done.context_version == 2

    sibling = await _start(
        service,
        public_id,
        "Agora por produto",
        parent_node_id=first_done.response_node_id,
        version=2,
    )
    _, branch_state = await service.load_state(
        tenant_id=TENANT_A,
        user_id=CONSULTA_A,
        public_session_id=public_id,
        head_node_id=sibling.parent_node_id,
    )
    assert branch_state.active_subject == "branch-a"
    assert branch_state.context_markers == ["A"]
    assert branch_state.context_version == 2


@pytest.mark.asyncio
async def test_context_reset_completion_advances_epoch_and_version_atomically() -> None:
    service = _service()
    public_id = f"lumina-{uuid.uuid4()}"
    first = await _start(service, public_id, "Faturamento de junho")
    first_done = await _complete(
        service,
        first,
        ConversationStateV2(active_subject="sales"),
    )
    reset_turn = await _start(
        service,
        public_id,
        "Comece uma nova analise",
        parent_node_id=first_done.response_node_id,
        version=1,
    )
    reset_done = await _complete(
        service,
        reset_turn,
        ConversationStateV2(),
        reset=True,
    )
    assert reset_done.context_epoch == 1
    assert reset_done.context_version == 2
    _, state = await service.load_state(
        tenant_id=TENANT_A,
        user_id=CONSULTA_A,
        public_session_id=public_id,
    )
    assert state.context_epoch == 1
    assert state.context_version == 2
    assert state.active_subject is None


@pytest.mark.asyncio
async def test_textual_backtrack_resolves_the_previous_response_head() -> None:
    service = _service()
    public_id = f"lumina-{uuid.uuid4()}"
    first = await _start(service, public_id, "Faturamento de junho")
    first_done = await _complete(
        service, first, ConversationStateV2(active_subject="first"),
    )
    second = await _start(
        service,
        public_id,
        "E julho?",
        parent_node_id=first_done.response_node_id,
        version=1,
    )
    await _complete(
        service, second, ConversationStateV2(active_subject="second"),
    )
    previous = await service.resolve_previous_head(
        tenant_id=TENANT_A,
        user_id=CONSULTA_A,
        public_session_id=public_id,
    )
    assert previous == first_done.response_node_id
