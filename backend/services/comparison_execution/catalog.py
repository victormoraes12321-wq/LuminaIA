from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from services.metric_registry import METRIC_DEFINITIONS


_SAFE_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]*$")


@dataclass(frozen=True)
class MetricExecutionDefinition:
    metric_id: str
    expression: str
    version: str
    unit: str = "BRL"
    additive: bool = True


@dataclass(frozen=True)
class DimensionExecutionDefinition:
    dimension_id: str
    expression: str


@dataclass(frozen=True)
class SourceExecutionDefinition:
    source_id: str
    relation: str
    tenant_column: str
    date_column: str
    source_version: str
    metrics: dict[str, MetricExecutionDefinition]
    dimensions: dict[str, DimensionExecutionDefinition]
    permitted_tenant_ids: tuple[UUID, ...] = ()
    source_kind: str = "ANALYTICAL_CLONE"
    isolation_evidence: str = "tenant bind applied to governed tenant column"
    target_source: bool = False

    def __post_init__(self) -> None:
        for value in (self.source_id, self.relation, self.tenant_column, self.date_column):
            if not _SAFE_IDENTIFIER.fullmatch(value):
                raise ValueError(f"Unsafe governed identifier: {value!r}")
        if self.source_kind != "ANALYTICAL_CLONE":
            raise ValueError("Comparison sources must be PostgreSQL analytical clones")
        for metric in self.metrics.values():
            _validate_expression(metric.expression)
        for dimension in self.dimensions.values():
            _validate_expression(dimension.expression)


class ComparisonExecutionCatalog(Protocol):
    def source(self, source_id: str, tenant_id: UUID) -> SourceExecutionDefinition | None:
        ...


@dataclass(frozen=True)
class StaticComparisonExecutionCatalog:
    sources: dict[str, SourceExecutionDefinition] = field(default_factory=dict)

    def source(self, source_id: str, tenant_id: UUID) -> SourceExecutionDefinition | None:
        source = self.sources.get(source_id.lower())
        if source is None:
            return None
        if source.permitted_tenant_ids and tenant_id not in source.permitted_tenant_ids:
            return None
        return source


def default_comparison_execution_catalog() -> StaticComparisonExecutionCatalog:
    metric_version = "2026-07-20-rb-devolucao-transferencias"
    commercial = "tp_ IN (2, 61)"
    transfer = "(tp_ IN (3, 31, 96) OR UPPER(COALESCE(tpdescricao_, '')) LIKE '%TRANSFER%')"
    metrics = {
        "faturamento_comercial": _metric(
            "faturamento_comercial",
            f"SUM(CASE WHEN {commercial} THEN ptotal_ ELSE 0 END)",
            metric_version,
        ),
        "total_bruto": _metric(
            "total_bruto",
            f"SUM(CASE WHEN NOT {transfer} THEN ptotal_ ELSE 0 END)",
            metric_version,
        ),
        "faturamento_bruto": _metric(
            "faturamento_bruto",
            f"SUM(CASE WHEN NOT {transfer} THEN ptotal_ ELSE 0 END)",
            metric_version,
        ),
        "total_movimentos_view": _metric(
            "total_movimentos_view", "SUM(ptotal_)", metric_version
        ),
        "saida_rb": _metric(
            "saida_rb",
            "SUM(CASE WHEN tp_ = 9 OR UPPER(COALESCE(tpdescricao_, '')) LIKE '%SAIDA RB%' THEN ptotal_ ELSE 0 END)",
            metric_version,
        ),
        "devolucao": _metric(
            "devolucao",
            "SUM(CASE WHEN UPPER(COALESCE(tpdescricao_, '')) LIKE '%DEVOL%' THEN ptotal_ ELSE 0 END)",
            metric_version,
        ),
        "venda_bonificada": _metric(
            "venda_bonificada",
            "SUM(CASE WHEN tp_ = 22 OR UPPER(COALESCE(tpdescricao_, '')) LIKE '%BONIFIC%' THEN ptotal_ ELSE 0 END)",
            metric_version,
        ),
        "transferencias": _metric(
            "transferencias",
            f"SUM(CASE WHEN {transfer} THEN ptotal_ ELSE 0 END)",
            metric_version,
        ),
        "desconto_total": _metric(
            "desconto_total",
            f"SUM(CASE WHEN {commercial} THEN COALESCE(desconto_total, 0) ELSE 0 END)",
            metric_version,
        ),
        "desconto_medio": _metric(
            "desconto_medio",
            f"COALESCE(SUM(CASE WHEN {commercial} THEN COALESCE(desconto_total, 0) ELSE 0 END) / NULLIF(COUNT(DISTINCT CASE WHEN {commercial} THEN pedido_ END), 0), 0)",
            metric_version,
            additive=False,
        ),
        "ticket_medio": _metric(
            "ticket_medio",
            f"COALESCE(SUM(CASE WHEN {commercial} THEN ptotal_ ELSE 0 END) / NULLIF(COUNT(DISTINCT CASE WHEN {commercial} THEN pedido_ END), 0), 0)",
            metric_version,
            additive=False,
        ),
        "ranking_vendedores": _metric(
            "ranking_vendedores",
            f"SUM(CASE WHEN {commercial} THEN ptotal_ ELSE 0 END)",
            metric_version,
        ),
        "ranking_clientes": _metric(
            "ranking_clientes",
            f"SUM(CASE WHEN {commercial} THEN ptotal_ ELSE 0 END)",
            metric_version,
        ),
    }
    dimensions = {
        "filial": DimensionExecutionDefinition("filial", "filial_"),
        "produto": DimensionExecutionDefinition("produto", "codprod_"),
        "vendedor": DimensionExecutionDefinition("vendedor", "rca_"),
        "cliente": DimensionExecutionDefinition("cliente", "codcliente_"),
        "mes": DimensionExecutionDefinition("mes", "TO_CHAR(dtemissao_, 'YYYY-MM')"),
        "dia": DimensionExecutionDefinition("dia", "dtemissao_::text"),
        "ano": DimensionExecutionDefinition("ano", "EXTRACT(YEAR FROM dtemissao_)::integer"),
    }
    source = SourceExecutionDefinition(
        source_id="vw_vendas_lm",
        relation="vw_vendas_lm",
        tenant_column="tenant_id",
        date_column="dtemissao_",
        source_version=metric_version,
        metrics=metrics,
        dimensions=dimensions,
    )
    return StaticComparisonExecutionCatalog(sources={source.source_id: source})


def _metric(
    metric_id: str,
    expression: str,
    version: str,
    *,
    additive: bool = True,
) -> MetricExecutionDefinition:
    if metric_id in METRIC_DEFINITIONS:
        supported = METRIC_DEFINITIONS[metric_id].supported
        if not supported:
            raise ValueError(f"Unsupported metric cannot be executable: {metric_id}")
    return MetricExecutionDefinition(
        metric_id=metric_id,
        expression=expression,
        version=version,
        additive=additive,
    )


def _validate_expression(expression: str) -> None:
    lowered = f" {expression.lower()} "
    forbidden = (
        ";",
        "--",
        "/*",
        "*/",
        " insert ",
        " update ",
        " delete ",
        " drop ",
        " alter ",
        " create ",
        " grant ",
        " revoke ",
        " copy ",
        " select ",
        " union ",
        " into ",
        " returning ",
    )
    if any(token in lowered for token in forbidden):
        raise ValueError("Governed expression contains a forbidden SQL token")
