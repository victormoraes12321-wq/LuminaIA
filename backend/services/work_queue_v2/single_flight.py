"""Singleflight Service for Background Work Queue Job Coalescing V2."""
from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable


class WorkQueueSingleFlightServiceV2:
    """Coalesces concurrent identical background execution calls by idempotency key."""

    def __init__(self) -> None:
        self._futures: dict[str, asyncio.Future[Any]] = {}
        self._lock = asyncio.Lock()
        self._coalesced_counts: dict[str, int] = {}

    async def execute_or_coalesce(
        self,
        key: str,
        coro_fn: Callable[[], Awaitable[Any]],
    ) -> tuple[Any, bool]:
        """Execute coro_fn or join existing in-flight future for key.

        Returns (result, was_coalesced: bool).
        """
        async with self._lock:
            if key in self._futures:
                fut = self._futures[key]
                self._coalesced_counts[key] = self._coalesced_counts.get(key, 0) + 1
                is_origin = False
            else:
                loop = asyncio.get_running_loop()
                fut = loop.create_future()
                self._futures[key] = fut
                self._coalesced_counts[key] = 0
                is_origin = True

        if not is_origin:
            result = await fut
            return result, True

        try:
            result = await coro_fn()
            fut.set_result(result)
            return result, False
        except Exception as exc:
            fut.set_exception(exc)
            raise
        finally:
            async with self._lock:
                self._futures.pop(key, None)
                self._coalesced_counts.pop(key, None)

    def get_coalesced_count(self, key: str) -> int:
        return self._coalesced_counts.get(key, 0)
