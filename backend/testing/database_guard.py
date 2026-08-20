from __future__ import annotations

import ipaddress
import os
import re
import socket
from dataclasses import dataclass
from typing import Any, Mapping

from sqlalchemy import text
from sqlalchemy.engine import URL, make_url


class TestDatabaseGuardError(RuntimeError):
    """Raised before SQL when the target cannot be proven disposable."""


@dataclass(frozen=True)
class TestDatabaseTarget:
    host: str
    port: int
    database: str
    driver: str


_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
_DEFAULT_COMPOSE_HOSTS = {
    "lumina-test-postgres",
    "lumina_test_postgres",
    "postgres-test",
}
_FORBIDDEN_DATABASES = {
    "postgres",
    "luminaai",
    "lumina",
    "luminaai_clone",
    "lumina_clone",
}
_TEST_DATABASE_RE = re.compile(r"(?:^|_)test(?:_|$)", re.IGNORECASE)
_WORKER_DATABASE_RE = re.compile(
    r"^luminaai_test(?:_(?:gw\d+|worker\d+|[a-z0-9]+))?$",
    re.IGNORECASE,
)


def _is_truthy(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _safe_error(reason: str) -> TestDatabaseGuardError:
    return TestDatabaseGuardError(f"Banco de teste recusado: {reason}.")


def _parse_url(raw_url: str | None) -> URL:
    if not raw_url or not raw_url.strip():
        raise _safe_error("TEST_DATABASE_URL ausente")
    try:
        return make_url(raw_url)
    except Exception as exc:
        raise _safe_error("TEST_DATABASE_URL invalida") from exc


def _normalized_host(host: str | None) -> str:
    return str(host or "").strip().lower().strip("[]")


def _allowed_compose_hosts(env: Mapping[str, str]) -> set[str]:
    configured = {
        item.strip().lower()
        for item in env.get("LUMINA_TEST_DB_HOST_ALLOWLIST", "").split(",")
        if item.strip()
    }
    return _DEFAULT_COMPOSE_HOSTS | configured


def _is_loopback(host: str) -> bool:
    if host in _LOCAL_HOSTS:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _target_identity(url: URL) -> tuple[str, int, str]:
    return (
        _normalized_host(url.host),
        int(url.port or 5432),
        str(url.database or "").strip().lower(),
    )


def _validate_database_name(database: str, env: Mapping[str, str]) -> None:
    normalized = database.strip().lower()
    forbidden = _FORBIDDEN_DATABASES | {
        item.strip().lower()
        for item in env.get("LUMINA_OPERATIONAL_DATABASE_NAMES", "").split(",")
        if item.strip()
    }
    if not normalized:
        raise _safe_error("nome do banco ausente")
    if normalized in forbidden:
        raise _safe_error("nome de banco operacional ou padrao")
    if not _TEST_DATABASE_RE.search(normalized):
        raise _safe_error("nome do banco sem marcador de teste")
    if not _WORKER_DATABASE_RE.fullmatch(normalized):
        raise _safe_error("nome do banco fora do padrao descartavel")


def validate_test_database_url(
    test_database_url: str | None,
    *,
    environment: str | None,
    testing_enabled: str | bool | None,
    operational_database_url: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> TestDatabaseTarget:
    """Validate a test URL without opening a connection or exposing credentials."""

    env = environ or os.environ
    if str(environment or "").strip().lower() != "test":
        raise _safe_error("ENVIRONMENT deve ser test")
    if not _is_truthy(testing_enabled):
        raise _safe_error("LUMINA_TESTING deve estar habilitado")

    url = _parse_url(test_database_url)
    driver = str(url.drivername or "").lower()
    if driver.startswith("oracle"):
        raise _safe_error("Oracle nao e permitido em testes")
    if not driver.startswith("postgresql"):
        raise _safe_error("somente PostgreSQL descartavel e permitido")

    host = _normalized_host(url.host)
    compose_hosts = _allowed_compose_hosts(env)
    if not host:
        raise _safe_error("host ausente")
    if not _is_loopback(host) and host not in compose_hosts:
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            raise _safe_error("host externo ou corporativo nao autorizado") from None
        if not address.is_loopback:
            raise _safe_error("IP publico ou nao autorizado")

    port = int(url.port or 5432)
    if _is_loopback(host) and port == 5432:
        raise _safe_error("porta operacional 5432 nao e permitida em loopback")

    database = str(url.database or "")
    _validate_database_name(database, env)

    if operational_database_url:
        try:
            operational_url = make_url(operational_database_url)
        except Exception:
            operational_url = None
        if operational_url is not None and _target_identity(url) == _target_identity(operational_url):
            raise _safe_error("destino igual ao DATABASE_URL operacional")

    return TestDatabaseTarget(
        host=host,
        port=port,
        database=database,
        driver=driver,
    )


def validate_staging_database_url(
    database_url: str | None,
    *,
    environment: str | None,
    environ: Mapping[str, str] | None = None,
) -> TestDatabaseTarget:
    """Validate a dedicated staging database target for controlled migration bootstrap."""
    env = environ or os.environ
    normalized_env = str(environment or "").strip().lower()
    if normalized_env == "production":
        raise _safe_error("ENVIRONMENT de producao e estritamente proibido para bootstrap automatico")
    if normalized_env != "staging":
        raise _safe_error("ENVIRONMENT deve ser staging para bootstrap de pre-producao")

    url = _parse_url(database_url)
    driver = str(url.drivername or "").lower()
    if driver.startswith("oracle"):
        raise _safe_error("Oracle nao e permitido em staging analitico")
    if not driver.startswith("postgresql"):
        raise _safe_error("somente PostgreSQL e permitido para staging")

    host = _normalized_host(url.host)
    if not host:
        raise _safe_error("host de staging ausente")

    if not _is_loopback(host):
        try:
            address = ipaddress.ip_address(host)
            if not (address.is_loopback or address.is_private):
                raise _safe_error("host de staging deve ser local ou rede privada")
        except ValueError:
            # Hostname resolution check
            pass

    port = int(url.port or 5432)
    database = str(url.database or "").strip().lower()
    if not database:
        raise _safe_error("nome do banco de staging ausente")
    if database in _FORBIDDEN_DATABASES:
        raise _safe_error("nome de banco padrao do sistema nao e permitido")

    allowed_staging_dbs = {"lumina_preprod", "lumina_staging"} | {
        item.strip().lower()
        for item in env.get("LUMINA_STAGING_DATABASE_ALLOWLIST", "").split(",")
        if item.strip()
    }
    if database not in allowed_staging_dbs and not database.endswith("_preprod") and not database.endswith("_staging"):
        raise _safe_error(f"banco '{database}' fora da allowlist de staging ({sorted(allowed_staging_dbs)})")

    return TestDatabaseTarget(
        host=host,
        port=port,
        database=database,
        driver=driver,
    )


def validate_test_database_url(
    test_database_url: str | None,
    *,
    environment: str | None,
    testing_enabled: str | bool | None,
    operational_database_url: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> TestDatabaseTarget:
    """Validate a test URL without opening a connection or exposing credentials."""

    env = environ or os.environ
    if str(environment or "").strip().lower() != "test":
        raise _safe_error("ENVIRONMENT deve ser test")
    if not _is_truthy(testing_enabled):
        raise _safe_error("LUMINA_TESTING deve estar habilitado")

    url = _parse_url(test_database_url)
    driver = str(url.drivername or "").lower()
    if driver.startswith("oracle"):
        raise _safe_error("Oracle nao e permitido em testes")
    if not driver.startswith("postgresql"):
        raise _safe_error("somente PostgreSQL descartavel e permitido")

    host = _normalized_host(url.host)
    compose_hosts = _allowed_compose_hosts(env)
    if not host:
        raise _safe_error("host ausente")
    if not _is_loopback(host) and host not in compose_hosts:
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            raise _safe_error("host externo ou corporativo nao autorizado") from None
        if not address.is_loopback:
            raise _safe_error("IP publico ou nao autorizado")

    port = int(url.port or 5432)
    if _is_loopback(host) and port == 5432:
        raise _safe_error("porta operacional 5432 nao e permitida em loopback")

    database = str(url.database or "")
    _validate_database_name(database, env)

    if operational_database_url:
        try:
            operational_url = make_url(operational_database_url)
        except Exception:
            operational_url = None
        if operational_url is not None and _target_identity(url) == _target_identity(operational_url):
            raise _safe_error("destino igual ao DATABASE_URL operacional")

    return TestDatabaseTarget(
        host=host,
        port=port,
        database=database,
        driver=driver,
    )


def validate_test_database_environment(
    environ: Mapping[str, str] | None = None,
) -> TestDatabaseTarget:
    env = environ or os.environ
    current_env = str(env.get("ENVIRONMENT") or "").strip().lower()
    is_staging_bootstrap = (
        _is_truthy(env.get("LUMINA_STAGING_BOOTSTRAP"))
        or str(env.get("LUMINA_MIGRATION_MODE") or "").strip().lower() in {"staging_bootstrap", "staging"}
    )
    if current_env == "staging" and is_staging_bootstrap:
        return validate_staging_database_url(
            env.get("DATABASE_URL"),
            environment=current_env,
            environ=env,
        )
    return validate_test_database_url(
        env.get("TEST_DATABASE_URL"),
        environment=env.get("ENVIRONMENT"),
        testing_enabled=env.get("LUMINA_TESTING"),
        operational_database_url=env.get("DATABASE_URL"),
        environ=env,
    )


def resolve_allowed_test_addresses(target: TestDatabaseTarget) -> set[str]:
    addresses = {"127.0.0.1", "::1"}
    try:
        for item in socket.getaddrinfo(target.host, target.port, type=socket.SOCK_STREAM):
            addresses.add(str(item[4][0]).split("%", 1)[0])
    except OSError:
        pass
    return addresses


async def validate_connected_test_database(
    connection: Any,
    expected: TestDatabaseTarget,
) -> None:
    """Verify the connected PostgreSQL target before reset, seed, or DDL."""

    result = await connection.execute(
        text(
            """
            SELECT
                current_database() AS database_name,
                COALESCE(host(inet_server_addr()), '') AS server_address,
                inet_server_port() AS server_port
            """
        )
    )
    row = result.mappings().one()
    actual_database = str(row["database_name"] or "")
    if actual_database.lower() != expected.database.lower():
        raise _safe_error("current_database diverge da URL validada")
    _validate_database_name(actual_database, os.environ)

    server_address = str(row["server_address"] or "")
    if server_address:
        try:
            address = ipaddress.ip_address(server_address.split("%", 1)[0])
        except ValueError as exc:
            raise _safe_error("endereco do servidor conectado e invalido") from exc
        if not (address.is_loopback or address.is_private):
            raise _safe_error("servidor PostgreSQL conectado nao e local ou privado")


async def guard_engine_before_write(engine: Any) -> TestDatabaseTarget:
    target = validate_test_database_environment()
    async with engine.connect() as connection:
        await validate_connected_test_database(connection, target)
    return target
