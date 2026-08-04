"""
LuminaAI Validation & Provenance V2 Migration Tests
"""

import importlib.util
from pathlib import Path
import pytest

_PATH = Path(__file__).resolve().parents[1] / "database" / "migration_v20_0.py"
_SPEC = importlib.util.spec_from_file_location("lumina_migration_v20_0", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

run_up = _MODULE.run_up
run_down = _MODULE.run_down


@pytest.mark.asyncio
async def test_migration_v20_0_up_and_idempotency():
    res1 = await run_up()
    assert res1["status"] == "SUCCESS"
    assert res1["migration"] == "v20_0"

    res2 = await run_up()
    assert res2["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_migration_v20_0_down():
    res_down = await run_down()
    assert res_down["status"] == "SUCCESS"

    res_reup = await run_up()
    assert res_reup["status"] == "SUCCESS"
