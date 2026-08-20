from __future__ import annotations

import base64
import hashlib
import json
import re
import unicodedata
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, JsonValue


def normalize_lexical(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    lowered = without_marks.casefold()
    return " ".join(re.findall(r"[a-z0-9]+", lowered))


def _canonical_value(value: object) -> JsonValue:
    if isinstance(value, BaseModel):
        return _canonical_value(value.model_dump(mode="json", exclude_none=True))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {
            str(key): _canonical_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unsupported canonical value: {type(value).__name__}")


def canonical_json(value: object) -> str:
    return json.dumps(
        _canonical_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def compute_checksum(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def encode_cursor(*, normalized_query: str, score: int, asset_id: uuid.UUID) -> str:
    payload = canonical_json(
        {"query_hash": compute_checksum(normalized_query), "score": score, "asset_id": asset_id}
    )
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def decode_cursor(cursor: str, *, normalized_query: str) -> tuple[int, uuid.UUID]:
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        payload = json.loads(decoded)
        if payload["query_hash"] != compute_checksum(normalized_query):
            raise ValueError("cursor query mismatch")
        return int(payload["score"]), uuid.UUID(str(payload["asset_id"]))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("invalid knowledge search cursor") from exc


def csv_safe(value: str) -> str:
    stripped_spaces = value.lstrip(" ")
    if value.startswith(("\t", "\r")) or stripped_spaces.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value
