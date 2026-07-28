"""Safe reset entry point for the disposable LuminaAI test database."""

from __future__ import annotations

import asyncio

from testing.database_guard import validate_test_database_environment

# This executes before importing database.py and therefore before engine creation.
validate_test_database_environment()

from database import engine
from testing.test_database import bootstrap_test_database, reset_and_seed_test_database


async def reset_test_state() -> None:
    validate_test_database_environment()
    await bootstrap_test_database(engine)
    await reset_and_seed_test_database(engine)


if __name__ == "__main__":
    asyncio.run(reset_test_state())
