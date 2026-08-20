from __future__ import annotations

from collections import Counter
from threading import Lock


_ALLOWED = frozenset(
    {
        "search",
        "resolution",
        "resolved",
        "ambiguous",
        "unresolved",
        "blocked",
        "exact_match",
        "alias_match",
        "cache_hit",
        "cache_miss",
        "stale_index",
        "stale_source",
        "publication",
        "rollback",
        "cross_tenant_denial",
        "forbidden_content",
        "build",
        "build_failed",
    }
)


class SemanticObservability:
    def __init__(self) -> None:
        self._counts: Counter[str] = Counter()
        self._lock = Lock()

    def increment(self, name: str, amount: int = 1) -> None:
        if name not in _ALLOWED:
            raise ValueError("semantic telemetry name is not allowlisted")
        with self._lock:
            self._counts[name] += amount

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {key: self._counts.get(key, 0) for key in sorted(_ALLOWED)}


semantic_observability = SemanticObservability()
