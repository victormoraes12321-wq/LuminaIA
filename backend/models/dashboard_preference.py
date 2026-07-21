from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from database import Base


class DashboardPreference(Base):
    """Preferencias persistidas de resposta/dashboard por usuario e tenant."""

    __tablename__ = "dashboard_preferences"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "user_id",
            "scope",
            name="uq_dashboard_preferences_tenant_user_scope",
        ),
    )

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
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        default="default",
    )
    basis: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="liquido",
    )
    format: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="tabela",
    )
    instructions: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
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
