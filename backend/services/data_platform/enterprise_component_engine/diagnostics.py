"""
Enterprise Component Engine (ECE) — Component Diagnostics
---------------------------------------------------------
Motor de diagnósticos que avalia a integridade técnica, conformidade de dados,
desempenho e pontuações de qualidade (Quality) e saúde (Health) dos componentes.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from services.data_platform.enterprise_component_engine.schemas import ComponentSchema

logger = logging.getLogger("luminaai.data_platform.enterprise_component_engine.diagnostics")


class ComponentDiagnostics:
    """
    Executa análises heurísticas e qualitativas de componentes visuais.
    """

    @staticmethod
    def run_diagnostics(component: ComponentSchema) -> Dict[str, Any]:
        """
        Executa uma auditoria no componente, atualizando seus scores e integridade.
        """
        diagnostics = component.diagnostics or {}
        warnings = diagnostics.get("warnings", [])
        errors = diagnostics.get("errors", [])

        # 1. Avaliação do Health Score (Integridade Técnica - 0.0 a 1.0)
        # Penaliza se houver erros severos de execução ou de carregamento de dados
        health_score = 1.0
        if errors:
            health_score -= 0.50
        if component.state == "Error":
            health_score -= 0.30
        if not component.data_snapshot:
            # Sem dados
            health_score -= 0.20

        # Garante limite inferior
        health_score = max(0.0, round(health_score, 2))

        # 2. Avaliação do Quality Score (Conformidade de Design - 0.0 a 1.0)
        # Penaliza se faltarem acessibilidade ou regras de responsividade
        quality_score = 1.0
        if warnings:
            quality_score -= 0.10 * len(warnings)
        if not component.accessibility_config.get("aria_label"):
            quality_score -= 0.15 # Sem acessibilidade
        if not component.responsiveness_config.get("breakpoints"):
            quality_score -= 0.15 # Sem responsividade configurada

        quality_score = max(0.0, round(quality_score, 2))

        # 3. Atualiza os campos de diagnóstico do Componente
        diagnostics["health_score"] = health_score
        diagnostics["quality_score"] = quality_score
        diagnostics["schema_valid"] = True
        diagnostics["audited_at"] = component.created_at

        component.diagnostics = diagnostics

        logger.debug(
            "[ComponentDiagnostics] Componente id=%s auditado | Health=%s | Quality=%s",
            component.id,
            health_score,
            quality_score
        )

        return diagnostics


# Export singleton
component_diagnostics = ComponentDiagnostics()
