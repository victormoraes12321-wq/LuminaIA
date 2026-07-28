from __future__ import annotations

import socket
from collections.abc import Callable
from typing import Any

from testing.database_guard import TestDatabaseTarget, resolve_allowed_test_addresses


class ExternalNetworkBlockedError(ConnectionError):
    """Raised when a test attempts to reach a non-allowlisted network target."""


def install_external_network_guard(
    target: TestDatabaseTarget,
) -> Callable[[], None]:
    """Block non-loopback sockets for the lifetime of the pytest process."""

    original_connect = socket.socket.connect
    allowed_addresses = resolve_allowed_test_addresses(target)

    def guarded_connect(sock: socket.socket, address: Any) -> Any:
        host = address[0] if isinstance(address, tuple) and address else address
        normalized = str(host or "").lower().strip("[]").split("%", 1)[0]
        if normalized in {"localhost", *allowed_addresses}:
            return original_connect(sock, address)
        try:
            resolved = {
                str(item[4][0]).split("%", 1)[0]
                for item in socket.getaddrinfo(
                    normalized,
                    address[1] if isinstance(address, tuple) and len(address) > 1 else 0,
                    type=socket.SOCK_STREAM,
                )
            }
        except OSError:
            resolved = set()
        if resolved and resolved.issubset(allowed_addresses):
            return original_connect(sock, address)
        raise ExternalNetworkBlockedError(
            f"Rede externa bloqueada durante teste (componente tentou acessar host nao autorizado: {normalized})."
        )

    socket.socket.connect = guarded_connect

    def restore() -> None:
        socket.socket.connect = original_connect

    return restore
