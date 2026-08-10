"""Fail-closed redaction service for observability payloads, headers, logs, and attributes."""
from __future__ import annotations

import re
from typing import Any
from contracts.observability_v2 import RedactionPolicyV2

_DEFAULT_POLICY = RedactionPolicyV2()
_EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_BEARER_REGEX = re.compile(r"Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*", re.IGNORECASE)
_SQL_KEYWORDS = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|UNION|FROM|WHERE)\b", re.IGNORECASE)


class ObservabilityRedactionService:
    def __init__(self, policy: RedactionPolicyV2 = _DEFAULT_POLICY) -> None:
        self.policy = policy

    def redact_string(self, text: str) -> str:
        if not text:
            return ""
        if _SQL_KEYWORDS.search(text):
            return self.policy.redaction_token
        result = _BEARER_REGEX.sub(self.policy.redaction_token, text)
        result = _EMAIL_REGEX.sub(self.policy.redaction_token, result)
        for key in self.policy.forbidden_keys:
            if key in result.lower():
                return self.policy.redaction_token
        return result

    def redact_dict(self, data: dict[str, Any]) -> dict[str, str]:
        sanitized: dict[str, str] = {}
        for k, v in data.items():
            key_lower = str(k).lower()
            if key_lower in self.policy.forbidden_headers or any(fk in key_lower for fk in self.policy.forbidden_keys):
                sanitized[str(k)] = self.policy.redaction_token
            elif isinstance(v, (str, bytes)):
                sanitized[str(k)] = self.redact_string(str(v))
            elif isinstance(v, (int, float, bool)):
                sanitized[str(k)] = str(v)
            else:
                sanitized[str(k)] = self.policy.redaction_token
        return sanitized

    def sanitize_attributes(self, attrs: dict[str, Any] | tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
        if isinstance(attrs, tuple):
            dict_attrs = dict(attrs)
        else:
            dict_attrs = attrs
        redacted = self.redact_dict(dict_attrs)
        return tuple(sorted((k, str(v)[:128]) for k, v in redacted.items()))
