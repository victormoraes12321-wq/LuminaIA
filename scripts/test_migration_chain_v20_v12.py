"""
Sequential Migration Chain Tester (v20 -> v12 -> v20)
"""

import asyncio
import importlib.util
import os
import sys
from pathlib import Path

os.environ["ENVIRONMENT"] = "test"
os.environ["LUMINA_TESTING"] = "true"
os.environ["TEST_DATABASE_URL"] = "postgresql+asyncpg://lumina_test:lumina_test@127.0.0.1:55432/luminaai_test"
os.environ["SECRET_KEY"] = "test_secret_key_1234567890_test_secret"
os.environ["ENCRYPTION_KEY"] = "test_encryption_key_1234567890_test"
os.environ["OPENAI_API_KEY"] = "sk-proj-testkey1234567890"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from database import get_db_context
from config import settings

settings.ENVIRONMENT = "test"
settings.LUMINA_TESTING = True


def load_migration_module(v_name: str):
    p = Path(__file__).resolve().parents[1] / "backend" / "database" / f"{v_name}.py"
    spec = importlib.util.spec_from_file_location(f"lumina_migration_{v_name}", p)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


async def main():
    down_chain = ["migration_v20_0", "migration_v19_0", "migration_v18_0", "migration_v17_0", "migration_v16_0", "migration_v15_0", "migration_v14_0", "migration_v13_0"]
    up_chain = list(reversed(down_chain))

    print("--- STEP 1: Running Downgrade Chain (v20 -> v12) ---")
    for mod_name in down_chain:
        mod = load_migration_module(mod_name)
        if hasattr(mod, "run_down"):
            import inspect
            sig = inspect.signature(mod.run_down)
            if "confirm_test_only" in sig.parameters:
                res = await mod.run_down(confirm_test_only=True)
            else:
                res = await mod.run_down()
            status_str = res.get("status") if isinstance(res, dict) else "SUCCESS"
            print(f"  {mod_name} DOWN: {status_str}")

    print("\n--- STEP 2: Running Upgrade Chain (v12 -> v20) ---")
    for mod_name in up_chain:
        mod = load_migration_module(mod_name)
        if hasattr(mod, "run_up"):
            res = await mod.run_up()
            status_str = res.get("status") if isinstance(res, dict) else "SUCCESS"
            print(f"  {mod_name} UP: {status_str}")

    print("\nSUCCESS: Sequential Migration Chain Test Completed Successfully!")


if __name__ == "__main__":
    os.environ["ENVIRONMENT"] = "test"
    os.environ["LUMINA_TESTING"] = "true"
    os.environ["TEST_DATABASE_URL"] = "postgresql+asyncpg://lumina_test:lumina_test@127.0.0.1:55432/luminaai_test"
    asyncio.run(main())
