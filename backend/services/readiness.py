from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from contracts.security_rollout_v2 import (
    ConfigurationSnapshotV2,
    SchemaCompatibilityStateV2,
    SchemaManifestV2,
)
from services.security_rollout_v2 import (
    GovernedFeatureRegistryV2,
    MigrationCompatibilityServiceV2,
)


READY_STATES = frozenset(
    {
        "healthy",
        "ok",
        "ready",
        "active",
        "disabled_by_policy",
        "not_applicable",
    }
)


def normalized_status(raw_status: object) -> str:
    value = str(raw_status or "unknown").strip().lower()
    return "healthy" if value in {"healthy", "ok", "ready", "active"} else "degraded"


def dependency_component(
    *,
    raw_status: object,
    required: bool,
    reason: str,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    status = normalized_status(raw_status) if required else "disabled_by_policy"
    component: dict[str, Any] = {
        "status": status,
        "required_in_current_mode": required,
        "state": status.upper(),
        "reason": reason,
    }
    if details:
        component["details"] = dict(details)
    return component


def overall_readiness(components: Mapping[str, Mapping[str, Any]]) -> str:
    required = (
        component
        for component in components.values()
        if bool(component.get("required_in_current_mode", True))
    )
    return "healthy" if all(str(item.get("status", "unknown")).lower() in READY_STATES for item in required) else "degraded"


def active_feature_names(snapshot: ConfigurationSnapshotV2) -> tuple[str, ...]:
    active: list[str] = []
    for feature in snapshot.features:
        disabled_mode = feature.mode in {"LEGACY_ONLY", "DISABLED"}
        execution_surface = feature.api_enabled or feature.worker_enabled or feature.execution_enabled
        if not disabled_mode and execution_surface:
            active.append(feature.feature.value)
    return tuple(sorted(active))


def migration_readiness_component(
    snapshot: ConfigurationSnapshotV2,
    table_names: Iterable[str],
) -> dict[str, Any]:
    active = tuple(
        feature
        for feature in snapshot.features
        if feature.feature.value in set(active_feature_names(snapshot))
    )
    if not active:
        return dependency_component(
            raw_status="not_applicable",
            required=False,
            reason="all governed V2 execution surfaces are disabled by policy",
            details={"active_features": []},
        )

    required_version = max(
        GovernedFeatureRegistryV2.get_policy(feature.feature).required_migration
        for feature in active
    )
    manifest = SchemaManifestV2(
        schema_version=26,
        migration_ids=tuple(f"v{version}_0" for version in range(12, 27)),
        tables=tuple(sorted(set(table_names))),
    )
    compatibility = MigrationCompatibilityServiceV2.evaluate(
        current_schema_version=26,
        required_schema_version=required_version,
        manifest=manifest,
    )
    compatible = compatibility.state is SchemaCompatibilityStateV2.COMPATIBLE
    return dependency_component(
        raw_status="healthy" if compatible else "blocked",
        required=True,
        reason=compatibility.reason,
        details={
            "active_features": list(active_feature_names(snapshot)),
            "required_schema_version": required_version,
            "compatibility_state": compatibility.state.value,
            "missing_objects": list(compatibility.missing_objects),
        },
    )
