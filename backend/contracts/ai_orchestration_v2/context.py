from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AIContextSectionTypeV2(str, Enum):
    SYSTEM_POLICY = "SYSTEM_POLICY"
    OUTPUT_CONTRACT = "OUTPUT_CONTRACT"
    CURRENT_USER_MESSAGE = "CURRENT_USER_MESSAGE"
    CANONICAL_INTENT = "CANONICAL_INTENT"
    CONVERSATION_PUBLIC_CONTEXT = "CONVERSATION_PUBLIC_CONTEXT"
    CLARIFICATION_CONTEXT = "CLARIFICATION_CONTEXT"
    ENTERPRISE_KNOWLEDGE = "ENTERPRISE_KNOWLEDGE"
    SEMANTIC_CANDIDATES = "SEMANTIC_CANDIDATES"
    USER_PROFILE_SUMMARY = "USER_PROFILE_SUMMARY"
    TOOL_CATALOG = "TOOL_CATALOG"
    VALIDATED_TOOL_RESULTS = "VALIDATED_TOOL_RESULTS"
    PUBLIC_PROVENANCE = "PUBLIC_PROVENANCE"
    RECENT_PUBLIC_HISTORY = "RECENT_PUBLIC_HISTORY"
    LEGACY_CONTEXT = "LEGACY_CONTEXT"


class AIContextSectionV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    section_type: AIContextSectionTypeV2 = Field(...)
    priority: int = Field(..., ge=1, le=100)
    classification: str = Field(default="INTERNAL")
    source: str = Field(default="system")
    content_text: str = Field(...)
    estimated_tokens: int = Field(default=0, ge=0)
    included: bool = Field(default=True)
    truncated: bool = Field(default=False)
    truncation_reason: Optional[str] = Field(default=None)
    checksum: str = Field(..., min_length=8)


class AIContextSelectionDecisionV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    section_type: AIContextSectionTypeV2 = Field(...)
    action: str = Field(...)  # INCLUDED, TRUNCATED, OMITTED_BUDGET
    reason: str = Field(...)
    token_delta: int = Field(default=0)


class AIContextEnvelopeV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    envelope_id: str = Field(..., min_length=3, max_length=128)
    tenant_id: str = Field(...)
    user_id: str = Field(...)
    sections: List[AIContextSectionV2] = Field(default_factory=list)
    selection_decisions: List[AIContextSelectionDecisionV2] = Field(default_factory=list)
    total_estimated_tokens: int = Field(default=0, ge=0)
    is_compacted: bool = Field(default=False)
    checksum: str = Field(..., min_length=8)
