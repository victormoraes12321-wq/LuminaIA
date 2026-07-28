from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .models import TemporalContext, TemporalNormalizationResult, TemporalRelation
from .normalizer import TemporalNormalizer, default_temporal_context


logger = logging.getLogger("luminaai.services.temporal.legacy")


class PluralTemporalResultError(ValueError):
    pass


class UnresolvedTemporalResultError(ValueError):
    pass


@dataclass(frozen=True)
class LegacyDateBinds:
    data_inicio: str
    data_fim: str
    end_exclusive: str


def normalize_legacy_date_range(
    text: str,
    *,
    context: TemporalContext | None = None,
    normalizer: TemporalNormalizer | None = None,
) -> tuple[str, str] | None:
    result = (normalizer or TemporalNormalizer()).normalize(
        text,
        context or default_temporal_context(),
    )
    return singular_range_from_result(result)


def singular_range_from_result(
    result: TemporalNormalizationResult,
) -> tuple[str, str] | None:
    if result.unresolved_expressions:
        raise UnresolvedTemporalResultError(
            "Temporal result requires clarification before legacy adaptation"
        )
    if result.relation in {TemporalRelation.PERIOD_LIST, TemporalRelation.COMPARISON}:
        raise PluralTemporalResultError(
            "Legacy singular temporal adapter refuses lists and comparisons"
        )
    if not result.windows:
        return None
    if len(result.windows) != 1:
        raise PluralTemporalResultError(
            "Legacy singular temporal adapter received multiple windows"
        )
    window = result.windows[0]
    return window.start.isoformat(), window.end.isoformat()


def legacy_binds_from_result(
    result: TemporalNormalizationResult,
) -> LegacyDateBinds | None:
    value = singular_range_from_result(result)
    if value is None:
        return None
    start, end = value
    end_exclusive = date.fromisoformat(end) + timedelta(days=1)
    return LegacyDateBinds(
        data_inicio=start,
        data_fim=end,
        end_exclusive=end_exclusive.isoformat(),
    )


def context_from_legacy_anchor(
    anchor: date,
    *,
    timezone_name: str = "America/Sao_Paulo",
) -> TemporalContext:
    from .timezone_support import resolve_timezone

    return default_temporal_context(
        reference_datetime=datetime.combine(
            anchor,
            datetime.min.time(),
            tzinfo=resolve_timezone(timezone_name),
        ),
        timezone_name=timezone_name,
    )


def envelope_plural_for_deprecated_caller(
    result: TemporalNormalizationResult,
) -> tuple[str, str] | None:
    """Explicit deprecated compatibility path; emits a warning instead of silent loss."""
    if not result.windows:
        return None
    logger.warning(
        "deprecated_temporal_plural_envelope relation=%s windows=%d version=%s",
        result.relation.value,
        len(result.windows),
        result.normalizer_version,
    )
    return (
        min(window.start for window in result.windows).isoformat(),
        max(window.end for window in result.windows).isoformat(),
    )
