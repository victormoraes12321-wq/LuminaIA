"""
LuminaAI — Business Formula ORM Model
--------------------------------------
Modelo que representa a biblioteca de fórmulas analíticas parametrizadas.
Contém parâmetros de entrada, saídas, pré-requisitos e validações matemáticas por tenant.
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


class BusinessFormula(Base):
    """
    Representa uma fórmula de cálculo corporativa oficial.
    """

    __tablename__ = "business_formulas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único da fórmula.",
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
        comment="Nome único da fórmula (ex: ROI, CAC).",
    )

    formula: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Expressão matemática ou lógica executável (ex: '(ganho - investimento) / investimento').",
    )

    entradas: Mapped[list[dict]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Parâmetros de entrada requeridos: nome, tipo, opcional.",
    )

    saidas: Mapped[list[dict]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Outputs gerados pela fórmula: nome, tipo.",
    )

    pre_requisitos: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Pré-requisitos analíticos (ex: 'investimento > 0').",
    )

    dependencias: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Métodos ou variáveis necessárias para o cálculo.",
    )

    validacoes: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Expressões extras de validação (ex: ['lucro != 0']).",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ACTIVE",
        comment="Status da fórmula: ACTIVE, DEPRECATED, DRAFT.",
    )

    versao: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Versão da fórmula para governança e rollback.",
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
        return f"<BusinessFormula nome={self.nome!r} versao={self.versao} status={self.status}>"
