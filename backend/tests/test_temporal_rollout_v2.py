from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from services.temporal import (
    TemporalContext,
    TemporalFeaturePolicy,
    TemporalNormalizationGateway,
)


pytestmark = [pytest.mark.unit, pytest.mark.no_database]
CONTEXT = TemporalContext(
    reference_datetime=datetime(
        2026,
        7,
        27,
        12,
        tzinfo=timezone(timedelta(hours=-3)),
    )
)


def _legacy_first_month(_: str) -> tuple[str, str]:
    return "2026-06-01", "2026-06-30"


def test_disabled_flag_preserves_legacy_selection() -> None:
    gateway = TemporalNormalizationGateway(
        policy=TemporalFeaturePolicy(enabled=False, shadow_mode=True)
    )
    result, selected = gateway.select_ranges(
        "06/2026 versus 07/2026",
        CONTEXT,
        legacy_parser=_legacy_first_month,
    )
    assert len(result.windows) == 2
    assert selected == [("2026-06-01", "2026-06-30")]


def test_enabled_flag_selects_all_canonical_windows() -> None:
    gateway = TemporalNormalizationGateway(
        policy=TemporalFeaturePolicy(enabled=True, shadow_mode=False)
    )
    _, selected = gateway.select_ranges(
        "06/2026 versus 07/2026",
        CONTEXT,
        legacy_parser=_legacy_first_month,
    )
    assert selected == [
        ("2026-06-01", "2026-06-30"),
        ("2026-07-01", "2026-07-31"),
    ]


def test_shadow_mode_logs_only_fingerprint_and_structural_difference(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO", logger="luminaai.services.temporal.rollout")
    gateway = TemporalNormalizationGateway(
        policy=TemporalFeaturePolicy(enabled=False, shadow_mode=True)
    )
    query = "06/2026 versus 07/2026"
    gateway.normalize(query, CONTEXT, legacy_parser=_legacy_first_month)
    assert "temporal_shadow_divergence" in caplog.text
    assert query not in caplog.text
