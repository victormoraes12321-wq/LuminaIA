"""
LuminaAI — Schemas Pydantic v2: Favorite

Validação de dados para favoritos de consultas dos usuários.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FavoriteCreate(BaseModel):
    """Schema para favoritar uma consulta."""

    view_catalog_id: uuid.UUID = Field(
        ...,
        description="ID da view a ser favoritada",
    )
    titulo_personalizado: str | None = Field(
        default=None,
        max_length=255,
        description="Título customizado. Se nulo, o nome da view é usado.",
        examples=["Vendas Q4 2024 — Região Sul"],
    )
    parametros_salvos: dict = Field(
        default_factory=dict,
        description="Parâmetros da consulta para re-execução futura",
        examples=[{"data_inicio": "2024-10-01", "data_fim": "2024-12-31"}],
    )


class FavoriteUpdate(BaseModel):
    """Schema para atualização de um favorito existente."""

    titulo_personalizado: str | None = Field(None, max_length=255)
    parametros_salvos: dict | None = None


class FavoriteResponse(BaseModel):
    """Schema de resposta para um favorito."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    view_catalog_id: uuid.UUID
    titulo_personalizado: str | None
    parametros_salvos: dict
    criado_em: datetime
