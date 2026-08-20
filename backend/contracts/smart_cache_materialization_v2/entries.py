"""
LuminaAI — Smart Cache Entry & Lease Contracts
lumina.smart-cache-materialization/1.0
"""
import hashlib
import json
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, ConfigDict, JsonValue
from .identity import CacheType, CacheEntryStatus, FreshnessStatus


class CacheEntryMetadataV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entry_id: str
    tenant_id: str
    cache_type: CacheType
    cache_key_checksum: str
    scope_fingerprint: str
    permission_fingerprint: str
    query_fingerprint: str
    metric_fingerprints: List[str]
    source_sync_version: str
    source_watermark: str
    validation_policy_version: str
    compiler_version: str
    tool_registry_snapshot: str
    certification_id: Optional[str] = None
    tenant_proof_id: Optional[str] = None
    created_at: str
    expires_at: str
    generation: int = Field(default=1, ge=0)
    hit_count: int = Field(default=0, ge=0)
    payload_size_bytes: int = Field(default=0, ge=0)
    classification: str = "INTERNAL"


class CacheEntryPayloadReferenceV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    payload_id: str
    payload_checksum: str
    payload_data: Dict[str, JsonValue]


class CacheEntryV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: str = "lumina.smart-cache-materialization/1.0"
    metadata: CacheEntryMetadataV2
    payload_ref: CacheEntryPayloadReferenceV2
    dependency_tags: List[str] = Field(default_factory=list)
    status: CacheEntryStatus = CacheEntryStatus.ACTIVE
    freshness: FreshnessStatus = FreshnessStatus.FRESH
    entry_checksum: str

    def verify_checksum(self) -> bool:
        payload_serialized = json.dumps(
            self.payload_ref.payload_data,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        payload_checksum = hashlib.sha256(payload_serialized.encode("utf-8")).hexdigest()
        if payload_checksum != self.payload_ref.payload_checksum:
            return False
        data = {
            "contract_version": self.contract_version,
            "entry_id": self.metadata.entry_id,
            "tenant_id": self.metadata.tenant_id,
            "cache_key_checksum": self.metadata.cache_key_checksum,
            "payload_checksum": self.payload_ref.payload_checksum,
            "generation": self.metadata.generation,
        }
        serialized = json.dumps(data, sort_keys=True)
        computed = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return computed == self.entry_checksum


class CacheLeaseV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    lease_id: str
    tenant_id: str
    cache_key_checksum: str
    owner_token_checksum: str
    acquired_at: str
    expires_at: str
    lock_version: int = Field(default=1, ge=1)
    status: str = "HELD"
