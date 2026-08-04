"""
LuminaAI Governed Validation & Provenance V2 - Numeric & Comparison Validators
Version: lumina.validation-provenance/1.0
"""

import math
import time
from decimal import Decimal
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


class DecimalValidator(GovernedValidator):
    @property
    def validator_id(self) -> str:
        return "decimal_precision.v1"

    @property
    def validator_version(self) -> str:
        return "1.0.0"

    @property
    def target_stage(self) -> ValidationStage:
        return ValidationStage.NUMERIC

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

        if payload.get("uses_raw_float", False):
            issues.append(
                ValidationIssueV2(
                    issue_id="ERR_RAW_FLOAT_USED_FOR_FINANCE",
                    stage=self.target_stage,
                    severity=self.default_severity,
                    message="Financial numbers must use Decimal representations instead of raw floats",
                    validator_id=self.validator_id,
                )
            )

        status = ValidationStatus.VALID if not issues else ValidationStatus.INVALID
        execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        return ValidationCheckResultV2(
            check_id="decimal_precision_check",
            validator_id=self.validator_id,
            validator_version=self.validator_version,
            stage=self.target_stage,
            status=status,
            issues=issues,
            execution_time_ms=execution_time_ms,
        )


class NumericFiniteValueValidator(GovernedValidator):
    @property
    def validator_id(self) -> str:
        return "numeric_finite.v1"

    @property
    def validator_version(self) -> str:
        return "1.0.0"

    @property
    def target_stage(self) -> ValidationStage:
        return ValidationStage.NUMERIC

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

        if payload.get("has_inf_or_nan", False):
            issues.append(
                ValidationIssueV2(
                    issue_id="ERR_NUMERIC_INF_OR_NAN",
                    stage=self.target_stage,
                    severity=self.default_severity,
                    message="Numerical results must contain finite numbers (no Inf/NaN)",
                    validator_id=self.validator_id,
                )
            )

        status = ValidationStatus.VALID if not issues else ValidationStatus.INVALID
        execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        return ValidationCheckResultV2(
            check_id="numeric_finite_check",
            validator_id=self.validator_id,
            validator_version=self.validator_version,
            stage=self.target_stage,
            status=status,
            issues=issues,
            execution_time_ms=execution_time_ms,
        )


class ComparisonOperandsValidator(GovernedValidator):
    @property
    def validator_id(self) -> str:
        return "comparison_operands.v1"

    @property
    def validator_version(self) -> str:
        return "1.0.0"

    @property
    def target_stage(self) -> ValidationStage:
        return ValidationStage.COMPARISON

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

        if payload.get("comparison_missing_baseline", False):
            issues.append(
                ValidationIssueV2(
                    issue_id="ERR_COMPARISON_MISSING_BASELINE",
                    stage=self.target_stage,
                    severity=self.default_severity,
                    message="Comparison payload requires explicit baseline operand",
                    validator_id=self.validator_id,
                )
            )

        status = ValidationStatus.VALID if not issues else ValidationStatus.INVALID
        execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        return ValidationCheckResultV2(
            check_id="comparison_operands_check",
            validator_id=self.validator_id,
            validator_version=self.validator_version,
            stage=self.target_stage,
            status=status,
            issues=issues,
            execution_time_ms=execution_time_ms,
        )


class ComparisonDeltaValidator(GovernedValidator):
    @property
    def validator_id(self) -> str:
        return "comparison_delta.v1"

    @property
    def validator_version(self) -> str:
        return "1.0.0"

    @property
    def target_stage(self) -> ValidationStage:
        return ValidationStage.COMPARISON

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

        if "baseline" in payload and "target" in payload and "delta" in payload:
            try:
                base = Decimal(str(payload["baseline"]))
                tgt = Decimal(str(payload["target"]))
                dlta = Decimal(str(payload["delta"]))
                expected_delta = tgt - base
                if abs(expected_delta - dlta) > Decimal("0.01"):
                    issues.append(
                        ValidationIssueV2(
                            issue_id="ERR_COMPARISON_DELTA_MISMATCH",
                            stage=self.target_stage,
                            severity=self.default_severity,
                            message=f"Delta {dlta} does not match target ({tgt}) - baseline ({base}) = {expected_delta}",
                            validator_id=self.validator_id,
                        )
                    )
            except Exception as ex:
                issues.append(
                    ValidationIssueV2(
                        issue_id="ERR_COMPARISON_DELTA_INVALID",
                        stage=self.target_stage,
                        severity=self.default_severity,
                        message=f"Failed to parse comparison delta operands: {ex}",
                        validator_id=self.validator_id,
                    )
                )

        status = ValidationStatus.VALID if not issues else ValidationStatus.INVALID
        execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        return ValidationCheckResultV2(
            check_id="comparison_delta_check",
            validator_id=self.validator_id,
            validator_version=self.validator_version,
            stage=self.target_stage,
            status=status,
            issues=issues,
            execution_time_ms=execution_time_ms,
        )


class ComparisonPercentageValidator(GovernedValidator):
    @property
    def validator_id(self) -> str:
        return "comparison_percentage.v1"

    @property
    def validator_version(self) -> str:
        return "1.0.0"

    @property
    def target_stage(self) -> ValidationStage:
        return ValidationStage.COMPARISON

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

        if payload.get("percentage_mismatch", False):
            issues.append(
                ValidationIssueV2(
                    issue_id="ERR_COMPARISON_PERCENTAGE_MISMATCH",
                    stage=self.target_stage,
                    severity=self.default_severity,
                    message="Comparison percentage mismatch detected against operands",
                    validator_id=self.validator_id,
                )
            )

        status = ValidationStatus.VALID if not issues else ValidationStatus.INVALID
        execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        return ValidationCheckResultV2(
            check_id="comparison_percentage_check",
            validator_id=self.validator_id,
            validator_version=self.validator_version,
            stage=self.target_stage,
            status=status,
            issues=issues,
            execution_time_ms=execution_time_ms,
        )
