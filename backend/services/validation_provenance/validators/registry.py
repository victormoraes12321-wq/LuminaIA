"""
LuminaAI Governed Validation & Provenance V2 - Static Validator Registry
Version: lumina.validation-provenance/1.0
"""

from typing import Dict, Type

from .base import GovernedValidator
from .contract_validators import ContractValidator, DuplicateKeyValidator, ResultShapeValidator
from .security_validators import AuthorizationValidator, PresentationSafetyValidator, TenantIsolationValidator
from .semantic_validators import (
    AuthorityReferenceValidator,
    MetricFingerprintValidator,
    MetricUnitValidator,
    SemanticCanonicalReferenceValidator,
)
from .temporal_validators import SourceFreshnessValidator, TemporalPeriodValidator
from .numeric_validators import (
    ComparisonDeltaValidator,
    ComparisonOperandsValidator,
    ComparisonPercentageValidator,
    DecimalValidator,
    NumericFiniteValueValidator,
)
from .completeness_validators import CompletenessValidator, TruncationValidator
from .tool_orchestration_validators import OrchestrationRunValidator, ToolResultChecksumValidator
from .fact_claim_validators import ClaimValueConsistencyValidator, FactReferenceValidator
from .provenance_validators import ProvenanceGraphValidator


REGISTERED_VALIDATORS: Dict[str, Type[GovernedValidator]] = {
    "contract.v1": ContractValidator,
    "tenant_isolation.v1": TenantIsolationValidator,
    "authorization.v1": AuthorizationValidator,
    "authority_reference.v1": AuthorityReferenceValidator,
    "semantic_canonical_ref.v1": SemanticCanonicalReferenceValidator,
    "temporal_period.v1": TemporalPeriodValidator,
    "metric_fingerprint.v1": MetricFingerprintValidator,
    "metric_unit.v1": MetricUnitValidator,
    "decimal_precision.v1": DecimalValidator,
    "numeric_finite.v1": NumericFiniteValueValidator,
    "comparison_operands.v1": ComparisonOperandsValidator,
    "comparison_delta.v1": ComparisonDeltaValidator,
    "comparison_percentage.v1": ComparisonPercentageValidator,
    "result_shape.v1": ResultShapeValidator,
    "duplicate_key.v1": DuplicateKeyValidator,
    "completeness.v1": CompletenessValidator,
    "truncation.v1": TruncationValidator,
    "source_freshness.v1": SourceFreshnessValidator,
    "tool_result_checksum.v1": ToolResultChecksumValidator,
    "orchestration_run.v1": OrchestrationRunValidator,
    "fact_reference.v1": FactReferenceValidator,
    "claim_value_consistency.v1": ClaimValueConsistencyValidator,
    "provenance_graph.v1": ProvenanceGraphValidator,
    "presentation_safety.v1": PresentationSafetyValidator,
}


def get_validator(validator_id: str) -> GovernedValidator:
    """
    Returns a new instance of a registered static validator by ID.
    Raises KeyError if validator_id is not allowlisted.
    """
    if validator_id not in REGISTERED_VALIDATORS:
        raise KeyError(f"Validator ID '{validator_id}' is not registered or allowlisted.")
    return REGISTERED_VALIDATORS[validator_id]()
