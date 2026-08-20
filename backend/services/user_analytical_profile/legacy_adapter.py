from __future__ import annotations

from dataclasses import dataclass

from contracts.user_analytical_profile_v2 import (
    PreferenceCreateV2,
    PreferenceOrigin,
    PresentationPreferenceV2,
)
from models.dashboard_preference import DashboardPreference


@dataclass(frozen=True)
class LegacyPreferenceAdaptation:
    preferences: tuple[PreferenceCreateV2, ...]
    warnings: tuple[str, ...]


class LegacyUserPreferenceAdapter:
    """Converts only owner-scoped, safe legacy presentation settings."""

    def adapt_dashboard_preference(
        self,
        row: DashboardPreference,
        *,
        tenant_id,
        user_id,
    ) -> LegacyPreferenceAdaptation:
        if row.tenant_id != tenant_id or row.user_id != user_id:
            raise ValueError("legacy preference owner mismatch")
        visualization = {
            "tabela": "TABLE",
            "grafico": "BAR_CHART",
            "ambos": "TABLE",
        }.get(row.format, "AUTO")
        return LegacyPreferenceAdaptation(
            preferences=(
                PreferenceCreateV2(
                    preference_key=f"legacy.dashboard.{row.scope}",
                    content=PresentationPreferenceV2(
                        preferred_visualization=visualization,
                        table_first=row.format != "grafico",
                    ),
                    origin=PreferenceOrigin.LEGACY_IMPORT,
                ),
            ),
            warnings=(
                "A preferência visual legada foi preservada sem criar defaults analíticos.",
                "Base financeira e instruções livres legadas não foram importadas.",
            ),
        )
