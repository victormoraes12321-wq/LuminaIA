"""
Dashboard Payload Builder — LuminaAI Data Platform
--------------------------------------------------
Responsável por montar o payload final otimizado para o Frontend.
Ele estrutura os dados em formato de widgets (cards, gráficos, tabelas e filtros)
deixando o Frontend encarregado puramente de renderizar os elementos visuais.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Any

from schemas.query import VisualizationItem
from models.view_catalog import ChartType

logger = logging.getLogger("luminaai.data_platform.dashboard_payload_builder")

# Cores semânticas padrão
_THEME_COLORS = {
    "primary": "#4F46E5",
    "success": "#059669",
    "warning": "#D97706",
    "danger": "#DC2626",
    "info": "#06B6D4",
    "gray": "#64748B"
}


class DashboardPayloadBuilder:
    """
    Construtor e formatador de Payload de Dashboard para o Frontend.
    """

    def build_payload(
        self,
        tenant_id: uuid.UUID,
        datasets: dict[str, dict[str, Any]],
        primary_intention: Any,
        analytics_results: dict[str, Any] = None
    ) -> dict[str, Any]:
        """
        Organiza múltiplos datasets e cálculos em uma estrutura visual de Dashboard
        delegando a renderização declarativa e governada ao Enterprise Component Engine (ECE).
        """
        logger.debug("[DashboardPayloadBuilder] Construindo payload final do dashboard via ECE...")

        # 1. Determina a estratégia visual a partir da intenção
        visual_strategy = {"primary_chart_type": "BAR"}
        if primary_intention and getattr(primary_intention, "chart_type_sobrescrever", None):
            visual_strategy["primary_chart_type"] = primary_intention.chart_type_sobrescrever.upper()

        # 2. Invoca o Enterprise Component Engine para renderização declarativa
        from services.data_platform.enterprise_component_engine import enterprise_component_engine
        ece_components = enterprise_component_engine.render_dashboard_layout(
            tenant_id=tenant_id,
            datasets=datasets,
            blueprint=None,
            visual_strategy=visual_strategy,
            theme_name="CORPORATIVO",
            active_filters=None,
            user_role="USER",
            analytics_results=analytics_results
        )

        # 3. Invoca o Adaptive Dashboard Engine para montar o grid responsivo de 12 colunas e aplicar personalizações
        from services.data_platform.adaptive_dashboard_engine import adaptive_dashboard_engine
        ade_layout = adaptive_dashboard_engine.assemble_dashboard_layout(
            tenant_id=tenant_id,
            ece_components=ece_components,
            blueprint=None,
            visual_strategy=visual_strategy,
            theme_name="CORPORATIVO",
            user_preferences=None,
            user_role="USER"
        )

        # 4. Mapeia os componentes ordenados e filtrados pelo ADE de volta aos widgets legados
        widgets = []
        for comp in ade_layout.get("components", []):
            w_type = comp.get("type")
            w_name = comp.get("name")
            w_data = comp.get("data_snapshot") or {}

            legacy_widget = {
                "type": w_type,
                "title": w_name,
                "ece_metadata": comp
            }

            if w_type == "TABLE":
                legacy_widget.update({
                    "columns": w_data.get("columns", []),
                    "rows": w_data.get("rows", []),
                    "total_rows": w_data.get("total_rows", 0)
                })
            elif w_type == "FILTROS":
                legacy_widget.update({
                    "active_filters": w_data.get("active_filters", {})
                })
            elif w_type == "KPI_CARD":
                legacy_widget.update({
                    "value": w_data.get("value", 0.0),
                    "diff_value": w_data.get("diff_value", 0.0),
                    "diff_percent": w_data.get("diff_percent", 0.0),
                    "direction": w_data.get("direction", "STABLE"),
                    "indicator_color": "#059669" if w_data.get("direction") == "UP" else ("#DC2626" if w_data.get("direction") == "DOWN" else "#4F46E5"),
                    "format": w_data.get("format", "number")
                })
            else:
                legacy_widget.update({
                    "data": w_data.get("data", []),
                    "label_field": w_data.get("label_field"),
                    "value_field": w_data.get("value_field"),
                    "color": comp.get("theme_config", {}).get("primary_color", "#4F46E5")
                })
            widgets.append(legacy_widget)

        # 5. Retorna a Dashboard Instance integrada com ADE e ECE
        return {
            "dashboard_id": ade_layout.get("dashboard_id", str(uuid.uuid4())),
            "tenant_id": str(tenant_id),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "widgets": widgets,
            "filters": {
                "available_filters": [],
                "active_filters": {}
            },
            "drill_down_paths": {},
            "performance": {
                "cache_hit": ade_layout.get("telemetry", {}).get("layout_cache_status") == "HIT",
                "processed_records": sum(ds["metadata"]["quantidade_registros"] for ds in datasets.values())
            },
            "ade_layout": ade_layout  # Anexa o layout adaptável completo com grids responsivos e telemetria
        }


# Singleton export
dashboard_payload_builder = DashboardPayloadBuilder()
