"""
LuminaAI — Smart Cache & Governed Materialization V2 Policy Contracts
lumina.smart-cache-materialization/1.0
"""
from typing import List, Dict
from pydantic import BaseModel, Field, ConfigDict, field_validator
from .identity import CacheType, MaterializationType, FreshnessStatus


class SmartCachePolicyV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: str = Field(default="lumina.smart-cache-materialization/1.0")
    policy_id: str = Field(default="default_cache_policy")
    policy_version: str = Field(default="v1.0")
    default_ttl_seconds: Dict[str, int] = Field(
        default_factory=lambda: {
            CacheType.METADATA.value: 86400,
            CacheType.CONTRACT_SCHEMA.value: 86400,
            CacheType.POLICY.value: 3600,
            CacheType.TOOL_CATALOG.value: 3600,
            CacheType.ANALYTICAL_CATALOG.value: 1800,
            CacheType.SEMANTIC_METADATA.value: 1800,
            CacheType.COMPILED_PLAN.value: 3600,
            CacheType.CERTIFIED_ANALYTICAL_RESULT.value: 900,
            CacheType.CERTIFICATION_ENVELOPE.value: 900,
            CacheType.PUBLIC_PROVENANCE.value: 1800,
            CacheType.DETERMINISTIC_PRESENTATION.value: 1800,
            CacheType.NEGATIVE_METADATA.value: 60,
        }
    )
    allow_stale_serving: bool = Field(default=False)
    stale_soft_grace_seconds: int = Field(default=300)
    max_payload_bytes: int = Field(default=10485760, ge=1, le=10485760)
    single_flight_lease_ttl_seconds: int = Field(default=30, ge=1, le=300)
    allow_valid_with_warnings: bool = Field(default=False)
    enable_cache_read: bool = Field(default=True)
    enable_cache_write: bool = Field(default=True)
    enable_materialization_read: bool = Field(default=True)
    enable_materialization_build: bool = Field(default=True)
    disallowed_cache_types: List[CacheType] = Field(
        default_factory=lambda: [CacheType.FORBIDDEN]
    )
    disallowed_materialization_types: List[MaterializationType] = Field(
        default_factory=lambda: [MaterializationType.ROW_LEVEL_DETAIL, MaterializationType.FORBIDDEN]
    )

    @field_validator("default_ttl_seconds")
    @classmethod
    def validate_governed_ttls(cls, value: Dict[str, int]) -> Dict[str, int]:
        if not value or any(ttl < 1 or ttl > 86400 for ttl in value.values()):
            raise ValueError("cache TTLs must be governed values between 1 and 86400 seconds")
        if CacheType.FORBIDDEN.value in value:
            raise ValueError("FORBIDDEN cache type cannot receive a TTL")
        return value


class MaterializationPolicyV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: str = Field(default="lumina.smart-cache-materialization/1.0")
    policy_id: str = Field(default="default_materialization_policy")
    policy_version: str = Field(default="v1.0")
    allow_incremental_builds: bool = Field(default=True)
    require_watermark_verification: bool = Field(default=True)
    max_snapshots_per_definition: int = Field(default=10, ge=2, le=100)
    auto_refresh_after_sync: bool = Field(default=True)
    forbid_row_level_snapshots: bool = Field(default=True)
    forbid_pii_fields: bool = Field(default=True)
