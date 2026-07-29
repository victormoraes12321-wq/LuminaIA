from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from testing.database_guard import validate_test_database_environment

# Fail before importing config, database, main, models, routers, or services.
_test_target = validate_test_database_environment()

# Test settings override sensitive values that an operational .env might contain.
# DATABASE_URL is intentionally not rewritten: Settings selects TEST_DATABASE_URL
# in test mode, while the guard can still compare an explicitly inherited
# operational DATABASE_URL with the disposable target.
os.environ["SECRET_KEY"] = "test-secret-key-only-32-characters-minimum"
os.environ["ENCRYPTION_KEY"] = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
os.environ["OPENAI_API_KEY"] = "sk-test-not-a-real-openai-credential-000000000000"
os.environ["MOCK_ORACLE"] = "true"
os.environ["MOCK_OPENAI"] = "true"
os.environ["LUMINA_DISABLE_EXTERNAL_NETWORK"] = "true"
os.environ["NEW_PIPELINE_ACTIVE"] = "false"
os.environ["ENABLE_DETERMINISTIC_PIPELINE"] = "false"
os.environ["CONTEXT_RESOLUTION_V2_ENABLED"] = "false"
os.environ["CONTEXT_RESOLUTION_V2_SHADOW_MODE"] = "false"
os.environ["CONTEXT_RESOLUTION_V2_FRONTEND_ENABLED"] = "false"

from testing.network_guard import install_external_network_guard

_restore_network = install_external_network_guard(_test_target)

from database import engine
from testing.test_database import bootstrap_test_database, reset_and_seed_test_database


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    _restore_network()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def isolated_test_database(request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("no_database"):
        yield
        return
    await bootstrap_test_database(engine)
    await reset_and_seed_test_database(engine)
    yield
    await engine.dispose()


@pytest.fixture
def expected_baseline() -> dict:
    from testing.test_database import load_expected_baseline

    return load_expected_baseline()


@pytest.fixture
def fake_openai_provider():
    from testing.ai_mock import deterministic_ai_provider

    deterministic_ai_provider.reset()
    yield deterministic_ai_provider
    deterministic_ai_provider.reset()
