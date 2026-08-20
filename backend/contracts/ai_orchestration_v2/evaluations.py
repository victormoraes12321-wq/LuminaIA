from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from .identity import AIOrchestrationStateV2, AIOrchestrationStrategyV2


class AIOrchestrationEvaluationCaseV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str = Field(..., min_length=3, max_length=128)
    title: str = Field(...)
    user_query: str = Field(...)
    expected_strategy: AIOrchestrationStrategyV2 = Field(...)
    expected_status: AIOrchestrationStateV2 = Field(...)
    expected_tools: List[str] = Field(default_factory=list)
    forbidden_tools: List[str] = Field(default_factory=list)
    expected_facts: List[Dict[str, Any]] = Field(default_factory=list)
    should_prompt_injection_block: bool = Field(default=False)
    checksum: str = Field(..., min_length=8)


class AIOrchestrationEvaluationResultV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    evaluation_id: str = Field(..., min_length=3, max_length=128)
    case_id: str = Field(...)
    passed: bool = Field(...)
    actual_strategy: AIOrchestrationStrategyV2 = Field(...)
    actual_status: AIOrchestrationStateV2 = Field(...)
    actual_tools: List[str] = Field(default_factory=list)
    tokens_used: int = Field(default=0)
    duration_ms: float = Field(default=0.0)
    failure_reasons: List[str] = Field(default_factory=list)
    checksum: str = Field(..., min_length=8)
