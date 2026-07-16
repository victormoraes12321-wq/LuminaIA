"""
Trend Engine — LuminaAI Data Platform
-------------------------------------
Módulo encarregado de processar variações, tendências, crescimento, sazonalidades
e oscilações sobre séries temporais analíticas.

Regra: Apenas faz cálculos determinísticos, nunca gera interpretações subjetivas.
"""
import logging
from typing import Any

logger = logging.getLogger("luminaai.data_platform.trend_engine")


class TrendEngine:
    """
    Motor de análise de séries temporais e tendências.
    """

    def analyze_trend(self, time_series_y: list[float]) -> dict[str, Any]:
        """
        Calcula a tendência de uma série temporal usando regressão linear simples (mínimos quadrados).
        Retorna o coeficiente angular (slope), variação estimada de ponta a ponta e indicador de direção.
        """
        n = len(time_series_y)
        if n < 2:
            return {
                "coeficiente_angular": 0.0,
                "tendencia": "STABLE",
                "variacao_projetada_percentual": 0.0,
                "msg": "Pontos insuficientes para cálculo de tendência."
            }

        # x assume índices de 0 a n-1
        xs = list(range(n))
        ys = time_series_y

        mean_x = sum(xs) / n
        mean_y = sum(ys) / n

        num = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
        den = sum((xs[i] - mean_x) ** 2 for i in range(n))

        slope = num / den if den != 0.0 else 0.0

        # Variação projetada (diferença entre reta inicial e final da regressão)
        val_start = mean_y - slope * mean_x
        val_end = val_start + slope * (n - 1)
        
        diff = val_end - val_start
        if val_start == 0.0:
            pct_var = 100.0 if diff > 0.0 else (0.0 if diff == 0.0 else -100.0)
        else:
            pct_var = (diff / val_start) * 100.0

        # Direção
        direction = "STABLE"
        if slope > 0.01:
            direction = "GROWTH"
        elif slope < -0.01:
            direction = "DECREASE"

        return {
            "coeficiente_angular": round(slope, 4),
            "tendencia": direction,
            "variacao_projetada_percentual": round(pct_var, 2),
            "total_pontos": n
        }

    def detect_seasonality(self, time_series_y: list[float], period: int = 7) -> dict[str, Any]:
        """
        Tenta detectar comportamento sazonal na série calculando a autocorrelação
        básica em relação ao período especificado (ex: 7 dias para semanal, 12 meses para anual).
        """
        n = len(time_series_y)
        if n < (period * 2):
            return {
                "sazonalidade_detectada": False,
                "score_autocorrelacao": 0.0,
                "msg": "Dados insuficientes para detectar ciclo de período."
            }

        mean = sum(time_series_y) / n
        var = sum((y - mean) ** 2 for y in time_series_y) / n
        if var == 0.0:
            return {"sazonalidade_detectada": False, "score_autocorrelacao": 0.0}

        # Calcula a covariância com lag = period
        cov_lag = sum(
            (time_series_y[i] - mean) * (time_series_y[i - period] - mean)
            for i in range(period, n)
        ) / (n - period)

        autocorr = cov_lag / var

        # Se a autocorrelação for alta (> 0.5), indica sazonalidade
        seasonality = autocorr > 0.5

        return {
            "sazonalidade_detectada": bool(seasonality),
            "score_autocorrelacao": round(autocorr, 3),
            "periodo_testado": period
        }


# Singleton export
trend_engine = TrendEngine()
