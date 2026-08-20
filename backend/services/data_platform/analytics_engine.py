"""
Analytics Engine — LuminaAI Data Platform
-----------------------------------------
Orquestrador central de inteligência matemática, estatística e comparativa.
Processa datasets analíticos com base no Blueprint solicitado, aplicando as
regras de negócio do CalculationEngine, ComparisonEngine e TrendEngine.

Regra: Nunca assume conceitos subjetivos nem executa IA.
"""
import uuid
import logging
from typing import Any

from services.data_platform.calculation_engine import calculation_engine
from services.data_platform.comparison_engine import comparison_engine
from services.data_platform.trend_engine import trend_engine
from services.data_platform.business_rules_engine import business_rules_engine

logger = logging.getLogger("luminaai.data_platform.analytics_engine")


class AnalyticsEngine:
    """
    Orquestrador analítico corporativo.
    """

    async def process_analytics(
        self,
        tenant_id: uuid.UUID,
        datasets: dict[str, dict[str, Any]],
        blueprint: Any
    ) -> dict[str, Any]:
        """
        Orquestra cálculos e comparações sobre os datasets lidos da Data Platform.
        """
        logger.info("[AnalyticsEngine] Iniciando processamento matemático e estatístico...")
        
        results = {
            "kpis": {},
            "trends": {},
            "stats": {}
        }

        # 1. Identifica métricas de negócio e regras de agregação solicitadas
        for q_id, ds in datasets.items():
            rows = ds["data"]
            schema = ds["schema"]
            view_name = ds["metadata"]["view_name"]

            # Identifica colunas financeiras/comerciais (valor, receita, custo)
            receita_col = next((c for c in schema if "receita" in c or "faturamento" in c), None)
            custo_col = next((c for c in schema if "custo" in c or "cmv" in c), None)
            valor_col = next((c for c in schema if "valor" in c or "vl_" in c or "receita" in c or "faturamento" in c or "total" in c), None)
            data_col = next((c for c in schema if "data" in c or "dt_" in c or "periodo" in c), None)

            # A. Cálculos de KPI Financeiros
            if receita_col and custo_col:
                tot_receita = sum(float(r.get(receita_col, 0.0)) for r in rows)
                tot_custo = sum(float(r.get(custo_col, 0.0)) for r in rows)
                
                margin = calculation_engine.calculate_margin(tot_receita, tot_custo)
                markup = calculation_engine.calculate_markup(tot_receita, tot_custo)

                # Verifica regras de consistência de agregação
                agg_valid = await business_rules_engine.validate_aggregation_rule(tenant_id, "margem", "SOMA")
                
                results["kpis"]["lucro"] = {
                    "valor_atual": tot_receita - tot_custo,
                    "valor_anterior": 0.0,
                    "diferenca_absoluta": tot_receita - tot_custo,
                    "variacao_percentual": 100.0 if tot_custo else 0.0,
                    "direcao": "UP" if tot_receita > tot_custo else "STABLE"
                }
                results["kpis"]["margem"] = {
                    "valor_atual": margin,
                    "valor_anterior": 0.0,
                    "diferenca_absoluta": margin,
                    "variacao_percentual": 0.0,
                    "direcao": "STABLE"
                }

            # B. Cálculo de Séries Temporais e Regressão de Tendências
            if valor_col and data_col:
                # Agrupa valores por data ordenados
                time_series_data = {}
                for r in rows:
                    dt = r[data_col]
                    val = float(r.get(valor_col, 0.0))
                    time_series_data[dt] = time_series_data.get(dt, 0.0) + val
                
                sorted_dates = sorted(time_series_data.keys())
                series_y = [time_series_data[d] for d in sorted_dates]

                # Executa regressão linear e sazonalidade se houver pontos suficientes
                if len(series_y) >= 3:
                    trend_res = trend_engine.analyze_trend(series_y)
                    results["trends"][view_name] = trend_res
                    
                    # Se houver faturamento/valores agrupados, compara o último ponto com o anterior
                    results["kpis"][f"{view_name.lower()}_ultimo_periodo"] = comparison_engine.compare_periods(
                        series_y[-1],
                        series_y[-2] if len(series_y) > 1 else 0.0
                    )

            # C. Estatísticas descritivas básicas das colunas numéricas
            for col, col_type in schema.items():
                if col_type in ("integer", "float"):
                    col_vals = [float(r.get(col, 0.0)) for r in rows]
                    if col_vals:
                        results["stats"][f"{view_name.lower()}.{col}"] = calculation_engine.compute_stats(col_vals)

        return results


# Singleton export
analytics_engine = AnalyticsEngine()
