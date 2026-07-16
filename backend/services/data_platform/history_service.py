import logging
import uuid
from typing import Any
from sqlalchemy import select
from models.data_platform_history import DataPlatformHistory
from database import get_db_context

logger = logging.getLogger("luminaai.data_platform.history_service")

class HistoryService:
    """
    Serviço centralizado para persistência e auditoria de mudanças estruturais na Data Platform.
    Registra e recupera logs históricos de forma isolada por tenant.
    """

    async def log_change(
        self,
        tenant_id: uuid.UUID,
        estrutura_tipo: str, # 'VIEW', 'BLUEPRINT', 'DATASET', 'METADADOS'
        estrutura_id: str,
        acao: str, # 'CREATE', 'UPDATE', 'RECONSTRUCT', 'VERSION_UP'
        detalhes: dict[str, Any]
    ) -> DataPlatformHistory:
        """Registra um evento de modificação estrutural de forma imutável."""
        logger.info(
            "[HistoryService] Gravando log histórico | tenant=%s | tipo=%s | acao=%s",
            str(tenant_id)[:8],
            estrutura_tipo,
            acao
        )
        
        async with get_db_context() as session:
            log_entry = DataPlatformHistory(
                tenant_id=tenant_id,
                estrutura_tipo=estrutura_tipo,
                estrutura_id=estrutura_id,
                acao=acao,
                detalhes=detalhes
            )
            session.add(log_entry)
            await session.flush()
            # Retorna uma cópia desacoplada
            return log_entry

    async def get_history(
        self,
        tenant_id: uuid.UUID,
        estrutura_tipo: str | None = None
    ) -> list[DataPlatformHistory]:
        """Recupera o log histórico do tenant, filtrando opcionalmente por tipo."""
        async with get_db_context() as session:
            stmt = select(DataPlatformHistory).where(
                DataPlatformHistory.tenant_id == tenant_id
            )
            if estrutura_tipo:
                stmt = stmt.where(DataPlatformHistory.estrutura_tipo == estrutura_tipo)
            
            stmt = stmt.order_by(DataPlatformHistory.criado_em.desc())
            res = await session.execute(stmt)
            return list(res.scalars().all())

# Singleton export
history_service = HistoryService()
