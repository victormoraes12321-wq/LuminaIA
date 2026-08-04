from __future__ import annotations

import pytest
from contracts.ai_orchestration_v2.identity import AIOrchestrationStateV2
from services.ai_orchestration.state_machine import GovernedAIStateMachine


@pytest.mark.unit
def test_valid_transitions() -> None:
    sm = GovernedAIStateMachine(AIOrchestrationStateV2.RECEIVED)
    assert sm.current_state == AIOrchestrationStateV2.RECEIVED

    sm.transition_to(AIOrchestrationStateV2.AUTHENTICATED, "Auth verified")
    assert sm.current_state == AIOrchestrationStateV2.AUTHENTICATED

    sm.transition_to(AIOrchestrationStateV2.CLASSIFIED, "Classification done")
    assert sm.current_state == AIOrchestrationStateV2.CLASSIFIED


@pytest.mark.unit
def test_invalid_transition_raises() -> None:
    sm = GovernedAIStateMachine(AIOrchestrationStateV2.RECEIVED)
    with pytest.raises(ValueError, match="Transicao invalida"):
        sm.transition_to(AIOrchestrationStateV2.COMPLETED, "Illegal skip")


@pytest.mark.unit
def test_terminal_states_cannot_transition() -> None:
    sm = GovernedAIStateMachine(AIOrchestrationStateV2.COMPLETED)
    assert sm.can_transition_to(AIOrchestrationStateV2.MODEL_INVOKED) is False
    with pytest.raises(ValueError):
        sm.transition_to(AIOrchestrationStateV2.MODEL_INVOKED, "Illegal transition from completed")
