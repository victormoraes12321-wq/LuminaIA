from __future__ import annotations

from datetime import timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class InvalidTemporalTimezone(ValueError):
    pass


def resolve_timezone(name: str) -> tzinfo:
    """Resolve an IANA zone, with a controlled no-dependency Windows fallback."""
    if name == "UTC":
        return timezone.utc
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        # Brazil has observed UTC-03:00 without DST since 2019. This fallback
        # keeps the documented application zone usable when Windows has no
        # system IANA database and adding tzdata is outside the task scope.
        if name == "America/Sao_Paulo":
            return timezone(timedelta(hours=-3), name="America/Sao_Paulo")
        raise InvalidTemporalTimezone(name) from exc
