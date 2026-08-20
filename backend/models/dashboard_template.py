from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

if TYPE_CHECKING:
    from models.tenant import Tenant
    from models.user import User
    from models.dashboard_instance import DashboardInstance
    from models.dashboard_studio_version import DashboardStudioVersion


class DashboardTemplate(Base):
    """
    Persistent visual contract for a dashboard.

    Templates store only layout and presentation strategy. They never store ERP
    data, calculated KPI values, formulas or query definitions.
    """

    __tablename__ = "dashboard_templates"

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

    blueprint_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Read-only reference to the analytical Blueprint.",
    )

    analytical_package_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Read-only reference to an Analytical Package.",
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="CUSTOM")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    layout: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    grid: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    components: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    component_order: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    groups: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    tabs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    sections: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    responsive: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    theme: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    visual_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    default_state: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    available_components: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    permissions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

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
    author: Mapped[User | None] = relationship("User", lazy="select")
    instances: Mapped[list[DashboardInstance]] = relationship(
        "DashboardInstance",
        back_populates="template",
        cascade="all, delete-orphan",
        lazy="select",
    )
    versions: Mapped[list[DashboardStudioVersion]] = relationship(
        "DashboardStudioVersion",
        back_populates="template",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="DashboardStudioVersion.version.desc()",
    )

    def __repr__(self) -> str:
        return f"<DashboardTemplate id={str(self.id)[:8]} name={self.name!r} version={self.version}>"
