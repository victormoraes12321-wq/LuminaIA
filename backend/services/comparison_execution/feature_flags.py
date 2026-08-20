from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ComparisonExecutorFeaturePolicy:
    enabled: bool = False
    shadow_mode: bool = False

    @classmethod
    def from_settings(cls, settings) -> "ComparisonExecutorFeaturePolicy":
        return cls(
            enabled=bool(getattr(settings, "COMPARISON_EXECUTOR_V2_ENABLED", False)),
            shadow_mode=bool(
                getattr(settings, "COMPARISON_EXECUTOR_V2_SHADOW_MODE", False)
            ),
        )
