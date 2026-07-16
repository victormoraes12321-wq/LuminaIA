"""
Adaptive Dashboard Engine (ADE) — Facade
-----------------------------------------
Ponto de entrada centralizado da camada Adaptive Dashboard Engine.
"""
from __future__ import annotations

import logging
import uuid
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.data_platform.adaptive_dashboard_engine.schemas import DashboardLayoutSchema
from services.data_platform.adaptive_dashboard_engine.interpreter import blueprint_interpreter
from services.data_platform.adaptive_dashboard_engine.grid_engine import adaptive_grid_engine
from services.data_platform.adaptive_dashboard_engine.personalization import personalization_engine
from services.data_platform.adaptive_dashboard_engine.optimizer import rendering_optimizer
from services.data_platform.adaptive_dashboard_engine.diagnostics import dashboard_diagnostics
from services.data_platform.adaptive_dashboard_engine.security import dashboard_security

logger = logging.getLogger("luminaai.data_platform.adaptive_dashboard_engine")


class AdaptiveDashboardEngine:
    """
    Fachada centralizadora do Adaptive Dashboard Engine (ADE).
    Orquestra a interpretação, montagem do grid responsivo, personalização
    e avaliações de segurança e diagnóstico.
    """

    def __init__(self):
        self._telemetry_history: List[Dict[str, Any]] = []

    def assemble_dashboard_layout(
        self,
        tenant_id: uuid.UUID,
        ece_components: List[Dict[str, Any]],
        blueprint: Any,
        visual_strategy: Dict[str, Any] = None,
        theme_name: str = "CORPORATIVO",
        user_preferences: Dict[str, Any] = None,
        user_role: str = "USER"
    ) -> Dict[str, Any]:
        """
        Interpreta e monta de forma adaptável, responsiva e performática o layout do painel.
        """
        start_time = time.perf_counter()
        logger.info("[ADE] Iniciando montagem adaptável do painel para tenant=%s", tenant_id)

        # 1. Segurança: Valida papéis de acesso
        dashboard_security.enforce_role_access(user_role)

        # 2. Aplica Personalização de Preferências do Usuário (Personalization Engine)
        customized_components, personalization_applied = personalization_engine.apply_preferences(
            components=ece_components,
            preferences=user_preferences
        )

        # 3. Calcula o posicionamento responsivo nos Breakpoints do Grid (Adaptive Grid Engine)
        grid_layouts = adaptive_grid_engine.compute_layouts(
            components=customized_components,
            blueprint=blueprint,
            visual_strategy=visual_strategy
        )

        # 4. Avalia Otimizações de Renderização e calcula latência (Rendering Optimizer)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        # Simulamos cache hit se todos os componentes já estavam em estado Ready/sem alterações
        cache_hit = len(ece_components) > 0 and all(c.get("state") == "Ready" for c in ece_components)
        opt_report = rendering_optimizer.evaluate_optimization(
            render_time_ms=elapsed_ms,
            components=customized_components,
            cache_hit=cache_hit
        )

        # 5. Executa Diagnósticos Globais do Painel (Dashboard Diagnostics)
        diag_report = dashboard_diagnostics.run_diagnostics(
            components=customized_components,
            personalization_applied=personalization_applied,
            render_time_ms=elapsed_ms
        )

        # 6. Constrói a Dashboard Instance a partir do Schema oficial do ADE
        dashboard_layout = DashboardLayoutSchema(
            dashboard_id=uuid.uuid4(),
            tenant_id=tenant_id,
            state="Ready" if not diag_report.get("errors") else "Error",
            grid_layouts=grid_layouts,
            components=customized_components,
            personalization_applied=personalization_applied,
            telemetry=opt_report,
            diagnostics=diag_report,
            created_at=datetime.now(timezone.utc).isoformat()
        )

        # 7. Serializa e sanitiza o payload contra vulnerabilidades XSS (Segurança)
        serialized = dashboard_layout.model_dump(mode="json")
        dashboard_security.sanitize_payload(serialized)

        # 8. Registra Telemetria/Observabilidade
        self._log_telemetry(tenant_id, serialized, elapsed_ms)

        logger.info(
            "[ADE] Layout de Dashboard montado com sucesso em %.2fms | Componentes=%d",
            elapsed_ms,
            len(customized_components)
        )

        return serialized

    def _log_telemetry(self, tenant_id: uuid.UUID, layout_payload: Dict[str, Any], elapsed_ms: float) -> None:
        """Registra logs detalhados para auditoria e observabilidade técnica."""
        telemetry_record = {
            "tenant_id": str(tenant_id),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_ms": elapsed_ms,
            "components_count": len(layout_payload.get("components", [])),
            "health_score": layout_payload.get("diagnostics", {}).get("health_score", 1.0),
            "quality_score": layout_payload.get("diagnostics", {}).get("quality_score", 1.0),
            "fps": layout_payload.get("telemetry", {}).get("fps", 60),
            "layout_cache_status": layout_payload.get("telemetry", {}).get("layout_cache_status", "MISS")
        }
        self._telemetry_history.append(telemetry_record)
        if len(self._telemetry_history) > 500:
            self._telemetry_history.pop(0)

    def get_observability_report(self, tenant_id: uuid.UUID | None = None) -> List[Dict[str, Any]]:
        """Retorna o histórico de telemetria da Engine."""
        if tenant_id:
            tenant_str = str(tenant_id)
            return [t for t in self._telemetry_history if t["tenant_id"] == tenant_str]
        return list(self._telemetry_history)


# Export central singleton
adaptive_dashboard_engine = AdaptiveDashboardEngine()
