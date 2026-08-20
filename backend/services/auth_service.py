"""
LuminaAI — Serviço de Autenticação e Criptografia
--------------------------------------------------
Responsável pelo gerenciamento de hashes de senha (Bcrypt) e emissão/validação
de tokens JSON Web Tokens (JWT) utilizando PyJWT.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from jwt import InvalidTokenError

from config import settings

logger = logging.getLogger("luminaai.services.auth")


def get_password_hash(password: str) -> str:
    """
    Gera o hash Bcrypt de uma senha em texto plano de forma segura.
    Utiliza diretamente a biblioteca bcrypt para contornar problemas de compatibilidade
    do passlib com versões recentes do Python/bcrypt.
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compara uma senha em texto plano com o hash Bcrypt armazenado.
    Retorna True se forem correspondentes, caso contrário False.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception as exc:
        logger.error("Erro durante verificação de hash Bcrypt: %s", exc)
        return False



def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None
) -> str:
    """
    Gera um token JWT com base nos dados do payload fornecidos.
    
    Payload deve incluir obrigatoriamente:
      - sub (ID do usuário)
      - tenant_id (ID do tenant)
      - role (Papel de acesso)
      - must_change_password (Flag de reset de senha)
      
    O token expira após o tempo definido em expires_delta ou default (30 minutos).
    """
    to_encode = data.copy()
    
    # Define o tempo de expiração do Token
    if expires_delta is not None:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
    # Converte UUIDs para string para garantir serialização no JWT
    for key, value in to_encode.items():
        if isinstance(value, uuid.UUID):
            to_encode[key] = str(value)
            
    # Adiciona expiração e emissão ao payload
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any] | None:
    """
    Decodifica e valida o token JWT usando a chave secreta e algoritmo definidos.
    Retorna o dicionário de claims (payload) ou None em caso de token inválido ou expirado.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except InvalidTokenError as exc:
        logger.warning("Falha na decodificação do JWT: %s", exc)
        return None
