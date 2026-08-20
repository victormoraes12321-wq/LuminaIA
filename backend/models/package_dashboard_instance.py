"""
LuminaAI — Package Dashboard Instance ORM Model
-------------------------------------------------
Representa um snapshot de execução de um Analytical Package.

Cada vez que um Package é reutilizado, uma nova PackageDashboardInstance
é criada com o payload de dashboard, datasets e resultados analíticos
daquela execução específica, com seus parâmetros e timestamp.

Isso permite:
- Histórico completo de execuções por Package
- Comparação temporal de dashboards
- Auditoria de frescor dos dados (data freshness)
- Cache de longo prazo de instâncias anteriores
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Float
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

if TYPE_CHECKING:
    from models.analytical_package import AnalyticalPackage
    from models.tenant import Tenant


class PackageDashboardInstance(Base):
    """
    Snapshot de uma execução de um Analytical Package.

    Criada tanto na primeira execução (MISS no Package Layer) quanto
    em cada reuso subsequente (HIT no Package Layer com dados novos).

    Preserva o estado completo de uma renderização de dashboard,
    permitindo auditoria histórica e cache de longo prazo.
    """

    __tablename__ = "package_dashboard_instances"

    # ── Identidade ─────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único desta instância de execução.",
    )

    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analytical_packages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Package ao qual esta instância pertence.",
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Isolamento por tenant.",
    )

    # ── Payload da Execução ─────────────────────────────────────────
    dashboard_payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment=(
            "Payload de dashboard completo desta execução, "
            "pronto para ser consumido pelo Frontend Inteligente."
        ),
    )

    datasets_snapshot: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment=(
            "Snapshot dos datasets analíticos desta execução. "
            "Incluindo schema, dados brutos e metadados."
        ),
    )

    analytics_snapshot: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment=(
            "Snapshot dos resultados analíticos: KPIs calculados, "
            "tendências, comparações e estatísticas descritivas."
        ),
    )

    bi_intelligence_snapshot: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Snapshot dos resultados da BI Intelligence desta execução.",
    )

    # ── Parâmetros e Contexto da Execução ──────────────────────────
    query_params: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment=(
            "Parâmetros usados nesta execução: date_range, filtros "
            "de produto/cliente/região, etc."
        ),
    )

    intent_fingerprint_used: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Fingerprint de intenção que disparou esta execução.",
    )

    pergunta_original: Mapped[str | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Pergunta original do usuário que gerou esta instância.",
    )

    # ── Métricas de Execução ────────────────────────────────────────
    execution_time_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Tempo total de execução desta instância em milissegundos.",
    )

    was_package_reuse: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="True se foi um reuso de Package (HIT). False se foi primeira criação (MISS).",
    )

    compatibility_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
        comment="Score de compatibilidade que levou ao reuso (1.0 para criação inicial).",
    )

    # ── Data Freshness ───────────────────────────────────────────────
    data_freshness_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp de quando os dados desta instância foram gerados na Data Platform.",
    )

    # ── Timestamps ──────────────────────────────────────────────────
    criado_em: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relacionamentos ─────────────────────────────────────────────
    package: Mapped[AnalyticalPackage] = relationship(
        "AnalyticalPackage",
        back_populates="instances",
        lazy="select",
    )

    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<PackageDashboardInstance id={self.id!s:.8} "
            f"package={self.package_id!s:.8} "
            f"reuse={self.was_package_reuse} "
            f"time={self.execution_time_ms}ms>"
        )
