from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from contracts.ai_orchestration_v2.proposals import AIModelProposalV2


class GovernedAIProviderAdapter(ABC):
    """Abstract Base Class for Governed AI Provider Adapters."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        pass

    @property
    @abstractmethod
    def provider_version(self) -> str:
        pass

    @abstractmethod
    async def validate_configuration(self) -> bool:
        pass

    @abstractmethod
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
        """Returns dict containing 'proposal': AIModelProposalV2, 'usage': dict, 'duration_ms': float."""
        pass

    @abstractmethod
    async def invoke_text(
        self,
        model_name: str,
        system_prompt: str,
        user_query: str,
        context_payload: Dict[str, Any],
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def cancel(self, run_id: str) -> bool:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass
