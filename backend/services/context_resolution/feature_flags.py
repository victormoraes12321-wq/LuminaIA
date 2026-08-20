from __future__ import annotations

from dataclasses import dataclass

from config import settings


@dataclass(frozen=True)
class ContextResolutionFeaturePolicy:
    enabled: bool
    shadow_mode: bool
    frontend_enabled: bool
    maximum_context_depth: int
    maximum_inherited_fields: int

    @classmethod
    def from_settings(cls) -> "ContextResolutionFeaturePolicy":
        return cls(
            enabled=settings.CONTEXT_RESOLUTION_V2_ENABLED,
            shadow_mode=settings.CONTEXT_RESOLUTION_V2_SHADOW_MODE,
            frontend_enabled=settings.CONTEXT_RESOLUTION_V2_FRONTEND_ENABLED,
            maximum_context_depth=settings.CONTEXT_RESOLUTION_MAXIMUM_DEPTH,
            maximum_inherited_fields=settings.CONTEXT_RESOLUTION_MAXIMUM_INHERITED_FIELDS,
        )

    @property
    def should_resolve(self) -> bool:
        return self.enabled or self.shadow_mode

    @property
    def can_author_state(self) -> bool:
        return self.enabled
