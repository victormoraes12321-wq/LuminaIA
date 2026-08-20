"""
LuminaAI — Governed Materialization Contracts
lumina.smart-cache-materialization/1.0
"""
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator
from .identity import (
    CertificationStatus,
    DataClassification,
    MaterializationBuildStatus,
    MaterializationType,
    MaterializationLifecycle,
    FreshnessStatus,
    RefreshTrigger,
)


class MaterializationSourceV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset: str
    relation_references: List[str]
    metric_fingerprints: List[str]
    catalog_version: str
    source_sync_version: str
    watermark: str
    tenant_strategy: str = "ISOLATED_ANALYTICAL_CLONE"


class MaterializationQueryV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    canonical_query_spec_id: str
    metrics: List[str]
    dimensions: List[str]
    filters_fingerprint: str
    time_window_fingerprint: str


class MaterializationDefinitionV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: str = "lumina.smart-cache-materialization/1.0"
    definition_id: str
    tenant_id: str
    canonical_name: str
    materialization_type: MaterializationType
    query: MaterializationQueryV2
    source: MaterializationSourceV2
    classification: str = "INTERNAL"
    lifecycle: MaterializationLifecycle = MaterializationLifecycle.DRAFT
    version: int = Field(default=1, ge=1)
    lock_version: int = Field(default=1, ge=1)
    created_at: str
    updated_at: str
    checksum: str

    @model_validator(mode="after")
    def reject_unsafe_definition(self) -> "MaterializationDefinitionV2":
        if self.materialization_type in {
            MaterializationType.ROW_LEVEL_DETAIL,
            MaterializationType.FORBIDDEN,
        }:
            raise ValueError("row-level or forbidden materializations are not allowed")
        if self.classification in {
            DataClassification.PII.value,
            DataClassification.SECRET.value,
            DataClassification.FORBIDDEN.value,
        }:
            raise ValueError("restricted classification cannot be materialized")
        return self


class MaterializationSnapshotV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot_id: str
    definition_id: str
    tenant_id: str
    version: int = Field(ge=1)
    row_count: int = Field(ge=0)
    fact_count: int = Field(ge=0)
    payload_size_bytes: int = Field(ge=0)
    certification_id: str
    certification_status: CertificationStatus = CertificationStatus.VALID
    tenant_proof_id: str
    watermark: str
    source_sync_version: str
    payload_checksum: str
    freshness: FreshnessStatus = FreshnessStatus.FRESH
    built_at: str
    expires_at: Optional[str] = None
    checksum: str


class MaterializationBuildV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    build_id: str
    definition_id: str
    tenant_id: str
    version: int = Field(ge=1)
    status: MaterializationBuildStatus
    error_code: Optional[str] = None
    build_duration_ms: float = Field(default=0.0, ge=0)
    snapshot_id: Optional[str] = None
    started_at: str
    completed_at: Optional[str] = None


class MaterializationPublicationV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    publication_id: str
    definition_id: str
    tenant_id: str
    active_snapshot_id: str
    published_by: str
    published_at: str
    previous_snapshot_id: Optional[str] = None
    lock_version: int = Field(default=1, ge=1)


class MaterializationRefreshV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    refresh_id: str
    definition_id: str
    tenant_id: str
    trigger: RefreshTrigger
    new_snapshot_id: str
    refreshed_at: str


class MaterializationRollbackV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rollback_id: str
    definition_id: str
    tenant_id: str
    from_snapshot_id: str
    to_snapshot_id: str
    rolled_back_by: str
    rolled_back_at: str
