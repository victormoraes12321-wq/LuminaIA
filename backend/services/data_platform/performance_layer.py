import logging
import uuid
from typing import Any
from services.cache_service import global_cache

logger = logging.getLogger("luminaai.data_platform.performance_layer")

class PerformanceLayer:
    """
    Módulo Performance Layer.
    Responsável por cache, reuso, otimizações e monitoramento de tempo de resposta.
    Nunca armazena regras de negócio.
    """

    def get_cache(self, tenant_id: uuid.UUID, namespace: str, key: str) -> Any | None:
        """Recupera dados do cache global."""
        try:
            return global_cache.get(tenant_id, namespace, key)
        except Exception as exc:
            logger.error("Erro ao obter dados da Performance Layer (Cache): %s", exc)
            return None

    def set_cache(self, tenant_id: uuid.UUID, namespace: str, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """Salva dados no cache global."""
        try:
            global_cache.set(tenant_id, namespace, key, value, ttl_seconds=ttl_seconds)
        except Exception as exc:
            logger.error("Erro ao gravar dados na Performance Layer (Cache): %s", exc)
