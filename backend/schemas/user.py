"""
LuminaAI — Schemas Pydantic v2: User

Validação de dados de entrada e saída para operações de User.
Senhas são aceitas apenas na criação e nunca expostas nas respostas.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from models.user import UserRole


class UserBase(BaseModel):
    """Campos comuns para criação e atualização de User."""

    nome: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Nome completo do usuário",
        examples=["João da Silva"],
    )
    email: EmailStr = Field(
        ...,
        description="Email de acesso (único por tenant)",
        examples=["joao.silva@empresa.com.br"],
    )
    role: UserRole = Field(
        default=UserRole.CONSULTA,
        description="Papel de acesso: ADMIN | GESTOR | CONSULTA",
    )


class UserCreate(UserBase):
    """Schema para criação de novo usuário."""

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Senha em plaintext (será hashada com bcrypt antes de salvar)",
        examples=["SenhaSegura@2024"],
    )


class UserUpdate(BaseModel):
    """Schema para atualização parcial de usuário."""

    nome: str | None = Field(None, min_length=2, max_length=255)
    email: EmailStr | None = Field(None, description="Email de acesso (único por tenant)")
    role: UserRole | None = None
    ativo: bool | None = None
    password: str | None = Field(None, min_length=8, max_length=128)


class UserResponse(UserBase):
    """Schema de resposta seguro — nunca expõe password_hash."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Identificador único do usuário")
    tenant_id: uuid.UUID = Field(description="Tenant ao qual o usuário pertence")
    ativo: bool = Field(description="Status de ativação da conta")
    must_change_password: bool = Field(
        description="Flag indicando se o usuário precisa mudar a senha"
    )
    ultimo_acesso: datetime | None = Field(
        default=None, description="Timestamp do último login"
    )
    criado_em: datetime = Field(description="Data de criação da conta")


class UserPublic(BaseModel):
    """Versão mínima do usuário para respostas onde apenas identidade é necessária."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    email: EmailStr
    role: UserRole
    tenant_id: uuid.UUID


class LoginRequest(BaseModel):
    """Corpo de requisição de login."""

    email: EmailStr = Field(..., description="E-mail de acesso do usuário")
    password: str = Field(..., description="Senha em texto plano")


class LoginResponse(BaseModel):
    """Resposta de login bem-sucedido com token JWT."""

    access_token: str = Field(..., description="Token de acesso JWT")
    token_type: str = Field(default="bearer", description="Tipo do token de acesso")
    must_change_password: bool = Field(
        ...,
        description="Se True, o usuário deve trocar de senha imediatamente",
    )


class ChangePasswordRequest(BaseModel):
    """Corpo de requisição para alteração de senha."""

    old_password: str = Field(..., description="Senha antiga/atual em texto plano")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Nova senha (mínimo de 8 caracteres)",
        examples=["NovaSenhaSegura@2026"],
    )


class UserCreateAdmin(BaseModel):
    """Schema para o administrador cadastrar novos usuários."""

    nome: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Nome completo do usuário",
        examples=["Maria da Silva"],
    )
    email: EmailStr = Field(
        ...,
        description="Email de acesso (único por tenant)",
        examples=["maria.silva@empresa.com.br"],
    )
    role: UserRole = Field(
        default=UserRole.CONSULTA,
        description="Papel do usuário: ADMIN | GESTOR | CONSULTA",
    )
    tenant_id: uuid.UUID = Field(
        ...,
        description="ID do Tenant que o usuário pertencerá",
    )


class UserCreateAdminResponse(BaseModel):
    """Resposta de usuário criado com sucesso com a senha temporária gerada."""

    user: UserResponse = Field(..., description="Dados do usuário criado")
    temp_password: str = Field(
        ...,
        description="Senha temporária em texto plano para ser fornecida ao usuário",
    )
