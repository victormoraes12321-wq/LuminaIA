from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

if TYPE_CHECKING:
    from models.dashboard_template import DashboardTemplate
    from models.dashboard_studio_version import DashboardStudioVersion
    from models.tenant import Tenant
    from models.user import User


class DashboardInstance(Base):
    """
    User-specific dashboard state.

    Instances can override visual preferences and current UI state, but never
    mutate the original template or analytical logic.
    """

    __tablename__ = "dashboard_instances"

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

    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dashboard_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE", index=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    current_filters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    expanded_components: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    panel_positions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    favorites: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    visible_columns: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    sort_orders: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    preferences: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    current_state: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    layout_override: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    atualizado_em: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    criado_em: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    tenant: Mapped[Tenant] = relationship("Tenant", lazy="select")
    user: Mapped[User] = relationship("User", lazy="select")
    template: Mapped[DashboardTemplate] = relationship(
        "DashboardTemplate",
        back_populates="instances",
        lazy="select",
    )
    versions: Mapped[list[DashboardStudioVersion]] = relationship(
        "DashboardStudioVersion",
        back_populates="instance",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="DashboardStudioVersion.version.desc()",
    )

    def __repr__(self) -> str:
        return f"<DashboardInstance id={str(self.id)[:8]} template={str(self.template_id)[:8]} version={self.version}>"
