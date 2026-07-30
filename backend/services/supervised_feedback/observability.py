from __future__ import annotations

from collections import Counter
from threading import Lock

from contracts.supervised_feedback_v2 import SUPERVISED_FEEDBACK_VERSION


ALLOWED_FEEDBACK_METRICS = frozenset(
    {
        "feedback_received",
        "feedback_positive",
        "feedback_negative",
        "feedback_partially_correct",
        "duplicate_replay",
        "redaction_blocks",
        "security_flags",
        "reviews",
        "approvals",
        "rejections",
        "withdrawals",
        "candidates",
        "approved_examples",
        "dataset_snapshots",
        "dataset_exports",
        "version_conflicts",
        "access_denied",
        "cross_tenant_denials",
        "cross_user_denials",
        "cache_hit",
        "cache_miss",
        "cache_invalidations",
        "import_dry_runs",
        "import_rejections",
    }
)


class FeedbackCounters:
    """Process-local structural counters. Names are fixed and values carry no content."""

    def __init__(self, *, rollout_mode: str) -> None:
        self.rollout_mode = rollout_mode
        self._counter: Counter[str] = Counter()
        self._lock = Lock()

    def increment(self, name: str, value: int = 1) -> None:
        if name not in ALLOWED_FEEDBACK_METRICS:
            raise ValueError("Metrica de feedback nao permitida.")
        if value < 0:
            raise ValueError("Incremento de metrica deve ser positivo.")
        with self._lock:
            self._counter[name] += value

    def snapshot(self) -> dict[str, str | int]:
        with self._lock:
            payload: dict[str, str | int] = dict(self._counter)
        payload["mode"] = self.rollout_mode
        payload["contract_version"] = SUPERVISED_FEEDBACK_VERSION
        return payload
