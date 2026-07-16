"""
LuminaAI — Model ORM: User + Enum UserRole

Representa um usuário autenticado do sistema, sempre vinculado a um tenant.
O sistema implementa RBAC (Role-Based Access Control) com 3 níveis de acesso.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

if TYPE_CHECKING:
    from models.tenant import Tenant
    from models.favorite import Favorite
    from models.search_history import SearchHistory


class UserRole(str, enum.Enum):
    """
    Papéis de acesso dos usuários no LuminaAI.

    ADMIN:    Acesso total — gerencia tenant, usuários, catálogo e histórico geral.
    GESTOR:   Gerencia catálogo de views e visualiza histórico de toda a equipe.
    CONSULTA: Apenas executa consultas e gerencia seus próprios favoritos.
    """

    ADMIN = "ADMIN"
    GESTOR = "GESTOR"
    CONSULTA = "CONSULTA"


class User(Base):
    """
    Usuário autenticado do LuminaAI, isolado por tenant.
    Email é único dentro de um mesmo tenant (não globalmente).
    """

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", "tenant_id", name="uq_users_email_per_tenant"),
    )

    # ── Primary Key ───────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── Foreign Key ───────────────────────────────────────────
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Dados Pessoais ────────────────────────────────────────
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Email único por tenant — não é único globalmente",
    )

    # ── Segurança ─────────────────────────────────────────────
    password_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Hash bcrypt da senha — nunca armazenar senha em plaintext",
    )

    # ── RBAC ──────────────────────────────────────────────────
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", create_type=False),
        nullable=False,
        default=UserRole.CONSULTA,
    )

    # ── Status ────────────────────────────────────────────────
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    must_change_password: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Se True, exige que o usuário altere a senha no próximo acesso",
    )
    ultimo_acesso: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Timestamp do último login bem-sucedido",
    )

    # ── Timestamps ────────────────────────────────────────────
    criado_em: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ── Relacionamentos ───────────────────────────────────────
    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        back_populates="users",
        lazy="select",
    )
    search_history: Mapped[list[SearchHistory]] = relationship(
        "SearchHistory",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
    favorites: Mapped[list[Favorite]] = relationship(
        "Favorite",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<User id={self.id!s:.8} email={self.email!r} role={self.role.value}>"
        )
