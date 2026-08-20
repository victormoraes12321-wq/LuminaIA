"""
LuminaAI Governed Validation & Provenance V2 - Contract & Shape Validators
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


class ContractValidator(GovernedValidator):
    @property
    def validator_id(self) -> str:
        return "contract.v1"

    @property
    def validator_version(self) -> str:
        return "1.0.0"

    @property
    def target_stage(self) -> ValidationStage:
        return ValidationStage.CONTRACT

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

        if not isinstance(payload, dict):
            issues.append(
                ValidationIssueV2(
                    issue_id="ERR_CONTRACT_PAYLOAD_NOT_DICT",
                    stage=self.target_stage,
                    severity=self.default_severity,
                    message="Payload must be a valid JSON dictionary",
                    validator_id=self.validator_id,
                )
            )

        status = ValidationStatus.VALID if not issues else ValidationStatus.INVALID
        execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        return ValidationCheckResultV2(
            check_id="contract_structure_check",
            validator_id=self.validator_id,
            validator_version=self.validator_version,
            stage=self.target_stage,
            status=status,
            issues=issues,
            execution_time_ms=execution_time_ms,
        )


class ResultShapeValidator(GovernedValidator):
    @property
    def validator_id(self) -> str:
        return "result_shape.v1"

    @property
    def validator_version(self) -> str:
        return "1.0.0"

    @property
    def target_stage(self) -> ValidationStage:
        return ValidationStage.SHAPE

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

        data_rows = payload.get("data", payload.get("rows", []))
        if not isinstance(data_rows, list):
            issues.append(
                ValidationIssueV2(
                    issue_id="ERR_SHAPE_INVALID_ROWS",
                    stage=self.target_stage,
                    severity=self.default_severity,
                    message="Data rows must be a list",
                    validator_id=self.validator_id,
                )
            )

        status = ValidationStatus.VALID if not issues else ValidationStatus.INVALID
        execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        return ValidationCheckResultV2(
            check_id="result_shape_check",
            validator_id=self.validator_id,
            validator_version=self.validator_version,
            stage=self.target_stage,
            status=status,
            issues=issues,
            execution_time_ms=execution_time_ms,
        )


class DuplicateKeyValidator(GovernedValidator):
    @property
    def validator_id(self) -> str:
        return "duplicate_key.v1"

    @property
    def validator_version(self) -> str:
        return "1.0.0"

    @property
    def target_stage(self) -> ValidationStage:
        return ValidationStage.SHAPE

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

        data_rows = payload.get("data", payload.get("rows", []))
        if isinstance(data_rows, list):
            seen_keys = set()
            for idx, row in enumerate(data_rows):
                if isinstance(row, dict) and "id" in row:
                    row_id = str(row["id"])
                    if row_id in seen_keys:
                        issues.append(
                            ValidationIssueV2(
                                issue_id="WARN_DUPLICATE_ROW_KEY",
                                stage=self.target_stage,
                                severity=self.default_severity,
                                message=f"Duplicate key '{row_id}' found at index {idx}",
                                validator_id=self.validator_id,
                            )
                        )
                    seen_keys.add(row_id)

        status = ValidationStatus.VALID_WITH_WARNINGS if issues else ValidationStatus.VALID
        execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        return ValidationCheckResultV2(
            check_id="duplicate_key_check",
            validator_id=self.validator_id,
            validator_version=self.validator_version,
            stage=self.target_stage,
            status=status,
            issues=issues,
            execution_time_ms=execution_time_ms,
        )
