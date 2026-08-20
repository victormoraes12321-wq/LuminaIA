from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import text

from config import settings
from contracts.analytical_v2 import ExecutionReadiness, PipelineKind, build_intent_v2
from database import engine
from services.ai_credential_manager import ai_credential_manager
from services.analytical_fact_policy import AnalyticalFactState, aggregate_fact
from services.new_query_orchestrator import new_query_orchestrator
from services.sales_value_breakdown import sales_value_breakdown
from services.temporal import build_temporal_context


TENANT_A = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"


@pytest.fixture(autouse=True)
def _authorize_governed_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "V2_GLOBAL_EMERGENCY_DISABLE", False)
    monkeypatch.setattr(settings, "ENABLE_DETERMINISTIC_PIPELINE", True)


def _resumo(payload: dict[str, Any]) -> dict[str, Any]:
    return (payload.get("chart_data") or {}).get("resumo") or {}


async def _run(question: str) -> dict[str, Any]:
    return await new_query_orchestrator.run_pipeline(
        pergunta=question,
        tenant_id=TENANT_A,
        session_id="rc2-integrity-remediation",
        history=[],
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("question", "raw_rows"),
    [
        ("Qual foi a quantidade vendida em janeiro de 1990?", 0),
        ("Qual foi a quantidade vendida em 12 de junho de 2026?", 1),
    ],
)
async def test_rc2_bug_0001_rows_without_eligible_commercial_fact_are_no_rows(
    question: str,
    raw_rows: int,
) -> None:
    payload = await _run(question)
    resumo = _resumo(payload)

    assert payload["status"] == AnalyticalFactState.NO_ROWS.value
    assert resumo["fact_state"] == AnalyticalFactState.NO_ROWS.value
    assert resumo["quantidade_total"] is None
    assert resumo["source_row_count"] == 0
    assert raw_rows >= resumo["source_row_count"]
    assert (payload["chart_data"].get("data") or []) == []
    assert " 0" not in payload["resposta_direta"]


@pytest.mark.asyncio
async def test_rc2_bug_0001_legitimate_commercial_zero_remains_zero() -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                INSERT INTO test_vendas_lm (
                    tenant_id, dtemissao_, filial_, pedido_, nota_, serie_, codcliente_,
                    rca_, cfop_, tp_, tpdescricao_, ptotal_, qtde_, p_unit_, codprod_,
                    descricao_, desconto_total
                ) VALUES (
                    :tenant_id, '2026-08-01', '1', 'ZERO-1', 'ZERO-1', '1', '10',
                    '1', '5102', 2, 'VENDA', 0, 0, 0, '100', 'Produto Compartilhado', 0
                )
                """
            ),
            {"tenant_id": TENANT_A},
        )

    payload = await _run("Qual foi a quantidade vendida em 1 de agosto de 2026?")
    resumo = _resumo(payload)
    assert payload["status"] == "FULL_RENDERING"
    assert resumo["fact_state"] == AnalyticalFactState.ZERO.value
    assert resumo["quantidade_total"] == 0.0
    assert resumo["source_row_count"] == 1


def test_rc2_bug_0001_null_commercial_aggregate_remains_null() -> None:
    fact = aggregate_fact(None, source_row_count=1)
    assert fact.state == AnalyticalFactState.NULL
    assert fact.value is None


@pytest.mark.asyncio
async def test_rc2_bug_0001_irrelevant_rows_do_not_change_commercial_fact_support() -> None:
    binds = {
        "tenant_id": TENANT_A,
        "start_date": datetime(2026, 6, 1).date(),
        "end_date": datetime(2026, 6, 30).date(),
        "end_exclusive": datetime(2026, 7, 1).date(),
    }
    async with engine.begin() as connection:
        before = await sales_value_breakdown.fetch_period_totals(connection, binds)
        await connection.execute(
            text(
                """
                INSERT INTO test_vendas_lm (
                    tenant_id, dtemissao_, filial_, pedido_, nota_, serie_, codcliente_,
                    rca_, cfop_, tp_, tpdescricao_, ptotal_, qtde_, p_unit_, codprod_,
                    descricao_, desconto_total
                ) VALUES (
                    :tenant_id, '2026-06-25', '1', 'IRRELEVANT-1', 'IRRELEVANT-1',
                    '1', '10', '1', '5102', 9, 'SAIDA RB', 999, 999, 1, '100',
                    'Produto Compartilhado', 0
                )
                """
            ),
            {"tenant_id": TENANT_A},
        )
        after = await sales_value_breakdown.fetch_period_totals(connection, binds)

    assert after["source_row_count"] == before["source_row_count"] + 1
    assert after["commercial_row_count"] == before["commercial_row_count"]
    assert after["quantidade_total"] == before["quantidade_total"]


def test_rc2_bug_0001_count_metric_empty_policy_is_explicit() -> None:
    count_fact = aggregate_fact(Decimal("0"), source_row_count=0, empty_is_zero=True)
    additive_fact = aggregate_fact(Decimal("0"), source_row_count=0)
    assert count_fact.state == AnalyticalFactState.ZERO
    assert additive_fact.state == AnalyticalFactState.NO_ROWS


@pytest.mark.parametrize(
    ("noun", "expected_metric"),
    [
        ("unidades", "unidades_vendidas"),
        ("pedidos", "quantidade_pedidos"),
        ("clientes", "clientes_distintos"),
    ],
)
@pytest.mark.parametrize("quantifier", ["quantidade de", "numero de", "quantos", "total de"])
def test_rc2_bug_0002_noun_specific_metric_matrix(
    noun: str,
    expected_metric: str,
    quantifier: str,
) -> None:
    intent = build_intent_v2(
        f"{quantifier} {noun} em junho de 2026",
        pipeline=PipelineKind.NEW,
    )
    assert intent.readiness == ExecutionReadiness.READY
    assert [metric.metric_id for metric in intent.metric_refs] == [expected_metric]
    if expected_metric == "clientes_distintos":
        assert [dimension.dimension_id for dimension in intent.dimension_refs] == []


def test_rc2_bug_0002_bare_quantidade_requires_clarification() -> None:
    intent = build_intent_v2("quantidade em 2026", pipeline=PipelineKind.NEW)
    assert intent.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED
    assert intent.metric_refs == []


@pytest.mark.asyncio
async def test_rc2_bug_0002_bare_quantidade_does_not_reach_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_calls = 0

    async def forbidden_provider(*args: Any, **kwargs: Any) -> Any:
        nonlocal provider_calls
        provider_calls += 1
        raise AssertionError("ambiguous quantity reached provider")

    monkeypatch.setattr(ai_credential_manager, "resolve_client", forbidden_provider)
    payload = await _run("quantidade em 2026")
    assert payload["status"] in {"AMBIGUOUS", "MISSING_INFORMATION"}
    assert payload["missing_information"]
    assert provider_calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("question", "metric_key", "expected"),
    [
        ("Quantidade de pedidos em junho de 2026", "pedidos_comerciais", 2),
        ("Quantidade de clientes em junho de 2026", "clientes_distintos", 2),
        ("Quantidade de unidades vendidas em junho de 2026", "quantidade_total", 4.0),
    ],
)
async def test_rc2_bug_0002_governed_metrics_execute_without_provider(
    monkeypatch: pytest.MonkeyPatch,
    question: str,
    metric_key: str,
    expected: int | float,
) -> None:
    provider_calls = 0

    async def forbidden_provider(*args: Any, **kwargs: Any) -> Any:
        nonlocal provider_calls
        provider_calls += 1
        raise AssertionError("governed metric reached provider")

    monkeypatch.setattr(ai_credential_manager, "resolve_client", forbidden_provider)
    payload = await _run(question)
    resumo = _resumo(payload)
    assert payload["status"] == "FULL_RENDERING"
    assert resumo[metric_key] == expected
    assert resumo["fact_state"] in {AnalyticalFactState.VALUE.value, AnalyticalFactState.ZERO.value}
    assert provider_calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("question", "minimum_rows"),
    [
        ("ranking de vendedores no historico completo", 2),
        ("produtos mais vendidos no historico completo", 2),
        ("faturamento historico completo, ver documentos", 5),
    ],
)
async def test_rc2_bug_0003_all_history_reaches_every_child_reader(
    question: str,
    minimum_rows: int,
) -> None:
    payload = await _run(question)
    resumo = _resumo(payload)
    assert payload["status"] == "FULL_RENDERING"
    assert len(payload["sample_rows"]) >= minimum_rows
    assert resumo["periodo"] == "todo o historico disponivel"
    assert resumo["temporal_scope_kind"] == "ALL_AVAILABLE_HISTORY"
    assert len(resumo["temporal_scope_fingerprint"]) == 64


@pytest.mark.asyncio
async def test_rc2_bug_0003_history_is_clock_independent(monkeypatch: pytest.MonkeyPatch) -> None:
    class JuneClock(datetime):
        @classmethod
        def now(cls, tz=None):
            value = cls(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
            return value if tz is not None else value.replace(tzinfo=None)

    class AugustClock(datetime):
        @classmethod
        def now(cls, tz=None):
            value = cls(2026, 8, 15, 12, 0, tzinfo=timezone.utc)
            return value if tz is not None else value.replace(tzinfo=None)

    monkeypatch.setattr("services.new_query_orchestrator.datetime", JuneClock)
    june = await _run("ranking de vendedores no historico completo")
    monkeypatch.setattr("services.new_query_orchestrator.datetime", AugustClock)
    august = await _run("ranking de vendedores no historico completo")
    assert june["sample_rows"] == august["sample_rows"]
    assert _resumo(june)["temporal_scope_fingerprint"] == _resumo(august)["temporal_scope_fingerprint"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("question", "expected_kind"),
    [
        (
            "ranking de vendedores, produtos mais vendidos e ver documentos no historico completo",
            "ALL_AVAILABLE_HISTORY",
        ),
        (
            "ranking de vendedores, produtos mais vendidos e ver documentos em julho de 2026",
            "BOUNDED",
        ),
        (
            "ranking de vendedores, produtos mais vendidos e ver documentos neste mes",
            "BOUNDED",
        ),
    ],
)
async def test_rc2_bug_0003_child_readers_share_the_root_temporal_fingerprint(
    monkeypatch: pytest.MonkeyPatch,
    question: str,
    expected_kind: str,
) -> None:
    if "neste mes" in question:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    INSERT INTO test_vendas_lm (
                        tenant_id, dtemissao_, filial_, pedido_, nota_, serie_, codcliente_,
                        rca_, cfop_, tp_, tpdescricao_, ptotal_, qtde_, p_unit_, codprod_,
                        descricao_, desconto_total
                    ) VALUES (
                        :tenant_id, '2026-08-05', '1', 'CURRENT-1', 'CURRENT-1',
                        '1', '10', '1', '5102', 2, 'VENDA', 10, 1, 10, '100',
                        'Produto Compartilhado', 0
                    )
                    """
                ),
                {"tenant_id": TENANT_A},
            )

    captured: dict[str, str] = {}
    method_names = (
        "fetch_period_totals",
        "fetch_period_totals_by_filial",
        "fetch_document_details",
        "fetch_vendor_ranking",
        "fetch_product_ranking",
    )
    for method_name in method_names:
        original = getattr(sales_value_breakdown, method_name)

        async def capture(*args: Any, _name: str = method_name, _original: Any = original, **kwargs: Any) -> Any:
            scope = kwargs["temporal_scope"]
            captured[_name] = scope.compute_fingerprint()
            return await _original(*args, **kwargs)

        monkeypatch.setattr(sales_value_breakdown, method_name, capture)

    payload = await _run(question)
    resumo = _resumo(payload)
    assert payload["status"] == "FULL_RENDERING"
    assert resumo["temporal_scope_kind"] == expected_kind
    assert set(captured) == set(method_names)
    assert set(captured.values()) == {resumo["temporal_scope_fingerprint"]}


def test_rc2_bug_0003_explicit_comparison_periods_are_preserved() -> None:
    context = build_temporal_context(
        reference_datetime=datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc),
    )
    intent = build_intent_v2(
        "Compare o faturamento de junho e julho de 2026",
        pipeline=PipelineKind.NEW,
        temporal_context=context,
    )
    assert intent.readiness == ExecutionReadiness.READY
    assert len(intent.time_windows) == 2
    assert intent.time_windows[0].window_id != intent.time_windows[1].window_id
