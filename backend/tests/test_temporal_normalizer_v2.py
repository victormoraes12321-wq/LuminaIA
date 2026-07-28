from __future__ import annotations

import json
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from contracts.analytical_v2 import (
    ConfidenceLevel,
    ExecutionReadiness,
    FieldOrigin,
    TemporalGranularity,
    TimeWindow,
)
from services.temporal import (
    CurrentPeriodMode,
    DefaultYearPolicy,
    PluralTemporalResultError,
    TemporalContext,
    TemporalInputError,
    TemporalNormalizer,
    TemporalRelation,
    TwoDigitYearPolicy,
    legacy_binds_from_result,
    default_temporal_context,
    singular_range_from_result,
)


pytestmark = [pytest.mark.unit, pytest.mark.no_database]
FIXTURE = Path(__file__).parent / "fixtures" / "temporal_cases_pt_br.json"
REFERENCE = datetime(2026, 7, 27, 12, tzinfo=timezone(timedelta(hours=-3)))


def context(**updates: object) -> TemporalContext:
    base = TemporalContext(reference_datetime=REFERENCE)
    return base.model_copy(update=updates)


@pytest.mark.parametrize("case", json.loads(FIXTURE.read_text(encoding="utf-8")), ids=lambda item: item["id"])
def test_versioned_pt_br_corpus(case: dict[str, object]) -> None:
    result = TemporalNormalizer().normalize(str(case["text"]), context())
    assert result.readiness.value == case["readiness"]
    assert result.relation.value == case["relation"]
    assert [
        [window.start.isoformat(), window.end.isoformat()]
        for window in result.windows
    ] == case["windows"]


def test_input_is_not_mutated_and_serialization_is_deterministic() -> None:
    query = "Compare junho e julho de 2026"
    original = deepcopy(query)
    result = TemporalNormalizer().normalize(query, context())
    assert query == original
    assert result.model_dump_json() == result.model_dump_json()


def test_normalization_is_idempotent_for_same_text_and_context() -> None:
    normalizer = TemporalNormalizer()
    first = normalizer.normalize("ultimos 30 dias", context())
    second = normalizer.normalize("ultimos 30 dias", context())
    first_payload = first.model_dump(mode="json", exclude={"duration_ms"})
    second_payload = second.model_dump(mode="json", exclude={"duration_ms"})
    assert first_payload == second_payload


@pytest.mark.parametrize(
    ("text", "start", "end"),
    [
        ("fevereiro de 2024", date(2024, 2, 1), date(2024, 2, 29)),
        ("abril de 2026", date(2026, 4, 1), date(2026, 4, 30)),
        ("julho de 2026", date(2026, 7, 1), date(2026, 7, 31)),
        ("fevereiro de 2025", date(2025, 2, 1), date(2025, 2, 28)),
    ],
)
def test_month_boundaries(text: str, start: date, end: date) -> None:
    window = TemporalNormalizer().normalize(text, context()).windows[0]
    assert (window.start, window.end) == (start, end)


def test_current_period_to_date_policy() -> None:
    result = TemporalNormalizer().normalize(
        "mes atual",
        context(current_period_mode=CurrentPeriodMode.TO_DATE),
    )
    assert (result.windows[0].start, result.windows[0].end) == (
        date(2026, 7, 1),
        date(2026, 7, 27),
    )


def test_missing_year_policies() -> None:
    current = TemporalNormalizer().normalize(
        "junho",
        context(default_year_policy=DefaultYearPolicy.CURRENT_YEAR),
    )
    recent = TemporalNormalizer().normalize(
        "dezembro",
        context(default_year_policy=DefaultYearPolicy.MOST_RECENT_OCCURRENCE),
    )
    required = TemporalNormalizer().normalize(
        "junho",
        context(default_year_policy=DefaultYearPolicy.REQUIRE_CLARIFICATION),
    )
    assert current.windows[0].start == date(2026, 6, 1)
    assert recent.windows[0].start == date(2025, 12, 1)
    assert required.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED


def test_two_digit_year_policies() -> None:
    rejected = TemporalNormalizer().normalize("jun/26", context())
    accepted = TemporalNormalizer().normalize(
        "jun/26",
        context(two_digit_year_policy=TwoDigitYearPolicy.CURRENT_CENTURY),
    )
    pivot = TemporalNormalizer().normalize(
        "jun/75",
        context(two_digit_year_policy=TwoDigitYearPolicy.PIVOT_YEAR),
    )
    assert rejected.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED
    assert accepted.windows[0].start == date(2026, 6, 1)
    assert accepted.confidence.level == ConfidenceLevel.MEDIUM
    assert pivot.windows[0].start == date(1975, 6, 1)


def test_range_list_and_comparison_are_structurally_distinct() -> None:
    normalizer = TemporalNormalizer()
    range_result = normalizer.normalize("entre junho e agosto de 2026", context())
    list_result = normalizer.normalize("junho, julho e agosto de 2026", context())
    comparison = normalizer.normalize("junho versus agosto de 2026", context())
    assert range_result.relation == TemporalRelation.RANGE
    assert len(range_result.windows) == 1
    assert list_result.relation == TemporalRelation.PERIOD_LIST
    assert len(list_result.windows) == 3
    assert comparison.relation == TemporalRelation.COMPARISON
    assert len(comparison.comparison_groups[0].operand_item_ids) == 2


def test_order_and_stable_deduplication() -> None:
    result = TemporalNormalizer().normalize(
        "julho, junho, julho e maio de 2026",
        context(),
    )
    assert [window.start.month for window in result.windows] == [7, 6, 5]
    distinct_years = TemporalNormalizer().normalize(
        "junho de 2025 e junho de 2026",
        context(),
    )
    assert [window.start.year for window in distinct_years.windows] == [2025, 2026]


def test_singular_legacy_adapter_refuses_plural_and_uses_exclusive_end() -> None:
    plural = TemporalNormalizer().normalize("junho e julho de 2026", context())
    with pytest.raises(PluralTemporalResultError):
        singular_range_from_result(plural)
    single = TemporalNormalizer().normalize("junho de 2026", context())
    binds = legacy_binds_from_result(single)
    assert binds is not None
    assert binds.data_inicio == "2026-06-01"
    assert binds.data_fim == "2026-06-30"
    assert binds.end_exclusive == "2026-07-01"


def test_same_period_requires_structured_base() -> None:
    missing = TemporalNormalizer().normalize(
        "mesmo periodo do ano passado",
        context(),
    )
    assert missing.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED
    confidence = TemporalNormalizer().normalize("junho de 2026", context()).confidence
    base = TimeWindow(
        window_id="base",
        label="Junho 2026",
        start=date(2026, 6, 1),
        end=date(2026, 6, 30),
        granularity=TemporalGranularity.MONTH,
        timezone="America/Sao_Paulo",
        origin=FieldOrigin.INHERITED_CONVERSATION,
        confidence=confidence,
    )
    resolved = TemporalNormalizer().normalize(
        "mesmo periodo do ano passado",
        context(base_time_windows=(base,)),
    )
    assert resolved.relation == TemporalRelation.COMPARISON
    assert [(window.start.year, window.end.year) for window in resolved.windows] == [
        (2026, 2026),
        (2025, 2025),
    ]


def test_input_limits_are_fail_closed() -> None:
    with pytest.raises(TemporalInputError):
        TemporalNormalizer().normalize("x" * 4001, context())


def test_clock_is_injectable_without_reading_the_system_clock() -> None:
    class FixedClock:
        def now(self) -> datetime:
            return REFERENCE

    injected = default_temporal_context(clock=FixedClock())
    assert injected.reference_datetime == REFERENCE


def test_future_rolling_period_respects_authorization() -> None:
    blocked = TemporalNormalizer().normalize("proximos 7 dias", context())
    allowed = TemporalNormalizer().normalize(
        "proximos 7 dias",
        context(allow_future_periods=True),
    )
    assert blocked.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED
    assert (allowed.windows[0].start, allowed.windows[0].end) == (
        date(2026, 7, 27),
        date(2026, 8, 2),
    )


def test_range_between_quarters_with_shared_year() -> None:
    result = TemporalNormalizer().normalize(
        "do primeiro ao segundo trimestre de 2026",
        context(),
    )
    assert result.relation == TemporalRelation.RANGE
    assert (result.windows[0].start, result.windows[0].end) == (
        date(2026, 1, 1),
        date(2026, 6, 30),
    )


def test_fortnight_without_month_uses_explicit_default_year_policy() -> None:
    result = TemporalNormalizer().normalize("1a quinzena", context())
    assert (result.windows[0].start, result.windows[0].end) == (
        date(2026, 7, 1),
        date(2026, 7, 15),
    )
    assert result.confidence.level == ConfidenceLevel.MEDIUM


@pytest.mark.parametrize("text", ["no dia 5", "ultimo periodo", "semana sideral"])
def test_material_ambiguities_require_clarification(text: str) -> None:
    result = TemporalNormalizer().normalize(text, context())
    assert result.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED
    assert result.unresolved_expressions
