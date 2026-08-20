from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String, Text, Integer, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

if TYPE_CHECKING:
    from models.tenant import Tenant


class SVRConcept(Base):
    """
    SVRConcept — Cadastro corporativo de conceitos versionados no SVR.
    Identifica cada conceito corporativo rastreável na plataforma.
    """

    __tablename__ = "svr_concepts"

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

    concept_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    concept_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,  # Ex: METRIC, KPI, DIMENSION, BLUEPRINT, DASHBOARD, etc.
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ACTIVE",
        index=True,  # ACTIVE, LEGACY, DEPRECATED, OBSOLETE
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


class SVRVersion(Base):
    """
    SVRVersion — Snapshots imutáveis de cada versão do conceito.
    Guarda o estado exato de cada versão (semântica, mapeamento ou blueprint).
    """

    __tablename__ = "svr_versions"

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

    concept_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    semantic_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="1.0",
    )

    mapping_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="1",
    )

    blueprint_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    autor: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="SYSTEM",
    )

    motivo: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    impacto: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    criado_em: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        lazy="select",
    )


class SVRCompatibilityMatrix(Base):
    """
    SVRCompatibilityMatrix — Matriz de Compatibilidade Oficial do SVR.
    Define as relações válidas e vigências das versões de negócios e físicas.
    """

    __tablename__ = "svr_compatibility_matrix"

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

    concept_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    semantic_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    mapping_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    blueprint_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ACTIVE",
        index=True,  # ACTIVE, LEGACY, DEPRECATED, OBSOLETE
    )

    data_vigencia: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    data_expiracao: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    motivo_alteracao: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    impacto: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    objetos_dependentes: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,  # IDs de Blueprints ou Dashboards afetados
    )

    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        lazy="select",
    )


class SVRAuditLog(Base):
    """
    SVRAuditLog — Log de Auditoria de Evolução Conceitual.
    Histórico completo das mudanças de versão no SVR para fins de conformidade e governança.
    """

    __tablename__ = "svr_audit_logs"

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

    concept_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    action_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,  # REGISTER, DEPRECATE, MIGRATE, STATUS_CHANGE
    )

    versao_anterior: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    versao_nova: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    motivo: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    usuario: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="SYSTEM",
    )

    criado_em: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    detalhes: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        lazy="select",
    )
