"""Governed authoring, revision, review and publication services."""
from __future__ import annotations

import json
import uuid
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, cast

from pydantic import JsonValue, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from contracts.dashboard_backend_v2 import (
    DashboardApprovalV2,
    DashboardArchiveRequestV2,
    DashboardAuditEventV2,
    DashboardBackupManifestV2,
    DashboardBackupTableV2,
    DashboardCapabilityBackendV2,
    DashboardCloneRequestV2,
    DashboardCollaboratorRoleV2,
    DashboardCreateRequestV2,
    DashboardCreateResultV2,
    DashboardEvaluationCaseV2,
    DashboardEvaluationResultV2,
    DashboardIdentityRecordV2,
    DashboardOwnershipTypeV2,
    DashboardOwnershipV2,
    DashboardPublicationRequestV2,
    DashboardPublicationResultV2,
    DashboardPublicationV2,
    DashboardRecordV2,
    DashboardRevisionCreateRequestV2,
    DashboardRevisionReferenceV2,
    DashboardRevisionV2,
    DashboardRollbackRequestV2,
    DashboardRollbackResultV2,
    DashboardRestoreValidationV2,
    DashboardRuntimeStatusV2,
    DashboardSemanticPatchRequestV2,
    DashboardSemanticRevisionV2,
    DashboardUpdateDraftRequestV2,
    DashboardVisualPatchRequestV2,
    DashboardVisualRevisionV2,
)
from contracts.dashboard_blueprint_v2 import (
    DashboardBlueprintV2,
    DashboardLifecycleV2,
    DashboardOriginV2,
    DashboardPatchOperationKindV2,
    DashboardRevisionV2 as BlueprintRevisionNumbersV2,
)
from models.dashboard_backend_v2 import (
    DashboardApprovalModelV2,
    DashboardAuditEventModelV2,
    DashboardModelV2,
    DashboardPublicationModelV2,
    DashboardRevisionModelV2,
)
from services.dashboard_blueprint_v2.canonicalizer import DashboardBlueprintCanonicalizer
from services.dashboard_blueprint_v2.validation_service import (
    DashboardBlueprintValidationService,
    DashboardPatchValidator,
)

from .errors import DashboardBackendError
from .integrity import checksum, idempotency_fingerprint
from .policy import DashboardAccessPolicyServiceV2, DashboardLifecycleServiceV2
from .repositories import (
    DashboardAuditRepositoryV2,
    DashboardAccessRepositoryV2,
    DashboardPublicationRepositoryV2,
    DashboardRepositoryV2,
    DashboardRevisionRepositoryV2,
    DashboardRuntimeRepositoryV2,
)


@dataclass(frozen=True, slots=True)
class DashboardActorContextV2:
    tenant_id: str
    user_id: str
    global_role: str


class DashboardCacheInvalidatorV2(Protocol):
    async def invalidate_dashboard(self, *, tenant_id: str, dashboard_id: str, semantic_checksum: str, generation: int) -> None: ...


class NoopDashboardCacheInvalidatorV2:
    """Used only while runtime cache rollout is disabled."""
    async def invalidate_dashboard(self, *, tenant_id: str, dashboard_id: str, semantic_checksum: str, generation: int) -> None:
        return None


def _uuid(value: str | uuid.UUID) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(value)


def _blueprint_from_json(payload: dict[str, object]) -> DashboardBlueprintV2:
    return DashboardBlueprintV2.model_validate_json(json.dumps(payload, ensure_ascii=False))


def revision_contract(row: DashboardRevisionModelV2) -> DashboardRevisionV2:
    blueprint = _blueprint_from_json(row.blueprint_json)
    return DashboardRevisionV2(
        revision_id=str(row.id), dashboard_id=str(row.dashboard_id),
        parent_revision_id=str(row.parent_revision_id) if row.parent_revision_id else None,
        blueprint_contract_version="lumina.dashboard-blueprint/2.0",
        blueprint_version=row.blueprint_version,
        semantic=DashboardSemanticRevisionV2(number=row.semantic_revision, checksum=row.semantic_checksum, validation_status=row.validation_status),
        visual=DashboardVisualRevisionV2(number=row.visual_revision, checksum=row.visual_checksum),
        blueprint=blueprint, blueprint_checksum=row.blueprint_checksum,
        validation_reference=f"validation:{row.blueprint_checksum}", author_reference=str(row.author_user_id),
        created_at=row.created_at, reason=row.reason, origin=DashboardOriginV2(row.origin), lock_version=row.lock_version,
    )


def revision_reference(row: DashboardRevisionModelV2) -> DashboardRevisionReferenceV2:
    return DashboardRevisionReferenceV2(
        revision_id=str(row.id), dashboard_id=str(row.dashboard_id),
        blueprint_checksum=row.blueprint_checksum, semantic_checksum=row.semantic_checksum,
        visual_checksum=row.visual_checksum,
    )


def dashboard_contract(row: DashboardModelV2, active_publication_id: str | None = None) -> DashboardRecordV2:
    return DashboardRecordV2(
        identity=DashboardIdentityRecordV2(
            dashboard_id=str(row.id), canonical_name=row.canonical_name,
            title=row.title, description=row.description,
        ),
        ownership=DashboardOwnershipV2(
            ownership_type=DashboardOwnershipTypeV2(row.ownership_type),
            owner_reference=str(row.owner_user_id),
        ),
        lifecycle=DashboardLifecycleV2(row.lifecycle), head_lifecycle=DashboardLifecycleV2(row.head_lifecycle), origin=DashboardOriginV2(row.origin),
        classification=row.classification,
        head_revision_id=str(row.head_revision_id) if row.head_revision_id else None,
        active_publication_id=active_publication_id,
        lock_version=row.lock_version, created_at=row.created_at, updated_at=row.updated_at,
    )


def publication_contract(row: DashboardPublicationModelV2, revision: DashboardRevisionModelV2, *, active: bool) -> DashboardPublicationV2:
    return DashboardPublicationV2(
        publication_id=str(row.id), dashboard_id=str(row.dashboard_id), revision=revision_reference(revision),
        publication_version=row.publication_version, generation=row.generation,
        status="PUBLISHED" if active else "SUPERSEDED",
        supersedes_publication_id=str(row.supersedes_publication_id) if row.supersedes_publication_id else None,
        published_by=str(row.published_by_user_id), published_at=row.published_at,
    )


async def _require_resource_access(
    access_repository: DashboardAccessRepositoryV2,
    *, actor: DashboardActorContextV2, dashboard: DashboardModelV2,
    capability: DashboardCapabilityBackendV2,
) -> None:
    capabilities = await resolve_resource_capabilities(
        access_repository, actor=actor, dashboard=dashboard,
    )
    if capability not in capabilities:
        raise DashboardBackendError(
            "DASHBOARD_PERMISSION_INSUFFICIENT", "Permissão insuficiente.", 403
        )


async def resolve_resource_capabilities(
    access_repository: DashboardAccessRepositoryV2,
    *, actor: DashboardActorContextV2, dashboard: DashboardModelV2,
) -> frozenset[DashboardCapabilityBackendV2]:
    collaborator = await access_repository.find_for_user(actor.tenant_id, str(dashboard.id), actor.user_id)
    tenant_policy_capabilities: frozenset[DashboardCapabilityBackendV2] = frozenset()
    if dashboard.lifecycle == "PUBLISHED":
        policy = await access_repository.get_policy(actor.tenant_id, str(dashboard.id))
        tenant_policy_capabilities = frozenset(
            DashboardCapabilityBackendV2(value) for value in policy.capabilities_json
        )
    return DashboardAccessPolicyServiceV2.effective_capabilities(
        global_role=actor.global_role,
        is_owner=dashboard.owner_user_id == _uuid(actor.user_id),
        collaborator_role=DashboardCollaboratorRoleV2(collaborator.role) if collaborator else None,
        tenant_policy_capabilities=tenant_policy_capabilities,
    )


class DashboardAuditServiceV2:
    def __init__(self, repository: DashboardAuditRepositoryV2):
        self.repository = repository

    async def append(self, *, actor: DashboardActorContextV2, dashboard_id: str | uuid.UUID, event_type: str, resource_reference: str | None = None, outcome: str = "SUCCESS", metadata: dict[str, object] | None = None, idempotency_scope: str | None = None) -> DashboardAuditEventV2:
        safe_metadata = metadata or {}
        row = await self.repository.append_event(
            id=uuid.uuid4(), tenant_id=_uuid(actor.tenant_id), dashboard_id=_uuid(dashboard_id),
            actor_user_id=_uuid(actor.user_id), event_type=event_type,
            resource_reference=resource_reference, outcome=outcome,
            metadata_json=safe_metadata, metadata_checksum=checksum(safe_metadata),
            idempotency_scope=idempotency_scope,
        )
        return DashboardAuditEventV2(
            event_id=str(row.id), dashboard_id=str(row.dashboard_id), event_type=row.event_type,
            actor_reference=str(row.actor_user_id), resource_reference=row.resource_reference,
            outcome=cast(object, row.outcome), metadata_checksum=row.metadata_checksum,
            occurred_at=row.occurred_at,
        )


class DashboardRevisionServiceV2:
    def __init__(self, session: AsyncSession):
        self.dashboard_repository = DashboardRepositoryV2(session)
        self.revision_repository = DashboardRevisionRepositoryV2(session)
        self.access_repository = DashboardAccessRepositoryV2(session)

    @staticmethod
    def validate_blueprint(blueprint: DashboardBlueprintV2) -> tuple[object, object]:
        validation = DashboardBlueprintValidationService.validate_payload(blueprint)
        if validation.status.value != "VALID" or validation.canonicalization is None:
            raise DashboardBackendError("DASHBOARD_BLUEPRINT_BLOCKED", "Blueprint bloqueado pela validação governada.", 422)
        return validation, validation.canonicalization

    async def create(
        self,
        *, actor: DashboardActorContextV2, dashboard: DashboardModelV2,
        request: DashboardRevisionCreateRequestV2, idempotency_key: str,
        required_capability: DashboardCapabilityBackendV2 = DashboardCapabilityBackendV2.EDIT_SEMANTIC,
        idempotency_operation: str = "CREATE_REVISION",
        idempotency_payload: object | None = None,
    ) -> tuple[DashboardRevisionModelV2, DashboardModelV2, bool]:
        await _require_resource_access(self.access_repository, actor=actor, dashboard=dashboard, capability=required_capability)
        scope, request_checksum = idempotency_fingerprint(
            tenant_id=actor.tenant_id, user_id=actor.user_id, operation=idempotency_operation,
            resource_id=str(dashboard.id), key=idempotency_key,
            payload=request if idempotency_payload is None else idempotency_payload,
        )
        replay = await self.revision_repository.find_revision_replay(actor.tenant_id, scope, request_checksum)
        if replay is not None:
            return replay, dashboard, True
        if dashboard.lifecycle in {"SUPERSEDED", "DEPRECATED", "ARCHIVED"}:
            raise DashboardBackendError("DASHBOARD_INVALID_LIFECYCLE_TRANSITION", "O estado atual não permite editar o head.", 409)
        if request.base_revision_id and str(dashboard.head_revision_id) != request.base_revision_id:
            raise DashboardBackendError("DASHBOARD_REVISION_STALE", "A revisão base não é o head atual.", 409)
        validation, canonical = self.validate_blueprint(request.blueprint)
        history = await self.revision_repository.list(actor.tenant_id, str(dashboard.id), 1)
        existing = await self.revision_repository.find_by_checksum(actor.tenant_id, str(dashboard.id), canonical.checksums.blueprint_checksum)
        if existing is not None and existing.idempotency_scope == scope:
            if existing.request_checksum != request_checksum:
                raise DashboardBackendError("DASHBOARD_IDEMPOTENCY_CONFLICT", "Chave reutilizada com conteúdo divergente.", 409)
            return existing, dashboard, True
        row = await self.revision_repository.create_revision(
            id=uuid.uuid4(), dashboard_id=dashboard.id, tenant_id=dashboard.tenant_id,
            parent_revision_id=dashboard.head_revision_id,
            revision_number=(history[0].revision_number + 1) if history else 1,
            blueprint_contract_version=request.blueprint.version.contract_version,
            blueprint_version=request.blueprint.version.blueprint_version,
            semantic_revision=request.blueprint.version.revision.semantic_revision,
            visual_revision=request.blueprint.version.revision.visual_revision,
            blueprint_json=json.loads(canonical.canonical_json),
            blueprint_checksum=canonical.checksums.blueprint_checksum,
            semantic_checksum=canonical.checksums.semantic_checksum,
            visual_checksum=canonical.checksums.visual_checksum,
            validation_status="VALID", validation_json=validation.model_dump(mode="json"),
            author_user_id=_uuid(actor.user_id), reason=request.reason,
            origin=request.blueprint.created_origin.value, lock_version=1,
            idempotency_scope=scope, request_checksum=request_checksum,
        )
        updated = await self.dashboard_repository.set_head_and_lifecycle_cas(
            actor.tenant_id, str(dashboard.id), request.expected_dashboard_lock_version,
            revision_id=row.id, lifecycle="DRAFT" if dashboard.lifecycle != "PUBLISHED" else None,
            head_lifecycle="DRAFT",
        )
        return row, updated, False


class DashboardAuthoringServiceV2:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.dashboard_repository = DashboardRepositoryV2(session)
        self.revision_service = DashboardRevisionServiceV2(session)
        self.revision_repository = DashboardRevisionRepositoryV2(session)
        self.access_repository = DashboardAccessRepositoryV2(session)
        self.audit = DashboardAuditServiceV2(DashboardAuditRepositoryV2(session))

    async def create(
        self, *, actor: DashboardActorContextV2, request: DashboardCreateRequestV2,
        idempotency_key: str, idempotency_operation: str = "CREATE_DASHBOARD",
        idempotency_payload: object | None = None,
        idempotency_resource_id: str | None = None,
        attribution_dashboard_id: uuid.UUID | None = None,
    ) -> DashboardCreateResultV2:
        DashboardAccessPolicyServiceV2.require(DashboardCapabilityBackendV2.CREATE, global_role=actor.global_role, is_owner=True, collaborator_role=None)
        if request.canonical_name != request.blueprint.identity.canonical_name:
            raise DashboardBackendError("DASHBOARD_BLUEPRINT_INVALID", "Identidade do blueprint diverge do dashboard.", 422)
        _, canonical = self.revision_service.validate_blueprint(request.blueprint)
        scope, request_checksum = idempotency_fingerprint(
            tenant_id=actor.tenant_id, user_id=actor.user_id,
            operation=idempotency_operation,
            resource_id=idempotency_resource_id or request.canonical_name,
            key=idempotency_key,
            payload=request if idempotency_payload is None else idempotency_payload,
        )
        replay = await self.dashboard_repository.find_create_replay(actor.tenant_id, scope, request_checksum)
        if replay is not None:
            if replay.head_revision_id is None:
                raise DashboardBackendError("DASHBOARD_VERSION_CONFLICT", "Criação incompleta detectada.", 409)
            revision = await self.revision_repository.get(actor.tenant_id, str(replay.id), str(replay.head_revision_id))
            return DashboardCreateResultV2(dashboard=dashboard_contract(replay), revision=revision_contract(revision), replayed=True)
        dashboard_id = uuid.uuid4()
        dashboard = await self.dashboard_repository.create_draft(
            id=dashboard_id, tenant_id=_uuid(actor.tenant_id), canonical_name=request.canonical_name,
            title=request.title, description=request.description, owner_user_id=_uuid(actor.user_id),
            ownership_type="USER", origin=request.origin.value, lifecycle="DRAFT", head_lifecycle="DRAFT",
            classification=request.blueprint.governance.classification.value, lock_version=1,
            create_idempotency_scope=scope, create_request_checksum=request_checksum,
            attribution_dashboard_id=attribution_dashboard_id,
        )
        await self.access_repository.create_policy(
            id=uuid.uuid4(), dashboard_id=dashboard_id, tenant_id=_uuid(actor.tenant_id),
            minimum_role=request.blueprint.audience.minimum_role,
            capabilities_json=["dashboard:view", "dashboard:execute", "dashboard:view_provenance"],
            classification_ceiling=request.blueprint.governance.classification.value,
            allow_partial_runtime=True, lock_version=1,
        )
        revision_scope, revision_request_checksum = idempotency_fingerprint(tenant_id=actor.tenant_id, user_id=actor.user_id, operation="CREATE_REVISION", resource_id=str(dashboard_id), key=f"{idempotency_key}:initial", payload=request.blueprint)
        validation = DashboardBlueprintValidationService.validate_payload(request.blueprint)
        revision = await self.revision_repository.create_revision(
            id=uuid.uuid4(), dashboard_id=dashboard_id, tenant_id=_uuid(actor.tenant_id), parent_revision_id=None,
            revision_number=1, blueprint_contract_version=request.blueprint.version.contract_version,
            blueprint_version=request.blueprint.version.blueprint_version,
            semantic_revision=request.blueprint.version.revision.semantic_revision,
            visual_revision=request.blueprint.version.revision.visual_revision,
            blueprint_json=json.loads(canonical.canonical_json), blueprint_checksum=canonical.checksums.blueprint_checksum,
            semantic_checksum=canonical.checksums.semantic_checksum, visual_checksum=canonical.checksums.visual_checksum,
            validation_status="VALID", validation_json=validation.model_dump(mode="json"), author_user_id=_uuid(actor.user_id),
            reason=request.reason, origin=request.origin.value, lock_version=1,
            idempotency_scope=revision_scope, request_checksum=revision_request_checksum,
        )
        dashboard = await self.dashboard_repository.set_head_and_lifecycle_cas(actor.tenant_id, str(dashboard_id), 1, revision_id=revision.id, lifecycle="DRAFT", head_lifecycle="DRAFT")
        await self.audit.append(actor=actor, dashboard_id=dashboard_id, event_type="DASHBOARD_CREATED", resource_reference=str(revision.id), metadata={"canonical_name": request.canonical_name, "blueprint_checksum": revision.blueprint_checksum})
        return DashboardCreateResultV2(dashboard=dashboard_contract(dashboard), revision=revision_contract(revision))

    async def update_draft(self, *, actor: DashboardActorContextV2, dashboard_id: str, request: DashboardUpdateDraftRequestV2, idempotency_key: str) -> DashboardCreateResultV2:
        dashboard = await self.dashboard_repository.get(actor.tenant_id, dashboard_id)
        is_owner = dashboard.owner_user_id == _uuid(actor.user_id)
        await _require_resource_access(self.access_repository, actor=actor, dashboard=dashboard, capability=DashboardCapabilityBackendV2.EDIT_VISUAL)
        if dashboard.head_lifecycle != "DRAFT" or dashboard.head_revision_id is None:
            raise DashboardBackendError("DASHBOARD_INVALID_LIFECYCLE_TRANSITION", "Somente draft pode ser atualizado.", 409)
        base = await self.revision_repository.get(actor.tenant_id, dashboard_id, str(dashboard.head_revision_id))
        blueprint = _blueprint_from_json(base.blueprint_json)
        new_identity = blueprint.identity.model_copy(update={
            "title": request.title if request.title is not None else blueprint.identity.title,
            "description": request.description if request.description is not None else blueprint.identity.description,
        })
        new_numbers = blueprint.version.revision.model_copy(update={"visual_revision": blueprint.version.revision.visual_revision + 1})
        updated_blueprint = blueprint.model_copy(update={"identity": new_identity, "version": blueprint.version.model_copy(update={"revision": new_numbers})})
        revision, updated, replayed = await self.revision_service.create(
            actor=actor, dashboard=dashboard,
            request=DashboardRevisionCreateRequestV2(blueprint=updated_blueprint, base_revision_id=str(base.id), expected_dashboard_lock_version=request.expected_lock_version, reason=request.reason),
            idempotency_key=idempotency_key,
            required_capability=DashboardCapabilityBackendV2.EDIT_VISUAL,
            idempotency_operation="UPDATE_DRAFT", idempotency_payload=request,
        )
        if replayed:
            current = await self.dashboard_repository.get(actor.tenant_id, dashboard_id)
            return DashboardCreateResultV2(dashboard=dashboard_contract(current), revision=revision_contract(revision), replayed=True)
        await self.dashboard_repository.update_metadata_cas(actor.tenant_id, dashboard_id, updated.lock_version, title=request.title, description=request.description)
        final = await self.dashboard_repository.get(actor.tenant_id, dashboard_id)
        await self.audit.append(actor=actor, dashboard_id=dashboard_id, event_type="DASHBOARD_METADATA_UPDATED", resource_reference=str(revision.id), metadata={"blueprint_checksum": revision.blueprint_checksum})
        return DashboardCreateResultV2(dashboard=dashboard_contract(final), revision=revision_contract(revision), replayed=replayed)

    async def archive(self, *, actor: DashboardActorContextV2, dashboard_id: str, request: DashboardArchiveRequestV2, idempotency_key: str) -> DashboardRecordV2:
        dashboard = await self.dashboard_repository.get(actor.tenant_id, dashboard_id)
        await _require_resource_access(self.access_repository, actor=actor, dashboard=dashboard, capability=DashboardCapabilityBackendV2.ARCHIVE)
        scope, request_checksum = idempotency_fingerprint(tenant_id=actor.tenant_id, user_id=actor.user_id, operation="ARCHIVE", resource_id=dashboard_id, key=idempotency_key, payload=request)
        replay = await self.audit.repository.find_by_idempotency(actor.tenant_id, scope, request_checksum)
        if replay is not None:
            return dashboard_contract(dashboard)
        if dashboard.lifecycle == "ARCHIVED":
            raise DashboardBackendError("DASHBOARD_IDEMPOTENCY_CONFLICT", "Archive existente exige a chave original.", 409)
        current_lifecycle = DashboardLifecycleV2(dashboard.lifecycle)
        if current_lifecycle is DashboardLifecycleV2.PUBLISHED:
            DashboardLifecycleServiceV2.assert_transition(current_lifecycle, DashboardLifecycleV2.DEPRECATED)
            DashboardLifecycleServiceV2.assert_transition(DashboardLifecycleV2.DEPRECATED, DashboardLifecycleV2.ARCHIVED)
        else:
            DashboardLifecycleServiceV2.assert_transition(current_lifecycle, DashboardLifecycleV2.ARCHIVED)
        updated = await self.dashboard_repository.set_head_and_lifecycle_cas(actor.tenant_id, dashboard_id, request.expected_dashboard_lock_version, lifecycle="ARCHIVED", head_lifecycle="ARCHIVED")
        await self.audit.append(actor=actor, dashboard_id=dashboard_id, event_type="DASHBOARD_ARCHIVED", metadata={"reason_checksum": checksum(request.reason), "request_checksum": request_checksum}, idempotency_scope=scope)
        return dashboard_contract(updated)


def _resolve_pointer(document: object, pointer: str, *, parent: bool) -> tuple[object, str]:
    segments = [segment.replace("~1", "/").replace("~0", "~") for segment in pointer.strip("/").split("/")]
    if not segments or segments == [""]:
        raise DashboardBackendError("DASHBOARD_PATCH_INVALID", "Patch na raiz é proibido.", 422)
    current = document
    for segment in segments[:-1] if parent else segments:
        if isinstance(current, list):
            try:
                current = current[int(segment)]
            except (ValueError, IndexError) as exc:
                raise DashboardBackendError("DASHBOARD_PATCH_INVALID", "Índice de patch inválido.", 422) from exc
        elif isinstance(current, dict) and segment in current:
            current = current[segment]
        else:
            raise DashboardBackendError("DASHBOARD_PATCH_INVALID", "Caminho de patch inexistente.", 422)
    return current, segments[-1]


def _apply_operations(payload: dict[str, JsonValue], operations: tuple[object, ...]) -> dict[str, JsonValue]:
    result = deepcopy(payload)
    for operation in operations:
        op = cast(object, operation)
        target, key = _resolve_pointer(result, op.path, parent=True)
        if op.operation is DashboardPatchOperationKindV2.MOVE:
            source, source_key = _resolve_pointer(result, op.from_path, parent=True)
            value = source.pop(int(source_key)) if isinstance(source, list) else source.pop(source_key)
        else:
            value = op.value
        if isinstance(target, list):
            try:
                index = len(target) if key == "-" else int(key)
                if op.operation is DashboardPatchOperationKindV2.ADD:
                    target.insert(index, value)
                elif op.operation in {DashboardPatchOperationKindV2.REPLACE, DashboardPatchOperationKindV2.MOVE}:
                    target[index] = value
                else:
                    target.pop(index)
            except (ValueError, IndexError) as exc:
                raise DashboardBackendError("DASHBOARD_PATCH_INVALID", "Índice de patch inválido.", 422) from exc
        elif isinstance(target, dict):
            if op.operation is DashboardPatchOperationKindV2.REMOVE:
                if key not in target:
                    raise DashboardBackendError("DASHBOARD_PATCH_INVALID", "Caminho de remoção inexistente.", 422)
                target.pop(key)
            else:
                if op.operation is DashboardPatchOperationKindV2.REPLACE and key not in target:
                    raise DashboardBackendError("DASHBOARD_PATCH_INVALID", "Caminho de substituição inexistente.", 422)
                target[key] = value
        else:
            raise DashboardBackendError("DASHBOARD_PATCH_INVALID", "Destino de patch inválido.", 422)
    return result


class DashboardPatchServiceV2:
    def __init__(self, session: AsyncSession):
        self.dashboard_repository = DashboardRepositoryV2(session)
        self.revision_repository = DashboardRevisionRepositoryV2(session)
        self.revision_service = DashboardRevisionServiceV2(session)
        self.access_repository = DashboardAccessRepositoryV2(session)
        self.audit = DashboardAuditServiceV2(DashboardAuditRepositoryV2(session))

    async def apply_visual(self, *, actor: DashboardActorContextV2, dashboard_id: str, request: DashboardVisualPatchRequestV2, idempotency_key: str) -> DashboardRevisionV2:
        dashboard = await self.dashboard_repository.get(actor.tenant_id, dashboard_id)
        await _require_resource_access(self.access_repository, actor=actor, dashboard=dashboard, capability=DashboardCapabilityBackendV2.EDIT_VISUAL)
        base = await self.revision_repository.find_by_checksum(actor.tenant_id, dashboard_id, request.patch.base_blueprint_checksum)
        if base is None:
            raise DashboardBackendError("DASHBOARD_REVISION_NOT_FOUND", "Revisão base não encontrada.", 404)
        if base.lock_version != request.expected_revision_lock_version or base.blueprint_checksum != request.patch.base_blueprint_checksum or base.semantic_checksum != request.patch.base_semantic_checksum or base.visual_revision != request.patch.base_visual_revision:
            raise DashboardBackendError("DASHBOARD_REVISION_STALE", "Patch visual baseado em revisão obsoleta.", 409)
        if any(issue.blocking for issue in DashboardPatchValidator.validate_visual(request.patch)):
            raise DashboardBackendError("DASHBOARD_PATCH_INVALID", "Patch visual fora da allowlist.", 422)
        raw = _apply_operations(cast(dict[str, JsonValue], deepcopy(base.blueprint_json)), request.patch.operations)
        revision_node = cast(dict[str, JsonValue], cast(dict[str, JsonValue], raw["version"])["revision"])
        revision_node["visual_revision"] = request.patch.target_visual_revision
        try:
            blueprint = DashboardBlueprintV2.model_validate_json(json.dumps(raw, ensure_ascii=False))
        except ValidationError as exc:
            raise DashboardBackendError("DASHBOARD_BLUEPRINT_INVALID", "Patch visual produziu blueprint inválido.", 422) from exc
        canonical = DashboardBlueprintCanonicalizer.canonicalize(blueprint)
        if canonical.checksums.semantic_checksum != base.semantic_checksum:
            raise DashboardBackendError("DASHBOARD_VISUAL_PATCH_SEMANTIC_CHANGE", "Patch visual alterou semântica.", 422)
        row, _, replayed = await self.revision_service.create(
            actor=actor, dashboard=dashboard,
            request=DashboardRevisionCreateRequestV2(blueprint=blueprint, base_revision_id=str(base.id), expected_dashboard_lock_version=request.expected_dashboard_lock_version, reason=request.reason),
            idempotency_key=idempotency_key,
            required_capability=DashboardCapabilityBackendV2.EDIT_VISUAL,
            idempotency_operation="VISUAL_PATCH", idempotency_payload=request,
        )
        if not replayed:
            await self.audit.append(actor=actor, dashboard_id=dashboard_id, event_type="DASHBOARD_VISUAL_PATCH_APPLIED", resource_reference=str(row.id), metadata={"visual_checksum": row.visual_checksum})
        return revision_contract(row)

    async def apply_semantic(self, *, actor: DashboardActorContextV2, dashboard_id: str, request: DashboardSemanticPatchRequestV2, idempotency_key: str) -> DashboardRevisionV2:
        dashboard = await self.dashboard_repository.get(actor.tenant_id, dashboard_id)
        await _require_resource_access(self.access_repository, actor=actor, dashboard=dashboard, capability=DashboardCapabilityBackendV2.EDIT_SEMANTIC)
        base = await self.revision_repository.find_by_checksum(actor.tenant_id, dashboard_id, request.patch.base_blueprint_checksum)
        if base is None:
            raise DashboardBackendError("DASHBOARD_REVISION_NOT_FOUND", "Revisão base não encontrada.", 404)
        if base.lock_version != request.expected_revision_lock_version or base.blueprint_checksum != request.patch.base_blueprint_checksum or base.semantic_checksum != request.patch.base_semantic_checksum or base.semantic_revision != request.patch.base_semantic_revision:
            raise DashboardBackendError("DASHBOARD_REVISION_STALE", "Patch semântico baseado em revisão obsoleta.", 409)
        if not request.patch.requires_revalidation:
            raise DashboardBackendError("DASHBOARD_SEMANTIC_PATCH_REVALIDATION_REQUIRED", "Revalidação é obrigatória.", 422)
        if any(issue.blocking for issue in DashboardPatchValidator.validate_semantic(request.patch)):
            raise DashboardBackendError("DASHBOARD_PATCH_INVALID", "Patch semântico fora da allowlist.", 422)
        raw = _apply_operations(cast(dict[str, JsonValue], deepcopy(base.blueprint_json)), request.patch.operations)
        revision_node = cast(dict[str, JsonValue], cast(dict[str, JsonValue], raw["version"])["revision"])
        revision_node["semantic_revision"] = request.patch.target_semantic_revision
        raw["lifecycle"] = "DRAFT"
        try:
            blueprint = DashboardBlueprintV2.model_validate_json(json.dumps(raw, ensure_ascii=False))
        except ValidationError as exc:
            raise DashboardBackendError("DASHBOARD_BLUEPRINT_INVALID", "Patch semântico produziu blueprint inválido.", 422) from exc
        canonical = DashboardBlueprintCanonicalizer.canonicalize(blueprint)
        if canonical.checksums.semantic_checksum == base.semantic_checksum:
            raise DashboardBackendError("DASHBOARD_PATCH_INVALID", "Patch semântico não produziu mudança semântica.", 422)
        row, _, replayed = await self.revision_service.create(
            actor=actor, dashboard=dashboard,
            request=DashboardRevisionCreateRequestV2(blueprint=blueprint, base_revision_id=str(base.id), expected_dashboard_lock_version=request.expected_dashboard_lock_version, reason=request.reason),
            idempotency_key=idempotency_key,
            idempotency_operation="SEMANTIC_PATCH", idempotency_payload=request,
        )
        if not replayed:
            await self.audit.append(actor=actor, dashboard_id=dashboard_id, event_type="DASHBOARD_SEMANTIC_PATCH_APPLIED", resource_reference=str(row.id), metadata={"semantic_checksum": row.semantic_checksum})
        return revision_contract(row)


class DashboardReviewServiceV2:
    def __init__(self, session: AsyncSession):
        self.dashboard_repository = DashboardRepositoryV2(session)
        self.revision_repository = DashboardRevisionRepositoryV2(session)
        self.access_repository = DashboardAccessRepositoryV2(session)
        self.audit = DashboardAuditServiceV2(DashboardAuditRepositoryV2(session))

    async def decide(self, *, actor: DashboardActorContextV2, dashboard_id: str, revision_id: str, expected_lock: int, action: str, comment: str, idempotency_key: str) -> DashboardApprovalV2 | None:
        dashboard = await self.dashboard_repository.get(actor.tenant_id, dashboard_id)
        required_capability = DashboardCapabilityBackendV2.APPROVE if action == "APPROVED" else DashboardCapabilityBackendV2.REVIEW
        await _require_resource_access(self.access_repository, actor=actor, dashboard=dashboard, capability=required_capability)
        revision = await self.revision_repository.get(actor.tenant_id, dashboard_id, revision_id)
        transitions = {"SUBMITTED": "IN_REVIEW", "CHANGES_REQUESTED": "DRAFT", "APPROVED": "APPROVED", "REJECTED": "REJECTED"}
        target = DashboardLifecycleV2(transitions[action])
        if action == "APPROVED" and revision.author_user_id == _uuid(actor.user_id):
            raise DashboardBackendError("DASHBOARD_ACCESS_DENIED", "O autor da revisão não pode aprová-la.", 403)
        operation = f"REVIEW_{action}"
        scope, request_checksum = idempotency_fingerprint(tenant_id=actor.tenant_id, user_id=actor.user_id, operation=operation, resource_id=dashboard_id, key=idempotency_key, payload={"revision_id": revision_id, "action": action, "comment": comment})
        replay = await self.revision_repository.find_review_replay(actor.tenant_id, scope, request_checksum)
        if replay is not None:
            if action == "APPROVED":
                approval = await self.revision_repository.approval_for_revision(actor.tenant_id, dashboard_id, revision_id, revision.blueprint_checksum)
                if approval is None:
                    raise DashboardBackendError("DASHBOARD_APPROVAL_REQUIRED", "Replay de aprovação incompleto.", 409)
                return DashboardApprovalV2(approval_id=str(approval.id), dashboard_id=dashboard_id, revision=revision_reference(revision), approved_by=str(approval.approved_by_user_id), approved_at=approval.approved_at)
            return None
        DashboardLifecycleServiceV2.assert_transition(DashboardLifecycleV2(dashboard.head_lifecycle), target)
        await self.revision_repository.append_review(id=uuid.uuid4(), dashboard_id=dashboard.id, tenant_id=dashboard.tenant_id, revision_id=revision.id, actor_user_id=_uuid(actor.user_id), action=action, comment=comment, dashboard_lock_version=expected_lock, idempotency_scope=scope, request_checksum=request_checksum)
        await self.dashboard_repository.set_head_and_lifecycle_cas(
            actor.tenant_id, dashboard_id, expected_lock,
            lifecycle=target.value if dashboard.lifecycle != "PUBLISHED" else None,
            head_lifecycle=target.value,
        )
        approval_contract: DashboardApprovalV2 | None = None
        if action == "APPROVED":
            approval_scope, approval_checksum = idempotency_fingerprint(tenant_id=actor.tenant_id, user_id=actor.user_id, operation="APPROVE", resource_id=revision_id, key=f"{idempotency_key}:approval", payload={"revision": revision_id, "checksum": revision.blueprint_checksum})
            approval = await self.revision_repository.create_approval(id=uuid.uuid4(), dashboard_id=dashboard.id, tenant_id=dashboard.tenant_id, revision_id=revision.id, blueprint_checksum=revision.blueprint_checksum, semantic_checksum=revision.semantic_checksum, visual_checksum=revision.visual_checksum, approved_by_user_id=_uuid(actor.user_id), idempotency_scope=approval_scope, request_checksum=approval_checksum)
            approval_contract = DashboardApprovalV2(approval_id=str(approval.id), dashboard_id=dashboard_id, revision=revision_reference(revision), approved_by=str(approval.approved_by_user_id), approved_at=approval.approved_at)
        event = {"SUBMITTED": "DASHBOARD_SUBMITTED_FOR_REVIEW", "CHANGES_REQUESTED": "DASHBOARD_REVIEW_CHANGES_REQUESTED", "APPROVED": "DASHBOARD_APPROVED", "REJECTED": "DASHBOARD_REJECTED"}[action]
        await self.audit.append(actor=actor, dashboard_id=dashboard_id, event_type=event, resource_reference=revision_id, metadata={"revision_checksum": revision.blueprint_checksum})
        return approval_contract


class DashboardPublicationServiceV2:
    def __init__(self, session: AsyncSession, invalidator: DashboardCacheInvalidatorV2 | None = None):
        self.dashboard_repository = DashboardRepositoryV2(session)
        self.revision_repository = DashboardRevisionRepositoryV2(session)
        self.publication_repository = DashboardPublicationRepositoryV2(session)
        self.access_repository = DashboardAccessRepositoryV2(session)
        self.audit = DashboardAuditServiceV2(DashboardAuditRepositoryV2(session))
        self.invalidator = invalidator or NoopDashboardCacheInvalidatorV2()

    async def publish(self, *, actor: DashboardActorContextV2, dashboard_id: str, request: DashboardPublicationRequestV2, idempotency_key: str, rollback_source: DashboardPublicationModelV2 | None = None) -> DashboardPublicationResultV2:
        dashboard = await self.dashboard_repository.get(actor.tenant_id, dashboard_id)
        await _require_resource_access(self.access_repository, actor=actor, dashboard=dashboard, capability=DashboardCapabilityBackendV2.PUBLISH)
        scope, request_checksum = idempotency_fingerprint(tenant_id=actor.tenant_id, user_id=actor.user_id, operation="ROLLBACK" if rollback_source else "PUBLISH", resource_id=dashboard_id, key=idempotency_key, payload=request)
        replay = await self.publication_repository.find_replay(actor.tenant_id, scope, request_checksum)
        if replay is not None:
            replay_revision = await self.revision_repository.get(actor.tenant_id, dashboard_id, str(replay.revision_id))
            active_replay = await self.publication_repository.active(actor.tenant_id, dashboard_id)
            return DashboardPublicationResultV2(publication=publication_contract(replay, replay_revision, active=active_replay is not None and active_replay[1].id == replay.id), superseded_publication_id=str(replay.supersedes_publication_id) if replay.supersedes_publication_id else None, replayed=True)
        if dashboard.head_lifecycle != "APPROVED" and rollback_source is None:
            raise DashboardBackendError("DASHBOARD_APPROVAL_REQUIRED", "Publicação exige lifecycle APPROVED.", 409)
        revision = await self.revision_repository.get(actor.tenant_id, dashboard_id, request.revision_id)
        DashboardRevisionServiceV2.validate_blueprint(_blueprint_from_json(revision.blueprint_json))
        approval = await self.revision_repository.approval_for_revision(actor.tenant_id, dashboard_id, request.revision_id, revision.blueprint_checksum)
        if approval is None:
            raise DashboardBackendError("DASHBOARD_APPROVAL_REQUIRED", "Aprovação vinculada ao checksum é obrigatória.", 409)
        active = await self.publication_repository.active(actor.tenant_id, dashboard_id)
        current_row = active[1] if active else None
        actual_generation = active[0].generation if active else 0
        if actual_generation != request.expected_active_generation:
            raise DashboardBackendError("DASHBOARD_PUBLICATION_CONFLICT", "Generation ativa obsoleta.", 409)
        publication = await self.publication_repository.create_publication(
            id=uuid.uuid4(), dashboard_id=dashboard.id, tenant_id=dashboard.tenant_id,
            revision_id=revision.id, approval_id=approval.id,
            supersedes_publication_id=current_row.id if current_row else None,
            rollback_source_publication_id=rollback_source.id if rollback_source else None,
            publication_version=request.publication_version, generation=actual_generation + 1,
            blueprint_checksum=revision.blueprint_checksum, semantic_checksum=revision.semantic_checksum,
            visual_checksum=revision.visual_checksum, published_by_user_id=_uuid(actor.user_id),
            idempotency_scope=scope, request_checksum=request_checksum,
        )
        await self.publication_repository.cas_active_pointer(actor.tenant_id, dashboard_id, publication.id, expected_generation=actual_generation, new_generation=actual_generation + 1)
        if rollback_source is None:
            await self.dashboard_repository.set_head_and_lifecycle_cas(actor.tenant_id, dashboard_id, request.expected_dashboard_lock_version, lifecycle="PUBLISHED", head_lifecycle="PUBLISHED")
        await self.invalidator.invalidate_dashboard(tenant_id=actor.tenant_id, dashboard_id=dashboard_id, semantic_checksum=revision.semantic_checksum, generation=actual_generation + 1)
        if current_row is not None:
            await self.audit.append(
                actor=actor, dashboard_id=dashboard_id,
                event_type="DASHBOARD_PUBLICATION_SUPERSEDED",
                resource_reference=str(current_row.id),
                metadata={"superseded_by": str(publication.id), "generation": publication.generation},
            )
        await self.audit.append(actor=actor, dashboard_id=dashboard_id, event_type="DASHBOARD_ROLLBACK_COMPLETED" if rollback_source else "DASHBOARD_PUBLISHED", resource_reference=str(publication.id), metadata={"generation": publication.generation, "blueprint_checksum": publication.blueprint_checksum})
        return DashboardPublicationResultV2(publication=publication_contract(publication, revision, active=True), superseded_publication_id=str(current_row.id) if current_row else None)


class DashboardRollbackServiceV2:
    def __init__(self, session: AsyncSession, invalidator: DashboardCacheInvalidatorV2 | None = None):
        self.dashboard_repository = DashboardRepositoryV2(session)
        self.revision_repository = DashboardRevisionRepositoryV2(session)
        self.publication_repository = DashboardPublicationRepositoryV2(session)
        self.access_repository = DashboardAccessRepositoryV2(session)
        self.publication_service = DashboardPublicationServiceV2(session, invalidator)

    async def rollback(self, *, actor: DashboardActorContextV2, dashboard_id: str, request: DashboardRollbackRequestV2, idempotency_key: str) -> DashboardRollbackResultV2:
        dashboard = await self.dashboard_repository.get(actor.tenant_id, dashboard_id)
        await _require_resource_access(self.access_repository, actor=actor, dashboard=dashboard, capability=DashboardCapabilityBackendV2.ROLLBACK)
        active = await self.publication_repository.active(actor.tenant_id, dashboard_id)
        if active is None:
            raise DashboardBackendError("DASHBOARD_ROLLBACK_INVALID", "Não existe publicação ativa.", 409)
        active_pointer, current = active
        target = await self.publication_repository.get(actor.tenant_id, dashboard_id, request.target_publication_id)
        if target.id == current.id or target.generation >= current.generation:
            raise DashboardBackendError("DASHBOARD_ROLLBACK_INVALID", "Alvo deve ser uma publicação histórica anterior.", 409)
        revision = await self.revision_repository.get(actor.tenant_id, dashboard_id, str(target.revision_id))
        publication_request = DashboardPublicationRequestV2(revision_id=str(revision.id), expected_dashboard_lock_version=request.expected_dashboard_lock_version, expected_active_generation=request.expected_active_generation, publication_version=request.publication_version, confirmation="PUBLISH_APPROVED_REVISION")
        result = await self.publication_service.publish(actor=actor, dashboard_id=dashboard_id, request=publication_request, idempotency_key=idempotency_key, rollback_source=target)
        superseded = result.superseded_publication_id or str(current.id)
        return DashboardRollbackResultV2(publication=result.publication, source_publication_id=str(target.id), superseded_publication_id=superseded, replayed=result.replayed)


class DashboardCloneServiceV2:
    def __init__(self, session: AsyncSession):
        self.dashboard_repository = DashboardRepositoryV2(session)
        self.revision_repository = DashboardRevisionRepositoryV2(session)
        self.authoring = DashboardAuthoringServiceV2(session)
        self.audit = DashboardAuditServiceV2(DashboardAuditRepositoryV2(session))

    async def clone(self, *, actor: DashboardActorContextV2, dashboard_id: str, request: DashboardCloneRequestV2, idempotency_key: str) -> DashboardCreateResultV2:
        source = await self.dashboard_repository.get(actor.tenant_id, dashboard_id)
        DashboardAccessPolicyServiceV2.require(DashboardCapabilityBackendV2.CLONE, global_role=actor.global_role, is_owner=source.owner_user_id == _uuid(actor.user_id), collaborator_role=None)
        revision_id = request.source_revision_id or (str(source.head_revision_id) if source.head_revision_id else None)
        if revision_id is None:
            raise DashboardBackendError("DASHBOARD_REVISION_NOT_FOUND", "Dashboard fonte sem revisão.", 409)
        revision = await self.revision_repository.get(actor.tenant_id, dashboard_id, revision_id)
        blueprint = _blueprint_from_json(revision.blueprint_json)
        new_identity = blueprint.identity.model_copy(update={"blueprint_id": f"dashboard.{uuid.uuid4().hex}", "canonical_name": request.canonical_name, "title": request.title, "description": request.description})
        new_version = blueprint.version.model_copy(update={"publication_version": None, "revision": BlueprintRevisionNumbersV2(visual_revision=1, semantic_revision=1)})
        cloned = blueprint.model_copy(update={"identity": new_identity, "version": new_version, "lifecycle": DashboardLifecycleV2.DRAFT, "created_origin": DashboardOriginV2.TEMPLATE})
        result = await self.authoring.create(
            actor=actor,
            request=DashboardCreateRequestV2(canonical_name=request.canonical_name, title=request.title, description=request.description, blueprint=cloned, origin=DashboardOriginV2.TEMPLATE, reason=request.reason),
            idempotency_key=idempotency_key,
            idempotency_operation="CLONE", idempotency_payload=request,
            idempotency_resource_id=dashboard_id, attribution_dashboard_id=source.id,
        )
        if not result.replayed:
            await self.audit.append(
                actor=actor, dashboard_id=result.dashboard.identity.dashboard_id,
                event_type="DASHBOARD_CLONED", resource_reference=dashboard_id,
                metadata={"source_revision_id": revision_id},
            )
        return result


class DashboardEvaluationServiceV2:
    def __init__(self, session: AsyncSession | None = None):
        self.repository = DashboardRuntimeRepositoryV2(session) if session is not None else None

    @staticmethod
    def evaluate(*, expected: str, actual: str, evidence: object) -> tuple[bool, str]:
        return expected == actual, checksum(evidence)

    async def create_case(
        self,
        *,
        tenant_id: str,
        case_key: str,
        name: str,
        category: str,
        fixture: dict[str, object],
        expected_status: DashboardRuntimeStatusV2,
    ) -> DashboardEvaluationCaseV2:
        if self.repository is None:
            raise RuntimeError("evaluation persistence requires a database session")
        row = await self.repository.create_evaluation_case(
            id=uuid.uuid4(), tenant_id=_uuid(tenant_id), case_key=case_key,
            name=name, category=category, fixture_json=fixture,
            fixture_checksum=checksum(fixture), expected_status=expected_status.value,
            status="ACTIVE",
        )
        return DashboardEvaluationCaseV2(
            case_id=str(row.id), name=row.name, category=row.category,
            fixture_checksum=row.fixture_checksum,
            expected_status=DashboardRuntimeStatusV2(row.expected_status),
        )

    async def record_result(
        self,
        *,
        tenant_id: str,
        case_id: str,
        actual_status: DashboardRuntimeStatusV2,
        evidence: dict[str, object],
    ) -> DashboardEvaluationResultV2:
        if self.repository is None:
            raise RuntimeError("evaluation persistence requires a database session")
        case = await self.repository.get_evaluation_case(tenant_id, case_id)
        passed, evidence_checksum = self.evaluate(
            expected=case.expected_status, actual=actual_status.value, evidence=evidence
        )
        row = await self.repository.record_evaluation_result(
            id=uuid.uuid4(), tenant_id=_uuid(tenant_id), case_id=case.id,
            passed=passed, actual_status=actual_status.value,
            evidence_json=evidence, evidence_checksum=evidence_checksum,
        )
        return DashboardEvaluationResultV2(
            result_id=str(row.id), case_id=str(row.case_id), passed=row.passed,
            actual_status=DashboardRuntimeStatusV2(row.actual_status),
            evidence_checksum=row.evidence_checksum, executed_at=row.executed_at,
        )


class DashboardBackupValidationServiceV2:
    """Sanitized manifest helper; restore orchestration is test-target only."""
    @staticmethod
    def table_checksum(rows: list[dict[str, object]]) -> str:
        sanitized = [{key: value for key, value in row.items() if key not in {"description", "blueprint_json", "validation_json", "metadata_json"}} for row in rows]
        return checksum(sanitized)

    @classmethod
    def create_manifest(
        cls, *, backup_id: str, tables: dict[str, list[dict[str, object]]]
    ) -> DashboardBackupManifestV2:
        table_contracts = tuple(
            DashboardBackupTableV2(
                table_name=table_name,
                row_count=len(rows),
                content_checksum=cls.table_checksum(rows),
            )
            for table_name, rows in sorted(tables.items())
        )
        created_at = datetime.now(timezone.utc)
        manifest_checksum = checksum(
            {"backup_id": backup_id, "tables": table_contracts, "sanitized": True}
        )
        return DashboardBackupManifestV2(
            backup_id=backup_id, tables=table_contracts,
            created_at=created_at, checksum=manifest_checksum,
        )

    @staticmethod
    def validate_restore(
        *,
        manifest: DashboardBackupManifestV2,
        restored_manifest: DashboardBackupManifestV2,
        active_publication_valid: bool,
        tenant_isolation_valid: bool,
        constraints_valid: bool,
        indexes_valid: bool,
    ) -> DashboardRestoreValidationV2:
        source_counts = {item.table_name: item.row_count for item in manifest.tables}
        restored_counts = {item.table_name: item.row_count for item in restored_manifest.tables}
        source_checksums = {item.table_name: item.content_checksum for item in manifest.tables}
        restored_checksums = {item.table_name: item.content_checksum for item in restored_manifest.tables}
        return DashboardRestoreValidationV2(
            backup_id=manifest.backup_id,
            restored=True,
            row_counts_match=source_counts == restored_counts,
            checksums_match=source_checksums == restored_checksums,
            active_publication_valid=active_publication_valid,
            tenant_isolation_valid=tenant_isolation_valid,
            constraints_valid=constraints_valid,
            indexes_valid=indexes_valid,
            validated_at=datetime.now(timezone.utc),
        )
