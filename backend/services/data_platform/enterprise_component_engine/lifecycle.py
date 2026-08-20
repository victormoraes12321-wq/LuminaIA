"""
Enterprise Component Engine (ECE) — Component Lifecycle
--------------------------------------------------------
Controla as transições do ciclo de vida físico do componente
e emite eventos correspondentes para auditoria técnica.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List

from services.data_platform.enterprise_component_engine.schemas import ComponentSchema
from services.data_platform.enterprise_component_engine.state_manager import component_state_manager

logger = logging.getLogger("luminaai.data_platform.enterprise_component_engine.lifecycle")


class ComponentLifecycle:
    """
    Rastreia a jornada de um componente visando auditar o tempo de vida,
    garantindo que hooks de eventos registrem todas as etapas lógicas.
    """

    # Fases físicas oficiais do Ciclo de Vida
    LIFECYCLE_PHASES = {
        "CREATE",
        "INITIALIZE",
        "MOUNT",
        "UPDATE",
        "REFRESH",
        "RESIZE",
        "PAUSE",
        "RESUME",
        "DESTROY",
    }

    @classmethod
    def trigger_phase(cls, component: ComponentSchema, phase: str, metadata: Dict[str, Any] = None) -> None:
        """
        Garante a passagem de fase no ciclo de vida físico do componente.
        Sincroniza automaticamente o estado de dados de diagnóstico.
        """
        phase_upper = phase.upper()
        if phase_upper not in cls.LIFECYCLE_PHASES:
            raise ValueError(f"Fase de ciclo de vida '{phase_upper}' inválida.")

        metadata = metadata or {}

        # Log de auditoria interna do componente
        if "lifecycle_events" not in component.diagnostics:
            component.diagnostics["lifecycle_events"] = []

        event_entry = {
            "phase": phase_upper,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata
        }
        component.diagnostics["lifecycle_events"].append(event_entry)

        # Trata transições de estado implícitas da fase
        if phase_upper == "CREATE":
            component_state_manager.transition_state(component, "Loading")
        elif phase_upper == "INITIALIZE":
            component_state_manager.transition_state(component, "Ready")
        elif phase_upper == "UPDATE":
            component_state_manager.transition_state(component, "Updating")
        elif phase_upper == "REFRESH":
            component_state_manager.transition_state(component, "Refreshing")
        elif phase_upper == "DESTROY":
            component_state_manager.transition_state(component, "Destroyed")

        logger.info(
            "[ComponentLifecycle] Componente id=%s | Fase=%s | Estado=%s",
            component.id,
            phase_upper,
            component.state
        )


# Export singleton
component_lifecycle = ComponentLifecycle()
