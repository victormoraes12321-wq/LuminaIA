"""Contract and feature compatibility checks without automatic migration."""
from __future__ import annotations

from dataclasses import dataclass

from contracts.dashboard_blueprint_v2 import DashboardBlueprintV2

from .registries import FEATURE_REGISTRY, WIDGET_REGISTRY


@dataclass(frozen=True, slots=True)
class DashboardCompatibilityCheckV2:
    compatible: bool
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


class DashboardBlueprintCompatibilityService:
    SUPPORTED_CONTRACT_VERSION = "lumina.dashboard-blueprint/2.0"

    @classmethod
    def check(cls, blueprint: DashboardBlueprintV2) -> DashboardCompatibilityCheckV2:
        errors: list[str] = []
        warnings: list[str] = []
        if blueprint.version.contract_version != cls.SUPPORTED_CONTRACT_VERSION:
            errors.append("unsupported dashboard blueprint major version")
        for feature in blueprint.compatibility.required_features:
            entry = FEATURE_REGISTRY.get(feature)
            if entry is None or not entry.supported:
                errors.append(f"unsupported required feature: {feature}")
        for feature in blueprint.compatibility.deprecated_features:
            if feature in FEATURE_REGISTRY:
                warnings.append(f"deprecated feature declared: {feature}")
        for widget in blueprint.widgets:
            entry = WIDGET_REGISTRY.get(widget.widget_type)
            if entry is None:
                errors.append(f"unsupported widget: {widget.widget_type}")
            elif entry.compatibility_version != "2.0":
                errors.append(f"incompatible widget version: {widget.widget_type}")
        return DashboardCompatibilityCheckV2(
            compatible=not errors,
            warnings=tuple(warnings),
            errors=tuple(errors),
        )

