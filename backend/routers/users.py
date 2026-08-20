"""
LuminaAI — Rotas de Gerenciamento de Usuários
--------------------------------------------
Endpoints para gerenciamento de usuários. O cadastro é restrito
exclusivamente para administradores autenticados.
"""
from __future__ import annotations

import logging
import secrets
import string
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Response

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


from database import get_db
from models.tenant import Tenant
from models.user import User
from routers.dependencies import check_admin_role, enforce_password_change
from schemas.user import (
    UserCreateAdmin,
    UserCreateAdminResponse,
    UserResponse,
    UserUpdate,
)
from services.auth_service import get_password_hash

logger = logging.getLogger("luminaai.routers.users")

router = APIRouter(
    prefix="/users",
    tags=["👤 Usuários"],
    dependencies=[Depends(enforce_password_change)],
)


def _generate_secure_password(length: int = 16) -> str:
    """
    Gera uma senha temporária segura de alta entropia.
    Contém pelo menos uma letra maiúscula, uma minúscula, um dígito e um caractere especial.
    """
    upper = string.ascii_uppercase
    lower = string.ascii_lowercase
    digits = string.digits
    special = "!@#$%^&*"
    all_chars = upper + lower + digits + special
    
    # Garante a presença de todos os tipos de caracteres
    password = [
        secrets.choice(upper),
        secrets.choice(lower),
        secrets.choice(digits),
        secrets.choice(special)
    ]
    
    # Preenche o restante do comprimento
    password += [secrets.choice(all_chars) for _ in range(length - 4)]
    
    # Mistura os caracteres de forma segura
    secrets.SystemRandom().shuffle(password)
    
    return "".join(password)


@router.post(
    "/",
    response_model=UserCreateAdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar Novo Usuário (Admin-Only)",
    description=(
        "Cadastra um novo usuário no sistema. Requer permissão de ADMIN. "
        "Uma senha forte de 16 caracteres é gerada automaticamente pelo backend "
        "e retornada em plaintext nesta resposta para repasse ao novo usuário. "
        "O usuário nascerá com must_change_password = True."
    ),
)
async def create_user_by_admin(
    payload: UserCreateAdmin,
    _admin_user: Annotated[User, Depends(check_admin_role)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> UserCreateAdminResponse:
    """
    Endpoint para que o administrador crie usuários dentro de um Tenant específico.
    Gera senha temporária de forma automática e segura.
    """
    # Segurança: Impede que o administrador do Tenant A crie usuários no Tenant B
    if _admin_user.tenant_id != payload.tenant_id:
        logger.warning(
            "Tentativa ilegal de criação cross-tenant bloqueada: admin_tenant=%s | target_tenant=%s",
            _admin_user.tenant_id,
            payload.tenant_id
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Você só pode criar usuários pertencentes à sua própria empresa.",
        )

    # 1. Verifica se o tenant_id de destino realmente existe no banco
    stmt_tenant = select(Tenant).where(Tenant.id == payload.tenant_id)
    res_tenant = await db.execute(stmt_tenant)
    tenant = res_tenant.scalar_one_or_none()
    
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="O Tenant informado não foi encontrado.",
        )
        
    # 2. Verifica se já existe um usuário com o mesmo e-mail no mesmo tenant
    stmt_user = select(User).where(
        User.email == payload.email,
        User.tenant_id == payload.tenant_id
    )
    res_user = await db.execute(stmt_user)
    existing_user = res_user.scalar_one_or_none()
    
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Um usuário com este e-mail já está cadastrado neste Tenant.",
        )
        
    # 3. Gera a senha temporária em plaintext e seu hash
    temp_password = _generate_secure_password(16)
    password_hash = get_password_hash(temp_password)
    
    # 4. Cria e persiste o novo usuário no PostgreSQL
    new_user = User(
        nome=payload.nome,
        email=payload.email,
        role=payload.role,
        tenant_id=payload.tenant_id,
        password_hash=password_hash,
        must_change_password=True,  # Força alteração no primeiro acesso
        ativo=True,
    )
    
    db.add(new_user)
    await db.flush()  # Executa a query para gerar o ID do usuário sem commitar a transação inteira
    
    logger.info(
        "Novo usuário criado pelo Administrador: email=%s | tenant=%s | role=%s",
        new_user.email,
        str(new_user.tenant_id)[:8],
        new_user.role.value
    )
    
    # 5. Monta a resposta de sucesso injetando a senha em texto plano
    user_response = UserResponse.model_validate(new_user)
    
    # Commita as alterações do novo usuário
    await db.commit()
    
    return UserCreateAdminResponse(
        user=user_response,
        temp_password=temp_password,
    )


@router.get(
    "/",
    response_model=list[UserResponse],
    summary="Listar Todos os Usuários do Tenant (Admin-Only)",
    description="Retorna a lista completa de usuários cadastrados no tenant do administrador autenticado.",
)
async def list_users(
    current_user: Annotated[User, Depends(check_admin_role)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> list[UserResponse]:
    """
    Retorna a lista de usuários associados ao mesmo tenant do administrador logado.
    """
    stmt = select(User).where(User.tenant_id == current_user.tenant_id).order_by(User.criado_em.desc())
    res = await db.execute(stmt)
    users = res.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Deletar Usuário (Admin-Only)",
    description="Remove permanentemente um usuário do banco de dados, exceto o próprio administrador logado.",
)
async def delete_user(
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(check_admin_role)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Response:
    """
    Permite que o administrador exclua um usuário específico do seu tenant.
    Impede a auto-exclusão do próprio usuário logado para evitar lockouts.
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é permitido deletar a sua própria conta de administrador.",
        )
        
    stmt = select(User).where(User.id == user_id, User.tenant_id == current_user.tenant_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado ou não pertence ao seu Tenant.",
        )
        
    await db.delete(user)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)



@router.put(
    "/{user_id}/toggle-active",
    response_model=UserResponse,
    summary="Ativar/Desativar Usuário (Admin-Only)",
    description="Alterna o status ativo (true/false) de um usuário específico.",
)
async def toggle_user_active(
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(check_admin_role)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> UserResponse:
    """
    Permite ativar ou suspender contas de usuários.
    Impede que o administrador desative a si próprio.
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é permitido desativar a sua própria conta de administrador.",
        )
        
    stmt = select(User).where(User.id == user_id, User.tenant_id == current_user.tenant_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado ou não pertence ao seu Tenant.",
        )
        
    user.ativo = not user.ativo
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Editar Usuário (Admin-Only)",
    description="Atualiza informações de um usuário existente (nome, email, role, ativo, password).",
)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    current_user: Annotated[User, Depends(check_admin_role)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> UserResponse:
    """
    Permite atualizar dados de um usuário (nome, email, papel, ativo, senha).
    Garante integridade e regras de negócio do tenant.
    """
    # 1. Busca o usuário
    stmt = select(User).where(User.id == user_id, User.tenant_id == current_user.tenant_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado ou não pertence ao seu Tenant.",
        )
        
    # 2. Se e-mail foi fornecido e é diferente, verifica colisão
    if payload.email is not None and payload.email != user.email:
        stmt_email = select(User).where(
            User.email == payload.email,
            User.tenant_id == current_user.tenant_id,
            User.id != user_id
        )
        res_email = await db.execute(stmt_email)
        colliding_user = res_email.scalar_one_or_none()
        if colliding_user is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Um usuário com este e-mail já está cadastrado neste Tenant.",
            )
        user.email = payload.email

    # 3. Atualiza campos
    if payload.nome is not None:
        user.nome = payload.nome
        
    if payload.role is not None:
        # Não permite que o admin altere seu próprio papel para evitar perda de acesso
        if user_id == current_user.id and payload.role != current_user.role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é permitido alterar o seu próprio papel de acesso.",
            )
        user.role = payload.role
        
    if payload.ativo is not None:
        if user_id == current_user.id and not payload.ativo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é permitido desativar a sua própria conta.",
            )
        user.ativo = payload.ativo
        
    if payload.password is not None and payload.password.strip() != "":
        user.password_hash = get_password_hash(payload.password)
        
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)

