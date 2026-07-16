"""
LuminaAI — Mock Service: Gerador de dados de demonstração (v5.2)

Encapsula todas as funções auxiliares de simulação de dados analíticos para demonstração.
Garante a unificação de schemas para alimentar o transformador e a engine de BI de forma consistente.
"""
from __future__ import annotations

import logging
import random
from datetime import date, timedelta
from typing import Any

from models.view_catalog import ViewCatalog, ChartType

logger = logging.getLogger("luminaai.services.mock_service")


def _labels_mensais(n_meses: int = 12) -> list[str]:
    """Gera lista de labels mensais retroativos (ex: ['Jul/2024', ..., 'Jun/2025'])."""
    hoje = date.today()
    labels: list[str] = []
    for i in range(n_meses - 1, -1, -1):
        mes_offset = hoje.month - 1 - i
        ano = hoje.year + mes_offset // 12
        mes = mes_offset % 12 + 1
        labels.append(date(ano, mes, 1).strftime("%b/%Y"))
    return labels


def gerar_raw_rows_mock(nome_view: str, parametros: dict[str, str]) -> list[dict[str, Any]]:
    """
    Gera registros brutos simulados equivalentes aos do Oracle/PostgreSQL
    para alimentar o pipeline de transformação de dados e a engine de BI.
    """
    nome_upper = str(nome_view).upper() if nome_view else ""
    rows: list[dict[str, Any]] = []
    random.seed(42)  # Seed para determinismo de simulação

    # ── 1. VW_VENDAS_MENSAIS / VW_FATURAMENTO ──
    if "MENSAIS" in nome_upper or "FATURAMENTO" in nome_upper:
        labels = _labels_mensais(12)
        for lbl in labels:
            fat = round(random.uniform(85_000.0, 620_000.0), 2)
            meta = round(fat * random.uniform(0.85, 1.15), 2)
            rows.append({
                "MES": lbl,
                "FATURAMENTO": fat,
                "META": meta,
                "MARGEM": round(random.uniform(28.0, 42.0), 2)
            })

    # ── 2. VW_EVOLUCAO_CLIENTES ──
    elif "CLIENTES" in nome_upper or "EVOLUCAO" in nome_upper:
        labels = _labels_mensais(12)
        base = random.randint(1500, 4000)
        for lbl in labels:
            base += random.randint(-50, 180)
            novos = round(random.uniform(50.0, 320.0), 0)
            churn = round(random.uniform(1.5, 6.2), 2)
            rows.append({
                "MES": lbl,
                "CLIENTES_ATIVOS": float(max(0, base)),
                "NOVOS_CLIENTES": novos,
                "CHURN_RATE": churn
            })

    # ── 3. VW_MARKET_SHARE_PRODUTOS ──
    elif "SHARE" in nome_upper or "PRODUTOS" in nome_upper or "CATEGORIA" in nome_upper:
        _LINHAS = [
            "Software Enterprise",
            "Suporte & Manutenção",
            "Consultoria",
            "Treinamento",
            "Hardware & Infra",
            "Licenças SaaS",
            "Outros"
        ]
        pesos = [random.uniform(4.0, 35.0) for _ in _LINHAS]
        total = sum(pesos)
        for name, p in zip(_LINHAS, pesos):
            rows.append({
                "CATEGORIA": name,
                "VALOR": round((p / total) * 100, 2)
            })

    # ── 4. VW_DETALHE_PEDIDOS / VW_VENDAS_CONTEXTO_GERAL ──
    elif "PEDIDOS" in nome_upper or "DETALHE" in nome_upper or "GERAL" in nome_upper:
        _STATUS_OPTS = ["APROVADO", "PENDENTE", "CANCELADO", "EM_PROCESSAMENTO"]
        _CLIENTES = [
            "Tech Solutions Ltda", "Grupo Horizonte S.A.", "DataBridge Corp",
            "Nexus Sistemas", "Alpha Tecnologia", "Beta Ventures"
        ]
        _VENDEDORES = ["Ana Costa", "Bruno Alves", "Carla Dias", "Daniel Souza", "Eduarda Lima"]
        hoje = date.today()
        for i in range(1, 25):
            pedido_date = hoje - timedelta(days=random.randint(0, 90))
            prazo_date = pedido_date + timedelta(days=random.randint(3, 45))
            st = random.choice(_STATUS_OPTS)
            valor = round(random.uniform(1200.0, 95000.0), 2)
            rows.append({
                "ID_PEDIDO": f"PED-{202400 + i:06d}",
                "CLIENTE": random.choice(_CLIENTES),
                "VENDEDOR": random.choice(_VENDEDORES),
                "VALOR": valor,
                "STATUS": st,
                "DATA_PEDIDO": pedido_date.isoformat(),
                "PRAZO_ENTREGA": prazo_date.isoformat(),
                "NF": f"NF-{random.randint(10000, 99999)}",
                "SLA_OK": prazo_date >= hoje if st != "CANCELADO" else None,
                "MARGEM": round(random.uniform(25.0, 48.0), 2)
            })

    # ── 5. VW_KPI_EXECUTIVO ──
    elif "KPI" in nome_upper or "EXECUTIVO" in nome_upper:
        rows = [
            {"METRICA": "Receita Total", "VALOR": round(random.uniform(2_500_000, 12_000_000), 2), "TENDENCIA": "up", "TREND_LABEL": "+12.4% vs mês anterior"},
            {"METRICA": "Margem Bruta", "VALOR": round(random.uniform(30.0, 45.0), 2), "TENDENCIA": "up", "TREND_LABEL": "+2.1 pp vs ano anterior"},
            {"METRICA": "Ticket Médio", "VALOR": round(random.uniform(8500, 62000), 2), "TENDENCIA": "stable", "TREND_LABEL": "estável"},
            {"METRICA": "NPS", "VALOR": round(random.uniform(60, 85), 1), "TENDENCIA": "up", "TREND_LABEL": "+4 pts"},
            {"METRICA": "Novos Clientes", "VALOR": float(random.randint(40, 280)), "TENDENCIA": "down", "TREND_LABEL": "-5% vs semana anterior"}
        ]

    # ── 6. VW_PERFORMANCE_VENDEDORES ──
    elif "VENDEDORES" in nome_upper or "PERFORMANCE" in nome_upper:
        _VENDEDORES = ["Ana Costa", "Bruno Alves", "Carla Dias", "Daniel Souza", "Eduarda Lima"]
        for v in _VENDEDORES:
            tot = round(random.uniform(50_000, 320_000), 2)
            meta = round(random.uniform(80_000, 250_000), 2)
            rows.append({
                "VENDEDOR": v,
                "TOTAL_VENDIDO": tot,
                "META": meta,
                "ATINGIMENTO": round((tot / meta) * 100, 2)
            })

    # ── Fallback Geral ──
    else:
        for i in range(1, 13):
            rows.append({
                "ITEM": f"Item {i}",
                "VALOR": round(random.uniform(100.0, 5000.0), 2)
            })

    return rows


def gerar_dados_mock_oracle(
    view: ViewCatalog,
    parametros: dict[str, str],
    chart_type: ChartType | None = None,
) -> dict[str, Any]:
    """
    Mantido temporariamente para compatibilidade legada direta de testes.
    Recomendado migrar para transform_data(gerar_raw_rows_mock(...)).
    """
    from services.data_transformer import transform_data
    raw = gerar_raw_rows_mock(view.nome_view_oracle, parametros)
    return transform_data(raw, chart_type or view.tipo_grafico_padrao)
