"""
Adaptive Dashboard Engine (ADE) — Schemas
-------------------------------------------
Modelos Pydantic oficiais para representação de layouts adaptáveis
de dashboards e configurações de grid responsivo.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GridPosition(BaseModel):
    """Representa a posição e dimensões físicas de um componente em uma grade de 12 colunas."""
    component_id: uuid.UUID = Field(..., description="ID do componente.")
    x: int = Field(..., description="Coordenada X (coluna inicial, 0 a 11).")
    y: int = Field(..., description="Coordenada Y (linha inicial, base 0).")
    w: int = Field(..., description="Largura (número de colunas, 1 a 12).")
    h: int = Field(..., description="Altura (número de linhas).")


class BreakpointLayout(BaseModel):
    """Layout completo para um breakpoint específico (ex: desktop, mobile)."""
    breakpoint_name: str = Field(..., description="Nome do breakpoint: ultra_wide, desktop, notebook, tablet, mobile.")
    positions: List[GridPosition] = Field(default_factory=list, description="Lista de posições de componentes.")


class DashboardLayoutSchema(BaseModel):
    """
    Schema consolidado que representa o layout de Dashboard gerado pelo ADE.
    Contém a composição física e responsiva final.
    """
    dashboard_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="ID único da Dashboard Instance.")
    tenant_id: uuid.UUID = Field(..., description="Tenant isolado.")
    state: str = Field("Ready", description="Estado da Dashboard (Loading, Ready, Error, etc.).")
    
    # ── Mapeamento Responsivo ──
    # breakpoint_name -> Lista de GridPosition
    grid_layouts: Dict[str, List[GridPosition]] = Field(
        default_factory=dict,
        description="Coordenadas de layout calculadas para cada breakpoint responsivo."
    )
    
    # ── Composição Visual ──
    components: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Lista de componentes visuais provenientes do Enterprise Component Engine (ECE)."
    )
    
    # ── Metadados e Personalização ──
    personalization_applied: bool = Field(False, description="True se preferências do usuário foram aplicadas.")
    telemetry: Dict[str, Any] = Field(default_factory=dict, description="Métricas de tempo de montagem, FPS e economia.")
    diagnostics: Dict[str, Any] = Field(default_factory=dict, description="Diagnóstico de integridade e scores globais.")
    created_at: str = Field(..., description="Data/hora de geração do layout.")
