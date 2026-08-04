"""
LuminaAI Validation & Provenance V2 Facts & Claims Tests
"""

from uuid import uuid4
import pytest

from contracts.validation_provenance_v2 import ValidationStatus
from services.validation_provenance.fact_service import AnalyticalFactService
from services.validation_provenance.claim_service import AnalyticalClaimValidationService


def test_fact_extraction_and_claim_validation():
    tid = uuid4()
    payload = {"value": "300", "metric_id": "sales"}
    proposed_facts = [
        {
            "fact_id": "FACT-001",
            "fact_type": "SCALAR_METRIC",
            "canonical_metric_id": "sales",
            "value": {"decimal_value": "300", "raw_type": "DECIMAL"},
            "source_result_ref": "res_ck_123",
        }
    ]
    fact_set = AnalyticalFactService.extract_facts(tenant_id=tid, result_payload=payload, proposed_facts=proposed_facts)
    assert len(fact_set.facts) == 1
    assert fact_set.facts[0].fact_id == "FACT-001"

    proposed_claims = [
        {
            "claim_id": "CLAIM-001",
            "claim_type": "NUMERIC",
            "text": "O faturamento de junho foi de 300",
            "fact_references": ["FACT-001"],
        }
    ]
    claim_val = AnalyticalClaimValidationService.validate_claims(tenant_id=tid, proposed_claims=proposed_claims, fact_set=fact_set)
    assert claim_val.validation_status == ValidationStatus.VALID
    assert claim_val.all_numeric_claims_bound is True


def test_claim_without_fact_fails():
    tid = uuid4()
    payload = {"value": "300"}
    fact_set = AnalyticalFactService.extract_facts(tenant_id=tid, result_payload=payload, proposed_facts=[])

    proposed_claims_unbound = [
        {
            "claim_id": "CLAIM-001",
            "claim_type": "NUMERIC",
            "text": "O faturamento foi de 500",
            "fact_references": [],
        }
    ]
    claim_val = AnalyticalClaimValidationService.validate_claims(tenant_id=tid, proposed_claims=proposed_claims_unbound, fact_set=fact_set)
    assert claim_val.validation_status == ValidationStatus.INVALID
    assert claim_val.all_numeric_claims_bound is False
