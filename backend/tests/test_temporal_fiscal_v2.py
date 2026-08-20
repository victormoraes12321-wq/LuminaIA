from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from contracts.analytical_v2 import ExecutionReadiness
from services.temporal import (
    FiscalYearLabelMode,
    TemporalContext,
    TemporalNormalizer,
)


pytestmark = [pytest.mark.unit, pytest.mark.no_database]
REFERENCE = datetime(2026, 7, 27, 12, tzinfo=timezone(timedelta(hours=-3)))


def fiscal_context(
    start_month: int | None,
    label_mode: FiscalYearLabelMode | None,
) -> TemporalContext:
    return TemporalContext(
        reference_datetime=REFERENCE,
        fiscal_year_start_month=start_month,
        fiscal_year_label_mode=label_mode,
    )


def test_starting_year_fiscal_calendar() -> None:
    result = TemporalNormalizer().normalize(
        "ano fiscal de 2026",
        fiscal_context(7, FiscalYearLabelMode.STARTING_YEAR),
    )
    assert (result.windows[0].start, result.windows[0].end) == (
        date(2026, 7, 1),
        date(2027, 6, 30),
    )


def test_ending_year_fiscal_calendar() -> None:
    result = TemporalNormalizer().normalize(
        "FY2026",
        fiscal_context(7, FiscalYearLabelMode.ENDING_YEAR),
    )
    assert (result.windows[0].start, result.windows[0].end) == (
        date(2025, 7, 1),
        date(2026, 6, 30),
    )


def test_fiscal_quarter_uses_configured_start_month() -> None:
    result = TemporalNormalizer().normalize(
        "Q1 fiscal de 2026",
        fiscal_context(7, FiscalYearLabelMode.STARTING_YEAR),
    )
    assert (result.windows[0].start, result.windows[0].end) == (
        date(2026, 7, 1),
        date(2026, 9, 30),
    )


def test_current_and_previous_fiscal_periods() -> None:
    context = fiscal_context(4, FiscalYearLabelMode.STARTING_YEAR)
    current = TemporalNormalizer().normalize("trimestre fiscal atual", context)
    previous = TemporalNormalizer().normalize("ano fiscal anterior", context)
    assert (current.windows[0].start, current.windows[0].end) == (
        date(2026, 7, 1),
        date(2026, 9, 30),
    )
    assert (previous.windows[0].start, previous.windows[0].end) == (
        date(2025, 4, 1),
        date(2026, 3, 31),
    )


def test_missing_fiscal_configuration_requires_clarification() -> None:
    result = TemporalNormalizer().normalize(
        "FY2026",
        fiscal_context(None, None),
    )
    assert result.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED


def test_non_january_fiscal_calendar_requires_label_mode() -> None:
    with pytest.raises(ValueError, match="label_mode"):
        fiscal_context(7, None)


def test_civil_fiscal_calendar_needs_no_label_mode() -> None:
    result = TemporalNormalizer().normalize(
        "ano fiscal de 2026",
        fiscal_context(1, None),
    )
    assert (result.windows[0].start, result.windows[0].end) == (
        date(2026, 1, 1),
        date(2026, 12, 31),
    )
