from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, Integer
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

if TYPE_CHECKING:
    from models.tenant import Tenant


class SemanticCatalog(Base):
    """
    Semantic Catalog (Catálogo Semântico).
    Fonte oficial e única de significado, regras, formatações e relacionamentos das métricas corporativas.
    """

    __tablename__ = "semantic_catalog"

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
    
    nome_oficial: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    
    descricao: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    
    sinonimos: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    
    categoria: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Geral",
    )
    
    tipo: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Fato",
    )
    
    unidade: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="",
    )
    
    formato: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="number",
    )
    
    metodo_agregacao: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Soma",
    )
    
    contexto: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    kpis_relacionados: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    
    indicadores_derivados: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    
    visualizacoes_recomendadas: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    
    restricoes: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    
    permissoes: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    
    versao: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    
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
    
    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<SemanticCatalog id={self.id!s:.8} "
            f"nome={self.nome_oficial!r} versao={self.versao}>"
        )
