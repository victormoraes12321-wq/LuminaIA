"""
Enterprise Component Engine (ECE) — Facade (Synchronous)
---------------------------------------------------------
Ponto de entrada centralizado da camada Enterprise Component Engine. Síncrono.
"""
from __future__ import annotations

import logging
import uuid
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from services.data_platform.enterprise_component_engine.schemas import ComponentSchema
from services.data_platform.enterprise_component_engine.registry import component_registry
from services.data_platform.enterprise_component_engine.factory import ComponentFactory
from services.data_platform.enterprise_component_engine.renderer import component_renderer
from services.data_platform.enterprise_component_engine.state_manager import component_state_manager
from services.data_platform.enterprise_component_engine.lifecycle import component_lifecycle
from services.data_platform.enterprise_component_engine.cache import component_cache
from services.data_platform.enterprise_component_engine.events import component_events
from services.data_platform.enterprise_component_engine.diagnostics import component_diagnostics
from services.data_platform.enterprise_component_engine.security import component_security

logger = logging.getLogger("luminaai.data_platform.enterprise_component_engine")


class EnterpriseComponentEngine:
    """
    Fachada centralizadora do Enterprise Component Engine (ECE). Síncrona.
    """

    def __init__(self):
        # Histórico de telemetria agregada do motor
        self._telemetry_records: List[Dict[str, Any]] = []

    def render_dashboard_layout(
        self,
        tenant_id: uuid.UUID,
        datasets: Dict[str, Dict[str, Any]],
        blueprint: Any,
        visual_strategy: Dict[str, Any] = None,
        theme_name: str = "CORPORATIVO",
        active_filters: Dict[str, Any] = None,
        user_role: str = "USER",
        analytics_results: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Renderiza recursivamente todo o layout de componentes visuais do dashboard de forma síncrona.
        Aplica segurança (Multi-Tenant + XSS), cacheamento e telemetria.
        """
        start_time = time.perf_counter()
        logger.info("[ECE] Iniciando renderização completa do layout para tenant=%s", tenant_id)

        # 1. Verifica se já existe renderização idêntica em cache para evitar custos de render (Component Cache)
        cache_hit = False
        cache_data = {q_id: ds.get("data") for q_id, ds in datasets.items()}
        cached_layout = component_cache.get(tenant_id, "LAYOUT", "DASHBOARD_COMPONENTS", cache_data)
        
        if cached_layout:
            logger.info("[ECE] Cache HIT para layout completo de componentes!")
            # Registra telemetria de reuso
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            self._log_telemetry(
                tenant_id=tenant_id,
                components_count=len(cached_layout),
                elapsed_ms=elapsed_ms,
                cache_hit=True,
                reused_count=len(cached_layout)
            )
            return cached_layout

        # 2. Executa a renderização física via Renderer (Síncrono)
        components = component_renderer.render_components(
            tenant_id=tenant_id,
            datasets=datasets,
            blueprint=blueprint,
            visual_strategy=visual_strategy,
            theme_name=theme_name,
            active_filters=active_filters,
            analytics_results=analytics_results,
        )

        reused_count = 0
        final_serialized = []

        # 3. Processa regras de segurança, estado, ciclo de vida e diagnóstico por componente
        for comp in components:
            # 3.1 Segurança: Valida tenant (isolamento Multi-Tenant) e papéis de acesso
            component_security.validate_tenant_scope(comp, tenant_id)
            component_security.enforce_permissions(comp, user_role)
            component_security.sanitize_component(comp)

            # 3.2 Ciclo de Vida: Transiciona para Mount e executa diagnósticos
            component_lifecycle.trigger_phase(comp, "MOUNT")
            component_diagnostics.run_diagnostics(comp)

            # Se o componente foi reutilizado do catálogo
            if comp.state == "Ready" and comp.diagnostics.get("health_score", 1.0) == 1.0:
                reused_count += 1

            # Serializa para entrega ao Frontend
            final_serialized.append(comp.model_dump(mode="json"))

        # 4. Salva o resultado final no Component Cache
        component_cache.set(tenant_id, "LAYOUT", "DASHBOARD_COMPONENTS", cache_data, final_serialized)

        # 5. Registra telemetria de performance
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        self._log_telemetry(
            tenant_id=tenant_id,
            components_count=len(final_serialized),
            elapsed_ms=elapsed_ms,
            cache_hit=False,
            reused_count=reused_count
        )

        logger.info(
            "[ECE] Renderização finalizada | componentes=%d | reusados=%d | tempo=%dms",
            len(final_serialized),
            reused_count,
            elapsed_ms
        )

        return final_serialized

    def _log_telemetry(
        self,
        tenant_id: uuid.UUID,
        components_count: int,
        elapsed_ms: int,
        cache_hit: bool,
        reused_count: int
    ) -> None:
        """Salva métricas de observabilidade de uso."""
        # Estima tempo economizado de CPU por cache/reuso
        tempo_economizado_ms = 0
        if cache_hit:
            tempo_economizado_ms = max(0, 150 - elapsed_ms)
        elif reused_count > 0:
            tempo_economizado_ms = max(0, (reused_count * 20) - elapsed_ms)

        record = {
            "tenant_id": str(tenant_id),
            "timestamp": datetime.now(timezone.utc).isoformat() if hasattr(datetime, "now") else "",
            "components_count": components_count,
            "elapsed_ms": elapsed_ms,
            "cache_hit": cache_hit,
            "reused_count": reused_count,
            "tempo_economizado_ms": tempo_economizado_ms,
            "fps": 60 if elapsed_ms < 16 else int(1000 / max(1, elapsed_ms)),
            "memory_usage_bytes": components_count * 1024 # Estimativa básica de alocação
        }
        self._telemetry_records.append(record)
        if len(self._telemetry_records) > 500:
            self._telemetry_records.pop(0)

    def get_telemetry_report(self, tenant_id: uuid.UUID | None = None) -> List[Dict[str, Any]]:
        """Retorna o histórico de observabilidade do motor."""
        if tenant_id:
            tenant_str = str(tenant_id)
            return [r for r in self._telemetry_records if r["tenant_id"] == tenant_str]
        return list(self._telemetry_records)


# Export central singleton
enterprise_component_engine = EnterpriseComponentEngine()
