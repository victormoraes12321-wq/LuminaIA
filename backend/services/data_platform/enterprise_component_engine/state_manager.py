"""
Enterprise Component Engine (ECE) — Component State Manager
------------------------------------------------------------
Controla e audita transições de estado individuais para cada componente visual.
Garante que componentes não compartilhem estados e previne estados inválidos.
"""
from __future__ import annotations

import logging
from typing import Set

from services.data_platform.enterprise_component_engine.schemas import ComponentSchema

logger = logging.getLogger("luminaai.data_platform.enterprise_component_engine.state_manager")


class ComponentStateManager:
    """
    Máquina de estados independente para componentes visuais.
    """

    # Lista oficial de estados permitidos
    VALID_STATES: Set[str] = {
        "Loading",
        "Ready",
        "Updating",
        "Expanded",
        "Collapsed",
        "Selected",
        "Filtered",
        "Error",
        "Offline",
        "Empty",
        "Refreshing",
        "Destroyed",
    }

    @classmethod
    def transition_state(cls, component: ComponentSchema, new_state: str) -> None:
        """
        Transiciona o estado do componente para o novo valor, aplicando regras de controle.
        Garante isolamento: cada componente possui seu próprio objeto de estado.
        """
        if new_state not in cls.VALID_STATES:
            logger.error("[StateManager] Tentativa de transição para estado inválido: %s", new_state)
            raise ValueError(f"Estado '{new_state}' não é reconhecido pelo Enterprise Component Engine.")

        # Regra de Segurança: Componentes destruídos não podem mais mudar de estado
        if component.state == "Destroyed":
            logger.warning("[StateManager] Recusada transição de componente já destruído (id=%s)", component.id)
            raise RuntimeError("Não é possível alterar o estado de um componente já destruído.")

        # Registra a transição no log de auditoria do componente
        prev_state = component.state
        component.state = new_state
        
        # Registra histórico de transição nos diagnósticos do componente
        if "state_history" not in component.diagnostics:
            component.diagnostics["state_history"] = []
        
        component.diagnostics["state_history"].append({
            "from": prev_state,
            "to": new_state,
            "timestamp": component.created_at
        })

        logger.debug(
            "[StateManager] Componente id=%s transicionou: %s -> %s",
            component.id,
            prev_state,
            new_state,
        )


# Export singleton
component_state_manager = ComponentStateManager()
