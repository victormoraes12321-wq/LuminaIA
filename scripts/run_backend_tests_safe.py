from __future__ import annotations

import argparse
import asyncio
import os
import socket
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DEFAULT_TEST_DATABASE_URL = (
    "postgresql+asyncpg://lumina_test:lumina_test"
    "@127.0.0.1:55432/luminaai_test"
)


def _configure_test_environment() -> None:
    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault("LUMINA_TESTING", "true")
    os.environ.setdefault("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
    os.environ["SECRET_KEY"] = "test-secret-key-only-32-characters-minimum"
    os.environ["ENCRYPTION_KEY"] = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
    os.environ["OPENAI_API_KEY"] = "sk-test-not-a-real-openai-credential-000000000000"
    os.environ["MOCK_ORACLE"] = "true"
    os.environ["MOCK_OPENAI"] = "true"
    os.environ["LUMINA_DISABLE_EXTERNAL_NETWORK"] = "true"
    os.environ["NEW_PIPELINE_ACTIVE"] = "false"
    os.environ["ENABLE_DETERMINISTIC_PIPELINE"] = "false"
    os.environ["DB_ECHO"] = "false"


def _load_guard():
    sys.path.insert(0, str(BACKEND))
    try:
        from testing.database_guard import validate_test_database_environment
    except ImportError as exc:
        raise RuntimeError(
            "Dependencias do backend ausentes. Execute o runner com o Python do ambiente virtual do projeto."
        ) from exc
    return validate_test_database_environment


def _wait_for_tcp(host: str, port: int, timeout_seconds: float = 30.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError(
        "PostgreSQL descartavel indisponivel. Execute "
        "'docker compose -f docker-compose.test.yml up -d --wait'."
    )


async def _prepare_database() -> None:
    from database import engine
    from testing.database_guard import guard_engine_before_write
    from testing.test_database import bootstrap_test_database, reset_and_seed_test_database

    await guard_engine_before_write(engine)
    await bootstrap_test_database(engine)
    await reset_and_seed_test_database(engine)
    await engine.dispose()


def _selection_args(selection: str) -> list[str]:
    return {
        "all": [],
        "unit": ["-m", "unit"],
        "baseline": ["-m", "baseline"],
        "security": ["-m", "security"],
        "multitenant": ["-m", "multitenant"],
        "ai-mock": ["-m", "ai_mock"],
        "oracle-mock": ["-m", "oracle_mock"],
        "guard": ["tests/test_test_database_guard.py"],
    }[selection]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Executa pytest somente contra PostgreSQL descartavel validado."
    )
    parser.add_argument(
        "--selection",
        choices=(
            "all",
            "unit",
            "baseline",
            "security",
            "multitenant",
            "ai-mock",
            "oracle-mock",
            "guard",
        ),
        default="all",
    )
    parser.add_argument(
        "--guard-only",
        action="store_true",
        help="Valida somente URL/ambiente; nao abre conexao nem executa pytest.",
    )
    parser.add_argument(
        "--",
        dest="pytest_args",
        nargs=argparse.REMAINDER,
        default=[],
        help="Argumentos adicionais repassados ao pytest.",
    )
    args, extra_args = parser.parse_known_args()

    _configure_test_environment()
    validate_environment = _load_guard()
    target = validate_environment()
    print(
        f"Guard aprovado: PostgreSQL de teste local ({target.host}:{target.port}/{target.database})."
    )
    if args.guard_only:
        return 0

    if args.selection != "guard":
        _wait_for_tcp(target.host, target.port)
        asyncio.run(_prepare_database())

    pytest_command = [
        sys.executable,
        "-m",
        "pytest",
        "-ra",
        *_selection_args(args.selection),
        *extra_args,
    ]
    result = subprocess.run(
        pytest_command,
        cwd=BACKEND,
        env=os.environ.copy(),
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
