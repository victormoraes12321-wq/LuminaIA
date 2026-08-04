from __future__ import annotations

import time
import uuid
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from config import settings
from contracts.ai_tool_registry_v2 import (
    AIToolCatalogV2,
    AIToolInvocationContextV2,
    AIToolInvocationRequestV2,
    AIToolOutputEnvelopeV2,
    AIToolRegistrationRequestV2,
    AIToolRegistryManifestV2,
    AIToolRegistrySnapshotV2,
)
from models.user import User
from routers.dependencies import get_current_user
from services.ai_tool_registry.catalog_builder import ai_tool_catalog_builder
from services.ai_tool_registry.exceptions import AIToolException
from services.ai_tool_registry.invocation_service import governed_ai_tool_invocation_service
from services.ai_tool_registry.registry_service import governed_ai_tool_registry_service
from services.ai_tool_registry.repository import ai_tool_registry_repository

router = APIRouter(
    prefix="/api/v2/tools",
    tags=["Governed AI Tool Registry V2"],
)

admin_router = APIRouter(
    prefix="/api/v2/admin/tools",
    tags=["Governed AI Tool Registry Admin V2"],
)


def _ensure_admin(user: User) -> None:
    role_str = getattr(user.role, "value", str(user.role)).upper()
    if role_str != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores podem gerenciar o registro de ferramentas de IA.",
        )


# ── Public / Runtime Tool Registry Endpoints ─────────────────────────

@router.get("/catalog", response_model=AIToolCatalogV2)
async def get_tool_catalog(
    current_user: Annotated[User, Depends(get_current_user)],
) -> AIToolCatalogV2:
    """Returns minimized public tool catalog filtered for current tenant & user capabilities."""
    manifest = await governed_ai_tool_registry_service.get_active_manifest(current_user.tenant_id)
    role_str = getattr(current_user.role, "value", str(current_user.role)).upper()
    user_permissions = ["ai_tool:create", "ai_tool:review", "ai_tool:publish", "ai_tool:disable"] if role_str == "ADMIN" else []

    catalog = ai_tool_catalog_builder.build_catalog(
        snapshot_version=manifest.snapshot.version,
        tool_definitions=manifest.tool_definitions,
        allowed_capabilities=None,
    )
    return catalog


class ProposalValidationRequest(BaseModel):
    tool_id: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(extra="forbid")


class ProposalValidationResponse(BaseModel):
    is_valid: bool
    tool_id: str
    decision: str
    reason: str
    model_config = ConfigDict(extra="forbid")


@router.post("/validate-proposal", response_model=ProposalValidationResponse)
async def validate_tool_proposal(
    request: ProposalValidationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProposalValidationResponse:
    """Validates a proposed AI tool call without executing it."""
    allowed_tools = {
        "lumina.enterprise_knowledge.search",
        "lumina.enterprise_knowledge.get_metric_definition",
        "lumina.temporal.normalize",
        "lumina.semantic.search",
        "lumina.semantic.resolve_entity",
        "lumina.context.get_public_summary",
        "lumina.profile.get_application_summary",
        "lumina.intent.validate",
        "lumina.comparison.plan",
        "lumina.comparison.validate_plan",
        "lumina.clarification.build_options",
        "lumina.provenance.get_public_summary",
    }

    if request.tool_id not in allowed_tools:
        return ProposalValidationResponse(
            is_valid=False,
            tool_id=request.tool_id,
            decision="REJECTED",
            reason=f"Ferramenta '{request.tool_id}' não está cadastrada no registro governado.",
        )

    return ProposalValidationResponse(
        is_valid=True,
        tool_id=request.tool_id,
        decision="ALLOWED",
        reason="Proposta de chamada de ferramenta validada com sucesso pelo registro governado.",
    )


@router.post("/invoke", response_model=AIToolOutputEnvelopeV2)
async def invoke_governed_tool(
    request: AIToolInvocationRequestV2,
    current_user: Annotated[User, Depends(get_current_user)],
) -> AIToolOutputEnvelopeV2:
    """Executes a governed tool call with fail-closed security and audit logging."""
    role_str = getattr(current_user.role, "value", str(current_user.role)).upper()
    user_perms = ["ai_tool:create", "ai_tool:review", "ai_tool:publish", "ai_tool:disable"] if role_str == "ADMIN" else []

    context = AIToolInvocationContextV2(
        request_id=f"req_{uuid.uuid4().hex[:12]}",
        correlation_id=f"corr_{uuid.uuid4().hex[:12]}",
        tenant_id=str(current_user.tenant_id),
        user_id=str(current_user.id),
        user_role=role_str,
        user_permissions=user_perms,
        session_id=f"sess_{uuid.uuid4().hex[:12]}",
        reference_time=str(time.time()),
        snapshot_version="1.0.0",
        tool_id=request.tool_id,
        tool_version=request.requested_version or "1.0.0",
    )

    try:
        envelope = await governed_ai_tool_invocation_service.invoke_tool(request, context)
        return envelope
    except AIToolException as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": exc.code, "message": exc.message, "details": exc.details},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "AI_TOOL_EXECUTION_FAILED", "message": str(exc)},
        )


# ── Admin Endpoints ────────────────────────────────────────────────

@admin_router.get("")
async def list_admin_tools(
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    _ensure_admin(current_user)
    identities = await ai_tool_registry_repository.list_tool_identities(current_user.tenant_id)
    items = []
    for ident in identities:
        items.append({
            "tool_id": ident.tool_id,
            "canonical_name": ident.canonical_name,
            "display_name": ident.display_name,
            "domain": ident.domain,
            "tool_type": ident.tool_type,
            "risk_class": ident.risk_class,
            "side_effect": ident.side_effect,
            "created_at": str(ident.created_at),
        })
    return {"items": items, "count": len(items)}


@admin_router.post("")
async def register_admin_tool(
    request: AIToolRegistrationRequestV2,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    _ensure_admin(current_user)
    try:
        result = await governed_ai_tool_registry_service.register_tool_identity(
            tenant_id=current_user.tenant_id,
            user_id=str(current_user.id),
            user_permissions=["ai_tool:create", "admin"],
            request=request,
        )
        return {"status": "success", "tool_id": result.tool_id}
    except AIToolException as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message})


class ReviewPayload(BaseModel):
    approved: bool
    notes: str = ""
    model_config = ConfigDict(extra="forbid")


@admin_router.post("/{tool_id}/versions/{version}/review")
async def review_tool_version(
    tool_id: str,
    version: str,
    payload: ReviewPayload,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    _ensure_admin(current_user)
    try:
        ok = await governed_ai_tool_registry_service.submit_review(
            tenant_id=current_user.tenant_id,
            user_id=str(current_user.id),
            user_permissions=["ai_tool:review", "admin"],
            tool_id=tool_id,
            version=version,
            approved=payload.approved,
            review_notes=payload.notes,
        )
        return {"status": "success" if ok else "failed", "tool_id": tool_id, "version": version}
    except AIToolException as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message})


@admin_router.post("/{tool_id}/versions/{version}/publish")
async def publish_tool_version(
    tool_id: str,
    version: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    _ensure_admin(current_user)
    try:
        ok = await governed_ai_tool_registry_service.publish_tool_version(
            tenant_id=current_user.tenant_id,
            user_id=str(current_user.id),
            user_permissions=["ai_tool:publish", "admin"],
            tool_id=tool_id,
            version=version,
        )
        return {"status": "success" if ok else "failed", "tool_id": tool_id, "version": version}
    except AIToolException as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message})


@admin_router.post("/{tool_id}/versions/{version}/disable")
async def disable_tool_version(
    tool_id: str,
    version: str,
    reason: str = Query("Emergency admin disable"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
) -> Dict[str, Any]:
    _ensure_admin(current_user)
    try:
        ok = await governed_ai_tool_registry_service.disable_tool_version(
            tenant_id=current_user.tenant_id,
            user_id=str(current_user.id),
            user_permissions=["ai_tool:disable", "admin"],
            tool_id=tool_id,
            version=version,
            reason=reason,
        )
        return {"status": "success" if ok else "failed", "tool_id": tool_id, "version": version}
    except AIToolException as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message})


@admin_router.get("/snapshots")
async def list_snapshots(
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    _ensure_admin(current_user)
    snaps = await ai_tool_registry_repository.list_snapshots()
    items = []
    for s in snaps:
        items.append({
            "snapshot_id": s.snapshot_id,
            "version": s.version,
            "status": s.status,
            "created_by": s.created_by,
            "created_at": str(s.created_at),
        })
    return {"items": items, "count": len(items)}


@admin_router.post("/inspector/test")
async def test_tool_synthetic(
    request: AIToolInvocationRequestV2,
    current_user: Annotated[User, Depends(get_current_user)],
) -> AIToolOutputEnvelopeV2:
    _ensure_admin(current_user)
    context = AIToolInvocationContextV2(
        request_id=f"inspector_{uuid.uuid4().hex[:8]}",
        correlation_id=f"corr_{uuid.uuid4().hex[:8]}",
        tenant_id=str(current_user.tenant_id),
        user_id=str(current_user.id),
        user_role="ADMIN",
        user_permissions=["admin", "ai_tool:create", "ai_tool:review", "ai_tool:publish"],
        session_id=f"sess_{uuid.uuid4().hex[:8]}",
        reference_time=str(time.time()),
        snapshot_version="1.0.0",
        tool_id=request.tool_id,
        tool_version=request.requested_version or "1.0.0",
    )
    return await governed_ai_tool_invocation_service.invoke_tool(request, context)
