"""
LuminaAI Governed Validation & Provenance V2 - Facts & Claims Contracts
Version: lumina.validation-provenance/1.0
"""

from typing import Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID

from .identity import ClaimType, CompletenessStatus, FactType, ValidationStatus


class AnalyticalFactValueV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decimal_value: Optional[str] = Field(default=None, description="Decimal as string representation for exact finance math")
    int_value: Optional[int] = Field(default=None)
    string_value: Optional[str] = Field(default=None)
    bool_value: Optional[bool] = Field(default=None)
    date_value: Optional[str] = Field(default=None)
    is_null: bool = Field(default=False)
    raw_type: str = Field(..., description="DECIMAL, INT, STRING, BOOL, DATE, NULL")


class AnalyticalFactV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_id: str = Field(..., description="Stable fact ID (e.g. FACT-001)")
    tenant_id: UUID = Field(...)
    fact_type: FactType = Field(...)
    canonical_metric_id: Optional[str] = Field(default=None)
    canonical_dimension_ids: List[str] = Field(default_factory=list)
    canonical_entity_refs: List[str] = Field(default_factory=list)
    period_start: Optional[str] = Field(default=None)
    period_end: Optional[str] = Field(default=None)
    value: AnalyticalFactValueV2 = Field(...)
    unit: Optional[str] = Field(default=None)
    currency: Optional[str] = Field(default=None)
    scale: int = Field(default=2)
    completeness: CompletenessStatus = Field(default=CompletenessStatus.COMPLETE)
    source_result_ref: str = Field(..., description="Query result checksum or tool invocation ID")
    metric_fingerprint: Optional[str] = Field(default=None)
    tenant_proof_checksum: str = Field(..., description="Proof checksum ensuring tenant authority")
    validation_status: ValidationStatus = Field(default=ValidationStatus.VALID)
    warnings: List[str] = Field(default_factory=list)
    checksum: str = Field(..., description="SHA-256 fact content hash")


class AnalyticalFactSetV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: UUID = Field(...)
    facts: List[AnalyticalFactV2] = Field(default_factory=list)
    fact_set_checksum: str = Field(...)


class AnalyticalClaimV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(..., description="Stable claim ID (e.g. CLAIM-001)")
    claim_type: ClaimType = Field(...)
    text: str = Field(..., description="Subsegment or text assertion")
    fact_references: List[str] = Field(default_factory=list, description="IDs of Supporting AnalyticalFactV2 items")
    metric_references: List[str] = Field(default_factory=list)
    period_references: List[str] = Field(default_factory=list)
    comparison_references: List[str] = Field(default_factory=list)
    qualifiers: List[str] = Field(default_factory=list)
    origin: str = Field(default="MODEL_PROPOSED")
    checksum: str = Field(...)


class AnalyticalClaimBindingV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(...)
    fact_ids: List[str] = Field(default_factory=list)
    validation_status: ValidationStatus = Field(...)
    public_display_value: Optional[str] = Field(default=None)
    canonical_value_checksum: str = Field(...)
    mismatch_reason: Optional[str] = Field(default=None)


class AnalyticalClaimValidationV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claims: List[AnalyticalClaimV2] = Field(default_factory=list)
    bindings: List[AnalyticalClaimBindingV2] = Field(default_factory=list)
    all_numeric_claims_bound: bool = Field(default=True)
    validation_status: ValidationStatus = Field(...)
