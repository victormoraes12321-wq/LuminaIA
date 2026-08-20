"""Responsive, deterministic, overlap-safe dashboard layout contracts."""
from __future__ import annotations

from enum import Enum

from pydantic import Field, model_validator

from .identity import CANONICAL_ID_PATTERN, StrictDashboardModel


class DashboardBreakpointV2(str, Enum):
    MOBILE = "MOBILE"
    TABLET = "TABLET"
    DESKTOP = "DESKTOP"
    ULTRAWIDE = "ULTRAWIDE"


BREAKPOINT_COLUMN_LIMITS: dict[DashboardBreakpointV2, int] = {
    DashboardBreakpointV2.MOBILE: 4,
    DashboardBreakpointV2.TABLET: 8,
    DashboardBreakpointV2.DESKTOP: 12,
    DashboardBreakpointV2.ULTRAWIDE: 16,
}


class DashboardGridV2(StrictDashboardModel):
    columns: int = Field(ge=1, le=16)
    row_height_policy: str = Field(
        default="CONTENT_AWARE", pattern=r"^(CONTENT_AWARE|FIXED_SMALL|FIXED_MEDIUM|FIXED_LARGE)$"
    )
    gap_px: int = Field(default=16, ge=0, le=48)
    padding_px: int = Field(default=16, ge=0, le=64)


class DashboardGridItemV2(StrictDashboardModel):
    widget_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    x: int = Field(ge=0, le=15)
    y: int = Field(ge=0, le=999)
    width: int = Field(ge=1, le=16)
    height: int = Field(ge=1, le=100)
    reading_order: int = Field(ge=0, le=999)
    visible: bool = True
    fallback_widget_id: str | None = Field(default=None, pattern=CANONICAL_ID_PATTERN)


class DashboardResponsiveBreakpointV2(StrictDashboardModel):
    breakpoint: DashboardBreakpointV2
    minimum_width_px: int = Field(ge=0, le=10_000)
    grid: DashboardGridV2
    items: tuple[DashboardGridItemV2, ...] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_grid(self) -> "DashboardResponsiveBreakpointV2":
        expected_columns = BREAKPOINT_COLUMN_LIMITS[self.breakpoint]
        if self.grid.columns != expected_columns:
            raise ValueError(
                f"{self.breakpoint.value} requires exactly {expected_columns} governed columns"
            )
        ids = [item.widget_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("a widget can appear only once per breakpoint")
        orders = [item.reading_order for item in self.items if item.visible]
        if len(orders) != len(set(orders)):
            raise ValueError("visible reading_order values must be unique")
        for item in self.items:
            if item.x + item.width > self.grid.columns:
                raise ValueError(f"widget {item.widget_id} exceeds the breakpoint grid")
        for index, left in enumerate(self.items):
            if not left.visible:
                continue
            for right in self.items[index + 1 :]:
                if not right.visible:
                    continue
                separated = (
                    left.x + left.width <= right.x
                    or right.x + right.width <= left.x
                    or left.y + left.height <= right.y
                    or right.y + right.height <= left.y
                )
                if not separated:
                    raise ValueError(
                        f"layout overlap between {left.widget_id} and {right.widget_id}"
                    )
        return self


class DashboardLayoutV2(StrictDashboardModel):
    breakpoints: tuple[DashboardResponsiveBreakpointV2, ...] = Field(
        min_length=4, max_length=4
    )

    @model_validator(mode="after")
    def validate_breakpoints(self) -> "DashboardLayoutV2":
        actual = [item.breakpoint for item in self.breakpoints]
        if len(actual) != len(set(actual)):
            raise ValueError("breakpoints must be unique")
        if set(actual) != set(DashboardBreakpointV2):
            raise ValueError("MOBILE, TABLET, DESKTOP, and ULTRAWIDE are required")
        expected_widths = {
            DashboardBreakpointV2.MOBILE: 0,
            DashboardBreakpointV2.TABLET: 768,
            DashboardBreakpointV2.DESKTOP: 1280,
            DashboardBreakpointV2.ULTRAWIDE: 1920,
        }
        for item in self.breakpoints:
            if item.minimum_width_px != expected_widths[item.breakpoint]:
                raise ValueError(f"invalid governed minimum width for {item.breakpoint.value}")
        return self

