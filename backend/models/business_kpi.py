"""
LuminaAI — Business KPI ORM Model
----------------------------------
Modelo que representa o registro oficial de KPIs corporativos.
Contém fórmulas, benchmarks, limites operacionais e tags de negócio por tenant.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, Integer, Float
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

if TYPE_CHECKING:
    from models.tenant import Tenant


class BusinessKPI(Base):
    """
    Representa um KPI (Key Performance Indicator) oficial corporativo.
    """

    __tablename__ = "business_kpis"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único do KPI.",
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
        comment="Nome único do KPI (ex: LTV, CAC).",
    )

    descricao: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Descrição detalhada do KPI.",
    )

    categoria: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Geral",
        comment="Categoria do KPI (ex: Financeiro, Operações).",
    )

    area: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Geral",
        comment="Área corporativa beneficiada.",
    )

    objetivo: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Objetivo estratégico do indicador.",
    )

    formula_oficial: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Fórmula oficial expressa em termos corporativos.",
    )

    periodicidade: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Mensal",
        comment="Periodicidade típica de cálculo (Diário, Semanal, Mensal).",
    )

    formato: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="number",
        comment="Formato de exibição: currency, percentage, integer, float.",
    )

    precisao: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
        comment="Casas decimais sugeridas.",
    )

    unidade: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="",
        comment="Unidade de medida (BRL, %, un, etc.).",
    )

    limites: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Limites aceitáveis para o valor (min, max).",
    )

    faixas: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Faixas de coloração/performance (verde, amarelo, vermelho).",
    )

    benchmark: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Meta oficial e benchmarks externos.",
    )

    responsavel: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Gestor",
        comment="Responsável pelo monitoramento deste KPI.",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ACTIVE",
        comment="Status do KPI: ACTIVE, DEPRECATED, DRAFT.",
    )

    versao: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Versão do KPI para governança e rollback.",
    )

    tags: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Tags de busca associadas.",
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
        return f"<BusinessKPI nome={self.nome!r} versao={self.versao} status={self.status}>"
