from __future__ import annotations

from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from .identity import AI_ORCHESTRATION_VERSION


class AITokenBudgetV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    max_request_tokens: int = Field(default=8192, ge=100)
    max_system_tokens: int = Field(default=2048, ge=50)
    max_context_tokens: int = Field(default=4096, ge=100)
    max_tool_catalog_tokens: int = Field(default=1024, ge=50)
    max_tool_result_tokens: int = Field(default=2048, ge=50)
    max_output_tokens: int = Field(default=2048, ge=50)
    reserved_output_tokens: int = Field(default=512, ge=16)
    safety_margin_tokens: int = Field(default=256, ge=0)
    estimated_input_tokens: int = Field(default=0, ge=0)
    actual_input_tokens: Optional[int] = Field(default=None, ge=0)
    actual_output_tokens: Optional[int] = Field(default=None, ge=0)
    total_actual_tokens: Optional[int] = Field(default=None, ge=0)
    remaining_tokens: int = Field(default=8192, ge=0)
    exceeded: bool = Field(default=False)
    policy_version: str = Field(default=AI_ORCHESTRATION_VERSION)


class AIToolBudgetV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    max_tool_calls: int = Field(default=4, ge=0, le=20)
    max_distinct_tools: int = Field(default=3, ge=0, le=10)
    max_sequential_depth: int = Field(default=3, ge=0, le=10)
    max_calls_per_tool: int = Field(default=2, ge=0, le=5)
    max_tool_output_bytes: int = Field(default=65536, ge=1024)
    max_cumulative_tool_output_bytes: int = Field(default=262144, ge=1024)
    max_analytical_executions: int = Field(default=2, ge=0, le=5)
    max_semantic_searches: int = Field(default=2, ge=0, le=5)
    remaining_calls: int = Field(default=4, ge=0)
    exceeded: bool = Field(default=False)


class AITimeBudgetV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    request_deadline_ms: int = Field(default=30000, ge=1000)
    max_orchestration_duration_ms: int = Field(default=25000, ge=1000)
    max_provider_duration_ms: int = Field(default=15000, ge=1000)
    max_tool_duration_ms: int = Field(default=10000, ge=1000)
    max_persistence_duration_ms: int = Field(default=5000, ge=500)
    remaining_duration_ms: int = Field(default=30000, ge=0)
    exceeded: bool = Field(default=False)


class AICostBudgetV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    estimated_input_cost: Decimal = Field(default=Decimal("0.0000"))
    estimated_output_cost: Decimal = Field(default=Decimal("0.0000"))
    actual_cost: Decimal = Field(default=Decimal("0.0000"))
    max_cost_limit: Decimal = Field(default=Decimal("0.1000"))
    currency: str = Field(default="USD")
    exceeded: bool = Field(default=False)


class AIContextBudgetV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    max_history_turns: int = Field(default=6, ge=0, le=20)
    max_knowledge_snippets: int = Field(default=5, ge=0, le=20)
    max_semantic_candidates: int = Field(default=5, ge=0, le=20)
    include_user_profile_summary: bool = Field(default=True)
    allow_dataset_snippets: bool = Field(default=False)
    allow_raw_sql: bool = Field(default=False)


class AIOutputBudgetV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    max_claims: int = Field(default=20, ge=1)
    max_fact_references: int = Field(default=50, ge=1)
    max_text_characters: int = Field(default=8000, ge=100)
