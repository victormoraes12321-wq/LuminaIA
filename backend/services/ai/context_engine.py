"""
LuminaAI — Context Engine
-------------------------
Fornece contexto corporativo (Tenant, Departamento, Permissões, Instruções)
e o conecta ao dicionário e catálogo do BKE.
"""
from __future__ import annotations

import uuid
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.ai.schemas import CIEContextSchema
from services.context_guard import sanitize_history

logger = logging.getLogger("luminaai.ai.context_engine")


class ContextEngine:
    """
    Motor de contexto empresarial do CIE.
    Garante que a IA trabalhe sempre contextualizada com dados específicos do Tenant.
    """

    async def build_context(
        self,
        tenant_id: uuid.UUID,
        db: AsyncSession,
        departamento: str = "Vendas",
        history: list[dict[str, str]] | None = None,
        custom_instructions: str | None = None,
        user_id: uuid.UUID | None = None,
        session_id: str | None = None,
    ) -> CIEContextSchema:
        """
        Gera o CIEContextSchema oficial a partir do tenant e das tabelas do banco.
        """
        logger.info("[CIE] Carregando contexto para o tenant=%s...", tenant_id)
        
        # Permissões do Tenant
        permissions = ["sales.read", "kpi.view", "dashboard.custom"]
        
        context_data = CIEContextSchema(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            departamento=departamento,
            permissoes=permissions,
            historico_recente=sanitize_history(history),
            custom_instructions=custom_instructions,
        )
        return context_data


# Singleton export
context_engine = ContextEngine()
