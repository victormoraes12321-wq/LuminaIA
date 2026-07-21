from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


DashboardBasis = Literal["liquido", "bruto", "ambos"]
DashboardFormat = Literal["tabela", "grafico", "ambos"]


class DashboardPreferenceUpdate(BaseModel):
    basis: DashboardBasis = "liquido"
    format: DashboardFormat = "tabela"
    instructions: str = Field(default="", max_length=400)

    @field_validator("instructions")
    @classmethod
    def normalize_instructions(cls, value: str) -> str:
        return str(value or "").strip()


class DashboardPreferenceResponse(DashboardPreferenceUpdate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID | None = None
    scope: str = "default"
