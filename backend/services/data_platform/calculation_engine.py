"""
Calculation Engine — LuminaAI Data Platform
-------------------------------------------
Módulo responsável por realizar toda a inteligência matemática, estatística e
cálculos de regras de negócio de BI (Margem, ROI, CMV, Ticket Médio, etc.) sobre datasets.

Regra: Nunca assume conceitos, sempre opera de forma exata e determinística.
"""
import math
import logging
from typing import Any

logger = logging.getLogger("luminaai.data_platform.calculation_engine")


class CalculationEngine:
    """
    Motor matemático e estatístico do Analytics Engine.
    """

    # ── KPIs Financeiros & Comerciais ───────────────────────────────────────

    def calculate_margin(self, receita: float, custo: float) -> float:
        """Calcula a margem de lucro operacional (%)."""
        if not receita:
            return 0.0
        return ((receita - custo) / receita) * 100.0

    def calculate_markup(self, receita: float, custo: float) -> float:
        """Calcula o markup de venda (%)."""
        if not custo:
            return 0.0
        return ((receita - custo) / custo) * 100.0

    def calculate_roi(self, retorno: float, investimento: float) -> float:
        """Calcula o Retorno sobre Investimento (%)."""
        if not investimento:
            return 0.0
        return ((retorno - investimento) / investimento) * 100.0

    def calculate_roas(self, receita: float, custo_ad: float) -> float:
        """Calcula o Retorno sobre Gasto Publicitário (ROAS)."""
        if not custo_ad:
            return 0.0
        return receita / custo_ad

    def calculate_ltv(self, valor_vida_cliente: float, taxa_churn: float) -> float:
        """Calcula o Lifetime Value (LTV)."""
        if not taxa_churn:
            return valor_vida_cliente
        return valor_vida_cliente / taxa_churn

    def calculate_ticket_medio(self, faturamento: float, transacoes: int) -> float:
        """Calcula o Ticket Médio."""
        if not transacoes:
            return 0.0
        return faturamento / transacoes

    # ── Estatísticas Descritivas ──────────────────────────────────────────

    def compute_stats(self, values: list[float]) -> dict[str, float]:
        """Calcula estatísticas básicas completas sobre uma lista de valores."""
        if not values:
            return {
                "count": 0, "sum": 0.0, "mean": 0.0, "median": 0.0,
                "min": 0.0, "max": 0.0, "std_dev": 0.0
            }
        
        sorted_vals = sorted(values)
        n = len(values)
        total = sum(sorted_vals)
        mean = total / n

        # Mediana
        if n % 2 == 1:
            median = sorted_vals[n // 2]
        else:
            median = (sorted_vals[(n // 2) - 1] + sorted_vals[n // 2]) / 2.0

        # Mínimo e Máximo
        min_v = sorted_vals[0]
        max_v = sorted_vals[-1]

        # Desvio Padrão
        variance = sum((x - mean) ** 2 for x in sorted_vals) / n if n > 1 else 0.0
        std_dev = math.sqrt(variance)

        return {
            "count": n,
            "sum": total,
            "mean": mean,
            "median": median,
            "min": min_v,
            "max": max_v,
            "std_dev": std_dev,
        }

    def compute_percentiles(self, values: list[float], percentiles: list[float]) -> dict[float, float]:
        """Calcula os percentis especificados de um conjunto de valores."""
        if not values:
            return {p: 0.0 for p in percentiles}
            
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        res = {}
        
        for p in percentiles:
            idx = (p / 100.0) * (n - 1)
            idx_floor = int(math.floor(idx))
            idx_ceil = int(math.ceil(idx))
            if idx_floor == idx_ceil:
                res[p] = sorted_vals[idx_floor]
            else:
                # Interpolação linear
                d = idx - idx_floor
                res[p] = sorted_vals[idx_floor] * (1.0 - d) + sorted_vals[idx_ceil] * d
        return res

    def compute_media_movel(self, values: list[float], window: int = 3) -> list[float]:
        """Calcula a média móvel simples com base em uma janela."""
        if not values:
            return []
        res = []
        for i in range(len(values)):
            start = max(0, i - window + 1)
            chunk = values[start:i + 1]
            res.append(sum(chunk) / len(chunk))
        return res

    # ── Curva ABC ───────────────────────────────────────────────────────────

    def compute_curva_abc(self, items: list[dict[str, Any]], key_value: str) -> list[dict[str, Any]]:
        """
        Segmenta itens na Curva ABC com base no valor acumulado acumulativo (80%, 15%, 5%).
        Adiciona a coluna 'classe_abc' ('A', 'B' ou 'C') em cada item.
        """
        if not items:
            return []

        # Ordena itens por valor decrescente
        sorted_items = sorted(items, key=lambda x: float(x.get(key_value, 0.0)), reverse=True)
        total_val = sum(float(x.get(key_value, 0.0)) for x in sorted_items)

        if total_val <= 0:
            for item in sorted_items:
                item["classe_abc"] = "C"
                item["participacao_acumulada_abc"] = 100.0
            return sorted_items

        acumulado = 0.0
        for item in sorted_items:
            val = float(item.get(key_value, 0.0))
            acumulado += val
            part = (acumulado / total_val) * 100.0
            
            item["participacao_acumulada_abc"] = round(part, 2)
            if part <= 80.0:
                item["classe_abc"] = "A"
            elif part <= 95.0:
                item["classe_abc"] = "B"
            else:
                item["classe_abc"] = "C"

        return sorted_items


# Singleton export
calculation_engine = CalculationEngine()
