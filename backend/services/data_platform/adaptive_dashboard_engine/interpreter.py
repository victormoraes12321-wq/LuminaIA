"""
Adaptive Dashboard Engine (ADE) — Blueprint Interpreter
---------------------------------------------------------
Interpreta as definições de prioridade, hierarquia, narrativa e layout
provenientes do Blueprint analítico e da estratégia visual da IA.
Nunca altera o Blueprint original.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("luminaai.data_platform.adaptive_dashboard_engine.interpreter")


class BlueprintInterpreter:
    """
    Analisa os metadados analíticos e extrai a ordem lógica de priorização visual
    para guiar o motor de Grid Inteligente na distribuição espacial.
    """

    @staticmethod
    def interpret_hierarchy(
        blueprint: Any,
        components: List[Dict[str, Any]],
        visual_strategy: Dict[str, Any] = None
    ) -> List[Tuple[str, str, int]]:
        """
        Determina a hierarquia visual e ordem de precedência espacial de cada componente.
        Retorna uma lista ordenada de tuplas: (component_id, prioridade_estrada, peso_visual)
        """
        visual_strategy = visual_strategy or {}
        hierarchy = []

        # Mapeia pesos de prioridade para cálculo de precedência
        priority_weights = {
            "ALTA": 100,
            "MEDIA": 50,
            "BAIXA": 10
        }

        for idx, comp in enumerate(components):
            comp_id = str(comp.get("id"))
            category = comp.get("category", "UTILITIES")
            comp_type = comp.get("type", "BAR")

            # Prioridade padrão extraída da responsividade do componente ECE
            priority = comp.get("responsiveness_config", {}).get("priority", "MEDIA")
            weight = priority_weights.get(priority, 50)

            # Heurísticas de Layout Inteligente:
            # 1. KPIs sempre no topo com peso de narrativa aumentado
            if category == "KPI":
                priority = "ALTA"
                weight += 200 # Garante prioridade máxima de posicionamento
            # 2. Componentes que correspondem ao tipo de gráfico primário da estratégia visual ganham peso
            elif comp_type == visual_strategy.get("primary_chart_type"):
                priority = "ALTA"
                weight += 100
            # 3. Filtros e controles ficam no início da página
            elif category == "CONTROLS" or comp_type == "FILTROS":
                priority = "ALTA"
                weight += 150
            # 4. Tabelas de detalhamento costumam ir para o final da hierarquia de leitura
            elif category == "TABLES":
                weight -= 10

            # Adiciona índice original como desempate (preserva fluxo sequencial)
            weight -= idx

            hierarchy.append((comp_id, priority, weight))

        # Ordena decrescentemente por peso visual (precedência de posicionamento)
        hierarchy.sort(key=lambda x: x[2], reverse=True)
        
        logger.info(
            "[BlueprintInterpreter] Hierarquia interpretada: %s componentes ordenados por precedência",
            len(hierarchy)
        )
        return hierarchy
        
        
# Export singleton
blueprint_interpreter = BlueprintInterpreter()
