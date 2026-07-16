from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String, Text, Integer, Boolean, Numeric
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

if TYPE_CHECKING:
    from models.tenant import Tenant
    from models.metadata_catalog import MetadataCatalog


class MetadataCatalogVersion(Base):
    """
    Snapshot imutável de uma versão do MetadataCatalog.
    Permite auditoria, histórico completo e rollback estrutural.
    Nunca é sobrescrito — apenas criado.
    """

    __tablename__ = "metadata_catalog_versions"

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

    metadata_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metadata_catalog.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    versao: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    autor: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    motivo: Mapped[str | None] = mapped_column(
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

    def __repr__(self) -> str:
        return (
            f"<MetadataCatalogVersion id={self.id!s:.8} "
            f"metadata_id={self.metadata_id!s:.8} versao={self.versao}>"
        )
