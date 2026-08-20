"""
Enterprise Component Engine (ECE) — Component Cache
---------------------------------------------------
Mecanismo de cache independente a nível de componente para otimização
de performance e reuso reativo de renderizações visuais.
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("luminaai.data_platform.enterprise_component_engine.cache")


class ComponentCache:
    """
    Gerenciador de cache local por componente.
    Garante que renderizações idênticas de dados idênticos não sofram overhead de CPU/memória.
    """

    def __init__(self):
        # Mapeia cache_key -> cache_payload
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _generate_key(self, tenant_id: uuid.UUID, component_type: str, component_name: str, data: Any) -> str:
        """Gera uma chave única e segura baseada no hash MD5 do snapshot de dados e metadados."""
        # Serializa dados de forma consistente para hashing estável
        try:
            data_str = json.dumps(data, sort_keys=True)
        except Exception:
            data_str = str(data)
            
        data_hash = hashlib.md5(data_str.encode("utf-8")).hexdigest()
        name_slug = "".join(c for c in component_name if c.isalnum()).lower()
        return f"{tenant_id}:{component_type.upper()}:{name_slug}:{data_hash}"

    def get(self, tenant_id: uuid.UUID, component_type: str, component_name: str, data: Any) -> Dict[str, Any] | None:
        """
        Tenta obter do cache a última renderização do componente.
        """
        key = self._generate_key(tenant_id, component_type, component_name, data)
        entry = self._cache.get(key)
        
        if entry:
            # TTL de 10 minutos (600 segundos) para cache de renderização de componente
            if (datetime.now(timezone.utc) - entry["timestamp"]).total_seconds() < 600:
                logger.debug("[ComponentCache] HIT para chave: %s", key)
                return copy.deepcopy(entry["payload"])
            else:
                del self._cache[key]
                logger.debug("[ComponentCache] Expirado e removido: %s", key)
        return None

    def set(
        self,
        tenant_id: uuid.UUID,
        component_type: str,
        component_name: str,
        data: Any,
        rendered_payload: Dict[str, Any],
        runtime_version: str = "1.0.0"
    ) -> None:
        """
        Salva em cache o payload da renderização do componente.
        """
        key = self._generate_key(tenant_id, component_type, component_name, data)
        self._cache[key] = {
            "payload": copy.deepcopy(rendered_payload),
            "timestamp": datetime.now(timezone.utc),
            "runtime_version": runtime_version,
            "hash": key.split(":")[-1]
        }
        logger.debug("[ComponentCache] Gravado cache para chave: %s", key)

    def clear(self) -> None:
        """Limpa todo o cache de componentes."""
        self._cache.clear()
        logger.info("[ComponentCache] Todo o cache de componentes foi limpo.")


# Export singleton
component_cache = ComponentCache()
