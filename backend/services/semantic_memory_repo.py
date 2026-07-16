import logging
import uuid
import json
from datetime import datetime
from typing import Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from models.semantic_memory import SemanticMemory

logger = logging.getLogger("luminaai.services.semantic_memory_repo")

async def get_semantic_memory_record(db: AsyncSession, tenant_id: uuid.UUID, text_clean: str) -> SemanticMemory | None:
    """Busca um registro de memória semântica ativo para a expressão limpa."""
    try:
        stmt = select(SemanticMemory).where(
            and_(
                SemanticMemory.tenant_id == tenant_id,
                SemanticMemory.expressao == text_clean
            )
        ).order_by(SemanticMemory.frequencia.desc()).limit(1)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()
    except Exception as exc:
        logger.error("[SemanticMemoryRepo] Erro ao buscar memória semântica: %s", exc)
        return None

async def increment_memory_frequencia(db: AsyncSession, memory: SemanticMemory) -> None:
    """Incrementa a frequência de uso de um registro de memória semântica."""
    try:
        memory.frequencia += 1
        db.add(memory)
        await db.commit()
    except Exception as exc:
        logger.error("[SemanticMemoryRepo] Erro ao incrementar frequência da memória: %s", exc)

async def create_semantic_memory_record(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    text_clean: str,
    objeto_resolvido: dict[str, Any],
    score: float,
    confianca: str,
    origem: str
) -> None:
    """Cria e persiste um novo registro de aprendizado semântico."""
    try:
        new_mem = SemanticMemory(
            tenant_id=tenant_id,
            expressao=text_clean,
            objeto_resolvido=objeto_resolvido,
            score=score,
            confianca=confianca,
            origem=origem
        )
        db.add(new_mem)
        await db.commit()
        logger.info("[SemanticMemoryRepo] Novo aprendizado semântico persistido: %r", text_clean)
    except Exception as exc:
        logger.error("[SemanticMemoryRepo] Erro ao persistir aprendizado semântico: %s", exc)
