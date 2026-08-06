"""Declarative formatting, accessibility, states, and refresh intent."""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import Field, model_validator

from .identity import StrictDashboardModel


class DashboardThemeTokenV2(str, Enum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    WARNING = "WARNING"
    NEUTRAL = "NEUTRAL"
    INFO = "INFO"
    SERIES_1 = "SERIES_1"
    SERIES_2 = "SERIES_2"
    SERIES_3 = "SERIES_3"
    SERIES_4 = "SERIES_4"
    SERIES_5 = "SERIES_5"
    SERIES_6 = "SERIES_6"
    SERIES_7 = "SERIES_7"
    SERIES_8 = "SERIES_8"


class DashboardNumberFormattingV2(StrictDashboardModel):
    style: Literal["DECIMAL", "INTEGER", "COMPACT"] = "DECIMAL"
    minimum_fraction_digits: int = Field(default=0, ge=0, le=6)
    maximum_fraction_digits: int = Field(default=2, ge=0, le=6)
    negative_display: Literal["MINUS", "PARENTHESES"] = "MINUS"
    null_display: Literal["SEM_VALOR", "TRACO", "VAZIO"] = "SEM_VALOR"
    unit_visible: bool = True

    @model_validator(mode="after")
    def validate_fraction_digits(self) -> "DashboardNumberFormattingV2":
        if self.minimum_fraction_digits > self.maximum_fraction_digits:
            raise ValueError("minimum fraction digits cannot exceed maximum")
        return self


class DashboardCurrencyFormattingV2(StrictDashboardModel):
    currency_code: Literal["BRL", "USD", "EUR"]
    display: Literal["SYMBOL", "CODE", "NAME"] = "SYMBOL"
    decimal_places: int = Field(default=2, ge=0, le=4)


class DashboardDateFormattingV2(StrictDashboardModel):
    format: Literal["DATE_SHORT", "DATE_LONG", "MONTH_YEAR", "YEAR", "DATETIME"]
    timezone_policy: Literal["DASHBOARD", "TENANT", "USER"] = "DASHBOARD"


class DashboardFormattingV2(StrictDashboardModel):
    locale: Literal["pt-BR"] = "pt-BR"
    number: DashboardNumberFormattingV2 = Field(
        default_factory=DashboardNumberFormattingV2
    )
    currency: DashboardCurrencyFormattingV2 | None = None
    date: DashboardDateFormattingV2 | None = None
    percentage_display: Literal["ALREADY_PERCENT", "RATIO_TO_PERCENT"] | None = None
    theme_token: DashboardThemeTokenV2 = DashboardThemeTokenV2.PRIMARY


class DashboardEmptyStateV2(StrictDashboardModel):
    title: str = Field(min_length=2, max_length=120)
    message: str = Field(min_length=4, max_length=320)
    action: Literal["NONE", "RESET_FILTERS", "CHANGE_PERIOD"] = "NONE"


class DashboardErrorStateV2(StrictDashboardModel):
    title: str = Field(min_length=2, max_length=120)
    message: str = Field(min_length=4, max_length=320)
    expose_diagnostics: bool = False
    action: Literal["NONE", "RETRY", "OPEN_PROVENANCE"] = "NONE"


class DashboardLoadingStateV2(StrictDashboardModel):
    label: str = Field(min_length=2, max_length=120)
    presentation: Literal["SKELETON", "PROGRESS", "TEXT"] = "SKELETON"
    announce_to_screen_reader: bool = True


class DashboardWidgetStatesV2(StrictDashboardModel):
    loading: DashboardLoadingStateV2
    empty: DashboardEmptyStateV2
    partial_message: str = Field(min_length=4, max_length=320)
    stale_message: str = Field(min_length=4, max_length=320)
    truncated_message: str = Field(min_length=4, max_length=320)
    error: DashboardErrorStateV2
    permission_denied_message: str = Field(min_length=4, max_length=320)
    unavailable_message: str = Field(min_length=4, max_length=320)


class DashboardWidgetAccessibilityV2(StrictDashboardModel):
    accessible_name: str = Field(min_length=2, max_length=160)
    accessible_description: str = Field(min_length=8, max_length=500)
    summary_template: str = Field(min_length=8, max_length=500)
    table_alternative_required: bool = False
    chart_text_summary_required: bool = False
    focus_behavior: Literal["CONTAINER", "FIRST_CONTROL", "NOT_FOCUSABLE"] = "CONTAINER"


class DashboardAccessibilityV2(StrictDashboardModel):
    accessible_title: str = Field(min_length=2, max_length=160)
    accessible_description: str = Field(min_length=8, max_length=800)
    reading_order: tuple[str, ...] = Field(min_length=1, max_length=64)
    landmark_strategy: Literal["SINGLE_MAIN", "SECTIONS_WITH_LABELS"]
    keyboard_navigation: Literal["DOCUMENT_ORDER", "GRID_WITH_DOCUMENT_FALLBACK"]
    reduced_motion: Literal["RESPECT_SYSTEM", "ALWAYS_REDUCED"] = "RESPECT_SYSTEM"
    screen_reader_summary: str = Field(min_length=8, max_length=800)
    textual_fallback_required: bool = True
    color_independent_status: bool = True


class DashboardRefreshPolicyV2(str, Enum):
    MANUAL = "MANUAL"
    ON_OPEN = "ON_OPEN"
    AFTER_SYNC = "AFTER_SYNC"
    SOURCE_WATERMARK = "SOURCE_WATERMARK"
    INTERVAL_POLICY = "INTERVAL_POLICY"
    DISABLED = "DISABLED"


class DashboardCachePreferenceV2(str, Enum):
    CACHE_PREFERRED = "CACHE_PREFERRED"
    CACHE_BYPASS_PROHIBITED = "CACHE_BYPASS_PROHIBITED"
    BACKEND_DECIDES = "BACKEND_DECIDES"


class DashboardMaterializationPreferenceV2(str, Enum):
    MATERIALIZATION_PREFERRED = "MATERIALIZATION_PREFERRED"
    MATERIALIZATION_REQUIRED = "MATERIALIZATION_REQUIRED"
    LIVE_QUERY_REQUIRED = "LIVE_QUERY_REQUIRED"
    BACKEND_DECIDES = "BACKEND_DECIDES"


class DashboardProvenanceRequirementV2(StrictDashboardModel):
    public_summary_required: bool = True
    source_freshness_required: bool = True
    applied_filters_required: bool = True
    metric_definition_required: bool = True
    cache_indicator_required: bool = True
    validation_status_required: bool = True
    warnings_required: bool = True

