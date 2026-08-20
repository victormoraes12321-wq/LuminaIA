"""
Enterprise Component Engine (ECE) — Component Factory
------------------------------------------------------
Responsável por instanciar a estrutura declarativa padrão de todos os
tipos de componentes visuais do LuminaAI, aplicando predefinições.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from services.data_platform.enterprise_component_engine.schemas import ComponentSchema


class ComponentFactory:
    """
    Fábrica unificada para instanciar componentes com configurações padrão de:
    - Acessibilidade (ARIA)
    - Responsividade por breakpoint
    - Animações padrão
    - Hooks de eventos suportados
    """

    @staticmethod
    def create_component(
        type: str,
        name: str,
        tenant_id: uuid.UUID,
        data_snapshot: Any = None,
        config: Dict[str, Any] = None,
    ) -> ComponentSchema:
        """
        Instancia e retorna um ComponentSchema configurado para o tipo específico.
        """
        type_upper = type.upper()
        config = config or {}

        # Determina a Categoria com base no Tipo
        category = "UTILITIES"
        if type_upper in ("BAR", "LINE", "PIE", "AREA", "SCATTER", "HEATMAP", "TREEMAP", "GAUGE", "TIMELINE", "MAPAS"):
            category = "CHARTS"
        elif type_upper in ("KPI_CARD", "KPI", "INDICADORES", "RANKING"):
            category = "KPI"
        elif type_upper in ("TABLE", "PIVOT"):
            category = "TABLES"
        elif type_upper in ("FILTROS", "ALERTAS", "BREADCRUMB", "DRAWER", "TABS", "ACCORDION", "CAROUSEL", "MODAL", "TOOLTIPS"):
            category = "CONTROLS"
        elif type_upper in ("SKELETON", "LOADING", "EMPTY STATE", "ERROR STATE"):
            category = "STATUS"
        elif type_upper in ("EXPORTACAO", "UPLOAD", "DOWNLOAD"):
            category = "ACTIONS"

        # Predefinições de Acessibilidade (ARIA)
        accessibility_config = {
            "role": "region" if category != "CHARTS" else "img",
            "aria_label": f"Componente {name} do tipo {type}",
            "tabindex": 0,
            "keyboard_focusable": True,
            "screen_reader_description": f"Exibindo dados visuais para {name}.",
        }

        # Predefinições de Responsividade por Breakpoint
        # Grid de 12 colunas no padrão Bootstrap/Tailwind
        responsiveness_config = {
            "min_width": 200,
            "min_height": 100,
            "priority": "MEDIA",
            "breakpoints": {
                "ultra_wide": {"cols": 4, "rows": 3},  # Exibe 3 por linha
                "desktop": {"cols": 6, "rows": 4},     # Exibe 2 por linha
                "notebook": {"cols": 6, "rows": 4},
                "tablet": {"cols": 12, "rows": 4},     # Exibe 1 por linha
                "mobile": {"cols": 12, "rows": 5},     # Exibe 1 por linha e mais alto
            }
        }

        # Ajusta dimensões/prioridades específicas para tabelas e gráficos maiores
        if category in ("CHARTS", "TABLES"):
            responsiveness_config["min_height"] = 300
            responsiveness_config["priority"] = "ALTA"
            responsiveness_config["breakpoints"]["desktop"] = {"cols": 12, "rows": 6}

        # Predefinições de Animação
        animation_config = {
            "enter_animation": "fade-in",
            "exit_animation": "fade-out",
            "update_animation": "grow",
            "duration_ms": 300,
            "use_hardware_acceleration": True
        }

        # Eventos permitidos por padrão
        allowed_events = [
            "onCreate",
            "onLoad",
            "onReady",
            "onRefresh",
            "onDestroy"
        ]
        if category in ("CHARTS", "TABLES", "KPI"):
            allowed_events.extend(["onExpand", "onCollapse", "onExport"])
        if type_upper == "FILTROS":
            allowed_events.append("onFilter")

        # Configurações Visuais de Tema Default (será resolvido pelo Theme Engine no Renderer)
        theme_config = {
            "background_color": "var(--bg-card)",
            "border_color": "var(--border-default)",
            "border_radius": "8px",
            "padding": "16px",
            "text_color": "var(--text-primary)"
        }

        # Criação do Objeto Schema
        return ComponentSchema(
            id=uuid.uuid4(),
            name=name,
            category=category,
            type=type_upper,
            version="1.0.0",
            description=f"Componente visual auto-gerado para {name}.",
            dependencies=[],
            allowed_events=allowed_events,
            permissions=["USER", "MANAGER", "ADMIN"],
            state="Ready" if type_upper not in ("LOADING", "SKELETON") else "Loading",
            theme_config=theme_config,
            accessibility_config=accessibility_config,
            responsiveness_config=responsiveness_config,
            animation_config=animation_config,
            interaction_config={
                "allow_drill_down": True if category in ("CHARTS", "TABLES") else False,
                "allow_cross_filter": True if type_upper == "FILTROS" else False,
                "allow_fullscreen": True,
                "allow_favorites": True,
                "allow_sharing": True,
                "allow_snapshot": True,
                "allow_history": True,
            },
            data_snapshot=data_snapshot,
            diagnostics={
                "warnings": [],
                "errors": [],
                "health_score": 1.0,
                "quality_score": 1.0,
                "schema_valid": True
            },
            tenant_id=tenant_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            author="ENTERPRISE_COMPONENT_FACTORY"
        )
