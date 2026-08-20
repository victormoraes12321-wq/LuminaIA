from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.no_database


def _run_bootstrap_probe(source: str, **overrides: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "SMART_CACHE_MATERIALIZATION_MODE": "LEGACY_ONLY",
            "SMART_CACHE_ADMIN_ENABLED": "false",
            "SMART_CACHE_FRONTEND_ENABLED": "false",
            "SMART_CACHE_INSPECTOR_ENABLED": "false",
            "SMART_CACHE_READ_ENABLED": "false",
            "SMART_CACHE_WRITE_ENABLED": "false",
            "SMART_MATERIALIZATION_READ_ENABLED": "false",
            "SMART_MATERIALIZATION_BUILD_ENABLED": "false",
        }
    )
    environment.update(overrides)
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(source)],
        cwd=BACKEND_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_models_import_does_not_register_prompt18_metadata() -> None:
    result = _run_bootstrap_probe(
        """
        import sys
        import models
        from database import Base

        assert "models.smart_cache_materialization" not in sys.modules
        assert "database.migration_v21_0" not in sys.modules
        forbidden = (
            "smart_cache_",
            "materialization_",
        )
        assert not any(name.startswith(forbidden) for name in Base.metadata.tables)
        """
    )
    assert result.returncode == 0, result.stderr


def test_main_legacy_only_does_not_load_prompt18_or_create_tasks() -> None:
    result = _run_bootstrap_probe(
        """
        import asyncio
        import sys

        def forbidden_create_task(*args, **kwargs):
            raise AssertionError("Prompt 18 must not create tasks during import")

        asyncio.create_task = forbidden_create_task
        import main

        paths = {route.path for route in main.app.routes}
        assert "routers.smart_cache_materialization" not in sys.modules
        assert "services.smart_cache_materialization" not in sys.modules
        assert "models.smart_cache_materialization" not in sys.modules
        assert "database.migration_v21_0" not in sys.modules
        assert not any(path.startswith("/api/v2/cache") for path in paths)
        assert not any(path.startswith("/api/v2/materialization") for path in paths)
        """
    )
    assert result.returncode == 0, result.stderr


def test_nonlegacy_mode_still_requires_server_admin_flag() -> None:
    result = _run_bootstrap_probe(
        """
        import sys
        import main

        paths = {route.path for route in main.app.routes}
        assert "routers.smart_cache_materialization" not in sys.modules
        assert not any(path.startswith("/api/v2/cache") for path in paths)
        """,
        SMART_CACHE_MATERIALIZATION_MODE="SHADOW_OBSERVE",
        SMART_CACHE_ADMIN_ENABLED="false",
    )
    assert result.returncode == 0, result.stderr


def test_experimental_router_requires_both_server_flags() -> None:
    result = _run_bootstrap_probe(
        """
        import sys
        import main

        paths = {route.path for route in main.app.routes}
        assert "routers.smart_cache_materialization" in sys.modules
        assert "services.smart_cache_materialization" not in sys.modules
        assert "models.smart_cache_materialization" not in sys.modules
        assert any(path.startswith("/api/v2/cache") for path in paths)
        assert "database.migration_v21_0" not in sys.modules
        """,
        SMART_CACHE_MATERIALIZATION_MODE="SHADOW_OBSERVE",
        SMART_CACHE_ADMIN_ENABLED="true",
    )
    assert result.returncode == 0, result.stderr
