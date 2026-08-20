"""
LuminaAI Validation & Provenance V2 Validators Tests
"""

from uuid import uuid4
import pytest

from contracts.validation_provenance_v2 import ValidationContextV2, ValidationStatus
from services.validation_provenance.validators.contract_validators import ContractValidator, DuplicateKeyValidator, ResultShapeValidator
from services.validation_provenance.validators.security_validators import TenantIsolationValidator
from services.validation_provenance.validators.numeric_validators import ComparisonDeltaValidator, DecimalValidator


@pytest.mark.asyncio
async def test_contract_validator():
    val = ContractValidator()
    ctx = ValidationContextV2(tenant_id=uuid4(), user_id=uuid4(), request_id="REQ-1")
    res = await val.validate(context=ctx, payload={"key": "val"}, proposed_facts=[], proposed_claims=[])
    assert res.status == ValidationStatus.VALID


@pytest.mark.asyncio
async def test_tenant_isolation_validator_pass():
    val = TenantIsolationValidator()
    tid = uuid4()
    ctx = ValidationContextV2(tenant_id=tid, user_id=uuid4(), request_id="REQ-1")
    res = await val.validate(
        context=ctx,
        payload={"tenant_id": str(tid)},
        proposed_facts=[],
        proposed_claims=[],
        tenant_proof={"tenant_id": str(tid)},
    )
    assert res.status == ValidationStatus.VALID


@pytest.mark.asyncio
async def test_tenant_isolation_validator_fail():
    val = TenantIsolationValidator()
    tid1 = uuid4()
    tid2 = uuid4()
    ctx = ValidationContextV2(tenant_id=tid1, user_id=uuid4(), request_id="REQ-1")
    res = await val.validate(
        context=ctx,
        payload={"tenant_id": str(tid1)},
        proposed_facts=[],
        proposed_claims=[],
        tenant_proof={"tenant_id": str(tid2)},
    )
    assert res.status == ValidationStatus.BLOCKED
    assert len(res.issues) == 1
    assert res.issues[0].issue_id == "ERR_TENANT_PROOF_MISMATCH"


@pytest.mark.asyncio
async def test_comparison_delta_validator():
    val = ComparisonDeltaValidator()
    ctx = ValidationContextV2(tenant_id=uuid4(), user_id=uuid4(), request_id="REQ-1")
    payload = {"baseline": "300", "target": "400", "delta": "100"}
    res = await val.validate(context=ctx, payload=payload, proposed_facts=[], proposed_claims=[])
    assert res.status == ValidationStatus.VALID

    payload_bad = {"baseline": "300", "target": "400", "delta": "50"}
    res_bad = await val.validate(context=ctx, payload=payload_bad, proposed_facts=[], proposed_claims=[])
    assert res_bad.status == ValidationStatus.INVALID
