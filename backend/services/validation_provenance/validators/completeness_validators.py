"""
LuminaAI Governed Validation & Provenance V2 - Completeness & Truncation Validators
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


class CompletenessValidator(GovernedValidator):
    @property
    def validator_id(self) -> str:
        return "completeness.v1"

    @property
    def validator_version(self) -> str:
        return "1.0.0"

    @property
    def target_stage(self) -> ValidationStage:
        return ValidationStage.COMPLETENESS

    @property
    def default_severity(self) -> ValidationSeverity:
        return ValidationSeverity.WARNING

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

        is_partial = payload.get("is_partial", False)
        if is_partial:
            issues.append(
                ValidationIssueV2(
                    issue_id="WARN_RESULT_PARTIAL",
                    stage=self.target_stage,
                    severity=self.default_severity,
                    message="Result is partial and does not include all requested scope",
                    validator_id=self.validator_id,
                )
            )

        status = ValidationStatus.PARTIAL if is_partial else ValidationStatus.VALID
        execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        return ValidationCheckResultV2(
            check_id="completeness_check",
            validator_id=self.validator_id,
            validator_version=self.validator_version,
            stage=self.target_stage,
            status=status,
            issues=issues,
            execution_time_ms=execution_time_ms,
        )


class TruncationValidator(GovernedValidator):
    @property
    def validator_id(self) -> str:
        return "truncation.v1"

    @property
    def validator_version(self) -> str:
        return "1.0.0"

    @property
    def target_stage(self) -> ValidationStage:
        return ValidationStage.COMPLETENESS

    @property
    def default_severity(self) -> ValidationSeverity:
        return ValidationSeverity.WARNING

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

        is_truncated = payload.get("truncated", False) or payload.get("is_truncated", False)
        if is_truncated:
            issues.append(
                ValidationIssueV2(
                    issue_id="WARN_RESULT_TRUNCATED",
                    stage=self.target_stage,
                    severity=self.default_severity,
                    message="Result rows were truncated due to row limit policies",
                    validator_id=self.validator_id,
                )
            )

        status = ValidationStatus.VALID_WITH_WARNINGS if is_truncated else ValidationStatus.VALID
        execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        return ValidationCheckResultV2(
            check_id="truncation_check",
            validator_id=self.validator_id,
            validator_version=self.validator_version,
            stage=self.target_stage,
            status=status,
            issues=issues,
            execution_time_ms=execution_time_ms,
        )
