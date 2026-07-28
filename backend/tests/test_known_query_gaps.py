from __future__ import annotations

import pytest

from services.new_query_orchestrator import NewQueryOrchestrator


pytestmark = [
    pytest.mark.unit,
    pytest.mark.baseline,
    pytest.mark.no_database,
]

JUNE = ("2026-06-01", "2026-06-30")
JULY = ("2026-07-01", "2026-07-31")


def _periods_exposed_by_current_core_summary(question: str) -> list[tuple[str, str]]:
    return NewQueryOrchestrator()._month_ranges_from_text(question)


def test_exact_june_july_comparison_preserves_both_periods() -> None:
    question = "Compare o faturamento do Mês 06/2026 e 07/2026"
    assert _periods_exposed_by_current_core_summary(question) == [JUNE, JULY]


@pytest.mark.parametrize(
    "question",
    [
        "Compare junho e julho de 2026",
        "Compare 06/2026 com 07/2026",
        "Faturamento de junho versus julho de 2026",
        "Compare 07/2026 com 06/2026",
    ],
)
def test_comparison_variations_preserve_two_periods(question: str) -> None:
    periods = _periods_exposed_by_current_core_summary(question)
    assert len(periods) == 2
    assert set(periods) == {JUNE, JULY}


@pytest.mark.xfail(
    strict=True,
    reason=(
        "LUMINA-GAP-CONTEXT-001 / future PostgreSQL conversation-state prompt: "
        "single-turn period parsing does not inherit year, branch, metric, or two "
        "comparison periods across the required four-turn scenario."
    ),
)
@pytest.mark.known_gap
def test_required_four_turn_conversation_continuity() -> None:
    orchestrator = NewQueryOrchestrator()
    questions = [
        "Qual foi o faturamento de junho de 2026 da filial Centro?",
        "E em julho?",
        "Agora compare os dois meses.",
        "Separe por produto.",
    ]
    periods = [orchestrator._month_range_from_text(question) for question in questions]
    expected = [JUNE, JULY, (JUNE, JULY), (JUNE, JULY)]
    assert periods == expected
