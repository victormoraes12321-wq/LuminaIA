"""
LuminaAI — Schemas Pydantic v2: ViewCatalog

Validação de dados para o Catálogo de Views Oracle.
Inclui ViewCatalogSummary — versão compacta injetada no prompt da IA.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Any

from models.view_catalog import ChartType


class ViewCatalogBase(BaseModel):
    """Campos comuns para criação e atualização de ViewCatalog."""

    nome_view_oracle: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Nome exato da view no Oracle (case-insensitive no banco)",
        examples=["VW_VENDAS_MENSAIS"],
    )
    descricao_para_ia: str = Field(
        ...,
        min_length=20,
        description=(
            "Descrição semântica detalhada para o Motor de Intenções. "
            "Deve incluir propósito, métricas, dimensões, casos de uso e sinônimos. "
            "Quanto mais rica, melhor o matching da IA."
        ),
        examples=[
            "Exibe o volume e valor total de vendas agrupados por mês. "
            "Útil para análise de faturamento, receita mensal e tendências comerciais."
        ],
    )
    tipo_grafico_padrao: ChartType = Field(
        default=ChartType.BAR,
        description="Tipo de componente visual padrão para esta view",
    )
    parametros_schema: dict = Field(
        default_factory=dict,
        description=(
            "Schema dos parâmetros aceitos. "
            "Formato: {campo: {type, required, description, example}}"
        ),
    )

    @field_validator("parametros_schema", mode="before")
    @classmethod
    def parse_schema_dict(cls, v: Any) -> dict:
        if isinstance(v, str) and v.strip():
            import json
            try:
                return json.loads(v)
            except Exception:
                pass
        return v or {}


class ViewCatalogCreate(ViewCatalogBase):
    """Schema para cadastro de nova view no catálogo."""
    pass


class ViewCatalogUpdate(BaseModel):
    """Schema para atualização parcial de uma view do catálogo."""

    descricao_para_ia: str | None = Field(None, min_length=20)
    tipo_grafico_padrao: ChartType | None = None
    parametros_schema: dict | None = None
    ativo: bool | None = None

    @field_validator("parametros_schema", mode="before")
    @classmethod
    def parse_schema_dict(cls, v: Any) -> dict | None:
        if v is None:
            return None
        if isinstance(v, str) and v.strip():
            import json
            try:
                return json.loads(v)
            except Exception:
                pass
        return v


class ViewCatalogResponse(ViewCatalogBase):
    """Schema de resposta completo para ViewCatalog."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Identificador único da view no catálogo")
    tenant_id: uuid.UUID = Field(description="Tenant proprietário desta view")
    ativo: bool = Field(description="Views inativas não são enviadas à IA")
    criado_em: datetime
    atualizado_em: datetime


class ViewCatalogSummary(BaseModel):
    """
    Versão compacta da view para injeção no prompt do Motor de Intenções.

    Contém os campos necessários para o LLM fazer o matching e saber quais
    parâmetros a view suporta.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="UUID a ser retornado pela IA no matching")
    nome_view_oracle: str = Field(description="Nome da view no Oracle")
    descricao_para_ia: str = Field(description="Descrição semântica para o LLM")
    tipo_grafico_padrao: ChartType = Field(description="Tipo de gráfico desta view")
    parametros_schema: dict = Field(
        default_factory=dict,
        description="Parâmetros aceitos por esta view no banco de dados."
    )

    @field_validator("parametros_schema", mode="before")
    @classmethod
    def parse_schema_dict(cls, v: Any) -> dict:
        if isinstance(v, str) and v.strip():
            import json
            try:
                return json.loads(v)
            except Exception:
                pass
        return v or {}
