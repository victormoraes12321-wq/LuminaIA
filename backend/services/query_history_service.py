"""Query history persistence service.

Routers expose HTTP contracts; persistence belongs to the service layer so the
Query Intelligence Engine does not need to import a router module.
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from database import get_db_context
from models.search_history import SearchHistory

logger = logging.getLogger("luminaai.query_history_service")


async def persist_query_history(
    user_id: uuid.UUID,
    view_catalog_id: uuid.UUID | None,
    pergunta: str,
    parametros: dict[str, str],
    confianca: float | None,
    tempo_ms: int,
) -> None:
    """Persist a query history record without affecting the user response."""
    try:
        async with get_db_context() as session:
            historico = SearchHistory(
                user_id=user_id,
                view_catalog_id=view_catalog_id,
                pergunta_texto=pergunta,
                parametros_extraidos=parametros,
                ia_confianca=Decimal(str(round(confianca, 4))) if confianca is not None else None,
                tempo_resposta_ms=tempo_ms,
            )
            session.add(historico)

        logger.info(
            "Historico persistido | user=%s | view=%s | tempo=%dms",
            str(user_id)[:8],
            str(view_catalog_id)[:8] if view_catalog_id else "N/A",
            tempo_ms,
        )
    except Exception:
        logger.exception(
            "Falha ao persistir historico (nao afeta o usuario) | user=%s",
            str(user_id)[:8],
        )
