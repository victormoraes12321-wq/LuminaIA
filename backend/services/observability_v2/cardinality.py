"""Cardinality guard for operational metric labels and dimension control."""
from __future__ import annotations

import re
from typing import Mapping
from contracts.observability_v2 import CardinalityPolicyV2

_DEFAULT_CARDINALITY_POLICY = CardinalityPolicyV2()
_UUID_REGEX = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_SQL_PATTERN = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN)\b", re.IGNORECASE)

FORBIDDEN_LABEL_KEYS = frozenset({
    "request_id", "trace_id", "span_id", "user_id", "email", "dashboard_id",
    "proposal_id", "conversation_id", "question", "sql", "bind", "binds",
    "exception_text", "raw_path", "authorization", "cookie",
})


class OperationalMetricCardinalityGuard:
    def __init__(self, policy: CardinalityPolicyV2 = _DEFAULT_CARDINALITY_POLICY) -> None:
        self.policy = policy
        self._dropped_count = 0

    @property
    def dropped_count(self) -> int:
        return self._dropped_count

    def validate_and_normalize_labels(
        self,
        labels: Mapping[str, str] | tuple[tuple[str, str], ...],
        allowed_keys: tuple[str, ...] | frozenset[str] = frozenset(),
    ) -> tuple[tuple[str, str], ...]:
        if isinstance(labels, tuple):
            label_dict = dict(labels)
        else:
            label_dict = dict(labels)

        allowed_set = frozenset(allowed_keys)
        normalized: dict[str, str] = {}

        for k, v in label_dict.items():
            key_clean = str(k).strip().lower()
            val_clean = str(v).strip()

            if key_clean in FORBIDDEN_LABEL_KEYS:
                self._dropped_count += 1
                continue

            if allowed_set and key_clean not in allowed_set:
                self._dropped_count += 1
                continue

            if _UUID_REGEX.match(val_clean) or _SQL_PATTERN.search(val_clean) or len(val_clean) > self.policy.max_label_value_length:
                val_clean = self.policy.fallback_value

            normalized[key_clean] = val_clean[: self.policy.max_label_value_length]

        return tuple(sorted(normalized.items()))
