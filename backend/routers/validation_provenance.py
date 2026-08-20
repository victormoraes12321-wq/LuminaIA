"""
LuminaAI Governed Validation & Provenance V2 Router
Version: lumina.validation-provenance/1.0
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_context
from contracts.validation_provenance_v2 import (
    CertificationEnvelopeV2,
    PublicProvenanceSummaryV2,
    ValidationContextV2,
    ValidationPolicyV2,
    ValidationRequestV2,
    ValidationStatus,
)
from services.validation_provenance import GovernedValidationPipeline, ValidationPolicyService
from routers.dependencies import get_current_user

router = APIRouter(prefix="/api/v2/validation", tags=["Validation & Provenance V2"])


async def get_current_user_tenant(
    current_user: Any = Depends(get_current_user),
) -> tuple[UUID, UUID]:
    """Derive identity exclusively from the signed token and PostgreSQL user."""
    return UUID(str(current_user.tenant_id)), UUID(str(current_user.id))


class ValidationRunRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    result_payload: Dict
    response_draft_text: Optional[str] = None
    proposed_facts: List[Dict] = []
    proposed_claims: List[Dict] = []
    tenant_proof: Optional[Dict] = None


@router.post("/run", response_model=CertificationEnvelopeV2)
async def run_validation_pipeline(
    body: ValidationRunRequestBody,
    auth: tuple[UUID, UUID] = Depends(get_current_user_tenant),
):
    tenant_id, user_id = auth
    context = ValidationContextV2(
        tenant_id=tenant_id,
        user_id=user_id,
        request_id=body.request_id,
        policy_version="1.0.0",
    )
    req = ValidationRequestV2(
        context=context,
        result_payload=body.result_payload,
        response_draft_text=body.response_draft_text,
        proposed_facts=body.proposed_facts,
        proposed_claims=body.proposed_claims,
        tenant_proof=body.tenant_proof,
    )
    pipeline = GovernedValidationPipeline()
    envelope = await pipeline.execute(req)
    return envelope


@router.get("/policy/default", response_model=ValidationPolicyV2)
async def get_default_policy(
    auth: tuple[UUID, UUID] = Depends(get_current_user_tenant),
):
    tenant_id, _ = auth
    return ValidationPolicyService.get_default_policy(tenant_id)
