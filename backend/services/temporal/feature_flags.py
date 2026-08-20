from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Callable

from .models import TemporalContext, TemporalNormalizationResult
from .normalizer import TemporalNormalizer


logger = logging.getLogger("luminaai.services.temporal.rollout")


@dataclass(frozen=True)
class TemporalFeaturePolicy:
    enabled: bool = False
    shadow_mode: bool = True

    @classmethod
    def from_settings(cls, settings: object) -> "TemporalFeaturePolicy":
        return cls(
            enabled=bool(getattr(settings, "TEMPORAL_NORMALIZER_V2_ENABLED", False)),
            shadow_mode=bool(getattr(settings, "TEMPORAL_NORMALIZER_V2_SHADOW_MODE", True)),
        )


class TemporalNormalizationGateway:
    def __init__(
        self,
        *,
        policy: TemporalFeaturePolicy,
        normalizer: TemporalNormalizer | None = None,
    ) -> None:
        self._policy = policy
        self._normalizer = normalizer or TemporalNormalizer()

    def normalize(
        self,
        text: str,
        context: TemporalContext,
        *,
        legacy_parser: Callable[[str], tuple[str, str] | None] | None = None,
    ) -> TemporalNormalizationResult:
        result = self._normalizer.normalize(text, context)
        if self._policy.shadow_mode and legacy_parser is not None:
            legacy = legacy_parser(text)
            modern = [
                (window.start.isoformat(), window.end.isoformat())
                for window in result.windows
            ]
            legacy_shape = [legacy] if legacy else []
            if modern != legacy_shape:
                fingerprint = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
                logger.info(
                    "temporal_shadow_divergence fingerprint=%s rules=%s legacy_windows=%d "
                    "modern_windows=%d relation=%s",
                    fingerprint,
                    ",".join(result.rule_ids),
                    len(legacy_shape),
                    len(modern),
                    result.relation.value,
                )
        return result

    def select_ranges(
        self,
        text: str,
        context: TemporalContext,
        *,
        legacy_parser: Callable[[str], tuple[str, str] | None],
    ) -> tuple[TemporalNormalizationResult, list[tuple[str, str]]]:
        result = self.normalize(text, context, legacy_parser=legacy_parser)
        if self._policy.enabled:
            selected = [
                (window.start.isoformat(), window.end.isoformat())
                for window in result.windows
            ]
        else:
            legacy = legacy_parser(text)
            selected = [legacy] if legacy else []
        return result, selected

    @property
    def enabled(self) -> bool:
        return self._policy.enabled
