"""
Enterprise Component Engine (ECE) — Component Renderer (Synchronous)
--------------------------------------------------------------------
O coração visual do ECE. Consome Blueprint, Template, Dataset e Strategy,
aplicando regras de temas, responsividade, acessibilidade e animações.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.data_platform.enterprise_component_engine.schemas import ComponentSchema
from services.data_platform.enterprise_component_engine.factory import ComponentFactory
from services.data_platform.enterprise_component_engine.registry import component_registry
from services.data_platform.enterprise_component_engine.lifecycle import component_lifecycle

logger = logging.getLogger("luminaai.data_platform.enterprise_component_engine.renderer")


class ComponentRenderer:
    """
    Renderizador universal de componentes do LuminaAI. Síncrono.
    """

    # Definição oficial de paletas de cores por Tema
    THEMES: Dict[str, Dict[str, str]] = {
        "LIGHT": {
            "background_color": "#FFFFFF",
            "border_color": "#E2E8F0",
            "text_color": "#1E293B",
            "primary_color": "#4F46E5",
            "accent_color": "#06B6D4",
        },
        "DARK": {
            "background_color": "#0F172A",
            "border_color": "#334155",
            "text_color": "#F8FAFC",
            "primary_color": "#6366F1",
            "accent_color": "#22D3EE",
        },
        "CORPORATIVO": {
            "background_color": "#F8FAFC",
            "border_color": "#CBD5E1",
            "text_color": "#0F172A",
            "primary_color": "#1E3A8A", # Azul Marinho Real
            "accent_color": "#10B981", # Verde Esmeralda
        }
    }

    def render_components(
        self,
        tenant_id: uuid.UUID,
        datasets: Dict[str, Dict[str, Any]],
        blueprint: Any,
        visual_strategy: Dict[str, Any] = None,
        theme_name: str = "CORPORATIVO",
        active_filters: Dict[str, Any] = None,
        analytics_results: Dict[str, Any] = None,
    ) -> List[ComponentSchema]:
        """
        Gera e renderiza de forma governada todos os componentes a serem expostos.
        Se um componente compatível já existir no Component Registry, ele será reutilizado.
        """
        rendered_components = []
        theme = self.THEMES.get(theme_name.upper(), self.THEMES["CORPORATIVO"])
        visual_strategy = visual_strategy or {}

        # 1. Processa KPIs do analytics_results se houver
        if analytics_results and "kpis" in analytics_results:
            for kpi_name, comp_data in analytics_results["kpis"].items():
                kpi_comp_name = kpi_name.upper().replace("_", " ")
                try:
                    kpi_comp = self._find_reusable_component(tenant_id, "KPI_CARD", kpi_comp_name)
                    kpi_data = {
                        "value": comp_data.get("valor_atual", 0.0),
                        "diff_value": comp_data.get("diferenca_absoluta", 0.0),
                        "diff_percent": comp_data.get("variacao_percentual", 0.0),
                        "direction": comp_data.get("direcao", "STABLE"),
                        "format": "currency" if "receita" in kpi_name or "lucro" in kpi_name else "number"
                    }
                    if kpi_comp:
                        component_lifecycle.trigger_phase(kpi_comp, "UPDATE")
                        kpi_comp.data_snapshot = kpi_data
                        kpi_comp.theme_config.update(theme)
                    else:
                        kpi_comp = ComponentFactory.create_component(
                            type="KPI_CARD",
                            name=kpi_comp_name,
                            tenant_id=tenant_id,
                            data_snapshot=kpi_data
                        )
                        kpi_comp.theme_config.update(theme)
                        # Acessibilidade no KPI
                        kpi_comp.accessibility_config.update({
                            "role": "status",
                            "aria_live": "polite",
                            "aria_label": f"Indicador chave de {kpi_comp_name}: {kpi_data['value']}"
                        })
                        component_registry.register(kpi_comp)
                    rendered_components.append(kpi_comp)
                except Exception as e:
                    logger.warning("[ComponentRenderer] Falha ao renderizar KPI %s: %s", kpi_comp_name, e)

        # 2. Instancia/Renderiza Componentes de Status e Filtros Auxiliares se houver filtros ativos
        filter_comp_name = "Painel de Filtros"
        try:
            # Tenta reutilizar do catálogo
            existing_filters = self._find_reusable_component(tenant_id, "FILTROS", filter_comp_name)
            if existing_filters:
                component_lifecycle.trigger_phase(existing_filters, "UPDATE")
                existing_filters.data_snapshot = {"active_filters": active_filters or {}}
                existing_filters.theme_config.update(theme)
                rendered_components.append(existing_filters)
            else:
                new_filter = ComponentFactory.create_component(
                    type="FILTROS",
                    name=filter_comp_name,
                    tenant_id=tenant_id,
                    data_snapshot={"active_filters": active_filters or {}}
                )
                new_filter.theme_config.update(theme)
                component_registry.register(new_filter)
                rendered_components.append(new_filter)
        except Exception as e:
            logger.warning("[ComponentRenderer] Falha ao renderizar componente de Filtro: %s", e)

        # 2. Renderiza componentes para cada dataset de execução
        for query_id, ds in datasets.items():
            view_name = ds["metadata"]["view_name"]
            view_clean = view_name.replace("VW_", "")
            rows = ds["data"]
            schema = ds["schema"]

            # 2.1 Renderiza Tabela Relacionada
            table_name = f"Tabela {view_clean}"
            try:
                table_comp = self._find_reusable_component(tenant_id, "TABLE", table_name)
                # Dados formatados estruturadamente para a tabela
                table_data = {
                    "columns": list(schema.keys()),
                    "rows": rows[:100], # Limita primeiras 100 linhas no payload
                    "total_rows": len(rows)
                }

                if table_comp:
                    component_lifecycle.trigger_phase(table_comp, "UPDATE")
                    table_comp.data_snapshot = table_data
                    table_comp.theme_config.update(theme)
                else:
                    table_comp = ComponentFactory.create_component(
                        type="TABLE",
                        name=table_name,
                        tenant_id=tenant_id,
                        data_snapshot=table_data
                    )
                    table_comp.theme_config.update(theme)
                    # Adiciona regras específicas de Acessibilidade para Leitores de Tela na Tabela
                    table_comp.accessibility_config.update({
                        "role": "table",
                        "aria_rowcount": len(rows),
                        "aria_colcount": len(schema),
                        "caption": f"Tabela de detalhamento analítico de {view_clean}."
                    })
                    component_registry.register(table_comp)

                rendered_components.append(table_comp)
            except Exception as e:
                logger.error("[ComponentRenderer] Erro ao instanciar tabela %s: %s", table_name, e)

            # 2.2 Renderiza Gráfico Correspondente
            chart_type_str = visual_strategy.get("primary_chart_type", "BAR")
            chart_name = f"Gráfico {view_clean}"
            try:
                chart_comp = self._find_reusable_component(tenant_id, chart_type_str, chart_name)
                
                # Prepara o snapshot de dados agrupados para o gráfico
                label_col = None
                value_col = None
                for col, t in schema.items():
                    if t == "string" and not label_col:
                        label_col = col
                    elif t in ("integer", "float") and not value_col:
                        value_col = col

                chart_points = []
                if label_col and value_col:
                    chart_points = [{"label": str(r[label_col]), "value": float(r.get(value_col, 0.0))} for r in rows[:15]]

                chart_data = {
                    "data": chart_points,
                    "label_field": label_col,
                    "value_field": value_col
                }

                if chart_comp:
                    component_lifecycle.trigger_phase(chart_comp, "UPDATE")
                    chart_comp.data_snapshot = chart_data
                    chart_comp.theme_config.update(theme)
                else:
                    chart_comp = ComponentFactory.create_component(
                        type=chart_type_str,
                        name=chart_name,
                        tenant_id=tenant_id,
                        data_snapshot=chart_data
                    )
                    chart_comp.theme_config.update(theme)
                    chart_comp.theme_config["primary_color"] = theme["primary_color"]
                    
                    # Acessibilidade no gráfico
                    chart_comp.accessibility_config.update({
                        "role": "img",
                        "aria_label": f"Gráfico de {chart_type_str} exibindo dados analíticos de {view_clean}."
                    })
                    component_registry.register(chart_comp)

                rendered_components.append(chart_comp)
            except Exception as e:
                logger.error("[ComponentRenderer] Erro ao instanciar gráfico %s: %s", chart_name, e)

        return rendered_components

    def _find_reusable_component(self, tenant_id: uuid.UUID, type: str, name: str) -> ComponentSchema | None:
        """
        Busca e retorna um componente do catálogo oficial para reuso (Component Reutilization).
        Garante isolamento Multi-Tenant.
        """
        registered = component_registry.list_components(tenant_id)
        type_upper = type.upper()
        name_lower = name.lower()
        for comp in registered:
            if comp.type == type_upper and comp.name.lower() == name_lower:
                logger.debug("[ComponentRenderer] Componente reutilizado (Catálogo HIT): id=%s", comp.id)
                return comp
        return None


# Export singleton
component_renderer = ComponentRenderer()
