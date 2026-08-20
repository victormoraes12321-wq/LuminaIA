"""
Adaptive Dashboard Engine (ADE) — Diagnostics
----------------------------------------------
Mede a saúde técnica e qualidade global do layout da Dashboard consolidada.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger("luminaai.data_platform.adaptive_dashboard_engine.diagnostics")


class DashboardDiagnostics:
    """
    Avalia a integridade técnica global e qualidade da composição do painel.
    """

    @staticmethod
    def run_diagnostics(
        components: List[Dict[str, Any]],
        personalization_applied: bool,
        render_time_ms: float
    ) -> Dict[str, Any]:
        """
        Gera o relatório de diagnósticos consolidado e calcula os scores de saúde e qualidade.
        """
        warnings = []
        errors = []

        if not components:
            errors.append("Nenhum componente cadastrado ou renderizado no painel.")

        # 1. Calcula a média do Health Score de todos os componentes
        sum_health = 0.0
        sum_quality = 0.0
        
        for c in components:
            diag = c.get("diagnostics", {})
            sum_health += diag.get("health_score", 1.0)
            sum_quality += diag.get("quality_score", 1.0)
            
            # Agrega erros e avisos
            for w in diag.get("warnings", []):
                warnings.append(f"Componente {c.get('name')}: {w}")
            for e in diag.get("errors", []):
                errors.append(f"Componente {c.get('name')}: {e}")

        comp_count = len(components) or 1
        avg_health = round(sum_health / comp_count, 2)
        avg_quality = round(sum_quality / comp_count, 2)

        # 2. Penalizações Globais
        global_health = avg_health
        if errors:
            global_health -= 0.15
        if render_time_ms > 200.0:
            global_health -= 0.10 # Lentidão penaliza saúde técnica

        global_health = max(0.0, min(1.0, round(global_health, 2)))

        global_quality = avg_quality
        if warnings:
            global_quality -= 0.05 * len(warnings)
        if not personalization_applied:
            # Não é uma falha, mas a personalização aplicada agrega qualidade de experiência
            pass

        global_quality = max(0.0, min(1.0, round(global_quality, 2)))

        diagnostics_report = {
            "health_score": global_health,
            "quality_score": global_quality,
            "warnings": warnings[:10], # Limita em 10 logs
            "errors": errors[:10],
            "components_audited_count": len(components),
            "render_latency_rating": "EXCELENTE" if render_time_ms < 50 else ("BOM" if render_time_ms < 150 else "ATENÇÃO")
        }

        logger.debug(
            "[DashboardDiagnostics] Globais: Health=%s | Quality=%s",
            global_health,
            global_quality
        )
        return diagnostics_report


# Export singleton
dashboard_diagnostics = DashboardDiagnostics()
