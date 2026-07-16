from __future__ import annotations

import uuid
from typing import Any
from pydantic import BaseModel, Field
from enum import Enum


class ComponentStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    PARTIAL = "PARTIAL"
    SYNC_PENDING = "SYNC_PENDING"
    CACHE_STALE = "CACHE_STALE"
    FAILED = "FAILED"
    NO_DATA = "NO_DATA"
    BLOCKED = "BLOCKED"
    INVALID = "INVALID"


class ComponentPriority(str, Enum):
    CRITICO = "CRITICO"
    IMPORTANTE = "IMPORTANTE"
    COMPLEMENTAR = "COMPLEMENTAR"
    OPCIONAL = "OPCIONAL"


class DeliveryDecision(str, Enum):
    FULL_RENDERING = "FULL_RENDERING"
    PARTIAL_RENDERING = "PARTIAL_RENDERING"
    TEXT_ONLY = "TEXT_ONLY"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    UNAVAILABLE = "UNAVAILABLE"


class ComponentRenderItem(BaseModel):
    """
    Estrutura individual de renderização de cada componente.
    Enviado ao frontend para controle estrito de exibição.
    """
    id: str = Field(description="ID do componente correspondente (ex: widget_task_1)")
    tipo: str = Field(description="Tipo visual (ex: BAR | LINE | PIE | TABLE | KPI)")
    posicao: dict[str, int] = Field(default_factory=dict, description="Coordenadas de grid (x, y, w, h)")
    status: ComponentStatus = Field(default=ComponentStatus.AVAILABLE)
    prioridade: ComponentPriority = Field(default=ComponentPriority.COMPLEMENTAR)
    health: float = Field(default=1.0, description="Indicador de integridade (0.0 a 1.0)")
    fonte: str | None = Field(default=None, description="Nome da View analítica de origem")
    versao: str | None = Field(default=None, description="Versão do mapeamento no SVR")
    ultima_sincronizacao: str | None = Field(default=None, description="Data/hora ISO da última sync")
    proxima_sincronizacao: str | None = Field(default=None, description="Data/hora ISO da próxima sync programada")
    mensagem: str | None = Field(default=None, description="Mensagem de negócio amigável explicativa")
    placeholder: str | None = Field(default=None, description="Texto ou sugestão visual alternativo em caso de falha")


class RenderPlan(BaseModel):
    """
    Plano completo de renderização do Dashboard Composto.
    """
    dashboard_id: uuid.UUID
    completeness_score: float = Field(description="Score geral de completude do dashboard (0 a 100)")
    decision: DeliveryDecision = Field(default=DeliveryDecision.FULL_RENDERING)
    mensagem_status: str | None = Field(default=None, description="Mensagem executiva sobre a entrega geral")
    componentes: list[ComponentRenderItem] = Field(default_factory=list)


class ROQGResponse(BaseModel):
    """
    Resposta estruturada final e auditada pelo Quality Gate.
    """
    validated_at: str
    audited: bool = Field(default=True)
    validation_steps_ms: dict[str, int] = Field(default_factory=dict, description="Tempo gasto em cada uma das 9 etapas")
    render_plan: RenderPlan
    audit_notes: list[str] = Field(default_factory=list, description="Histórico de decisões e anotações do Quality Gate")
