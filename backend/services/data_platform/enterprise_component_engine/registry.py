"""
Enterprise Component Engine (ECE) — Registry (Synchronous)
-----------------------------------------------------------
Catálogo oficial e governado de componentes visuais.
Garante que componentes não sejam duplicados e estejam em conformidade.
"""
from __future__ import annotations

import logging
import uuid
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.data_platform.enterprise_component_engine.schemas import ComponentSchema

logger = logging.getLogger("luminaai.data_platform.enterprise_component_engine.registry")


class ComponentRegistry:
    """
    Mantém o registro centralizado de todos os tipos de componentes instanciados
    ou disponíveis no runtime do LuminaAI. Thread-safe e síncrono.
    """

    def __init__(self):
        # Mapeia component_id -> ComponentSchema
        self._components: Dict[uuid.UUID, ComponentSchema] = {}
        # Lock de concorrência síncrono
        self._lock = threading.Lock()

    def register(self, component: ComponentSchema) -> ComponentSchema:
        """
        Registra um componente no catálogo oficial.
        Lança ValueError se já existir um componente com o mesmo nome na mesma categoria e tenant.
        """
        with self._lock:
            # Valida duplicidade por nome + categoria no escopo do Tenant
            for existing in list(self._components.values()):
                if (
                    existing.tenant_id == component.tenant_id
                    and existing.name.lower() == component.name.lower()
                    and existing.category.lower() == component.category.lower()
                ):
                    logger.warning(
                        "[ComponentRegistry] Componente duplicado recusado: name=%s | category=%s",
                        component.name,
                        component.category,
                    )
                    raise ValueError(
                        f"Componente '{component.name}' já registrado na categoria '{component.category}'."
                    )

            self._components[component.id] = component
            logger.info(
                "[ComponentRegistry] Componente registrado: id=%s | name=%s | category=%s | type=%s | tenant=%s",
                component.id,
                component.name,
                component.category,
                component.type,
                component.tenant_id,
            )
            return component

    def get(self, component_id: uuid.UUID, tenant_id: uuid.UUID) -> ComponentSchema | None:
        """
        Retorna um componente do catálogo, garantindo o isolamento Multi-Tenant.
        """
        component = self._components.get(component_id)
        if component and component.tenant_id == tenant_id:
            return component
        return None

    def list_components(self, tenant_id: uuid.UUID, category: str | None = None) -> List[ComponentSchema]:
        """
        Lista todos os componentes registrados para um determinado Tenant.
        """
        components = [c for c in list(self._components.values()) if c.tenant_id == tenant_id]
        if category:
            cat_lower = category.lower()
            components = [c for c in components if c.category.lower() == cat_lower]
        return components

    def unregister(self, component_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        """
        Remove um componente do catálogo oficial.
        """
        with self._lock:
            component = self._components.get(component_id)
            if component and component.tenant_id == tenant_id:
                del self._components[component_id]
                logger.info("[ComponentRegistry] Componente removido: id=%s | tenant=%s", component_id, tenant_id)
                return True
            return False

    def clear(self) -> None:
        """Limpa todo o catálogo (útil para testes unitários)."""
        self._components.clear()


# Export central singleton
component_registry = ComponentRegistry()
