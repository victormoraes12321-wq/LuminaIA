from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from contracts.analytical_v2 import MetricReference
from services.metric_registry import METRIC_DEFINITIONS


DEFAULT_COMPARISON_DIMENSIONS = (
    "filial",
    "produto",
    "categoria",
    "vendedor",
    "cliente",
    "estado",
    "cidade",
    "mes",
    "dia",
    "ano",
)
DEFAULT_COMPARISON_ENTITY_TYPES = (
    "filial",
    "produto",
    "categoria",
    "vendedor",
    "cliente",
    "estado",
    "cidade",
)


@dataclass(frozen=True)
class MetricCatalogEntry:
    metric_id: str
    metric_version: str
    unit: str
    aggregation: str
    allowed_dimension_ids: tuple[str, ...]
    allowed_source_ids: tuple[str, ...]
    supported: bool = True
    comparability_group: str | None = None


@dataclass(frozen=True)
class DimensionCatalogEntry:
    dimension_id: str
    allowed_source_ids: tuple[str, ...] = ()
    supported_granularities: tuple[str, ...] = ()


@dataclass(frozen=True)
class EntityCatalogEntry:
    entity_id: str
    tenant_id: UUID
    entity_type: str
    allowed_source_ids: tuple[str, ...] = ()
    permitted_roles: tuple[str, ...] = ("ADMIN", "GESTOR", "CONSULTA")


@dataclass(frozen=True)
class TargetCatalogEntry:
    tenant_id: UUID
    actual_metric_id: str
    target_metric_id: str
    unit: str
    granularity: str
    source_id: str
    official: bool = True
    permitted_roles: tuple[str, ...] = ("ADMIN", "GESTOR", "CONSULTA")


class ComparisonCatalogProvider(Protocol):
    def metric(self, metric_id: str, tenant_id: UUID) -> MetricCatalogEntry | None:
        ...

    def dimension(
        self,
        dimension_id: str,
        tenant_id: UUID,
    ) -> DimensionCatalogEntry | None:
        ...

    def entity(self, entity_id: str, tenant_id: UUID) -> EntityCatalogEntry | None:
        ...

    def target(
        self,
        actual_metric_id: str,
        tenant_id: UUID,
    ) -> TargetCatalogEntry | None:
        ...

    def metric_ids(self) -> tuple[str, ...]:
        ...


@dataclass(frozen=True)
class StaticComparisonCatalog:
    metrics: dict[str, MetricCatalogEntry]
    dimensions: dict[str, DimensionCatalogEntry]
    entities: dict[tuple[UUID, str], EntityCatalogEntry] = field(default_factory=dict)
    targets: dict[tuple[UUID, str], TargetCatalogEntry] = field(default_factory=dict)

    def metric(self, metric_id: str, tenant_id: UUID) -> MetricCatalogEntry | None:
        del tenant_id
        return self.metrics.get(metric_id)

    def dimension(
        self,
        dimension_id: str,
        tenant_id: UUID,
    ) -> DimensionCatalogEntry | None:
        del tenant_id
        return self.dimensions.get(dimension_id)

    def entity(self, entity_id: str, tenant_id: UUID) -> EntityCatalogEntry | None:
        return self.entities.get((tenant_id, entity_id))

    def target(
        self,
        actual_metric_id: str,
        tenant_id: UUID,
    ) -> TargetCatalogEntry | None:
        return self.targets.get((tenant_id, actual_metric_id))

    def metric_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.metrics))


def default_comparison_catalog() -> StaticComparisonCatalog:
    metrics: dict[str, MetricCatalogEntry] = {}
    for metric_id, definition in METRIC_DEFINITIONS.items():
        unit, aggregation, group = _metric_semantics(metric_id)
        metrics[metric_id] = MetricCatalogEntry(
            metric_id=metric_id,
            metric_version="2026-07-20-rb-devolucao-transferencias",
            unit=unit,
            aggregation=aggregation,
            allowed_dimension_ids=DEFAULT_COMPARISON_DIMENSIONS,
            allowed_source_ids=_logical_sources(definition.source),
            supported=definition.supported,
            comparability_group=group,
        )
    dimensions = {
        dimension_id: DimensionCatalogEntry(
            dimension_id=dimension_id,
            allowed_source_ids=("vw_vendas_lm",),
            supported_granularities=(
                "DAY",
                "WEEK",
                "MONTH",
                "QUARTER",
                "SEMESTER",
                "YEAR",
                "CUSTOM",
            ),
        )
        for dimension_id in DEFAULT_COMPARISON_DIMENSIONS
    }
    return StaticComparisonCatalog(metrics=metrics, dimensions=dimensions)


def metric_reference_matches_catalog(
    reference: MetricReference,
    entry: MetricCatalogEntry,
) -> bool:
    return (
        reference.metric_id == entry.metric_id
        and reference.metric_version == entry.metric_version
        and reference.unit == entry.unit
        and reference.aggregation == entry.aggregation
    )


def _metric_semantics(metric_id: str) -> tuple[str, str, str]:
    if metric_id in {"ranking_vendedores", "ranking_clientes"}:
        return "BRL", "SUM", "currency"
    if metric_id in {"desconto_medio", "ticket_medio"}:
        return "BRL", "AVG", "currency"
    if metric_id == "lucro":
        return "BRL", "SUM", "currency"
    if metric_id == "vendas_nao_faturadas":
        return "BRL", "SUM", "currency"
    return "BRL", "SUM", "currency"


def _logical_sources(source: str) -> tuple[str, ...]:
    if source.lower().startswith("nao disponivel"):
        return ()
    names = re.findall(r"\bVW_[A-Z0-9_]+\b", source.upper())
    normalized = tuple(dict.fromkeys(name.lower() for name in names))
    return normalized or ("vw_vendas_lm",)
