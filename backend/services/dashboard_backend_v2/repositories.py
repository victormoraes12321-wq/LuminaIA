"""Tenant-scoped repositories for the governed dashboard backend."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.dashboard_backend_v2 import (
    DashboardActivePublicationModelV2,
    DashboardAccessPolicyModelV2,
    DashboardApprovalModelV2,
    DashboardAuditEventModelV2,
    DashboardCollaboratorModelV2,
    DashboardModelV2,
    DashboardPublicationModelV2,
    DashboardRevisionModelV2,
    DashboardReviewModelV2,
    DashboardRuntimeExecutionModelV2,
    DashboardWidgetExecutionModelV2,
    DashboardEvaluationCaseModelV2,
    DashboardEvaluationResultModelV2,
)

from .errors import DashboardBackendError, not_found


def _uuid(value: str | uuid.UUID) -> uuid.UUID:
    try:
        return value if isinstance(value, uuid.UUID) else uuid.UUID(value)
    except ValueError as exc:
        raise not_found() from exc


def _assert_replay(existing: object, request_checksum: str) -> None:
    if getattr(existing, "request_checksum", getattr(existing, "create_request_checksum", None)) != request_checksum:
        raise DashboardBackendError(
            "DASHBOARD_IDEMPOTENCY_CONFLICT",
            "A chave de idempotência já foi usada com outro conteúdo.",
            409,
        )


class DashboardRepositoryV2:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_create_replay(self, tenant_id: str, scope: str, request_checksum: str) -> DashboardModelV2 | None:
        row = await self.session.scalar(select(DashboardModelV2).where(DashboardModelV2.tenant_id == _uuid(tenant_id), DashboardModelV2.create_idempotency_scope == scope))
        if row is not None:
            _assert_replay(row, request_checksum)
        return row

    async def create_draft(self, **values: object) -> DashboardModelV2:
        row = DashboardModelV2(**values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def get(self, tenant_id: str, dashboard_id: str, *, for_update: bool = False) -> DashboardModelV2:
        query = select(DashboardModelV2).where(DashboardModelV2.tenant_id == _uuid(tenant_id), DashboardModelV2.id == _uuid(dashboard_id))
        if for_update:
            query = query.with_for_update()
        row = await self.session.scalar(query)
        if row is None:
            raise not_found()
        return row

    async def list_tenant(self, tenant_id: str, *, lifecycle: str | None, cursor: str | None, limit: int) -> list[DashboardModelV2]:
        clauses = [DashboardModelV2.tenant_id == _uuid(tenant_id)]
        if lifecycle:
            clauses.append(DashboardModelV2.lifecycle == lifecycle)
        if cursor:
            clauses.append(DashboardModelV2.id > _uuid(cursor))
        result = await self.session.scalars(select(DashboardModelV2).where(*clauses).order_by(DashboardModelV2.id).limit(limit))
        return list(result)

    async def update_metadata_cas(self, tenant_id: str, dashboard_id: str, expected_lock: int, *, title: str | None, description: str | None) -> DashboardModelV2:
        values: dict[str, object] = {"lock_version": expected_lock + 1, "updated_at": datetime.now(timezone.utc)}
        if title is not None:
            values["title"] = title
        if description is not None:
            values["description"] = description
        result = await self.session.execute(update(DashboardModelV2).where(DashboardModelV2.tenant_id == _uuid(tenant_id), DashboardModelV2.id == _uuid(dashboard_id), DashboardModelV2.lock_version == expected_lock, DashboardModelV2.head_lifecycle == "DRAFT").values(**values))
        if result.rowcount != 1:
            raise DashboardBackendError("DASHBOARD_VERSION_CONFLICT", "Versão de dashboard obsoleta.", 409)
        return await self.get(tenant_id, dashboard_id)

    async def set_head_and_lifecycle_cas(self, tenant_id: str, dashboard_id: str, expected_lock: int, *, revision_id: str | uuid.UUID | None = None, lifecycle: str | None = None, head_lifecycle: str | None = None) -> DashboardModelV2:
        values: dict[str, object] = {"lock_version": expected_lock + 1, "updated_at": datetime.now(timezone.utc)}
        if revision_id is not None:
            values["head_revision_id"] = _uuid(revision_id)
        if lifecycle is not None:
            values["lifecycle"] = lifecycle
        if head_lifecycle is not None:
            values["head_lifecycle"] = head_lifecycle
        result = await self.session.execute(update(DashboardModelV2).where(DashboardModelV2.tenant_id == _uuid(tenant_id), DashboardModelV2.id == _uuid(dashboard_id), DashboardModelV2.lock_version == expected_lock).values(**values))
        if result.rowcount != 1:
            raise DashboardBackendError("DASHBOARD_VERSION_CONFLICT", "Atualização concorrente detectada.", 409)
        return await self.get(tenant_id, dashboard_id)

    async def verify_ownership(self, tenant_id: str, dashboard_id: str, user_id: str) -> bool:
        dashboard = await self.get(tenant_id, dashboard_id)
        return dashboard.owner_user_id == _uuid(user_id)


class DashboardRevisionRepositoryV2:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_revision(self, **values: object) -> DashboardRevisionModelV2:
        existing = await self.session.scalar(select(DashboardRevisionModelV2).where(DashboardRevisionModelV2.tenant_id == values["tenant_id"], DashboardRevisionModelV2.idempotency_scope == values["idempotency_scope"]))
        if existing is not None:
            _assert_replay(existing, str(values["request_checksum"]))
            return existing
        row = DashboardRevisionModelV2(**values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def find_revision_replay(self, tenant_id: str, scope: str, request_checksum: str) -> DashboardRevisionModelV2 | None:
        row = await self.session.scalar(select(DashboardRevisionModelV2).where(DashboardRevisionModelV2.tenant_id == _uuid(tenant_id), DashboardRevisionModelV2.idempotency_scope == scope))
        if row is not None:
            _assert_replay(row, request_checksum)
        return row

    async def find_review_replay(self, tenant_id: str, scope: str, request_checksum: str) -> DashboardReviewModelV2 | None:
        row = await self.session.scalar(select(DashboardReviewModelV2).where(DashboardReviewModelV2.tenant_id == _uuid(tenant_id), DashboardReviewModelV2.idempotency_scope == scope))
        if row is not None:
            _assert_replay(row, request_checksum)
        return row

    async def get(self, tenant_id: str, dashboard_id: str, revision_id: str) -> DashboardRevisionModelV2:
        row = await self.session.scalar(select(DashboardRevisionModelV2).where(DashboardRevisionModelV2.tenant_id == _uuid(tenant_id), DashboardRevisionModelV2.dashboard_id == _uuid(dashboard_id), DashboardRevisionModelV2.id == _uuid(revision_id)))
        if row is None:
            raise DashboardBackendError("DASHBOARD_REVISION_NOT_FOUND", "Revisão não encontrada.", 404)
        return row

    async def list(self, tenant_id: str, dashboard_id: str, limit: int = 100) -> list[DashboardRevisionModelV2]:
        result = await self.session.scalars(select(DashboardRevisionModelV2).where(DashboardRevisionModelV2.tenant_id == _uuid(tenant_id), DashboardRevisionModelV2.dashboard_id == _uuid(dashboard_id)).order_by(DashboardRevisionModelV2.revision_number.desc()).limit(limit))
        return list(result)

    async def find_by_checksum(self, tenant_id: str, dashboard_id: str, checksum: str) -> DashboardRevisionModelV2 | None:
        return await self.session.scalar(select(DashboardRevisionModelV2).where(DashboardRevisionModelV2.tenant_id == _uuid(tenant_id), DashboardRevisionModelV2.dashboard_id == _uuid(dashboard_id), DashboardRevisionModelV2.blueprint_checksum == checksum))

    async def append_review(self, **values: object) -> DashboardReviewModelV2:
        existing = await self.session.scalar(select(DashboardReviewModelV2).where(DashboardReviewModelV2.tenant_id == values["tenant_id"], DashboardReviewModelV2.idempotency_scope == values["idempotency_scope"]))
        if existing is not None:
            _assert_replay(existing, str(values["request_checksum"]))
            return existing
        row = DashboardReviewModelV2(**values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_approval(self, **values: object) -> DashboardApprovalModelV2:
        existing = await self.session.scalar(select(DashboardApprovalModelV2).where(DashboardApprovalModelV2.tenant_id == values["tenant_id"], DashboardApprovalModelV2.idempotency_scope == values["idempotency_scope"]))
        if existing is not None:
            _assert_replay(existing, str(values["request_checksum"]))
            return existing
        row = DashboardApprovalModelV2(**values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def approval_for_revision(self, tenant_id: str, dashboard_id: str, revision_id: str, blueprint_checksum: str) -> DashboardApprovalModelV2 | None:
        return await self.session.scalar(select(DashboardApprovalModelV2).where(DashboardApprovalModelV2.tenant_id == _uuid(tenant_id), DashboardApprovalModelV2.dashboard_id == _uuid(dashboard_id), DashboardApprovalModelV2.revision_id == _uuid(revision_id), DashboardApprovalModelV2.blueprint_checksum == blueprint_checksum))


class DashboardPublicationRepositoryV2:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_publication(self, **values: object) -> DashboardPublicationModelV2:
        existing = await self.session.scalar(select(DashboardPublicationModelV2).where(DashboardPublicationModelV2.tenant_id == values["tenant_id"], DashboardPublicationModelV2.idempotency_scope == values["idempotency_scope"]))
        if existing is not None:
            _assert_replay(existing, str(values["request_checksum"]))
            return existing
        row = DashboardPublicationModelV2(**values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def find_replay(self, tenant_id: str, scope: str, request_checksum: str) -> DashboardPublicationModelV2 | None:
        row = await self.session.scalar(select(DashboardPublicationModelV2).where(DashboardPublicationModelV2.tenant_id == _uuid(tenant_id), DashboardPublicationModelV2.idempotency_scope == scope))
        if row is not None:
            _assert_replay(row, request_checksum)
        return row

    async def get(self, tenant_id: str, dashboard_id: str, publication_id: str) -> DashboardPublicationModelV2:
        row = await self.session.scalar(select(DashboardPublicationModelV2).where(DashboardPublicationModelV2.tenant_id == _uuid(tenant_id), DashboardPublicationModelV2.dashboard_id == _uuid(dashboard_id), DashboardPublicationModelV2.id == _uuid(publication_id)))
        if row is None:
            raise DashboardBackendError("DASHBOARD_PUBLICATION_NOT_FOUND", "Publicação não encontrada.", 404)
        return row

    async def active(self, tenant_id: str, dashboard_id: str) -> tuple[DashboardActivePublicationModelV2, DashboardPublicationModelV2] | None:
        row = (await self.session.execute(select(DashboardActivePublicationModelV2, DashboardPublicationModelV2).join(DashboardPublicationModelV2, and_(DashboardPublicationModelV2.id == DashboardActivePublicationModelV2.publication_id, DashboardPublicationModelV2.dashboard_id == DashboardActivePublicationModelV2.dashboard_id, DashboardPublicationModelV2.tenant_id == DashboardActivePublicationModelV2.tenant_id)).where(DashboardActivePublicationModelV2.tenant_id == _uuid(tenant_id), DashboardActivePublicationModelV2.dashboard_id == _uuid(dashboard_id)))).first()
        return row if row is not None else None

    async def list_history(self, tenant_id: str, dashboard_id: str, limit: int = 100) -> list[DashboardPublicationModelV2]:
        result = await self.session.scalars(select(DashboardPublicationModelV2).where(DashboardPublicationModelV2.tenant_id == _uuid(tenant_id), DashboardPublicationModelV2.dashboard_id == _uuid(dashboard_id)).order_by(DashboardPublicationModelV2.generation.desc()).limit(limit))
        return list(result)

    async def cas_active_pointer(self, tenant_id: str, dashboard_id: str, publication_id: str | uuid.UUID, *, expected_generation: int, new_generation: int) -> None:
        tenant = _uuid(tenant_id)
        dashboard = _uuid(dashboard_id)
        publication = _uuid(publication_id)
        if expected_generation == 0:
            statement = insert(DashboardActivePublicationModelV2).values(tenant_id=tenant, dashboard_id=dashboard, publication_id=publication, generation=new_generation).on_conflict_do_nothing(index_elements=[DashboardActivePublicationModelV2.dashboard_id, DashboardActivePublicationModelV2.tenant_id])
        else:
            statement = update(DashboardActivePublicationModelV2).where(DashboardActivePublicationModelV2.tenant_id == tenant, DashboardActivePublicationModelV2.dashboard_id == dashboard, DashboardActivePublicationModelV2.generation == expected_generation).values(publication_id=publication, generation=new_generation, updated_at=datetime.now(timezone.utc))
        result = await self.session.execute(statement)
        if result.rowcount != 1:
            raise DashboardBackendError("DASHBOARD_PUBLICATION_CONFLICT", "Publicação ativa mudou concorrentemente.", 409)


class DashboardAccessRepositoryV2:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_collaborators(self, tenant_id: str, dashboard_id: str) -> list[DashboardCollaboratorModelV2]:
        result = await self.session.scalars(select(DashboardCollaboratorModelV2).where(DashboardCollaboratorModelV2.tenant_id == _uuid(tenant_id), DashboardCollaboratorModelV2.dashboard_id == _uuid(dashboard_id)).order_by(DashboardCollaboratorModelV2.id))
        return list(result)

    async def create_policy(self, **values: object) -> DashboardAccessPolicyModelV2:
        row = DashboardAccessPolicyModelV2(**values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_policy(self, tenant_id: str, dashboard_id: str) -> DashboardAccessPolicyModelV2:
        row = await self.session.scalar(select(DashboardAccessPolicyModelV2).where(DashboardAccessPolicyModelV2.tenant_id == _uuid(tenant_id), DashboardAccessPolicyModelV2.dashboard_id == _uuid(dashboard_id)))
        if row is None:
            raise DashboardBackendError("DASHBOARD_ACCESS_DENIED", "Política de acesso ausente.", 403)
        return row

    async def find_for_user(self, tenant_id: str, dashboard_id: str, user_id: str) -> DashboardCollaboratorModelV2 | None:
        return await self.session.scalar(select(DashboardCollaboratorModelV2).where(DashboardCollaboratorModelV2.tenant_id == _uuid(tenant_id), DashboardCollaboratorModelV2.dashboard_id == _uuid(dashboard_id), DashboardCollaboratorModelV2.user_id == _uuid(user_id)))

    async def add_collaborator(self, **values: object) -> DashboardCollaboratorModelV2:
        row = DashboardCollaboratorModelV2(**values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def update_collaborator_cas(self, tenant_id: str, dashboard_id: str, collaborator_id: str, expected_lock: int, role: str) -> DashboardCollaboratorModelV2:
        result = await self.session.execute(update(DashboardCollaboratorModelV2).where(DashboardCollaboratorModelV2.tenant_id == _uuid(tenant_id), DashboardCollaboratorModelV2.dashboard_id == _uuid(dashboard_id), DashboardCollaboratorModelV2.id == _uuid(collaborator_id), DashboardCollaboratorModelV2.lock_version == expected_lock).values(role=role, lock_version=expected_lock + 1, updated_at=datetime.now(timezone.utc)))
        if result.rowcount != 1:
            raise DashboardBackendError("DASHBOARD_VERSION_CONFLICT", "Colaborador mudou concorrentemente.", 409)
        row = await self.session.scalar(select(DashboardCollaboratorModelV2).where(DashboardCollaboratorModelV2.tenant_id == _uuid(tenant_id), DashboardCollaboratorModelV2.id == _uuid(collaborator_id)))
        if row is None:
            raise not_found()
        return row

    async def remove_collaborator_cas(self, tenant_id: str, dashboard_id: str, collaborator_id: str, expected_lock: int) -> None:
        row = await self.session.scalar(select(DashboardCollaboratorModelV2).where(DashboardCollaboratorModelV2.tenant_id == _uuid(tenant_id), DashboardCollaboratorModelV2.dashboard_id == _uuid(dashboard_id), DashboardCollaboratorModelV2.id == _uuid(collaborator_id), DashboardCollaboratorModelV2.lock_version == expected_lock).with_for_update())
        if row is None:
            raise DashboardBackendError("DASHBOARD_VERSION_CONFLICT", "Colaborador ausente ou obsoleto.", 409)
        await self.session.delete(row)


class DashboardAuditRepositoryV2:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def append_event(self, **values: object) -> DashboardAuditEventModelV2:
        row = DashboardAuditEventModelV2(**values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def find_by_idempotency(
        self, tenant_id: str, scope: str, request_checksum: str
    ) -> DashboardAuditEventModelV2 | None:
        row = await self.session.scalar(
            select(DashboardAuditEventModelV2).where(
                DashboardAuditEventModelV2.tenant_id == _uuid(tenant_id),
                DashboardAuditEventModelV2.idempotency_scope == scope,
            )
        )
        if row is not None:
            stored_checksum = str(row.metadata_json.get("request_checksum", ""))
            if stored_checksum != request_checksum:
                raise DashboardBackendError(
                    "DASHBOARD_IDEMPOTENCY_CONFLICT",
                    "A chave de idempotência já foi usada com outro conteúdo.",
                    409,
                )
        return row

    async def list_timeline(self, tenant_id: str, dashboard_id: str, limit: int = 100) -> list[DashboardAuditEventModelV2]:
        result = await self.session.scalars(select(DashboardAuditEventModelV2).where(DashboardAuditEventModelV2.tenant_id == _uuid(tenant_id), DashboardAuditEventModelV2.dashboard_id == _uuid(dashboard_id)).order_by(DashboardAuditEventModelV2.occurred_at.desc(), DashboardAuditEventModelV2.id.desc()).limit(limit))
        return list(result)


class DashboardRuntimeRepositoryV2:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_execution(self, **values: object) -> DashboardRuntimeExecutionModelV2:
        existing = await self.session.scalar(select(DashboardRuntimeExecutionModelV2).where(DashboardRuntimeExecutionModelV2.tenant_id == values["tenant_id"], DashboardRuntimeExecutionModelV2.idempotency_scope == values["idempotency_scope"]))
        if existing is not None:
            _assert_replay(existing, str(values["request_checksum"]))
            return existing
        row = DashboardRuntimeExecutionModelV2(**values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def complete_execution(self, tenant_id: str, execution_id: str, **values: object) -> None:
        result = await self.session.execute(update(DashboardRuntimeExecutionModelV2).where(DashboardRuntimeExecutionModelV2.tenant_id == _uuid(tenant_id), DashboardRuntimeExecutionModelV2.id == _uuid(execution_id), DashboardRuntimeExecutionModelV2.status == "STARTED").values(completed_at=datetime.now(timezone.utc), **values))
        if result.rowcount != 1:
            raise DashboardBackendError("DASHBOARD_VERSION_CONFLICT", "Execução já finalizada.", 409)

    async def record_widget(self, **values: object) -> DashboardWidgetExecutionModelV2:
        row = DashboardWidgetExecutionModelV2(**values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_evaluation_case(self, **values: object) -> DashboardEvaluationCaseModelV2:
        row = DashboardEvaluationCaseModelV2(**values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_evaluation_case(self, tenant_id: str, case_id: str) -> DashboardEvaluationCaseModelV2:
        row = await self.session.scalar(
            select(DashboardEvaluationCaseModelV2).where(
                DashboardEvaluationCaseModelV2.tenant_id == _uuid(tenant_id),
                DashboardEvaluationCaseModelV2.id == _uuid(case_id),
            )
        )
        if row is None:
            raise not_found()
        return row

    async def record_evaluation_result(self, **values: object) -> DashboardEvaluationResultModelV2:
        row = DashboardEvaluationResultModelV2(**values)
        self.session.add(row)
        await self.session.flush()
        return row
