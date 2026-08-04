from __future__ import annotations

from typing import Any, Dict, List
from contracts.ai_tool_registry_v2 import (
    AIToolCapability,
    AIToolInvocationContextV2,
    AIToolValidatedArgumentsV2,
)
from services.ai_tool_registry.adapters.base import GovernedToolAdapter


class ContextGetPublicSummaryToolAdapter(GovernedToolAdapter):
    """Adapter for obtaining public conversational context summary."""

    @property
    def adapter_id(self) -> str:
        return "context.get_public_summary.v1"

    @property
    def tool_id(self) -> str:
        return "lumina.context.get_public_summary"

    @property
    def tool_version(self) -> str:
        return "1.0.0"

    async def validate_registration(self) -> None:
        pass

    async def validate_context(self, context: AIToolInvocationContextV2) -> None:
        if not context.session_id:
            raise ValueError("Session ID required in context.")

    async def validate_arguments(self, raw_args: Dict[str, Any]) -> AIToolValidatedArgumentsV2:
        clean_args = {"include_filters": bool(raw_args.get("include_filters", True))}
        checksum = self.compute_args_checksum(clean_args)
        return AIToolValidatedArgumentsV2(
            tool_id=self.tool_id,
            version=self.tool_version,
            validated_args=clean_args,
            args_checksum=checksum,
        )

    async def execute(
        self, valid_args: AIToolValidatedArgumentsV2, context: AIToolInvocationContextV2
    ) -> Dict[str, Any]:
        from services.conversation_state import conversation_state_service

        state_session = await conversation_state_service.get_session(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            session_id=context.session_id,
        )
        if not state_session:
            return {
                "session_id": context.session_id,
                "has_active_context": False,
                "active_metric": None,
                "active_period": None,
                "active_filters": {},
            }

        snapshot = getattr(state_session, "active_snapshot", None)
        active_metric = None
        active_period = None
        active_filters = {}

        if snapshot and isinstance(snapshot, dict):
            active_metric = snapshot.get("active_metric")
            active_period = snapshot.get("active_period")
            if valid_args.validated_args.get("include_filters"):
                active_filters = snapshot.get("filters", {})

        return {
            "session_id": context.session_id,
            "has_active_context": bool(snapshot),
            "active_metric": active_metric,
            "active_period": active_period,
            "active_filters": active_filters,
        }

    async def validate_output(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        if "has_active_context" not in raw_result:
            raise ValueError("Output missing 'has_active_context' field.")
        return raw_result

    async def redact_output(
        self, raw_result: Dict[str, Any], context: AIToolInvocationContextV2
    ) -> Dict[str, Any]:
        # Strip internal node_ids or database SQL if present
        return raw_result

    async def health_check(self) -> bool:
        return True

    def capabilities(self) -> List[AIToolCapability]:
        return [AIToolCapability.READ_CONVERSATION_CONTEXT]
