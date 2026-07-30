from __future__ import annotations

import uuid

from contracts.user_analytical_profile_v2 import (
    ProfileAccessDecisionV2,
    ProfilePermission,
)
from models.user import UserRole

from .errors import UserProfileAccessDeniedError


ROLE_PERMISSIONS: dict[UserRole, frozenset[ProfilePermission]] = {
    UserRole.CONSULTA: frozenset(
        {
            ProfilePermission.READ_OWN,
            ProfilePermission.UPDATE_OWN,
            ProfilePermission.EXPORT_OWN,
            ProfilePermission.DELETE_OWN,
        }
    ),
    UserRole.GESTOR: frozenset(
        {
            ProfilePermission.READ_OWN,
            ProfilePermission.UPDATE_OWN,
            ProfilePermission.EXPORT_OWN,
            ProfilePermission.DELETE_OWN,
        }
    ),
    UserRole.ADMIN: frozenset(
        {
            ProfilePermission.READ_OWN,
            ProfilePermission.UPDATE_OWN,
            ProfilePermission.EXPORT_OWN,
            ProfilePermission.DELETE_OWN,
            ProfilePermission.MANAGE_POLICY,
            ProfilePermission.AUDIT_READ,
            ProfilePermission.SUPPORT_READ_REDACTED,
        }
    ),
}


def access_decision(
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    role: UserRole,
    permission: ProfilePermission,
) -> ProfileAccessDecisionV2:
    allowed = permission in ROLE_PERMISSIONS.get(role, frozenset())
    return ProfileAccessDecisionV2(
        tenant_id=tenant_id,
        user_id=user_id,
        permission=permission,
        allowed=allowed,
        redacted=permission == ProfilePermission.SUPPORT_READ_REDACTED,
        reason_code="ROLE_PERMISSION_GRANTED" if allowed else "ROLE_PERMISSION_DENIED",
    )


def require_permission(
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    role: UserRole,
    permission: ProfilePermission,
) -> None:
    if not access_decision(
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
        permission=permission,
    ).allowed:
        raise UserProfileAccessDeniedError(
            "A operação não está disponível para o perfil autenticado.",
            details={"permission": permission.value},
        )
