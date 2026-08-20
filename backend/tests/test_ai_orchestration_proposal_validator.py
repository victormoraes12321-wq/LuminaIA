from __future__ import annotations

import pytest
from contracts.ai_orchestration_v2.identity import (
    AIOrchestrationStrategyV2,
    AIToolProposalDecisionV2,
)
from contracts.ai_orchestration_v2.proposals import (
    AIModelProposalV2,
    AIToolCallProposalV2,
)
from services.ai_orchestration.proposal_validator import AIModelProposalValidator


@pytest.mark.unit
def test_validator_rejects_authority_injection() -> None:
    validator = AIModelProposalValidator()
    tp = AIToolCallProposalV2(
        proposal_id="prop-1",
        sequence=1,
        tool_id="lumina.analytical_postgresql.query",
        tool_version="1.0.0",
        arguments={"tenant_id": "forged_tenant", "dataset_id": "sales_analytics"},
        args_checksum="12345678",
    )
    proposal = AIModelProposalV2(
        proposal_id="p-1",
        strategy=AIOrchestrationStrategyV2.SINGLE_TOOL_CALL,
        tool_proposals=[tp],
        checksum="12345678",
    )
    decision, validations, validated_calls, warnings = validator.validate_proposal(
        proposal=proposal,
        tenant_id="real_tenant",
        user_roles=["CONSULTA"],
    )
    assert decision == AIToolProposalDecisionV2.REJECTED
    assert len(validated_calls) == 0
    assert validations[0].reason_code == "AUTHORITY_FIELD_INJECTION"


@pytest.mark.unit
def test_validator_rejects_invented_tool() -> None:
    validator = AIModelProposalValidator()
    tp = AIToolCallProposalV2(
        proposal_id="prop-2",
        sequence=1,
        tool_id="lumina.invented_tool_xyz",
        tool_version="1.0.0",
        arguments={},
        args_checksum="12345678",
    )
    proposal = AIModelProposalV2(
        proposal_id="p-2",
        strategy=AIOrchestrationStrategyV2.SINGLE_TOOL_CALL,
        tool_proposals=[tp],
        checksum="12345678",
    )
    decision, validations, validated_calls, warnings = validator.validate_proposal(
        proposal=proposal,
        tenant_id="real_tenant",
        user_roles=["CONSULTA"],
    )
    assert decision == AIToolProposalDecisionV2.REJECTED
    assert validations[0].reason_code == "TOOL_NOT_FOUND"


@pytest.mark.unit
def test_validator_accepts_registered_tool() -> None:
    validator = AIModelProposalValidator()
    tp = AIToolCallProposalV2(
        proposal_id="prop-3",
        sequence=1,
        tool_id="lumina.analytical_postgresql.query",
        tool_version="1.0.0",
        arguments={"dataset_id": "sales_analytics", "metrics": ["total_sales"]},
        args_checksum="12345678",
    )
    proposal = AIModelProposalV2(
        proposal_id="p-3",
        strategy=AIOrchestrationStrategyV2.SINGLE_TOOL_CALL,
        tool_proposals=[tp],
        checksum="12345678",
    )
    decision, validations, validated_calls, warnings = validator.validate_proposal(
        proposal=proposal,
        tenant_id="real_tenant",
        user_roles=["CONSULTA"],
    )
    assert decision == AIToolProposalDecisionV2.ACCEPTED
    assert len(validated_calls) == 1
    assert validated_calls[0].tool_id == "lumina.analytical_postgresql.query"
