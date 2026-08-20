from __future__ import annotations

import hashlib
import os
from typing import Dict
from contracts.ai_orchestration_v2.identity import AI_ORCHESTRATION_VERSION
from contracts.ai_orchestration_v2.registry import AIModelPolicyV2, AIProviderPolicyV2


class AIOrchestrationPolicyService:
    """Policy Service for AI Orchestration policies, model policies, and provider policies."""

    def __init__(self) -> None:
        self._model_policies: Dict[str, AIModelPolicyV2] = {}
        self._provider_policies: Dict[str, AIProviderPolicyV2] = {}
        self._bootstrap_defaults()

    def _bootstrap_defaults(self) -> None:
        is_testing = (
            os.environ.get("LUMINA_TESTING", "").lower() in ("true", "1", "yes")
            or os.environ.get("MOCK_OPENAI", "").lower() in ("true", "1", "yes")
            or os.environ.get("ENVIRONMENT", "").lower() == "test"
        )
        default_model = "fake-deterministic-v1" if is_testing else "gpt-4o-mini"
        default_provider = "fake_provider" if is_testing else "openai"

        default_mp = AIModelPolicyV2(
            policy_id="default-model-policy",
            tenant_id="system",
            purpose_map={
                "INTENT_ASSISTANCE": default_model,
                "TOOL_PROPOSAL": default_model,
                "RESPONSE_DRAFTING": default_model,
                "CLARIFICATION_DRAFTING": default_model,
            },
            fallback_chain=[default_model, "gpt-4o-mini"],
            version=AI_ORCHESTRATION_VERSION,
            checksum=hashlib.sha256(b"default-model-policy").hexdigest()[:16],
        )
        default_pp = AIProviderPolicyV2(
            policy_id="default-provider-policy",
            tenant_id="system",
            allowed_providers=["openai", "fake_provider"],
            default_provider=default_provider,
            version=AI_ORCHESTRATION_VERSION,
            checksum=hashlib.sha256(b"default-provider-policy").hexdigest()[:16],
        )
        self._model_policies["system"] = default_mp
        self._provider_policies["system"] = default_pp

    def get_model_policy(self, tenant_id: str) -> AIModelPolicyV2:
        return self._model_policies.get(tenant_id, self._model_policies["system"])

    def get_provider_policy(self, tenant_id: str) -> AIProviderPolicyV2:
        return self._provider_policies.get(tenant_id, self._provider_policies["system"])
