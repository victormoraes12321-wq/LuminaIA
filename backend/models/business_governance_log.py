"""
LuminaAI — Business Governance Log ORM Model
----------------------------------------------
Modelo de log de auditoria, versionamento e aprovações para governança da Business Layer.
Armazena snapshots completos para suporte a rollback.
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


class BusinessGovernanceLog(Base):
    """
    Registra histórico de alterações, snapshots de versão e rollbacks.
    """

    __tablename__ = "business_governance_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único do log.",
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Isolamento multi-tenant.",
    )

    estrutura_tipo: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Tipo da estrutura alterada: CONCEPT, KPI, FORMULA, RELATIONSHIP.",
    )

    estrutura_nome: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Nome do elemento alterado.",
    )

    versao: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Versão gravada na alteração.",
    )

    autor: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Email do autor da alteração.",
    )

    acao: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Ação: CREATE, UPDATE, ROLLBACK, DEPRECATE.",
    )

    alteracoes: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Diferença JSON contendo campos alterados.",
    )

    status_aprovacao: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="APPROVED",
        comment="Status de aprovação: APPROVED, PENDING, REJECTED.",
    )

    snapshot: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Snapshot completo do objeto na versão indicada para rollback.",
    )

    criado_em: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relacionamentos ─────────────────────────────────────────────
    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<BusinessGovernanceLog structure={self.estrutura_nome} action={self.acao} version={self.versao}>"
