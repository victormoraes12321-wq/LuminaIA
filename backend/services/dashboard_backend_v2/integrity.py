"""Deterministic checksums and idempotency scope helpers."""
from __future__ import annotations

import hashlib
import json
import unicodedata
import uuid
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel


def _normalize(value: object) -> object:
    if isinstance(value, BaseModel):
        return _normalize(value.model_dump(mode="json", exclude_none=True))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value).strip()
    if isinstance(value, Mapping):
        return {str(key): _normalize(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize(item) for item in value]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    raise TypeError(f"unsupported checksum type: {type(value).__name__}")


def canonical_json(value: object) -> str:
    return json.dumps(_normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def checksum(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def idempotency_fingerprint(
    *, tenant_id: str, user_id: str, operation: str, resource_id: str, key: str, payload: object
) -> tuple[str, str]:
    if not 8 <= len(key) <= 200:
        raise ValueError("idempotency key must contain 8 to 200 characters")
    request_checksum = checksum(payload)
    scope = checksum({
        "tenant": tenant_id,
        "user": user_id,
        "operation": operation,
        "resource": resource_id,
        "key": key,
    })
    return scope, request_checksum
