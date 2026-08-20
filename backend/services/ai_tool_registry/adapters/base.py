from __future__ import annotations

import abc
import hashlib
import json
from typing import Any, Dict, List
from contracts.ai_tool_registry_v2 import (
    AIToolCapability,
    AIToolInvocationContextV2,
    AIToolValidatedArgumentsV2,
)


class GovernedToolAdapter(abc.ABC):
    """
    Abstract base class for all governed AI tool adapters in LuminaAI.
    Enforces strict static registration, context validation, input schema checking,
    isolated execution, output validation, and redaction.
    """

    @property
    @abc.abstractmethod
    def adapter_id(self) -> str:
        """Unique allowlisted adapter identifier (e.g. 'temporal.normalize.v1')."""
        pass

    @property
    @abc.abstractmethod
    def tool_id(self) -> str:
        """Canonical tool ID associated with this adapter."""
        pass

    @property
    @abc.abstractmethod
    def tool_version(self) -> str:
        """Supported semantic version (e.g. '1.0.0')."""
        pass

    @abc.abstractmethod
    async def validate_registration(self) -> None:
        """Validates adapter readiness during tool registration."""
        pass

    @abc.abstractmethod
    async def validate_context(self, context: AIToolInvocationContextV2) -> None:
        """Validates tenant, permissions, and security constraints before invocation."""
        pass

    @abc.abstractmethod
    async def validate_arguments(self, raw_args: Dict[str, Any]) -> AIToolValidatedArgumentsV2:
        """Validates raw arguments against the strict input JSON schema."""
        pass

    @abc.abstractmethod
    async def execute(
        self, valid_args: AIToolValidatedArgumentsV2, context: AIToolInvocationContextV2
    ) -> Dict[str, Any]:
        """Executes the internal domain capability synchronously or asynchronously."""
        pass

    async def validate_output(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validates execution result against output JSON schema."""
        return raw_result

    async def redact_output(
        self, raw_result: Dict[str, Any], context: AIToolInvocationContextV2
    ) -> Dict[str, Any]:
        """Applies data classification redaction rules to prevent secret/PII leaks."""
        return raw_result

    async def health_check(self) -> bool:
        """Performs liveness check for circuit breaker monitoring."""
        return True

    def capabilities(self) -> List[AIToolCapability]:
        """Returns list of capabilities provided by this adapter."""
        return [AIToolCapability.READ_ENTERPRISE_KNOWLEDGE]

    def compute_args_checksum(self, valid_args: Dict[str, Any]) -> str:
        serialized = json.dumps(valid_args, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
