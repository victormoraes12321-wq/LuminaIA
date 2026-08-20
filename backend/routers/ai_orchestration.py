from __future__ import annotations

import logging
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from routers.auth import get_current_user
from contracts.ai_orchestration_v2.identity import AI_ORCHESTRATION_VERSION
from contracts.ai_orchestration_v2.orchestration import (
    AIOrchestrationRequestV2,
    AIOrchestrationResponseV2,
)
from services.ai_orchestration.orchestrator import GovernedAIOrchestrator
from services.ai_orchestration.model_registry_service import GovernedAIModelRouter
from services.ai_orchestration.policy_service import AIOrchestrationPolicyService
from services.ai_orchestration.prompt_template_service import AIPromptTemplateService

logger = logging.getLogger("luminaai.routers.ai_orchestration")

router = APIRouter(
    prefix="/api/v2/ai-orchestration",
    tags=["AI Orchestration V2"],
)

_orchestrator = GovernedAIOrchestrator()
_model_router = GovernedAIModelRouter()
_policy_service = AIOrchestrationPolicyService()
_prompt_template_service = AIPromptTemplateService()


def _require_admin(user: Any = Depends(get_current_user)) -> Any:
    role_value = getattr(user.role, "value", user.role)
    role = str(role_value or "").upper()
    if role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso permitido somente para administradores.",
        )
    return user


@router.post("/run", response_model=AIOrchestrationResponseV2)
async def run_ai_orchestration(
    payload: AIOrchestrationRequestV2,
    current_user: Any = Depends(get_current_user),
) -> AIOrchestrationResponseV2:
    """Runs governed AI orchestration for authenticated user and tenant."""
    tenant_id = str(current_user.tenant_id)
    user_id = str(current_user.id)
    user_role = str(getattr(current_user.role, "value", current_user.role) or "CONSULTA")

    try:
        return await _orchestrator.execute_orchestration(
            request=payload,
            tenant_id=tenant_id,
            user_id=user_id,
            user_roles=[user_role],
        )
    except Exception as exc:
        logger.error("[AIOrchestrationRouter] failure type=%s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro durante orquestracao de IA.",
        ) from exc


@router.get("/models")
async def list_model_definitions(
    current_user: Any = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Lists registered canonical models in the server-controlled Model Registry."""
    models = _model_router.list_models()
    return [m.model_dump(mode="json") for m in models]


@router.get("/providers")
async def list_provider_definitions(
    current_user: Any = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Lists registered provider adapters."""
    providers = _model_router.list_providers()
    return [p.model_dump(mode="json") for p in providers]


@router.get("/prompts")
async def list_prompt_templates(
    current_user: Any = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Lists active prompt templates and version histories."""
    templates = _prompt_template_service.list_templates()
    return [t.model_dump(mode="json") for t in templates]


class PolicyUpdatePayload(BaseModel):
    purpose_map: Dict[str, str]
    fallback_chain: List[str]


@router.get("/policies")
async def get_orchestration_policies(
    admin_user: Any = Depends(_require_admin),
) -> Dict[str, Any]:
    """Returns active model and provider policies for tenant."""
    tenant_id = str(admin_user.tenant_id)
    mp = _policy_service.get_model_policy(tenant_id)
    pp = _policy_service.get_provider_policy(tenant_id)
    return {
        "model_policy": mp.model_dump(mode="json"),
        "provider_policy": pp.model_dump(mode="json"),
        "version": AI_ORCHESTRATION_VERSION,
    }


@router.post("/inspector/simulate")
async def simulate_inspection(
    payload: AIOrchestrationRequestV2,
    admin_user: Any = Depends(_require_admin),
) -> Dict[str, Any]:
    """Synthetic dry-run inspection tool for ADMIN users."""
    tenant_id = str(admin_user.tenant_id)
    user_id = str(admin_user.id)

    response = await _orchestrator.execute_orchestration(
        request=payload,
        tenant_id=tenant_id,
        user_id=user_id,
        user_roles=["ADMIN"],
    )
    return {
        "simulation": "COMPLETED",
        "response": response.model_dump(mode="json"),
        "inspector_note": "Dry-run simulation executed safely without external LLM network calls.",
    }
