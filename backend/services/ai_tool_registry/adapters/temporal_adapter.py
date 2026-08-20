from __future__ import annotations

from datetime import datetime, timezone as tz
from typing import Any, Dict, List
from contracts.ai_tool_registry_v2 import (
    AIToolCapability,
    AIToolInvocationContextV2,
    AIToolValidatedArgumentsV2,
)
from services.ai_tool_registry.adapters.base import GovernedToolAdapter


class TemporalNormalizeToolAdapter(GovernedToolAdapter):

    @property
    def adapter_id(self) -> str:
        return "temporal.normalize.v1"

    @property
    def tool_id(self) -> str:
        return "lumina.temporal.normalize"

    @property
    def tool_version(self) -> str:
        return "1.0.0"

    def capabilities(self) -> List[AIToolCapability]:
        return [AIToolCapability.NORMALIZE_TEMPORAL_EXPRESSION]

    async def validate_registration(self) -> None:
        pass

    async def validate_context(self, context: AIToolInvocationContextV2) -> None:
        pass

    async def validate_arguments(self, raw_args: Dict[str, Any]) -> AIToolValidatedArgumentsV2:
        expression = str(raw_args.get("expression") or "").strip()
        if not expression:
            raise ValueError("Argument 'expression' is required.")
        clean_args = {"expression": expression}
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
        from config import settings
        from services.temporal.context import build_temporal_context
        from services.temporal.feature_flags import TemporalFeaturePolicy, TemporalNormalizationGateway

        expression = valid_args.validated_args["expression"]
        if context.reference_time:
            try:
                ref_dt = datetime.fromisoformat(context.reference_time)
                if ref_dt.tzinfo is None:
                    ref_dt = ref_dt.replace(tzinfo=tz.utc)
            except Exception:
                ref_dt = datetime.now(tz.utc)
        else:
            ref_dt = datetime.now(tz.utc)

        temp_context = build_temporal_context(
            reference_datetime=ref_dt,
            explicit_authorized_timezone=context.timezone,
        )
        gateway = TemporalNormalizationGateway(
            policy=TemporalFeaturePolicy.from_settings(settings)
        )

        try:
            res = gateway.normalize(expression, temp_context)
            time_window = None
            if res.windows:
                w = res.windows[0]
                time_window = {
                    "start": w.start.isoformat(),
                    "end": w.end.isoformat(),
                    "granularity": str(w.granularity.value) if hasattr(w.granularity, "value") else str(w.granularity),
                }
            return {
                "expression": expression,
                "success": time_window is not None,
                "time_window": time_window,
                "windows_count": len(res.windows),
            }
        except Exception as exc:
            return {
                "expression": expression,
                "success": False,
                "error": str(exc),
            }
