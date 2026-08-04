"""
LuminaAI Governed Validation & Provenance V2 - Temporal & Freshness Validators
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


class TemporalPeriodValidator(GovernedValidator):
    @property
    def validator_id(self) -> str:
        return "temporal_period.v1"

    @property
    def validator_version(self) -> str:
        return "1.0.0"

    @property
    def target_stage(self) -> ValidationStage:
        return ValidationStage.TEMPORAL

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

        if payload.get("period_mismatch", False):
            issues.append(
                ValidationIssueV2(
                    issue_id="ERR_TEMPORAL_PERIOD_MISMATCH",
                    stage=self.target_stage,
                    severity=self.default_severity,
                    message="Result period does not match requested temporal window",
                    validator_id=self.validator_id,
                )
            )

        status = ValidationStatus.VALID if not issues else ValidationStatus.INVALID
        execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        return ValidationCheckResultV2(
            check_id="temporal_period_check",
            validator_id=self.validator_id,
            validator_version=self.validator_version,
            stage=self.target_stage,
            status=status,
            issues=issues,
            execution_time_ms=execution_time_ms,
        )


class SourceFreshnessValidator(GovernedValidator):
    @property
    def validator_id(self) -> str:
        return "source_freshness.v1"

    @property
    def validator_version(self) -> str:
        return "1.0.0"

    @property
    def target_stage(self) -> ValidationStage:
        return ValidationStage.FRESHNESS

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

        if payload.get("is_stale", False):
            issues.append(
                ValidationIssueV2(
                    issue_id="WARN_SOURCE_STALE",
                    stage=self.target_stage,
                    severity=self.default_severity,
                    message="Data source sync version is stale beyond threshold",
                    validator_id=self.validator_id,
                )
            )

        status = ValidationStatus.VALID_WITH_WARNINGS if issues else ValidationStatus.VALID
        execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        return ValidationCheckResultV2(
            check_id="source_freshness_check",
            validator_id=self.validator_id,
            validator_version=self.validator_version,
            stage=self.target_stage,
            status=status,
            issues=issues,
            execution_time_ms=execution_time_ms,
        )
