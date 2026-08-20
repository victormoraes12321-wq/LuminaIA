"""Conditionally mounted API for the governed Dashboard Backend V2."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from contracts.dashboard_backend_v2 import (
    DashboardApprovalV2,
    DashboardArchiveRequestV2,
    DashboardAuditEventV2,
    DashboardCapabilityBackendV2,
    DashboardCloneRequestV2,
    DashboardCollaboratorCreateRequestV2,
    DashboardCollaboratorUpdateRequestV2,
    DashboardCollaboratorV2,
    DashboardCreateRequestV2,
    DashboardCreateResultV2,
    DashboardDetailV2,
    DashboardListItemV2,
    DashboardListRequestV2,
    DashboardPublicationRequestV2,
    DashboardPublicationResultV2,
    DashboardPublicationV2,
    DashboardRecordV2,
    DashboardRevisionCreateRequestV2,
    DashboardRevisionV2,
    DashboardReviewDecisionKindV2,
    DashboardReviewDecisionV2,
    DashboardReviewRequestV2,
    DashboardRollbackRequestV2,
    DashboardRollbackResultV2,
    DashboardRuntimePlanV2,
    DashboardRuntimeProvenanceV2,
    DashboardRuntimeRequestV2,
    DashboardRuntimeResultV2,
    DashboardSemanticPatchRequestV2,
    DashboardUpdateDraftRequestV2,
    DashboardVisualPatchRequestV2,
)
from database import get_db
from models.user import User
from routers.dependencies import get_current_user
from services.dashboard_backend_v2 import (
    DashboardAccessRepositoryV2,
    DashboardAccessServiceV2,
    DashboardActorContextV2,
    DashboardAuditRepositoryV2,
    DashboardAuthoringServiceV2,
    DashboardBackendError,
    DashboardCloneServiceV2,
    DashboardPatchServiceV2,
    DashboardPublicationRepositoryV2,
    DashboardPublicationServiceV2,
    DashboardRepositoryV2,
    DashboardRevisionRepositoryV2,
    DashboardRevisionServiceV2,
    DashboardReviewServiceV2,
    DashboardRollbackServiceV2,
    DashboardRuntimeExecutionServiceV2,
    ExistingAnalyticalAuthoritiesWidgetExecutorV2,
    ExistingSmartCacheDashboardInvalidatorV2,
    GovernedCatalogWidgetQueryResolverV2,
    dashboard_contract,
    publication_contract,
    revision_contract,
    resolve_resource_capabilities,
)
from services.smart_cache_materialization.pipeline import SmartCachePipeline


router = APIRouter(prefix="/api/v2/dashboards", tags=["Governed Dashboard Backend V2"])
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=200)]


def _actor(user: User) -> DashboardActorContextV2:
    return DashboardActorContextV2(
        tenant_id=str(user.tenant_id), user_id=str(user.id),
        global_role=user.role.value if hasattr(user.role, "value") else str(user.role),
    )


def _require_authoring(actor: DashboardActorContextV2) -> None:
    if settings.DASHBOARD_BACKEND_MODE not in {"V2_AUTHORING", "V2_RUNTIME"} or not settings.DASHBOARD_ADMIN_APIS_ENABLED:
        raise DashboardBackendError("DASHBOARD_RUNTIME_UNAVAILABLE", "APIs de authoring V2 desativadas.", 503)
    if settings.DASHBOARD_TENANT_ALLOWLIST and actor.tenant_id not in settings.DASHBOARD_TENANT_ALLOWLIST:
        raise DashboardBackendError("DASHBOARD_ACCESS_DENIED", "Tenant fora do rollout aprovado.", 403)


def _require_published_read(actor: DashboardActorContextV2) -> None:
    if settings.DASHBOARD_BACKEND_MODE not in {"V2_AUTHORING", "V2_PUBLISHED_READ", "V2_RUNTIME"} or not settings.DASHBOARD_ADMIN_APIS_ENABLED:
        raise DashboardBackendError("DASHBOARD_RUNTIME_UNAVAILABLE", "Leitura V2 desativada.", 503)
    if settings.DASHBOARD_TENANT_ALLOWLIST and actor.tenant_id not in settings.DASHBOARD_TENANT_ALLOWLIST:
        raise DashboardBackendError("DASHBOARD_ACCESS_DENIED", "Tenant fora do rollout aprovado.", 403)


def _require_runtime(actor: DashboardActorContextV2) -> None:
    if settings.DASHBOARD_BACKEND_MODE != "V2_RUNTIME" or not settings.DASHBOARD_RUNTIME_APIS_ENABLED:
        raise DashboardBackendError("DASHBOARD_RUNTIME_UNAVAILABLE", "Runtime V2 desativado.", 503)
    if settings.DASHBOARD_TENANT_ALLOWLIST and actor.tenant_id not in settings.DASHBOARD_TENANT_ALLOWLIST:
        raise DashboardBackendError("DASHBOARD_ACCESS_DENIED", "Tenant fora do rollout aprovado.", 403)


async def _runtime_service(db: AsyncSession) -> DashboardRuntimeExecutionServiceV2:
    safe_resolver = GovernedCatalogWidgetQueryResolverV2()
    cache = SmartCachePipeline(db) if settings.DASHBOARD_RUNTIME_CACHE_ENABLED else None
    authority = ExistingAnalyticalAuthoritiesWidgetExecutorV2(
        safe_resolver, safe_service=safe_resolver.safe_service, smart_cache_pipeline=cache,
        materialization_enabled=settings.DASHBOARD_MATERIALIZATION_ENABLED,
    )
    return DashboardRuntimeExecutionServiceV2(db, authority)


async def _authorized_dashboard(
    db: AsyncSession,
    *,
    actor: DashboardActorContextV2,
    dashboard_id: str,
    capability: DashboardCapabilityBackendV2,
):
    dashboard = await DashboardRepositoryV2(db).get(actor.tenant_id, dashboard_id)
    capabilities = await resolve_resource_capabilities(
        DashboardAccessRepositoryV2(db), actor=actor, dashboard=dashboard
    )
    if capability not in capabilities:
        raise DashboardBackendError("DASHBOARD_NOT_FOUND", "Dashboard não encontrado.", 404)
    return dashboard


@router.post("", response_model=DashboardCreateResultV2, status_code=201)
async def create_dashboard(request: DashboardCreateRequestV2, idempotency_key: IdempotencyKey, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> DashboardCreateResultV2:
    actor = _actor(user); _require_authoring(actor)
    return await DashboardAuthoringServiceV2(db).create(actor=actor, request=request, idempotency_key=idempotency_key)


@router.get("", response_model=tuple[DashboardListItemV2, ...])
async def list_dashboards(db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)], lifecycle: str | None = None, cursor: str | None = None, limit: int = Query(default=50, ge=1, le=100)) -> tuple[DashboardListItemV2, ...]:
    actor = _actor(user); _require_published_read(actor)
    rows = await DashboardRepositoryV2(db).list_tenant(actor.tenant_id, lifecycle=lifecycle, cursor=cursor, limit=limit)
    access = DashboardAccessRepositoryV2(db)
    items: list[DashboardListItemV2] = []
    for row in rows:
        if settings.DASHBOARD_BACKEND_MODE == "V2_PUBLISHED_READ" and row.lifecycle != "PUBLISHED":
            continue
        capabilities = await resolve_resource_capabilities(access, actor=actor, dashboard=row)
        if DashboardCapabilityBackendV2.VIEW in capabilities:
            items.append(DashboardListItemV2(dashboard=dashboard_contract(row), effective_capabilities=tuple(sorted(capabilities, key=lambda item: item.value))))
    return tuple(items)


@router.get("/{dashboard_id}", response_model=DashboardDetailV2)
async def get_dashboard(dashboard_id: str, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> DashboardDetailV2:
    actor = _actor(user); _require_published_read(actor)
    dashboard = await DashboardRepositoryV2(db).get(actor.tenant_id, dashboard_id)
    if settings.DASHBOARD_BACKEND_MODE == "V2_PUBLISHED_READ" and dashboard.lifecycle != "PUBLISHED":
        raise DashboardBackendError("DASHBOARD_NOT_FOUND", "Dashboard não encontrado.", 404)
    revisions = DashboardRevisionRepositoryV2(db)
    head = await revisions.get(actor.tenant_id, dashboard_id, str(dashboard.head_revision_id)) if dashboard.head_revision_id else None
    publications = DashboardPublicationRepositoryV2(db)
    active = await publications.active(actor.tenant_id, dashboard_id)
    active_contract = None
    active_id = None
    if active:
        active_id = str(active[1].id)
        active_revision = await revisions.get(actor.tenant_id, dashboard_id, str(active[1].revision_id))
        active_contract = publication_contract(active[1], active_revision, active=True)
    access = DashboardAccessRepositoryV2(db)
    capabilities = await resolve_resource_capabilities(access, actor=actor, dashboard=dashboard)
    if DashboardCapabilityBackendV2.VIEW not in capabilities:
        raise DashboardBackendError("DASHBOARD_NOT_FOUND", "Dashboard não encontrado.", 404)
    collaborator = await access.find_for_user(actor.tenant_id, dashboard_id, actor.user_id)
    if active_contract is not None and (
        settings.DASHBOARD_BACKEND_MODE == "V2_PUBLISHED_READ"
        or (
            dashboard.owner_user_id != user.id
            and collaborator is None
            and actor.global_role != "ADMIN"
        )
    ):
        head = active_revision
    return DashboardDetailV2(dashboard=dashboard_contract(dashboard, active_id), head_revision=revision_contract(head) if head else None, active_publication=active_contract, collaborators=await DashboardAccessServiceV2(db).list(actor=actor, dashboard_id=dashboard_id) if actor.global_role == "ADMIN" else (), effective_capabilities=tuple(sorted(capabilities, key=lambda item: item.value)))


@router.patch("/{dashboard_id}", response_model=DashboardCreateResultV2)
async def update_dashboard(dashboard_id: str, request: DashboardUpdateDraftRequestV2, idempotency_key: IdempotencyKey, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> DashboardCreateResultV2:
    actor = _actor(user); _require_authoring(actor)
    return await DashboardAuthoringServiceV2(db).update_draft(actor=actor, dashboard_id=dashboard_id, request=request, idempotency_key=idempotency_key)


@router.post("/{dashboard_id}/clone", response_model=DashboardCreateResultV2, status_code=201)
async def clone_dashboard(dashboard_id: str, request: DashboardCloneRequestV2, idempotency_key: IdempotencyKey, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> DashboardCreateResultV2:
    actor = _actor(user); _require_authoring(actor)
    return await DashboardCloneServiceV2(db).clone(actor=actor, dashboard_id=dashboard_id, request=request, idempotency_key=idempotency_key)


@router.post("/{dashboard_id}/archive", response_model=DashboardRecordV2)
async def archive_dashboard(dashboard_id: str, request: DashboardArchiveRequestV2, idempotency_key: IdempotencyKey, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> DashboardRecordV2:
    actor = _actor(user); _require_authoring(actor)
    return await DashboardAuthoringServiceV2(db).archive(actor=actor, dashboard_id=dashboard_id, request=request, idempotency_key=idempotency_key)


@router.get("/{dashboard_id}/revisions", response_model=tuple[DashboardRevisionV2, ...])
async def list_revisions(dashboard_id: str, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> tuple[DashboardRevisionV2, ...]:
    actor = _actor(user); _require_authoring(actor)
    await _authorized_dashboard(db, actor=actor, dashboard_id=dashboard_id, capability=DashboardCapabilityBackendV2.EDIT_VISUAL)
    return tuple(revision_contract(row) for row in await DashboardRevisionRepositoryV2(db).list(actor.tenant_id, dashboard_id))


@router.get("/{dashboard_id}/revisions/compare")
async def compare_revisions(dashboard_id: str, left_revision_id: str, right_revision_id: str, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> dict[str, str | bool]:
    actor = _actor(user); _require_authoring(actor)
    await _authorized_dashboard(db, actor=actor, dashboard_id=dashboard_id, capability=DashboardCapabilityBackendV2.EDIT_VISUAL)
    repository = DashboardRevisionRepositoryV2(db)
    left = await repository.get(actor.tenant_id, dashboard_id, left_revision_id)
    right = await repository.get(actor.tenant_id, dashboard_id, right_revision_id)
    return {"left_revision_id": str(left.id), "right_revision_id": str(right.id), "semantic_changed": left.semantic_checksum != right.semantic_checksum, "visual_changed": left.visual_checksum != right.visual_checksum}


@router.get("/{dashboard_id}/revisions/{revision_id}", response_model=DashboardRevisionV2)
async def get_revision(dashboard_id: str, revision_id: str, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> DashboardRevisionV2:
    actor = _actor(user); _require_authoring(actor)
    await _authorized_dashboard(db, actor=actor, dashboard_id=dashboard_id, capability=DashboardCapabilityBackendV2.EDIT_VISUAL)
    return revision_contract(await DashboardRevisionRepositoryV2(db).get(actor.tenant_id, dashboard_id, revision_id))


@router.post("/{dashboard_id}/revisions", response_model=DashboardRevisionV2, status_code=201)
async def create_revision(dashboard_id: str, request: DashboardRevisionCreateRequestV2, idempotency_key: IdempotencyKey, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> DashboardRevisionV2:
    actor = _actor(user); _require_authoring(actor)
    dashboard = await DashboardRepositoryV2(db).get(actor.tenant_id, dashboard_id)
    row, _, _ = await DashboardRevisionServiceV2(db).create(actor=actor, dashboard=dashboard, request=request, idempotency_key=idempotency_key)
    return revision_contract(row)


@router.post("/{dashboard_id}/patches/visual", response_model=DashboardRevisionV2, status_code=201)
async def visual_patch(dashboard_id: str, request: DashboardVisualPatchRequestV2, idempotency_key: IdempotencyKey, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> DashboardRevisionV2:
    actor = _actor(user); _require_authoring(actor)
    return await DashboardPatchServiceV2(db).apply_visual(actor=actor, dashboard_id=dashboard_id, request=request, idempotency_key=idempotency_key)


@router.post("/{dashboard_id}/patches/semantic", response_model=DashboardRevisionV2, status_code=201)
async def semantic_patch(dashboard_id: str, request: DashboardSemanticPatchRequestV2, idempotency_key: IdempotencyKey, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> DashboardRevisionV2:
    actor = _actor(user); _require_authoring(actor)
    return await DashboardPatchServiceV2(db).apply_semantic(actor=actor, dashboard_id=dashboard_id, request=request, idempotency_key=idempotency_key)


@router.post("/{dashboard_id}/review", status_code=204)
async def submit_review(dashboard_id: str, request: DashboardReviewRequestV2, idempotency_key: IdempotencyKey, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> Response:
    actor = _actor(user); _require_authoring(actor)
    await DashboardReviewServiceV2(db).decide(actor=actor, dashboard_id=dashboard_id, revision_id=request.revision_id, expected_lock=request.expected_dashboard_lock_version, action=request.action, comment=request.comment, idempotency_key=idempotency_key)
    return Response(status_code=204)


@router.post("/{dashboard_id}/approve", response_model=DashboardApprovalV2)
async def approve_dashboard(dashboard_id: str, request: DashboardReviewDecisionV2, idempotency_key: IdempotencyKey, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> DashboardApprovalV2:
    actor = _actor(user); _require_authoring(actor)
    if request.decision is not DashboardReviewDecisionKindV2.APPROVED:
        raise DashboardBackendError("DASHBOARD_REVIEW_REQUIRED", "Decision incompatível com endpoint approve.", 422)
    approval = await DashboardReviewServiceV2(db).decide(actor=actor, dashboard_id=dashboard_id, revision_id=request.revision_id, expected_lock=request.expected_dashboard_lock_version, action="APPROVED", comment=request.comment, idempotency_key=idempotency_key)
    assert approval is not None
    return approval


@router.post("/{dashboard_id}/reject", status_code=204)
async def reject_dashboard(dashboard_id: str, request: DashboardReviewDecisionV2, idempotency_key: IdempotencyKey, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> Response:
    actor = _actor(user); _require_authoring(actor)
    if request.decision is not DashboardReviewDecisionKindV2.REJECTED:
        raise DashboardBackendError("DASHBOARD_REVIEW_REQUIRED", "Decision incompatível com endpoint reject.", 422)
    await DashboardReviewServiceV2(db).decide(actor=actor, dashboard_id=dashboard_id, revision_id=request.revision_id, expected_lock=request.expected_dashboard_lock_version, action="REJECTED", comment=request.comment, idempotency_key=idempotency_key)
    return Response(status_code=204)


@router.post("/{dashboard_id}/publish", response_model=DashboardPublicationResultV2, status_code=201)
async def publish_dashboard(dashboard_id: str, request: DashboardPublicationRequestV2, idempotency_key: IdempotencyKey, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> DashboardPublicationResultV2:
    actor = _actor(user); _require_authoring(actor)
    if not settings.DASHBOARD_PUBLISHING_ENABLED:
        raise DashboardBackendError("DASHBOARD_RUNTIME_UNAVAILABLE", "Publicação V2 desativada.", 503)
    invalidator = ExistingSmartCacheDashboardInvalidatorV2(db) if settings.DASHBOARD_RUNTIME_CACHE_ENABLED else None
    return await DashboardPublicationServiceV2(db, invalidator).publish(actor=actor, dashboard_id=dashboard_id, request=request, idempotency_key=idempotency_key)


@router.get("/{dashboard_id}/publications", response_model=tuple[DashboardPublicationV2, ...])
async def list_publications(dashboard_id: str, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> tuple[DashboardPublicationV2, ...]:
    actor = _actor(user); _require_published_read(actor)
    await _authorized_dashboard(db, actor=actor, dashboard_id=dashboard_id, capability=DashboardCapabilityBackendV2.VIEW)
    repository = DashboardPublicationRepositoryV2(db); revisions = DashboardRevisionRepositoryV2(db)
    active = await repository.active(actor.tenant_id, dashboard_id); active_id = active[1].id if active else None
    history = await repository.list_history(actor.tenant_id, dashboard_id)
    return tuple(publication_contract(row, await revisions.get(actor.tenant_id, dashboard_id, str(row.revision_id)), active=row.id == active_id) for row in history)


@router.get("/{dashboard_id}/publication", response_model=DashboardPublicationV2)
async def get_active_publication(dashboard_id: str, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> DashboardPublicationV2:
    actor = _actor(user); _require_published_read(actor)
    await _authorized_dashboard(db, actor=actor, dashboard_id=dashboard_id, capability=DashboardCapabilityBackendV2.VIEW)
    active = await DashboardPublicationRepositoryV2(db).active(actor.tenant_id, dashboard_id)
    if active is None:
        raise DashboardBackendError("DASHBOARD_PUBLICATION_NOT_FOUND", "Publicação não encontrada.", 404)
    revision = await DashboardRevisionRepositoryV2(db).get(actor.tenant_id, dashboard_id, str(active[1].revision_id))
    return publication_contract(active[1], revision, active=True)


@router.post("/{dashboard_id}/rollback", response_model=DashboardRollbackResultV2, status_code=201)
async def rollback_dashboard(dashboard_id: str, request: DashboardRollbackRequestV2, idempotency_key: IdempotencyKey, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> DashboardRollbackResultV2:
    actor = _actor(user); _require_authoring(actor)
    if not settings.DASHBOARD_ROLLBACK_ENABLED:
        raise DashboardBackendError("DASHBOARD_RUNTIME_UNAVAILABLE", "Rollback V2 desativado.", 503)
    invalidator = ExistingSmartCacheDashboardInvalidatorV2(db) if settings.DASHBOARD_RUNTIME_CACHE_ENABLED else None
    return await DashboardRollbackServiceV2(db, invalidator).rollback(actor=actor, dashboard_id=dashboard_id, request=request, idempotency_key=idempotency_key)


@router.get("/{dashboard_id}/collaborators", response_model=tuple[DashboardCollaboratorV2, ...])
async def list_collaborators(dashboard_id: str, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> tuple[DashboardCollaboratorV2, ...]:
    actor = _actor(user); _require_authoring(actor)
    if not settings.DASHBOARD_COLLABORATORS_ENABLED: raise DashboardBackendError("DASHBOARD_RUNTIME_UNAVAILABLE", "Colaboração V2 desativada.", 503)
    return await DashboardAccessServiceV2(db).list(actor=actor, dashboard_id=dashboard_id)


@router.post("/{dashboard_id}/collaborators", response_model=DashboardCollaboratorV2, status_code=201)
async def add_collaborator(dashboard_id: str, request: DashboardCollaboratorCreateRequestV2, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> DashboardCollaboratorV2:
    actor = _actor(user); _require_authoring(actor)
    if not settings.DASHBOARD_COLLABORATORS_ENABLED: raise DashboardBackendError("DASHBOARD_RUNTIME_UNAVAILABLE", "Colaboração V2 desativada.", 503)
    return await DashboardAccessServiceV2(db).add(actor=actor, dashboard_id=dashboard_id, request=request)


@router.patch("/{dashboard_id}/collaborators/{collaborator_id}", response_model=DashboardCollaboratorV2)
async def update_collaborator(dashboard_id: str, collaborator_id: str, request: DashboardCollaboratorUpdateRequestV2, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> DashboardCollaboratorV2:
    actor = _actor(user); _require_authoring(actor)
    if not settings.DASHBOARD_COLLABORATORS_ENABLED: raise DashboardBackendError("DASHBOARD_RUNTIME_UNAVAILABLE", "Colaboração V2 desativada.", 503)
    return await DashboardAccessServiceV2(db).update(actor=actor, dashboard_id=dashboard_id, collaborator_id=collaborator_id, request=request)


@router.delete("/{dashboard_id}/collaborators/{collaborator_id}", status_code=204)
async def delete_collaborator(dashboard_id: str, collaborator_id: str, expected_lock_version: int, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> Response:
    actor = _actor(user); _require_authoring(actor)
    if not settings.DASHBOARD_COLLABORATORS_ENABLED: raise DashboardBackendError("DASHBOARD_RUNTIME_UNAVAILABLE", "Colaboração V2 desativada.", 503)
    await DashboardAccessServiceV2(db).remove(actor=actor, dashboard_id=dashboard_id, collaborator_id=collaborator_id, expected_lock_version=expected_lock_version)
    return Response(status_code=204)


@router.post("/{dashboard_id}/runtime/plan", response_model=DashboardRuntimePlanV2)
async def runtime_plan(dashboard_id: str, request: DashboardRuntimeRequestV2, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> DashboardRuntimePlanV2:
    actor = _actor(user); _require_runtime(actor)
    service = await _runtime_service(db)
    plan, _, _ = await service.load_and_plan(actor=actor, dashboard_id=dashboard_id, request=request)
    return plan


@router.post("/{dashboard_id}/runtime/execute", response_model=DashboardRuntimeResultV2)
async def runtime_execute(dashboard_id: str, request: DashboardRuntimeRequestV2, idempotency_key: IdempotencyKey, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> DashboardRuntimeResultV2:
    actor = _actor(user); _require_runtime(actor)
    return await (await _runtime_service(db)).execute(actor=actor, dashboard_id=dashboard_id, request=request, idempotency_key=idempotency_key)


@router.get("/{dashboard_id}/runtime/provenance", response_model=DashboardRuntimeProvenanceV2)
async def runtime_provenance(dashboard_id: str, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> DashboardRuntimeProvenanceV2:
    actor = _actor(user); _require_runtime(actor)
    dashboard = await _authorized_dashboard(db, actor=actor, dashboard_id=dashboard_id, capability=DashboardCapabilityBackendV2.VIEW_PROVENANCE)
    if dashboard.lifecycle != "PUBLISHED":
        raise DashboardBackendError("DASHBOARD_RUNTIME_UNAVAILABLE", "Somente dashboard publicado possui proveniência de runtime.", 409)
    active = await DashboardPublicationRepositoryV2(db).active(actor.tenant_id, dashboard_id)
    if active is None: raise DashboardBackendError("DASHBOARD_PUBLICATION_NOT_FOUND", "Publicação não encontrada.", 404)
    revision = await DashboardRevisionRepositoryV2(db).get(actor.tenant_id, dashboard_id, str(active[1].revision_id))
    return DashboardRuntimeProvenanceV2(publication_id=str(active[1].id), blueprint_version=revision.blueprint_version, revision_id=str(revision.id), validation_status="CERTIFIED", source_freshness="per-widget", cache_indicator="BYPASS")


@router.get("/{dashboard_id}/audit", response_model=tuple[DashboardAuditEventV2, ...])
async def dashboard_audit(dashboard_id: str, db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]) -> tuple[DashboardAuditEventV2, ...]:
    actor = _actor(user); _require_authoring(actor)
    if not settings.DASHBOARD_AUDIT_ENABLED or actor.global_role not in {"ADMIN", "GESTOR"}: raise DashboardBackendError("DASHBOARD_PERMISSION_INSUFFICIENT", "Auditoria indisponível.", 403)
    await _authorized_dashboard(db, actor=actor, dashboard_id=dashboard_id, capability=DashboardCapabilityBackendV2.VIEW_AUDIT)
    rows = await DashboardAuditRepositoryV2(db).list_timeline(actor.tenant_id, dashboard_id)
    return tuple(DashboardAuditEventV2(event_id=str(row.id), dashboard_id=str(row.dashboard_id), event_type=row.event_type, actor_reference=str(row.actor_user_id), resource_reference=row.resource_reference, outcome=row.outcome, metadata_checksum=row.metadata_checksum, occurred_at=row.occurred_at) for row in rows)
