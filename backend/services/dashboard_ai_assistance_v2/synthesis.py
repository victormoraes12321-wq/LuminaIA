from __future__ import annotations

from contracts.dashboard_ai_assistance_v2 import DashboardDesignSpecV2
from contracts.dashboard_blueprint_v2 import (
    DashboardOriginV2,
    DashboardResultShapeV2,
)
from services.dashboard_blueprint_v2.fixtures import (
    assemble_blueprint,
    build_comparison_dashboard,
    build_executive_dashboard,
    data_binding,
    kpi_widget,
    line_widget,
    ranking_widget,
)


class DashboardBlueprintSynthesisService:
    """Pure builder: same design spec always yields the same Blueprint V2."""

    def synthesize(self, design: DashboardDesignSpecV2):
        blueprint_id = f"dashboard.ai.{design.resolution_checksum[:24]}"
        if design.template_id == "EXECUTIVE_OVERVIEW":
            blueprint = build_executive_dashboard()
        elif design.template_id == "COMPARATIVE_ANALYSIS":
            blueprint = build_comparison_dashboard()
        else:
            widgets = []
            bindings = []
            for index, metric_id in enumerate(design.metric_ids):
                widget_id = f"widget.ai.kpi.{index + 1}"
                binding_id = f"binding.ai.kpi.{index + 1}"
                widgets.append(kpi_widget(widget_id, binding_id, self._metric_label(metric_id)))
                bindings.append(data_binding(binding_id, metric_id, DashboardResultShapeV2.SCALAR))
            if "dimension.month" in design.dimension_ids and design.metric_ids:
                widgets.append(line_widget("widget.ai.series", "binding.ai.series", design.metric_ids[0]))
                bindings.append(data_binding("binding.ai.series", design.metric_ids[0], DashboardResultShapeV2.TIME_SERIES, dimension_id="dimension.month"))
            if design.template_id == "PRODUCT_RANKING" and design.metric_ids:
                widgets.append(ranking_widget("widget.ai.ranking", "binding.ai.ranking", design.metric_ids[0]))
                bindings.append(data_binding("binding.ai.ranking", design.metric_ids[0], DashboardResultShapeV2.RANKING, dimension_id="dimension.product"))
            blueprint = assemble_blueprint(tuple(widgets), tuple(bindings), blueprint_id=blueprint_id, title=design.title)
        identity = blueprint.identity.model_copy(update={
            "blueprint_id": blueprint_id,
            "canonical_name": blueprint_id,
            "title": design.title,
            "description": design.description,
        })
        return blueprint.model_copy(update={"identity": identity, "created_origin": DashboardOriginV2.AI_PROPOSED})

    @staticmethod
    def _metric_label(metric_id: str) -> str:
        return {
            "metric.revenue": "Faturamento comercial",
            "metric.gross.revenue": "Faturamento bruto",
            "metric.average.ticket": "Ticket médio",
            "metric.discount.total": "Desconto total",
            "metric.discount.average": "Desconto médio",
            "metric.gross.profit": "Lucro",
            "metric.open.accounts": "Contas em aberto",
            "metric.inventory.balance": "Saldo de estoque",
        }.get(metric_id, metric_id)

