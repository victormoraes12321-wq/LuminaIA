from __future__ import annotations

import pytest
from contracts.ai_orchestration_v2.identity import (
    AI_ORCHESTRATION_VERSION,
    AIOrchestrationStateV2,
    AIOrchestrationStrategyV2,
)
from contracts.ai_orchestration_v2.budgets import (
    AITokenBudgetV2,
    AIToolBudgetV2,
    AITimeBudgetV2,
    AICostBudgetV2,
)
from contracts.ai_orchestration_v2.orchestration import (
    AIOrchestrationRequestV2,
    AIOrchestrationResponseV2,
)


@pytest.mark.unit
def test_identity_and_defaults() -> None:
    assert AI_ORCHESTRATION_VERSION == "lumina.ai-orchestration/1.0"
    assert AIOrchestrationStateV2.RECEIVED.value == "RECEIVED"
    assert AIOrchestrationStateV2.COMPLETED.value == "COMPLETED"
    assert AIOrchestrationStrategyV2.SINGLE_MODEL_CALL.value == "SINGLE_MODEL_CALL"


@pytest.mark.unit
def test_budgets_initialization() -> None:
    tb = AITokenBudgetV2()
    assert tb.max_request_tokens == 8192
    assert tb.exceeded is False

    tool_b = AIToolBudgetV2()
    assert tool_b.max_tool_calls == 4
    assert tool_b.remaining_calls == 4

    time_b = AITimeBudgetV2()
    assert time_b.request_deadline_ms == 30000

    cost_b = AICostBudgetV2()
    assert cost_b.currency == "USD"


@pytest.mark.unit
def test_request_and_response_validation() -> None:
    req = AIOrchestrationRequestV2(user_query="faturamento de junho de 2026")
    assert req.user_query == "faturamento de junho de 2026"
    assert req.locale == "pt-BR"

    resp = AIOrchestrationResponseV2(
        run_id="run-123",
        tenant_id="tenant-a",
        user_id="user-1",
        status=AIOrchestrationStateV2.COMPLETED,
        strategy=AIOrchestrationStrategyV2.SINGLE_TOOL_CALL,
        response_text="Faturamento de R$ 300,00",
        token_usage=AITokenBudgetV2(),
        checksum="12345678",
    )
    assert resp.run_id == "run-123"
    assert resp.status == AIOrchestrationStateV2.COMPLETED
