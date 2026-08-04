"""Experimental administrative API for smart cache/materializations.

The module is imported only when both server-controlled feature gates are
enabled. It intentionally exposes no cache-write, force-hit, raw-key, SQL, bind,
connection-string, or result-row endpoint.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from contracts.smart_cache_materialization_v2 import (
    CacheEvictionResultV2,
    CacheGarbageCollectionRequestV2,
    CacheInvalidationRequestV2,
    CacheInvalidationResultV2,
    CacheStatisticsV2,
    MaterializationPublicationV2,
    MaterializationRollbackV2,
)
from database import get_db
from models.user import User
from routers.auth import get_current_user


router = APIRouter(prefix="/api/v2/cache", tags=["Smart Cache & Materialization"])

_ADMIN_PERMISSIONS = {
    "cache:inspect",
    "cache:invalidate",
    "cache:policy_read",
    "cache:policy_publish",
    "cache:gc_dry_run",
    "cache:gc_execute",
    "cache:lease_manage",
    "materialization:read",
    "materialization:create",
    "materialization:build",
    "materialization:validate",
    "materialization:publish",
    "materialization:refresh",
    "materialization:rollback",
    "materialization:disable",
}
_GESTOR_PERMISSIONS = {
    "cache:inspect",
    "cache:policy_read",
    "cache:gc_dry_run",
    "materialization:read",
    "materialization:create",
    "materialization:build",
    "materialization:validate",
}


class MaterializationPublicationCommandV2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    definition_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    snapshot_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    expected_lock_version: int = Field(ge=0)


class MaterializationRollbackCommandV2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    definition_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    to_snapshot_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    expected_lock_version: int = Field(ge=1)


def _permissions(user: User) -> set[str]:
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    if role == "ADMIN":
        return set(_ADMIN_PERMISSIONS)
    if role == "GESTOR":
        return set(_GESTOR_PERMISSIONS)
    return set()


def _require(user: User, permission: str) -> list[str]:
    permissions = _permissions(user)
    if permission not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied for governed cache operation.",
        )
    return sorted(permissions)


@router.get("/statistics", response_model=CacheStatisticsV2)
async def get_cache_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from services.smart_cache_materialization import (
        MaterializationRepository,
        SmartCacheRepository,
        SmartCacheStatisticsService,
    )

    _require(current_user, "cache:inspect")
    cache_repo = SmartCacheRepository(db)
    materialization_repo = MaterializationRepository(db)
    service = SmartCacheStatisticsService(cache_repo, materialization_repo)
    return await service.get_cache_statistics(str(current_user.tenant_id))


@router.post("/invalidate", response_model=CacheInvalidationResultV2)
async def invalidate_cache(
    request: CacheInvalidationRequestV2,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from services.smart_cache_materialization import (
        SmartCacheInvalidationService,
        SmartCacheRepository,
    )

    _require(current_user, "cache:invalidate")
    service = SmartCacheInvalidationService(SmartCacheRepository(db))
    try:
        return await service.invalidate(str(current_user.tenant_id), request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/gc", response_model=CacheEvictionResultV2)
async def execute_garbage_collection(
    request: CacheGarbageCollectionRequestV2,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from services.smart_cache_materialization import (
        MaterializationRepository,
        SmartCacheGarbageCollectionService,
        SmartCacheRepository,
    )

    _require(current_user, "cache:gc_dry_run" if request.dry_run else "cache:gc_execute")
    service = SmartCacheGarbageCollectionService(
        SmartCacheRepository(db), MaterializationRepository(db)
    )
    return await service.execute_gc(
        str(current_user.tenant_id),
        dry_run=request.dry_run,
        limit=request.limit,
        cursor=request.cursor,
    )


@router.post("/materialization/publish", response_model=MaterializationPublicationV2)
async def publish_materialization(
    request: MaterializationPublicationCommandV2,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from services.smart_cache_materialization import (
        MaterializationPublicationService,
        MaterializationRepository,
    )

    permissions = _require(current_user, "materialization:publish")
    service = MaterializationPublicationService(MaterializationRepository(db))
    try:
        return await service.publish(
            str(current_user.tenant_id),
            request.definition_id,
            request.snapshot_id,
            str(current_user.id),
            expected_lock_version=request.expected_lock_version,
            permissions=permissions,
        )
    except (ValueError, RuntimeError, PermissionError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/materialization/rollback", response_model=MaterializationRollbackV2)
async def rollback_materialization(
    request: MaterializationRollbackCommandV2,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from services.smart_cache_materialization import (
        MaterializationRepository,
        MaterializationRollbackService,
    )

    permissions = _require(current_user, "materialization:rollback")
    service = MaterializationRollbackService(MaterializationRepository(db))
    try:
        return await service.rollback(
            str(current_user.tenant_id),
            request.definition_id,
            request.to_snapshot_id,
            str(current_user.id),
            expected_lock_version=request.expected_lock_version,
            permissions=permissions,
        )
    except (ValueError, RuntimeError, PermissionError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
