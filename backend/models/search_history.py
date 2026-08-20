"""
LuminaAI — Model ORM: SearchHistory

Auditoria completa de todas as consultas realizadas no sistema.
Permite análise de uso, melhoria do catálogo e debug do Motor de Intenções.
O view_catalog_id é nullable: nulo quando a IA não identifica a intenção.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

if TYPE_CHECKING:
    from models.user import User
    from models.view_catalog import ViewCatalog


class SearchHistory(Base):
    """
    Registro imutável de cada consulta realizada no LuminaAI.

    Este model NÃO possui campo atualizado_em pois registros de histórico
    são append-only — nunca devem ser modificados após criação.

    Campos de análise:
        ia_confianca: Score retornado pelo LLM (0.0 = sem match, 1.0 = certeza)
        tempo_resposta_ms: Latência total (IA + geração de dados + overhead HTTP)
    """

    __tablename__ = "search_history"
    __table_args__ = (
        CheckConstraint(
            "ia_confianca IS NULL OR (ia_confianca >= 0 AND ia_confianca <= 1)",
            name="chk_sh_confianca_range",
        ),
        CheckConstraint(
            "tempo_resposta_ms IS NULL OR tempo_resposta_ms >= 0",
            name="chk_sh_tempo_positivo",
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
    view_catalog_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("view_catalog.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Nulo quando a IA não identificou nenhuma view correspondente",
    )

    # ── Dados da Consulta ─────────────────────────────────────
    pergunta_texto: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Pergunta original do usuário em linguagem natural",
    )
    parametros_extraidos: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Parâmetros identificados pela IA: datas, filtros, dimensões",
    )

    # ── Métricas da IA ────────────────────────────────────────
    ia_confianca: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
        comment="Score de confiança do matching (0.0000 a 1.0000)",
    )
    tempo_resposta_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Latência total da requisição em milissegundos",
    )

    # ── Timestamp (append-only) ───────────────────────────────
    criado_em: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relacionamentos ───────────────────────────────────────
    user: Mapped[User] = relationship(
        "User",
        back_populates="search_history",
        lazy="select",
    )
    view_catalog: Mapped[ViewCatalog | None] = relationship(
        "ViewCatalog",
        back_populates="search_history",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<SearchHistory id={self.id!s:.8} "
            f"user_id={self.user_id!s:.8} confianca={self.ia_confianca}>"
        )
