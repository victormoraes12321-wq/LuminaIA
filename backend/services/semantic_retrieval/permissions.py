from __future__ import annotations

import uuid

from contracts.semantic_retrieval_v2 import (
    SemanticAccessDecisionV2,
    SemanticPermission,
)
from models.user import UserRole
from services.semantic_retrieval.checksums import checksum_for
from services.semantic_retrieval.errors import semantic_error


_CONSULTA = frozenset(
    {
        SemanticPermission.SEARCH,
        SemanticPermission.RESOLVE,
        SemanticPermission.READ_PUBLIC_CANDIDATE,
    }
)
_GESTOR = _CONSULTA | frozenset(
    {
        SemanticPermission.INSPECT_SCORES,
        SemanticPermission.RUN_EVALUATION,
        SemanticPermission.AUDIT_READ,
    }
)
_ADMIN = frozenset(SemanticPermission)
ROLE_PERMISSIONS: dict[UserRole, frozenset[SemanticPermission]] = {
    UserRole.CONSULTA: _CONSULTA,
    UserRole.GESTOR: _GESTOR,
    UserRole.ADMIN: _ADMIN,
}


def permission_fingerprint(role: UserRole) -> str:
    return checksum_for(sorted(item.value for item in ROLE_PERMISSIONS[role]))


def access_decision(
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    role: UserRole,
    permission: SemanticPermission,
) -> SemanticAccessDecisionV2:
    allowed = permission in ROLE_PERMISSIONS.get(role, frozenset())
    return SemanticAccessDecisionV2(
        allowed=allowed,
        permission=permission,
        reason_code="ROLE_PERMISSION_GRANTED" if allowed else "ROLE_PERMISSION_DENIED",
        permission_fingerprint=permission_fingerprint(role),
    )


def require_permission(
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    role: UserRole,
    permission: SemanticPermission,
) -> None:
    decision = access_decision(
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
        permission=permission,
    )
    if not decision.allowed:
        raise semantic_error(
            "SEMANTIC_INDEX_ACCESS_DENIED",
            "A operacao semantica nao esta disponivel para o perfil autenticado.",
        )
