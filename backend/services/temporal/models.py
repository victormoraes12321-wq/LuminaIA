from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from contracts.analytical_v2 import (
    ClarificationRequest,
    ConfidenceAssessment,
    ExecutionReadiness,
    FieldOrigin,
    TimeWindow,
)


TEMPORAL_NORMALIZER_VERSION = "lumina.temporal.pt-BR/1.0"


class CurrentPeriodMode(str, Enum):
    TO_DATE = "TO_DATE"
    FULL_PERIOD = "FULL_PERIOD"


class DefaultYearPolicy(str, Enum):
    CURRENT_YEAR = "CURRENT_YEAR"
    MOST_RECENT_OCCURRENCE = "MOST_RECENT_OCCURRENCE"
    REQUIRE_CLARIFICATION = "REQUIRE_CLARIFICATION"


class TwoDigitYearPolicy(str, Enum):
    REJECT = "REJECT"
    CURRENT_CENTURY = "CURRENT_CENTURY"
    PIVOT_YEAR = "PIVOT_YEAR"


class FiscalYearLabelMode(str, Enum):
    STARTING_YEAR = "STARTING_YEAR"
    ENDING_YEAR = "ENDING_YEAR"


class TemporalRelation(str, Enum):
    SINGLE = "SINGLE"
    RANGE = "RANGE"
    PERIOD_LIST = "PERIOD_LIST"
    COMPARISON = "COMPARISON"
    NONE = "NONE"


class TemporalSemanticType(str, Enum):
    ABSOLUTE_DATE = "ABSOLUTE_DATE"
    MONTH = "MONTH"
    YEAR = "YEAR"
    QUARTER = "QUARTER"
    SEMESTER = "SEMESTER"
    WEEK = "WEEK"
    FORTNIGHT = "FORTNIGHT"
    DATE_RANGE = "DATE_RANGE"
    PERIOD_LIST = "PERIOD_LIST"
    RELATIVE_PERIOD = "RELATIVE_PERIOD"
    ROLLING_WINDOW = "ROLLING_WINDOW"
    COMPARISON_TEMPORAL = "COMPARISON_TEMPORAL"
    FISCAL_PERIOD = "FISCAL_PERIOD"
    ACCUMULATED_PERIOD = "ACCUMULATED_PERIOD"


class TemporalContextSource(str, Enum):
    REQUEST_AUTHORIZED = "REQUEST_AUTHORIZED"
    USER_PREFERENCE = "USER_PREFERENCE"
    TENANT_CONFIGURATION = "TENANT_CONFIGURATION"
    APPLICATION_CONFIGURATION = "APPLICATION_CONFIGURATION"
    DOCUMENTED_FALLBACK = "DOCUMENTED_FALLBACK"
    TEST = "TEST"


class TemporalLexiconProvider(Protocol):
    def aliases(self) -> dict[str, str]:
        """Return approved aliases. Values are canonical temporal tokens."""


class StrictTemporalModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        str_strip_whitespace=True,
    )


class TemporalContext(StrictTemporalModel):
    locale: str = "pt-BR"
    timezone: str = "America/Sao_Paulo"
    reference_datetime: datetime
    week_start: int = Field(default=0, ge=0, le=6)
    fiscal_year_start_month: int | None = Field(default=1, ge=1, le=12)
    fiscal_year_label_mode: FiscalYearLabelMode | None = None
    current_period_mode: CurrentPeriodMode = CurrentPeriodMode.FULL_PERIOD
    two_digit_year_policy: TwoDigitYearPolicy = TwoDigitYearPolicy.REJECT
    two_digit_year_pivot: int = Field(default=69, ge=0, le=99)
    default_year_policy: DefaultYearPolicy = DefaultYearPolicy.CURRENT_YEAR
    allow_future_periods: bool = False
    tenant_id: UUID | None = None
    user_id: UUID | None = None
    source: TemporalContextSource = TemporalContextSource.DOCUMENTED_FALLBACK
    origin: FieldOrigin = FieldOrigin.EXPLICIT_USER
    base_time_windows: tuple[TimeWindow, ...] = ()

    @model_validator(mode="after")
    def validate_context(self) -> "TemporalContext":
        if self.locale != "pt-BR":
            raise ValueError("TemporalContext currently supports locale pt-BR only")
        if self.reference_datetime.tzinfo is None or self.reference_datetime.utcoffset() is None:
            raise ValueError("reference_datetime must be timezone-aware")
        if (
            self.fiscal_year_start_month not in (None, 1)
            and self.fiscal_year_label_mode is None
        ):
            raise ValueError(
                "fiscal_year_label_mode is required when the fiscal year does not start in January"
            )
        return self


class TemporalTextSpan(StrictTemporalModel):
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    original: str = Field(min_length=1, max_length=256)
    normalized: str = Field(min_length=1, max_length=256)
    rule_id: str = Field(min_length=1, max_length=100)
    confidence: ConfidenceAssessment

    @model_validator(mode="after")
    def validate_span(self) -> "TemporalTextSpan":
        if self.end <= self.start:
            raise ValueError("TemporalTextSpan end must be greater than start")
        return self


class ResolvedTemporalItem(StrictTemporalModel):
    item_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_.:-]*$")
    window: TimeWindow
    semantic_type: TemporalSemanticType
    source_text: str = Field(min_length=1, max_length=256)
    rule_id: str = Field(min_length=1, max_length=100)
    confidence: ConfidenceAssessment
    warnings: tuple[str, ...] = ()
    partial: bool = False
    open_ended: bool = False
    inferred: bool = False
    requires_confirmation: bool = False


class TemporalComparisonGroup(StrictTemporalModel):
    group_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_.:-]*$")
    operand_item_ids: tuple[str, ...] = Field(min_length=2)


class TemporalNormalizationResult(StrictTemporalModel):
    windows: tuple[TimeWindow, ...] = ()
    range: ResolvedTemporalItem | None = None
    period_list: tuple[ResolvedTemporalItem, ...] = ()
    comparison_groups: tuple[TemporalComparisonGroup, ...] = ()
    items: tuple[ResolvedTemporalItem, ...] = ()
    relation: TemporalRelation = TemporalRelation.NONE
    consumed_spans: tuple[TemporalTextSpan, ...] = ()
    unresolved_expressions: tuple[str, ...] = ()
    confidence: ConfidenceAssessment
    readiness: ExecutionReadiness
    clarification: ClarificationRequest | None = None
    warnings: tuple[str, ...] = ()
    rule_ids: tuple[str, ...] = ()
    normalizer_version: str = TEMPORAL_NORMALIZER_VERSION
    reference_datetime: datetime
    timezone: str
    calendar_kind: str = "CIVIL"
    duration_ms: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_result(self) -> "TemporalNormalizationResult":
        ids = [window.window_id for window in self.windows]
        if len(ids) != len(set(ids)):
            raise ValueError("Temporal normalization cannot contain duplicate TimeWindow IDs")
        if (
            self.readiness == ExecutionReadiness.CLARIFICATION_REQUIRED
            and self.clarification is None
        ):
            raise ValueError("Temporal clarification readiness requires a clarification")
        if self.clarification is not None and self.readiness != ExecutionReadiness.CLARIFICATION_REQUIRED:
            raise ValueError("Temporal clarification is only valid when clarification is required")
        return self
