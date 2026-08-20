from __future__ import annotations

import logging
from typing import Dict, List, Set, Tuple
from contracts.ai_orchestration_v2.identity import AIOrchestrationStateV2

logger = logging.getLogger("luminaai.ai_orchestration.state_machine")

# Allowlisted transitions
ALLOWED_TRANSITIONS: Dict[AIOrchestrationStateV2, Set[AIOrchestrationStateV2]] = {
    AIOrchestrationStateV2.RECEIVED: {
        AIOrchestrationStateV2.AUTHENTICATED,
        AIOrchestrationStateV2.BLOCKED,
        AIOrchestrationStateV2.CANCELLED,
        AIOrchestrationStateV2.FAILED,
    },
    AIOrchestrationStateV2.AUTHENTICATED: {
        AIOrchestrationStateV2.CLASSIFIED,
        AIOrchestrationStateV2.CLARIFICATION_REQUIRED,
        AIOrchestrationStateV2.BLOCKED,
        AIOrchestrationStateV2.CANCELLED,
        AIOrchestrationStateV2.FAILED,
    },
    AIOrchestrationStateV2.CLASSIFIED: {
        AIOrchestrationStateV2.CONTEXT_ASSEMBLED,
        AIOrchestrationStateV2.CLARIFICATION_REQUIRED,
        AIOrchestrationStateV2.BLOCKED,
        AIOrchestrationStateV2.CANCELLED,
        AIOrchestrationStateV2.FAILED,
    },
    AIOrchestrationStateV2.CONTEXT_ASSEMBLED: {
        AIOrchestrationStateV2.BUDGET_ALLOCATED,
        AIOrchestrationStateV2.BLOCKED,
        AIOrchestrationStateV2.CANCELLED,
        AIOrchestrationStateV2.FAILED,
        AIOrchestrationStateV2.TIMED_OUT,
    },
    AIOrchestrationStateV2.BUDGET_ALLOCATED: {
        AIOrchestrationStateV2.CATALOG_READY,
        AIOrchestrationStateV2.BLOCKED,
        AIOrchestrationStateV2.CANCELLED,
        AIOrchestrationStateV2.FAILED,
        AIOrchestrationStateV2.TIMED_OUT,
    },
    AIOrchestrationStateV2.CATALOG_READY: {
        AIOrchestrationStateV2.MODEL_REQUEST_PREPARED,
        AIOrchestrationStateV2.RESPONSE_DRAFTED,
        AIOrchestrationStateV2.CLARIFICATION_REQUIRED,
        AIOrchestrationStateV2.BLOCKED,
        AIOrchestrationStateV2.CANCELLED,
        AIOrchestrationStateV2.FAILED,
    },
    AIOrchestrationStateV2.MODEL_REQUEST_PREPARED: {
        AIOrchestrationStateV2.MODEL_INVOKED,
        AIOrchestrationStateV2.BLOCKED,
        AIOrchestrationStateV2.CANCELLED,
        AIOrchestrationStateV2.FAILED,
        AIOrchestrationStateV2.TIMED_OUT,
    },
    AIOrchestrationStateV2.MODEL_INVOKED: {
        AIOrchestrationStateV2.PROPOSAL_RECEIVED,
        AIOrchestrationStateV2.BLOCKED,
        AIOrchestrationStateV2.CANCELLED,
        AIOrchestrationStateV2.FAILED,
        AIOrchestrationStateV2.TIMED_OUT,
    },
    AIOrchestrationStateV2.PROPOSAL_RECEIVED: {
        AIOrchestrationStateV2.PROPOSAL_VALIDATED,
        AIOrchestrationStateV2.CLARIFICATION_REQUIRED,
        AIOrchestrationStateV2.BLOCKED,
        AIOrchestrationStateV2.CANCELLED,
        AIOrchestrationStateV2.FAILED,
    },
    AIOrchestrationStateV2.PROPOSAL_VALIDATED: {
        AIOrchestrationStateV2.TOOL_INVOCATION_PENDING,
        AIOrchestrationStateV2.RESPONSE_DRAFTED,
        AIOrchestrationStateV2.CLARIFICATION_REQUIRED,
        AIOrchestrationStateV2.BLOCKED,
        AIOrchestrationStateV2.CANCELLED,
        AIOrchestrationStateV2.FAILED,
    },
    AIOrchestrationStateV2.TOOL_INVOCATION_PENDING: {
        AIOrchestrationStateV2.TOOL_INVOCATION_RUNNING,
        AIOrchestrationStateV2.BLOCKED,
        AIOrchestrationStateV2.CANCELLED,
        AIOrchestrationStateV2.FAILED,
        AIOrchestrationStateV2.TIMED_OUT,
    },
    AIOrchestrationStateV2.TOOL_INVOCATION_RUNNING: {
        AIOrchestrationStateV2.TOOL_RESULT_VALIDATED,
        AIOrchestrationStateV2.BLOCKED,
        AIOrchestrationStateV2.CANCELLED,
        AIOrchestrationStateV2.FAILED,
        AIOrchestrationStateV2.TIMED_OUT,
    },
    AIOrchestrationStateV2.TOOL_RESULT_VALIDATED: {
        AIOrchestrationStateV2.MODEL_REQUEST_PREPARED,
        AIOrchestrationStateV2.RESPONSE_DRAFTED,
        AIOrchestrationStateV2.CLARIFICATION_REQUIRED,
        AIOrchestrationStateV2.BLOCKED,
        AIOrchestrationStateV2.CANCELLED,
        AIOrchestrationStateV2.FAILED,
    },
    AIOrchestrationStateV2.RESPONSE_DRAFTED: {
        AIOrchestrationStateV2.RESPONSE_VALIDATED,
        AIOrchestrationStateV2.CLARIFICATION_REQUIRED,
        AIOrchestrationStateV2.BLOCKED,
        AIOrchestrationStateV2.CANCELLED,
        AIOrchestrationStateV2.FAILED,
    },
    AIOrchestrationStateV2.RESPONSE_VALIDATED: {
        AIOrchestrationStateV2.PERSISTING,
        AIOrchestrationStateV2.PARTIAL,
        AIOrchestrationStateV2.BLOCKED,
        AIOrchestrationStateV2.CANCELLED,
        AIOrchestrationStateV2.FAILED,
    },
    AIOrchestrationStateV2.PERSISTING: {
        AIOrchestrationStateV2.COMPLETED,
        AIOrchestrationStateV2.FAILED,
    },
    AIOrchestrationStateV2.CLARIFICATION_REQUIRED: {
        AIOrchestrationStateV2.COMPLETED,
        AIOrchestrationStateV2.PERSISTING,
        AIOrchestrationStateV2.FAILED,
    },
    AIOrchestrationStateV2.COMPLETED: set(),
    AIOrchestrationStateV2.BLOCKED: set(),
    AIOrchestrationStateV2.TIMED_OUT: set(),
    AIOrchestrationStateV2.CANCELLED: set(),
    AIOrchestrationStateV2.FAILED: set(),
    AIOrchestrationStateV2.PARTIAL: set(),
}


class GovernedAIStateMachine:
    """State machine governing state transitions in LuminaAI Orchestration."""

    def __init__(self, initial_state: AIOrchestrationStateV2 = AIOrchestrationStateV2.RECEIVED) -> None:
        self._current_state = initial_state
        self._history: List[Tuple[AIOrchestrationStateV2, AIOrchestrationStateV2, str]] = []

    @property
    def current_state(self) -> AIOrchestrationStateV2:
        return self._current_state

    def can_transition_to(self, target_state: AIOrchestrationStateV2) -> bool:
        allowed = ALLOWED_TRANSITIONS.get(self._current_state, set())
        return target_state in allowed

    def transition_to(self, target_state: AIOrchestrationStateV2, reason: str) -> None:
        if not self.can_transition_to(target_state):
            raise ValueError(
                f"Transicao invalida de {self._current_state.value} para {target_state.value} (Motivo: {reason})"
            )
        from_state = self._current_state
        self._current_state = target_state
        self._history.append((from_state, target_state, reason))
        logger.info(
            "[StateMachine] State transition: %s -> %s | Reason: %s",
            from_state.value,
            target_state.value,
            reason,
        )
