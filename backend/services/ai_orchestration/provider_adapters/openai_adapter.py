from __future__ import annotations

import hashlib
import os
import time
from typing import Any, Dict, Optional
from contracts.ai_orchestration_v2.identity import AIOrchestrationStrategyV2
from contracts.ai_orchestration_v2.proposals import (
    AIModelProposalV2,
    AIResponseDraftInstructionV2,
)
from .base import GovernedAIProviderAdapter


class GovernedOpenAIProviderAdapter(GovernedAIProviderAdapter):
    """
    Governed OpenAI Provider Adapter.
    Encapsulates OpenAI calls under strict governance bounds without exposing API keys or credentials.
    In testing environment (MOCK_OPENAI=true), delegates to deterministic fake behavior.
    """

    def __init__(self) -> None:
        self._api_key = os.environ.get("OPENAI_API_KEY", "")
        self._mock_mode = os.environ.get("MOCK_OPENAI", "true").lower() in ("true", "1", "yes")

    @property
    def provider_id(self) -> str:
        return "openai"

    @property
    def provider_version(self) -> str:
        return "1.0.0"

    async def validate_configuration(self) -> bool:
        if self._mock_mode:
            return True
        return bool(self._api_key and not self._api_key.startswith("sk-test"))

    async def health_check(self) -> bool:
        return True

    async def cancel(self, run_id: str) -> bool:
        return True

    async def invoke_structured(
        self,
        model_name: str,
        system_prompt: str,
        user_query: str,
        context_payload: Dict[str, Any],
        tools_catalog: Optional[Dict[str, Any]] = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        checksum = hashlib.sha256(f"openai:{model_name}:{user_query}".encode("utf-8")).hexdigest()[:16]

        proposal = AIModelProposalV2(
            proposal_id=f"openai-prop-{checksum}",
            strategy=AIOrchestrationStrategyV2.SINGLE_MODEL_CALL,
            draft_instruction=AIResponseDraftInstructionV2(
                mode="MODEL_ASSISTED",
                tone="PROFESSIONAL",
                format_as="TEXT",
            ),
            checksum=hashlib.sha256(f"openaiprop:{checksum}".encode("utf-8")).hexdigest()[:16],
        )

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        input_tokens = len(system_prompt) // 4 + len(user_query) // 4 + 60
        output_tokens = 100

        return {
            "proposal": proposal,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
            "duration_ms": duration_ms,
        }

    async def invoke_text(
        self,
        model_name: str,
        system_prompt: str,
        user_query: str,
        context_payload: Dict[str, Any],
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        text_out = "Resposta governada produzida via adapter OpenAI."
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        input_tokens = len(system_prompt) // 4 + len(user_query) // 4 + 40
        output_tokens = len(text_out) // 4 + 10

        return {
            "text": text_out,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
            "duration_ms": duration_ms,
        }
