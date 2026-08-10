"""Governed Concurrency Controller for V2 Work Queue and background execution."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from config import settings
from contracts.work_queue_v2.enums import ConcurrencyClassV2


@dataclass
class ConcurrencyPermitV2:
    permit_id: str
    tenant_id: str
    concurrency_class: ConcurrencyClassV2
    acquired_at_ns: int


class GovernedConcurrencyControllerV2:
    """Manages global, tenant, and class-level bounded semaphores safely."""

    def __init__(self, global_limit: int | None = None, tenant_limit: int | None = None) -> None:
        self.global_limit = global_limit or getattr(settings, "WORK_QUEUE_MAX_CONCURRENCY", 10)
        self.tenant_limit = tenant_limit or getattr(settings, "WORK_QUEUE_PER_TENANT_CONCURRENCY", 3)

        self._global_semaphore = asyncio.Semaphore(self.global_limit)
        self._tenant_semaphores: dict[str, asyncio.Semaphore] = {}
        self._class_semaphores: dict[ConcurrencyClassV2, asyncio.Semaphore] = {
            ConcurrencyClassV2.DB_BOUND: asyncio.Semaphore(5),
            ConcurrencyClassV2.CPU_BOUND: asyncio.Semaphore(4),
            ConcurrencyClassV2.AI_BOUND: asyncio.Semaphore(2),
            ConcurrencyClassV2.MATERIALIZATION_BOUND: asyncio.Semaphore(2),
            ConcurrencyClassV2.BACKGROUND: asyncio.Semaphore(5),
        }
        self._active_permits: dict[str, ConcurrencyPermitV2] = {}
        self._lock = asyncio.Lock()

    def _get_tenant_semaphore(self, tenant_id: str) -> asyncio.Semaphore:
        if tenant_id not in self._tenant_semaphores:
            self._tenant_semaphores[tenant_id] = asyncio.Semaphore(self.tenant_limit)
        return self._tenant_semaphores[tenant_id]

    @asynccontextmanager
    async def acquire_permit(
        self,
        tenant_id: str,
        concurrency_class: ConcurrencyClassV2,
        timeout_seconds: float = 30.0,
    ) -> AsyncGenerator[ConcurrencyPermitV2, None]:
        permit_id = f"{tenant_id}:{concurrency_class}:{id(asyncio.current_task())}"
        tenant_sem = self._get_tenant_semaphore(tenant_id)
        class_sem = self._class_semaphores.get(concurrency_class, self._global_semaphore)

        # Acquire in deterministic order to prevent deadlock: global -> tenant -> class
        acquired_global = False
        acquired_tenant = False
        acquired_class = False

        try:
            await asyncio.wait_for(self._global_semaphore.acquire(), timeout=timeout_seconds)
            acquired_global = True

            await asyncio.wait_for(tenant_sem.acquire(), timeout=timeout_seconds)
            acquired_tenant = True

            if class_sem is not self._global_semaphore:
                await asyncio.wait_for(class_sem.acquire(), timeout=timeout_seconds)
                acquired_class = True

            permit = ConcurrencyPermitV2(
                permit_id=permit_id,
                tenant_id=tenant_id,
                concurrency_class=concurrency_class,
                acquired_at_ns=asyncio.get_event_loop().time() * 1e9,
            )
            async with self._lock:
                self._active_permits[permit_id] = permit

            yield permit

        finally:
            async with self._lock:
                self._active_permits.pop(permit_id, None)

            if acquired_class and class_sem is not self._global_semaphore:
                class_sem.release()
            if acquired_tenant:
                tenant_sem.release()
            if acquired_global:
                self._global_semaphore.release()

    def get_active_permit_count(self) -> int:
        return len(self._active_permits)

    def get_tenant_active_count(self, tenant_id: str) -> int:
        return sum(1 for p in self._active_permits.values() if p.tenant_id == tenant_id)
