"""Explicitly non-persisting legacy dashboard validation path."""
from __future__ import annotations

from collections.abc import Mapping

from contracts.dashboard_blueprint_v2 import (
    LegacyDashboardAdaptationResultV2,
    LegacyDashboardAdaptationStatusV2,
)
from services.dashboard_blueprint_v2.legacy_adapter import LegacyDashboardBlueprintAdapter
from services.dashboard_blueprint_v2.validation_service import DashboardBlueprintValidationService

from .errors import DashboardBackendError


class DashboardLegacyDryRunServiceV2:
    """Adapter + validator only: no database, publication, query, or permission side effect."""

    def __init__(self, *, enabled: bool, shadow: bool = False) -> None:
        self.enabled = enabled
        self.shadow = shadow

    def validate(self, legacy: Mapping[str, object]) -> LegacyDashboardAdaptationResultV2:
        if not self.enabled:
            raise DashboardBackendError(
                "DASHBOARD_RUNTIME_UNAVAILABLE", "Dry-run legado V2 desativado.", 503
            )
        adapted = LegacyDashboardBlueprintAdapter.adapt(legacy)
        if adapted.proposal is None:
            return adapted
        validation = DashboardBlueprintValidationService.validate_payload(adapted.proposal)
        warnings = list(adapted.warnings)
        warnings.extend(
            f"validation:{issue.code}" for issue in validation.issues if issue.blocking
        )
        status = adapted.status
        if validation.status.value != "VALID":
            status = LegacyDashboardAdaptationStatusV2.PARTIAL
        if self.shadow:
            warnings.append("shadow validation only; no V2 persistence or publication")
        return adapted.model_copy(update={"status": status, "warnings": tuple(warnings)})

