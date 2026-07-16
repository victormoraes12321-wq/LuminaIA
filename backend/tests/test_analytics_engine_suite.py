"""
Testes de Integração e Unitários: Analytics Engine Suite
---------------------------------------------------------
Valida todos os submotores analíticos e matemáticos do LuminaAI:
  1. CalculationEngine (KPIs de BI, estatísticas, Curva ABC)
  2. ComparisonEngine (comparações entre períodos temporais)
  3. TrendEngine (regressão linear de tendências e sazonalidades)
  4. BusinessRulesEngine (validação de agregações consistentes)
  5. DatasetBuilder (estruturação, schema, normalização e checksum)
  6. DashboardPayloadBuilder (montagem de widgets para o frontend)
  7. AnalyticsEngine (orquestração completa dos cálculos)
"""
from __future__ import annotations

import uuid
import pytest
from datetime import datetime, date

from services.data_platform.query_resolver import query_resolver
from services.data_platform.calculation_engine import calculation_engine
from services.data_platform.comparison_engine import comparison_engine
from services.data_platform.trend_engine import trend_engine
from services.data_platform.business_rules_engine import business_rules_engine
from services.data_platform.dataset_builder import dataset_builder
from services.data_platform.dashboard_payload_builder import dashboard_payload_builder
from services.data_platform.analytics_engine import analytics_engine

TENANT_A = uuid.UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")


class TestCalculationEngine:

    def test_calculate_margin(self):
        """Deve calcular a margem corretamente."""
        margin = calculation_engine.calculate_margin(receita=1000.0, custo=600.0)
        assert margin == 40.0

        margin_zero = calculation_engine.calculate_margin(receita=0.0, custo=600.0)
        assert margin_zero == 0.0

    def test_calculate_markup(self):
        """Deve calcular o markup corretamente."""
        markup = calculation_engine.calculate_markup(receita=1000.0, custo=500.0)
        assert markup == 100.0

        markup_zero = calculation_engine.calculate_markup(receita=1000.0, custo=0.0)
        assert markup_zero == 0.0

    def test_calculate_roi(self):
        """Deve calcular o ROI corretamente."""
        roi = calculation_engine.calculate_roi(retorno=1500.0, investimento=1000.0)
        assert roi == 50.0

    def test_calculate_roas(self):
        """Deve calcular o ROAS corretamente."""
        roas = calculation_engine.calculate_roas(receita=5000.0, custo_ad=1000.0)
        assert roas == 5.0

    def test_calculate_ticket_medio(self):
        """Deve calcular o Ticket Médio."""
        ticket = calculation_engine.calculate_ticket_medio(faturamento=15000.0, transacoes=10)
        assert ticket == 1500.0

    def test_compute_stats_descritivas(self):
        """Deve calcular média, mediana, desvio padrão de um conjunto numérico."""
        vals = [10.0, 20.0, 30.0, 40.0, 50.0]
        stats = calculation_engine.compute_stats(vals)
        assert stats["count"] == 5
        assert stats["sum"] == 150.0
        assert stats["mean"] == 30.0
        assert stats["median"] == 30.0
        assert stats["min"] == 10.0
        assert stats["max"] == 50.0
        assert stats["std_dev"] > 0.0

    def test_compute_percentiles_e_quartis(self):
        """Deve calcular percentis e quartis corretos."""
        vals = [10.0, 20.0, 30.0, 40.0, 50.0]
        percentiles = calculation_engine.compute_percentiles(vals, [25.0, 50.0, 75.0])
        assert percentiles[50.0] == 30.0
        assert percentiles[25.0] == 20.0
        assert percentiles[75.0] == 40.0

    def test_compute_media_movel(self):
        """Deve calcular a média móvel simples por janela temporal."""
        vals = [10.0, 20.0, 30.0, 40.0, 50.0]
        ma = calculation_engine.compute_media_movel(vals, window=3)
        assert len(ma) == 5
        assert ma[0] == 10.0
        assert ma[1] == 15.0 # (10+20)/2
        assert ma[2] == 20.0 # (10+20+30)/3
        assert ma[3] == 30.0 # (20+30+40)/3

    def test_compute_curva_abc(self):
        """Deve segmentar itens na curva ABC com base no acumulado acumulativo."""
        items = [
            {"item": "Prod A", "valor": 80.0},
            {"item": "Prod B", "valor": 15.0},
            {"item": "Prod C", "valor": 5.0},
        ]
        abc_list = calculation_engine.compute_curva_abc(items, "valor")
        assert abc_list[0]["classe_abc"] == "A"
        assert abc_list[1]["classe_abc"] == "B"
        assert abc_list[2]["classe_abc"] == "C"


class TestComparisonEngine:

    def test_compare_periods_growth(self):
        """Deve retornar crescimento (UP) e diferença percentual de 50%."""
        comp = comparison_engine.compare_periods(current_val=150.0, previous_val=100.0)
        assert comp["variacao_percentual"] == 50.0
        assert comp["diferenca_absoluta"] == 50.0
        assert comp["direcao"] == "UP"

    def test_compare_periods_decrease(self):
        """Deve retornar queda (DOWN) e diferença percentual de -25%."""
        comp = comparison_engine.compare_periods(current_val=75.0, previous_val=100.0)
        assert comp["variacao_percentual"] == -25.0
        assert comp["direcao"] == "DOWN"


class TestTrendEngine:

    def test_analyze_trend_growth(self):
        """Deve detectar tendência de crescimento para série crescente."""
        ys = [10.0, 20.0, 30.0, 40.0, 50.0]
        trend = trend_engine.analyze_trend(ys)
        assert trend["tendencia"] == "GROWTH"
        assert trend["coeficiente_angular"] > 0.0

    def test_analyze_trend_decrease(self):
        """Deve detectar tendência de queda para série decrescente."""
        ys = [50.0, 40.0, 30.0, 20.0, 10.0]
        trend = trend_engine.analyze_trend(ys)
        assert trend["tendencia"] == "DECREASE"
        assert trend["coeficiente_angular"] < 0.0

    def test_detect_seasonality(self):
        """Deve calcular autocorrelação e indicar se há sazonalidade."""
        ys = [10.0, 20.0, 10.0, 20.0, 10.0, 20.0, 10.0, 20.0, 10.0, 20.0, 10.0, 20.0, 10.0, 20.0, 10.0, 20.0]
        season = trend_engine.detect_seasonality(ys, period=2)
        assert season["sazonalidade_detectada"] is True
        assert season["score_autocorrelacao"] > 0.5


class TestBusinessRulesEngine:

    @pytest.mark.asyncio
    async def test_validate_aggregation_rule_sum_on_margin(self):
        """Deve barrar soma de margem por ser percentual/taxa (inconsistência de BI)."""
        valid = await business_rules_engine.validate_aggregation_rule(
            tenant_id=TENANT_A,
            kpi_name="margem_bruta",
            operation="SOMA"
        )
        assert valid is False

    @pytest.mark.asyncio
    async def test_validate_aggregation_rule_sum_on_revenue(self):
        """Deve permitir soma de faturamento."""
        valid = await business_rules_engine.validate_aggregation_rule(
            tenant_id=TENANT_A,
            kpi_name="faturamento_total",
            operation="SOMA"
        )
        assert valid is True

    @pytest.mark.asyncio
    async def test_apply_tenant_filters_prevention(self):
        """Deve barrar e filtrar registros pertencentes a outro tenant (Cross-Tenant prevention)."""
        rows = [
            {"id": 1, "tenant_id": TENANT_A, "valor": 100.0},
            {"id": 2, "tenant_id": uuid.uuid4(), "valor": 200.0}, # Tenant intruso
        ]
        filtered = await business_rules_engine.apply_tenant_filters(TENANT_A, rows, "VW_VENDAS")
        assert len(filtered) == 1
        assert filtered[0]["id"] == 1


class TestDatasetBuilder:

    def test_build_dataset_structure(self):
        """Deve formatar o dataset analítico e tipar corretamente as colunas."""
        rows = [
            {"id": 1, "data": datetime(2026, 7, 6), "valor": 1500.0, "ativo": True}
        ]
        ds = dataset_builder.build_dataset(
            tenant_id=TENANT_A,
            raw_rows=rows,
            view_name="VW_VENDAS"
        )
        assert "metadata" in ds
        assert "schema" in ds
        assert "data" in ds
        assert ds["schema"]["valor"] == "float"
        assert ds["schema"]["ativo"] == "boolean"
        assert ds["schema"]["data"] == "date"
        assert isinstance(ds["data"][0]["data"], str) # Data em ISO string


class TestDashboardPayloadBuilder:

    def test_build_payload_structure(self):
        """Deve estruturar widgets, cards de KPI, gráficos e tabelas para o frontend."""
        datasets = {
            "principal": dataset_builder.build_dataset(
                tenant_id=TENANT_A,
                raw_rows=[{"categoria": "Comercial", "faturamento": 25000.0}],
                view_name="VW_VENDAS"
            )
        }
        
        analytics_results = {
            "kpis": {
                "lucro": {
                    "valor_atual": 15000.0,
                    "valor_anterior": 10000.0,
                    "diferenca_absoluta": 5000.0,
                    "variacao_percentual": 50.0,
                    "direcao": "UP"
                }
            }
        }

        payload = dashboard_payload_builder.build_payload(
            tenant_id=TENANT_A,
            datasets=datasets,
            primary_intention=None,
            analytics_results=analytics_results
        )

        assert payload["tenant_id"] == str(TENANT_A)
        assert len(payload["widgets"]) > 0
        
        # Confere se os widgets contêm o Card de KPI e a Tabela/Gráfico
        types = [w["type"] for w in payload["widgets"]]
        assert "KPI_CARD" in types
        assert "TABLE" in types
        assert "BAR" in types


class TestAnalyticsEngine:

    @pytest.mark.asyncio
    async def test_process_analytics_orchestration(self):
        """Deve orquestrar e processar KPIs, séries temporais e estatísticas."""
        datasets = {
            "principal": dataset_builder.build_dataset(
                tenant_id=TENANT_A,
                raw_rows=[
                    {"data": "2026-07-06", "receita": 1000.0, "custo": 600.0},
                    {"data": "2026-07-07", "receita": 2000.0, "custo": 1200.0},
                    {"data": "2026-07-08", "receita": 3000.0, "custo": 1800.0},
                ],
                view_name="VW_VENDAS"
            )
        }

        results = await analytics_engine.process_analytics(
            tenant_id=TENANT_A,
            datasets=datasets,
            blueprint=None
        )

        assert "lucro" in results["kpis"]
        assert "margem" in results["kpis"]
        assert results["kpis"]["margem"]["valor_atual"] == 40.0 # Margem de 40% (6000 receita - 3600 custo) / 6000
        assert "VW_VENDAS" in results["trends"]
        assert results["trends"]["VW_VENDAS"]["tendencia"] == "GROWTH"
