from __future__ import annotations

from services.query_response_governance import query_response_governance
from models.user import UserRole
from types import SimpleNamespace
import uuid
import pytest


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _FakeDb:
    def __init__(self):
        self.results = [_Result(None), _Result(None)]

    async def execute(self, _statement):
        return self.results.pop(0)


def _payload(resumo: dict, rows: list[dict] | None = None) -> dict:
    return {
        "chart_data": {
            "resumo": resumo,
            "rows": rows or [],
        }
    }


def test_validation_accepts_balanced_totals_without_transfers() -> None:
    payload = _payload({
        "faturamento_total": 100,
        "faturamento_comercial": 100,
        "saida_rb": 20,
        "devolucao": 5,
        "venda_bonificada": 10,
        "outras_vendas": 0,
        "remessa_uso_consumo": 0,
        "outros_movimentos": 0,
        "transferencias": 50,
        "total_bruto": 135,
        "total_movimentos_view": 185,
        "filiais": [
            {"filial": "1", "faturamento_comercial": 60},
            {"filial": "2", "faturamento_comercial": 40},
        ],
    })

    result = query_response_governance.validate_math(payload)

    assert result["status"] == "PASSED"
    assert {item["code"] for item in result["checks"]} >= {
        "TOTAL_BRUTO_EXCLUI_TRANSFERENCIAS",
        "TOTAL_MOVIMENTOS_INCLUI_TRANSFERENCIAS",
        "SOMA_FILIAIS_IGUAL_TOTAL",
    }


def test_validation_rejects_transfer_inside_total_bruto() -> None:
    payload = _payload({
        "faturamento_comercial": 100,
        "saida_rb": 20,
        "devolucao": 0,
        "venda_bonificada": 0,
        "outras_vendas": 0,
        "remessa_uso_consumo": 0,
        "outros_movimentos": 0,
        "transferencias": 50,
        "total_bruto": 170,
        "total_movimentos_view": 170,
    })

    result = query_response_governance.validate_math(payload)

    assert result["status"] == "FAILED"
    assert any(
        item["code"] == "TOTAL_BRUTO_EXCLUI_TRANSFERENCIAS" and item["status"] == "FAIL"
        for item in result["checks"]
    )


def test_validation_checks_pivoted_ranking_and_duplicate_names() -> None:
    payload = _payload(
        {"primary_metric": "faturamento_comercial"},
        [
            {"vendedor": "ANA", "filial_1_faturamento_comercial": 40, "filial_2_faturamento_comercial": 60, "valor_total": 100},
            {"vendedor": "ANA", "filial_1_faturamento_comercial": 10, "filial_2_faturamento_comercial": 10, "valor_total": 25},
        ],
    )

    result = query_response_governance.validate_math(payload)

    assert result["status"] == "FAILED"
    failed = {item["code"] for item in result["checks"] if item["status"] == "FAIL"}
    assert failed == {"DIMENSAO_SEM_DUPLICIDADE", "TOTAL_RANKING_IGUAL_SOMA_FILIAIS"}


def test_context_inherits_filial_only_for_followup() -> None:
    from services.new_query_orchestrator import NewQueryOrchestrator

    orchestrator = NewQueryOrchestrator()
    history = [{"role": "user", "content": "Faturamento 07/2026 da filial 3"}]

    inherited = orchestrator._question_with_inherited_context("e agora por vendedor?", history)
    cleared = orchestrator._question_with_inherited_context("agora em todas as filiais", history)

    assert "filial 3" in inherited
    assert "filial 3" not in cleared


@pytest.mark.asyncio
async def test_non_admin_never_receives_technical_trace() -> None:
    payload = {
        "query_id": str(uuid.uuid4()),
        "pergunta_original": "Faturamento 07/2026",
        "chart_data": {"resumo": {}, "rows": []},
        "parametros_extraidos": {"periodo": "2026-07"},
        "telemetry": {"timings": {"total_pipeline": 10}},
        "debug_info": {"sql": {"raw_sql": "SELECT secret"}},
    }
    tenant = SimpleNamespace(id=uuid.uuid4(), sync_config={})
    user = SimpleNamespace(role=UserRole.CONSULTA)

    result = await query_response_governance.enrich(
        payload,
        db=_FakeDb(),
        tenant=tenant,
        current_user=user,
    )

    assert result["admin_diagnostics"] is None
    assert result["telemetry"] is None
    assert "debug_info" not in result
    assert result["data_status"]["query_source"] == "POSTGRESQL_ANALYTICAL_CLONE"
