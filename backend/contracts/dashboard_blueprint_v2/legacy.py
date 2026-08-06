"""Typed result of a pure legacy dashboard adaptation proposal."""
from __future__ import annotations

from enum import Enum

from pydantic import Field

from .blueprint import DashboardBlueprintV2
from .identity import StrictDashboardModel


class LegacyDashboardAdaptationStatusV2(str, Enum):
    COMPLETE = "COMPLETE"
    COMPLETE_WITH_WARNINGS = "COMPLETE_WITH_WARNINGS"
    PARTIAL = "PARTIAL"
    UNSUPPORTED = "UNSUPPORTED"
    BLOCKED = "BLOCKED"


class LegacyDashboardAdaptationResultV2(StrictDashboardModel):
    status: LegacyDashboardAdaptationStatusV2
    proposal: DashboardBlueprintV2 | None = None
    warnings: tuple[str, ...] = Field(default=(), max_length=64)
    unmapped_fields: tuple[str, ...] = Field(default=(), max_length=64)
    original_unchanged: bool = True

