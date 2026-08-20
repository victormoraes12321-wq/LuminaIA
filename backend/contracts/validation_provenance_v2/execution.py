"""
LuminaAI Governed Validation & Provenance V2 - Execution & Request Contracts
Version: lumina.validation-provenance/1.0
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID

from .identity import ValidationSeverity, ValidationStage, ValidationStatus


class ValidationEvidenceReferenceV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref_type: str = Field(..., description="Type of evidence ref (e.g. QUERY_FINGERPRINT, TENANT_PROOF)")
    ref_id: str = Field(..., description="Reference ID or hash string")
    metadata: Dict[str, str] = Field(default_factory=dict)


class ValidationEvidenceV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: UUID = Field(..., description="Evidence UUID")
    tenant_id: UUID = Field(..., description="Tenant ID")
    stage: ValidationStage = Field(...)
    references: List[ValidationEvidenceReferenceV2] = Field(default_factory=list)
    checksum: str = Field(..., description="SHA-256 evidence payload hash")


class ValidationAuthorityReferenceV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authority_type: str = Field(..., description="MetricRegistry, EnterpriseKnowledge, TemporalNormalizer, etc.")
    canonical_id: str = Field(..., description="Canonical ID or key")
    version_fingerprint: str = Field(..., description="Fingerprint/checksum of authority state")


class ValidationIssueV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_id: str = Field(..., description="Unique issue code (e.g. ERR_TENANT_MISMATCH)")
    stage: ValidationStage = Field(...)
    severity: ValidationSeverity = Field(...)
    message: str = Field(..., description="Human readable description")
    field_path: Optional[str] = Field(default=None)
    validator_id: str = Field(...)
    evidence_ref: Optional[str] = Field(default=None)


class ValidationCheckResultV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_id: str = Field(..., description="Check code or name")
    validator_id: str = Field(...)
    validator_version: str = Field(...)
    stage: ValidationStage = Field(...)
    status: ValidationStatus = Field(...)
    issues: List[ValidationIssueV2] = Field(default_factory=list)
    execution_time_ms: float = Field(default=0.0)


class ValidationStageResultV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: ValidationStage = Field(...)
    status: ValidationStatus = Field(...)
    checks: List[ValidationCheckResultV2] = Field(default_factory=list)
    issues: List[ValidationIssueV2] = Field(default_factory=list)
    execution_time_ms: float = Field(default=0.0)


class ValidationContextV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: UUID = Field(...)
    user_id: UUID = Field(...)
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    session_id: Optional[str] = Field(default=None)
    request_id: str = Field(...)
    orchestration_run_id: Optional[str] = Field(default=None)
    policy_version: str = Field(default="1.0.0")


class ValidationRequestV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context: ValidationContextV2 = Field(...)
    result_payload: Dict = Field(..., description="Analytical result payload to validate")
    response_draft_text: Optional[str] = Field(default=None)
    proposed_facts: List[Dict] = Field(default_factory=list)
    proposed_claims: List[Dict] = Field(default_factory=list)
    tenant_proof: Optional[Dict] = Field(default=None)


class ValidationRunV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: UUID = Field(...)
    tenant_id: UUID = Field(...)
    user_id: UUID = Field(...)
    request_id: str = Field(...)
    orchestration_run_id: Optional[str] = Field(default=None)
    overall_status: ValidationStatus = Field(...)
    stage_results: List[ValidationStageResultV2] = Field(default_factory=list)
    total_execution_time_ms: float = Field(default=0.0)
    created_at: str = Field(...)
    checksum: str = Field(...)
