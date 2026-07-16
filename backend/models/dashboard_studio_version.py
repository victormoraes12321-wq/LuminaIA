from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

if TYPE_CHECKING:
    from models.dashboard_instance import DashboardInstance
    from models.dashboard_template import DashboardTemplate
    from models.tenant import Tenant
    from models.user import User


class DashboardStudioVersion(Base):
    """Immutable version snapshot for Dashboard Studio templates and instances."""

    __tablename__ = "dashboard_studio_versions"
    __table_args__ = (
        CheckConstraint(
            "(template_id IS NOT NULL AND instance_id IS NULL) OR "
            "(template_id IS NULL AND instance_id IS NOT NULL)",
            name="ck_dashboard_studio_version_single_target",
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

    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dashboard_templates.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    instance_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dashboard_instances.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    target_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    tenant: Mapped[Tenant] = relationship("Tenant", lazy="select")
    author: Mapped[User | None] = relationship("User", lazy="select")
    template: Mapped[DashboardTemplate | None] = relationship(
        "DashboardTemplate",
        back_populates="versions",
        lazy="select",
    )
    instance: Mapped[DashboardInstance | None] = relationship(
        "DashboardInstance",
        back_populates="versions",
        lazy="select",
    )

    def __repr__(self) -> str:
        target_id = self.template_id or self.instance_id
        return f"<DashboardStudioVersion target={str(target_id)[:8]} version={self.version}>"
