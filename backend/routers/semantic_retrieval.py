from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from contracts.semantic_retrieval_v2 import (
    EntityResolutionRequestV2,
    EntityResolutionResultV2,
    IndexBuildRequestV2,
    IndexBuildResultV2,
    IndexPublicationV2,
    IndexRollbackV2,
    SemanticIndexDefinitionV2,
    SemanticIndexSourceV2,
    SemanticIndexVersionV2,
    IndexAuditEventV2,
    SemanticDataClassification,
    SemanticEvaluationResultV2,
    SemanticPermission,
    SemanticRolloutMode,
    SemanticSearchRequestV2,
    SemanticSearchResultV2,
)
from database import get_db
from models.user import User
from routers.dependencies import enforce_password_change
from services.enterprise_knowledge.repository import EnterpriseKnowledgeRepository
from services.semantic_retrieval.cache import SemanticRetrievalCache
from services.semantic_retrieval.clarification import SemanticClarificationService
from services.semantic_retrieval.errors import semantic_error
from services.semantic_retrieval.evaluation import SemanticEvaluationService
from services.semantic_retrieval.feature_flags import SemanticRetrievalFeaturePolicy
from services.semantic_retrieval.indexing import (
    SemanticIndexLifecycleService,
    _version_contract,
)
from services.semantic_retrieval.observability import semantic_observability
from services.semantic_retrieval.permissions import (
    ROLE_PERMISSIONS,
    permission_fingerprint,
    require_permission,
)
from services.semantic_retrieval.repository import SemanticRetrievalRepository
from services.semantic_retrieval.resolution import GovernedEntityResolutionService
from services.semantic_retrieval.retrieval import SemanticRetrievalService
from services.semantic_retrieval.sources import (
    EnterpriseKnowledgeSemanticSourceProvider,
    MetricRegistrySemanticSourceProvider,
)


router = APIRouter(
    prefix="/api/v2/semantic",
    tags=["Governed Semantic Retrieval V2"],
)

_cache = SemanticRetrievalCache(
    enabled=settings.SEMANTIC_RETRIEVAL_CACHE_ENABLED,
    ttl_seconds=settings.SEMANTIC_RETRIEVAL_CACHE_TTL_SECONDS,
)


class StrictAction(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SemanticCapabilities(StrictAction):
    contract_version: Literal["lumina.semantic-retrieval/1.0"]
    mode: SemanticRolloutMode
    frontend_enabled: bool
    entity_instance_indexing_enabled: bool
    vector_channel_enabled: bool
    profile_tie_breaker_enabled: bool
    admin_inspector_enabled: bool
    cache_enabled: bool
    incremental_build_enabled: bool
    permission_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


class DefinitionCreateAction(StrictAction):
    name: str = Field(default="Indice semantico empresarial", min_length=3, max_length=128)


class PublishAction(StrictAction):
    version_id: uuid.UUID
    expected_definition_lock_version: int = Field(ge=0)
    reason: str = Field(min_length=3, max_length=256)


class ClarificationResolveAction(StrictAction):
    session_id: uuid.UUID
    option_token: str = Field(min_length=32, max_length=512)


class ClarificationResolvedResponse(StrictAction):
    document_id: uuid.UUID


class SemanticObservabilityResponse(StrictAction):
    counters: dict[str, int]


class EvaluationAction(StrictAction):
    corpus_version: str = Field(min_length=1, max_length=128)


class DefinitionUpdateAction(StrictAction):
    expected_lock_version: int = Field(ge=0)
    name: str | None = Field(default=None, min_length=3, max_length=128)
    status: Literal["ACTIVE", "DISABLED", "ARCHIVED"] | None = None

    @model_validator(mode="after")
    def require_change(self) -> "DefinitionUpdateAction":
        if self.name is None and self.status is None:
            raise ValueError("Informe ao menos uma alteracao.")
        return self


class DeprecateAction(StrictAction):
    reason: str = Field(min_length=3, max_length=128)


class PublicCandidateDetail(StrictAction):
    document_id: uuid.UUID
    canonical_id: str
    public_label: str
    entity_type: str
    domain: str
    source_type: str
    source_id: str
    source_version: str
    index_version_id: uuid.UUID


class IndexManifestResponse(StrictAction):
    index_id: uuid.UUID
    version_id: uuid.UUID
    version: int
    source_manifest: dict
    document_count: int
    entity_count: int
    alias_count: int
    relation_count: int
    checksum: str


def _policy() -> SemanticRetrievalFeaturePolicy:
    return SemanticRetrievalFeaturePolicy.from_settings()


def _retrieval(db: AsyncSession) -> SemanticRetrievalService:
    policy = _policy()
    return SemanticRetrievalService(
        SemanticRetrievalRepository(db),
        cache=_cache,
        vector_channel_enabled=policy.vector_channel_enabled,
        profile_tie_breaker_enabled=policy.profile_tie_breaker_enabled,
    )


def _lifecycle(db: AsyncSession) -> SemanticIndexLifecycleService:
    repository = SemanticRetrievalRepository(db)
    return SemanticIndexLifecycleService(
        repository,
        providers=(
            EnterpriseKnowledgeSemanticSourceProvider(
                EnterpriseKnowledgeRepository(db)
            ),
            MetricRegistrySemanticSourceProvider(),
        ),
        cache=_cache,
    )


def _definition_contract(row) -> SemanticIndexDefinitionV2:
    return SemanticIndexDefinitionV2(
        index_id=row.id,
        tenant_id=row.tenant_id,
        name=row.name,
        locale=row.locale,
        document_types=tuple(row.document_types),
        entity_policies=tuple(row.entity_policies),
        source_policies=tuple(row.source_policies),
        allowed_classifications=tuple(row.classification_policy),
        representation_provider=row.representation_provider,
        representation_version=row.representation_version,
        ranking_policy=row.ranking_policy,
        threshold_policy=row.threshold_policy,
        status=row.status,
        owner_user_id=row.owner_user_id,
        lock_version=row.lock_version,
        active_version_id=row.active_version_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _require_read() -> None:
    if not _policy().can_read_v2:
        raise semantic_error(
            "SEMANTIC_PROVIDER_UNAVAILABLE",
            "A recuperacao semantica V2 esta desabilitada neste ambiente.",
        )


def _require_admin_feature() -> None:
    if not _policy().admin_inspector_enabled:
        raise semantic_error(
            "SEMANTIC_INDEX_ACCESS_DENIED",
            "A administracao do indice semantico esta desabilitada.",
        )


@router.get("/capabilities", response_model=SemanticCapabilities)
async def capabilities(
    user: Annotated[User, Depends(enforce_password_change)],
) -> SemanticCapabilities:
    policy = _policy()
    return SemanticCapabilities(
        contract_version="lumina.semantic-retrieval/1.0",
        mode=policy.mode,
        frontend_enabled=policy.frontend_enabled,
        entity_instance_indexing_enabled=policy.entity_instance_indexing_enabled,
        vector_channel_enabled=policy.vector_channel_enabled,
        profile_tie_breaker_enabled=policy.profile_tie_breaker_enabled,
        admin_inspector_enabled=policy.admin_inspector_enabled,
        cache_enabled=policy.cache_enabled,
        incremental_build_enabled=policy.incremental_build_enabled,
        permission_fingerprint=permission_fingerprint(user.role),
    )


@router.post("/search", response_model=SemanticSearchResultV2)
async def search(
    body: SemanticSearchRequestV2,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SemanticSearchResultV2:
    _require_read()
    return await _retrieval(db).search(user=user, request=body)


@router.post("/admin/search", response_model=SemanticSearchResultV2)
async def inspect_search(
    body: SemanticSearchRequestV2,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SemanticSearchResultV2:
    _require_read()
    _require_admin_feature()
    return await _retrieval(db).search(
        user=user,
        request=body,
        inspect_scores=True,
    )


@router.post("/resolve", response_model=EntityResolutionResultV2)
async def resolve(
    body: EntityResolutionRequestV2,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EntityResolutionResultV2:
    _require_read()
    clarification = SemanticClarificationService(
        SemanticRetrievalRepository(db),
        signing_secret=settings.SECRET_KEY,
    )
    return await GovernedEntityResolutionService(
        _retrieval(db), clarification=clarification
    ).resolve(user=user, request=body)


@router.post("/entities/resolve", response_model=EntityResolutionResultV2)
async def resolve_entity(
    body: EntityResolutionRequestV2,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EntityResolutionResultV2:
    return await resolve(body=body, user=user, db=db)


@router.get(
    "/candidates/{document_id}",
    response_model=PublicCandidateDetail,
)
async def public_candidate_detail(
    document_id: uuid.UUID,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
    index_id: uuid.UUID | None = None,
) -> PublicCandidateDetail:
    _require_read()
    require_permission(
        tenant_id=user.tenant_id,
        user_id=user.id,
        role=user.role,
        permission=SemanticPermission.READ_PUBLIC_CANDIDATE,
    )
    repository = SemanticRetrievalRepository(db)
    active = await repository.get_active_version(
        tenant_id=user.tenant_id,
        index_id=index_id,
    )
    if active is None:
        raise semantic_error(
            "SEMANTIC_CANDIDATE_NOT_FOUND",
            "Candidato semantico nao encontrado.",
        )
    _, version = active
    document = await repository.get_document(
        tenant_id=user.tenant_id,
        version_id=version.id,
        document_id=document_id,
    )
    candidate_allowed = False
    if document is not None:
        if document.permission_requirement is not None:
            try:
                candidate_allowed = (
                    SemanticPermission(document.permission_requirement)
                    in ROLE_PERMISSIONS.get(user.role, frozenset())
                )
            except ValueError:
                candidate_allowed = False
        else:
            candidate_allowed = document.classification in {
                SemanticDataClassification.PUBLIC_BUSINESS_METADATA.value,
                SemanticDataClassification.TENANT_BUSINESS_METADATA.value,
            }
    if (
        document is None
        or document.lifecycle != "ACTIVE"
        or not candidate_allowed
    ):
        raise semantic_error(
            "SEMANTIC_CANDIDATE_NOT_FOUND",
            "Candidato semantico nao encontrado.",
        )
    return PublicCandidateDetail(
        document_id=document.id,
        canonical_id=document.canonical_key,
        public_label=document.display_label,
        entity_type=document.entity_type,
        domain=document.domain,
        source_type=document.source_type,
        source_id=document.source_id,
        source_version=document.source_version,
        index_version_id=version.id,
    )


@router.post(
    "/clarifications/{clarification_id}/resolve",
    response_model=ClarificationResolvedResponse,
)
async def resolve_clarification(
    clarification_id: uuid.UUID,
    body: ClarificationResolveAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ClarificationResolvedResponse:
    _require_read()
    document_id = await SemanticClarificationService(
        SemanticRetrievalRepository(db),
        signing_secret=settings.SECRET_KEY,
    ).resolve(
        user=user,
        session_id=body.session_id,
        clarification_id=clarification_id,
        option_token=body.option_token,
    )
    return ClarificationResolvedResponse(document_id=document_id)


@router.post("/admin/indexes/default", response_model=SemanticIndexDefinitionV2)
async def create_default_index(
    body: DefinitionCreateAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SemanticIndexDefinitionV2:
    _require_admin_feature()
    row = await _lifecycle(db).create_default_definition(user=user, name=body.name)
    return _definition_contract(row)


@router.get("/admin/indexes", response_model=list[SemanticIndexDefinitionV2])
async def list_indexes(
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(50, ge=1, le=100),
) -> list[SemanticIndexDefinitionV2]:
    _require_admin_feature()
    require_permission(
        tenant_id=user.tenant_id,
        user_id=user.id,
        role=user.role,
        permission=SemanticPermission.MANAGE_INDEX,
    )
    rows = await SemanticRetrievalRepository(db).list_definitions(
        tenant_id=user.tenant_id, limit=limit
    )
    return [_definition_contract(row) for row in rows]


@router.patch(
    "/admin/indexes/{index_id}",
    response_model=SemanticIndexDefinitionV2,
)
async def update_index_definition(
    index_id: uuid.UUID,
    body: DefinitionUpdateAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SemanticIndexDefinitionV2:
    _require_admin_feature()
    require_permission(
        tenant_id=user.tenant_id,
        user_id=user.id,
        role=user.role,
        permission=SemanticPermission.MANAGE_INDEX,
    )
    repository = SemanticRetrievalRepository(db)
    values = {
        key: value
        for key, value in {"name": body.name, "status": body.status}.items()
        if value is not None
    }
    updated = await repository.update_definition_cas(
        tenant_id=user.tenant_id,
        index_id=index_id,
        expected_lock_version=body.expected_lock_version,
        values=values,
    )
    if not updated:
        raise semantic_error(
            "SEMANTIC_INDEX_VERSION_CONFLICT",
            "A definicao nao existe ou foi alterada por outra operacao.",
        )
    row = await repository.get_definition(
        tenant_id=user.tenant_id,
        index_id=index_id,
    )
    assert row is not None
    return _definition_contract(row)


@router.get(
    "/admin/indexes/{index_id}/versions",
    response_model=list[SemanticIndexVersionV2],
)
async def list_versions(
    index_id: uuid.UUID,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(50, ge=1, le=100),
) -> list[SemanticIndexVersionV2]:
    _require_admin_feature()
    require_permission(
        tenant_id=user.tenant_id,
        user_id=user.id,
        role=user.role,
        permission=SemanticPermission.MANAGE_INDEX,
    )
    rows = await SemanticRetrievalRepository(db).list_versions(
        tenant_id=user.tenant_id, index_id=index_id, limit=limit
    )
    return [_version_contract(row) for row in rows]


@router.get(
    "/admin/indexes/{index_id}/versions/{version_id}",
    response_model=SemanticIndexVersionV2,
)
async def inspect_version(
    index_id: uuid.UUID,
    version_id: uuid.UUID,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SemanticIndexVersionV2:
    _require_admin_feature()
    require_permission(
        tenant_id=user.tenant_id,
        user_id=user.id,
        role=user.role,
        permission=SemanticPermission.MANAGE_INDEX,
    )
    row = await SemanticRetrievalRepository(db).get_version(
        tenant_id=user.tenant_id,
        index_id=index_id,
        version_id=version_id,
    )
    if row is None:
        raise semantic_error(
            "SEMANTIC_INDEX_NOT_FOUND",
            "Indice ou versao nao encontrado.",
        )
    return _version_contract(row)


@router.get(
    "/admin/indexes/{index_id}/versions/{version_id}/manifest",
    response_model=IndexManifestResponse,
)
async def export_index_manifest(
    index_id: uuid.UUID,
    version_id: uuid.UUID,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IndexManifestResponse:
    version = await inspect_version(
        index_id=index_id,
        version_id=version_id,
        user=user,
        db=db,
    )
    if version.checksum is None:
        raise semantic_error(
            "SEMANTIC_INDEX_NOT_READY",
            "A versao ainda nao possui manifest validado.",
        )
    return IndexManifestResponse(
        index_id=index_id,
        version_id=version_id,
        version=version.version,
        source_manifest=version.source_manifest.model_dump(mode="json"),
        document_count=version.document_count,
        entity_count=version.entity_count,
        alias_count=version.alias_count,
        relation_count=version.relation_count,
        checksum=version.checksum,
    )


@router.post(
    "/admin/indexes/{index_id}/build",
    response_model=IndexBuildResultV2,
)
async def build_index(
    index_id: uuid.UUID,
    body: IndexBuildRequestV2,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IndexBuildResultV2:
    _require_admin_feature()
    if body.index_id != index_id:
        raise semantic_error(
            "SEMANTIC_INDEX_TENANT_MISMATCH",
            "O indice da rota nao corresponde ao corpo da requisicao.",
        )
    if body.build_mode == "INCREMENTAL" and not _policy().incremental_build_enabled:
        raise semantic_error(
            "SEMANTIC_PROVIDER_UNAVAILABLE",
            "O build incremental esta desabilitado.",
        )
    return await _lifecycle(db).build(user=user, request=body)


@router.post(
    "/admin/indexes/{index_id}/publish",
    response_model=IndexPublicationV2,
)
async def publish_index(
    index_id: uuid.UUID,
    body: PublishAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IndexPublicationV2:
    _require_admin_feature()
    return await _lifecycle(db).publish(
        user=user,
        index_id=index_id,
        version_id=body.version_id,
        expected_definition_lock_version=body.expected_definition_lock_version,
        reason=body.reason,
    )


@router.post(
    "/admin/indexes/{index_id}/rollback",
    response_model=IndexPublicationV2,
)
async def rollback_index(
    index_id: uuid.UUID,
    body: IndexRollbackV2,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IndexPublicationV2:
    _require_admin_feature()
    if body.index_id != index_id:
        raise semantic_error(
            "SEMANTIC_INDEX_TENANT_MISMATCH",
            "O indice da rota nao corresponde ao corpo da requisicao.",
        )
    return await _lifecycle(db).rollback(user=user, request=body)


@router.post(
    "/admin/indexes/{index_id}/versions/{version_id}/deprecate",
    response_model=SemanticIndexVersionV2,
)
async def deprecate_index_version(
    index_id: uuid.UUID,
    version_id: uuid.UUID,
    body: DeprecateAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SemanticIndexVersionV2:
    _require_admin_feature()
    return await _lifecycle(db).deprecate(
        user=user,
        index_id=index_id,
        version_id=version_id,
        reason=body.reason,
    )


@router.get(
    "/admin/indexes/{index_id}/stale-sources",
    response_model=list[SemanticIndexSourceV2],
)
async def list_stale_sources(
    index_id: uuid.UUID,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SemanticIndexSourceV2]:
    _require_admin_feature()
    inspected = await _lifecycle(db).inspect_stale_sources(
        user=user,
        index_id=index_id,
    )
    return [item for item in inspected if item.stale]


@router.get("/admin/observability", response_model=SemanticObservabilityResponse)
async def observability(
    user: Annotated[User, Depends(enforce_password_change)],
) -> SemanticObservabilityResponse:
    _require_admin_feature()
    require_permission(
        tenant_id=user.tenant_id,
        user_id=user.id,
        role=user.role,
        permission=SemanticPermission.AUDIT_READ,
    )
    return SemanticObservabilityResponse(counters=semantic_observability.snapshot())


@router.get("/admin/audit", response_model=list[IndexAuditEventV2])
async def audit_events(
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
    index_id: uuid.UUID | None = None,
    limit: int = Query(100, ge=1, le=200),
) -> list[IndexAuditEventV2]:
    _require_admin_feature()
    require_permission(
        tenant_id=user.tenant_id,
        user_id=user.id,
        role=user.role,
        permission=SemanticPermission.AUDIT_READ,
    )
    rows = await SemanticRetrievalRepository(db).list_events(
        tenant_id=user.tenant_id,
        index_id=index_id,
        limit=limit,
    )
    return [
        IndexAuditEventV2(
            event_id=row.id,
            tenant_id=row.tenant_id,
            index_id=row.index_id,
            version_id=row.version_id,
            actor_user_id=row.actor_user_id,
            event_type=row.event_type,
            reason_code=row.reason_code,
            structural_fingerprint=row.structural_fingerprint,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post(
    "/admin/indexes/{index_id}/evaluations",
    response_model=SemanticEvaluationResultV2,
)
async def run_evaluation(
    index_id: uuid.UUID,
    body: EvaluationAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SemanticEvaluationResultV2:
    _require_admin_feature()
    retrieval = _retrieval(db)
    return await SemanticEvaluationService(
        SemanticRetrievalRepository(db), retrieval
    ).run(
        user=user,
        index_id=index_id,
        corpus_version=body.corpus_version,
    )


@router.get(
    "/admin/indexes/{index_id}/evaluations",
    response_model=list[SemanticEvaluationResultV2],
)
async def list_evaluations(
    index_id: uuid.UUID,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
    before: datetime | None = None,
    limit: int = Query(50, ge=1, le=100),
) -> list[SemanticEvaluationResultV2]:
    _require_admin_feature()
    require_permission(
        tenant_id=user.tenant_id,
        user_id=user.id,
        role=user.role,
        permission=SemanticPermission.RUN_EVALUATION,
    )
    rows = await SemanticRetrievalRepository(db).list_evaluation_results(
        tenant_id=user.tenant_id,
        index_id=index_id,
        before=before,
        limit=limit,
    )
    return [
        SemanticEvaluationResultV2(
            evaluation_id=row.id,
            tenant_id=row.tenant_id,
            index_version_id=row.index_version_id,
            corpus_version=row.corpus_version,
            case_count=row.case_count,
            passed=row.passed,
            metrics=tuple(row.metrics),
            checksum=row.checksum,
            executed_at=row.executed_at,
        )
        for row in rows
    ]
