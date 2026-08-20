"""
LuminaAI Validation & Provenance V2 Mandatory Scenarios Tests
"""

from uuid import uuid4
import pytest

from contracts.validation_provenance_v2 import ValidationContextV2, ValidationRequestV2, ValidationStatus
from services.validation_provenance.pipeline import GovernedValidationPipeline


@pytest.mark.asyncio
async def test_scenario_comparison_june_july():
    tid = uuid4()
    req = ValidationRequestV2(
        context=ValidationContextV2(tenant_id=tid, user_id=uuid4(), request_id="REQ-COMP-001"),
        result_payload={
            "baseline": "300",
            "target": "400",
            "delta": "100",
            "percentage": "33.33",
        },
        response_draft_text="Faturamento cresceu de 300 para 400 (+33.33%)",
        proposed_facts=[
            {
                "fact_id": "FACT-JUNE",
                "fact_type": "COMPARISON_OPERAND",
                "value": {"decimal_value": "300", "raw_type": "DECIMAL"},
                "source_result_ref": "ck_res_1",
            },
            {
                "fact_id": "FACT-JULY",
                "fact_type": "COMPARISON_OPERAND",
                "value": {"decimal_value": "400", "raw_type": "DECIMAL"},
                "source_result_ref": "ck_res_1",
            },
        ],
        proposed_claims=[
            {
                "claim_id": "CLAIM-COMP",
                "claim_type": "COMPARATIVE",
                "text": "Faturamento cresceu de 300 para 400 (+33.33%)",
                "fact_references": ["FACT-JUNE", "FACT-JULY"],
            }
        ],
        tenant_proof={"tenant_id": str(tid)},
    )
    pipeline = GovernedValidationPipeline()
    envelope = await pipeline.execute(req)
    assert envelope.overall_status == ValidationStatus.VALID


@pytest.mark.asyncio
async def test_scenario_wrong_percentage_blocked():
    tid = uuid4()
    req = ValidationRequestV2(
        context=ValidationContextV2(tenant_id=tid, user_id=uuid4(), request_id="REQ-COMP-002"),
        result_payload={
            "baseline": "300",
            "target": "400",
            "delta": "100",
            "percentage_mismatch": True,
        },
        response_draft_text="Faturamento cresceu de 300 para 400 (+25%)",
        proposed_facts=[],
        proposed_claims=[],
        tenant_proof={"tenant_id": str(tid)},
    )
    pipeline = GovernedValidationPipeline()
    envelope = await pipeline.execute(req)
    assert envelope.overall_status in (ValidationStatus.INVALID, ValidationStatus.BLOCKED)


@pytest.mark.asyncio
async def test_scenario_truncation_warning():
    tid = uuid4()
    req = ValidationRequestV2(
        context=ValidationContextV2(tenant_id=tid, user_id=uuid4(), request_id="REQ-TRUNC-001"),
        result_payload={"truncated": True, "value": "100"},
        response_draft_text="Exibindo dados truncados",
        proposed_facts=[
            {
                "fact_id": "FACT-TRUNC",
                "fact_type": "SCALAR_METRIC",
                "value": {"decimal_value": "100", "raw_type": "DECIMAL"},
                "source_result_ref": "ck_res_2",
            }
        ],
        proposed_claims=[
            {
                "claim_id": "CLAIM-TRUNC",
                "claim_type": "NUMERIC",
                "text": "Exibindo dados truncados 100",
                "fact_references": ["FACT-TRUNC"],
            }
        ],
        tenant_proof={"tenant_id": str(tid)},
    )
    pipeline = GovernedValidationPipeline()
    envelope = await pipeline.execute(req)
    assert envelope.overall_status == ValidationStatus.VALID_WITH_WARNINGS
    assert envelope.public_summary.truncated is True
