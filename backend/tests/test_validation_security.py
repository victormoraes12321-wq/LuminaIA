"""
LuminaAI Validation & Provenance V2 Security & Multi-Tenant Tests
"""

from uuid import uuid4
import pytest

from contracts.validation_provenance_v2 import ValidationContextV2, ValidationRequestV2, ValidationStatus
from services.validation_provenance.pipeline import GovernedValidationPipeline


@pytest.mark.asyncio
async def test_cross_tenant_proof_fails():
    tid1 = uuid4()
    tid2 = uuid4()
    req = ValidationRequestV2(
        context=ValidationContextV2(tenant_id=tid1, user_id=uuid4(), request_id="REQ-SEC-001"),
        result_payload={"value": "100"},
        tenant_proof={"tenant_id": str(tid2)},
    )
    pipeline = GovernedValidationPipeline()
    envelope = await pipeline.execute(req)

    assert envelope.overall_status in (ValidationStatus.BLOCKED, ValidationStatus.INVALID)
    assert any("TENANT_ISOLATION" in item or "mismatch" in item for item in envelope.critical_issues)


@pytest.mark.asyncio
async def test_forged_numeric_claim_fails():
    tid = uuid4()
    req = ValidationRequestV2(
        context=ValidationContextV2(tenant_id=tid, user_id=uuid4(), request_id="REQ-SEC-002"),
        result_payload={"value": "100"},
        proposed_facts=[],
        proposed_claims=[
            {
                "claim_id": "CLAIM-FORGED",
                "claim_type": "NUMERIC",
                "text": "O lucro total foi de R$ 1.000.000,00",
                "fact_references": [],
            }
        ],
        tenant_proof={"tenant_id": str(tid)},
    )
    pipeline = GovernedValidationPipeline()
    envelope = await pipeline.execute(req)

    assert envelope.overall_status in (ValidationStatus.BLOCKED, ValidationStatus.INVALID)
