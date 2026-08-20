import pytest
from services.bi_engine import process_bi_intelligence


def test_bi_intelligence_calculations():
    # Dados de teste simulando vendas com um outlier claro (80.000)
    rows = [
        {"VALOR": 10000.0, "MARGEM": 30.0, "DATA_PEDIDO": "2026-01-01", "VENDEDOR": "Ana", "CLIENTE": "Nexus"},
        {"VALOR": 20000.0, "MARGEM": 40.0, "DATA_PEDIDO": "2026-01-02", "VENDEDOR": "Bruno", "CLIENTE": "Horizonte"},
        {"VALOR": 15000.0, "MARGEM": 35.0, "DATA_PEDIDO": "2026-01-03", "VENDEDOR": "Ana", "CLIENTE": "Nexus"},
        {"VALOR": 80000.0, "MARGEM": 38.0, "DATA_PEDIDO": "2026-01-04", "VENDEDOR": "Carla", "CLIENTE": "Gamma"},
    ]

    res = process_bi_intelligence(rows, "VW_TEST")

    # Verifica o JSON estruturado obrigatório
    assert "kpis" in res
    assert "metrics" in res
    assert "datasets" in res
    assert "time_series" in res
    assert "comparisons" in res
    assert "segments" in res
    assert "anomalies" in res

    # Verifica cálculos de KPIs
    kpis = res["kpis"]
    assert kpis["receita_total"] == 125000.0
    assert kpis["ticket_medio"] == 31250.0
    assert kpis["margem_bruta_media"] == 35.75
    assert kpis["lucro_bruto"] == round(125000.0 * 0.3575, 2)
    assert kpis["total_registros"] == 4

    # Verifica se o outlier de 80k foi pego como anomalia
    anoms = res["anomalies"]
    assert len(anoms) > 0
    assert any(a["valor"] == 80000.0 for a in anoms)
    assert any("Crescimento anormal" in a["tipo"] for a in anoms)

    # Verifica agregação categórica por vendedor
    datasets = res["datasets"]
    assert "vendedor" in datasets
    vendedores = [item["segmento"] for item in datasets["vendedor"]]
    assert "Ana" in vendedores
    assert "Carla" in vendedores
