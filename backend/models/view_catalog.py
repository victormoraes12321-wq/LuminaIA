"""
LuminaAI — Model ORM: ViewCatalog + Enum ChartType

Catálogo de views Oracle disponíveis para consulta por tenant.
Cada view possui uma descrição semântica que é injetada no prompt da IA
para que o Motor de Intenções identifique a view correta.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

if TYPE_CHECKING:
    from models.tenant import Tenant
    from models.favorite import Favorite
    from models.search_history import SearchHistory


class ChartType(str, enum.Enum):
    """
    Tipos de componentes visuais suportados pelo LuminaAI.

    Cada tipo determina o formato dos dados retornados ao frontend
    e o componente de visualização a ser renderizado.
    """

    BAR = "BAR"         # Gráfico de barras (vertical/horizontal)
    LINE = "LINE"       # Gráfico de linhas (série temporal)
    PIE = "PIE"         # Gráfico de pizza / donut chart
    TABLE = "TABLE"     # Tabela de dados paginada com colunas tipadas
    KPI = "KPI"         # Painel de KPIs executivos com trends
    KPI_CARD = "KPI_CARD"  # Alias do KPI Card (compatibilidade com novo pipeline)
    AREA = "AREA"       # Gráfico de área (linha com preenchimento)
    SCATTER = "SCATTER" # Gráfico de dispersão (scatter plot)
    HEATMAP = "HEATMAP" # Mapa de calor
    TREEMAP = "TREEMAP" # Treemap hierárquico
    FUNNEL = "FUNNEL"   # Funil de conversão
    DONUT = "DONUT"     # Gráfico donut


class ViewCatalog(Base):
    """
    View Oracle registrada no catálogo do tenant.

    A descricao_para_ia é o campo mais crítico: deve ser detalhada e
    semântica o suficiente para que o LLM identifique corretamente
    a intenção do usuário e mapeie para esta view.
    """

    __tablename__ = "view_catalog"
    __table_args__ = (
        UniqueConstraint(
            "nome_view_oracle", "tenant_id", name="uq_view_catalog_nome_per_tenant"
        ),
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

    # ── Identificação da View ─────────────────────────────────
    nome_view_oracle: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Nome exato da view no banco Oracle (ex: VW_VENDAS_MENSAIS)",
    )
    descricao_para_ia: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "Descrição semântica detalhada injetada no prompt do LLM. "
            "Deve incluir: propósito, métricas, dimensões, casos de uso e sinônimos."
        ),
    )

    # ── Configuração Visual ───────────────────────────────────
    tipo_grafico_padrao: Mapped[ChartType] = mapped_column(
        Enum(ChartType, name="chart_type", create_type=False),
        nullable=False,
        default=ChartType.BAR,
        comment="Componente visual padrão para renderização dos dados desta view",
    )

    # ── Schema de Parâmetros ──────────────────────────────────
    parametros_schema: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment=(
            "Schema JSON dos parâmetros aceitos pela view. "
            "Formato: {campo: {type, required, description, example}}"
        ),
    )

    # ── Status ────────────────────────────────────────────────
    ativo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Views inativas não aparecem no catálogo da IA",
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
        back_populates="view_catalog",
        lazy="select",
    )
    search_history: Mapped[list[SearchHistory]] = relationship(
        "SearchHistory",
        back_populates="view_catalog",
        lazy="select",
    )
    favorites: Mapped[list[Favorite]] = relationship(
        "Favorite",
        back_populates="view_catalog",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<ViewCatalog id={self.id!s:.8} "
            f"nome={self.nome_view_oracle!r} tipo={self.tipo_grafico_padrao.value}>"
        )
