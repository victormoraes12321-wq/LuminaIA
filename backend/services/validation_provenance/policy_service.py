"""
LuminaAI Governed Validation Policy Service
Version: lumina.validation-provenance/1.0
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from contracts.validation_provenance_v2 import (
    ValidationPolicyV2,
    ValidationPolicyVersionV2,
    ValidationSeverity,
    ValidationStage,
    ValidatorDefinitionV2,
)


class ValidationPolicyService:
    @staticmethod
    def get_default_policy(tenant_id: UUID) -> ValidationPolicyV2:
        version = ValidationPolicyVersionV2(
            version="1.0.0",
            contract_version="lumina.validation-provenance/1.0",
            author="SYSTEM",
            created_at=datetime.now(timezone.utc).isoformat(),
            checksum=hashlib.sha256(b"DEFAULT_SYSTEM_POLICY_V1").hexdigest(),
        )
        validators = [
            ValidatorDefinitionV2(
                validator_id="contract.v1",
                validator_version="1.0.0",
                stage=ValidationStage.CONTRACT,
                criticality=ValidationSeverity.CRITICAL,
            ),
            ValidatorDefinitionV2(
                validator_id="tenant_isolation.v1",
                validator_version="1.0.0",
                stage=ValidationStage.TENANT_ISOLATION,
                criticality=ValidationSeverity.CRITICAL,
            ),
            ValidatorDefinitionV2(
                validator_id="authorization.v1",
                validator_version="1.0.0",
                stage=ValidationStage.AUTHORIZATION,
                criticality=ValidationSeverity.CRITICAL,
            ),
            ValidatorDefinitionV2(
                validator_id="semantic_canonical_ref.v1",
                validator_version="1.0.0",
                stage=ValidationStage.SEMANTIC,
                criticality=ValidationSeverity.ERROR,
            ),
            ValidatorDefinitionV2(
                validator_id="metric_fingerprint.v1",
                validator_version="1.0.0",
                stage=ValidationStage.METRIC,
                criticality=ValidationSeverity.CRITICAL,
            ),
            ValidatorDefinitionV2(
                validator_id="metric_unit.v1",
                validator_version="1.0.0",
                stage=ValidationStage.METRIC,
                criticality=ValidationSeverity.ERROR,
            ),
            ValidatorDefinitionV2(
                validator_id="decimal_precision.v1",
                validator_version="1.0.0",
                stage=ValidationStage.NUMERIC,
                criticality=ValidationSeverity.ERROR,
            ),
            ValidatorDefinitionV2(
                validator_id="numeric_finite.v1",
                validator_version="1.0.0",
                stage=ValidationStage.NUMERIC,
                criticality=ValidationSeverity.ERROR,
            ),
            ValidatorDefinitionV2(
                validator_id="comparison_delta.v1",
                validator_version="1.0.0",
                stage=ValidationStage.COMPARISON,
                criticality=ValidationSeverity.ERROR,
            ),
            ValidatorDefinitionV2(
                validator_id="comparison_percentage.v1",
                validator_version="1.0.0",
                stage=ValidationStage.COMPARISON,
                criticality=ValidationSeverity.ERROR,
            ),
            ValidatorDefinitionV2(
                validator_id="fact_reference.v1",
                validator_version="1.0.0",
                stage=ValidationStage.CLAIMS,
                criticality=ValidationSeverity.CRITICAL,
            ),
            ValidatorDefinitionV2(
                validator_id="claim_value_consistency.v1",
                validator_version="1.0.0",
                stage=ValidationStage.CLAIMS,
                criticality=ValidationSeverity.ERROR,
            ),
            ValidatorDefinitionV2(
                validator_id="provenance_graph.v1",
                validator_version="1.0.0",
                stage=ValidationStage.PROVENANCE,
                criticality=ValidationSeverity.CRITICAL,
            ),
            ValidatorDefinitionV2(
                validator_id="completeness.v1",
                validator_version="1.0.0",
                stage=ValidationStage.COMPLETENESS,
                criticality=ValidationSeverity.WARNING,
            ),
            ValidatorDefinitionV2(
                validator_id="truncation.v1",
                validator_version="1.0.0",
                stage=ValidationStage.COMPLETENESS,
                criticality=ValidationSeverity.WARNING,
            ),
            ValidatorDefinitionV2(
                validator_id="presentation_safety.v1",
                validator_version="1.0.0",
                stage=ValidationStage.PRESENTATION,
                criticality=ValidationSeverity.ERROR,
            ),
        ]

        return ValidationPolicyV2(
            policy_id=uuid4(),
            tenant_id=tenant_id,
            policy_name="System Default Governed Validation Policy",
            version_info=version,
            required_stages=list(ValidationStage),
            validators=validators,
            fail_fast_on_critical=True,
            allow_partial_results=False,
            require_fact_bindings_for_numeric_claims=True,
            strict_decimal_precision=True,
            freshness_tolerance_seconds=86400,
            is_active=True,
        )
