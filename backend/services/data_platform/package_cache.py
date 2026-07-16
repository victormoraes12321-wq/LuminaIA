"""
LuminaAI — Package Cache Intelligence (ICP integrated)
------------------------------------------------------
Encaminha as operações do cache de Analytical Packages para a
Intelligent Caching Platform (ICP) global, mantendo a interface
antiga totalmente funcional e compatível.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from services.cache_service import global_cache

logger = logging.getLogger("luminaai.data_platform.package_cache")

_L1_TTL_SECONDS = 300
_L1_MAX_PER_TENANT = 20

class _CacheEntry:
    """Mantido apenas para compatibilidade de import com testes unitários antigos."""
    __slots__ = ("package_data", "expires_at")

    def __init__(self, package_data: dict[str, Any], ttl: float = _L1_TTL_SECONDS):
        self.package_data = package_data
        import time
        self.expires_at = time.monotonic() + ttl

    @property
    def is_expired(self) -> bool:
        import time
        return time.monotonic() > self.expires_at

class PackageCacheIntelligence:
    """
    Wrapper de compatibilidade que mapeia o cache de Analytical Packages
    para a Intelligent Caching Platform (ICP) global sob o namespace 'package'.
    """

    def __init__(self) -> None:
        self._l1: dict[str, dict[str, Any]] = {}

    def l1_get(self, tenant_id: uuid.UUID, intent_key: str) -> dict[str, Any] | None:
        """Tenta recuperar o Package do cache L1 local ou ICP global."""
        tenant_str = str(tenant_id)
        tenant_cache = self._l1.get(tenant_str, {})
        entry = tenant_cache.get(intent_key)
        if entry is not None:
            if hasattr(entry, 'is_expired') and entry.is_expired:
                tenant_cache.pop(intent_key, None)
                return None
            if hasattr(entry, 'package_data'):
                return entry.package_data
            return entry

        val = global_cache.get(tenant_id, "package", intent_key)
        if val:
            logger.debug("[PackageCache L1 -> ICP] HIT | tenant=%s key=%s", tenant_id, intent_key[:12])
            return val
        return None

    def l1_set(
        self,
        tenant_id: uuid.UUID,
        intent_key: str,
        package_data: dict[str, Any],
        ttl: float = _L1_TTL_SECONDS,
    ) -> None:
        """Armazena o Package no cache L1 local e no ICP global."""
        tenant_str = str(tenant_id)
        if tenant_str not in self._l1:
            self._l1[tenant_str] = {}
        
        self._l1[tenant_str][intent_key] = package_data

        global_cache.set(
            tenant_id=tenant_id,
            namespace="package",
            key_hash=intent_key,
            value=package_data,
            ttl_seconds=int(ttl),
            cost_ms=300.0,
            dependencies=package_data.get("view_names", [])
        )
        logger.debug("[PackageCache L1 -> ICP] SET | tenant=%s key=%s", tenant_id, intent_key[:12])

    def l1_invalidate(self, tenant_id: uuid.UUID, intent_key: str | None = None) -> None:
        """Invalida as entradas correspondentes localmente e no ICP global."""
        tenant_str = str(tenant_id)
        if tenant_str in self._l1:
            if intent_key is None:
                self._l1.pop(tenant_str, None)
            else:
                self._l1[tenant_str].pop(intent_key, None)

        if intent_key is None:
            global_cache.clear_namespace(tenant_id, "package")
            logger.info("[PackageCache L1 -> ICP] INVALIDATED tenant=%s (all)", tenant_id)
        else:
            global_cache.clear_pattern(f"{tenant_id}:package:{intent_key}")
            logger.debug("[PackageCache L1 -> ICP] INVALIDATED tenant=%s key=%s", tenant_id, intent_key[:12])

    def l1_invalidate_by_view(self, tenant_id: uuid.UUID, view_name: str) -> None:
        """Invalida as entradas baseadas em dependência de view no ICP global."""
        tenant_str = str(tenant_id)
        tenant_cache = self._l1.get(tenant_str, {})
        if tenant_cache:
            keys_to_remove = []
            for key, entry in tenant_cache.items():
                pkg_data = entry.package_data if hasattr(entry, 'package_data') else entry
                if isinstance(pkg_data, dict):
                    view_names = pkg_data.get("view_names", [])
                    if view_name in view_names:
                        keys_to_remove.append(key)
            for key in keys_to_remove:
                tenant_cache.pop(key, None)

        global_cache.invalidate_by_dependency(view_name)
        logger.info("[PackageCache L1 -> ICP] INVALIDATED por dependência de view %r | tenant=%s", view_name, tenant_id)

    def get_stats(self) -> dict[str, Any]:
        """Retorna estatísticas delegadas do ICP global."""
        stats = global_cache.get_statistics()
        return {
            "l1_total_entries": stats["active_items"],
            "l1_expired_entries": 0,
            "l1_active_entries": stats["active_items"],
            "l1_tenants": stats["items_by_namespace"].get("package", 0),
            "l1_ttl_seconds": _L1_TTL_SECONDS,
            "l1_max_per_tenant": _L1_MAX_PER_TENANT,
        }

# Singleton export
package_cache = PackageCacheIntelligence()
