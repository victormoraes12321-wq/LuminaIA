from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from .identity import AI_ORCHESTRATION_VERSION, AIModelPurposeV2, AIPromptTemplateStatusV2


class AIModelCapabilityV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    supports_tool_calling: bool = Field(default=True)
    supports_structured_output: bool = Field(default=True)
    supports_streaming: bool = Field(default=False)
    supports_vision: bool = Field(default=False)
    max_input_context_tokens: int = Field(default=128000, ge=1000)
    max_output_generation_tokens: int = Field(default=16384, ge=100)


class AIModelDefinitionV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    canonical_model_id: str = Field(..., min_length=3, max_length=128)
    provider_id: str = Field(..., min_length=3, max_length=64)
    internal_provider_model_name: str = Field(..., min_length=1, max_length=128)
    is_active: bool = Field(default=True)
    allowed_purposes: List[AIModelPurposeV2] = Field(default_factory=lambda: [AIModelPurposeV2.INTENT_ASSISTANCE, AIModelPurposeV2.TOOL_PROPOSAL, AIModelPurposeV2.RESPONSE_DRAFTING])
    capability: AIModelCapabilityV2 = Field(default_factory=AIModelCapabilityV2)
    temperature_default: float = Field(default=0.0, ge=0.0, le=2.0)
    data_classification_ceiling: str = Field(default="INTERNAL_CONFIDENTIAL")
    owner: str = Field(default="system")
    checksum: str = Field(..., min_length=8)


class AIProviderDefinitionV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider_id: str = Field(..., min_length=3, max_length=64)
    display_name: str = Field(..., min_length=3, max_length=128)
    adapter_class: str = Field(..., min_length=5, max_length=256)
    is_active: bool = Field(default=True)
    health_status: str = Field(default="HEALTHY")
    latency_p95_ms: float = Field(default=150.0, ge=0.0)
    error_rate_5m: float = Field(default=0.0, ge=0.0, le=1.0)
    checksum: str = Field(..., min_length=8)


class AIModelPolicyV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    policy_id: str = Field(..., min_length=3, max_length=128)
    tenant_id: str = Field(default="system")
    purpose_map: dict[str, str] = Field(default_factory=lambda: {
        AIModelPurposeV2.INTENT_ASSISTANCE.value: "gpt-4o-mini",
        AIModelPurposeV2.TOOL_PROPOSAL.value: "gpt-4o-mini",
        AIModelPurposeV2.RESPONSE_DRAFTING.value: "gpt-4o-mini",
        AIModelPurposeV2.CLARIFICATION_DRAFTING.value: "gpt-4o-mini",
    })
    fallback_chain: List[str] = Field(default_factory=lambda: ["gpt-4o-mini", "fake-deterministic-v1"])
    version: str = Field(default=AI_ORCHESTRATION_VERSION)
    checksum: str = Field(..., min_length=8)


class AIProviderPolicyV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    policy_id: str = Field(..., min_length=3, max_length=128)
    tenant_id: str = Field(default="system")
    allowed_providers: List[str] = Field(default_factory=lambda: ["openai", "fake_provider"])
    default_provider: str = Field(default="fake_provider")
    version: str = Field(default=AI_ORCHESTRATION_VERSION)
    checksum: str = Field(..., min_length=8)


class AIPromptTemplateVersionV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    template_id: str = Field(..., min_length=3, max_length=128)
    version: int = Field(..., ge=1)
    purpose: AIModelPurposeV2 = Field(...)
    locale: str = Field(default="pt-BR")
    status: AIPromptTemplateStatusV2 = Field(default=AIPromptTemplateStatusV2.ACTIVE)
    system_policy_text: str = Field(..., min_length=10)
    required_context_sections: List[str] = Field(default_factory=list)
    output_contract_schema_name: str = Field(default="AIModelProposalV2")
    checksum: str = Field(..., min_length=8)


class AIPromptTemplateV2(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    template_id: str = Field(..., min_length=3, max_length=128)
    description: str = Field(...)
    active_version: int = Field(default=1, ge=1)
    versions: List[AIPromptTemplateVersionV2] = Field(default_factory=list)
    checksum: str = Field(..., min_length=8)
