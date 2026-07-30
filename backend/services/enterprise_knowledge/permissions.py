from __future__ import annotations

import uuid

from contracts.enterprise_knowledge_v2 import (
    KnowledgeAccessDecisionV2,
    KnowledgePermission,
)
from models.user import UserRole
from services.enterprise_knowledge.errors import KnowledgeAccessDeniedError


ROLE_PERMISSIONS: dict[UserRole, frozenset[KnowledgePermission]] = {
    UserRole.CONSULTA: frozenset({KnowledgePermission.READ}),
    UserRole.GESTOR: frozenset(
        {
            KnowledgePermission.READ,
            KnowledgePermission.CREATE,
            KnowledgePermission.EDIT,
            KnowledgePermission.SUBMIT,
            KnowledgePermission.REVIEW,
            KnowledgePermission.APPROVE,
            KnowledgePermission.REJECT,
            KnowledgePermission.EXPORT,
        }
    ),
    UserRole.ADMIN: frozenset(KnowledgePermission),
}


def access_decision(
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    role: UserRole,
    permission: KnowledgePermission,
) -> KnowledgeAccessDecisionV2:
    allowed = permission in ROLE_PERMISSIONS.get(role, frozenset())
    return KnowledgeAccessDecisionV2(
        tenant_id=tenant_id,
        user_id=user_id,
        permission=permission,
        allowed=allowed,
        reason_code="ROLE_PERMISSION_GRANTED" if allowed else "ROLE_PERMISSION_DENIED",
    )


def require_permission(
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    role: UserRole,
    permission: KnowledgePermission,
) -> None:
    decision = access_decision(
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
        permission=permission,
    )
    if not decision.allowed:
        raise KnowledgeAccessDeniedError(
            "O perfil autenticado não possui permissão para esta operação.",
            details={"permission": permission.value, "reason": decision.reason_code},
        )
