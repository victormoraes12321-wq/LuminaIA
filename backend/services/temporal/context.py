from __future__ import annotations

from datetime import datetime
from uuid import UUID

from contracts.analytical_v2 import FieldOrigin, TimeWindow

from .models import (
    CurrentPeriodMode,
    DefaultYearPolicy,
    FiscalYearLabelMode,
    TemporalContext,
    TemporalContextSource,
    TwoDigitYearPolicy,
)
from .timezone_support import resolve_timezone


def build_temporal_context(
    *,
    reference_datetime: datetime,
    explicit_authorized_timezone: str | None = None,
    user_preference_timezone: str | None = None,
    tenant_timezone: str | None = None,
    application_timezone: str | None = None,
    fallback_timezone: str = "America/Sao_Paulo",
    week_start: int = 0,
    fiscal_year_start_month: int | None = 1,
    fiscal_year_label_mode: FiscalYearLabelMode | None = None,
    current_period_mode: CurrentPeriodMode = CurrentPeriodMode.FULL_PERIOD,
    two_digit_year_policy: TwoDigitYearPolicy = TwoDigitYearPolicy.REJECT,
    default_year_policy: DefaultYearPolicy = DefaultYearPolicy.CURRENT_YEAR,
    allow_future_periods: bool = False,
    tenant_id: UUID | None = None,
    user_id: UUID | None = None,
    origin: FieldOrigin = FieldOrigin.EXPLICIT_USER,
    base_time_windows: tuple[TimeWindow, ...] = (),
) -> TemporalContext:
    candidates = (
        (explicit_authorized_timezone, TemporalContextSource.REQUEST_AUTHORIZED),
        (user_preference_timezone, TemporalContextSource.USER_PREFERENCE),
        (tenant_timezone, TemporalContextSource.TENANT_CONFIGURATION),
        (application_timezone, TemporalContextSource.APPLICATION_CONFIGURATION),
        (fallback_timezone, TemporalContextSource.DOCUMENTED_FALLBACK),
    )
    timezone_name = fallback_timezone
    source = TemporalContextSource.DOCUMENTED_FALLBACK
    for candidate, candidate_source in candidates:
        if not candidate:
            continue
        resolve_timezone(candidate)
        timezone_name = candidate
        source = candidate_source
        break
    return TemporalContext(
        timezone=timezone_name,
        reference_datetime=reference_datetime,
        week_start=week_start,
        fiscal_year_start_month=fiscal_year_start_month,
        fiscal_year_label_mode=fiscal_year_label_mode,
        current_period_mode=current_period_mode,
        two_digit_year_policy=two_digit_year_policy,
        default_year_policy=default_year_policy,
        allow_future_periods=allow_future_periods,
        tenant_id=tenant_id,
        user_id=user_id,
        source=source,
        origin=origin,
        base_time_windows=base_time_windows,
    )
