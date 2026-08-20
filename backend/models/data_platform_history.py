from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

if TYPE_CHECKING:
    from models.tenant import Tenant


class DataPlatformHistory(Base):
    """
    Registro histórico operacional e estrutural de evolução da Data Platform (audit trail).
    """

    __tablename__ = "data_platform_history"

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
    
    estrutura_tipo: Mapped[str] = mapped_column(
        String(100), # 'VIEW', 'BLUEPRINT', 'DATASET', 'METADADOS'
        nullable=False,
    )
    
    estrutura_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    acao: Mapped[str] = mapped_column(
        String(100), # 'CREATE', 'UPDATE', 'RECONSTRUCT', 'VERSION_UP'
        nullable=False,
    )
    
    detalhes: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
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
            f"<DataPlatformHistory id={self.id!s:.8} "
            f"tipo={self.estrutura_tipo!r} acao={self.acao!r}>"
        )
