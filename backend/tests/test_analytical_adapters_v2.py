from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import pytest

from contracts.analytical_v2 import (
    AnalyticalResponseV2,
    ExecutionReadiness,
    IntentKind,
    PipelineKind,
    ValidationStatus,
    VisualizationKind,
    attach_v2_sidecar,
    build_intent_v2,
    legacy_payload_to_v2,
    v2_response_to_legacy,
)
from schemas.query import QueryResponse


pytestmark = [pytest.mark.unit, pytest.mark.no_database]
TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")
GOLDEN_PATH = Path(__file__).resolve().parent / "golden" / "analytical_v2_payloads.json"


def _legacy(
    question: str,
    *,
    status: str = "FULL_RENDERING",
    chart_type: str | None = "TABLE",
    visualizations: list[str] | None = None,
    with_data: bool = True,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "query_id": "33333333-3333-3333-3333-333333333333",
        "pergunta_original": question,
        "status": status,
        "view_name": "VW_VENDAS_LM" if with_data else None,
        "chart_type": chart_type,
        "chart_data": (
            {
                "columns": [{"key": "valor", "label": "Valor", "type": "currency"}],
                "rows": [{"valor": 300}],
                "total_rows": 1,
                "resumo": {},
            }
            if with_data
            else None
        ),
        "visualizations": (
            [{"chart_type": item, "chart_data": {}} for item in visualizations]
            if visualizations
            else None
        ),
        "validation_summary": (
            {"checks": [{"code": "TOTAL_VALIDADO", "status": "PASS", "required": True}]}
            if with_data
            else None
        ),
    }
    return payload


def _adapt(
    payload: dict[str, object],
    *,
    pipeline: PipelineKind = PipelineKind.NEW,
) -> AnalyticalResponseV2:
    return legacy_payload_to_v2(
        payload,
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        user_role="CONSULTA",
        session_id="session-1",
        pipeline=pipeline,
    )


def _projection(response: AnalyticalResponseV2) -> dict[str, object]:
    return {
        "schema": f"{response.contract.schema_name}/{response.contract.schema_version}",
        "pipeline": response.contract.pipeline.value,
        "intent_kind": response.intent.intent_kind.value,
        "readiness": response.intent.readiness.value,
        "metric_ids": [metric.metric_id for metric in response.intent.metric_refs],
        "periods": [
            [window.start.isoformat(), window.end.isoformat()]
            for window in response.intent.time_windows
        ],
        "comparison_operands": (
            len(response.intent.comparison.operands)
            if response.intent.comparison
            else 0
        ),
        "visualizations": [item.kind.value for item in response.visualizations],
        "datasets": len(response.datasets),
        "validation": response.validation.status.value,
        "errors": [error.code.value for error in response.errors],
        "clarification": response.clarification is not None,
        "tenant_id": str(response.scope_summary.tenant_id),
    }


@pytest.mark.parametrize(
    ("case_name", "payload", "pipeline"),
    [
        ("simple", _legacy("Faturamento de 06/2026 em tabela"), PipelineKind.NEW),
        ("ranking", _legacy("Ranking de vendedores de 07/2026 em tabela"), PipelineKind.NEW),
        (
            "comparison",
            _legacy("Compare o faturamento de 06/2026 e 07/2026 em tabela"),
            PipelineKind.NEW,
        ),
        (
            "multiple_visualizations",
            _legacy(
                "Faturamento de 06/2026 em tabela e grafico",
                visualizations=["TABLE", "BAR"],
            ),
            PipelineKind.NEW,
        ),
        (
            "clarification",
            _legacy("Compare o faturamento de 06/2026", status="AMBIGUOUS", with_data=False),
            PipelineKind.NEW,
        ),
        (
            "out_of_scope",
            _legacy("Quem criou o Excel?", status="OUT_OF_SCOPE", with_data=False),
            PipelineKind.NEW,
        ),
        (
            "error",
            _legacy("Faturamento de 06/2026", status="INTENT_ENGINE_ERROR", with_data=False),
            PipelineKind.NEW,
        ),
        (
            "legacy_adapter",
            _legacy("Ticket medio de 06/2026 em KPI", chart_type="KPI"),
            PipelineKind.LEGACY,
        ),
    ],
)
def test_v2_golden_semantic_payloads(
    case_name: str,
    payload: dict[str, object],
    pipeline: PipelineKind,
) -> None:
    expected = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert _projection(_adapt(payload, pipeline=pipeline)) == expected[case_name]


def test_v1_to_v2_preserves_comparison_and_visualizations() -> None:
    response = _adapt(
        _legacy(
            "Compare o faturamento de 06/2026 e 07/2026 em tabela e grafico",
            visualizations=["TABLE", "BAR"],
        )
    )
    assert response.intent.intent_kind == IntentKind.COMPARISON
    assert len(response.intent.time_windows) == 2
    assert response.intent.comparison is not None
    assert len(response.intent.comparison.operands) == 2
    assert [item.kind for item in response.visualizations] == [
        VisualizationKind.DATA_TABLE,
        VisualizationKind.BAR_CHART,
    ]


def test_v2_to_v1_preserves_legacy_fields_and_adds_sidecar() -> None:
    payload = _legacy("Faturamento de 06/2026 em tabela")
    legacy = v2_response_to_legacy(_adapt(payload), legacy_payload=payload)
    assert legacy["query_id"] == payload["query_id"]
    assert legacy["chart_type"] == "TABLE"
    assert legacy["status"] == "FULL_RENDERING"
    assert isinstance(legacy["analytical_contract"], AnalyticalResponseV2)
    assert legacy["analytical_contract"].contract.schema_version == "2.0"


def test_sidecar_attachment_is_idempotent() -> None:
    payload = _legacy("Faturamento de 06/2026 em tabela")
    first = attach_v2_sidecar(
        payload,
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        user_role="CONSULTA",
        session_id="session-1",
        pipeline=PipelineKind.NEW,
    )
    second = attach_v2_sidecar(
        first,
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        user_role="CONSULTA",
        session_id="session-1",
        pipeline=PipelineKind.NEW,
    )
    assert first["analytical_contract"] == second["analytical_contract"]


def test_legacy_ambiguous_maps_to_clarification_without_dataset() -> None:
    response = _adapt(
        _legacy("Faturamento", status="AMBIGUOUS", with_data=False)
    )
    assert response.intent.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED
    assert response.clarification is not None
    assert response.datasets == []


def test_out_of_scope_is_not_ambiguity_or_execution() -> None:
    response = _adapt(
        _legacy("Quem criou o Excel?", status="OUT_OF_SCOPE", with_data=False)
    )
    assert response.intent.intent_kind == IntentKind.OUT_OF_SCOPE
    assert response.intent.readiness == ExecutionReadiness.OUT_OF_SCOPE
    assert response.clarification is None
    assert response.datasets == []
    legacy = v2_response_to_legacy(response)
    assert legacy["status"] == "OUT_OF_SCOPE"


def test_intent_error_never_becomes_client_or_success() -> None:
    response = _adapt(
        _legacy("Faturamento", status="INTENT_ENGINE_ERROR", with_data=False)
    )
    serialized = response.model_dump_json()
    assert response.intent.readiness == ExecutionReadiness.ERROR
    assert response.errors
    assert '"Cliente"' not in serialized
    legacy = v2_response_to_legacy(response)
    assert legacy["status"] == "ERROR"
    assert legacy["chart_data"] is None


def test_adapter_records_not_executed_when_legacy_has_no_checks() -> None:
    payload = _legacy("Faturamento de 06/2026", with_data=False)
    response = _adapt(payload)
    assert response.validation.status == ValidationStatus.NOT_EXECUTED


def test_embedded_sidecar_rejects_unknown_version() -> None:
    payload = attach_v2_sidecar(
        _legacy("Faturamento de 06/2026 em tabela"),
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        user_role="CONSULTA",
        session_id="session-1",
        pipeline=PipelineKind.NEW,
    )
    payload["analytical_contract"] = payload["analytical_contract"].model_dump(mode="json")
    payload["analytical_contract"]["contract"]["schema_version"] = "9.9"
    with pytest.raises(ValueError, match="Unsupported analytical contract version"):
        _adapt(payload)


def test_comparison_without_second_period_requires_clarification() -> None:
    intent = build_intent_v2(
        "Compare o faturamento de 06/2026",
        pipeline=PipelineKind.NEW,
    )
    assert intent.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED
    assert intent.comparison is None
    assert intent.clarification is not None


def test_query_response_openapi_contract_keeps_sidecar_optional() -> None:
    schema = QueryResponse.model_json_schema()
    assert "analytical_contract" in schema["properties"]
    assert "analytical_contract" not in schema.get("required", [])
    legacy = QueryResponse.model_validate(
        {
            "query_id": "33333333-3333-3333-3333-333333333333",
            "pergunta_original": "Faturamento de 06/2026",
        }
    )
    assert legacy.analytical_contract is None
