"""
LuminaAI — Business Concept ORM Model
--------------------------------------
Modelo que representa os conceitos oficiais de negócio do Dicionário Corporativo.
Centraliza as definições de termos empresariais com isolamento por tenant.
"""
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


class BusinessConcept(Base):
    """
    Representa um termo ou conceito de negócio oficial no dicionário corporativo.
    """

    __tablename__ = "business_concepts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único do conceito.",
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Isolamento multi-tenant.",
    )

    nome: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Nome único do conceito por tenant.",
    )

    descricao: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Descrição detalhada do conceito.",
    )

    categoria: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Geral",
        comment="Categoria do conceito.",
    )

    area: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Geral",
        comment="Área corporativa (ex: Vendas, Marketing).",
    )

    departamento: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Geral",
        comment="Departamento responsável.",
    )

    definicao_oficial: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Definição corporativa formal do termo.",
    )

    unidade: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="",
        comment="Unidade de medida padrão.",
    )

    tipo: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Métrica",
        comment="Tipo do conceito: Métrica, Dimensão, Fato, etc.",
    )

    origem: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Manual",
        comment="Origem (ERP, CRM, Planilha, Manual).",
    )

    owner: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Negócio",
        comment="Responsável pelo conceito (Dono do produto/área).",
    )

    versao: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Versão do conceito para governança e rollback.",
    )

    sinonimos: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Sinônimos aceitos para mapeamento dinâmico.",
    )

    abreviacoes: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Abreviações comuns.",
    )

    exemplos: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Exemplos de aplicação prática.",
    )

    observacoes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Observações adicionais.",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ACTIVE",
        comment="Status do conceito: ACTIVE, DEPRECATED, DRAFT.",
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
        return f"<BusinessConcept nome={self.nome!r} versao={self.versao} status={self.status}>"
