from __future__ import annotations

import time
from typing import Dict, List, Tuple


class RateLimiterManager:
    """
    Manages in-memory sliding window rate limits per tenant, user, and tool.
    Guarantees isolation across tenants and users without cross-tenant leakage.
    """

    def __init__(self):
        # Key: (tenant_id, user_id, tool_id) -> List[timestamp]
        self._requests: Dict[Tuple[str, str, str], List[float]] = {}

    def check_rate_limit(
        self, tenant_id: str, user_id: str, tool_id: str, max_requests: int = 100, window_seconds: int = 60
    ) -> bool:
        key = (tenant_id, user_id, tool_id)
        now = time.time()
        cutoff = now - window_seconds

        timestamps = self._requests.setdefault(key, [])
        # Prune outdated timestamps
        self._requests[key] = [t for t in timestamps if t > cutoff]

        if len(self._requests[key]) >= max_requests:
            return False

        self._requests[key].append(now)
        return True


rate_limiter_manager = RateLimiterManager()
