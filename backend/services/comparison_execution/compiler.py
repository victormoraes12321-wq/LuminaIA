from __future__ import annotations

from collections.abc import Iterable
from datetime import timedelta
from typing import Any

from contracts.analytical_v2 import (
    ComparisonKind,
    ComparisonOperand,
    FilterOperator,
    FilterSpecification,
    QueryPlanV2,
)

from .catalog import (
    ComparisonExecutionCatalog,
    SourceExecutionDefinition,
)
from .fingerprints import stable_fingerprint
from .models import (
    CompiledOperandQuery,
    ComparisonExecutionContext,
    ComparisonExecutionStrategy,
)


class ComparisonCompilationError(ValueError):
    pass


_OPERATORS = {
    FilterOperator.EQ: "=",
    FilterOperator.NE: "<>",
    FilterOperator.GT: ">",
    FilterOperator.GTE: ">=",
    FilterOperator.LT: "<",
    FilterOperator.LTE: "<=",
}


class GovernedComparisonQueryCompiler:
    def __init__(self, catalog: ComparisonExecutionCatalog) -> None:
        self._catalog = catalog

    def compile(
        self,
        plan: QueryPlanV2,
        context: ComparisonExecutionContext,
        strategy: ComparisonExecutionStrategy,
    ) -> tuple[CompiledOperandQuery, ...]:
        comparison = plan.comparison
        if comparison is None:
            raise ComparisonCompilationError("Comparison specification is required")
        if len(comparison.operands) > context.maximum_operands:
            raise ComparisonCompilationError("Operand budget exceeded")

        compiled = tuple(
            self._compile_operand(plan, operand, context, strategy)
            for operand in comparison.operands
        )
        if len(compiled) > context.maximum_queries:
            raise ComparisonCompilationError("Query budget exceeded")
        return compiled

    def _compile_operand(
        self,
        plan: QueryPlanV2,
        operand: ComparisonOperand,
        context: ComparisonExecutionContext,
        strategy: ComparisonExecutionStrategy,
    ) -> CompiledOperandQuery:
        metrics = tuple(operand.metric_refs or plan.metric_refs)
        if not metrics:
            raise ComparisonCompilationError(
                f"Operand {operand.operand_id} has no governed metric"
            )
        metric_ids = tuple(item.metric_id for item in metrics)
        if any(metric_id not in context.allowed_metric_ids for metric_id in metric_ids):
            raise ComparisonCompilationError("Metric is not permitted by trusted context")

        dimension_ids = tuple(item.dimension_id for item in plan.dimension_refs)
        if any(item not in context.allowed_dimension_ids for item in dimension_ids):
            raise ComparisonCompilationError("Dimension is not permitted by trusted context")
        if set(plan.comparison.alignment_dimensions) - set(dimension_ids):
            raise ComparisonCompilationError(
                "Alignment dimensions must be present in the governed plan dimensions"
            )

        source = self._select_source(plan, metric_ids, dimension_ids, context)
        select_parts = [
            f"{source.dimensions[item].expression} AS {item}"
            for item in dimension_ids
        ]
        select_parts.extend(
            f"{source.metrics[item].expression} AS {item}" for item in metric_ids
        )
        if not select_parts:
            raise ComparisonCompilationError("Compiled query has no selected fields")

        binds: dict[str, Any] = {"tenant_id": context.tenant_id}
        where = [f"{source.tenant_column} = :tenant_id"]
        windows = tuple(operand.time_windows or plan.time_windows)
        if windows:
            window_parts: list[str] = []
            for index, window in enumerate(windows):
                start_name = f"window_start_{index}"
                end_name = f"window_end_{index}"
                end = window.end + timedelta(days=1) if window.end_inclusive else window.end
                window_parts.append(
                    f"({source.date_column} >= :{start_name} AND "
                    f"{source.date_column} < :{end_name})"
                )
                binds[start_name] = window.start
                binds[end_name] = end
            where.append(f"({' OR '.join(window_parts)})")

        logical_filters = tuple([*plan.filters, *operand.filters])
        for index, item in enumerate(logical_filters):
            where.append(self._compile_filter(item, source, binds, index))
        for entity_index, entity in enumerate(operand.entity_refs):
            where.append(
                self._compile_entity_filter(
                    entity.entity_id,
                    source,
                    context,
                    binds,
                    entity_index,
                )
            )

        group_by = (
            " GROUP BY " + ", ".join(
                source.dimensions[item].expression for item in dimension_ids
            )
            if dimension_ids
            else ""
        )
        order_by = (
            " ORDER BY " + ", ".join(dimension_ids)
            if dimension_ids
            else ""
        )
        row_limit = min(context.maximum_rows_per_operand, plan.limit or context.maximum_rows_per_operand)
        binds["row_limit"] = row_limit + 1
        statement = (
            f"SELECT {', '.join(select_parts)} "
            f"FROM {source.relation} "
            f"WHERE {' AND '.join(where)}"
            f"{group_by}{order_by} LIMIT :row_limit"
        )
        fingerprint = stable_fingerprint(
            {
                "operand_id": operand.operand_id,
                "source": source.source_id,
                "metrics": metric_ids,
                "dimensions": dimension_ids,
                "filters": [item.model_dump(mode="json") for item in logical_filters],
                "windows": [item.model_dump(mode="json") for item in windows],
                "entities": [item.entity_id for item in operand.entity_refs],
                "tenant_id": str(context.tenant_id),
                "permission": context.permission_fingerprint,
                "source_version": context.source_version,
                "statement_shape": statement,
            }
        )
        return CompiledOperandQuery(
            operand_id=operand.operand_id,
            source_id=source.source_id,
            metric_ids=metric_ids,
            dimension_ids=dimension_ids,
            logical_filters=logical_filters,
            time_windows=windows,
            statement=statement,
            binds=binds,
            expected_columns=tuple([*dimension_ids, *metric_ids]),
            query_fingerprint=fingerprint,
            timeout_seconds=context.query_timeout_seconds,
            row_limit=row_limit,
            strategy=strategy,
        )

    def _select_source(
        self,
        plan: QueryPlanV2,
        metric_ids: tuple[str, ...],
        dimension_ids: tuple[str, ...],
        context: ComparisonExecutionContext,
    ) -> SourceExecutionDefinition:
        candidates = [
            item.source_id.lower()
            for item in plan.source_refs
            if item.source_id.lower() in context.allowed_source_ids
        ]
        if not candidates:
            raise ComparisonCompilationError("No permitted analytical source in plan")
        for source_id in candidates:
            source = self._catalog.source(source_id, context.tenant_id)
            if source is None:
                continue
            if source.source_kind != "ANALYTICAL_CLONE":
                continue
            if source.source_version != context.source_version:
                continue
            if all(item in source.metrics for item in metric_ids) and all(
                item in source.dimensions for item in dimension_ids
            ):
                return source
        raise ComparisonCompilationError(
            "No governed tenant-scoped PostgreSQL source satisfies this operand"
        )

    def _compile_filter(
        self,
        item: FilterSpecification,
        source: SourceExecutionDefinition,
        binds: dict[str, Any],
        index: int,
    ) -> str:
        definition = source.dimensions.get(item.field_id)
        if definition is None:
            raise ComparisonCompilationError(
                f"Filter field is not an allowlisted dimension: {item.field_id}"
            )
        expression = definition.expression
        bind_name = f"filter_{index}"
        if item.operator in _OPERATORS:
            binds[bind_name] = item.value
            return f"{expression} {_OPERATORS[item.operator]} :{bind_name}"
        if item.operator in {FilterOperator.IN, FilterOperator.NOT_IN}:
            placeholders: list[str] = []
            for value_index, value in enumerate(item.values):
                name = f"{bind_name}_{value_index}"
                binds[name] = value
                placeholders.append(f":{name}")
            keyword = "IN" if item.operator == FilterOperator.IN else "NOT IN"
            return f"{expression} {keyword} ({', '.join(placeholders)})"
        if item.operator == FilterOperator.BETWEEN:
            low, high = item.values
            binds[f"{bind_name}_low"] = low
            binds[f"{bind_name}_high"] = high
            return (
                f"{expression} BETWEEN :{bind_name}_low AND :{bind_name}_high"
            )
        if item.operator in {FilterOperator.CONTAINS, FilterOperator.STARTS_WITH}:
            value = str(item.value)
            binds[bind_name] = f"%{value}%" if item.operator == FilterOperator.CONTAINS else f"{value}%"
            return f"CAST({expression} AS TEXT) ILIKE :{bind_name}"
        if item.operator == FilterOperator.IS_NULL:
            return f"{expression} IS NULL"
        if item.operator == FilterOperator.IS_NOT_NULL:
            return f"{expression} IS NOT NULL"
        raise ComparisonCompilationError(f"Unsupported filter operator: {item.operator}")

    def _compile_entity_filter(
        self,
        entity_id: str,
        source: SourceExecutionDefinition,
        context: ComparisonExecutionContext,
        binds: dict[str, Any],
        index: int,
    ) -> str:
        entity_type, separator, fallback_value = entity_id.partition(":")
        definition = source.dimensions.get(entity_type)
        if not separator or definition is None:
            raise ComparisonCompilationError(
                f"Entity is not resolvable by a governed dimension: {entity_id}"
            )
        value = context.entity_values.get(entity_id, fallback_value)
        if not value:
            raise ComparisonCompilationError(f"Entity has no governed value: {entity_id}")
        bind_name = f"entity_{index}"
        binds[bind_name] = value
        return f"{definition.expression} = :{bind_name}"


def select_execution_strategy(plan: QueryPlanV2) -> ComparisonExecutionStrategy:
    comparison = plan.comparison
    if comparison is None:
        raise ComparisonCompilationError("Comparison specification is required")
    metadata = plan.contract.extensions.get("comparison_planner")
    hint = metadata.get("strategy_hint") if isinstance(metadata, dict) else None
    if isinstance(hint, str):
        try:
            strategy = ComparisonExecutionStrategy(hint)
        except ValueError:
            strategy = ComparisonExecutionStrategy.MULTI_QUERY
    else:
        strategy = ComparisonExecutionStrategy.MULTI_QUERY

    source_ids = {item.source_id for item in plan.source_refs}
    if comparison.kind == ComparisonKind.ACTUAL_VS_TARGET:
        return ComparisonExecutionStrategy.TARGET_JOIN
    if len(source_ids) > 1:
        return ComparisonExecutionStrategy.MULTI_QUERY
    if plan.dimension_refs and strategy == ComparisonExecutionStrategy.SINGLE_AGGREGATION:
        return ComparisonExecutionStrategy.GROUPED_SERIES
    return strategy
