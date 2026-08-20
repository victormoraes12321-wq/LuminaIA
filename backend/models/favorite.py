"""
LuminaAI — Model ORM: Favorite

Consultas salvas pelos usuários para re-execução rápida.
O usuário pode personalizar o título e os parâmetros são persistidos
para reproduzir exatamente a mesma consulta no futuro.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

if TYPE_CHECKING:
    from models.user import User
    from models.view_catalog import ViewCatalog


class Favorite(Base):
    """
    Análise favoritada por um usuário com parâmetros persistidos.

    A constraint UNIQUE (user_id, view_catalog_id) garante que um usuário
    não pode favoritar a mesma view duas vezes — porém pode ter múltiplos
    favoritos de views diferentes, cada um com seus próprios parâmetros_salvos.
    """

    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "view_catalog_id", name="uq_favorites_user_view"
        ),
    )

    # ── Primary Key ───────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── Foreign Keys ──────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    view_catalog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("view_catalog.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Personalização ────────────────────────────────────────
    titulo_personalizado: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment=(
            "Título customizado pelo usuário. "
            "Se nulo, o frontend usa o nome da view como título."
        ),
    )
    parametros_salvos: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Snapshot dos parâmetros da consulta original para re-execução fiel",
    )

    # ── Timestamp ─────────────────────────────────────────────
    criado_em: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relacionamentos ───────────────────────────────────────
    user: Mapped[User] = relationship(
        "User",
        back_populates="favorites",
        lazy="select",
    )
    view_catalog: Mapped[ViewCatalog] = relationship(
        "ViewCatalog",
        back_populates="favorites",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<Favorite id={self.id!s:.8} "
            f"user_id={self.user_id!s:.8} view_id={self.view_catalog_id!s:.8}>"
        )
