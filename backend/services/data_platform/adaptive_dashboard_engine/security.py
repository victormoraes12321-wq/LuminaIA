"""
Adaptive Dashboard Engine (ADE) — Security Layer
-------------------------------------------------
Enforca limites de Multi-Tenant, sanitização XSS e integridade de estado
para o layout unificado de Dashboards.
"""
from __future__ import annotations

import html
import logging
import uuid
from typing import Any, Dict, List
from fastapi import HTTPException, status

logger = logging.getLogger("luminaai.data_platform.adaptive_dashboard_engine.security")


class DashboardSecurity:
    """
    Guarda de segurança que bloqueia vazamento de dados corporativos
    e limpa injeções de tags HTML/scripts.
    """

    @staticmethod
    def validate_tenant_isolation(dashboard_tenant_id: uuid.UUID, target_tenant_id: uuid.UUID) -> None:
        """
        Garante que o Tenant solicitante possui acesso exclusivo a este dashboard.
        Lança ScopeViolationError se houver tentativa de invasão lateral.
        """
        if dashboard_tenant_id != target_tenant_id:
            logger.critical(
                "[Security Alert] Invasão lateral recusada! Tenant=%s tentou ler recursos do Tenant=%s",
                target_tenant_id,
                dashboard_tenant_id
            )
            from services.context_guard import ScopeViolationError
            raise ScopeViolationError("Tentativa não autorizada de cruzamento de dados de empresas.")

    @staticmethod
    def enforce_role_access(user_role: str, required_roles: List[str] = None) -> None:
        """
        Valida que o papel do usuário é autorizado a ver o painel.
        """
        required_roles = required_roles or ["USER", "MANAGER", "ADMIN"]
        role_upper = user_role.upper()
        if role_upper not in [r.upper() for r in required_roles]:
            logger.warning("[Security] Usuário com role %s teve acesso negado à dashboard", user_role)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado: privilégios insuficientes para visualizar este painel."
            )

    @classmethod
    def sanitize_payload(cls, payload: Dict[str, Any]) -> None:
        """
        Sanitiza recursivamente todas as strings de dados do layout final,
        prevenindo injeções XSS e injeção de manipuladores JavaScript nos eventos.
        """
        for k, v in list(payload.items()):
            payload[k] = cls._sanitize_value(v)

    @classmethod
    def _sanitize_value(cls, val: Any) -> Any:
        """Limpa dados recursivamente contra tags scripts e injeções."""
        if isinstance(val, str):
            escaped = html.escape(val)
            # Remove assinaturas js perigosas
            if "javascript:" in escaped.lower() or "onclick" in escaped.lower():
                return ""
            return escaped
        elif isinstance(val, dict):
            return {k: cls._sanitize_value(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [cls._sanitize_value(item) for item in val]
        return val


# Export singleton
dashboard_security = DashboardSecurity()
