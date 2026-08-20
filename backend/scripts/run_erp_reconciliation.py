"""Runs ERP-vs-clone reconciliation for critical sales reports."""
from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from database import get_db_context
from models.tenant import Tenant
from services.erp_reconciliation import erp_reconciliation
from services.oracle_service import decrypt_connection_details, get_oracle_connection


async def _close_resource(resource: Any) -> None:
    if not resource:
        return
    close = getattr(resource, "close", None)
    if not close:
        return
    result = close()
    if inspect.isawaitable(result):
        await result


async def _load_tenant(session: Any, tenant_id: str | None) -> Tenant | None:
    stmt = select(Tenant)
    if tenant_id:
        stmt = stmt.where(Tenant.id == tenant_id)
    stmt = stmt.limit(1)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def _safe_oracle_error(exc: Exception) -> dict[str, Any]:
    return {
        "type": type(exc).__name__,
        "code": getattr(exc, "code", None),
        "message": getattr(exc, "user_message", str(exc)),
        "technical_detail": getattr(exc, "technical_detail", None),
    }


async def run_reconciliation(
    *,
    periods: list[str],
    json_report: Path,
    tenant_id: str | None = None,
    skip_oracle: bool = False,
) -> dict[str, Any]:
    oracle_connection = None
    oracle_error = None
    async with get_db_context() as session:
        tenant = await _load_tenant(session, tenant_id)
        if not skip_oracle:
            if not tenant:
                oracle_error = {"code": "TENANT_NOT_FOUND", "message": "Tenant nao encontrado para carregar conexao Oracle."}
            else:
                try:
                    details = decrypt_connection_details(tenant.oracle_conn)
                    oracle_connection = await get_oracle_connection(details, tenant_id=tenant.id)
                except Exception as exc:
                    oracle_error = _safe_oracle_error(exc)

        try:
            report = await erp_reconciliation.reconcile(
                session,
                periods=periods,
                oracle_connection=oracle_connection,
                oracle_error=oracle_error,
                include_oracle=not skip_oracle,
            )
        finally:
            await _close_resource(oracle_connection)

    json_report.parent.mkdir(parents=True, exist_ok=True)
    json_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "version": report.get("version"),
        "overall_status": report.get("overall_status"),
        "periods": [item.get("period") for item in report.get("periods", [])],
        "json_report": str(json_report),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Bate relatorios criticos do clone contra o ERP Oracle.")
    parser.add_argument(
        "--period",
        action="append",
        dest="periods",
        default=None,
        help="Periodo no formato YYYY-MM. Pode ser usado mais de uma vez.",
    )
    parser.add_argument("--tenant-id", default=None, help="Tenant especifico. Padrao: primeiro tenant.")
    parser.add_argument("--skip-oracle", action="store_true", help="Gera somente o lado clone e marca Oracle como ignorado.")
    parser.add_argument("--require-oracle", action="store_true", help="Falha se Oracle estiver indisponivel.")
    parser.add_argument("--fail-on-mismatch", action="store_true", help="Falha se houver divergencia numerica contra o ERP.")
    parser.add_argument(
        "--json-report",
        type=Path,
        default=Path("reports") / f"erp_reconciliation_{date.today().isoformat()}.json",
        help="Caminho para salvar o relatorio JSON.",
    )
    args = parser.parse_args()
    periods = args.periods or ["2026-06", "2026-07"]
    report = asyncio.run(
        run_reconciliation(
            periods=periods,
            json_report=args.json_report,
            tenant_id=args.tenant_id,
            skip_oracle=args.skip_oracle,
        )
    )

    status = report.get("overall_status")
    if args.require_oracle and status != "ok":
        raise SystemExit(2)
    if args.fail_on_mismatch and status == "mismatch":
        raise SystemExit(1)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()
