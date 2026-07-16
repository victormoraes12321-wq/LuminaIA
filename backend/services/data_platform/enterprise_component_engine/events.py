"""
Enterprise Component Engine (ECE) — Component Events
---------------------------------------------------
Gerenciador de assinaturas e disparos de eventos para componentes visuais.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from services.data_platform.enterprise_component_engine.schemas import ComponentSchema

logger = logging.getLogger("luminaai.data_platform.enterprise_component_engine.events")


class ComponentEvents:
    """
    Controla o vinculo de ações do frontend (callbacks declarados)
    sobre os componentes visuais, garantindo isolamento de assinaturas.
    """

    @staticmethod
    def bind_event(component: ComponentSchema, event_name: str, action_url: str) -> None:
        """
        Associa uma ação ou webhook à assinatura do evento do componente.
        """
        if event_name not in component.allowed_events:
            logger.warning(
                "[ComponentEvents] Evento '%s' não suportado pelo tipo de componente %s (id=%s)",
                event_name,
                component.type,
                component.id,
            )
            raise ValueError(f"Evento '{event_name}' não é permitido para componentes do tipo {component.type}.")

        # Registra a assinatura nas interações do componente
        if "events" not in component.interaction_config:
            component.interaction_config["events"] = {}

        component.interaction_config["events"][event_name] = action_url
        logger.info(
            "[ComponentEvents] Evento registrado: id=%s | evento=%s | acao=%s",
            component.id,
            event_name,
            action_url,
        )

    @staticmethod
    def trigger_event(component: ComponentSchema, event_name: str, context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Simula/executa um disparo de evento, auditando a conformidade de dados
        e retornando as configurações necessárias de callback para o frontend.
        """
        if event_name not in component.allowed_events:
            raise ValueError(f"Evento '{event_name}' não é permitido para o componente {component.name}.")

        registered_action = component.interaction_config.get("events", {}).get(event_name)

        # Log do disparo
        logger.info(
            "[ComponentEvents] Evento disparado: id=%s | evento=%s | acao_registrada=%s",
            component.id,
            event_name,
            registered_action
        )

        return {
            "component_id": str(component.id),
            "event": event_name,
            "action_url": registered_action,
            "timestamp": component.created_at,
            "context_data": context_data or {}
        }


# Export singleton
component_events = ComponentEvents()
