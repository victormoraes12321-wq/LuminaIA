from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from typing import Any, Awaitable, Protocol

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .models import CompiledOperandQuery


class ComparisonQueryRunner(Protocol):
    source_kind: str
    tenant_isolation_verified: bool
    isolation_evidence: str

    async def execute(self, query: CompiledOperandQuery) -> list[dict[str, Any]]:
        ...


class TransientComparisonQueryError(RuntimeError):
    pass


class SQLAlchemyComparisonQueryRunner:
    source_kind = "ANALYTICAL_CLONE"

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | Callable[[], AsyncSession],
        *,
        tenant_isolation_evidence: str | None = None,
    ) -> None:
        self._session_factory = session_factory
        self.tenant_isolation_verified = tenant_isolation_evidence is not None
        self.isolation_evidence = tenant_isolation_evidence or (
            "tenant isolation was not independently verified"
        )

    async def execute(self, query: CompiledOperandQuery) -> list[dict[str, Any]]:
        timeout_ms = max(1, int(query.timeout_seconds * 1000))
        try:
            async with self._session_factory() as session:
                await session.execute(
                    text("SELECT set_config('statement_timeout', :timeout_ms, true)"),
                    {"timeout_ms": str(timeout_ms)},
                )
                result = await session.execute(text(query.statement), dict(query.binds))
                return [dict(row) for row in result.mappings().all()]
        except (OperationalError, DBAPIError) as exc:
            sqlstate = getattr(getattr(exc, "orig", None), "sqlstate", None)
            if sqlstate in {"40001", "40P01", "55P03"}:
                raise TransientComparisonQueryError("Transient analytical query failure") from exc
            raise
        except asyncio.CancelledError:
            raise


class AsyncpgComparisonQueryRunner:
    source_kind = "ANALYTICAL_CLONE"
    tenant_isolation_verified = True
    isolation_evidence = "tenant column verified in clone metadata and bound by compiler"

    def __init__(
        self,
        acquire: Callable[[], Awaitable[Any]],
        release: Callable[[Any], Awaitable[None]],
        *,
        tenant_column: str = "tenant_id",
    ) -> None:
        self._acquire = acquire
        self._release = release
        self._tenant_column = tenant_column
        self._verified_relations: set[str] = set()

    async def execute(self, query: CompiledOperandQuery) -> list[dict[str, Any]]:
        connection = await self._acquire()
        try:
            await self._verify_tenant_column(connection, query.source_id)
            statement, values = _to_asyncpg_statement(query.statement, query.binds)
            async with connection.transaction():
                await connection.execute(
                    "SELECT set_config('statement_timeout', $1, true)",
                    str(max(1, int(query.timeout_seconds * 1000))),
                )
                rows = await connection.fetch(statement, *values)
            return [dict(row) for row in rows]
        finally:
            await self._release(connection)

    async def _verify_tenant_column(self, connection: Any, relation: str) -> None:
        if relation in self._verified_relations:
            return
        exists = await connection.fetchval(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = $1
                  AND column_name = $2
            )
            """,
            relation,
            self._tenant_column,
        )
        if not exists:
            raise RuntimeError(
                "Analytical source has no verifiable tenant isolation column"
            )
        self._verified_relations.add(relation)


_NAMED_BIND = re.compile(r"(?<!:):([A-Za-z_][A-Za-z0-9_]*)")


def _to_asyncpg_statement(
    statement: str,
    binds: dict[str, Any],
) -> tuple[str, list[Any]]:
    positions: dict[str, int] = {}
    values: list[Any] = []

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in binds:
            raise ValueError("Compiled query references an unknown bind")
        if name not in positions:
            positions[name] = len(values) + 1
            values.append(binds[name])
        return f"${positions[name]}"

    converted = _NAMED_BIND.sub(replace, statement)
    if set(binds) - set(positions):
        raise ValueError("Compiled query contains unused binds")
    return converted, values
