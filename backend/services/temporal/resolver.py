from __future__ import annotations

import calendar
from datetime import date, timedelta

from contracts.analytical_v2 import TemporalGranularity

from .lexicon_pt_br import MONTH_LABELS
from .models import (
    CurrentPeriodMode,
    DefaultYearPolicy,
    FiscalYearLabelMode,
    TemporalContext,
    TemporalSemanticType,
    TwoDigitYearPolicy,
)
from .parser import ParsedTemporalExpression
from .timezone_support import resolve_timezone


class TemporalResolutionError(ValueError):
    pass


class TemporalAmbiguityError(TemporalResolutionError):
    def __init__(self, message: str, *, candidates: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.candidates = candidates


class FutureTemporalPeriodError(TemporalResolutionError):
    pass


def resolve_expression(
    expression: ParsedTemporalExpression,
    context: TemporalContext,
) -> tuple[date, date, str, TemporalGranularity, bool, tuple[str, ...]]:
    values = expression.values
    semantic_type = expression.semantic_type
    reference = context.reference_datetime.astimezone(resolve_timezone(context.timezone)).date()
    warnings: list[str] = []
    partial = False

    if semantic_type == TemporalSemanticType.ABSOLUTE_DATE:
        try:
            resolved = date(values["year"], values["month"], values["day"])
        except ValueError as exc:
            raise TemporalResolutionError("Data civil invalida.") from exc
        start, end, label, granularity = resolved, resolved, resolved.strftime("%d/%m/%Y"), TemporalGranularity.DAY
    elif semantic_type == TemporalSemanticType.MONTH:
        year = _resolve_year(values.get("year"), values.get("two_digit_year", False), values["month"], context, warnings)
        start = date(year, values["month"], 1)
        end = _month_end(year, values["month"])
        label = f"{MONTH_LABELS[values['month']]} {year}"
        granularity = TemporalGranularity.MONTH
    elif semantic_type == TemporalSemanticType.YEAR:
        year = values["year"]
        start, end = date(year, 1, 1), date(year, 12, 31)
        label, granularity = str(year), TemporalGranularity.YEAR
    elif semantic_type == TemporalSemanticType.QUARTER:
        quarter = values["quarter"]
        year = _resolve_year(values.get("year"), False, (quarter - 1) * 3 + 1, context, warnings)
        start_month = (quarter - 1) * 3 + 1
        start, end = date(year, start_month, 1), _month_end(year, start_month + 2)
        label, granularity = f"T{quarter} {year}", TemporalGranularity.QUARTER
    elif semantic_type == TemporalSemanticType.SEMESTER:
        semester = values["semester"]
        year = _resolve_year(values.get("year"), False, 1 if semester == 1 else 7, context, warnings)
        start_month = 1 if semester == 1 else 7
        start, end = date(year, start_month, 1), _month_end(year, start_month + 5)
        label, granularity = f"S{semester} {year}", TemporalGranularity.SEMESTER
    elif semantic_type == TemporalSemanticType.WEEK:
        try:
            start = date.fromisocalendar(values["year"], values["iso_week"], 1)
            end = date.fromisocalendar(values["year"], values["iso_week"], 7)
        except ValueError as exc:
            raise TemporalResolutionError("Semana ISO invalida para o ano informado.") from exc
        label, granularity = f"Semana ISO {values['iso_week']} de {values['year']}", TemporalGranularity.WEEK
    elif semantic_type == TemporalSemanticType.FORTNIGHT:
        month = int(values.get("month") or reference.month)
        year = _resolve_year(values.get("year"), False, month, context, warnings)
        if values["fortnight"] == 1:
            start, end = date(year, month, 1), date(year, month, 15)
        else:
            start, end = date(year, month, 16), _month_end(year, month)
        label = f"{values['fortnight']}a quinzena de {MONTH_LABELS[month]} {year}"
        granularity = TemporalGranularity.CUSTOM
    elif semantic_type == TemporalSemanticType.RELATIVE_PERIOD:
        start, end, label, granularity = _resolve_relative(values["relative"], reference, context)
    elif semantic_type == TemporalSemanticType.ROLLING_WINDOW:
        start, end, label, granularity, partial = _resolve_rolling(values, reference)
    elif semantic_type == TemporalSemanticType.ACCUMULATED_PERIOD:
        start, end, label, granularity = _resolve_accumulation(values["accumulation"], reference)
        partial = True
    elif semantic_type == TemporalSemanticType.FISCAL_PERIOD:
        start, end, label, granularity = _resolve_fiscal(values, reference, context)
    else:
        raise TemporalResolutionError(f"Tipo temporal nao resolvivel: {semantic_type.value}")

    if context.current_period_mode == CurrentPeriodMode.TO_DATE and start <= reference <= end:
        end = reference
        partial = True
        warnings.append("Periodo corrente limitado ate a data de referencia por politica TO_DATE.")
    if end > reference and not context.allow_future_periods:
        is_future_relative = (
            semantic_type == TemporalSemanticType.RELATIVE_PERIOD
            and values.get("relative") == "TOMORROW"
        )
        is_future_rolling = (
            semantic_type == TemporalSemanticType.ROLLING_WINDOW
            and values.get("direction") == "FUTURE"
        )
        if is_future_relative or is_future_rolling:
            raise FutureTemporalPeriodError("Periodos futuros nao estao autorizados neste contexto.")
    return start, end, label, granularity, partial, tuple(warnings)


def _resolve_year(
    raw_year: int | None,
    two_digit: bool,
    month: int,
    context: TemporalContext,
    warnings: list[str],
) -> int:
    reference = context.reference_datetime.astimezone(resolve_timezone(context.timezone)).date()
    if raw_year is not None and not two_digit:
        return raw_year
    if raw_year is not None and two_digit:
        if context.two_digit_year_policy == TwoDigitYearPolicy.REJECT:
            raise TemporalAmbiguityError(
                "Ano com dois digitos exige confirmacao.",
                candidates=(f"20{raw_year:02d}", f"19{raw_year:02d}"),
            )
        warnings.append("Ano de dois digitos resolvido por politica explicita.")
        if context.two_digit_year_policy == TwoDigitYearPolicy.CURRENT_CENTURY:
            return (reference.year // 100) * 100 + raw_year
        return 1900 + raw_year if raw_year >= context.two_digit_year_pivot else 2000 + raw_year
    if context.default_year_policy == DefaultYearPolicy.REQUIRE_CLARIFICATION:
        raise TemporalAmbiguityError(
            "O mes foi informado sem ano.",
            candidates=(str(reference.year), str(reference.year - 1)),
        )
    warnings.append("Ano inferido por politica temporal explicita.")
    if context.default_year_policy == DefaultYearPolicy.MOST_RECENT_OCCURRENCE and month > reference.month:
        return reference.year - 1
    return reference.year


def _resolve_relative(
    relative: str,
    reference: date,
    context: TemporalContext,
) -> tuple[date, date, str, TemporalGranularity]:
    if relative == "TODAY":
        return reference, reference, "Hoje", TemporalGranularity.DAY
    if relative == "YESTERDAY":
        day = reference - timedelta(days=1)
        return day, day, "Ontem", TemporalGranularity.DAY
    if relative == "DAY_BEFORE_YESTERDAY":
        day = reference - timedelta(days=2)
        return day, day, "Anteontem", TemporalGranularity.DAY
    if relative == "TOMORROW":
        day = reference + timedelta(days=1)
        return day, day, "Amanha", TemporalGranularity.DAY
    if relative in {"CURRENT_WEEK", "PREVIOUS_WEEK"}:
        start = reference - timedelta(days=(reference.weekday() - context.week_start) % 7)
        if relative == "PREVIOUS_WEEK":
            start -= timedelta(days=7)
        return start, start + timedelta(days=6), "Semana atual" if relative == "CURRENT_WEEK" else "Semana anterior", TemporalGranularity.WEEK
    if relative in {"CURRENT_MONTH", "PREVIOUS_MONTH"}:
        target = reference if relative == "CURRENT_MONTH" else _shift_month(reference.replace(day=1), -1)
        start = date(target.year, target.month, 1)
        return start, _month_end(target.year, target.month), "Mes atual" if relative == "CURRENT_MONTH" else "Mes anterior", TemporalGranularity.MONTH
    if relative in {"CURRENT_QUARTER", "PREVIOUS_QUARTER"}:
        quarter = (reference.month - 1) // 3 + 1
        year = reference.year
        if relative == "PREVIOUS_QUARTER":
            quarter -= 1
            if quarter == 0:
                quarter, year = 4, year - 1
        month = (quarter - 1) * 3 + 1
        return date(year, month, 1), _month_end(year, month + 2), f"T{quarter} {year}", TemporalGranularity.QUARTER
    if relative in {"CURRENT_SEMESTER", "PREVIOUS_SEMESTER"}:
        semester = 1 if reference.month <= 6 else 2
        year = reference.year
        if relative == "PREVIOUS_SEMESTER":
            if semester == 1:
                semester, year = 2, year - 1
            else:
                semester = 1
        month = 1 if semester == 1 else 7
        return date(year, month, 1), _month_end(year, month + 5), f"S{semester} {year}", TemporalGranularity.SEMESTER
    if relative in {"CURRENT_YEAR", "PREVIOUS_YEAR"}:
        year = reference.year if relative == "CURRENT_YEAR" else reference.year - 1
        return date(year, 1, 1), date(year, 12, 31), str(year), TemporalGranularity.YEAR
    raise TemporalResolutionError(f"Periodo relativo desconhecido: {relative}")


def _resolve_rolling(
    values: dict[str, object],
    reference: date,
) -> tuple[date, date, str, TemporalGranularity, bool]:
    amount = int(values["amount"])
    unit = str(values["unit"])
    future = values["direction"] == "FUTURE"
    closed = bool(values["closed"])
    if bool(values.get("previous_equivalent")) and unit.startswith("dia"):
        current_start = reference - timedelta(days=max(amount - 1, 0))
        end = current_start - timedelta(days=1)
        start = end - timedelta(days=max(amount - 1, 0))
        return start, end, f"{amount} dias anteriores equivalentes", TemporalGranularity.DAY, False
    if closed:
        if unit.startswith("mes"):
            end = reference.replace(day=1) - timedelta(days=1)
            start = _shift_month(end.replace(day=1), -(amount - 1))
            return start, end, f"Ultimos {amount} meses fechados", TemporalGranularity.MONTH, False
        if unit.startswith("semana"):
            current_week_start = reference - timedelta(days=reference.weekday())
            end = current_week_start - timedelta(days=1)
            start = end - timedelta(days=(amount * 7) - 1)
            return start, end, f"Ultimas {amount} semanas completas", TemporalGranularity.WEEK, False
    if unit.startswith("dia"):
        delta = timedelta(days=max(amount - 1, 0))
        granularity = TemporalGranularity.DAY
    elif unit.startswith("semana"):
        delta = timedelta(days=max(amount * 7 - 1, 0))
        granularity = TemporalGranularity.WEEK
    elif unit.startswith("mes"):
        if future:
            start, end = reference, _shift_month_clamped(reference, amount)
        else:
            start, end = _shift_month_clamped(reference, -amount) + timedelta(days=1), reference
        return start, end, f"{'Proximos' if future else 'Ultimos'} {amount} meses", TemporalGranularity.CUSTOM, True
    else:
        if future:
            start, end = reference, date(reference.year + amount, reference.month, min(reference.day, calendar.monthrange(reference.year + amount, reference.month)[1]))
        else:
            start, end = date(reference.year - amount, reference.month, min(reference.day, calendar.monthrange(reference.year - amount, reference.month)[1])) + timedelta(days=1), reference
        return start, end, f"{'Proximos' if future else 'Ultimos'} {amount} anos", TemporalGranularity.CUSTOM, True
    return (
        (reference, reference + delta, f"Proximos {amount} {unit}", granularity, True)
        if future
        else (reference - delta, reference, f"Ultimos {amount} {unit}", granularity, True)
    )


def _resolve_accumulation(
    accumulation: str,
    reference: date,
) -> tuple[date, date, str, TemporalGranularity]:
    if accumulation == "MONTH_TO_DATE":
        return reference.replace(day=1), reference, "MTD", TemporalGranularity.MONTH
    if accumulation == "YEAR_TO_DATE":
        return date(reference.year, 1, 1), reference, "YTD", TemporalGranularity.YEAR
    if accumulation == "QUARTER_TO_DATE":
        month = ((reference.month - 1) // 3) * 3 + 1
        return date(reference.year, month, 1), reference, "QTD", TemporalGranularity.QUARTER
    month = 1 if reference.month <= 6 else 7
    return date(reference.year, month, 1), reference, "Semestre ate hoje", TemporalGranularity.SEMESTER


def _resolve_fiscal(
    values: dict[str, object],
    reference: date,
    context: TemporalContext,
) -> tuple[date, date, str, TemporalGranularity]:
    start_month = context.fiscal_year_start_month
    if start_month is None:
        raise TemporalAmbiguityError("Calendario fiscal nao configurado.")
    if start_month != 1 and context.fiscal_year_label_mode is None:
        raise TemporalAmbiguityError("Modo de rotulagem do ano fiscal nao configurado.")
    relative = str(values.get("relative") or "")
    current_start_year = (
        reference.year
        if reference.month >= start_month
        else reference.year - 1
    )
    if relative:
        fiscal_start_year = current_start_year
        month_distance = (reference.year - fiscal_start_year) * 12 + reference.month - start_month
        quarter = month_distance // 3 + 1
        if relative == "PREVIOUS_FISCAL_YEAR":
            fiscal_start_year -= 1
        elif relative == "PREVIOUS_FISCAL_QUARTER":
            quarter -= 1
            if quarter == 0:
                quarter = 4
                fiscal_start_year -= 1
        label_year = (
            fiscal_start_year
            if start_month == 1 or context.fiscal_year_label_mode == FiscalYearLabelMode.STARTING_YEAR
            else fiscal_start_year + 1
        )
        if "QUARTER" in relative:
            values = dict(values)
            values["quarter"] = quarter
        start_year = fiscal_start_year
    else:
        label_year = int(values.get("year") or reference.year)
        if start_month == 1 or context.fiscal_year_label_mode == FiscalYearLabelMode.STARTING_YEAR:
            start_year = label_year
        else:
            start_year = label_year - 1
    fiscal_start = date(start_year, start_month, 1)
    if "quarter" in values:
        quarter = int(values["quarter"])
        start = _shift_month(fiscal_start, (quarter - 1) * 3)
        end = _shift_month(start, 3) - timedelta(days=1)
        return start, end, f"T{quarter} fiscal {label_year}", TemporalGranularity.QUARTER
    end = _shift_month(fiscal_start, 12) - timedelta(days=1)
    return fiscal_start, end, f"FY{label_year}", TemporalGranularity.YEAR


def _month_end(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def _shift_month(value: date, offset: int) -> date:
    index = value.year * 12 + (value.month - 1) + offset
    year, month_index = divmod(index, 12)
    return date(year, month_index + 1, 1)


def _shift_month_clamped(value: date, offset: int) -> date:
    shifted = _shift_month(value.replace(day=1), offset)
    return shifted.replace(day=min(value.day, calendar.monthrange(shifted.year, shifted.month)[1]))
