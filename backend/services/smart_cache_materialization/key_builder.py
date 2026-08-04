"""
LuminaAI — Smart Cache Key Builder
lumina.smart-cache-materialization/1.0
"""
from typing import List, Optional, Dict
from contracts.smart_cache_materialization_v2 import (
    CacheScopeV2,
    CacheKeyV2,
    CacheKeyComponentV2,
    CacheType,
)


class SmartCacheKeyBuilder:
    @staticmethod
    def build_key(
        *,
        cache_type: CacheType,
        scope: CacheScopeV2,
        canonical_query_fingerprint: str,
        analytical_catalog_version: str,
        metric_fingerprints: List[str],
        filter_structure_fingerprint: str = "",
        canonical_period_fingerprint: str = "",
        tenant_strategy: str = "ISOLATED_ANALYTICAL_CLONE",
        source_sync_version: str = "v1",
        source_watermark: str = "unknown",
        validation_policy_version: str = "v1.0",
        certification_contract_version: str = "lumina.validation-provenance/1.0",
        compiler_version: str = "v1",
        tool_registry_snapshot: str = "v1",
        generation_counter: int = 1,
        generation_counters: Optional[Dict[str, int]] = None,
        additional_components: Optional[List[CacheKeyComponentV2]] = None,
    ) -> CacheKeyV2:
        scope_fingerprint = scope.compute_scope_fingerprint()

        components = additional_components or []

        cache_key = CacheKeyV2(
            cache_type=cache_type,
            tenant_id=str(scope.tenant_id),
            scope_fingerprint=scope_fingerprint,
            canonical_query_fingerprint=canonical_query_fingerprint,
            analytical_catalog_version=analytical_catalog_version,
            metric_fingerprints=sorted(metric_fingerprints),
            filter_structure_fingerprint=filter_structure_fingerprint,
            canonical_period_fingerprint=canonical_period_fingerprint,
            tenant_strategy=tenant_strategy,
            source_sync_version=source_sync_version,
            source_watermark=source_watermark,
            validation_policy_version=validation_policy_version,
            certification_contract_version=certification_contract_version,
            compiler_version=compiler_version,
            tool_registry_snapshot=tool_registry_snapshot,
            generation_counter=generation_counter,
            generation_counters=generation_counters or {},
            components=components,
        )

        return cache_key
