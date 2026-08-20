from __future__ import annotations

import uuid
from datetime import datetime, date, time
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String, Integer, Numeric, Date, Time, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

if TYPE_CHECKING:
    from models.tenant import Tenant


class SyncQueue(Base):
    """
    Representa a fila e o histórico operacional de sincronizações da Data Platform (Sync Engine).
    Registra os metadados de execuções em andamento e finalizadas.
    """

    __tablename__ = "sync_queue"

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

    data_execucao: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        default=func.current_date(),
    )

    hora_execucao: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        default=func.current_time(),
    )

    status: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="PENDING", # PENDING, RUNNING, SUCCESS, FAILED
        index=True,
    )

    tempo_duracao_ms: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0.0,
    )

    quantidade_views: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    quantidade_registros: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    resultado: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    erros: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    avisos: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    criado_em: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
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

    def __repr__(self) -> str:
        return (
            f"<SyncQueue id={self.id!s:.8} tenant_id={self.tenant_id!s:.8} "
            f"status={self.status!r} views={self.quantidade_views}>"
        )
