from __future__ import annotations

from enum import Enum

from contracts.dashboard_ai_assistance_v2 import DashboardAiOperationV2


class DashboardAiCapabilityV2(str, Enum):
    VIEW = "dashboard_ai:view"
    CREATE_PROPOSAL = "dashboard_ai:create_proposal"
    REVISE = "dashboard_ai:revise"
    DECIDE = "dashboard_ai:decide"
    APPLY_CREATE = "dashboard_ai:apply_create"
    APPLY_EDIT = "dashboard_ai:apply_edit"
    EVALUATE = "dashboard_ai:evaluate"


_ROLE_CAPABILITIES = {
    "CONSULTA": frozenset({DashboardAiCapabilityV2.VIEW}),
    "GESTOR": frozenset(DashboardAiCapabilityV2),
    "ADMIN": frozenset(DashboardAiCapabilityV2),
}


class DashboardAiPolicyV2:
    @staticmethod
    def require(role: str, capability: DashboardAiCapabilityV2) -> None:
        if capability not in _ROLE_CAPABILITIES.get(role.upper(), frozenset()):
            raise PermissionError("DASHBOARD_AI_ACCESS_DENIED")

    @staticmethod
    def assert_operation(operation: DashboardAiOperationV2) -> None:
        if operation.value in {"PUBLISH", "APPROVE", "ROLLBACK", "MANAGE_COLLABORATORS", "CHANGE_OWNER", "GRANT_PERMISSION"}:
            raise PermissionError("DASHBOARD_AI_OPERATION_FORBIDDEN")

