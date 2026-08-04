"""
LuminaAI Governed Validation & Provenance V2 - Certification & Audit Contracts
Version: lumina.validation-provenance/1.0
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID

from .facts_claims import AnalyticalClaimValidationV2, AnalyticalFactV2
from .identity import ValidationSeverity, ValidationStatus
from .provenance import PublicProvenanceSummaryV2


class ResultCertificationV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    certification_id: UUID = Field(...)
    tenant_id: UUID = Field(...)
    request_id: str = Field(...)
    result_checksum: str = Field(...)
    query_fingerprint: Optional[str] = Field(default=None)
    tenant_proof_checksum: str = Field(...)
    status: ValidationStatus = Field(...)
    certified_at: str = Field(...)
    checksum: str = Field(...)


class ResponseCertificationV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    certification_id: UUID = Field(...)
    result_certification_id: UUID = Field(...)
    tenant_id: UUID = Field(...)
    request_id: str = Field(...)
    response_draft_checksum: str = Field(...)
    claim_validation: AnalyticalClaimValidationV2 = Field(...)
    status: ValidationStatus = Field(...)
    certified_at: str = Field(...)
    checksum: str = Field(...)


class CertificationEnvelopeV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str = Field(default="lumina.validation-provenance/1.0")
    certification_id: UUID = Field(...)
    tenant_id: UUID = Field(...)
    user_id: UUID = Field(...)
    request_id: str = Field(...)
    orchestration_run_id: Optional[str] = Field(default=None)
    result_certification: ResultCertificationV2 = Field(...)
    response_certification: ResponseCertificationV2 = Field(...)
    facts: List[AnalyticalFactV2] = Field(default_factory=list)
    public_summary: PublicProvenanceSummaryV2 = Field(...)
    overall_status: ValidationStatus = Field(...)
    warnings: List[str] = Field(default_factory=list)
    critical_issues: List[str] = Field(default_factory=list)
    policy_version: str = Field(default="1.0.0")
    validator_versions: Dict[str, str] = Field(default_factory=dict)
    superseded_by_id: Optional[UUID] = Field(default=None)
    created_at: str = Field(...)
    checksum: str = Field(...)


class ValidationAuditEventV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID = Field(...)
    tenant_id: UUID = Field(...)
    user_id: UUID = Field(...)
    event_type: str = Field(...)
    certification_id: Optional[UUID] = Field(default=None)
    severity: ValidationSeverity = Field(default=ValidationSeverity.INFO)
    message: str = Field(...)
    details: Dict[str, str] = Field(default_factory=dict)
    created_at: str = Field(...)


class ValidationEvaluationCaseV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(...)
    name: str = Field(...)
    input_payload: Dict = Field(...)
    expected_status: ValidationStatus = Field(...)
    expected_issues: List[str] = Field(default_factory=list)


class ValidationEvaluationResultV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evaluation_id: UUID = Field(...)
    cases_run: int = Field(...)
    passed_count: int = Field(...)
    failed_count: int = Field(...)
    accuracy_percentage: float = Field(...)
    evaluated_at: str = Field(...)
