from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, String, Text, Integer, Float
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

if TYPE_CHECKING:
    from models.tenant import Tenant


class Blueprint(Base):
    """
    Blueprint Inteligente armazenado no repositório de blueprints da Data Platform.
    Guarda as estratégias de visualização, layouts, configurações e versionamento.
    """

    __tablename__ = "blueprint_repository"

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
    
    intent_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    
    nome_consulta: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    objetivo: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    
    tipo_analise: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="AGGREGATION",
    )
    
    view_catalog_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    
    view_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    metrics: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    
    group_by: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    
    filters: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    
    visualization_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="TABLE",
    )
    
    layout: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    
    exemplos_perguntas: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Enterprise identity and marketplace metadata
    categoria: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Geral",
    )

    dominio_negocio: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="GERAL",
    )

    area: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Geral",
    )

    tags: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    autor: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="IA",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ACTIVE",
        index=True,
    )

    marketplace_scope: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="TENANT",
    )

    is_marketplace: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    fingerprint: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    fingerprint_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="",
        index=True,
    )

    identity: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    business_intent: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    semantic_context: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    business_context: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    kpi_strategy: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    visualization_strategy: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    component_strategy: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    filter_strategy: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    grouping_strategy: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    navigation_strategy: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    dashboard_template_reference: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    metadata_info: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    dependencies_map: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    version_info: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    performance_profile: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    quality_profile: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    health_profile: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    
    # Versionamento / metadados do Blueprint
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    
    dependencias: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    
    permissoes: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    
    # Audit fields
    quantidade_utilizacoes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    
    tempo_acumulado_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    
    tempo_ia_acumulado_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    
    tokens_economizados: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    
    ultima_utilizacao: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
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
