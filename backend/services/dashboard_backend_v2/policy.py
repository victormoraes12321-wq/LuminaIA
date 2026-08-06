"""Rollout, lifecycle and RBAC policies with no I/O."""
from __future__ import annotations

from enum import Enum

from contracts.dashboard_backend_v2 import (
    DashboardCapabilityBackendV2,
    DashboardCollaboratorRoleV2,
)
from contracts.dashboard_blueprint_v2 import DashboardLifecycleV2

from .errors import DashboardBackendError


class DashboardBackendMode(str, Enum):
    LEGACY_ONLY = "LEGACY_ONLY"
    SHADOW_VALIDATE = "SHADOW_VALIDATE"
    V2_AUTHORING = "V2_AUTHORING"
    V2_PUBLISHED_READ = "V2_PUBLISHED_READ"
    V2_RUNTIME = "V2_RUNTIME"


TRANSITIONS: dict[DashboardLifecycleV2, frozenset[DashboardLifecycleV2]] = {
    DashboardLifecycleV2.DRAFT: frozenset({DashboardLifecycleV2.IN_REVIEW}),
    DashboardLifecycleV2.IN_REVIEW: frozenset({DashboardLifecycleV2.DRAFT, DashboardLifecycleV2.APPROVED, DashboardLifecycleV2.REJECTED}),
    DashboardLifecycleV2.APPROVED: frozenset({DashboardLifecycleV2.PUBLISHED, DashboardLifecycleV2.DRAFT}),
    DashboardLifecycleV2.PUBLISHED: frozenset({DashboardLifecycleV2.SUPERSEDED, DashboardLifecycleV2.DEPRECATED}),
    DashboardLifecycleV2.SUPERSEDED: frozenset({DashboardLifecycleV2.ARCHIVED}),
    DashboardLifecycleV2.DEPRECATED: frozenset({DashboardLifecycleV2.ARCHIVED}),
    DashboardLifecycleV2.REJECTED: frozenset({DashboardLifecycleV2.DRAFT}),
    DashboardLifecycleV2.ARCHIVED: frozenset(),
}


ROLE_CAPABILITIES: dict[str, frozenset[DashboardCapabilityBackendV2]] = {
    "CONSULTA": frozenset({
        DashboardCapabilityBackendV2.VIEW, DashboardCapabilityBackendV2.LIST,
        DashboardCapabilityBackendV2.EXECUTE, DashboardCapabilityBackendV2.VIEW_PROVENANCE,
    }),
    "GESTOR": frozenset({
        DashboardCapabilityBackendV2.CREATE, DashboardCapabilityBackendV2.VIEW,
        DashboardCapabilityBackendV2.LIST, DashboardCapabilityBackendV2.EDIT_VISUAL,
        DashboardCapabilityBackendV2.EDIT_SEMANTIC, DashboardCapabilityBackendV2.REVIEW,
        DashboardCapabilityBackendV2.CLONE, DashboardCapabilityBackendV2.EXECUTE,
        DashboardCapabilityBackendV2.VIEW_PROVENANCE, DashboardCapabilityBackendV2.VIEW_AUDIT,
    }),
    "ADMIN": frozenset(DashboardCapabilityBackendV2),
}


COLLABORATOR_CAPABILITIES: dict[DashboardCollaboratorRoleV2, frozenset[DashboardCapabilityBackendV2]] = {
    DashboardCollaboratorRoleV2.VIEWER: frozenset({DashboardCapabilityBackendV2.VIEW, DashboardCapabilityBackendV2.EXECUTE}),
    DashboardCollaboratorRoleV2.EDITOR_VISUAL: frozenset({DashboardCapabilityBackendV2.VIEW, DashboardCapabilityBackendV2.EDIT_VISUAL}),
    DashboardCollaboratorRoleV2.EDITOR_SEMANTIC: frozenset({DashboardCapabilityBackendV2.VIEW, DashboardCapabilityBackendV2.EDIT_VISUAL, DashboardCapabilityBackendV2.EDIT_SEMANTIC}),
    DashboardCollaboratorRoleV2.REVIEWER: frozenset({DashboardCapabilityBackendV2.VIEW, DashboardCapabilityBackendV2.REVIEW}),
    DashboardCollaboratorRoleV2.PUBLISHER: frozenset({DashboardCapabilityBackendV2.VIEW, DashboardCapabilityBackendV2.PUBLISH}),
    DashboardCollaboratorRoleV2.ADMINISTRATOR: frozenset(DashboardCapabilityBackendV2),
}


class DashboardLifecycleServiceV2:
    @staticmethod
    def permitted(current: DashboardLifecycleV2) -> tuple[DashboardLifecycleV2, ...]:
        return tuple(sorted(TRANSITIONS[current], key=lambda item: item.value))

    @staticmethod
    def assert_transition(current: DashboardLifecycleV2, target: DashboardLifecycleV2) -> None:
        if target not in TRANSITIONS[current]:
            raise DashboardBackendError(
                "DASHBOARD_INVALID_LIFECYCLE_TRANSITION",
                f"Transição {current.value} → {target.value} não permitida.",
                409,
            )

    @staticmethod
    def runtime_eligible(state: DashboardLifecycleV2) -> bool:
        return state is DashboardLifecycleV2.PUBLISHED


class DashboardAccessPolicyServiceV2:
    """Intersect global RBAC with resource grants; grants never elevate global RBAC."""

    @staticmethod
    def effective_capabilities(
        *,
        global_role: str,
        is_owner: bool,
        collaborator_role: DashboardCollaboratorRoleV2 | str | None,
        tenant_policy_capabilities: frozenset[DashboardCapabilityBackendV2] = frozenset(),
    ) -> frozenset[DashboardCapabilityBackendV2]:
        global_capabilities = ROLE_CAPABILITIES.get(global_role, frozenset())
        if global_role == "ADMIN":
            resource_capabilities = frozenset(DashboardCapabilityBackendV2)
        elif is_owner:
            resource_capabilities = frozenset(DashboardCapabilityBackendV2)
        elif collaborator_role is not None:
            normalized_role = collaborator_role if isinstance(collaborator_role, DashboardCollaboratorRoleV2) else DashboardCollaboratorRoleV2(collaborator_role)
            resource_capabilities = COLLABORATOR_CAPABILITIES[normalized_role]
        else:
            resource_capabilities = tenant_policy_capabilities
        return global_capabilities & resource_capabilities

    @classmethod
    def require(
        cls,
        capability: DashboardCapabilityBackendV2,
        *,
        global_role: str,
        is_owner: bool,
        collaborator_role: DashboardCollaboratorRoleV2 | str | None,
        tenant_policy_capabilities: frozenset[DashboardCapabilityBackendV2] = frozenset(),
    ) -> None:
        if capability not in cls.effective_capabilities(
            global_role=global_role,
            is_owner=is_owner,
            collaborator_role=collaborator_role,
            tenant_policy_capabilities=tenant_policy_capabilities,
        ):
            raise DashboardBackendError(
                "DASHBOARD_PERMISSION_INSUFFICIENT", "Permissão insuficiente.", 403
            )
