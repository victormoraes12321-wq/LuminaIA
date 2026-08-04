from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from database import get_db_context
from sqlalchemy import text

_PATH = Path(__file__).resolve().parents[1] / "database" / "migration_v17_0.py"
_SPEC = importlib.util.spec_from_file_location("lumina_migration_v17_0", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

TABLES = _MODULE.TABLES
run_up = _MODULE.run_up
run_down = _MODULE.run_down

pytestmark = [pytest.mark.integration, pytest.mark.database]


@pytest.mark.asyncio
async def test_migration_v17_idempotency() -> None:
    await run_down(confirm_test_only=True)
    res_up1 = await run_up()
    assert res_up1["status"] == "success"
    assert len(res_up1["tables"]) == 12

    # Second UP call must succeed without errors (idempotent)
    res_up2 = await run_up()
    assert res_up2["status"] == "success"

    async with get_db_context() as session:
        for t in TABLES:
            chk = await session.execute(
                text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :t)"),
                {"t": t},
            )
            assert chk.scalar() is True, f"Table '{t}' missing after migration_v17 UP."


@pytest.mark.asyncio
async def test_migration_v17_down_up_cycle() -> None:
    res_down = await run_down(confirm_test_only=True)
    assert res_down["status"] == "success"

    async with get_db_context() as session:
        for t in TABLES:
            chk = await session.execute(
                text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :t)"),
                {"t": t},
            )
            assert chk.scalar() is False, f"Table '{t}' still exists after migration_v17 DOWN."

    res_up = await run_up()
    assert res_up["status"] == "success"
