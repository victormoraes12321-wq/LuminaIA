from __future__ import annotations

from decimal import Decimal
from typing import Any

from services.comparison_planning import MissingBucketPolicy, NullValuePolicy

from .catalog import ComparisonExecutionCatalog
from .models import (
    AlignedComparisonDataset,
    AlignedComparisonRow,
    CompiledOperandQuery,
    ComparisonExecutionContext,
    OperandExecutionResult,
    OperandExecutionStatus,
)


class ComparisonAlignmentError(ValueError):
    pass


def align_operand_results(
    queries: tuple[CompiledOperandQuery, ...],
    results: tuple[OperandExecutionResult, ...],
    context: ComparisonExecutionContext,
    catalog: ComparisonExecutionCatalog,
) -> tuple[AlignedComparisonDataset, ...]:
    successful = {
        item.operand_id: item
        for item in results
        if item.status in {
            OperandExecutionStatus.READY,
            OperandExecutionStatus.EMPTY,
            OperandExecutionStatus.TRUNCATED,
        }
    }
    query_by_operand = {item.operand_id: item for item in queries}
    metric_ids = tuple(
        dict.fromkeys(metric for query in queries for metric in query.metric_ids)
    )
    series = tuple(query.operand_id for query in queries)
    aligned: list[AlignedComparisonDataset] = []
    cross_metric = (
        len(metric_ids) > 1
        and len(queries) == len(metric_ids)
        and all(len(query.metric_ids) == 1 for query in queries)
    )
    metric_groups = (
        (
            (
                queries[0].metric_ids[0],
                {query.operand_id: query.metric_ids[0] for query in queries},
            ),
        )
        if cross_metric
        else tuple(
            (
                metric_id,
                {
                    query.operand_id: metric_id
                    for query in queries
                    if metric_id in query.metric_ids
                },
            )
            for metric_id in metric_ids
        )
    )

    for metric_id, operand_metric_ids in metric_groups:
        applicable_queries = tuple(
            query for query in queries if query.operand_id in operand_metric_ids
        )
        alignment_keys = applicable_queries[0].dimension_ids if applicable_queries else ()
        if any(query.dimension_ids != alignment_keys for query in applicable_queries):
            raise ComparisonAlignmentError(
                "Operands cannot be aligned at different dimension grains"
            )
        buckets: dict[tuple[str, ...], dict[str, Decimal | None]] = {}
        dimensions: dict[tuple[str, ...], dict[str, str | None]] = {}
        null_buckets: set[tuple[str, ...]] = set()
        seen: set[tuple[str, str, tuple[str, ...]]] = set()

        for query in applicable_queries:
            result = successful.get(query.operand_id)
            if result is None:
                continue
            for row in result.dataset:
                key = _alignment_key(row, alignment_keys)
                identity = (query.operand_id, metric_id, key)
                if identity in seen:
                    raise ComparisonAlignmentError(
                        "Duplicate canonical alignment key in operand result"
                    )
                seen.add(identity)
                value = _decimal_or_none(
                    row.get(operand_metric_ids[query.operand_id])
                )
                if value is None:
                    null_buckets.add(key)
                buckets.setdefault(key, {})[query.operand_id] = value
                dimensions[key] = {
                    item: _string_or_none(row.get(item)) for item in alignment_keys
                }

        if not alignment_keys and not buckets:
            buckets[("__all__",)] = {}
            dimensions[("__all__",)] = {}

        definitions = []
        for query in applicable_queries:
            source = catalog.source(query.source_id, context.tenant_id)
            physical_metric_id = operand_metric_ids[query.operand_id]
            if source is None or physical_metric_id not in source.metrics:
                raise ComparisonAlignmentError(
                    "Metric source disappeared during alignment"
                )
            definitions.append(source.metrics[physical_metric_id])
        units = {item.unit for item in definitions}
        if len(units) != 1:
            raise ComparisonAlignmentError(
                "Cross-metric operands use incompatible units"
            )
        additive = all(item.additive for item in definitions)
        missing: set[tuple[str, ...]] = set()
        rows: list[AlignedComparisonRow] = []
        for key in sorted(buckets):
            values = dict(buckets[key])
            absent = [operand_id for operand_id in series if operand_id not in values]
            if absent:
                missing.add(key)
            if context.missing_bucket_policy == MissingBucketPolicy.OMIT and absent:
                continue
            for operand_id in absent:
                values[operand_id] = (
                    Decimal("0")
                    if context.missing_bucket_policy == MissingBucketPolicy.ZERO_FILL
                    and additive
                    else None
                )
            for operand_id, value in tuple(values.items()):
                if value is None and context.null_policy == NullValuePolicy.ZERO_IF_ADDITIVE and additive:
                    values[operand_id] = Decimal("0")
                elif value is None and context.null_policy == NullValuePolicy.OMIT:
                    values.pop(operand_id)
            rows.append(
                AlignedComparisonRow(
                    alignment_key=key,
                    dimensions=dimensions[key],
                    values=values,
                )
            )
        aligned.append(
            AlignedComparisonDataset(
                dataset_id=f"comparison:{metric_id}",
                metric_id=metric_id,
                alignment_keys=alignment_keys,
                series=series,
                rows=tuple(rows),
                missing_buckets=tuple(sorted(missing)),
                null_buckets=tuple(sorted(null_buckets)),
                alignment_policy=(
                    f"{context.missing_bucket_policy.value}/"
                    f"{context.null_policy.value}/canonical_ids"
                ),
                row_count=len(rows),
                truncated=any(item.truncated for item in successful.values()),
                data_types={metric_id: "DECIMAL", **{item: "STRING" for item in alignment_keys}},
                units={metric_id: definitions[0].unit},
            )
        )
    return tuple(aligned)


def _alignment_key(row: dict[str, Any], keys: tuple[str, ...]) -> tuple[str, ...]:
    if not keys:
        return ("__all__",)
    return tuple("" if row.get(item) is None else str(row[item]) for item in keys)


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, str)):
        return Decimal(str(value))
    raise ComparisonAlignmentError("Metric value is not an exact decimal-compatible type")


def _string_or_none(value: Any) -> str | None:
    return None if value is None else str(value)
