"""
Enterprise Component Engine (ECE) — Component Security
-------------------------------------------------------
Aplica barreiras de segurança e higienização para componentes.
Garante proteção multi-tenant, sanitização XSS e integridade de eventos.
"""
from __future__ import annotations

import html
import logging
import uuid
from typing import Any, Dict

from services.data_platform.enterprise_component_engine.schemas import ComponentSchema

logger = logging.getLogger("luminaai.data_platform.enterprise_component_engine.security")


class ComponentSecurity:
    """
    Portão de segurança para sanitização e validação multi-tenant de componentes.
    """

    @staticmethod
    def validate_tenant_scope(component: ComponentSchema, tenant_id: uuid.UUID) -> None:
        """
        Valida que o componente pertence ao Tenant do contexto atual.
        Lança ScopeViolationError se houver tentativa de acesso cruzado.
        """
        if component.tenant_id != tenant_id:
            logger.critical(
                "[Security Alert] Tentativa de invasão detectada! Componente tenant=%s acessado por tenant=%s",
                component.tenant_id,
                tenant_id,
            )
            # Lança o erro de escopo oficial do LuminaAI
            from services.context_guard import ScopeViolationError
            raise ScopeViolationError("Acesso cruzado de dados de empresas não é permitido.")

    @staticmethod
    def enforce_permissions(component: ComponentSchema, user_role: str) -> None:
        """
        Valida se o papel do usuário (role) possui permissões cadastradas no componente.
        """
        role_upper = user_role.upper()
        if component.permissions and role_upper not in [p.upper() for p in component.permissions]:
            logger.warning("[Security] Usuário com papel %s teve acesso recusado ao componente %s", user_role, component.id)
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não possui permissões suficientes para visualizar este componente."
            )

    @classmethod
    def sanitize_component(cls, component: ComponentSchema) -> None:
        """
        Previne injeção XSS sanitizando todas as strings de entrada do título e descrição
        do componente, incluindo dados sensíveis.
        """
        # Sanitiza campos principais
        component.name = html.escape(component.name)
        component.description = html.escape(component.description)

        # Sanitiza recursivamente strings de dados no snapshot
        if component.data_snapshot:
            component.data_snapshot = cls._sanitize_value(component.data_snapshot)

        # Sanitiza eventos para evitar injeção de manipuladores JavaScript
        events = component.interaction_config.get("events", {})
        for ev, action in list(events.items()):
            if "javascript:" in action.lower() or "<script" in action.lower():
                logger.warning("[Security] Detectada tentativa de injeção de script em evento: %s", action)
                del events[ev]

        logger.debug("[Security] Componente id=%s sanitizado com sucesso", component.id)

    @classmethod
    def _sanitize_value(cls, val: Any) -> Any:
        """Sanitiza recursivamente strings para evitar XSS."""
        if isinstance(val, str):
            return html.escape(val)
        elif isinstance(val, dict):
            return {k: cls._sanitize_value(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [cls._sanitize_value(item) for item in val]
        return val


# Export singleton
component_security = ComponentSecurity()
