from __future__ import annotations

from typing import Any, Dict, List
from contracts.ai_tool_registry_v2 import (
    AIToolCapability,
    AIToolInvocationContextV2,
    AIToolValidatedArgumentsV2,
)
from services.ai_tool_registry.adapters.base import GovernedToolAdapter


class ProfileGetApplicationSummaryToolAdapter(GovernedToolAdapter):
    """Adapter for obtaining consented user analytical profile application summary."""

    @property
    def adapter_id(self) -> str:
        return "profile.get_application_summary.v1"

    @property
    def tool_id(self) -> str:
        return "lumina.profile.get_application_summary"

    @property
    def tool_version(self) -> str:
        return "1.0.0"

    async def validate_registration(self) -> None:
        pass

    async def validate_context(self, context: AIToolInvocationContextV2) -> None:
        if not context.user_id or not context.tenant_id:
            raise ValueError("User and Tenant authentication context required.")

    async def validate_arguments(self, raw_args: Dict[str, Any]) -> AIToolValidatedArgumentsV2:
        clean_args = {}
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
        from services.user_analytical_profile import get_user_analytical_profile_service

        service = get_user_analytical_profile_service()
        profile = await service.get_or_create_profile(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
        )
        if not profile:
            return {
                "has_profile": False,
                "preferred_chart_type": "bar_chart",
                "default_period": "current_year",
            }

        return {
            "has_profile": True,
            "preferred_chart_type": getattr(profile, "preferred_chart_type", "bar_chart") or "bar_chart",
            "default_period": getattr(profile, "default_period", "current_year") or "current_year",
            "consent_active": getattr(profile, "consent_active", True),
        }

    async def validate_output(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        if "has_profile" not in raw_result:
            raise ValueError("Output missing 'has_profile' field.")
        return raw_result

    async def redact_output(
        self, raw_result: Dict[str, Any], context: AIToolInvocationContextV2
    ) -> Dict[str, Any]:
        return raw_result

    async def health_check(self) -> bool:
        return True

    def capabilities(self) -> List[AIToolCapability]:
        return [AIToolCapability.READ_USER_PROFILE_SUMMARY]
