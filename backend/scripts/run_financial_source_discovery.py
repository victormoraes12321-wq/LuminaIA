"""Discovers candidate sources for profit and unbilled-sales metrics."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import date
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db_context
from services.financial_source_discovery import financial_source_discovery


async def run_discovery(json_report: Path, include_row_counts: bool = False) -> dict:
    async with get_db_context() as session:
        report = await financial_source_discovery.discover_postgres(
            session,
            include_row_counts=include_row_counts,
        )

    json_report.parent.mkdir(parents=True, exist_ok=True)
    json_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "version": report.get("version"),
        "source_count": report.get("source_count"),
        "lucro_bruto": report.get("profit", {}).get("lucro_bruto", {}).get("status"),
        "lucro_liquido": report.get("profit", {}).get("lucro_liquido", {}).get("status"),
        "vendas_nao_faturadas": report.get("unbilled_sales", {}).get("vendas_nao_faturadas", {}).get("status"),
        "json_report": str(json_report),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Mapeia fontes candidatas para lucro e vendas nao faturadas.")
    parser.add_argument(
        "--json-report",
        type=Path,
        default=Path("reports") / f"financial_source_discovery_{date.today().isoformat()}.json",
        help="Caminho para salvar o relatorio JSON.",
    )
    parser.add_argument(
        "--include-row-counts",
        action="store_true",
        help="Conta linhas das fontes candidatas. Pode ser mais lento em bases grandes.",
    )
    args = parser.parse_args()
    asyncio.run(run_discovery(args.json_report, include_row_counts=args.include_row_counts))


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()
