from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from contracts.user_analytical_profile_v2 import (
    ConsentGrantV2,
    ConsentRevokeV2,
    PreferenceConsentV2,
    PreferenceCreateV2,
    PreferenceStatus,
    PreferenceUpdateV2,
    ProfileDeletionRequestV2,
    ProfileExportV2,
    ProfileImportResultV2,
    ProfileImportV2,
    ProfileStatus,
    UserAnalyticalProfileSummaryV2,
    UserAnalyticalProfileV2,
    UserPreferenceItemV2,
)
from database import get_db
from models.user import User
from routers.dependencies import enforce_password_change
from services.user_analytical_profile.cache import UserProfileCache
from services.user_analytical_profile.errors import UserProfileFeatureDisabledError
from services.user_analytical_profile.observability import UserProfileCounters
from services.user_analytical_profile.service import UserAnalyticalProfileService


router = APIRouter(
    prefix="/api/v2/me",
    tags=["User Analytical Profile V2"],
)

_cache = UserProfileCache(
    enabled=settings.USER_ANALYTICAL_PROFILE_CACHE_ENABLED,
    ttl_seconds=settings.USER_ANALYTICAL_PROFILE_CACHE_TTL_SECONDS,
)
_counters = UserProfileCounters(rollout_mode=settings.USER_ANALYTICAL_PROFILE_MODE)


class StrictAction(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class LockAction(StrictAction):
    expected_lock_version: int = Field(ge=0)


class DeletionAction(StrictAction):
    reason: str | None = Field(default=None, max_length=500)


class ProfileCapabilities(StrictAction):
    mode: Literal["LEGACY_ONLY", "SHADOW", "V2_READ", "V2_READ_WRITE"]
    frontend_enabled: bool
    defaults_enabled: bool
    saved_filters_enabled: bool
    export_enabled: bool
    deletion_enabled: bool
    legacy_import_enabled: bool


def _service(db: AsyncSession) -> UserAnalyticalProfileService:
    return UserAnalyticalProfileService(db, cache=_cache, counters=_counters)


def _require_read() -> None:
    if settings.USER_ANALYTICAL_PROFILE_MODE == "LEGACY_ONLY":
        raise UserProfileFeatureDisabledError(
            "O perfil analítico V2 está desabilitado neste ambiente."
        )


def _require_write() -> None:
    if settings.USER_ANALYTICAL_PROFILE_MODE != "V2_READ_WRITE":
        raise UserProfileFeatureDisabledError(
            "A edição do perfil analítico V2 está desabilitada."
        )


def _etag(lock_version: int) -> str:
    return f'W/"profile-{lock_version}"'


@router.get("/analytical-profile/capabilities", response_model=ProfileCapabilities)
async def capabilities(
    _user: Annotated[User, Depends(enforce_password_change)],
) -> ProfileCapabilities:
    return ProfileCapabilities(
        mode=settings.USER_ANALYTICAL_PROFILE_MODE,
        frontend_enabled=settings.USER_ANALYTICAL_PROFILE_FRONTEND_ENABLED,
        defaults_enabled=settings.USER_ANALYTICAL_PROFILE_DEFAULTS_ENABLED,
        saved_filters_enabled=settings.USER_ANALYTICAL_PROFILE_SAVED_FILTERS_ENABLED,
        export_enabled=settings.USER_ANALYTICAL_PROFILE_EXPORT_ENABLED,
        deletion_enabled=settings.USER_ANALYTICAL_PROFILE_DELETION_ENABLED,
        legacy_import_enabled=settings.USER_ANALYTICAL_PROFILE_LEGACY_IMPORT_ENABLED,
    )


@router.get("/analytical-profile", response_model=UserAnalyticalProfileV2)
async def get_profile(
    response: Response,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserAnalyticalProfileV2:
    _require_read()
    result = await _service(db).profile_contract(user=user)
    response.headers["ETag"] = _etag(result.lock_version)
    return result


@router.get(
    "/analytical-profile/summary",
    response_model=UserAnalyticalProfileSummaryV2,
)
async def get_summary(
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserAnalyticalProfileSummaryV2:
    _require_read()
    return await _service(db).summary(user=user)


@router.get("/preferences", response_model=list[UserPreferenceItemV2])
async def list_preferences(
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
    include_inactive: bool = Query(True),
    limit: int = Query(50, ge=1, le=200),
    after_id: uuid.UUID | None = Query(None),
) -> list[UserPreferenceItemV2]:
    _require_read()
    return await _service(db).list_preferences(
        user=user,
        include_inactive=include_inactive,
        limit=limit,
        after_id=after_id,
    )


@router.get("/preferences/applicable", response_model=list[UserPreferenceItemV2])
async def applicable_preferences(
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(100, ge=1, le=200),
) -> list[UserPreferenceItemV2]:
    _require_read()
    return await _service(db).list_preferences(
        user=user,
        include_inactive=False,
        limit=limit,
        after_id=None,
    )


@router.get("/preferences/{preference_id}", response_model=UserPreferenceItemV2)
async def get_preference(
    preference_id: uuid.UUID,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserPreferenceItemV2:
    _require_read()
    return await _service(db).get_preference(
        user=user,
        preference_id=preference_id,
    )


@router.post(
    "/preferences",
    response_model=UserPreferenceItemV2,
    status_code=status.HTTP_201_CREATED,
)
async def create_preference(
    body: PreferenceCreateV2,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserPreferenceItemV2:
    _require_write()
    return await _service(db).create_preference(user=user, request=body)


@router.put("/preferences/{preference_id}", response_model=UserPreferenceItemV2)
async def update_preference(
    preference_id: uuid.UUID,
    body: PreferenceUpdateV2,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserPreferenceItemV2:
    _require_write()
    return await _service(db).update_preference(
        user=user,
        preference_id=preference_id,
        request=body,
    )


async def _preference_status(
    *,
    preference_id: uuid.UUID,
    body: LockAction,
    target: PreferenceStatus,
    user: User,
    db: AsyncSession,
) -> UserPreferenceItemV2:
    _require_write()
    return await _service(db).set_preference_status(
        user=user,
        preference_id=preference_id,
        expected_lock_version=body.expected_lock_version,
        target=target,
    )


@router.post("/preferences/{preference_id}/disable", response_model=UserPreferenceItemV2)
async def disable_preference(
    preference_id: uuid.UUID,
    body: LockAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserPreferenceItemV2:
    return await _preference_status(
        preference_id=preference_id, body=body, target=PreferenceStatus.DISABLED,
        user=user, db=db,
    )


@router.post("/preferences/{preference_id}/reactivate", response_model=UserPreferenceItemV2)
async def reactivate_preference(
    preference_id: uuid.UUID,
    body: LockAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserPreferenceItemV2:
    return await _preference_status(
        preference_id=preference_id, body=body, target=PreferenceStatus.ACTIVE,
        user=user, db=db,
    )


@router.post("/preferences/{preference_id}/revoke", response_model=UserPreferenceItemV2)
async def revoke_preference(
    preference_id: uuid.UUID,
    body: LockAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserPreferenceItemV2:
    return await _preference_status(
        preference_id=preference_id, body=body, target=PreferenceStatus.REVOKED,
        user=user, db=db,
    )


@router.delete("/preferences/{preference_id}", response_model=UserPreferenceItemV2)
async def delete_preference(
    preference_id: uuid.UUID,
    body: LockAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserPreferenceItemV2:
    return await _preference_status(
        preference_id=preference_id, body=body, target=PreferenceStatus.DELETED,
        user=user, db=db,
    )


@router.post(
    "/preferences/{preference_id}/consent",
    response_model=PreferenceConsentV2,
)
async def grant_consent(
    preference_id: uuid.UUID,
    body: ConsentGrantV2,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PreferenceConsentV2:
    _require_write()
    return await _service(db).grant_consent(
        user=user,
        preference_id=preference_id,
        request=body,
    )


@router.delete(
    "/preferences/{preference_id}/consent",
    response_model=PreferenceConsentV2,
)
async def revoke_consent(
    preference_id: uuid.UUID,
    body: ConsentRevokeV2,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PreferenceConsentV2:
    _require_write()
    return await _service(db).revoke_consent(
        user=user,
        preference_id=preference_id,
        expected_lock_version=body.expected_lock_version,
    )


@router.post("/analytical-profile/disable", response_model=UserAnalyticalProfileV2)
async def disable_profile(
    body: LockAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserAnalyticalProfileV2:
    _require_write()
    return await _service(db).set_profile_status(
        user=user,
        expected_lock_version=body.expected_lock_version,
        target=ProfileStatus.DISABLED,
    )


@router.post("/analytical-profile/reactivate", response_model=UserAnalyticalProfileV2)
async def reactivate_profile(
    body: LockAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserAnalyticalProfileV2:
    _require_write()
    return await _service(db).set_profile_status(
        user=user,
        expected_lock_version=body.expected_lock_version,
        target=ProfileStatus.ACTIVE,
    )


@router.get("/profile/export", response_model=ProfileExportV2)
@router.post("/profile/export", response_model=ProfileExportV2)
async def export_profile(
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProfileExportV2:
    _require_read()
    if not settings.USER_ANALYTICAL_PROFILE_EXPORT_ENABLED:
        raise UserProfileFeatureDisabledError("A exportação de perfil está desabilitada.")
    return await _service(db).export_profile(user=user)


@router.post(
    "/analytical-profile/deletion-requests",
    response_model=ProfileDeletionRequestV2,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_deletion(
    body: DeletionAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=256)],
) -> ProfileDeletionRequestV2:
    _require_write()
    if not settings.USER_ANALYTICAL_PROFILE_DELETION_ENABLED:
        raise UserProfileFeatureDisabledError("A exclusão de perfil está desabilitada.")
    return await _service(db).request_deletion(
        user=user,
        idempotency_key=idempotency_key,
        reason=body.reason,
    )


@router.post("/analytical-profile/import/dry-run", response_model=ProfileImportResultV2)
async def import_dry_run(
    body: ProfileImportV2,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProfileImportResultV2:
    _require_write()
    if not settings.USER_ANALYTICAL_PROFILE_LEGACY_IMPORT_ENABLED:
        raise UserProfileFeatureDisabledError("A importação de perfil está desabilitada.")
    return await _service(db).import_profile(
        user=user,
        request=body.model_copy(update={"confirm": False}),
    )


@router.post("/analytical-profile/import/confirm", response_model=ProfileImportResultV2)
async def import_confirm(
    body: ProfileImportV2,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProfileImportResultV2:
    _require_write()
    if not settings.USER_ANALYTICAL_PROFILE_LEGACY_IMPORT_ENABLED:
        raise UserProfileFeatureDisabledError("A importação de perfil está desabilitada.")
    return await _service(db).import_profile(
        user=user,
        request=body.model_copy(update={"confirm": True}),
    )
