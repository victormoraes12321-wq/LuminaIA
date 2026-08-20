from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from .identity import (
    AI_ORCHESTRATION_VERSION,
    AIFallbackReasonV2,
    AIOrchestrationStateV2,
    AIOrchestrationStrategyV2,
)
from .budgets import (
    AICostBudgetV2,
    AITimeBudgetV2,
    AITokenBudgetV2,
    AIToolBudgetV2,
)
from .proposals import AIToolCallValidationV2


class AIOrchestrationRequestV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    user_query: str = Field(..., min_length=1, max_length=4096)
    session_id: Optional[str] = Field(default=None, max_length=128)
    client_request_id: Optional[str] = Field(default=None, max_length=128)
    idempotency_key: Optional[str] = Field(default=None, max_length=128)
    locale: str = Field(default="pt-BR")
    response_mode: str = Field(default="DETERMINISTIC_PREFERRED")
    presentation_hints: Dict[str, Any] = Field(default_factory=dict)


class AIResponseFactReferenceV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    fact_id: str = Field(...)
    metric_id: Optional[str] = Field(default=None)
    dimension_id: Optional[str] = Field(default=None)
    fact_value_raw: Any = Field(...)
    fact_value_decimal: Optional[Decimal] = Field(default=None)
    fact_value_formatted: str = Field(...)
    source_tool_id: str = Field(...)
    result_checksum: str = Field(...)


class AIResponseClaimV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str = Field(...)
    statement: str = Field(...)
    fact_references: List[str] = Field(default_factory=list)
    is_verified: bool = Field(default=True)


class AIResponseDraftV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    draft_text: str = Field(...)
    claims: List[AIResponseClaimV2] = Field(default_factory=list)
    facts: List[AIResponseFactReferenceV2] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    clarification_question: Optional[str] = Field(default=None)
    clarification_options: List[str] = Field(default_factory=list)
    checksum: str = Field(..., min_length=8)


class AIOrchestrationStepV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    step_sequence: int = Field(..., ge=1)
    state_from: AIOrchestrationStateV2 = Field(...)
    state_to: AIOrchestrationStateV2 = Field(...)
    transition_reason: str = Field(...)
    duration_ms: float = Field(default=0.0, ge=0.0)
    created_at: datetime = Field(...)


class AIOrchestrationAuditEventV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str = Field(...)
    event_type: str = Field(...)
    tenant_id: str = Field(...)
    user_id: str = Field(...)
    run_id: str = Field(...)
    step_sequence: int = Field(...)
    model_id: Optional[str] = Field(default=None)
    provider_id: Optional[str] = Field(default=None)
    tokens_consumed: int = Field(default=0)
    status: str = Field(...)
    checksum: str = Field(...)
    timestamp: datetime = Field(...)


class AIOrchestrationRunV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(..., min_length=3, max_length=128)
    tenant_id: str = Field(...)
    user_id: str = Field(...)
    session_id: str = Field(...)
    status: AIOrchestrationStateV2 = Field(default=AIOrchestrationStateV2.RECEIVED)
    strategy: AIOrchestrationStrategyV2 = Field(default=AIOrchestrationStrategyV2.SINGLE_MODEL_CALL)
    policy_version: str = Field(default=AI_ORCHESTRATION_VERSION)
    model_id: Optional[str] = Field(default=None)
    provider_id: Optional[str] = Field(default=None)
    prompt_template_version: Optional[int] = Field(default=None)
    token_budget: AITokenBudgetV2 = Field(...)
    tool_budget: AIToolBudgetV2 = Field(...)
    time_budget: AITimeBudgetV2 = Field(...)
    cost_budget: AICostBudgetV2 = Field(...)
    steps: List[AIOrchestrationStepV2] = Field(default_factory=list)
    validations: List[AIToolCallValidationV2] = Field(default_factory=list)
    fallback_reason: AIFallbackReasonV2 = Field(default=AIFallbackReasonV2.NONE)
    idempotency_key: Optional[str] = Field(default=None)
    checksum: str = Field(..., min_length=8)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)


class AIOrchestrationResponseV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(...)
    tenant_id: str = Field(...)
    user_id: str = Field(...)
    status: AIOrchestrationStateV2 = Field(...)
    strategy: AIOrchestrationStrategyV2 = Field(...)
    response_text: str = Field(...)
    facts: List[AIResponseFactReferenceV2] = Field(default_factory=list)
    clarification_question: Optional[str] = Field(default=None)
    clarification_options: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    token_usage: AITokenBudgetV2 = Field(...)
    fallback_reason: AIFallbackReasonV2 = Field(default=AIFallbackReasonV2.NONE)
    execution_time_ms: float = Field(default=0.0, ge=0.0)
    version: str = Field(default=AI_ORCHESTRATION_VERSION)
    checksum: str = Field(..., min_length=8)
