"""Controlled resync for LM Oracle views into the PostgreSQL clone."""
from __future__ import annotations

import argparse
import asyncio
import inspect
import os
import sys
import time
from typing import Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from database import get_db_context
from models.tenant import Tenant
from models.view_catalog import ViewCatalog
from services.data_platform.sync_engine import sync_engine
from services.oracle_service import decrypt_connection_details, get_oracle_connection
from services.postgresql_clone_service import get_clone_db_connection, release_clone_db_connection


async def _close_resource(resource: Any) -> None:
    if not resource:
        return
    close = getattr(resource, "close", None)
    if not close:
        return
    result = close()
    if inspect.isawaitable(result):
        await result


async def run_resync(*, views: list[str], tenant_id: str | None, force_full: bool) -> list[dict[str, Any]]:
    async with get_db_context() as session:
        tenant_stmt = select(Tenant)
        if tenant_id:
            tenant_stmt = tenant_stmt.where(Tenant.id == tenant_id)
        tenant = (await session.execute(tenant_stmt.limit(1))).scalar_one()
        view_rows = (
            await session.execute(
                select(ViewCatalog).where(ViewCatalog.nome_view_oracle.in_([view.upper() for view in views]))
            )
        ).scalars().all()
        view_by_name = {row.nome_view_oracle.upper(): row for row in view_rows}
        oracle_details = decrypt_connection_details(tenant.oracle_conn)
        pg_details = decrypt_connection_details(tenant.clone_db_conn)

    missing = [view.upper() for view in views if view.upper() not in view_by_name]
    if missing:
        raise RuntimeError(f"Views nao cadastradas no catalogo: {', '.join(missing)}")

    oracle_conn = None
    pg_conn = None
    results: list[dict[str, Any]] = []
    try:
        oracle_conn = await get_oracle_connection(oracle_details, tenant_id=tenant.id)
        oracle_conn.call_timeout = 600000
        pg_conn = await get_clone_db_connection(pg_details)

        for view_name in [view.upper() for view in views]:
            catalog_view = view_by_name[view_name]
            started = time.perf_counter()

            async def progress(event: dict[str, Any], *, _view_name: str = view_name) -> None:
                phase = str(event.get("phase") or "syncing")
                imported = int(event.get("imported_rows") or 0)
                estimated = event.get("estimated_rows")
                suffix = f"/{estimated}" if estimated is not None else ""
                print(f"[{_view_name}] {phase}: {imported}{suffix}")

            imported = await sync_engine._sync_single_view(
                tenant_id=tenant.id,
                view_name=view_name,
                view_catalog_id=catalog_view.id,
                oracle_conn=oracle_conn,
                pg_conn=pg_conn,
                progress_callback=progress,
                force_full=force_full,
            )
            results.append(
                {
                    "view": view_name,
                    "status": "success",
                    "force_full": force_full,
                    "imported_rows": imported,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                }
            )
    finally:
        if pg_conn:
            await release_clone_db_connection(pg_conn)
        await _close_resource(oracle_conn)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Ressincroniza views LM do Oracle para o clone.")
    parser.add_argument("--tenant-id", default=None, help="Tenant especifico. Padrao: primeiro tenant.")
    parser.add_argument("--view", action="append", dest="views", default=None, help="Nome da view. Pode repetir.")
    parser.add_argument("--full", action="store_true", help="Forca carga completa em staging antes da troca atomica.")
    args = parser.parse_args()
    views = args.views or ["VW_VENDAS_LM"]
    results = asyncio.run(run_resync(views=views, tenant_id=args.tenant_id, force_full=args.full))
    for result in results:
        print(result)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()
