from __future__ import annotations

from typing import Any


VOLATILE_KEYS = {
    "created_at",
    "criado_em",
    "duration_ms",
    "execution_time_ms",
    "query_id",
    "request_id",
    "timestamp",
    "trace_id",
    "updated_at",
}


def normalize_golden_payload(value: Any) -> Any:
    """Remove only runtime volatility while preserving semantic contracts."""

    if isinstance(value, dict):
        return {
            key: normalize_golden_payload(item)
            for key, item in sorted(value.items())
            if key not in VOLATILE_KEYS
        }
    if isinstance(value, list):
        return [normalize_golden_payload(item) for item in value]
    if isinstance(value, float):
        return round(value, 6)
    return value
