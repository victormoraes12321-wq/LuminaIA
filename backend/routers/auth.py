"""
LuminaAI — Rotas de Autenticação
--------------------------------
Endpoints para login e alteração de senha inicial obrigatória.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from config import settings
from models.user import User
from routers.dependencies import AUTH_COOKIE_NAME, get_current_user
from schemas.user import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
)
from services.auth_service import (
    create_access_token,
    get_password_hash,
    verify_password,
)

logger = logging.getLogger("luminaai.routers.auth")


def _set_auth_cookie(response: Response, access_token: str) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
    )

router = APIRouter(
    prefix="/auth",
    tags=["🔑 Autenticação"],
)


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Login de Usuário",
    description="Autentica o usuário pelo e-mail e senha. Suporta e-mails idênticos em tenants diferentes escolhendo o correspondente ao password correto.",
)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> LoginResponse:
    """
    Realiza o login do usuário verificando e-mail e senha.
    Retorna o Token JWT e a flag se ele precisa resetar a senha.
    """
    # Busca todos os usuários com o email fornecido (devido a restrição Unique email + tenant_id)
    stmt = select(User).where(User.email == payload.email)
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    if not users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos.",
        )
        
    # Encontra o usuário cujo password bate com o hash cadastrado
    authenticated_user: User | None = None
    for u in users:
        if verify_password(payload.password, u.password_hash):
            authenticated_user = u
            break
            
    if authenticated_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos.",
        )
        
    # Valida status do usuário
    if not authenticated_user.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo. Contate o administrador do sistema.",
        )
        
    # Atualiza a data de último acesso do usuário
    authenticated_user.ultimo_acesso = datetime.now(timezone.utc)
    db.add(authenticated_user)
    
    # Gera o Token JWT
    token_data = {
        "sub": str(authenticated_user.id),
        "tenant_id": str(authenticated_user.tenant_id),
        "role": authenticated_user.role.value,
        "must_change_password": authenticated_user.must_change_password,
        "nome": authenticated_user.nome,
        "email": authenticated_user.email
    }
    
    access_token = create_access_token(data=token_data)
    if request.headers.get("origin") or request.headers.get("x-lumina-cookie-auth") == "1":
        _set_auth_cookie(response, access_token)
    
    logger.info(
        "Usuário autenticado com sucesso: email=%s | tenant=%s | role=%s",
        authenticated_user.email,
        str(authenticated_user.tenant_id)[:8],
        authenticated_user.role.value
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        must_change_password=authenticated_user.must_change_password,
    )


@router.get(
    "/session",
    status_code=status.HTTP_200_OK,
    summary="Sessao autenticada",
)
async def get_session(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str | bool]:
    """Retorna a identidade da sessao sem expor novamente o JWT ao browser."""
    return {
        "id": str(current_user.id),
        "nome": current_user.nome,
        "email": current_user.email,
        "role": current_user.role.value,
        "tenant_id": str(current_user.tenant_id),
        "must_change_password": current_user.must_change_password,
    }


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Encerrar sessao",
)
async def logout(response: Response) -> dict[str, bool]:
    """Remove o cookie HttpOnly de autenticacao."""
    _clear_auth_cookie(response)
    return {"success": True}


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Alteração de Senha Obrigatória",
    description="Permite que qualquer usuário logado (mesmo com must_change_password = True) altere sua senha e desative o bloqueio.",
)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict[str, str | bool]:
    """
    Altera a senha do usuário autenticado no banco de dados.
    Muda a flag must_change_password para False.
    """
    # 1. Valida se a senha atual confere
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha atual incorreta.",
        )
        
    # 2. Impede definir a mesma senha
    if payload.old_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A nova senha não pode ser idêntica à senha atual.",
        )
        
    # 3. Faz o hash da nova senha e atualiza o banco
    current_user.password_hash = get_password_hash(payload.new_password)
    current_user.must_change_password = False
    
    db.add(current_user)
    
    logger.info("Senha redefinida com sucesso para o usuário: email=%s", current_user.email)
    
    return {
        "success": True,
        "message": "Senha alterada com sucesso. Bloqueio de primeiro acesso removido."
    }
