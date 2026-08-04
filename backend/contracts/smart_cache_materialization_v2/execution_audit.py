"""
LuminaAI — Smart Cache Execution & Audit Contracts
lumina.smart-cache-materialization/1.0
"""
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, ConfigDict, JsonValue
from .identity import CacheType, CacheDecision, FreshnessStatus, InvalidationScope
from .scope_key import CacheScopeV2, CacheKeyV2
from .entries import CacheEntryV2
from .eligibility import CacheEligibilityRequestV2


class CacheLookupRequestV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scope: CacheScopeV2
    cache_type: CacheType
    canonical_query_fingerprint: str
    analytical_catalog_version: str
    metric_fingerprints: List[str]
    filter_structure_fingerprint: str = ""
    canonical_period_fingerprint: str = ""
    source_sync_version: str = ""
    source_watermark: str = ""
    validation_policy_version: str = "v1.0"
    certification_contract_version: str = "lumina.validation-provenance/1.0"
    compiler_version: str = "v1"
    tool_registry_snapshot: str = "v1"
    generation_counters: Dict[str, int] = Field(default_factory=dict)


class CacheLookupResultV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: CacheDecision
    reason_code: str
    cache_key_checksum: str
    entry: Optional[CacheEntryV2] = None
    freshness: FreshnessStatus = FreshnessStatus.UNKNOWN
    lookup_latency_ms: float = 0.0


class CacheWriteRequestV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scope: CacheScopeV2
    cache_key: CacheKeyV2
    payload: Dict[str, JsonValue]
    certification_id: str
    tenant_proof_id: str
    eligibility: CacheEligibilityRequestV2
    dependency_tags: List[str] = Field(default_factory=list)


class CacheWriteResultV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    success: bool
    entry_id: Optional[str] = None
    cache_key_checksum: str
    reason_code: str
    payload_size_bytes: int = 0


class CacheInvalidationRequestV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    invalidation_scope: InvalidationScope
    target_identifier: Optional[str] = None
    reason: str = Field(min_length=1, max_length=256)


class CacheInvalidationResultV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    success: bool
    invalidated_count: int
    tenant_id: str
    invalidation_scope: InvalidationScope


class CacheGarbageCollectionRequestV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dry_run: bool = True
    limit: int = Field(default=100, ge=1, le=1000)
    cursor: Optional[str] = None


class CacheEvictionResultV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    evicted_count: int
    bytes_freed: int
    dry_run: bool
    next_cursor: Optional[str] = None


class CacheStatisticsV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tenant_id: str
    total_lookups: int = 0
    hit_count: int = 0
    miss_count: int = 0
    bypass_count: int = 0
    stale_count: int = 0
    hit_rate: float = 0.0
    active_entries_count: int = 0
    active_payload_bytes: int = 0
    active_leases_count: int = 0
    published_materializations_count: int = 0


class CacheAuditEventV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str
    tenant_id: str
    event_type: str
    cache_key_checksum: Optional[str] = None
    user_id: Optional[str] = None
    decision: Optional[str] = None
    reason_code: str
    details: Dict[str, JsonValue] = Field(default_factory=dict)
    timestamp: str


class MaterializationStatisticsV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tenant_id: str
    total_definitions: int = 0
    published_definitions: int = 0
    stale_snapshots: int = 0
    total_builds: int = 0
    successful_builds: int = 0
    failed_builds: int = 0
