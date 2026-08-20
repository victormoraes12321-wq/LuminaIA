import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String, Integer, Numeric
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

if TYPE_CHECKING:
    from models.tenant import Tenant


class SemanticMemory(Base):
    """
    Semantic Memory — Repositório de Memória Semântica Corporativa.
    Armazena resoluções de expressões coloquiais para IDs corporativos estáveis,
    permitindo aprendizado contínuo e consultas super rápidas sem invocar IA.
    """

    __tablename__ = "semantic_memory"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    expressao: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )

    objeto_resolvido: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    score: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=100.0,
    )

    criado_em: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    blueprint_associado: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    frequencia: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    confianca: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ALTA",
    )

    origem: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="IA",
    )

    # Relacionamento de Tenant
    tenant: Mapped["Tenant"] = relationship(back_populates="semantic_memories" if hasattr(Base, "semantic_memories") else None)
