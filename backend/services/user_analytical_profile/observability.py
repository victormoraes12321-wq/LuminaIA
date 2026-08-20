from __future__ import annotations

from collections import Counter
from threading import Lock

from contracts.user_analytical_profile_v2 import USER_ANALYTICAL_PROFILE_VERSION


class UserProfileCounters:
    def __init__(self, *, rollout_mode: str) -> None:
        self.rollout_mode = rollout_mode
        self._counter: Counter[str] = Counter()
        self._lock = Lock()

    def increment(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counter[name] += value

    def snapshot(self) -> dict[str, str | int]:
        with self._lock:
            payload: dict[str, str | int] = dict(self._counter)
        payload["rollout_mode"] = self.rollout_mode
        payload["contract_version"] = USER_ANALYTICAL_PROFILE_VERSION
        return payload
