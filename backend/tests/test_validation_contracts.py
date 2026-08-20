"""
LuminaAI Validation & Provenance V2 Contracts Tests
"""

from uuid import uuid4
import pytest

from contracts.validation_provenance_v2 import (
    AnalyticalClaimV2,
    AnalyticalFactV2,
    AnalyticalFactValueV2,
    CertificationEnvelopeV2,
    ClaimType,
    CompletenessStatus,
    FactType,
    PublicProvenanceSummaryV2,
    ResponseCertificationV2,
    ResultCertificationV2,
    ValidationPolicyV2,
    ValidationSeverity,
    ValidationStage,
    ValidationStatus,
)


def test_validation_identity_enums():
    assert ValidationStage.CONTRACT.value == "CONTRACT"
    assert ValidationStatus.VALID.value == "VALID"
    assert ValidationSeverity.CRITICAL.value == "CRITICAL"
    assert FactType.SCALAR_METRIC.value == "SCALAR_METRIC"
    assert ClaimType.NUMERIC.value == "NUMERIC"


def test_analytical_fact_contract():
    val = AnalyticalFactValueV2(decimal_value="100.50", raw_type="DECIMAL")
    fact = AnalyticalFactV2(
        fact_id="FACT-001",
        tenant_id=uuid4(),
        fact_type=FactType.SCALAR_METRIC,
        canonical_metric_id="gross_revenue",
        value=val,
        unit="BRL",
        source_result_ref="ck_123",
        tenant_proof_checksum="proof_ck",
        checksum="fact_ck_123",
    )
    assert fact.fact_id == "FACT-001"
    assert fact.value.decimal_value == "100.50"
    assert fact.completeness == CompletenessStatus.COMPLETE
