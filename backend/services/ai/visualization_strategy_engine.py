"""
LuminaAI — Visualization Strategy Engine
----------------------------------------
Define o formato de gráfico e a prioridade de layout ideais para o frontend,
incorporando a estratégia ao Blueprint.
"""
from __future__ import annotations

import logging
from services.ai.schemas import VisualStrategySchema

logger = logging.getLogger("luminaai.ai.visualization_strategy_engine")


class VisualizationStrategyEngine:
    """
    Motor de definição estratégica de visualização de dados.
    """

    def determine_strategy(
        self,
        operacao: str,
        entidade: str,
        explicit_chart: str | None = None,
        explicit_charts: list[str] | None = None,
    ) -> VisualStrategySchema:
        """
        Calcula o componente ideal e os níveis de interatividade e layout recomendados.
        """
        op = operacao.upper() if operacao else "SOMA"
        ent = entidade.upper() if entidade else "VENDA"
        
        # 1. Componente principal
        if explicit_chart:
            main_component = explicit_chart.upper()
        else:
            if op in ("RANKING", "TOP", "BOTTOM", "MAIOR", "MENOR"):
                main_component = "BAR"
            elif op in ("TENDENCIA", "CRESCIMENTO", "QUEDA", "PROJECOES"):
                main_component = "LINE"
            elif op in ("PARTICIPACAO", "DISTRIBUICAO"):
                main_component = "PIE"
            elif op in ("TOTAL", "KPI", "SOMA", "MEDIA", "MAXIMO", "MINIMO") and ent in ("RECEITA", "LUCRO", "MARGEM", "TICKET"):
                main_component = "KPI"
            else:
                main_component = "TABLE"

        # 2. Componentes secundários (tabelas e cards auxiliares de suporte)
        sec_components = []
        if explicit_charts:
            sec_components = [c.upper() for c in explicit_charts if c.upper() != main_component]
        elif main_component in ("BAR", "LINE", "PIE"):
            sec_components = ["TABLE"]  # Sempre fornece tabela de apoio a gráficos

        # 3. Interatividade e recursos extras
        interactivity = ["drill-down"]
        if op in ("DETALHAMENTO", "LISTAGEM"):
            interactivity.append("export-excel")
            interactivity.append("column-sort")

        return VisualStrategySchema(
            componente_principal=main_component,
            componentes_secundarios=sec_components,
            interatividade=interactivity,
            layout_sugerido="FLOW" if main_component == "KPI" else "GRID",
            responsividade=True,
        )


# Singleton export
visualization_strategy_engine = VisualizationStrategyEngine()
