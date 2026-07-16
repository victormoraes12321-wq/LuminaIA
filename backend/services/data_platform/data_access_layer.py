import logging
import uuid
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from services.data_platform.analytical_storage import AnalyticalStorage
from services.data_platform.performance_layer import PerformanceLayer
from models.tenant import Tenant

logger = logging.getLogger("luminaai.data_platform.data_access_layer")


def _get_catalog_api():
    from services.data_platform.catalog_api import catalog_api
    return catalog_api


class DataAccessLayer:
    """
    Data Access Layer (DAL).
    Única camada autorizada a ler dados da Data Platform.
    Garante o isolamento multi-tenant, segurança, cache e paginação.
    """

    def __init__(self, analytical_storage: AnalyticalStorage, performance_layer: PerformanceLayer):
        self.analytical_storage = analytical_storage
        self.performance_layer = performance_layer

    async def read_view_data(
        self,
        tenant: Tenant,
        view_name: str,
        parameters: dict[str, Any],
        db_session: AsyncSession,
        use_cache: bool = True,
        ttl_seconds: int = 300
    ) -> list[dict[str, Any]]:
        """
        Lê dados de uma view analítica na Data Platform com isolamento multi-tenant,
        cache de performance e validações de segurança.
        """
        tenant_id = tenant.id
        logger.info(
            "[DataAccessLayer] Solicitada leitura da view: %s | Tenant: %s",
            view_name,
            str(tenant_id)[:8]
        )
        
        # 1. Segurança e Isolamento Multi-Tenant
        # Garante que os parâmetros sempre herdem e respeitem o tenant_id
        parameters = dict(parameters)
        parameters["tenant_id"] = str(tenant_id)
        
        # 2. Cache (Performance Layer)
        import json
        import hashlib
        param_hash = hashlib.sha256(json.dumps(parameters, sort_keys=True).encode()).hexdigest()
        cache_key = f"view_data:{view_name}:{param_hash}"
        
        if use_cache:
            cached_data = self.performance_layer.get_cache(tenant_id, "data_layer", cache_key)
            if cached_data is not None:
                logger.info("[DataAccessLayer] [CACHE HIT] Dados recuperados da Performance Layer para view: %s", view_name)
                try:
                    await _get_catalog_api().update_cache(
                        tenant_id=tenant_id,
                        estrutura_id=view_name,
                        ativo=True,
                        ttl_segundos=ttl_seconds,
                        hit_rate=1.0,
                    )
                except Exception as cache_meta_exc:
                    logger.debug("[DataAccessLayer] Metadata de cache ignorado: %s", cache_meta_exc)
                return cached_data
                
        # 3. Leitura Física do Analytical Storage (Data Platform PostgreSQL/Demo)
        try:
            raw_data = await self.analytical_storage.execute_view(
                tenant=tenant,
                view_name=view_name,
                parameters=parameters,
                db_session=db_session
            )
            
            # Paginação (se o limite estiver nos parâmetros)
            limite = parameters.get("limite")
            if limite:
                try:
                    lim = int(limite)
                    raw_data = raw_data[:lim]
                except ValueError:
                    pass
            
            # Grava no Cache se a leitura deu certo
            if use_cache and raw_data:
                self.performance_layer.set_cache(
                    tenant_id=tenant_id,
                    namespace="data_layer",
                    key=cache_key,
                    value=raw_data,
                    ttl_seconds=ttl_seconds
                )
                try:
                    await _get_catalog_api().update_cache(
                        tenant_id=tenant_id,
                        estrutura_id=view_name,
                        ativo=True,
                        ttl_segundos=ttl_seconds,
                    )
                except Exception as cache_meta_exc:
                    logger.debug("[DataAccessLayer] Metadata de cache ignorado: %s", cache_meta_exc)
                
            return raw_data
        except Exception as exc:
            logger.error("[DataAccessLayer] Falha ao ler dados da view %s: %s", view_name, exc)
            raise exc
