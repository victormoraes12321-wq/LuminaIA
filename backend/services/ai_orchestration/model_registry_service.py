from __future__ import annotations

import hashlib
from typing import Dict, List, Optional
from contracts.ai_orchestration_v2.identity import AIModelPurposeV2
from contracts.ai_orchestration_v2.registry import (
    AIModelCapabilityV2,
    AIModelDefinitionV2,
    AIModelPolicyV2,
    AIProviderDefinitionV2,
)
from .provider_adapters.base import GovernedAIProviderAdapter
from .provider_adapters.deterministic_fake import DeterministicFakeAIProviderAdapter
from .provider_adapters.openai_adapter import GovernedOpenAIProviderAdapter


class GovernedAIModelRouter:
    """
    Model Registry and Governed Model Router.
    Server-controlled routing based on explicit policies, capabilities, and health status.
    Prohibits user-supplied model names or unapproved provider endpoints.
    """

    def __init__(self) -> None:
        self._adapters: Dict[str, GovernedAIProviderAdapter] = {
            "fake_provider": DeterministicFakeAIProviderAdapter(),
            "openai": GovernedOpenAIProviderAdapter(),
        }
        self._models: Dict[str, AIModelDefinitionV2] = {}
        self._providers: Dict[str, AIProviderDefinitionV2] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        fake_def = AIProviderDefinitionV2(
            provider_id="fake_provider",
            display_name="Deterministic Fake AI Provider",
            adapter_class="DeterministicFakeAIProviderAdapter",
            is_active=True,
            health_status="HEALTHY",
            checksum=hashlib.sha256(b"fake_provider_def").hexdigest()[:16],
        )
        openai_def = AIProviderDefinitionV2(
            provider_id="openai",
            display_name="Governed OpenAI Provider",
            adapter_class="GovernedOpenAIProviderAdapter",
            is_active=True,
            health_status="HEALTHY",
            checksum=hashlib.sha256(b"openai_def").hexdigest()[:16],
        )
        self._providers["fake_provider"] = fake_def
        self._providers["openai"] = openai_def

        gpt4o_mini = AIModelDefinitionV2(
            canonical_model_id="gpt-4o-mini",
            provider_id="openai",
            internal_provider_model_name="gpt-4o-mini",
            is_active=True,
            allowed_purposes=[
                AIModelPurposeV2.INTENT_ASSISTANCE,
                AIModelPurposeV2.TOOL_PROPOSAL,
                AIModelPurposeV2.RESPONSE_DRAFTING,
                AIModelPurposeV2.CLARIFICATION_DRAFTING,
            ],
            capability=AIModelCapabilityV2(
                supports_tool_calling=True,
                supports_structured_output=True,
            ),
            checksum=hashlib.sha256(b"gpt-4o-mini").hexdigest()[:16],
        )
        fake_model = AIModelDefinitionV2(
            canonical_model_id="fake-deterministic-v1",
            provider_id="fake_provider",
            internal_provider_model_name="fake-deterministic-v1",
            is_active=True,
            allowed_purposes=[
                AIModelPurposeV2.INTENT_ASSISTANCE,
                AIModelPurposeV2.TOOL_PROPOSAL,
                AIModelPurposeV2.RESPONSE_DRAFTING,
                AIModelPurposeV2.CLARIFICATION_DRAFTING,
            ],
            capability=AIModelCapabilityV2(
                supports_tool_calling=True,
                supports_structured_output=True,
            ),
            checksum=hashlib.sha256(b"fake-deterministic-v1").hexdigest()[:16],
        )
        self._models["gpt-4o-mini"] = gpt4o_mini
        self._models["fake-deterministic-v1"] = fake_model

    def get_adapter(self, provider_id: str) -> GovernedAIProviderAdapter:
        if provider_id not in self._adapters:
            raise ValueError(f"Provider nao registrado ou proibido: {provider_id}")
        return self._adapters[provider_id]

    def get_model(self, canonical_model_id: str) -> AIModelDefinitionV2:
        if canonical_model_id not in self._models:
            raise ValueError(f"Modelo nao registrado ou proibido: {canonical_model_id}")
        return self._models[canonical_model_id]

    def list_models(self) -> List[AIModelDefinitionV2]:
        return list(self._models.values())

    def list_providers(self) -> List[AIProviderDefinitionV2]:
        return list(self._providers.values())

    def route_model(
        self,
        purpose: AIModelPurposeV2,
        model_policy: AIModelPolicyV2,
        requested_model_override: Optional[str] = None,
    ) -> Tuple[AIModelDefinitionV2, GovernedAIProviderAdapter]:
        # Server-controlled routing: resolve from model_policy purpose_map
        target_model_id = model_policy.purpose_map.get(purpose.value, "gpt-4o-mini")
        if target_model_id not in self._models or not self._models[target_model_id].is_active:
            # Fallback chain resolution
            for fb_model_id in model_policy.fallback_chain:
                if fb_model_id in self._models and self._models[fb_model_id].is_active:
                    target_model_id = fb_model_id
                    break

        model_def = self.get_model(target_model_id)
        if purpose not in model_def.allowed_purposes:
            raise ValueError(f"Modelo {model_def.canonical_model_id} nao e autorizado para {purpose.value}")

        adapter = self.get_adapter(model_def.provider_id)
        return model_def, adapter
