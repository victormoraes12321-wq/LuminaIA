"""
LuminaAI — Business Relationship ORM Model
-------------------------------------------
Modelo que define relacionamentos e influências de causa e efeito entre indicadores.
Permite à IA e ao validador compreender dependências conceituais por tenant.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

if TYPE_CHECKING:
    from models.tenant import Tenant


class BusinessRelationship(Base):
    """
    Representa uma relação conceitual entre indicadores de negócio.
    """

    __tablename__ = "business_relationships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único da relação.",
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Isolamento multi-tenant.",
    )

    origem_nome: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Métrica/KPI influenciador (ex: receita_total).",
    )

    destino_nome: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Métrica/KPI influenciado (ex: lucro_bruto).",
    )

    tipo_relacao: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="INFLUENCIA",
        comment="Tipo de relação: INFLUENCIA, DEPENDE, COMPLEMENTA.",
    )

    descricao: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Explicação de causa e efeito da relação.",
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

    # ── Relacionamentos ─────────────────────────────────────────────
    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<BusinessRelationship {self.origem_nome} -> ({self.tipo_relacao}) -> {self.destino_nome}>"
