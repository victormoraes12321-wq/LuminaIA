"""
Adaptive Dashboard Engine (ADE) — Grid Engine & Layout Intelligence
-------------------------------------------------------------------
Calcula posicionamento bidimensional responsivo (x, y, w, h)
em grade de 12 colunas, eliminando sobreposições e lacunas vazias.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Tuple

from services.data_platform.adaptive_dashboard_engine.schemas import GridPosition
from services.data_platform.adaptive_dashboard_engine.interpreter import blueprint_interpreter

logger = logging.getLogger("luminaai.data_platform.adaptive_dashboard_engine.grid_engine")


class AdaptiveGridEngine:
    """
    Motor inteligente de layout. Organiza componentes na tela baseando-se em pesos,
    prioridades e dimensões relativas para 5 breakpoints oficiais de dispositivos.
    """

    SUPPORTED_BREAKPOINTS = [
        "ultra_wide",
        "desktop",
        "notebook",
        "tablet",
        "mobile"
    ]

    def compute_layouts(
        self,
        components: List[Dict[str, Any]],
        blueprint: Any,
        visual_strategy: Dict[str, Any] = None
    ) -> Dict[str, List[GridPosition]]:
        """
        Gera o mapa completo de coordenadas responsivas do dashboard para todos os breakpoints.
        """
        logger.info("[AdaptiveGridEngine] Iniciando cálculo tridimensional de posições...")
        
        # 1. Interpreta a hierarquia e ordem de precedência visual dos componentes
        hierarchy = blueprint_interpreter.interpret_hierarchy(blueprint, components, visual_strategy)
        
        grid_layouts = {}

        # 2. Roda a distribuição bidimensional para cada breakpoint de tela
        for bp in self.SUPPORTED_BREAKPOINTS:
            grid_layouts[bp] = self._pack_grid(components, hierarchy, bp)

        logger.info(
            "[AdaptiveGridEngine] Posicionamento responsivo gerado para %d breakpoints com sucesso",
            len(grid_layouts)
        )
        return grid_layouts

    def _pack_grid(
        self,
        components: List[Dict[str, Any]],
        hierarchy: List[Tuple[str, str, int]],
        breakpoint_name: str
    ) -> List[GridPosition]:
        """
        Algoritmo de empacotamento 2D (Bin Packing / Grid Packing).
        Encontra a primeira vaga disponível (x, y) de tamanho (w, h) na grade de 12 colunas.
        Garante alinhamento e previne colisões/sobreposições.
        """
        positions = []
        # Matriz de controle de ocupação: 12 colunas por até 1000 linhas
        max_rows = 1000
        occupied = [[False] * 12 for _ in range(max_rows)]
        
        comp_map = {str(c["id"]): c for c in components}

        for comp_id, _, _ in hierarchy:
            comp = comp_map.get(comp_id)
            if not comp:
                continue

            # Obtém dimensões especificadas pelo ECE para este breakpoint
            bp_config = (
                comp.get("responsiveness_config", {})
                .get("breakpoints", {})
                .get(breakpoint_name, {"cols": 6, "rows": 4})
            )
            
            # Limita largura mínima em 1 e máxima em 12 colunas
            w = min(12, max(1, bp_config.get("cols", 6)))
            h = max(1, bp_config.get("rows", 4))

            placed = False
            
            # Busca a primeira coordenada (x, y) livre onde caiba o bloco (w, h)
            for y in range(max_rows):
                for x in range(12 - w + 1):
                    # Verifica se todas as células sob o bloco estão livres
                    cell_free = True
                    for dy in range(h):
                        for dx in range(w):
                            if occupied[y + dy][x + dx]:
                                cell_free = False
                                break
                        if not cell_free:
                            break

                    if cell_free:
                        # Reserva o espaço marcando como ocupado
                        for dy in range(h):
                            for dx in range(w):
                                occupied[y + dy][x + dx] = True
                        
                        positions.append(
                            GridPosition(
                                component_id=uuid.UUID(comp_id),
                                x=x,
                                y=y,
                                w=w,
                                h=h
                            )
                        )
                        placed = True
                        break
                if placed:
                    break

        return positions


# Export singleton
adaptive_grid_engine = AdaptiveGridEngine()
