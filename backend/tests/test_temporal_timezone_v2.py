from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from contracts.analytical_v2 import ExecutionReadiness
from services.temporal import (
    TemporalContext,
    TemporalContextSource,
    TemporalNormalizer,
    build_temporal_context,
)
from services.temporal.timezone_support import InvalidTemporalTimezone


pytestmark = [pytest.mark.unit, pytest.mark.no_database]


def test_sao_paulo_and_utc_can_resolve_different_calendar_days() -> None:
    reference = datetime(2026, 7, 28, 1, 30, tzinfo=timezone.utc)
    sao_paulo = TemporalNormalizer().normalize(
        "hoje",
        TemporalContext(
            timezone="America/Sao_Paulo",
            reference_datetime=reference,
        ),
    )
    utc = TemporalNormalizer().normalize(
        "hoje",
        TemporalContext(timezone="UTC", reference_datetime=reference),
    )
    assert sao_paulo.windows[0].start == date(2026, 7, 27)
    assert utc.windows[0].start == date(2026, 7, 28)


def test_invalid_timezone_produces_typed_clarification() -> None:
    result = TemporalNormalizer().normalize(
        "hoje",
        TemporalContext(
            timezone="Invalid/Nowhere",
            reference_datetime=datetime(2026, 7, 27, 12, tzinfo=timezone.utc),
        ),
    )
    assert result.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED
    assert result.clarification is not None
    assert result.clarification.missing_fields == ["timezone"]


def test_naive_reference_datetime_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        TemporalContext(reference_datetime=datetime(2026, 7, 27, 12))


def test_tenant_timezone_precedes_application_and_server_timezone() -> None:
    context = build_temporal_context(
        reference_datetime=datetime(2026, 7, 27, 12, tzinfo=timezone.utc),
        tenant_timezone="America/Sao_Paulo",
        application_timezone="UTC",
    )
    assert context.timezone == "America/Sao_Paulo"
    assert context.source == TemporalContextSource.TENANT_CONFIGURATION


def test_authorized_request_and_user_preference_precedence() -> None:
    authorized = build_temporal_context(
        reference_datetime=datetime(2026, 7, 27, 12, tzinfo=timezone.utc),
        explicit_authorized_timezone="UTC",
        user_preference_timezone="America/Sao_Paulo",
    )
    user = build_temporal_context(
        reference_datetime=datetime(2026, 7, 27, 12, tzinfo=timezone.utc),
        user_preference_timezone="UTC",
        tenant_timezone="America/Sao_Paulo",
    )
    assert authorized.timezone == "UTC"
    assert authorized.source == TemporalContextSource.REQUEST_AUTHORIZED
    assert user.timezone == "UTC"
    assert user.source == TemporalContextSource.USER_PREFERENCE


def test_context_builder_rejects_invalid_controlled_timezone() -> None:
    with pytest.raises(InvalidTemporalTimezone):
        build_temporal_context(
            reference_datetime=datetime(2026, 7, 27, 12, tzinfo=timezone.utc),
            tenant_timezone="Invalid/Nowhere",
        )


def test_week_start_is_configurable() -> None:
    reference = datetime(
        2026,
        7,
        27,
        12,
        tzinfo=timezone(timedelta(hours=-3)),
    )
    monday = TemporalNormalizer().normalize(
        "semana atual",
        TemporalContext(reference_datetime=reference, week_start=0),
    )
    sunday = TemporalNormalizer().normalize(
        "semana atual",
        TemporalContext(reference_datetime=reference, week_start=6),
    )
    assert monday.windows[0].start == date(2026, 7, 27)
    assert sunday.windows[0].start == date(2026, 7, 26)
