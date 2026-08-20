from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from contracts.enterprise_knowledge_v2 import (
    EnterpriseKnowledgeAssetV2,
    EnterpriseKnowledgeVersionV2,
    KnowledgeApprovalDecision,
    KnowledgeApprovalV2,
    KnowledgeAssetCreateV2,
    KnowledgeAssetType,
    KnowledgeAuditEventV2,
    KnowledgeDiffV2,
    KnowledgeExportFormat,
    KnowledgeExportV2,
    KnowledgeImportRequestV2,
    KnowledgeImportResultV2,
    KnowledgeLifecycle,
    KnowledgeRolloutMode,
    KnowledgePublicationV2,
    KnowledgeSearchRequestV2,
    KnowledgeSearchResultV2,
    KnowledgeVersionUpdateV2,
)
from database import get_db
from models.user import User
from routers.dependencies import enforce_password_change
from services.enterprise_knowledge.cache import EnterpriseKnowledgeCache
from services.enterprise_knowledge.errors import (
    EnterpriseKnowledgeError,
    KnowledgeFeatureDisabledError,
)
from services.enterprise_knowledge.observability import KnowledgeCounters
from services.enterprise_knowledge.service import EnterpriseKnowledgeService


router = APIRouter(
    prefix="/api/v2/enterprise-knowledge",
    tags=["Enterprise Knowledge V2"],
)

_cache = EnterpriseKnowledgeCache(
    enabled=settings.ENTERPRISE_KNOWLEDGE_CACHE_ENABLED,
    ttl_seconds=settings.ENTERPRISE_KNOWLEDGE_CACHE_TTL_SECONDS,
)
_counters = KnowledgeCounters(mode=KnowledgeRolloutMode(settings.ENTERPRISE_KNOWLEDGE_MODE))


class StrictAction(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AssetCreatedResponse(StrictAction):
    asset: EnterpriseKnowledgeAssetV2
    version: EnterpriseKnowledgeVersionV2


class AssetDetailResponse(StrictAction):
    asset: EnterpriseKnowledgeAssetV2
    versions: list[EnterpriseKnowledgeVersionV2]


class ReviewAction(StrictAction):
    decision: KnowledgeApprovalDecision
    comment: str = Field(min_length=1, max_length=4000)
    expected_lock_version: int = Field(ge=0)


class ReviewResponse(StrictAction):
    version: EnterpriseKnowledgeVersionV2
    approval: KnowledgeApprovalV2


class LockAction(StrictAction):
    expected_lock_version: int = Field(ge=0)


class PublishAction(LockAction):
    effective_at: datetime | None = None


class PublicationResponse(StrictAction):
    version: EnterpriseKnowledgeVersionV2
    publication: KnowledgePublicationV2


class DraftAction(StrictAction):
    from_version_id: uuid.UUID | None = None


class RollbackAction(StrictAction):
    source_version_id: uuid.UUID


class OwnershipAction(LockAction):
    new_owner_user_id: uuid.UUID


class DiffQuery(StrictAction):
    from_version_id: uuid.UUID
    to_version_id: uuid.UUID


def _service(db: AsyncSession) -> EnterpriseKnowledgeService:
    return EnterpriseKnowledgeService(
        db,
        cache=_cache,
        counters=_counters,
        import_enabled=settings.ENTERPRISE_KNOWLEDGE_IMPORT_ENABLED,
        export_enabled=settings.ENTERPRISE_KNOWLEDGE_EXPORT_ENABLED,
    )


def _require_read_mode() -> None:
    if settings.ENTERPRISE_KNOWLEDGE_MODE == "LEGACY_ONLY":
        raise KnowledgeFeatureDisabledError(
            "A Base de Conhecimento V2 está desabilitada neste ambiente."
        )


def _require_write_mode() -> None:
    if settings.ENTERPRISE_KNOWLEDGE_MODE != "V2_READ_WRITE":
        raise KnowledgeFeatureDisabledError(
            "O workflow de escrita da Base de Conhecimento V2 está desabilitado."
        )


@router.post("/search", response_model=KnowledgeSearchResultV2)
async def search_published_knowledge(
    body: KnowledgeSearchRequestV2,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeSearchResultV2:
    _require_read_mode()
    return await _service(db).search(user=user, request=body)


@router.get("/glossary", response_model=KnowledgeSearchResultV2)
async def search_glossary(
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
    query: str = Query(..., min_length=1, max_length=256),
    locale: str = Query("pt-BR", pattern=r"^[a-z]{2}(?:-[A-Z]{2})?$"),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None, max_length=512),
) -> KnowledgeSearchResultV2:
    _require_read_mode()
    return await _service(db).search(
        user=user,
        request=KnowledgeSearchRequestV2(
            query=query,
            locale=locale,
            limit=limit,
            cursor=cursor,
        ),
    )


@router.get("/published/{canonical_key}", response_model=AssetDetailResponse)
async def get_published_asset(
    canonical_key: Annotated[str, Path(min_length=2, max_length=128)],
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AssetDetailResponse:
    _require_read_mode()
    asset, version = await _service(db).get_published_asset(
        user=user,
        canonical_key=canonical_key,
    )
    return AssetDetailResponse(asset=asset, versions=[version])


@router.get("/metrics/{canonical_metric_id}", response_model=AssetDetailResponse)
async def get_metric_definition(
    canonical_metric_id: Annotated[str, Path(min_length=2, max_length=128)],
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AssetDetailResponse:
    _require_read_mode()
    asset, version = await _service(db).get_published_asset(
        user=user,
        canonical_key=canonical_metric_id,
        asset_types=(KnowledgeAssetType.METRIC, KnowledgeAssetType.KPI),
    )
    return AssetDetailResponse(asset=asset, versions=[version])


@router.get("/review-queue", response_model=list[EnterpriseKnowledgeAssetV2])
async def review_queue(
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(50, ge=1, le=100),
    asset_type: KnowledgeAssetType | None = Query(None),
    domain: str | None = Query(None, max_length=128),
) -> list[EnterpriseKnowledgeAssetV2]:
    _require_read_mode()
    return await _service(db).list_review_queue(
        user=user,
        limit=limit,
        asset_type=asset_type.value if asset_type else None,
        domain=domain,
    )


@router.get("/assets", response_model=list[EnterpriseKnowledgeAssetV2])
async def list_assets(
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(50, ge=1, le=100),
    lifecycle: KnowledgeLifecycle | None = Query(None),
    asset_type: KnowledgeAssetType | None = Query(None),
    domain: str | None = Query(None, max_length=128),
) -> list[EnterpriseKnowledgeAssetV2]:
    _require_read_mode()
    return await _service(db).list_assets(
        user=user,
        limit=limit,
        lifecycle=lifecycle.value if lifecycle else None,
        asset_type=asset_type.value if asset_type else None,
        domain=domain,
    )


@router.post(
    "/assets",
    response_model=AssetCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_asset(
    body: KnowledgeAssetCreateV2,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AssetCreatedResponse:
    _require_write_mode()
    asset, version = await _service(db).create_asset(user=user, request=body)
    return AssetCreatedResponse(asset=asset, version=version)


@router.get("/assets/{asset_id}", response_model=AssetDetailResponse)
async def get_asset(
    asset_id: uuid.UUID,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AssetDetailResponse:
    _require_read_mode()
    service = _service(db)
    asset = await service._asset(user=user, asset_id=asset_id)
    versions = await service.list_versions(user=user, asset_id=asset_id)
    if not versions:
        from services.enterprise_knowledge.errors import KnowledgeNotFoundError

        raise KnowledgeNotFoundError("Asset publicado não encontrado.")
    return AssetDetailResponse(asset=service.asset_contract(asset), versions=versions)


@router.get(
    "/assets/{asset_id}/versions",
    response_model=list[EnterpriseKnowledgeVersionV2],
)
async def list_versions(
    asset_id: uuid.UUID,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[EnterpriseKnowledgeVersionV2]:
    _require_read_mode()
    return await _service(db).list_versions(user=user, asset_id=asset_id)


@router.post(
    "/assets/{asset_id}/drafts",
    response_model=EnterpriseKnowledgeVersionV2,
    status_code=status.HTTP_201_CREATED,
)
async def create_draft(
    asset_id: uuid.UUID,
    body: DraftAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EnterpriseKnowledgeVersionV2:
    _require_write_mode()
    return await _service(db).create_draft(
        user=user,
        asset_id=asset_id,
        from_version_id=body.from_version_id,
    )


@router.put(
    "/assets/{asset_id}/versions/{version_id}",
    response_model=EnterpriseKnowledgeVersionV2,
)
async def update_draft(
    asset_id: uuid.UUID,
    version_id: uuid.UUID,
    body: KnowledgeVersionUpdateV2,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EnterpriseKnowledgeVersionV2:
    _require_write_mode()
    try:
        return await _service(db).update_draft(
            user=user,
            asset_id=asset_id,
            version_id=version_id,
            request=body,
        )
    except EnterpriseKnowledgeError:
        await db.commit()
        raise


@router.post(
    "/assets/{asset_id}/versions/{version_id}/submit",
    response_model=EnterpriseKnowledgeVersionV2,
)
async def submit_review(
    asset_id: uuid.UUID,
    version_id: uuid.UUID,
    body: LockAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EnterpriseKnowledgeVersionV2:
    _require_write_mode()
    return await _service(db).submit_review(
        user=user,
        asset_id=asset_id,
        version_id=version_id,
        expected_lock_version=body.expected_lock_version,
    )


@router.post(
    "/assets/{asset_id}/versions/{version_id}/review",
    response_model=ReviewResponse,
)
async def review_version(
    asset_id: uuid.UUID,
    version_id: uuid.UUID,
    body: ReviewAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReviewResponse:
    _require_write_mode()
    try:
        version, approval = await _service(db).review(
            user=user,
            asset_id=asset_id,
            version_id=version_id,
            decision=body.decision,
            comment=body.comment,
            expected_lock_version=body.expected_lock_version,
        )
    except EnterpriseKnowledgeError:
        await db.commit()
        raise
    return ReviewResponse(version=version, approval=approval)


@router.post(
    "/assets/{asset_id}/versions/{version_id}/publish",
    response_model=PublicationResponse,
)
async def publish_version(
    asset_id: uuid.UUID,
    version_id: uuid.UUID,
    body: PublishAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublicationResponse:
    _require_write_mode()
    try:
        version, publication = await _service(db).publish(
            user=user,
            asset_id=asset_id,
            version_id=version_id,
            expected_lock_version=body.expected_lock_version,
            effective_at=body.effective_at,
        )
    except EnterpriseKnowledgeError:
        await db.commit()
        raise
    return PublicationResponse(version=version, publication=publication)


@router.post(
    "/assets/{asset_id}/versions/{version_id}/deprecate",
    response_model=EnterpriseKnowledgeVersionV2,
)
async def deprecate_version(
    asset_id: uuid.UUID,
    version_id: uuid.UUID,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EnterpriseKnowledgeVersionV2:
    _require_write_mode()
    return await _service(db).deprecate(
        user=user,
        asset_id=asset_id,
        version_id=version_id,
    )


@router.post(
    "/assets/{asset_id}/archive",
    response_model=EnterpriseKnowledgeAssetV2,
)
async def archive_asset(
    asset_id: uuid.UUID,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EnterpriseKnowledgeAssetV2:
    _require_write_mode()
    return await _service(db).archive(user=user, asset_id=asset_id)


@router.delete(
    "/assets/{asset_id}",
    response_model=dict[str, bool],
)
async def soft_delete_asset(
    asset_id: uuid.UUID,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, bool]:
    _require_write_mode()
    await _service(db).soft_delete(user=user, asset_id=asset_id)
    return {"deleted": True}


@router.post(
    "/assets/{asset_id}/rollback",
    response_model=EnterpriseKnowledgeVersionV2,
    status_code=status.HTTP_201_CREATED,
)
async def rollback_asset(
    asset_id: uuid.UUID,
    body: RollbackAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EnterpriseKnowledgeVersionV2:
    _require_write_mode()
    return await _service(db).rollback(
        user=user,
        asset_id=asset_id,
        source_version_id=body.source_version_id,
    )


@router.post(
    "/assets/{asset_id}/ownership",
    response_model=EnterpriseKnowledgeAssetV2,
)
async def transfer_ownership(
    asset_id: uuid.UUID,
    body: OwnershipAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EnterpriseKnowledgeAssetV2:
    _require_write_mode()
    return await _service(db).transfer_ownership(
        user=user,
        asset_id=asset_id,
        new_owner_user_id=body.new_owner_user_id,
        expected_lock_version=body.expected_lock_version,
    )


@router.post("/assets/{asset_id}/diff", response_model=KnowledgeDiffV2)
async def version_diff(
    asset_id: uuid.UUID,
    body: DiffQuery,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeDiffV2:
    _require_read_mode()
    return await _service(db).diff(
        user=user,
        asset_id=asset_id,
        from_version_id=body.from_version_id,
        to_version_id=body.to_version_id,
    )


@router.get(
    "/assets/{asset_id}/audit",
    response_model=list[KnowledgeAuditEventV2],
)
async def asset_audit(
    asset_id: uuid.UUID,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[KnowledgeAuditEventV2]:
    _require_read_mode()
    return await _service(db).audit_events(user=user, asset_id=asset_id)


@router.post("/imports", response_model=KnowledgeImportResultV2)
async def import_knowledge(
    body: KnowledgeImportRequestV2,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeImportResultV2:
    _require_write_mode()
    return await _service(db).import_assets(user=user, request=body)


@router.get("/exports/{export_format}", response_model=KnowledgeExportV2)
async def export_knowledge(
    export_format: KnowledgeExportFormat,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeExportV2:
    _require_read_mode()
    return await _service(db).export_published(
        user=user,
        export_format=export_format,
    )
