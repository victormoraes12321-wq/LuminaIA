"""Governed Post-Sync Insights V2 API router."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from contracts.post_sync_insights_v2 import (
    PostSyncInsightAcknowledgementV2,
    PostSyncInsightCategoryV2,
    PostSyncInsightDetailV2,
    PostSyncInsightDismissalV2,
    PostSyncInsightEvidenceV2,
    PostSyncInsightLifecycleV2,
    PostSyncInsightListItemV2,
    PostSyncInsightListRequestV2,
    PostSyncInsightPolicyV2,
    PostSyncInsightReplayRequestV2,
    PostSyncInsightRunResultV2,
    PostSyncInsightSeverityV2,
)
from database import get_db
from models.user import User
from routers.dependencies import get_current_user
from services.post_sync_insights_v2 import (
    audit_service,
    get_default_post_sync_policy,
    post_sync_insights_service,
    replay_service,
    user_state_service,
)

router = APIRouter(prefix="/api/v2/post-sync-insights", tags=["Governed Post-Sync Insights V2"])
IdempotencyKey = Annotated[str | None, Header(alias="Idempotency-Key")]


class StrictPostSyncApiBody(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class AcknowledgeBodyV2(StrictPostSyncApiBody):
    note: str | None = Field(default=None, max_length=255)


class DismissBodyV2(StrictPostSyncApiBody):
    reason: str = Field(default="NOT_RELEVANT", max_length=64)


class ReplayBodyV2(StrictPostSyncApiBody):
    reason: str = Field(..., max_length=255)


def _check_enabled(tenant_id: str) -> None:
    if settings.POST_SYNC_INSIGHTS_MODE == "LEGACY_ONLY" and not settings.POST_SYNC_INSIGHTS_APIS_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": {
                    "code": "POST_SYNC_INSIGHTS_NOT_AVAILABLE",
                    "message": "Serviço de insights pós-sincronização desativado no ambiente.",
                }
            },
        )
    if settings.POST_SYNC_INSIGHTS_TENANT_ALLOWLIST and tenant_id not in settings.POST_SYNC_INSIGHTS_TENANT_ALLOWLIST:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "POST_SYNC_INSIGHTS_ACCESS_DENIED",
                    "message": "Tenant fora do grupo autorizado para insights V2.",
                }
            },
        )


@router.get("", response_model=dict[str, object])
async def list_post_sync_insights(
    severity: PostSyncInsightSeverityV2 | None = Query(default=None),
    category: PostSyncInsightCategoryV2 | None = Query(default=None),
    lifecycle: PostSyncInsightLifecycleV2 | None = Query(default=None),
    metric_key: str | None = Query(default=None),
    include_dismissed: bool = Query(default=False),
    include_acknowledged: bool = Query(default=True),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = str(current_user.tenant_id)
    _check_enabled(tenant_id)

    req = PostSyncInsightListRequestV2(
        tenant_id=tenant_id,
        severity=severity,
        category=category,
        lifecycle=lifecycle,
        metric_key=metric_key,
        include_dismissed=include_dismissed,
        include_acknowledged=include_acknowledged,
        cursor=cursor,
        limit=limit,
    )

    items, next_cursor = await post_sync_insights_service.list_insights(db, req, user_id=str(current_user.id))
    return {
        "items": [item.model_dump(mode="json") for item in items],
        "next_cursor": next_cursor,
        "contract_version": "lumina.post-sync-insights/1.0",
    }


@router.get("/policies", response_model=dict[str, object])
async def get_post_sync_policy(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = str(current_user.tenant_id)
    _check_enabled(tenant_id)
    policy = await post_sync_insights_service.get_active_policy(db, tenant_id)
    return policy.model_dump(mode="json")


@router.get("/{insight_id}", response_model=dict[str, object])
async def get_post_sync_insight_detail(
    insight_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = str(current_user.tenant_id)
    _check_enabled(tenant_id)

    try:
        detail = await post_sync_insights_service.get_insight_detail(
            db, tenant_id=tenant_id, insight_id=insight_id, user_id=str(current_user.id)
        )
        return detail.model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "POST_SYNC_INSIGHTS_NOT_FOUND", "message": str(exc)}},
        )


@router.get("/{insight_id}/evidence", response_model=dict[str, object])
async def get_post_sync_insight_evidence(
    insight_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = str(current_user.tenant_id)
    _check_enabled(tenant_id)

    try:
        detail = await post_sync_insights_service.get_insight_detail(
            db, tenant_id=tenant_id, insight_id=insight_id, user_id=str(current_user.id)
        )
        return detail.insight.evidence.model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "POST_SYNC_INSIGHTS_NOT_FOUND", "message": str(exc)}},
        )


@router.post("/{insight_id}/acknowledge", response_model=dict[str, object])
async def acknowledge_post_sync_insight(
    insight_id: str,
    body: AcknowledgeBodyV2,
    idempotency_key: IdempotencyKey = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = str(current_user.tenant_id)
    _check_enabled(tenant_id)

    try:
        ack = await user_state_service.acknowledge_insight(
            db, tenant_id=tenant_id, user_id=str(current_user.id), insight_id=insight_id, note=body.note
        )
        await audit_service.log_event(
            db, tenant_id=tenant_id, user_id=str(current_user.id), action="ACKNOWLEDGE", insight_id=insight_id
        )
        return ack.model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "POST_SYNC_INSIGHTS_NOT_FOUND", "message": str(exc)}},
        )


@router.post("/{insight_id}/dismiss", response_model=dict[str, object])
async def dismiss_post_sync_insight(
    insight_id: str,
    body: DismissBodyV2,
    idempotency_key: IdempotencyKey = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = str(current_user.tenant_id)
    _check_enabled(tenant_id)

    try:
        dsm = await user_state_service.dismiss_insight(
            db, tenant_id=tenant_id, user_id=str(current_user.id), insight_id=insight_id, reason=body.reason
        )
        await audit_service.log_event(
            db, tenant_id=tenant_id, user_id=str(current_user.id), action="DISMISS", insight_id=insight_id
        )
        return dsm.model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "POST_SYNC_INSIGHTS_NOT_FOUND", "message": str(exc)}},
        )


@router.post("/runs/{run_id}/replay", response_model=dict[str, object])
async def replay_post_sync_insight_run(
    run_id: str,
    body: ReplayBodyV2,
    idempotency_key: IdempotencyKey = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = str(current_user.tenant_id)
    _check_enabled(tenant_id)

    user_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if user_role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "POST_SYNC_INSIGHTS_REPLAY_NOT_ALLOWED",
                    "message": "Apenas perfil ADMIN pode solicitar replay de execuções pós-sincronização.",
                }
            },
        )

    replay_req = PostSyncInsightReplayRequestV2(
        tenant_id=tenant_id,
        run_id=run_id,
        reason=body.reason,
    )
    result = await replay_service.replay_run(db, replay_req, post_sync_insights_service)
    await audit_service.log_event(
        db, tenant_id=tenant_id, user_id=str(current_user.id), action="REPLAY", run_id=run_id, details={"reason": body.reason}
    )
    return result.model_dump(mode="json")
