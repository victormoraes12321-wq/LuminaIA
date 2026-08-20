from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict


class AnalyticalFactState(str, Enum):
    VALUE = "VALUE"
    ZERO = "ZERO"
    NULL = "NULL"
    NO_ROWS = "NO_ROWS"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNSUPPORTED = "UNSUPPORTED"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"
    PARTIAL = "PARTIAL"


class NumericalFact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: AnalyticalFactState
    value: Decimal | None = None


def aggregate_fact(
    value: Decimal | None,
    *,
    source_row_count: int,
    empty_is_zero: bool = False,
) -> NumericalFact:
    if source_row_count < 0:
        raise ValueError("source_row_count cannot be negative")
    if source_row_count == 0:
        if empty_is_zero:
            return NumericalFact(state=AnalyticalFactState.ZERO, value=Decimal("0"))
        return NumericalFact(state=AnalyticalFactState.NO_ROWS)
    if value is None:
        return NumericalFact(state=AnalyticalFactState.NULL)
    if value == 0:
        return NumericalFact(state=AnalyticalFactState.ZERO, value=value)
    return NumericalFact(state=AnalyticalFactState.VALUE, value=value)


def ratio_fact(
    numerator: Decimal | None,
    denominator: int | Decimal | None,
    *,
    source_row_count: int,
) -> NumericalFact:
    if source_row_count < 0:
        raise ValueError("source_row_count cannot be negative")
    if source_row_count == 0:
        return NumericalFact(state=AnalyticalFactState.NO_ROWS)
    if numerator is None:
        return NumericalFact(state=AnalyticalFactState.NULL)
    if denominator in (None, 0, Decimal("0")):
        return NumericalFact(state=AnalyticalFactState.NOT_APPLICABLE)
    value = numerator / Decimal(denominator)
    return NumericalFact(
        state=AnalyticalFactState.ZERO if value == 0 else AnalyticalFactState.VALUE,
        value=value,
    )


def unavailable_fact(state: AnalyticalFactState) -> NumericalFact:
    if state not in {
        AnalyticalFactState.UNSUPPORTED,
        AnalyticalFactState.BLOCKED,
        AnalyticalFactState.ERROR,
        AnalyticalFactState.PARTIAL,
    }:
        raise ValueError("unavailable_fact requires a non-numerical availability state")
    return NumericalFact(state=state)
