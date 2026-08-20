"""
LuminaAI Governed Validation & Provenance V2 - Provenance Graph Validators
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


class ProvenanceGraphValidator(GovernedValidator):
    @property
    def validator_id(self) -> str:
        return "provenance_graph.v1"

    @property
    def validator_version(self) -> str:
        return "1.0.0"

    @property
    def target_stage(self) -> ValidationStage:
        return ValidationStage.PROVENANCE

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

        if payload.get("provenance_cycle_detected", False):
            issues.append(
                ValidationIssueV2(
                    issue_id="ERR_PROVENANCE_CYCLE",
                    stage=self.target_stage,
                    severity=self.default_severity,
                    message="Provenance DAG contains cycle dependency",
                    validator_id=self.validator_id,
                )
            )

        if payload.get("provenance_cross_tenant", False):
            issues.append(
                ValidationIssueV2(
                    issue_id="ERR_PROVENANCE_CROSS_TENANT",
                    stage=self.target_stage,
                    severity=self.default_severity,
                    message="Provenance edge connects nodes across different tenants",
                    validator_id=self.validator_id,
                )
            )

        status = ValidationStatus.VALID if not issues else ValidationStatus.BLOCKED
        execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        return ValidationCheckResultV2(
            check_id="provenance_graph_check",
            validator_id=self.validator_id,
            validator_version=self.validator_version,
            stage=self.target_stage,
            status=status,
            issues=issues,
            execution_time_ms=execution_time_ms,
        )
