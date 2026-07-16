"""Lazy Data Platform facade.

The public names below are kept for backward compatibility, but engines are
loaded only when requested. This avoids fragile import cycles during app boot.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_CACHE: dict[str, Any] = {}

_MODULE_EXPORTS = {
    "blueprint_repository": ("services.data_platform.blueprint_repository", "blueprint_repository"),
    "history_service": ("services.data_platform.history_service", "history_service"),
    "integrity_service": ("services.data_platform.integrity_service", "integrity_service"),
    "semantic_catalog": ("services.data_platform.semantic_catalog", "semantic_catalog"),
    "view_manager": ("services.data_platform.view_manager", "view_manager"),
    "health_monitor": ("services.data_platform.health_monitor", "health_monitor"),
    "lineage_service": ("services.data_platform.lineage_service", "lineage_service"),
    "dependency_graph": ("services.data_platform.dependency_graph", "dependency_graph"),
    "catalog_api": ("services.data_platform.catalog_api", "catalog_api"),
    "sync_engine": ("services.data_platform.sync_engine", "sync_engine"),
    "sync_orchestrator": ("services.data_platform.sync_scheduler", "sync_orchestrator"),
    "query_resolver": ("services.data_platform.query_resolver", "query_resolver"),
    "calculation_engine": ("services.data_platform.calculation_engine", "calculation_engine"),
    "comparison_engine": ("services.data_platform.comparison_engine", "comparison_engine"),
    "trend_engine": ("services.data_platform.trend_engine", "trend_engine"),
    "business_rules_engine": ("services.data_platform.business_rules_engine", "business_rules_engine"),
    "dataset_builder": ("services.data_platform.dataset_builder", "dataset_builder"),
    "dashboard_payload_builder": ("services.data_platform.dashboard_payload_builder", "dashboard_payload_builder"),
    "analytics_engine": ("services.data_platform.analytics_engine", "analytics_engine"),
    "intent_fingerprint_generator": ("services.data_platform.intent_fingerprint", "intent_fingerprint_generator"),
    "package_compatibility_engine": ("services.data_platform.package_compatibility", "package_compatibility_engine"),
    "analytical_package_service": ("services.data_platform.analytical_package_service", "analytical_package_service"),
    "package_version_manager": ("services.data_platform.package_version_manager", "package_version_manager"),
    "package_cache": ("services.data_platform.package_cache", "package_cache"),
    "event_engine": ("services.data_platform.event_engine", "event_engine"),
    "live_dashboard_runtime": ("services.data_platform.live_dashboard_runtime", "live_dashboard_runtime"),
    "enterprise_component_engine": (
        "services.data_platform.enterprise_component_engine",
        "enterprise_component_engine",
    ),
    "adaptive_dashboard_engine": (
        "services.data_platform.adaptive_dashboard_engine",
        "adaptive_dashboard_engine",
    ),
}

_CLASS_EXPORTS = {
    "AnalyticalStorage": ("services.data_platform.analytical_storage", "AnalyticalStorage"),
    "MetadataCatalogService": ("services.data_platform.metadata_catalog", "MetadataCatalogService"),
    "PerformanceLayer": ("services.data_platform.performance_layer", "PerformanceLayer"),
    "BusinessLayer": ("services.data_platform.business_layer", "BusinessLayer"),
    "BlueprintResolver": ("services.data_platform.blueprint_resolver", "BlueprintResolver"),
    "DataAccessLayer": ("services.data_platform.data_access_layer", "DataAccessLayer"),
    "ExecutionEngine": ("services.data_platform.execution_engine", "ExecutionEngine"),
    "InsightLayer": ("services.data_platform.insight_layer", "InsightLayer"),
    "DashboardBuilder": ("services.data_platform.dashboard_builder", "DashboardBuilder"),
}


def _export(module_name: str, attr_name: str) -> Any:
    return getattr(import_module(module_name), attr_name)


def _build_compat_singleton(name: str) -> Any:
    if name == "analytical_storage":
        return _export("services.data_platform.analytical_storage", "AnalyticalStorage")()
    if name == "metadata_catalog":
        return _export("services.data_platform.metadata_catalog", "MetadataCatalogService")()
    if name == "performance_layer":
        return _export("services.data_platform.performance_layer", "PerformanceLayer")()
    if name == "business_layer":
        return _export("services.data_platform.business_layer", "BusinessLayer")()
    if name == "blueprint_resolver":
        resolver_cls = _export("services.data_platform.blueprint_resolver", "BlueprintResolver")
        return resolver_cls(__getattr__("blueprint_repository"))
    if name == "data_access_layer":
        dal_cls = _export("services.data_platform.data_access_layer", "DataAccessLayer")
        return dal_cls(__getattr__("analytical_storage"), __getattr__("performance_layer"))
    if name == "execution_engine":
        engine_cls = _export("services.data_platform.execution_engine", "ExecutionEngine")
        return engine_cls(__getattr__("data_access_layer"))
    if name == "insight_layer":
        return _export("services.data_platform.insight_layer", "InsightLayer")()
    if name == "dashboard_builder":
        return _export("services.data_platform.dashboard_builder", "DashboardBuilder")()
    raise AttributeError(name)


def __getattr__(name: str) -> Any:
    if name in _CACHE:
        return _CACHE[name]

    if name in _MODULE_EXPORTS:
        _CACHE[name] = _export(*_MODULE_EXPORTS[name])
        globals()[name] = _CACHE[name]
        return _CACHE[name]

    if name in _CLASS_EXPORTS:
        value = _export(*_CLASS_EXPORTS[name])
        globals()[name] = value
        return value

    compat_singletons = {
        "analytical_storage",
        "metadata_catalog",
        "performance_layer",
        "business_layer",
        "blueprint_resolver",
        "data_access_layer",
        "execution_engine",
        "insight_layer",
        "dashboard_builder",
    }
    if name in compat_singletons:
        _CACHE[name] = _build_compat_singleton(name)
        globals()[name] = _CACHE[name]
        return _CACHE[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AnalyticalStorage",
    "MetadataCatalogService",
    "PerformanceLayer",
    "BusinessLayer",
    "BlueprintResolver",
    "DataAccessLayer",
    "ExecutionEngine",
    "InsightLayer",
    "DashboardBuilder",
    "analytical_storage",
    "blueprint_repository",
    "metadata_catalog",
    "performance_layer",
    "business_layer",
    "blueprint_resolver",
    "data_access_layer",
    "execution_engine",
    "insight_layer",
    "dashboard_builder",
    *_MODULE_EXPORTS.keys(),
]
