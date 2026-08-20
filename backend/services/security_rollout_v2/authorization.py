"""Extracted server-side authorization matrix for Prompt 26 certification."""
from __future__ import annotations

from contracts.security_rollout_v2 import CapabilityCheckV2, CapabilityDecisionV2

ROLES = ("CONSULTA", "GESTOR", "ADMIN")

_ALLOWED: dict[str, frozenset[str]] = {
    "dashboard.read": frozenset(ROLES),
    "dashboard.author": frozenset({"GESTOR", "ADMIN"}),
    "dashboard.approve": frozenset({"ADMIN"}),
    "dashboard.publish": frozenset({"ADMIN"}),
    "dashboard.rollback": frozenset({"ADMIN"}),
    "dashboard_ai.proposal": frozenset({"GESTOR", "ADMIN"}),
    "insight.read": frozenset(ROLES),
    "insight.acknowledge": frozenset(ROLES),
    "insight.dismiss": frozenset(ROLES),
    "observability.read": frozenset({"GESTOR", "ADMIN"}),
    "evaluation.run": frozenset({"ADMIN"}),
    "baseline.manage": frozenset({"ADMIN"}),
    "queue.view": frozenset({"GESTOR", "ADMIN"}),
    "queue.cancel": frozenset({"ADMIN"}),
    "queue.replay": frozenset({"ADMIN"}),
    "queue.drain": frozenset({"ADMIN"}),
    "performance.certify": frozenset({"ADMIN"}),
    "rollout.readiness": frozenset({"ADMIN"}),
    "security.readiness": frozenset({"ADMIN"}),
}


class AuthorizationMatrixServiceV2:
    @staticmethod
    def decide(*, server_role: str, capability: str) -> CapabilityCheckV2:
        normalized_role = str(server_role).upper()
        allowed = normalized_role in _ALLOWED.get(capability, frozenset())
        return CapabilityCheckV2(
            role=normalized_role,
            capability=capability,
            decision=CapabilityDecisionV2.ALLOW if allowed else CapabilityDecisionV2.DENY,
            authority_source="authenticated PostgreSQL User.role and static governed policy",
        )

    @staticmethod
    def matrix() -> tuple[CapabilityCheckV2, ...]:
        return tuple(
            AuthorizationMatrixServiceV2.decide(server_role=role, capability=capability)
            for capability in sorted(_ALLOWED)
            for role in ROLES
        )
