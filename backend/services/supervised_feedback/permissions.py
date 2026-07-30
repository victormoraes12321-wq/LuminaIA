from __future__ import annotations

import uuid

from contracts.supervised_feedback_v2 import FeedbackAccessDecisionV2, FeedbackPermission
from models.user import UserRole
from services.supervised_feedback.errors import FeedbackAccessDeniedError


_OWN = frozenset(
    {
        FeedbackPermission.CREATE_OWN,
        FeedbackPermission.READ_OWN,
        FeedbackPermission.UPDATE_OWN,
        FeedbackPermission.WITHDRAW_OWN,
        FeedbackPermission.EXPORT_OWN,
    }
)
_GESTOR = _OWN | frozenset(
    {
        FeedbackPermission.TRIAGE,
        FeedbackPermission.REVIEW,
        FeedbackPermission.REQUEST_INFORMATION,
        FeedbackPermission.SUPPORT_READ_REDACTED,
    }
)
_ADMIN = frozenset(FeedbackPermission)


def access_decision(
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    role: UserRole,
    permission: FeedbackPermission,
) -> FeedbackAccessDecisionV2:
    allowed = permission in {
        UserRole.CONSULTA: _OWN,
        UserRole.GESTOR: _GESTOR,
        UserRole.ADMIN: _ADMIN,
    }[role]
    return FeedbackAccessDecisionV2(
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
    permission: FeedbackPermission,
) -> None:
    if not access_decision(
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
        permission=permission,
    ).allowed:
        raise FeedbackAccessDeniedError(
            "A operacao nao esta disponivel para o perfil autenticado.",
            details={"permission": permission.value},
        )
