from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
FRONTEND_ROOT = REPOSITORY_ROOT / "frontend"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_backend_runtime_copy_is_an_explicit_allowlist() -> None:
    dockerfile = _read(BACKEND_ROOT / "Dockerfile")

    assert "COPY . ." not in dockerfile
    assert "COPY --chown=10001:10001 main.py config.py database.py ./" in dockerfile
    for runtime_directory in (
        "contracts",
        "database",
        "models",
        "routers",
        "schemas",
        "services",
    ):
        assert f"COPY --chown=10001:10001 {runtime_directory} ./{runtime_directory}" in dockerfile
    assert (
        "COPY --chown=10001:10001 testing/__init__.py "
        "testing/database_guard.py ./testing/"
    ) in dockerfile
    for prohibited in ("tests", "reports", "backups", ".env", "runtime-logs"):
        assert f"COPY --chown=10001:10001 {prohibited}" not in dockerfile


def test_docker_contexts_are_allowlisted_and_exclude_local_state() -> None:
    backend_ignore = _read(BACKEND_ROOT / ".dockerignore")
    frontend_ignore = _read(FRONTEND_ROOT / ".dockerignore")

    assert backend_ignore.lstrip().startswith("#")
    assert "\n**\n" in backend_ignore
    for prohibited in ("**/.env", "**/.env.*", "**/__pycache__/", "**/*.log"):
        assert prohibited in backend_ignore
    assert "!testing/database_guard.py" in backend_ignore
    assert "!testing/**" not in backend_ignore

    assert "\n**\n" in frontend_ignore
    for prohibited in (
        "**/node_modules/",
        "**/.next/",
        "**/tests/",
        "**/.env",
        "**/.env.*",
    ):
        assert prohibited in frontend_ignore


def test_application_images_use_numeric_non_root_users() -> None:
    for path in (BACKEND_ROOT / "Dockerfile", FRONTEND_ROOT / "Dockerfile"):
        dockerfile = _read(path)
        assert "USER 10001:10001" in dockerfile
        assert dockerfile.index("USER 10001:10001") < dockerfile.index("CMD [")


def test_compose_hardens_both_application_services() -> None:
    compose = _read(REPOSITORY_ROOT / "docker-compose.yml")

    assert compose.count("privileged: false") == 2
    assert compose.count("read_only: true") == 2
    assert compose.count("no-new-privileges:true") == 2
    assert compose.count("cap_drop:") == 2
    assert compose.count("- ALL") == 2
    assert "/app/.lumina_conversations" in compose
    assert "/app/runtime-logs" in compose
    assert "/app/.next/cache" in compose


def test_healthchecks_and_commands_use_exec_form() -> None:
    backend = _read(BACKEND_ROOT / "Dockerfile")
    frontend = _read(FRONTEND_ROOT / "Dockerfile")

    assert 'CMD ["gunicorn"' in backend
    assert 'CMD ["node", "node_modules/next/dist/bin/next", "start"]' in frontend
    assert 'CMD ["curl"' in backend
    assert 'CMD ["wget"' in frontend
