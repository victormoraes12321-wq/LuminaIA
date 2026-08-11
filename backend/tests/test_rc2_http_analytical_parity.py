from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from services.ai_credential_manager import ai_credential_manager
from services.analytical_fact_policy import (
    AnalyticalFactState,
    aggregate_fact,
    ratio_fact,
    unavailable_fact,
)
from services.analytical_parity import (
    ExpectedResolutionPath,
    ParityStage,
    trace_from_pipeline_payload,
)
from services.new_query_orchestrator import new_query_orchestrator


CORPUS = json.loads(
    (Path(__file__).parent / "fixtures" / "rc1" / "numerical_truth.json").read_text(
        encoding="utf-8"
    )
)
HTTP_CASES = CORPUS[:30]
TENANTS = {
    "A": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    "B": "b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22",
}
USERS = {
    "A": "consulta.a@lumina.internal",
    "B": "consulta.b@lumina.internal",
}
METRIC_KEYS = {
    "revenue": "faturamento_total",
    "quantity": "quantidade_total",
    "average_ticket": "ticket_medio",
    "discount": "desconto_total",
}


class _FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2026, 8, 11, 12, 0, 0, tzinfo=timezone.utc)
        return value if tz is not None else value.replace(tzinfo=None)


def _facts(payload: dict[str, Any]) -> dict[str, Any]:
    chart_data = payload.get("chart_data") or {}
    return chart_data.get("resumo") or {}


async def _login(client: AsyncClient, tenant_key: str) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": USERS[tenant_key], "password": "SyntheticUser@2026"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_deployed_http_matches_internal_truth_for_30_cases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("services.new_query_orchestrator.datetime", _FixedDateTime)
    provider_calls = 0

    async def forbidden_provider(*args, **kwargs):
        nonlocal provider_calls
        provider_calls += 1
        raise AssertionError("deterministic numerical case reached the provider boundary")

    monkeypatch.setattr(ai_credential_manager, "resolve_client", forbidden_provider)
    original_run_pipeline = new_query_orchestrator.run_pipeline
    captured_http_payloads: list[dict[str, Any]] = []

    async def capture_http_payload(*args, **kwargs):
        result = await original_run_pipeline(*args, **kwargs)
        captured_http_payloads.append(copy.deepcopy(result))
        return result

    monkeypatch.setattr(new_query_orchestrator, "run_pipeline", capture_http_payload)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        tokens = {key: await _login(client, key) for key in TENANTS}

        for case in HTTP_CASES:
            tenant_key = case["expected_filters"]["tenant"]
            tenant_id = TENANTS[tenant_key]
            direct_payload = await original_run_pipeline(
                pergunta=case["question"],
                tenant_id=tenant_id,
                session_id=f"rc2-direct-{case['case_id'].lower()}",
                history=[],
            )
            before = len(captured_http_payloads)
            response = await client.post(
                "/api/v1/query/",
                headers={"Authorization": f"Bearer {tokens[tenant_key]}"},
                json={
                    "tenant_id": tenant_id,
                    "pergunta": case["question"],
                    "session_id": f"rc2-http-{case['case_id'].lower()}",
                    "use_new_pipeline": True,
                },
            )
            assert response.status_code == 200, case["case_id"]
            assert len(captured_http_payloads) == before + 1
            http_pipeline_payload = captured_http_payloads[-1]
            public_payload = response.json()

            resolution_path = ExpectedResolutionPath(case["expected_resolution_path"])
            direct_trace = trace_from_pipeline_payload(
                case_id=case["case_id"],
                question=case["question"],
                expected_resolution_path=resolution_path,
                payload=direct_payload,
            )
            http_trace = trace_from_pipeline_payload(
                case_id=case["case_id"],
                question=case["question"],
                expected_resolution_path=resolution_path,
                payload=http_pipeline_payload,
            )

            assert direct_trace.temporal_fingerprint == http_trace.temporal_fingerprint
            assert direct_trace.context_fingerprint == http_trace.context_fingerprint
            assert direct_trace.entity_fingerprint == http_trace.entity_fingerprint
            assert direct_trace.intent_fingerprint == http_trace.intent_fingerprint
            assert direct_trace.selected_capability == http_trace.selected_capability
            assert direct_trace.plan_fingerprint == http_trace.plan_fingerprint
            assert direct_trace.execution_fingerprint == http_trace.execution_fingerprint
            assert direct_trace.response_fingerprint == http_trace.response_fingerprint
            assert direct_trace.provider_invoked is False
            assert http_trace.provider_invoked is False
            assert {stage.stage for stage in http_trace.stages} >= {
                ParityStage.HTTP_ACCEPTED,
                ParityStage.AUTH_RESOLVED,
                ParityStage.TENANT_RESOLVED,
                ParityStage.INTENT_RESOLVED,
                ParityStage.PLAN_CREATED,
                ParityStage.EXECUTION_COMPLETED,
                ParityStage.VALIDATED,
                ParityStage.RESPONSE_RENDERED,
            }

            metric_key = METRIC_KEYS[case["expected_metric"]]
            expected = Decimal(case["expected_behavior"]["value"])
            direct_value = _facts(direct_payload).get(metric_key)
            http_value = _facts(public_payload).get(metric_key)
            assert direct_value is not None, case["case_id"]
            assert http_value is not None, case["case_id"]
            assert Decimal(str(direct_value)) == expected, case["case_id"]
            assert Decimal(str(http_value)) == expected, case["case_id"]

    assert provider_calls == 0


def test_zero_safety_matrix_never_fabricates_zero() -> None:
    positive = aggregate_fact(Decimal("155.00"), source_row_count=5)
    negative = aggregate_fact(Decimal("-30.00"), source_row_count=1)
    zero = aggregate_fact(Decimal("0"), source_row_count=1)
    null = aggregate_fact(None, source_row_count=1)
    no_rows = aggregate_fact(Decimal("0"), source_row_count=0)
    zero_count = aggregate_fact(Decimal("0"), source_row_count=0, empty_is_zero=True)
    not_applicable = ratio_fact(Decimal("100"), 0, source_row_count=1)
    timeout = unavailable_fact(AnalyticalFactState.ERROR)
    blocked = unavailable_fact(AnalyticalFactState.BLOCKED)
    unsupported = unavailable_fact(AnalyticalFactState.UNSUPPORTED)
    provider_unavailable = unavailable_fact(AnalyticalFactState.ERROR)
    validation_failure = unavailable_fact(AnalyticalFactState.BLOCKED)

    assert positive.value == Decimal("155.00") and positive.state == AnalyticalFactState.VALUE
    assert negative.value == Decimal("-30.00") and negative.state == AnalyticalFactState.VALUE
    assert zero.value == Decimal("0") and zero.state == AnalyticalFactState.ZERO
    assert zero_count.value == Decimal("0") and zero_count.state == AnalyticalFactState.ZERO
    assert null.value is None and null.state == AnalyticalFactState.NULL
    assert no_rows.value is None and no_rows.state == AnalyticalFactState.NO_ROWS
    assert not_applicable.value is None and not_applicable.state == AnalyticalFactState.NOT_APPLICABLE
    assert all(
        fact.value is None
        for fact in (timeout, blocked, unsupported, provider_unavailable, validation_failure)
    )


@pytest.mark.asyncio
async def test_provider_unavailable_is_fail_closed_without_numerical_fact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def unavailable_provider(*args, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(ai_credential_manager, "resolve_client", unavailable_provider)
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://testserver",
    ) as client:
        token = await _login(client, "A")
        response = await client.post(
            "/api/v1/query/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "tenant_id": TENANTS["A"],
                "pergunta": "Redija uma saudacao executiva sem consultar dados",
                "use_new_pipeline": True,
            },
        )
    assert response.status_code == 500
    assert "chart_data" not in response.text
    assert "0.0" not in response.text
