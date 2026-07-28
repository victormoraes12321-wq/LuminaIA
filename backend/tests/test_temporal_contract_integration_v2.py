from __future__ import annotations

import inspect
import time
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import pytest

from contracts.analytical_v2 import (
    ExecutionReadiness,
    IntentKind,
    PipelineKind,
    build_intent_v2,
    build_plan_v2,
)
from services.temporal import (
    TemporalContext,
    TemporalNormalizer,
)


pytestmark = [pytest.mark.unit, pytest.mark.no_database]
TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")
CONTEXT = TemporalContext(
    reference_datetime=datetime(
        2026,
        7,
        27,
        12,
        tzinfo=timezone(timedelta(hours=-3)),
    )
)


def test_june_july_contract_preserves_both_operands_in_order() -> None:
    intent = build_intent_v2(
        "Compare o faturamento do Mes 06/2026 e 07/2026",
        pipeline=PipelineKind.NEW,
        temporal_context=CONTEXT,
    )
    assert intent.intent_kind == IntentKind.COMPARISON
    assert [(window.start, window.end) for window in intent.time_windows] == [
        (date(2026, 6, 1), date(2026, 6, 30)),
        (date(2026, 7, 1), date(2026, 7, 31)),
    ]
    assert intent.comparison is not None
    assert len(intent.comparison.operands) == 2
    assert intent.contract.extensions["temporal"]["normalizer_version"] == (
        "lumina.temporal.pt-BR/1.0"
    )


def test_temporal_clarification_blocks_ready_intent() -> None:
    intent = build_intent_v2(
        "Compare o faturamento de 06/2026",
        pipeline=PipelineKind.NEW,
        temporal_context=CONTEXT,
    )
    assert intent.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED
    assert intent.clarification is not None


def test_plan_preserves_temporal_contract_without_reinterpretation() -> None:
    intent = build_intent_v2(
        "Faturamento de junho e julho de 2026",
        pipeline=PipelineKind.NEW,
        temporal_context=CONTEXT,
    )
    plan = build_plan_v2(
        intent,
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        user_role="CONSULTA",
        session_id="temporal-session",
        allowed_source_ids=["vw_vendas_lm"],
        pipeline=PipelineKind.NEW,
    )
    assert plan.time_windows == intent.time_windows
    assert plan.intent.contract.extensions["temporal"]["relation"] == "PERIOD_LIST"


def test_parser_source_has_no_openai_or_database_dependency() -> None:
    source = "\n".join(
        inspect.getsource(module)
        for module in (
            __import__("services.temporal.parser", fromlist=["x"]),
            __import__("services.temporal.resolver", fromlist=["x"]),
            __import__("services.temporal.normalizer", fromlist=["x"]),
        )
    ).lower()
    assert "openai" not in source
    assert "sqlalchemy" not in source
    assert "get_db" not in source
    assert "oracle" not in source


def test_common_parsing_has_generous_non_flaky_performance_bound() -> None:
    normalizer = TemporalNormalizer()
    started = time.perf_counter()
    for _ in range(500):
        result = normalizer.normalize(
            "Compare o faturamento do Mes 06/2026 e 07/2026",
            CONTEXT,
        )
        assert len(result.windows) == 2
    elapsed = time.perf_counter() - started
    # This is a regression guard, not a CI microbenchmark. Keep enough margin
    # for Windows antivirus and a loaded full-suite process.
    assert elapsed < 30


def test_comparison_of_rolling_and_previous_equivalent_period() -> None:
    result = TemporalNormalizer().normalize(
        "ultimos 30 dias contra os 30 dias anteriores",
        CONTEXT,
    )
    assert [(window.start, window.end) for window in result.windows] == [
        (date(2026, 6, 28), date(2026, 7, 27)),
        (date(2026, 5, 29), date(2026, 6, 27)),
    ]
