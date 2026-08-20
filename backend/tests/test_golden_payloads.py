from __future__ import annotations

import json
from pathlib import Path

import pytest

from testing.golden_payload import normalize_golden_payload


pytestmark = [
    pytest.mark.unit,
    pytest.mark.baseline,
    pytest.mark.no_database,
]

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
TENANT_A = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"


@pytest.mark.parametrize(
    ("filename", "payload"),
    [
        (
            "legacy_query_response.json",
            {
                "query_id": "random-query-id",
                "trace_id": "random-trace-id",
                "duration_ms": 12.34567,
                "contract": "legacy",
                "tenant_id": TENANT_A,
                "metric": "faturamento_comercial",
                "value": 300.0,
                "chart_type": "KPI",
                "filters": {
                    "start_date": "2026-06-01",
                    "end_date": "2026-06-30",
                },
                "provenance": {
                    "source": "PostgreSQL test clone",
                    "view": "vw_vendas_lm",
                },
            },
        ),
        (
            "new_query_response.json",
            {
                "request_id": "random-request-id",
                "execution_time_ms": 88.0,
                "contract": "new_pipeline",
                "status": "FULL_RENDERING",
                "tenant_id": TENANT_A,
                "metric": "faturamento_comercial",
                "dataset": [{"periodo": "2026-06", "faturamento_comercial": 300.0}],
                "visualization": "KPI_CARD",
                "filters": {
                    "start_date": "2026-06-01",
                    "end_date": "2026-06-30",
                },
                "provenance": {
                    "source": "PostgreSQL test clone",
                    "view": "vw_vendas_lm",
                },
            },
        ),
    ],
)
def test_normalized_pipeline_payload_matches_golden(
    filename: str,
    payload: dict,
) -> None:
    expected = json.loads((GOLDEN_DIR / filename).read_text(encoding="utf-8"))
    assert normalize_golden_payload(payload) == expected


def test_normalizer_preserves_semantic_fields() -> None:
    payload = {
        "trace_id": "volatile",
        "tenant_id": TENANT_A,
        "metric": "ticket_medio",
        "filters": {"filial": "1"},
        "errors": [{"code": "NO_DATA"}],
        "value": 150.1234567,
    }
    normalized = normalize_golden_payload(payload)
    assert "trace_id" not in normalized
    assert normalized["tenant_id"] == TENANT_A
    assert normalized["metric"] == "ticket_medio"
    assert normalized["filters"] == {"filial": "1"}
    assert normalized["errors"] == [{"code": "NO_DATA"}]
    assert normalized["value"] == 150.123457
