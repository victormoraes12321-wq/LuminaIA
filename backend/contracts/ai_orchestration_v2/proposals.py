from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from .identity import AIOrchestrationStrategyV2, AIToolProposalDecisionV2


class AIToolCallProposalV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    proposal_id: str = Field(..., min_length=3, max_length=128)
    sequence: int = Field(default=1, ge=1)
    tool_id: str = Field(..., min_length=3, max_length=128)
    tool_version: str = Field(default="1.0.0")
    arguments: Dict[str, Any] = Field(default_factory=dict)
    justification: Optional[str] = Field(default=None)
    args_checksum: str = Field(..., min_length=8)


class AIToolCallValidationV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    proposal_id: str = Field(...)
    tool_id: str = Field(...)
    decision: AIToolProposalDecisionV2 = Field(...)
    reason_code: str = Field(...)
    reason_details: str = Field(...)
    sanitized_arguments: Dict[str, Any] = Field(default_factory=dict)
    risk_level: str = Field(default="LOW")


class AIValidatedToolCallV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    proposal_id: str = Field(...)
    sequence: int = Field(...)
    tool_id: str = Field(...)
    tool_version: str = Field(...)
    sanitized_arguments: Dict[str, Any] = Field(default_factory=dict)
    capability_required: str = Field(...)
    args_checksum: str = Field(...)


class AIResponseDraftInstructionV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: str = Field(default="DETERMINISTIC_PRESENTATION")
    tone: str = Field(default="PROFESSIONAL")
    highlight_facts: List[str] = Field(default_factory=list)
    format_as: str = Field(default="TEXT")


class AIModelProposalV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    proposal_id: str = Field(..., min_length=3, max_length=128)
    strategy: AIOrchestrationStrategyV2 = Field(default=AIOrchestrationStrategyV2.SINGLE_MODEL_CALL)
    intent_refinement: Optional[str] = Field(default=None)
    clarification_question: Optional[str] = Field(default=None)
    clarification_options: List[str] = Field(default_factory=list)
    tool_proposals: List[AIToolCallProposalV2] = Field(default_factory=list)
    draft_instruction: Optional[AIResponseDraftInstructionV2] = Field(default=None)
    raw_reasoning_summary: Optional[str] = Field(default=None)
    checksum: str = Field(..., min_length=8)
