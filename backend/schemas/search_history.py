"""
LuminaAI — Schemas Pydantic v2: SearchHistory

Validação de dados para o histórico de consultas.
Registros são imutáveis — apenas Create e Response são necessários.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SearchHistoryCreate(BaseModel):
    """
    Schema interno para criação de registro no histórico.
    Usado apenas pelo backend — não exposto como endpoint de criação direta.
    """

    user_id: uuid.UUID = Field(description="ID do usuário que realizou a consulta")
    view_catalog_id: uuid.UUID | None = Field(
        default=None,
        description="ID da view identificada (nulo se IA não encontrou correspondência)",
    )
    pergunta_texto: str = Field(
        ...,
        description="Pergunta original em linguagem natural",
    )
    parametros_extraidos: dict = Field(
        default_factory=dict,
        description="Parâmetros identificados pela IA na pergunta",
    )
    ia_confianca: Decimal | None = Field(
        default=None,
        description="Score de confiança do matching (0.0000 a 1.0000)",
    )
    tempo_resposta_ms: int | None = Field(
        default=None,
        description="Latência total da requisição em ms",
    )


class SearchHistoryResponse(BaseModel):
    """Schema de resposta para um registro do histórico."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    view_catalog_id: uuid.UUID | None
    pergunta_texto: str
    parametros_extraidos: dict
    ia_confianca: Decimal | None = Field(
        description="Score de confiança (0.0000 a 1.0000)"
    )
    tempo_resposta_ms: int | None
    criado_em: datetime


class SearchHistoryListResponse(BaseModel):
    """Schema de resposta paginada para listagem do histórico."""

    items: list[SearchHistoryResponse]
    total: int
    page: int
    page_size: int
