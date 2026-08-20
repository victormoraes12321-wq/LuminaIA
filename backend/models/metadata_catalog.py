from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String, Integer, Numeric, Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

if TYPE_CHECKING:
    from models.tenant import Tenant


class MetadataCatalog(Base):
    """
    Metadata Catalog — Centro de Governança da Data Platform.
    Registra, organiza, monitora e disponibiliza todas as informações estruturais
    da plataforma analítica (Views, Blueprints, Datasets, KPIs, Dashboards).
    """

    __tablename__ = "metadata_catalog"

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

    # ── Identificação ─────────────────────────────────────────────────────

    nome_view: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    tipo_estrutura: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="VIEW",
        index=True,
    )

    estrutura_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
        index=True,
    )

    origem: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="ERP_ORACLE",
    )

    owner: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
    )

    categoria: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Geral",
    )

    tags: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    blueprint_associado: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    dashboard_associado: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # ── Estrutura ─────────────────────────────────────────────────────────

    tabelas_utilizadas: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    campos_utilizados: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    relacionamentos: Mapped[list[dict]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    filtros_padrao: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    periodos_suportados: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    kpis_suportados: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    dependencias: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # ── Data Lineage & Dependency Graph ───────────────────────────────────

    lineage: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    dependencias_grafo: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # ── Health Monitor Scores (0–100) ─────────────────────────────────────

    health_score: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=100.0,
    )

    integrity_score: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=100.0,
    )

    performance_score: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=100.0,
    )

    freshness_score: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=100.0,
    )

    usage_score: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=0.0,
    )

    alertas: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # ── Cache ─────────────────────────────────────────────────────────────

    cache_ativo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    cache_atualizado_em: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    cache_ttl_segundos: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3600,
    )

    cache_hit_rate: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=0.0,
    )

    # ── Versionamento ─────────────────────────────────────────────────────

    versao: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    status: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="success",
    )

    integridade: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="valid",
    )

    hash_integridade: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="",
    )

    # ── Sincronização ─────────────────────────────────────────────────────

    ultima_sincronizacao: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    proxima_sincronizacao: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    duracao_ultima_sync_ms: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0.0,
    )

    registros_ultima_sync: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    erros_sync: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # ── Métricas de uso & Performance ─────────────────────────────────────

    quantidade_consultas: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    quantidade_usuarios: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    ultima_utilizacao: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    tempo_medio_atualizacao: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0.0,
    )

    tempo_medio_execucao: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0.0,
    )

    # ── Timestamps ────────────────────────────────────────────────────────

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

    # ── Relationships ─────────────────────────────────────────────────────

    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        lazy="select",
    )
