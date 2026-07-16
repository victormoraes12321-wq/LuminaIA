import logging
import uuid
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from services.data_platform.blueprint_repository import BlueprintRepository
from models.blueprint import Blueprint

logger = logging.getLogger("luminaai.data_platform.blueprint_resolver")

class BlueprintResolver:
    """
    Blueprint Resolver (Blueprint Resolver).
    Responsável por localizar blueprints, layouts, versões e configurações existentes na Data Platform.
    Nunca cria blueprints diretamente.
    """

    def __init__(self, repository: BlueprintRepository):
        self.repository = repository

    async def resolve_blueprint(
        self,
        tenant_id: uuid.UUID,
        view_name: str,
        db_session: AsyncSession,
        blueprint_model: Any | None = None,
    ) -> Blueprint | None:
        """
        Tenta localizar um blueprint compatível para a view informada.
        """
        logger.info(
            "[BlueprintResolver] Buscando blueprint existente para a view: %s (tenant=%s)...",
            view_name,
            str(tenant_id)[:8]
        )
        
        # Busca todos os blueprints do tenant
        db_blueprints = await self.repository.get_all_blueprints(tenant_id, db_session)
        
        # Encontra um blueprint que pertença à mesma view e que possa ser reutilizado
        for bp in db_blueprints:
            if bp.view_name == view_name:
                logger.info(
                    "[BlueprintResolver] Blueprint compatível encontrado! Reutilizando id: %s (v%d)",
                    bp.intent_id,
                    bp.version
                )
                return bp

        if blueprint_model is not None:
            compatible, score = await self.repository.find_compatible_blueprint(
                tenant_id=tenant_id,
                blueprint_model=blueprint_model,
                db_session=db_session,
            )
            if compatible:
                logger.info(
                    "[BlueprintResolver] Blueprint compativel por fingerprint encontrado! id=%s score=%.3f",
                    compatible.intent_id,
                    score,
                )
                return compatible

        logger.info("[BlueprintResolver] Nenhum blueprint correspondente encontrado na Data Platform.")
        return None


from services.data_platform.blueprint_repository import blueprint_repository

blueprint_resolver = BlueprintResolver(blueprint_repository)


async def resolve_blueprint(*args: Any, **kwargs: Any) -> Blueprint | None:
    """Compatibility proxy for legacy package-level imports."""
    return await blueprint_resolver.resolve_blueprint(*args, **kwargs)
