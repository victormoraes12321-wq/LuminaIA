"""Governed collaborator operations; global RBAC and resource grants are intersected."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contracts.dashboard_backend_v2 import (
    DashboardCapabilityBackendV2,
    DashboardCollaboratorCreateRequestV2,
    DashboardCollaboratorRoleV2,
    DashboardCollaboratorUpdateRequestV2,
    DashboardCollaboratorV2,
)
from models.user import User

from .application import DashboardActorContextV2, DashboardAuditServiceV2, _require_resource_access
from .errors import DashboardBackendError
from .repositories import DashboardAccessRepositoryV2, DashboardAuditRepositoryV2, DashboardRepositoryV2


def _contract(row: object) -> DashboardCollaboratorV2:
    return DashboardCollaboratorV2(
        collaborator_id=str(row.id), user_reference=str(row.user_id),
        role=DashboardCollaboratorRoleV2(row.role), lock_version=row.lock_version,
        created_at=row.created_at, updated_at=row.updated_at,
    )


class DashboardAccessServiceV2:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.dashboards = DashboardRepositoryV2(session)
        self.access = DashboardAccessRepositoryV2(session)
        self.audit = DashboardAuditServiceV2(DashboardAuditRepositoryV2(session))

    async def list(self, *, actor: DashboardActorContextV2, dashboard_id: str) -> tuple[DashboardCollaboratorV2, ...]:
        dashboard = await self.dashboards.get(actor.tenant_id, dashboard_id)
        await _require_resource_access(self.access, actor=actor, dashboard=dashboard, capability=DashboardCapabilityBackendV2.MANAGE_COLLABORATORS)
        return tuple(_contract(row) for row in await self.access.list_collaborators(actor.tenant_id, dashboard_id))

    async def add(self, *, actor: DashboardActorContextV2, dashboard_id: str, request: DashboardCollaboratorCreateRequestV2) -> DashboardCollaboratorV2:
        dashboard = await self.dashboards.get(actor.tenant_id, dashboard_id)
        await _require_resource_access(self.access, actor=actor, dashboard=dashboard, capability=DashboardCapabilityBackendV2.MANAGE_COLLABORATORS)
        user_id = uuid.UUID(request.user_reference)
        user = await self.session.scalar(select(User).where(User.id == user_id, User.tenant_id == uuid.UUID(actor.tenant_id)))
        if user is None:
            raise DashboardBackendError("DASHBOARD_NOT_FOUND", "Recurso não encontrado.", 404)
        if user_id == dashboard.owner_user_id:
            raise DashboardBackendError("DASHBOARD_ACCESS_DENIED", "Owner não deve ser duplicado como colaborador.", 409)
        row = await self.access.add_collaborator(id=uuid.uuid4(), dashboard_id=dashboard.id, tenant_id=dashboard.tenant_id, user_id=user_id, role=request.role.value, lock_version=1)
        await self.audit.append(actor=actor, dashboard_id=dashboard_id, event_type="DASHBOARD_COLLABORATOR_ADDED", resource_reference=str(row.id), metadata={"role": request.role.value})
        return _contract(row)

    async def update(self, *, actor: DashboardActorContextV2, dashboard_id: str, collaborator_id: str, request: DashboardCollaboratorUpdateRequestV2) -> DashboardCollaboratorV2:
        dashboard = await self.dashboards.get(actor.tenant_id, dashboard_id)
        await _require_resource_access(self.access, actor=actor, dashboard=dashboard, capability=DashboardCapabilityBackendV2.MANAGE_COLLABORATORS)
        row = await self.access.update_collaborator_cas(actor.tenant_id, dashboard_id, collaborator_id, request.expected_lock_version, request.role.value)
        await self.audit.append(actor=actor, dashboard_id=dashboard_id, event_type="DASHBOARD_COLLABORATOR_UPDATED", resource_reference=str(row.id), metadata={"role": request.role.value, "lock_version": row.lock_version})
        return _contract(row)

    async def remove(self, *, actor: DashboardActorContextV2, dashboard_id: str, collaborator_id: str, expected_lock_version: int) -> None:
        dashboard = await self.dashboards.get(actor.tenant_id, dashboard_id)
        await _require_resource_access(self.access, actor=actor, dashboard=dashboard, capability=DashboardCapabilityBackendV2.MANAGE_COLLABORATORS)
        await self.access.remove_collaborator_cas(actor.tenant_id, dashboard_id, collaborator_id, expected_lock_version)
        await self.audit.append(actor=actor, dashboard_id=dashboard_id, event_type="DASHBOARD_COLLABORATOR_REMOVED", resource_reference=collaborator_id, metadata={"expected_lock_version": expected_lock_version})
