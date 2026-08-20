"""
LuminaAI — Smart Cache Scope, Key, Tag & Generation Contracts
lumina.smart-cache-materialization/1.0
"""
import hashlib
import json
from typing import List, Optional, Dict, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator
from .identity import CacheType


class CacheScopeV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tenant_id: str = Field(min_length=1, max_length=128)
    user_id: Optional[str] = None
    role: str = "CONSULTA"
    permission_fingerprint: str = Field(min_length=16, max_length=128)
    classification_ceiling: str = "INTERNAL"
    locale: str = "pt-BR"
    timezone: str = "America/Sao_Paulo"
    policy_version: str = "v1.0"

    def compute_scope_fingerprint(self) -> str:
        data = {
            "tenant_id": str(self.tenant_id),
            "user_id": str(self.user_id) if self.user_id else None,
            "role": self.role,
            "permission_fingerprint": self.permission_fingerprint,
            "classification_ceiling": self.classification_ceiling,
            "locale": self.locale,
            "timezone": self.timezone,
            "policy_version": self.policy_version,
        }
        serialized = json.dumps(data, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class CacheKeyComponentV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: Literal[
        "presentation_policy_fingerprint",
        "compiler_options_fingerprint",
        "locale_fingerprint",
    ]
    value: str = Field(min_length=16, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")


class CacheKeyV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: str = "lumina.smart-cache-materialization/1.0"
    namespace: str = "lumina"
    cache_type: CacheType
    tenant_id: str
    scope_fingerprint: str
    canonical_query_fingerprint: str
    analytical_catalog_version: str
    metric_fingerprints: List[str]
    filter_structure_fingerprint: str
    canonical_period_fingerprint: str
    tenant_strategy: str
    source_sync_version: str
    source_watermark: str
    validation_policy_version: str
    certification_contract_version: str
    compiler_version: str
    tool_registry_snapshot: str
    generation_counter: int = Field(default=1, ge=0)
    generation_counters: Dict[str, int] = Field(default_factory=dict)
    components: List[CacheKeyComponentV2] = Field(default_factory=list)

    @field_validator("generation_counters")
    @classmethod
    def validate_generations(cls, value: Dict[str, int]) -> Dict[str, int]:
        if any(counter < 0 for counter in value.values()):
            raise ValueError("generation counters must be non-negative")
        return value

    def compute_key_checksum(self) -> str:
        data = {
            "contract_version": self.contract_version,
            "namespace": self.namespace,
            "cache_type": self.cache_type.value,
            "tenant_id": str(self.tenant_id),
            "scope_fingerprint": self.scope_fingerprint,
            "canonical_query_fingerprint": self.canonical_query_fingerprint,
            "analytical_catalog_version": self.analytical_catalog_version,
            "metric_fingerprints": sorted(self.metric_fingerprints),
            "filter_structure_fingerprint": self.filter_structure_fingerprint,
            "canonical_period_fingerprint": self.canonical_period_fingerprint,
            "tenant_strategy": self.tenant_strategy,
            "source_sync_version": self.source_sync_version,
            "source_watermark": self.source_watermark,
            "validation_policy_version": self.validation_policy_version,
            "certification_contract_version": self.certification_contract_version,
            "compiler_version": self.compiler_version,
            "tool_registry_snapshot": self.tool_registry_snapshot,
            "generation_counter": self.generation_counter,
            "generation_counters": dict(sorted(self.generation_counters.items())),
            "components": [{"name": c.name, "value": c.value} for c in self.components],
        }
        serialized = json.dumps(data, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class CacheDependencyTagV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tag_type: str
    tag_value: str

    def format_tag(self) -> str:
        return f"{self.tag_type}:{self.tag_value}"


class CacheGenerationV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tenant_id: str
    target_scope: str
    generation: int = Field(default=1, ge=0)
    reason: str
    updated_at: str
