"""Conditionally mounted governed dashboard AI proposal API."""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Query
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from contracts.dashboard_ai_assistance_v2 import (
    DashboardAiApplyRequestV2,
    DashboardAiApplyResultV2,
    DashboardAiAssistanceRequestV2,
    DashboardAiAuditEventV2,
    DashboardAiClarificationResponseV2,
    DashboardAiProposalDecisionV2,
    DashboardAiProposalEvidenceV2,
    DashboardAiProposalV2,
    DashboardAiReviseRequestV2,
    StrictDashboardAiModel,
)
from database import get_db
from models.user import User
from routers.dependencies import get_current_user
from services.dashboard_ai_assistance_v2 import (
    DashboardAiAssistanceError,
    DashboardAiAssistanceServiceV2,
    DashboardAiAuditRepositoryV2,
    DashboardAiEvidenceRepositoryV2,
    DashboardAiProposalApplicationServiceV2,
    DashboardAiProposalRepositoryV2,
)
from services.dashboard_backend_v2 import DashboardActorContextV2

router = APIRouter(prefix="/api/v2/dashboard-ai", tags=["Governed Dashboard AI Assistance V2"])
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=200)]


class DashboardAiDecisionRequestV2(StrictDashboardAiModel):
    proposal_version: int = Field(ge=1)
    expected_lock_version: int = Field(ge=1)
    comment: str = Field(min_length=3, max_length=1000)


class DashboardAiCancelRequestV2(StrictDashboardAiModel):
    expected_lock_version: int = Field(ge=1)
    confirmation: Literal["CANCEL_DASHBOARD_AI_PROPOSAL"]


def _actor(user: User) -> DashboardActorContextV2:
    return DashboardActorContextV2(tenant_id=str(user.tenant_id), user_id=str(user.id), global_role=user.role.value if hasattr(user.role, "value") else str(user.role))


def _require_enabled(actor: DashboardActorContextV2) -> None:
    if settings.DASHBOARD_AI_ASSISTANCE_MODE == "LEGACY_ONLY" or not settings.DASHBOARD_AI_APIS_ENABLED:
        raise DashboardAiAssistanceError("DASHBOARD_AI_UNAVAILABLE", "Assistência de dashboard desativada.", 503)
    if settings.DASHBOARD_AI_TENANT_ALLOWLIST and actor.tenant_id not in settings.DASHBOARD_AI_TENANT_ALLOWLIST:
        raise DashboardAiAssistanceError("DASHBOARD_AI_ACCESS_DENIED", "Tenant fora do rollout aprovado.", 403)


def _require_generation(actor: DashboardActorContextV2) -> None:
    _require_enabled(actor)
    if settings.DASHBOARD_AI_ASSISTANCE_MODE not in {"AI_PROPOSAL_PREVIEW", "AI_DRAFT_CREATE", "AI_ASSISTED_EDIT"}:
        raise DashboardAiAssistanceError("DASHBOARD_AI_PREVIEW_DISABLED", "Geração de propostas desativada neste modo.", 503)
    if not settings.LUMINA_TESTING or not settings.DASHBOARD_AI_FAKE_PROVIDER_ENABLED:
        raise DashboardAiAssistanceError("DASHBOARD_AI_PROVIDER_UNAVAILABLE", "Provider governado não habilitado para esta implantação.", 503)


@router.post("/proposals", response_model=DashboardAiProposalV2, status_code=201)
async def create_proposal(request: DashboardAiAssistanceRequestV2, idempotency_key: IdempotencyKey, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> DashboardAiProposalV2:
    actor = _actor(user); _require_generation(actor)
    return await DashboardAiAssistanceServiceV2(session).create(actor=actor, request=request, idempotency_key=idempotency_key)


@router.get("/proposals", response_model=tuple[DashboardAiProposalV2, ...])
async def list_proposals(limit: int = Query(default=50, ge=1, le=100), cursor: str | None = Query(default=None), user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> tuple[DashboardAiProposalV2, ...]:
    actor = _actor(user); _require_enabled(actor)
    service = DashboardAiAssistanceServiceV2(session)
    rows = await service.proposals.list(actor.tenant_id, actor.user_id, limit=limit, cursor=cursor)
    return tuple([await service.contract(actor, row) for row in rows])


@router.get("/proposals/{proposal_id}", response_model=DashboardAiProposalV2)
async def get_proposal(proposal_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> DashboardAiProposalV2:
    actor = _actor(user); _require_enabled(actor)
    service = DashboardAiAssistanceServiceV2(session)
    row = await service.proposals.get(actor.tenant_id, proposal_id, user_id=actor.user_id)
    return await service.contract(actor, row)


@router.post("/proposals/{proposal_id}/clarifications", response_model=DashboardAiProposalV2)
async def answer_clarification(proposal_id: str, response: DashboardAiClarificationResponseV2, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> DashboardAiProposalV2:
    actor = _actor(user); _require_generation(actor)
    return await DashboardAiAssistanceServiceV2(session).answer_clarification(actor=actor, proposal_id=proposal_id, response=response)


@router.post("/proposals/{proposal_id}/revise", response_model=DashboardAiProposalV2)
async def revise_proposal(proposal_id: str, request: DashboardAiReviseRequestV2, idempotency_key: IdempotencyKey, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> DashboardAiProposalV2:
    actor = _actor(user); _require_generation(actor)
    return await DashboardAiAssistanceServiceV2(session).revise(actor=actor, proposal_id=proposal_id, request=request, idempotency_key=idempotency_key)


async def _decide(proposal_id: str, request: DashboardAiDecisionRequestV2, decision: str, idempotency_key: str, user: User, session: AsyncSession) -> DashboardAiProposalDecisionV2:
    actor = _actor(user); _require_enabled(actor)
    return await DashboardAiAssistanceServiceV2(session).decide(actor=actor, proposal_id=proposal_id, version=request.proposal_version, decision=decision, comment=request.comment, expected_lock=request.expected_lock_version, idempotency_key=idempotency_key)


@router.post("/proposals/{proposal_id}/accept", response_model=DashboardAiProposalDecisionV2)
async def accept_proposal(proposal_id: str, request: DashboardAiDecisionRequestV2, idempotency_key: IdempotencyKey, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> DashboardAiProposalDecisionV2:
    return await _decide(proposal_id, request, "ACCEPT", idempotency_key, user, session)


@router.post("/proposals/{proposal_id}/reject", response_model=DashboardAiProposalDecisionV2)
async def reject_proposal(proposal_id: str, request: DashboardAiDecisionRequestV2, idempotency_key: IdempotencyKey, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> DashboardAiProposalDecisionV2:
    return await _decide(proposal_id, request, "REJECT", idempotency_key, user, session)


@router.post("/proposals/{proposal_id}/cancel", response_model=DashboardAiProposalV2)
async def cancel_proposal(proposal_id: str, request: DashboardAiCancelRequestV2, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> DashboardAiProposalV2:
    actor = _actor(user); _require_enabled(actor)
    return await DashboardAiAssistanceServiceV2(session).cancel(actor=actor, proposal_id=proposal_id, expected_lock=request.expected_lock_version)


@router.post("/proposals/{proposal_id}/apply", response_model=DashboardAiApplyResultV2)
async def apply_proposal(proposal_id: str, request: DashboardAiApplyRequestV2, idempotency_key: IdempotencyKey, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> DashboardAiApplyResultV2:
    actor = _actor(user); _require_enabled(actor)
    if settings.DASHBOARD_AI_ASSISTANCE_MODE not in {"AI_DRAFT_CREATE", "AI_ASSISTED_EDIT"}:
        raise DashboardAiAssistanceError("DASHBOARD_AI_APPLY_DISABLED", "Aplicação de propostas desativada neste modo.", 503)
    return await DashboardAiProposalApplicationServiceV2(session).apply(actor=actor, proposal_id=proposal_id, request=request, idempotency_key=idempotency_key)


@router.get("/proposals/{proposal_id}/evidence", response_model=tuple[DashboardAiProposalEvidenceV2, ...])
async def proposal_evidence(proposal_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> tuple[DashboardAiProposalEvidenceV2, ...]:
    actor = _actor(user); _require_enabled(actor)
    await DashboardAiProposalRepositoryV2(session).get(actor.tenant_id, proposal_id, user_id=actor.user_id)
    rows = await DashboardAiEvidenceRepositoryV2(session).list(actor.tenant_id, proposal_id)
    return tuple(DashboardAiProposalEvidenceV2(evidence_id=str(row.id), evidence_type=row.evidence_type, canonical_reference=row.canonical_reference, public_label=row.public_label, authority_version=row.authority_version, checksum=row.evidence_checksum) for row in rows)


@router.get("/proposals/{proposal_id}/audit", response_model=tuple[DashboardAiAuditEventV2, ...])
async def proposal_audit(proposal_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)) -> tuple[DashboardAiAuditEventV2, ...]:
    actor = _actor(user); _require_enabled(actor)
    await DashboardAiProposalRepositoryV2(session).get(actor.tenant_id, proposal_id, user_id=actor.user_id)
    rows = await DashboardAiAuditRepositoryV2(session).list(actor.tenant_id, proposal_id)
    return tuple(DashboardAiAuditEventV2(event_id=str(row.id), proposal_id=str(row.proposal_id), event_type=row.event_type, outcome=row.outcome, actor_user_id=str(row.actor_user_id), metadata_checksum=row.metadata_checksum, occurred_at=row.occurred_at) for row in rows)


@router.post("/evaluations")
async def evaluation_status(user: User = Depends(get_current_user)) -> dict[str, str]:
    actor = _actor(user); _require_enabled(actor)
    if actor.global_role != "ADMIN" or not settings.DASHBOARD_AI_EVALUATIONS_ENABLED:
        raise DashboardAiAssistanceError("DASHBOARD_AI_EVALUATIONS_DISABLED", "Avaliações administrativas desativadas.", 503)
    return {"contract_version": "lumina.dashboard-ai-assistance/1.0", "status": "AVAILABLE_OFFLINE"}
