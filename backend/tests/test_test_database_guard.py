from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from testing.database_guard import (
    TestDatabaseGuardError as GuardError,
    TestDatabaseTarget as DatabaseTarget,
    validate_connected_test_database,
    validate_test_database_url,
)


pytestmark = [
    pytest.mark.unit,
    pytest.mark.security,
    pytest.mark.no_database,
]

SAFE_URL = (
    "postgresql+asyncpg://lumina_test:local-only-password"
    "@127.0.0.1:55432/luminaai_test"
)
COMPOSE_URL = (
    "postgresql+asyncpg://lumina_test:local-only-password"
    "@lumina-test-postgres:5432/luminaai_test"
)


def _validate(url: str | None, **overrides: Any) -> DatabaseTarget:
    values = {
        "environment": "test",
        "testing_enabled": True,
        "operational_database_url": None,
        "environ": {},
    }
    values.update(overrides)
    return validate_test_database_url(url, **values)


@pytest.mark.parametrize(
    ("url", "overrides"),
    [
        (None, {}),
        (SAFE_URL, {"environment": "development"}),
        ("postgresql+asyncpg://u:p@127.0.0.1:55432/postgres", {}),
        ("postgresql+asyncpg://u:p@127.0.0.1:55432/luminaai", {}),
        ("postgresql+asyncpg://u:p@db.corp.local:55432/luminaai_test", {}),
        ("postgresql+asyncpg://u:p@8.8.8.8:55432/luminaai_test", {}),
        ("oracle+oracledb://u:p@127.0.0.1:1521/luminaai_test", {}),
        ("not-a-url", {}),
        ("postgresql+asyncpg://u:p@127.0.0.1:5432/luminaai_test", {}),
        ("postgresql+asyncpg://u:p@127.0.0.1:55432/luminaai", {}),
    ],
)
def test_guard_rejects_unsafe_targets(
    url: str | None,
    overrides: dict[str, Any],
) -> None:
    with pytest.raises(GuardError):
        _validate(url, **overrides)


def test_guard_requires_explicit_testing_flag() -> None:
    with pytest.raises(GuardError, match="LUMINA_TESTING"):
        _validate(SAFE_URL, testing_enabled=False)


def test_guard_rejects_same_target_as_operational_url() -> None:
    with pytest.raises(GuardError, match="destino igual"):
        _validate(SAFE_URL, operational_database_url=SAFE_URL)


def test_guard_accepts_local_disposable_database() -> None:
    target = _validate(SAFE_URL)
    assert target.host == "127.0.0.1"
    assert target.port == 55432
    assert target.database == "luminaai_test"


def test_guard_accepts_allowlisted_compose_service() -> None:
    target = _validate(COMPOSE_URL)
    assert target.host == "lumina-test-postgres"
    assert target.port == 5432


def test_guard_accepts_worker_database() -> None:
    target = _validate(SAFE_URL.replace("luminaai_test", "luminaai_test_gw3"))
    assert target.database == "luminaai_test_gw3"


def test_guard_never_exposes_password() -> None:
    secret = "never-print-this-password"
    url = f"postgresql+asyncpg://user:{secret}@public.example.com:55432/luminaai_test"
    with pytest.raises(GuardError) as exc_info:
        _validate(url)
    assert secret not in str(exc_info.value)
    assert url not in str(exc_info.value)


class _FakeMappings:
    def __init__(self, row: dict[str, Any]) -> None:
        self._row = row

    def one(self) -> dict[str, Any]:
        return self._row


class _FakeResult:
    def __init__(self, row: dict[str, Any]) -> None:
        self._row = row

    def mappings(self) -> _FakeMappings:
        return _FakeMappings(self._row)


class _FakeConnection:
    async def execute(self, statement: Any) -> _FakeResult:
        return _FakeResult(
            {
                "database_name": "operational_database",
                "server_address": "127.0.0.1",
                "server_port": 55432,
            }
        )


@pytest.mark.asyncio
async def test_connected_guard_rejects_current_database_divergence() -> None:
    expected = _validate(SAFE_URL)
    with pytest.raises(GuardError, match="current_database"):
        await validate_connected_test_database(_FakeConnection(), expected)


def _subprocess_environment() -> dict[str, str]:
    env = os.environ.copy()
    for name in (
        "TEST_DATABASE_URL",
        "DATABASE_URL",
        "ENVIRONMENT",
        "LUMINA_TESTING",
    ):
        env.pop(name, None)
    return env


def test_reset_script_refuses_unsafe_database_before_importing_engine() -> None:
    env = _subprocess_environment()
    env.update(
        {
            "ENVIRONMENT": "test",
            "LUMINA_TESTING": "true",
            "TEST_DATABASE_URL": (
                "postgresql+asyncpg://unsafe:never-print-this-password"
                "@127.0.0.1:5432/luminaai_test"
            ),
        }
    )
    result = subprocess.run(
        [sys.executable, "reset_test_state.py"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "Banco de teste recusado" in output
    assert "never-print-this-password" not in output


def test_importing_conftest_without_url_fails_before_database_import() -> None:
    env = _subprocess_environment()
    env.update({"ENVIRONMENT": "test", "LUMINA_TESTING": "true"})
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import runpy,sys;"
                "runpy.run_path('tests/conftest.py', run_name='unsafe_probe');"
                "sys.exit(99)"
            ),
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert result.returncode != 99
    assert "TEST_DATABASE_URL ausente" in output


def test_direct_pytest_without_url_triggers_guard() -> None:
    env = _subprocess_environment()
    env.update({"ENVIRONMENT": "test", "LUMINA_TESTING": "true"})
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_test_database_guard.py"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "TEST_DATABASE_URL ausente" in output
