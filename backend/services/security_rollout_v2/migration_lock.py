"""PostgreSQL advisory lock wrapper for governed future migration execution."""
from __future__ import annotations

import hashlib
from contextlib import asynccontextmanager
from typing import AsyncIterator, Protocol

from sqlalchemy import text


class AsyncExecuteTarget(Protocol):
    async def execute(self, statement: object, parameters: dict[str, int] | None = None) -> object: ...


class MigrationLockUnavailable(RuntimeError):
    pass


class PostgresMigrationLockV2:
    LOCK_NAMESPACE = "lumina.security-migration-rollout/1.0:migrations"

    @classmethod
    def lock_key(cls) -> int:
        raw = hashlib.sha256(cls.LOCK_NAMESPACE.encode("utf-8")).digest()[:8]
        return int.from_bytes(raw, byteorder="big", signed=True)

    @classmethod
    @asynccontextmanager
    async def hold(cls, target: AsyncExecuteTarget) -> AsyncIterator[None]:
        key = cls.lock_key()
        result = await target.execute(text("SELECT pg_try_advisory_lock(:lock_key)"), {"lock_key": key})
        acquired = bool(result.scalar())
        if not acquired:
            raise MigrationLockUnavailable("MIGRATION_LOCK_CONTENDED")
        try:
            yield
        finally:
            await target.execute(text("SELECT pg_advisory_unlock(:lock_key)"), {"lock_key": key})
