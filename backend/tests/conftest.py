import pytest
import asyncio
import pytest_asyncio
from reset_test_state import reset_test_state

# Configura NullPool para evitar conflitos de event loop no pool de conexões durante os testes
from sqlalchemy.pool import NullPool
from database import engine
engine.pool = NullPool(engine.pool._creator, recycle=engine.pool._recycle)



@pytest_asyncio.fixture(scope="function", autouse=True)
async def auto_reset_db():
    """Automatically resets the database state before every test function runs."""
    from database import engine
    await engine.dispose()
    await reset_test_state()
