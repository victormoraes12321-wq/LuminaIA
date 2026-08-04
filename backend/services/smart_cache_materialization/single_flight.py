"""Bounded single-flight coordination backed by tenant-scoped leases."""
from __future__ import annotations

import asyncio
import secrets
from collections.abc import Awaitable, Callable
from typing import TypeVar

from .repository import SmartCacheRepository


T = TypeVar("T")


class CacheSingleFlightService:
    def __init__(self, repository: SmartCacheRepository, *, lease_ttl_seconds: int = 30):
        self.repository = repository
        self.lease_ttl_seconds = lease_ttl_seconds
        self._guard = asyncio.Lock()
        self._in_flight: dict[str, asyncio.Task[T]] = {}

    async def execute_single_flight(
        self,
        tenant_id: str,
        cache_key_checksum: str,
        coroutine_factory: Callable[[], Awaitable[T]],
        *,
        wait_timeout_seconds: float = 30.0,
    ) -> tuple[bool, T | None]:
        key = f"{tenant_id}:{cache_key_checksum}"
        async with self._guard:
            existing = self._in_flight.get(key)
            if existing is None:
                owner_token = secrets.token_urlsafe(32)
                task = asyncio.create_task(
                    self._execute_as_owner(
                        tenant_id,
                        cache_key_checksum,
                        owner_token,
                        coroutine_factory,
                    )
                )
                self._in_flight[key] = task
                task.add_done_callback(
                    lambda completed, flight_key=key: asyncio.create_task(
                        self._discard_completed(flight_key, completed)
                    )
                )
                is_owner = True
            else:
                task = existing
                is_owner = False
        try:
            result = await asyncio.wait_for(asyncio.shield(task), timeout=wait_timeout_seconds)
            return is_owner, result
        except asyncio.TimeoutError:
            return False, None
        finally:
            if task.done():
                async with self._guard:
                    if self._in_flight.get(key) is task:
                        self._in_flight.pop(key, None)

    async def _execute_as_owner(
        self,
        tenant_id: str,
        cache_key_checksum: str,
        owner_token: str,
        coroutine_factory: Callable[[], Awaitable[T]],
    ) -> T:
        acquired = await self.repository.acquire_lease(
            tenant_id,
            cache_key_checksum,
            owner_token,
            self.lease_ttl_seconds,
        )
        if not acquired:
            raise RuntimeError("single-flight lease is held by another replica")
        try:
            return await coroutine_factory()
        finally:
            await self.repository.release_lease(tenant_id, cache_key_checksum, owner_token)

    async def _discard_completed(self, key: str, task: asyncio.Task[T]) -> None:
        async with self._guard:
            if self._in_flight.get(key) is task:
                self._in_flight.pop(key, None)
