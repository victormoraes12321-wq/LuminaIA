from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol


class TemporalClock(Protocol):
    def now(self) -> datetime:
        """Return a timezone-aware reference instant."""


class SystemTemporalClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)
