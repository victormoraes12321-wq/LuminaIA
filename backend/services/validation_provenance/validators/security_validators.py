"""
LuminaAI Governed Validation & Provenance V2 - Security & Tenant Isolation Validators
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


class TenantIsolationValidator(GovernedValidator):
    @property
    def validator_id(self) -> str:
        return "tenant_isolation.v1"

    @property
    def validator_version(self) -> str:
        return "1.0.0"

    @property
    def target_stage(self) -> ValidationStage:
        return ValidationStage.TENANT_ISOLATION

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

        ctx_tenant_str = str(context.tenant_id)
        if tenant_proof:
            proof_tenant = str(tenant_proof.get("tenant_id", ""))
            if proof_tenant and proof_tenant != ctx_tenant_str:
                issues.append(
                    ValidationIssueV2(
                        issue_id="ERR_TENANT_PROOF_MISMATCH",
                        stage=self.target_stage,
                        severity=self.default_severity,
                        message=f"Tenant proof tenant_id '{proof_tenant}' does not match authenticated context '{ctx_tenant_str}'",
                        validator_id=self.validator_id,
                    )
                )

        payload_tenant = str(payload.get("tenant_id", ctx_tenant_str))
        if payload_tenant != ctx_tenant_str:
            issues.append(
                ValidationIssueV2(
                    issue_id="ERR_TENANT_PAYLOAD_MISMATCH",
                    stage=self.target_stage,
                    severity=self.default_severity,
                    message=f"Payload tenant_id '{payload_tenant}' does not match context '{ctx_tenant_str}'",
                    validator_id=self.validator_id,
                )
            )

        status = ValidationStatus.VALID if not issues else ValidationStatus.BLOCKED
        execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        return ValidationCheckResultV2(
            check_id="tenant_isolation_check",
            validator_id=self.validator_id,
            validator_version=self.validator_version,
            stage=self.target_stage,
            status=status,
            issues=issues,
            execution_time_ms=execution_time_ms,
        )


class AuthorizationValidator(GovernedValidator):
    @property
    def validator_id(self) -> str:
        return "authorization.v1"

    @property
    def validator_version(self) -> str:
        return "1.0.0"

    @property
    def target_stage(self) -> ValidationStage:
        return ValidationStage.AUTHORIZATION

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

        if not context.user_id:
            issues.append(
                ValidationIssueV2(
                    issue_id="ERR_AUTH_USER_MISSING",
                    stage=self.target_stage,
                    severity=self.default_severity,
                    message="Authenticated user_id is required for validation context",
                    validator_id=self.validator_id,
                )
            )

        status = ValidationStatus.VALID if not issues else ValidationStatus.BLOCKED
        execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        return ValidationCheckResultV2(
            check_id="authorization_check",
            validator_id=self.validator_id,
            validator_version=self.validator_version,
            stage=self.target_stage,
            status=status,
            issues=issues,
            execution_time_ms=execution_time_ms,
        )


class PresentationSafetyValidator(GovernedValidator):
    @property
    def validator_id(self) -> str:
        return "presentation_safety.v1"

    @property
    def validator_version(self) -> str:
        return "1.0.0"

    @property
    def target_stage(self) -> ValidationStage:
        return ValidationStage.PRESENTATION

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

        raw_text = str(payload.get("raw_text", ""))
        injection_patterns = ["<script>", "javascript:", "DROP TABLE", "TRUNCATE TABLE", "UNION SELECT"]
        for pattern in injection_patterns:
            if pattern.lower() in raw_text.lower():
                issues.append(
                    ValidationIssueV2(
                        issue_id="ERR_PRESENTATION_INJECTION_DETECTED",
                        stage=self.target_stage,
                        severity=self.default_severity,
                        message=f"Potentially unsafe injection pattern '{pattern}' detected in response",
                        validator_id=self.validator_id,
                    )
                )

        status = ValidationStatus.VALID if not issues else ValidationStatus.INVALID
        execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        return ValidationCheckResultV2(
            check_id="presentation_safety_check",
            validator_id=self.validator_id,
            validator_version=self.validator_version,
            stage=self.target_stage,
            status=status,
            issues=issues,
            execution_time_ms=execution_time_ms,
        )
