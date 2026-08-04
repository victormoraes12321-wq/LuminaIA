"""
LuminaAI Governed Validation & Provenance V2 - Fact & Claim Validators
Version: lumina.validation-provenance/1.0
"""

import time
from typing import Dict, List, Optional

from contracts.validation_provenance_v2 import (
    ValidationCheckResultV2,
    ValidationContextV2,
    ValidationIssueV2,
    ValidationSeverity,
    ValidationStage,
    ValidationStatus,
)
from .base import GovernedValidator


class FactReferenceValidator(GovernedValidator):
    @property
    def validator_id(self) -> str:
        return "fact_reference.v1"

    @property
    def validator_version(self) -> str:
        return "1.0.0"

    @property
    def target_stage(self) -> ValidationStage:
        return ValidationStage.CLAIMS

    @property
    def default_severity(self) -> ValidationSeverity:
        return ValidationSeverity.CRITICAL

    async def validate(
        self,
        context: ValidationContextV2,
        payload: Dict,
        proposed_facts: List[Dict],
        proposed_claims: List[Dict],
        tenant_proof: Optional[Dict] = None,
    ) -> ValidationCheckResultV2:
        start_time = time.perf_counter()
        issues: List[ValidationIssueV2] = []

        valid_fact_ids = {str(f.get("fact_id")) for f in proposed_facts if f.get("fact_id")}
        for fact in proposed_facts:
            if not fact.get("source_result_ref"):
                issues.append(
                    ValidationIssueV2(
                        issue_id="ERR_FACT_WITHOUT_SOURCE",
                        stage=self.target_stage,
                        severity=self.default_severity,
                        message=f"Analytical fact '{fact.get('fact_id')}' has no source result reference",
                        validator_id=self.validator_id,
                    )
                )

        fact_requiring_claim_types = {"NUMERIC", "COMPARATIVE", "TEMPORAL", "RANKING", "COMPLETENESS"}
        for claim in proposed_claims:
            ctype = str(claim.get("claim_type", "")).upper()
            fact_refs = claim.get("fact_references", [])
            if ctype in fact_requiring_claim_types:
                if not fact_refs:
                    issues.append(
                        ValidationIssueV2(
                            issue_id="ERR_NUMERIC_CLAIM_WITHOUT_FACT",
                            stage=self.target_stage,
                            severity=self.default_severity,
                            message=f"Claim '{claim.get('claim_id')}' of type '{ctype}' requires supporting fact references",
                            validator_id=self.validator_id,
                        )
                    )
                else:
                    for fref in fact_refs:
                        if str(fref) not in valid_fact_ids:
                            issues.append(
                                ValidationIssueV2(
                                    issue_id="ERR_CLAIM_FACT_REF_INVALID",
                                    stage=self.target_stage,
                                    severity=self.default_severity,
                                    message=f"Claim '{claim.get('claim_id')}' references non-existent fact '{fref}'",
                                    validator_id=self.validator_id,
                                )
                            )

        status = ValidationStatus.VALID if not issues else ValidationStatus.BLOCKED
        execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        return ValidationCheckResultV2(
            check_id="fact_reference_check",
            validator_id=self.validator_id,
            validator_version=self.validator_version,
            stage=self.target_stage,
            status=status,
            issues=issues,
            execution_time_ms=execution_time_ms,
        )


class ClaimValueConsistencyValidator(GovernedValidator):
    @property
    def validator_id(self) -> str:
        return "claim_value_consistency.v1"

    @property
    def validator_version(self) -> str:
        return "1.0.0"

    @property
    def target_stage(self) -> ValidationStage:
        return ValidationStage.CLAIMS

    @property
    def default_severity(self) -> ValidationSeverity:
        return ValidationSeverity.ERROR

    async def validate(
        self,
        context: ValidationContextV2,
        payload: Dict,
        proposed_facts: List[Dict],
        proposed_claims: List[Dict],
        tenant_proof: Optional[Dict] = None,
    ) -> ValidationCheckResultV2:
        start_time = time.perf_counter()
        issues: List[ValidationIssueV2] = []

        if payload.get("invented_number_detected", False) or payload.get("claim_mismatch", False):
            issues.append(
                ValidationIssueV2(
                    issue_id="ERR_CLAIM_VALUE_MISMATCH",
                    stage=self.target_stage,
                    severity=self.default_severity,
                    message="Text claim value or percentage diverges from analytical fact value",
                    validator_id=self.validator_id,
                )
            )

        status = ValidationStatus.VALID if not issues else ValidationStatus.INVALID
        execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        return ValidationCheckResultV2(
            check_id="claim_value_consistency_check",
            validator_id=self.validator_id,
            validator_version=self.validator_version,
            stage=self.target_stage,
            status=status,
            issues=issues,
            execution_time_ms=execution_time_ms,
        )
