"""
Comparison Engine — LuminaAI Data Platform
------------------------------------------
Módulo analítico encarregado de executar análises comparativas de períodos
(Hoje x Ontem, Semana x Semana, Mês x Mês, Ano x Ano, ou períodos personalizados).
"""
import logging
from typing import Any

logger = logging.getLogger("luminaai.data_platform.comparison_engine")


class ComparisonEngine:
    """
    Motor de comparações temporais e de faturamento.
    """

    def compare_periods(self, current_val: float, previous_val: float) -> dict[str, Any]:
        """
        Compara dois valores e retorna a variação absoluta, percentual e direção.
        """
        diff = current_val - previous_val
        
        if previous_val == 0.0:
            pct_var = 100.0 if current_val > 0.0 else (0.0 if current_val == 0.0 else -100.0)
        else:
            pct_var = (diff / previous_val) * 100.0

        direction = "STABLE"
        if pct_var > 0.5:
            direction = "UP"
        elif pct_var < -0.5:
            direction = "DOWN"

        return {
            "valor_atual": round(current_val, 2),
            "valor_anterior": round(previous_val, 2),
            "diferenca_absoluta": round(diff, 2),
            "variacao_percentual": round(pct_var, 2),
            "direcao": direction,
        }

    def compare_groups(
        self,
        current_data: list[dict[str, Any]],
        previous_data: list[dict[str, Any]],
        group_key: str,
        value_key: str
    ) -> list[dict[str, Any]]:
        """
        Compara dois grupos agrupados por uma chave (ex: comparar vendas de filiais Mês Atual vs Anterior).
        """
        curr_map = {str(item[group_key]): float(item.get(value_key, 0.0)) for item in current_data}
        prev_map = {str(item[group_key]): float(item.get(value_key, 0.0)) for item in previous_data}
        
        all_keys = set(curr_map.keys()) | set(prev_map.keys())
        comparison_result = []

        for key in all_keys:
            c_val = curr_map.get(key, 0.0)
            p_val = prev_map.get(key, 0.0)
            
            comp = self.compare_periods(c_val, p_val)
            comp[group_key] = key
            comparison_result.append(comp)

        # Ordena pelo valor atual decrescente
        return sorted(comparison_result, key=lambda x: x["valor_atual"], reverse=True)


# Singleton export
comparison_engine = ComparisonEngine()
