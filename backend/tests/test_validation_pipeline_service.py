"""
LuminaAI Validation & Provenance V2 Pipeline Service Tests
"""

from uuid import uuid4
import pytest

from contracts.validation_provenance_v2 import ValidationContextV2, ValidationRequestV2, ValidationStatus
from services.validation_provenance.pipeline import GovernedValidationPipeline


@pytest.mark.asyncio
async def test_validation_pipeline_execution_pass():
    tid = uuid4()
    uid = uuid4()
    req = ValidationRequestV2(
        context=ValidationContextV2(tenant_id=tid, user_id=uid, request_id="REQ-TEST-001"),
        result_payload={"value": "300", "metric_id": "gross_revenue"},
        response_draft_text="O faturamento foi de 300",
        proposed_facts=[
            {
                "fact_id": "FACT-001",
                "fact_type": "SCALAR_METRIC",
                "canonical_metric_id": "gross_revenue",
                "value": {"decimal_value": "300", "raw_type": "DECIMAL"},
                "source_result_ref": "res_123",
            }
        ],
        proposed_claims=[
            {
                "claim_id": "CLAIM-001",
                "claim_type": "NUMERIC",
                "text": "O faturamento foi de 300",
                "fact_references": ["FACT-001"],
            }
        ],
        tenant_proof={"tenant_id": str(tid)},
    )

    pipeline = GovernedValidationPipeline()
    envelope = await pipeline.execute(req)

    assert envelope.overall_status == ValidationStatus.VALID
    assert envelope.certification_id is not None
    assert envelope.checksum is not None
