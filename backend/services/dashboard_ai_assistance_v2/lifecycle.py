from __future__ import annotations

from contracts.dashboard_ai_assistance_v2 import DashboardAiProposalStatusV2

_TRANSITIONS: dict[DashboardAiProposalStatusV2, frozenset[DashboardAiProposalStatusV2]] = {
    DashboardAiProposalStatusV2.RECEIVED: frozenset({DashboardAiProposalStatusV2.ANALYZING, DashboardAiProposalStatusV2.CANCELLED, DashboardAiProposalStatusV2.BLOCKED}),
    DashboardAiProposalStatusV2.ANALYZING: frozenset({DashboardAiProposalStatusV2.NEEDS_CLARIFICATION, DashboardAiProposalStatusV2.RESOLVING, DashboardAiProposalStatusV2.BLOCKED, DashboardAiProposalStatusV2.FAILED, DashboardAiProposalStatusV2.CANCELLED}),
    DashboardAiProposalStatusV2.NEEDS_CLARIFICATION: frozenset({DashboardAiProposalStatusV2.RESOLVING, DashboardAiProposalStatusV2.CANCELLED, DashboardAiProposalStatusV2.EXPIRED, DashboardAiProposalStatusV2.SUPERSEDED}),
    DashboardAiProposalStatusV2.RESOLVING: frozenset({DashboardAiProposalStatusV2.NEEDS_CLARIFICATION, DashboardAiProposalStatusV2.SYNTHESIZING, DashboardAiProposalStatusV2.BLOCKED, DashboardAiProposalStatusV2.FAILED, DashboardAiProposalStatusV2.CANCELLED}),
    DashboardAiProposalStatusV2.SYNTHESIZING: frozenset({DashboardAiProposalStatusV2.VALIDATING, DashboardAiProposalStatusV2.BLOCKED, DashboardAiProposalStatusV2.FAILED, DashboardAiProposalStatusV2.CANCELLED}),
    DashboardAiProposalStatusV2.VALIDATING: frozenset({DashboardAiProposalStatusV2.READY_FOR_REVIEW, DashboardAiProposalStatusV2.BLOCKED, DashboardAiProposalStatusV2.FAILED}),
    DashboardAiProposalStatusV2.READY_FOR_REVIEW: frozenset({DashboardAiProposalStatusV2.ANALYZING, DashboardAiProposalStatusV2.ACCEPTED, DashboardAiProposalStatusV2.REJECTED, DashboardAiProposalStatusV2.CANCELLED, DashboardAiProposalStatusV2.SUPERSEDED, DashboardAiProposalStatusV2.EXPIRED}),
    DashboardAiProposalStatusV2.ACCEPTED: frozenset({DashboardAiProposalStatusV2.APPLYING, DashboardAiProposalStatusV2.CANCELLED, DashboardAiProposalStatusV2.SUPERSEDED, DashboardAiProposalStatusV2.EXPIRED}),
    DashboardAiProposalStatusV2.APPLYING: frozenset({DashboardAiProposalStatusV2.APPLIED, DashboardAiProposalStatusV2.FAILED, DashboardAiProposalStatusV2.BLOCKED}),
    DashboardAiProposalStatusV2.REJECTED: frozenset({DashboardAiProposalStatusV2.SUPERSEDED}),
    DashboardAiProposalStatusV2.APPLIED: frozenset(),
    DashboardAiProposalStatusV2.BLOCKED: frozenset(),
    DashboardAiProposalStatusV2.FAILED: frozenset(),
    DashboardAiProposalStatusV2.CANCELLED: frozenset(),
    DashboardAiProposalStatusV2.SUPERSEDED: frozenset(),
    DashboardAiProposalStatusV2.EXPIRED: frozenset(),
}


class DashboardAiProposalStateMachineV2:
    @staticmethod
    def assert_transition(current: DashboardAiProposalStatusV2, target: DashboardAiProposalStatusV2) -> None:
        if target not in _TRANSITIONS[current]:
            raise ValueError(f"DASHBOARD_AI_INVALID_TRANSITION:{current.value}->{target.value}")

    @staticmethod
    def can_transition(current: DashboardAiProposalStatusV2, target: DashboardAiProposalStatusV2) -> bool:
        return target in _TRANSITIONS[current]
