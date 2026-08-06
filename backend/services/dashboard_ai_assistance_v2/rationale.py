from __future__ import annotations

from contracts.dashboard_ai_assistance_v2 import DashboardAiPublicRationaleV2, DashboardDesignSpecV2


class DashboardAiRationaleServiceV2:
    @staticmethod
    def for_design(design: DashboardDesignSpecV2) -> DashboardAiPublicRationaleV2:
        return DashboardAiPublicRationaleV2(
            summary=f"A proposta usa o template {design.template_id} com {len(design.widgets)} componente(s) declarativo(s).",
            decisions=(
                f"Métricas canônicas: {len(design.metric_ids)}",
                f"Dimensões canônicas: {len(design.dimension_ids)}",
                f"Período: {design.canonical_period_id}",
            ),
        )

