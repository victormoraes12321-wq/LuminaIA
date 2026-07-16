from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MetadataCatalogResponse(BaseModel):
    """Read-only response for the corporate Metadata Catalog."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID

    nome_view: str
    tipo_estrutura: str
    estrutura_id: str
    origem: str
    owner: str
    categoria: str
    tags: list[str] = Field(default_factory=list)
    blueprint_associado: str | None = None
    dashboard_associado: str | None = None

    tabelas_utilizadas: list[str] = Field(default_factory=list)
    campos_utilizados: list[str] = Field(default_factory=list)
    relacionamentos: list[dict[str, Any]] = Field(default_factory=list)
    filtros_padrao: dict[str, Any] = Field(default_factory=dict)
    periodos_suportados: list[str] = Field(default_factory=list)
    kpis_suportados: list[str] = Field(default_factory=list)
    dependencias: list[str] = Field(default_factory=list)

    lineage: list[dict[str, Any]] = Field(default_factory=list)
    dependencias_grafo: dict[str, Any] = Field(default_factory=dict)

    health_score: float
    integrity_score: float
    performance_score: float
    freshness_score: float
    usage_score: float
    alertas: list[dict[str, Any]] = Field(default_factory=list)

    cache_ativo: bool
    cache_atualizado_em: datetime | None = None
    cache_ttl_segundos: int
    cache_hit_rate: float

    versao: int
    status: str
    integridade: str
    hash_integridade: str

    ultima_sincronizacao: datetime | None = None
    proxima_sincronizacao: datetime | None = None
    duracao_ultima_sync_ms: float
    registros_ultima_sync: int
    erros_sync: list[dict[str, Any]] = Field(default_factory=list)

    quantidade_consultas: int
    quantidade_usuarios: int
    ultima_utilizacao: datetime | None = None
    tempo_medio_atualizacao: float
    tempo_medio_execucao: float

    criado_em: datetime
    atualizado_em: datetime


class MetadataCatalogVersionResponse(BaseModel):
    """Immutable Metadata Catalog version snapshot."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    metadata_id: uuid.UUID
    versao: int
    snapshot: dict[str, Any]
    autor: str | None = None
    motivo: str | None = None
    criado_em: datetime
