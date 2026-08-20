"""
LuminaAI — Schemas Pydantic v2: Tenant

Validação de dados de entrada e saída para operações de Tenant.
Usa ConfigDict(from_attributes=True) para compatibilidade com SQLAlchemy ORM.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Any
import json


class TenantBase(BaseModel):
    """Campos comuns para criação e atualização de Tenant."""

    nome: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Razão social ou nome fantasia da empresa",
        examples=["Acme Corporation Ltda"],
    )
    logo_url: str | None = Field(
        default=None,
        description="URL completa da logo do tenant",
        examples=["https://cdn.empresa.com/logos/acme.png"],
    )
    tema_config: dict = Field(
        default_factory=dict,
        description="Configurações visuais: primary_color, dark_mode, font_family",
        examples=[{"primary_color": "#6C63FF", "dark_mode": True}],
    )
    ia_config: dict = Field(
        default_factory=dict,
        description="Configurações de IA: model, temperature, custom_instructions",
        examples=[{"model": "gpt-4o-mini", "temperature": 0.0}],
    )

    @field_validator("tema_config", "ia_config", mode="before")
    @classmethod
    def parse_dict_field(cls, v: Any) -> dict:
        if isinstance(v, str) and v.strip():
            try:
                return json.loads(v)
            except Exception:
                pass
        return v or {}


class TenantCreate(TenantBase):
    """Schema para criação de novo Tenant."""

    oracle_conn: dict = Field(
        default_factory=dict,
        description="Dados de conexão Oracle (serão criptografados antes de salvar)",
        examples=[{"host": "oracle.empresa.com", "port": 1521, "sid": "PROD"}],
    )


class TenantUpdate(BaseModel):
    """Schema para atualização parcial de Tenant (todos os campos opcionais)."""

    nome: str | None = Field(None, min_length=2, max_length=255)
    logo_url: str | None = None
    tema_config: dict | None = None
    ia_config: dict | None = None
    ativo: bool | None = None

    @field_validator("tema_config", "ia_config", mode="before")
    @classmethod
    def parse_dict_field_optional(cls, v: Any) -> dict | None:
        if v is None:
            return None
        if isinstance(v, str) and v.strip():
            try:
                return json.loads(v)
            except Exception:
                pass
        return v


class TenantResponse(TenantBase):
    """Schema de resposta para Tenant — expõe dados públicos (oracle_conn excluído)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Identificador único do tenant")
    ativo: bool = Field(description="Status de ativação do tenant")
    criado_em: datetime = Field(description="Data e hora de criação (UTC)")
    atualizado_em: datetime = Field(description="Data e hora da última atualização (UTC)")


class TenantSettingsUpdate(BaseModel):
    """Schema para o administrador atualizar todas as configurações de visual, IA, banco de dados e sincronização."""

    nome: str | None = Field(None, min_length=2, max_length=255, description="Nome da empresa")
    logo_url: str | None = Field(None, description="URL da logo da empresa")
    tema_config: dict | None = Field(None, description="Tema visual: primary_color, secondary_color, dark_mode, font_family, border_radius")
    ia_config: dict | None = Field(None, description="IA Configs: model, temperature, custom_instructions, api_key")
    oracle_conn: dict | None = Field(None, description="Credenciais Oracle (host, port, user, password, sid, service_name)")
    clone_db_conn: dict | None = Field(None, description="Credenciais PostgreSQL do Clone (host, port, user, password, database)")
    sync_config: dict | None = Field(None, description="Configurações de sincronização (enabled, times)")

    @field_validator("tema_config", "ia_config", "oracle_conn", "clone_db_conn", "sync_config", mode="before")
    @classmethod
    def parse_settings_dict(cls, v: Any) -> dict | None:
        if v is None:
            return None
        if isinstance(v, str) and v.strip():
            try:
                return json.loads(v)
            except Exception:
                pass
        return v

