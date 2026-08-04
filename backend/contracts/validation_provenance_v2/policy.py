"""
LuminaAI Governed Validation & Provenance V2 - Policy Contracts
Version: lumina.validation-provenance/1.0
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID

from .identity import ValidationSeverity, ValidationStage


class ValidationPolicyVersionV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(default="1.0.0", description="Policy semver string")
    contract_version: str = Field(default="lumina.validation-provenance/1.0")
    author: str = Field(..., description="Author user ID or system identifier")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    checksum: str = Field(..., description="SHA-256 policy contents hash")


class ValidatorDefinitionV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    validator_id: str = Field(..., description="Unique validator identifier (e.g. tenant_proof.v1)")
    validator_version: str = Field(..., description="Validator implementation version")
    stage: ValidationStage = Field(..., description="Target validation stage")
    criticality: ValidationSeverity = Field(default=ValidationSeverity.ERROR)
    enabled: bool = Field(default=True)
    params: Dict[str, str] = Field(default_factory=dict)


class ValidationPolicyV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: UUID = Field(..., description="Unique policy UUID")
    tenant_id: UUID = Field(..., description="Tenant owner ID")
    policy_name: str = Field(..., description="Human readable policy name")
    version_info: ValidationPolicyVersionV2 = Field(...)
    required_stages: List[ValidationStage] = Field(
        default_factory=lambda: list(ValidationStage)
    )
    validators: List[ValidatorDefinitionV2] = Field(default_factory=list)
    fail_fast_on_critical: bool = Field(default=True)
    allow_partial_results: bool = Field(default=False)
    require_fact_bindings_for_numeric_claims: bool = Field(default=True)
    strict_decimal_precision: bool = Field(default=True)
    freshness_tolerance_seconds: int = Field(default=86400)
    is_active: bool = Field(default=True)
