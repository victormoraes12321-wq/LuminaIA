from __future__ import annotations

import json
import logging
from typing import Any

from cryptography.fernet import Fernet

from config import settings


logger = logging.getLogger("luminaai.services.connection_credentials")


def decrypt_connection_details(connection: dict[str, Any] | str) -> dict[str, Any]:
    """Decrypt a tenant-owned database connection payload."""
    if not connection:
        raise ValueError("Dados de conexao nao fornecidos ou vazios.")

    if isinstance(connection, str):
        try:
            connection = json.loads(connection)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Dados de conexao invalidos ou mal estruturados.") from exc

    if not isinstance(connection, dict):
        raise ValueError("Dados de conexao invalidos ou mal estruturados.")

    if not connection.get("encrypted", True):
        logger.warning("Credenciais em plaintext habilitadas para desenvolvimento.")
        payload_data = connection.get("payload")
        if isinstance(payload_data, dict):
            return payload_data
        if isinstance(payload_data, str):
            try:
                decoded = json.loads(payload_data)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "Payload de conexao nao criptografado invalido."
                ) from exc
            if isinstance(decoded, dict):
                return decoded
        raise ValueError("Payload de conexao nao criptografado invalido.")

    payload = connection.get("payload")
    if not isinstance(payload, str) or not payload:
        raise ValueError("Carga criptografada ausente nas credenciais do tenant.")

    try:
        cipher = Fernet(settings.ENCRYPTION_KEY.encode("utf-8"))
        decrypted = cipher.decrypt(payload.encode("utf-8")).decode("utf-8")
        details = json.loads(decrypted)
        if not isinstance(details, dict):
            raise ValueError("Payload descriptografado nao e um objeto.")
        return details
    except Exception as exc:
        logger.error(
            "Falha ao descriptografar credenciais do tenant: %s",
            type(exc).__name__,
        )
        raise ValueError(
            "Chave de criptografia invalida ou payload de conexao corrompido."
        ) from exc
