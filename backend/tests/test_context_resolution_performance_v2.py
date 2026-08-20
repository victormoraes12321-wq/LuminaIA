from __future__ import annotations

import time
from decimal import Decimal

import pytest

from contracts.analytical_v2 import (
    ConfidenceAssessment,
    ConfidenceLevel,
    FieldOrigin,
    FilterOperator,
    FilterSpecification,
)
from services.context_resolution.feature_flags import ContextResolutionFeaturePolicy

from context_resolution_fixtures import persisted, resolve_turn


pytestmark = [pytest.mark.unit, pytest.mark.no_database]


def _confidence() -> ConfidenceAssessment:
    return ConfidenceAssessment(
        level=ConfidenceLevel.HIGH,
        score=Decimal("1"),
        reasons=["Fixture deterministica."],
        requires_confirmation=False,
    )


@pytest.mark.parametrize("turn_count", [10, 25])
def test_bounded_conversation_resolution_remains_fast(turn_count: int) -> None:
    state = persisted(resolve_turn("Faturamento de janeiro de 2026"))
    started = time.perf_counter()
    for turn in range(2, turn_count + 2):
        month = (turn - 1) % 12 + 1
        result = resolve_turn(f"E em {month:02d}/2026?", state=state, turn=turn)
        state = persisted(result)
    elapsed = time.perf_counter() - started
    assert elapsed < 2.0
    assert len(state.recent_time_windows) <= 12


def test_twenty_compatible_filters_are_preserved_without_graph_scan() -> None:
    base = resolve_turn("Faturamento de junho de 2026")
    filters = [
        FilterSpecification(
            filter_id=f"filter_{index}",
            field_id=f"dimension_{index}",
            operator=FilterOperator.EQ,
            value=f"value_{index}",
            values=[],
            origin=FieldOrigin.EXPLICIT_USER,
            confidence=_confidence(),
            is_explicit=True,
        )
        for index in range(20)
    ]
    state = persisted(base).model_copy(update={"active_filters": filters})
    started = time.perf_counter()
    result = resolve_turn("Continue.", state=state, turn=2)
    assert time.perf_counter() - started < 0.5
    assert len(result.resolved_intent.filters) == 20


def test_shadow_policy_never_authors_state() -> None:
    policy = ContextResolutionFeaturePolicy(
        enabled=False,
        shadow_mode=True,
        frontend_enabled=False,
        maximum_context_depth=20,
        maximum_inherited_fields=50,
    )
    assert policy.should_resolve
    assert not policy.can_author_state
