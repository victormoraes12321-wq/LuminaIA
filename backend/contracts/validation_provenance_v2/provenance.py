"""
LuminaAI Governed Validation & Provenance V2 - Provenance & Graph Contracts
Version: lumina.validation-provenance/1.0
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID

from .identity import ProvenanceEdgeType, ProvenanceNodeType, ValidationStatus


class ProvenanceNodeV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(..., description="Unique node ID in graph")
    tenant_id: UUID = Field(...)
    node_type: ProvenanceNodeType = Field(...)
    label: str = Field(...)
    reference_id: str = Field(..., description="External entity ID or checksum")
    metadata: Dict[str, str] = Field(default_factory=dict)
    checksum: str = Field(...)


class ProvenanceEdgeV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edge_id: str = Field(...)
    tenant_id: UUID = Field(...)
    source_node_id: str = Field(...)
    target_node_id: str = Field(...)
    edge_type: ProvenanceEdgeType = Field(...)
    checksum: str = Field(...)


class ProvenanceGraphV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    graph_id: UUID = Field(...)
    tenant_id: UUID = Field(...)
    nodes: List[ProvenanceNodeV2] = Field(default_factory=list)
    edges: List[ProvenanceEdgeV2] = Field(default_factory=list)
    has_cycles: bool = Field(default=False)
    orphan_node_ids: List[str] = Field(default_factory=list)
    checksum: str = Field(...)


class ProvenanceManifestV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest_id: UUID = Field(...)
    tenant_id: UUID = Field(...)
    request_id: str = Field(...)
    graph_checksum: str = Field(...)
    fact_count: int = Field(...)
    claim_count: int = Field(...)
    created_at: str = Field(...)
    manifest_checksum: str = Field(...)


class PublicProvenanceSummaryV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str = Field(default="lumina.validation-provenance/1.0")
    metric_names: List[str] = Field(default_factory=list)
    period_description: Optional[str] = Field(default=None)
    applied_filters: List[str] = Field(default_factory=list)
    data_source_description: str = Field(default="PostgreSQL Clone Analítico Governado")
    source_last_updated: Optional[str] = Field(default=None)
    validation_status: ValidationStatus = Field(...)
    warnings: List[str] = Field(default_factory=list)
    truncated: bool = Field(default=False)
    certification_checksum: str = Field(...)


class InternalProvenanceSummaryV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest: ProvenanceManifestV2 = Field(...)
    graph: ProvenanceGraphV2 = Field(...)
    canonical_metric_ids: List[str] = Field(default_factory=list)
    formula_fingerprints: List[str] = Field(default_factory=list)
    query_fingerprints: List[str] = Field(default_factory=list)
    tenant_proof_checksums: List[str] = Field(default_factory=list)
