"""Bounded structural sanitization delegated to Prompt 24 redaction."""
from __future__ import annotations

import re
from typing import Any

from services.observability_v2.redaction import ObservabilityRedactionService

_FORBIDDEN_KEYS = frozenset({
    "authorization", "cookie", "password", "secret", "token", "api_key", "dsn", "credentials",
    "sql", "raw_sql", "query_sql", "bind", "binds", "parameters", "rows", "sample_rows", "dataset",
    "prompt", "llm_prompt", "chain_of_thought", "reasoning", "traceback", "error_traceback",
    "pergunta", "question", "user_query", "payload_frontend", "result_payload", "raw_business_result",
})
_SECRET_PATTERNS = (
    re.compile(r"(?:postgresql(?:\+asyncpg)?|oracle|mysql)://[^\s]+", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    re.compile(r"(?:[A-Za-z]:\\|/(?:etc|home|root|var|opt|srv)/)"),
    re.compile(r"\bTraceback \(most recent call last\):"),
)
_PUBLIC_ERROR_CODES = frozenset({"PASSWORD_CHANGE_REQUIRED"})


class SecurityPayloadSanitizerV2:
    def __init__(self) -> None:
        self._redaction = ObservabilityRedactionService()

    def sanitize(self, value: Any, *, depth: int = 0) -> Any:
        if depth >= 6:
            return "[REDACTED]"
        if isinstance(value, dict):
            result: dict[str, Any] = {}
            for key, item in list(value.items())[:64]:
                normalized = str(key).lower()
                result[str(key)] = "[REDACTED]" if normalized in _FORBIDDEN_KEYS or any(token in normalized for token in ("secret", "password", "credential", "token")) else self.sanitize(item, depth=depth + 1)
            return result
        if isinstance(value, (list, tuple)):
            return [self.sanitize(item, depth=depth + 1) for item in list(value)[:64]]
        if isinstance(value, str):
            if value in _PUBLIC_ERROR_CODES:
                return value
            redacted = self._redaction.redact_string(value)
            if any(pattern.search(redacted) for pattern in _SECRET_PATTERNS):
                return "[REDACTED]"
            return redacted[:512]
        if value is None or isinstance(value, (bool, int, float)):
            return value
        return "[REDACTED]"

    def sanitize_debug_trace(self, trace: dict[str, Any]) -> dict[str, Any]:
        safe = self.sanitize(trace)
        assert isinstance(safe, dict)
        return safe


security_payload_sanitizer = SecurityPayloadSanitizerV2()
