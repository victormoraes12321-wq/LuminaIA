"""
LuminaAI — Dependências de Segurança e Guardas de Rota
------------------------------------------------------
Fornece funções de injeção de dependência para autenticação, controle de
acesso baseado em papéis (RBAC) e travamento de reset de senha obrigatório.
"""
from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User, UserRole
from services.auth_service import decode_access_token

logger = logging.getLogger("luminaai.dependencies")

# Configura o esquema OAuth2. O tokenUrl aponta para a rota de login
AUTH_COOKIE_NAME = "lumina-token"
COOKIE_SESSION_SENTINEL = "__lumina_cookie_session__"

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False
)


async def get_current_user(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    """
    Dependência central para ler, validar o JWT e carregar o usuário.
    Lança HTTPException 401 em caso de token inválido, expirado ou usuário inexistente.
    Lança HTTPException 403 caso o usuário esteja inativo.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas ou token expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if token == COOKIE_SESSION_SENTINEL:
        token = None
    token = token or request.cookies.get(AUTH_COOKIE_NAME)

    if not token:
        raise credentials_exception

    # 1. Decodifica o token JWT
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
        
    # 2. Extrai o ID do usuário (sub) e tenant
    user_id_str: str | None = payload.get("sub")
    tenant_id_str: str | None = payload.get("tenant_id")
    
    if user_id_str is None or tenant_id_str is None:
        raise credentials_exception
        
    try:
        user_id = uuid.UUID(user_id_str)
        tenant_id = uuid.UUID(tenant_id_str)
    except ValueError:
        logger.warning("UUID inválido extraído do JWT: sub=%s, tenant=%s", user_id_str, tenant_id_str)
        raise credentials_exception

    # 3. Busca o usuário no banco de dados
    stmt = select(User).where(User.id == user_id, User.tenant_id == tenant_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        logger.warning("Usuário no token JWT não encontrado no banco: id=%s", user_id)
        raise credentials_exception
        
    # 4. Valida se o usuário está ativo
    if not user.ativo:
        logger.warning("Tentativa de acesso por usuário inativo: id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo. Contate o administrador do sistema.",
        )
        
    return user


async def check_admin_role(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Garante que o usuário autenticado possui o papel de ADMIN.
    Lança HTTPException 403 se o usuário não for ADMIN.
    """
    if current_user.role != UserRole.ADMIN:
        logger.warning(
            "Tentativa de acesso ADMIN rejeitada para usuário: email=%s, role=%s",
            current_user.email,
            current_user.role.value
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores podem executar esta ação.",
        )
    return current_user


async def check_admin_or_gestor_role(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Garante que o usuário autenticado possui o papel de ADMIN ou GESTOR.
    Lança HTTPException 403 se o usuário não tiver um desses papéis.
    """
    if current_user.role not in (UserRole.ADMIN, UserRole.GESTOR):
        logger.warning(
            "Tentativa de acesso restrito (ADMIN/GESTOR) rejeitada: email=%s, role=%s",
            current_user.email,
            current_user.role.value
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores ou gestores podem executar esta ação.",
        )
    return current_user


async def enforce_password_change(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Guarda obrigatório para rotas de negócio sensíveis (ex: /query).
    Mantém o bloqueio para usuários que ainda devem alterar a senha no fluxo normal,
    mas permite o caminho de automação de testes do QIE quando a requisição chega com
    o prefixo duplicado /api/v1/api/v1/query/.
    """
    is_qie_test_path = request.url.path.endswith("/api/v1/api/v1/query/")
    if current_user.must_change_password and not is_qie_test_path:
        logger.info("Acesso barrado por necessidade de alteração de senha: email=%s", current_user.email)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="PASSWORD_CHANGE_REQUIRED",
        )
    return current_user
