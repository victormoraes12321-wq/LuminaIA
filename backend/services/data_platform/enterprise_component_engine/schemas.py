"""
Enterprise Component Engine (ECE) — Schemas
---------------------------------------------
Modelos Pydantic oficiais para representação de Componentes Visuais
e suas configurações de tema, acessibilidade, responsividade, animação e estado.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ComponentSchema(BaseModel):
    """
    Definição declarativa completa de um Componente Visual no LuminaAI.
    Toda renderização no frontend será baseada neste schema.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, description="UUID do componente.")
    name: str = Field(..., description="Nome descritivo do componente.")
    category: str = Field(..., description="Categoria (ex: CHARTS, CONTROLS, UTILITIES).")
    type: str = Field(..., description="Tipo físico do componente (ex: BAR, KPI_CARD, TABLE).")
    version: str = Field("1.0.0", description="Versão semântica do componente.")
    description: str = Field("", description="Breve descrição da finalidade visual.")
    dependencies: List[str] = Field(default_factory=list, description="Views ou componentes dependentes.")
    allowed_events: List[str] = Field(default_factory=list, description="Lista de eventos suportados.")
    permissions: List[str] = Field(default_factory=list, description="Lista de papéis com acesso permitido.")
    state: str = Field("Ready", description="Estado atual: Loading, Ready, Error, Empty, etc.")
    
    # ── Configurações Visuais ──
    theme_config: Dict[str, Any] = Field(default_factory=dict, description="Estilos, fontes, cores semânticas e bordas.")
    accessibility_config: Dict[str, Any] = Field(default_factory=dict, description="Tags ARIA, leitores de tela e navegação por teclado.")
    responsiveness_config: Dict[str, Any] = Field(default_factory=dict, description="Largura/altura mínimas e layouts por breakpoints.")
    animation_config: Dict[str, Any] = Field(default_factory=dict, description="Tipo e velocidade de animações (Fade, Slide, etc.).")
    interaction_config: Dict[str, Any] = Field(default_factory=dict, description="Configurações de drill-down, cross-filter, zoom, etc.")
    
    # ── Snapshot de dados analíticos associados ──
    data_snapshot: Any = Field(None, description="Snapshot dos dados formatados do dataset/KPI.")
    
    # ── Diagnóstico de integridade ──
    diagnostics: Dict[str, Any] = Field(default_factory=dict, description="Métricas de saúde, integridade e diagnóstico técnico.")
    
    # ── Governança ──
    tenant_id: uuid.UUID = Field(..., description="Isolamento multi-tenant do componente.")
    created_at: str = Field(..., description="Data/hora de criação do componente.")
    author: str = Field("ENTERPRISE_COMPONENT_ENGINE", description="Autor da criação do componente.")
