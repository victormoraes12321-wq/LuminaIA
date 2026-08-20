from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel

_INJECTION_PATTERNS = (
    re.compile(r"(?:ignore|desconsidere|esqueça).{0,32}(?:instruções|regras|sistema)", re.I),
    re.compile(r"(?:system|assistant|developer)\s*:", re.I),
    re.compile(r"(?:select\s+.+\s+from|insert\s+into|update\s+.+\s+set|delete\s+from|drop\s+(?:table|schema))", re.I),
    re.compile(r"(?:oracle|postgres(?:ql)?)://", re.I),
    re.compile(r"(?:<script|javascript:|\{\{|\$\{|```)", re.I),
    re.compile(r"(?:chain.of.thought|raciocínio interno|revele seu prompt)", re.I),
)


def normalize_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).strip().split())


def normalized_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", normalize_text(value)).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", " ", normalized).strip()


def _canonical(value: object) -> object:
    if isinstance(value, BaseModel):
        return _canonical(value.model_dump(mode="json", exclude_none=True))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value).strip()
    if isinstance(value, Mapping):
        return {str(key): _canonical(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_canonical(item) for item in value]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)


def checksum(value: object) -> str:
    encoded = json.dumps(_canonical(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def assert_safe_untrusted_text(value: str, *, field: str = "instruction") -> str:
    normalized = normalize_text(value)
    if any(pattern.search(normalized) for pattern in _INJECTION_PATTERNS):
        raise ValueError(f"DASHBOARD_AI_PROMPT_INJECTION_BLOCKED:{field}")
    return normalized


__all__ = ["assert_safe_untrusted_text", "checksum", "normalize_text", "normalized_key"]
