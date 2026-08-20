from __future__ import annotations

from uuid import UUID
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from contracts.analytical_v2 import ExecutionReadiness, FieldOrigin, IntentKind
from contracts.conversation_state_v2 import (
    ConversationRolloutMode,
    ConversationStateV2,
    compute_state_checksum,
)
from services.context_resolution import (
    CONTEXT_RESOLUTION_VERSION,
    ContextResolutionError,
    ContextRelationship,
    ContextResolutionContext,
    ContextResolutionEngine,
    FIELD_POLICIES,
)
from services.context_resolution.feature_flags import ContextResolutionFeaturePolicy

from context_resolution_fixtures import REFERENCE, persisted, resolve_turn


pytestmark = [pytest.mark.unit, pytest.mark.no_database]


def test_required_four_turn_conversation_is_resolved_structurally() -> None:
    first = resolve_turn("Qual foi o faturamento de junho de 2026 da filial Centro?")
    assert first.relationship == ContextRelationship.NEW_TOPIC
    assert [item.metric_id for item in first.resolved_intent.metric_refs] == [
        "faturamento_comercial"
    ]
    assert [(item.start.isoformat(), item.end.isoformat()) for item in first.resolved_intent.time_windows] == [
        ("2026-06-01", "2026-06-30")
    ]
    assert first.resolved_intent.filters[0].field_id == "filial"
    assert first.resolved_intent.filters[0].value == "centro"

    second = resolve_turn("E em julho?", state=persisted(first), turn=2)
    assert second.relationship == ContextRelationship.REFINEMENT
    assert second.readiness == ExecutionReadiness.READY
    assert second.resolved_intent.metric_refs[0].origin == FieldOrigin.INHERITED_CONVERSATION
    assert second.resolved_intent.filters[0].origin == FieldOrigin.INHERITED_CONVERSATION
    assert [(item.start.isoformat(), item.end.isoformat()) for item in second.resolved_intent.time_windows] == [
        ("2026-07-01", "2026-07-31")
    ]
    assert [(item.start.isoformat(), item.end.isoformat()) for item in second.resolved_state.recent_time_windows] == [
        ("2026-06-01", "2026-06-30"),
        ("2026-07-01", "2026-07-31"),
    ]

    third = resolve_turn("Agora compare os dois meses.", state=persisted(second), turn=3)
    assert third.relationship == ContextRelationship.COMPARISON_EXTENSION
    assert third.resolved_intent.intent_kind == IntentKind.COMPARISON
    assert third.resolved_intent.comparison is not None
    assert len(third.resolved_intent.comparison.operands) == 2
    assert [
        operand.time_windows[0].start.isoformat()
        for operand in third.resolved_intent.comparison.operands
    ] == ["2026-06-01", "2026-07-01"]

    fourth = resolve_turn("Separe por produto.", state=persisted(third), turn=4)
    assert fourth.relationship == ContextRelationship.DRILL_DOWN
    assert fourth.resolved_intent.intent_kind == IntentKind.COMPARISON
    assert fourth.resolved_intent.comparison is not None
    assert [item.dimension_id for item in fourth.resolved_intent.dimension_refs] == ["produto"]
    assert len(fourth.resolved_intent.time_windows) == 2
    assert fourth.resolved_intent.filters[0].value == "centro"


@pytest.mark.parametrize(
    ("follow_up", "relationship", "expected_dimension"),
    [
        ("E em julho?", ContextRelationship.REFINEMENT, None),
        ("Separe por produto.", ContextRelationship.DRILL_DOWN, "produto"),
        ("Separe por vendedor.", ContextRelationship.DRILL_DOWN, "vendedor"),
        ("Na verdade, filial Sul.", ContextRelationship.CORRECTION, None),
        ("Sem a filial Centro.", ContextRelationship.REMOVAL, None),
        ("Resuma em um total geral.", ContextRelationship.ROLL_UP, None),
        ("Agora compare os dois meses.", ContextRelationship.COMPARISON_EXTENSION, None),
        ("Continue.", ContextRelationship.FOLLOW_UP, None),
    ],
)
def test_relationship_corpus(
    follow_up: str,
    relationship: ContextRelationship,
    expected_dimension: str | None,
) -> None:
    june = resolve_turn("Faturamento de junho de 2026 da filial Centro")
    if "dois meses" in follow_up:
        july = resolve_turn("E julho de 2026?", state=persisted(june), turn=2)
        state = persisted(july)
        turn = 3
    else:
        state = persisted(june)
        turn = 2
    result = resolve_turn(follow_up, state=state, turn=turn)
    assert result.relationship == relationship
    if expected_dimension:
        assert expected_dimension in {
            item.dimension_id for item in result.resolved_intent.dimension_refs
        }


@pytest.mark.parametrize(
    "question",
    [
        "E no mes seguinte?",
        "E no mes anterior?",
        "Mostre em tabela.",
        "Agora em grafico de barras.",
        "Detalhe por produto.",
        "Detalhe por cliente.",
        "Detalhe por vendedor.",
        "Mantenha a filial e troque o periodo para julho de 2026.",
        "E o ticket medio?",
        "E o total de desconto?",
        "Mostre as devolucoes.",
        "Mostre as vendas RB.",
    ],
)
def test_follow_ups_never_lose_explicit_current_fields(question: str) -> None:
    base = resolve_turn("Faturamento de junho de 2026 da filial 1")
    result = resolve_turn(question, state=persisted(base), turn=2)
    assert result.expected_context_version == 1
    assert result.patch.base_context_version == 1
    assert result.state_checksum_before == compute_state_checksum(persisted(base))
    assert result.resolution_version == CONTEXT_RESOLUTION_VERSION


def test_explicit_metric_replaces_inherited_metric() -> None:
    base = resolve_turn("Faturamento de junho de 2026")
    result = resolve_turn("E o ticket medio?", state=persisted(base), turn=2)
    assert [item.metric_id for item in result.resolved_intent.metric_refs] == ["ticket_medio"]
    metric_decision = next(
        item for item in result.field_decisions
        if item.field_path == "active_metric_refs"
    )
    assert metric_decision.overridden
    assert not metric_decision.inherited


def test_explicit_period_replaces_active_period_but_preserves_recent_history() -> None:
    base = resolve_turn("Faturamento de junho de 2026")
    result = resolve_turn("E em julho de 2026?", state=persisted(base), turn=2)
    assert [item.start.month for item in result.resolved_intent.time_windows] == [7]
    assert [item.start.month for item in result.resolved_state.recent_time_windows] == [6, 7]


def test_removal_does_not_resurrect_filter_in_same_turn() -> None:
    base = resolve_turn("Faturamento de junho de 2026 da filial Centro")
    result = resolve_turn("Sem a filial Centro.", state=persisted(base), turn=2)
    assert not result.resolved_intent.filters
    assert "active_filters" in result.public_context_summary.removed_fields


def test_new_domain_does_not_inherit_sales_metric() -> None:
    base = resolve_turn("Faturamento de junho de 2026")
    result = resolve_turn("Vamos falar de estoque.", state=persisted(base), turn=2)
    assert result.relationship == ContextRelationship.NEW_TOPIC
    assert not result.resolved_intent.metric_refs
    assert result.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED


@pytest.mark.parametrize(
    "question",
    [
        "Sem devolucoes.",
        "Nao considere RB.",
        "Remova a filial Centro.",
        "Exceto a filial Centro.",
        "Nao quero grafico.",
        "Sem agrupamento.",
        "Nao compare.",
    ],
)
def test_negation_is_never_interpreted_as_inclusion(question: str) -> None:
    base = resolve_turn(
        "Compare o faturamento de junho e julho de 2026 da filial Centro em grafico"
    )
    result = resolve_turn(question, state=persisted(base), turn=2)
    assert result.relationship == ContextRelationship.REMOVAL
    assert all(metric.metric_id not in {"devolucao", "saida_rb"} for metric in result.resolved_intent.metric_refs)
    if "filial" in question.lower():
        assert not result.resolved_intent.filters
    if "grafico" in question.lower():
        assert not result.resolved_intent.requested_visualizations
    if "agrupamento" in question.lower():
        assert not result.resolved_intent.dimension_refs
    if "compare" in question.lower():
        assert result.resolved_intent.comparison is None


def test_two_explicit_scalar_filter_values_require_clarification() -> None:
    result = resolve_turn(
        "Faturamento de junho de 2026 da filial Centro e filial Sul"
    )
    assert result.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED
    assert result.conflicts
    assert result.conflicts[0].blocks_execution
    assert result.clarification is not None
    assert set(result.clarification.candidate_options) == {"centro", "sul"}


def test_pending_clarification_only_clears_after_explicit_answer() -> None:
    conflict = resolve_turn(
        "Faturamento de junho de 2026 da filial Centro e filial Sul",
    )
    state = persisted(conflict)

    vague = resolve_turn("sim", state=state, turn=2)
    assert vague.relationship == ContextRelationship.CLARIFICATION_ANSWER
    assert vague.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED
    assert vague.clarification == conflict.clarification

    answered = resolve_turn("centro", state=state, turn=3)
    assert answered.relationship == ContextRelationship.CLARIFICATION_ANSWER
    assert answered.readiness == ExecutionReadiness.READY
    assert answered.clarification is None
    assert [(item.field_id, item.value) for item in answered.resolved_intent.filters] == [
        ("filial", "centro")
    ]


def test_total_reset_clears_context_without_mutating_input() -> None:
    base = resolve_turn("Faturamento de junho de 2026")
    state = persisted(base)
    checksum = compute_state_checksum(state)
    result = resolve_turn("Comece de novo com uma nova analise.", state=state, turn=2)
    assert result.relationship == ContextRelationship.RESET
    assert result.public_context_summary.reset
    assert result.public_context_summary.clarification_required is False
    assert result.clarification is None
    assert not result.resolved_state.active_metric_refs
    assert compute_state_checksum(state) == checksum


def test_same_input_is_idempotent_and_deterministic() -> None:
    base = persisted(resolve_turn("Faturamento de junho de 2026"))
    first = resolve_turn("E em julho?", state=base, turn=2)
    second = resolve_turn("E em julho?", state=base, turn=2)
    assert first.patch == second.patch
    assert first.resolved_intent == second.resolved_intent
    assert first.state_checksum_after == second.state_checksum_after


def test_stale_context_version_fails_closed() -> None:
    state = ConversationStateV2(context_version=3, updated_at=REFERENCE)
    context = ContextResolutionContext(
        tenant_id=UUID("10000000-0000-0000-0000-000000000001"),
        user_id=UUID("20000000-0000-0000-0000-000000000001"),
        session_id=UUID("30000000-0000-0000-0000-000000000001"),
        current_node_id=UUID("40000000-0000-0000-0000-000000000001"),
        context_epoch=0,
        context_version=2,
        expected_context_version=2,
        user_role="CONSULTA",
        timezone="America/Sao_Paulo",
        reference_datetime=REFERENCE,
        rollout_mode=ConversationRolloutMode.POSTGRES_READ_WRITE,
        source="TEST",
    )
    with pytest.raises(ContextResolutionError, match="Context version is stale"):
        ContextResolutionEngine().resolve(
            current_intent=resolve_turn("Faturamento de junho de 2026").resolved_intent,
            current_question="E julho?",
            persisted_state=state,
            context=context,
        )


def test_context_contract_rejects_dataset_and_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ContextResolutionContext.model_validate({
            "tenant_id": "10000000-0000-0000-0000-000000000001",
            "user_id": "20000000-0000-0000-0000-000000000001",
            "session_id": "30000000-0000-0000-0000-000000000001",
            "current_node_id": "40000000-0000-0000-0000-000000000001",
            "context_epoch": 0,
            "context_version": 0,
            "user_role": "CONSULTA",
            "timezone": "America/Sao_Paulo",
            "reference_datetime": REFERENCE.isoformat(),
            "rollout_mode": "POSTGRES_READ_WRITE",
            "source": "TEST",
            "dataset": [{"valor": 1}],
        })


def test_all_governed_field_policies_exist() -> None:
    assert set(FIELD_POLICIES) == {
        "metrics", "dimensions", "filters", "periods", "comparison",
        "visualizations", "subject", "ordering", "limit", "clarification",
    }


def test_inherited_field_limit_counts_items_inside_mixed_lists() -> None:
    first = resolve_turn(
        "Faturamento de junho de 2026 por vendedor da filial Centro",
    )

    with pytest.raises(ContextResolutionError, match="governed field limit"):
        resolve_turn(
            "e por produto",
            state=persisted(first),
            turn=2,
            maximum_inherited_fields=1,
        )


def test_context_resolution_rollout_defaults_are_inactive() -> None:
    policy = ContextResolutionFeaturePolicy.from_settings()
    assert policy.enabled is False
    assert policy.shadow_mode is False
    assert policy.frontend_enabled is False


def test_public_summary_contains_labels_not_internal_node_ids() -> None:
    parent_node_id = UUID("50000000-0000-0000-0000-000000000001")
    result = resolve_turn(
        "Faturamento de junho de 2026 da filial Centro",
        parent_node_id=parent_node_id,
    )
    summary = result.public_context_summary.model_dump(mode="json")
    assert summary["active_metrics"] == ["Faturamento comercial"]
    assert str(parent_node_id) not in str(summary)


def test_patch_contains_only_typed_discriminated_operations() -> None:
    result = resolve_turn("Faturamento de junho de 2026 da filial Centro")
    payload = result.patch.model_dump(mode="json")
    assert payload["operations"]
    assert all("operation" in operation for operation in payload["operations"])
    assert all("operation_id" in operation for operation in payload["operations"])
    assert all("value_fingerprint" in operation for operation in payload["operations"])


def test_golden_transition_catalog_is_complete_and_versioned() -> None:
    fixture = json.loads(
        (Path(__file__).parent / "golden" / "context_resolution_v2.json").read_text(
            encoding="utf-8"
        )
    )
    assert fixture["schema_version"] == CONTEXT_RESOLUTION_VERSION
    assert len(fixture["transitions"]) == 18
    assert len({item["name"] for item in fixture["transitions"]}) == 18


def test_long_conversation_keeps_recent_windows_bounded() -> None:
    state = ConversationStateV2(updated_at=REFERENCE)
    for turn in range(1, 41):
        month = (turn - 1) % 12 + 1
        question = (
            f"Faturamento de {month:02d}/2026"
            if turn == 1 else f"E em {month:02d}/2026?"
        )
        result = resolve_turn(question, state=state, turn=turn)
        state = persisted(result)
        assert len(state.recent_time_windows) <= 12
    assert state.context_version == 40


@pytest.mark.parametrize("repeat", range(30))
def test_repeated_follow_up_property_is_stable(repeat: int) -> None:
    base = persisted(resolve_turn("Faturamento de junho de 2026 da filial 1"))
    result = resolve_turn("Separe por produto.", state=base, turn=repeat + 2)
    assert result.readiness == ExecutionReadiness.READY
    assert result.resolved_intent.metric_refs
    assert result.resolved_intent.filters
    assert result.resolved_intent.dimension_refs
