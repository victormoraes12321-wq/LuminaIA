"""
LuminaAI — Model ORM: Tenant

Representa uma empresa cliente do sistema (multi-tenant SaaS).
Cada tenant possui seu próprio catálogo de views, usuários e configurações.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

if TYPE_CHECKING:
    from models.user import User
    from models.view_catalog import ViewCatalog
    from models.semantic_memory import SemanticMemory


class Tenant(Base):
    """
    Empresa cliente do LuminaAI.

    Campos JSONB:
        tema_config: Configurações visuais (cores, fontes, dark mode)
        ia_config: Configurações de IA (modelo, temperatura, instruções customizadas)
        oracle_conn: Dados de conexão Oracle criptografados com Fernet
    """

    __tablename__ = "tenants"

    # ── Primary Key ───────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único do tenant (UUID v4)",
    )

    # ── Dados Básicos ─────────────────────────────────────────
    nome: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Razão social ou nome fantasia da empresa",
    )
    logo_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="URL da logo da empresa para exibição no frontend",
    )

    # ── Configurações JSON ────────────────────────────────────
    tema_config: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Configurações de tema: primary_color, dark_mode, font_family, border_radius",
    )
    ia_config: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Config de IA: model, temperature, max_tokens, custom_instructions",
    )
    oracle_conn: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Conexão Oracle criptografada com Fernet: {encrypted, algorithm, payload}",
    )
    clone_db_conn: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Conexão PostgreSQL do Clone criptografada com Fernet: {encrypted, algorithm, payload}",
    )
    sync_config: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Configurações de sincronização: {enabled, times, last_sync, last_sync_status, last_sync_message}",
    )

    # ── Status ────────────────────────────────────────────────
    ativo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Indica se o tenant está ativo no sistema",
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
    users: Mapped[list[User]] = relationship(
        "User",
        back_populates="tenant",
        cascade="all, delete-orphan",
        lazy="select",
    )
    view_catalog: Mapped[list[ViewCatalog]] = relationship(
        "ViewCatalog",
        back_populates="tenant",
        cascade="all, delete-orphan",
        lazy="select",
    )
    semantic_memories: Mapped[list[SemanticMemory]] = relationship(
        "SemanticMemory",
        back_populates="tenant",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id!s:.8} nome={self.nome!r} ativo={self.ativo}>"
