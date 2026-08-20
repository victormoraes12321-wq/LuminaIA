from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from contracts.analytical_v2 import (
    DataSourceKind,
    ExecutionProvenance,
    ExecutionReadiness,
    PlanOperation,
    QueryPlanV2,
    ValidationStatus,
)

from .alignment import ComparisonAlignmentError, align_operand_results
from .calculations import ComparisonMathError, calculate_comparison
from .catalog import (
    ComparisonExecutionCatalog,
    default_comparison_execution_catalog,
)
from .compiler import (
    ComparisonCompilationError,
    GovernedComparisonQueryCompiler,
    select_execution_strategy,
)
from .fingerprints import stable_fingerprint
from .graph import build_execution_graph
from .models import (
    COMPARISON_EXECUTOR_VERSION,
    CompiledOperandQuery,
    ComparisonExecutionContext,
    ComparisonExecutionIssue,
    ComparisonExecutionProvenance,
    ComparisonExecutionResult,
    ComparisonExecutionStatus,
    FailurePolicy,
    OperandExecutionResult,
    OperandExecutionStatus,
)
from .query_runner import ComparisonQueryRunner, TransientComparisonQueryError
from .validation import VALIDATION_VERSION, build_validation_report


logger = logging.getLogger(__name__)


class ComparisonExecutionRejected(ValueError):
    pass


class UniversalComparisonExecutor:
    def __init__(
        self,
        query_runner: ComparisonQueryRunner,
        *,
        catalog: ComparisonExecutionCatalog | None = None,
    ) -> None:
        self._runner = query_runner
        self._catalog = catalog or default_comparison_execution_catalog()
        self._compiler = GovernedComparisonQueryCompiler(self._catalog)
        self._local_cache: dict[str, tuple[OperandExecutionResult, ...]] = {}

    async def execute(
        self,
        plan: QueryPlanV2,
        context: ComparisonExecutionContext,
    ) -> ComparisonExecutionResult:
        started = time.perf_counter()
        self._validate_execution_boundary(plan, context)
        strategy = select_execution_strategy(plan)
        graph = build_execution_graph(plan, context, strategy)
        plan_id = stable_fingerprint(plan)
        try:
            queries = self._compiler.compile(plan, context, strategy)
        except ComparisonCompilationError as exc:
            raise ComparisonExecutionRejected(str(exc)) from exc

        cache_key = stable_fingerprint(
            {
                "plan": plan_id,
                "tenant": str(context.tenant_id),
                "permission": context.permission_fingerprint,
                "source_version": context.source_version,
                "executor": COMPARISON_EXECUTOR_VERSION,
                "rounding": context.rounding_policy.value,
                "precision": context.decimal_precision,
                "zero": context.zero_denominator_policy.value,
                "missing": context.missing_bucket_policy.value,
                "null": context.null_policy.value,
                "queries": [item.query_fingerprint for item in queries],
            }
        )
        cache_enabled = context.feature_flags.get(
            "comparison_executor_local_cache", False
        )
        if cache_enabled and cache_key in self._local_cache:
            operands = tuple(
                item.model_copy(update={"duration_ms": Decimal("0")})
                for item in self._local_cache[cache_key]
            )
            cache_status = "HIT"
        else:
            operands = await self._execute_all(queries, context)
            cache_status = "MISS" if cache_enabled else "BYPASS"
            if cache_enabled and all(
                item.status in {OperandExecutionStatus.READY, OperandExecutionStatus.EMPTY}
                for item in operands
            ):
                self._local_cache[cache_key] = operands

        total_rows = sum(item.row_count for item in operands)
        if total_rows > context.maximum_total_rows:
            raise ComparisonExecutionRejected("Total row budget exceeded")
        payload_size = len(
            json.dumps(
                [item.dataset for item in operands],
                default=str,
                ensure_ascii=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        if payload_size > context.maximum_payload_bytes:
            raise ComparisonExecutionRejected("Payload budget exceeded")

        try:
            aligned = align_operand_results(
                queries, operands, context, self._catalog
            )
            calculations = calculate_comparison(plan, aligned, context)
        except (ComparisonAlignmentError, ComparisonMathError) as exc:
            raise ComparisonExecutionRejected(str(exc)) from exc

        validation = build_validation_report(
            context,
            operands,
            calculations,
            expected_operand_count=len(queries),
        )
        provenance = tuple(
            self._provenance(
                plan,
                context,
                graph.graph_fingerprint,
                plan_id,
                query,
                cache_status,
            )
            for query, operand in zip(queries, operands, strict=True)
            if operand.status
            in {
                OperandExecutionStatus.READY,
                OperandExecutionStatus.EMPTY,
                OperandExecutionStatus.TRUNCATED,
            }
        )
        provenance_by_operand = {
            query.operand_id: item
            for query, item in zip(
                (
                    query
                    for query, operand in zip(queries, operands, strict=True)
                    if operand.status
                    in {
                        OperandExecutionStatus.READY,
                        OperandExecutionStatus.EMPTY,
                        OperandExecutionStatus.TRUNCATED,
                    }
                ),
                provenance,
                strict=True,
            )
        }
        operands = tuple(
            item.model_copy(
                update={
                    "provenance": provenance_by_operand.get(item.operand_id),
                    "validation": validation,
                }
            )
            for item in operands
        )
        failures = tuple(
            item
            for item in operands
            if item.status
            in {
                OperandExecutionStatus.FAILED,
                OperandExecutionStatus.TIMED_OUT,
                OperandExecutionStatus.BLOCKED,
            }
        )
        truncated = any(item.truncated for item in operands)
        if failures and context.failure_policy == FailurePolicy.ALLOW_PARTIAL:
            status = ComparisonExecutionStatus.PARTIAL
        elif failures:
            status = ComparisonExecutionStatus.FAILED
        elif truncated:
            status = ComparisonExecutionStatus.PARTIAL
        elif validation.status == ValidationStatus.FAILED:
            status = ComparisonExecutionStatus.FAILED
        else:
            status = ComparisonExecutionStatus.READY
        issues = tuple(self._failure_issue(item) for item in failures)
        warnings = tuple(
            message
            for item in operands
            for message in item.warnings
        ) + (("Um ou mais datasets foram truncados.",) if truncated else ())
        duration_ms = Decimal(str((time.perf_counter() - started) * 1000))
        result = ComparisonExecutionResult(
            status=status,
            plan_id=plan_id,
            execution_id=uuid4(),
            comparison_kind=plan.comparison.kind,
            operands=operands,
            aligned_datasets=aligned,
            calculations=calculations,
            summary_values=_summary_values(calculations),
            provenance=provenance,
            validation=validation,
            warnings=warnings,
            errors=issues,
            partial=status == ComparisonExecutionStatus.PARTIAL,
            duration_ms=duration_ms,
            strategy_used=strategy,
            cache_status=cache_status,
        )
        logger.info(
            "comparison_execution executor=%s plan=%s graph=%s strategy=%s "
            "tenant=%s permission=%s operands=%d queries=%d rows=%d duration_ms=%.3f "
            "cache=%s partial=%s validation=%s issues=%s",
            COMPARISON_EXECUTOR_VERSION,
            plan_id,
            graph.graph_fingerprint,
            strategy.value,
            stable_fingerprint(str(context.tenant_id)),
            stable_fingerprint(context.permission_fingerprint),
            len(operands),
            len(queries),
            total_rows,
            float(duration_ms),
            cache_status,
            result.partial,
            validation.status.value,
            [item.code for item in issues],
        )
        return result

    def _validate_execution_boundary(
        self,
        plan: QueryPlanV2,
        context: ComparisonExecutionContext,
    ) -> None:
        if plan.comparison is None or plan.operation != PlanOperation.COMPARE:
            raise ComparisonExecutionRejected("Only comparison plans are executable")
        if plan.intent.readiness != ExecutionReadiness.READY:
            raise ComparisonExecutionRejected("Only READY plans are executable")
        if plan.scope is None:
            raise ComparisonExecutionRejected("Trusted tenant scope is required")
        if plan.scope.tenant_id != context.tenant_id:
            raise ComparisonExecutionRejected("Plan tenant does not match authenticated tenant")
        if plan.scope.permission_fingerprint != context.permission_fingerprint:
            raise ComparisonExecutionRejected("Permission fingerprint mismatch")
        if not set(item.source_id for item in plan.source_refs).issubset(
            set(context.allowed_source_ids)
        ):
            raise ComparisonExecutionRejected("Plan source is outside trusted permissions")
        if any("oracle" in item.source_id.lower() for item in plan.source_refs):
            raise ComparisonExecutionRejected("Oracle is not an analytical execution source")
        if self._runner.source_kind != "ANALYTICAL_CLONE":
            raise ComparisonExecutionRejected("Runner is not an analytical PostgreSQL clone")
        if not self._runner.tenant_isolation_verified:
            raise ComparisonExecutionRejected("Runner has no verified tenant isolation")

    async def _execute_all(
        self,
        queries: tuple[CompiledOperandQuery, ...],
        context: ComparisonExecutionContext,
    ) -> tuple[OperandExecutionResult, ...]:
        semaphore = asyncio.Semaphore(context.maximum_concurrency)

        async def run(query: CompiledOperandQuery) -> OperandExecutionResult:
            async with semaphore:
                return await self._execute_operand(query)

        try:
            async with asyncio.timeout(float(context.total_timeout_seconds)):
                values = await asyncio.gather(*(run(query) for query in queries))
        except TimeoutError:
            return tuple(
                OperandExecutionResult(
                    operand_id=query.operand_id,
                    status=OperandExecutionStatus.TIMED_OUT,
                    row_count=0,
                    duration_ms=Decimal(str(context.total_timeout_seconds * 1000)),
                    query_fingerprint=query.query_fingerprint,
                    source_version=context.source_version,
                    errors=("Tempo total da comparacao excedido.",),
                )
                for query in queries
            )
        return tuple(values)

    async def _execute_operand(
        self,
        query: CompiledOperandQuery,
    ) -> OperandExecutionResult:
        started = time.perf_counter()
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                async with asyncio.timeout(float(query.timeout_seconds)):
                    rows = await self._runner.execute(query)
                truncated = len(rows) > query.row_limit
                rows = rows[: query.row_limit]
                normalized = tuple(
                    _normalize_row(row, query.metric_ids, query.expected_columns)
                    for row in rows
                )
                status = (
                    OperandExecutionStatus.TRUNCATED
                    if truncated
                    else OperandExecutionStatus.READY
                    if normalized
                    else OperandExecutionStatus.EMPTY
                )
                return OperandExecutionResult(
                    operand_id=query.operand_id,
                    status=status,
                    dataset=normalized,
                    row_count=len(normalized),
                    truncated=truncated,
                    duration_ms=Decimal(str((time.perf_counter() - started) * 1000)),
                    query_fingerprint=query.query_fingerprint,
                    source_version=self._source_version(query.source_id),
                    warnings=("Dataset truncado no limite autorizado.",) if truncated else (),
                )
            except TransientComparisonQueryError as exc:
                last_error = exc
                if attempt == 0:
                    await asyncio.sleep(0)
                    continue
            except TimeoutError as exc:
                return OperandExecutionResult(
                    operand_id=query.operand_id,
                    status=OperandExecutionStatus.TIMED_OUT,
                    row_count=0,
                    duration_ms=Decimal(str((time.perf_counter() - started) * 1000)),
                    query_fingerprint=query.query_fingerprint,
                    source_version=self._source_version(query.source_id),
                    errors=("Tempo limite do operando excedido.",),
                )
            except Exception as exc:
                last_error = exc
                break
        return OperandExecutionResult(
            operand_id=query.operand_id,
            status=OperandExecutionStatus.FAILED,
            row_count=0,
            duration_ms=Decimal(str((time.perf_counter() - started) * 1000)),
            query_fingerprint=query.query_fingerprint,
            source_version=self._source_version(query.source_id),
            errors=(f"Falha controlada do operando: {type(last_error).__name__}",),
        )

    def _source_version(self, source_id: str) -> str:
        # Tenant is already enforced at compile time; source version is immutable.
        for source in getattr(self._catalog, "sources", {}).values():
            if source.source_id == source_id:
                return source.source_version
        return "unknown"

    def _provenance(
        self,
        plan: QueryPlanV2,
        context: ComparisonExecutionContext,
        graph_fingerprint: str,
        plan_fingerprint: str,
        query: CompiledOperandQuery,
        cache_status: str,
    ) -> ComparisonExecutionProvenance:
        planner_metadata = plan.contract.extensions.get("comparison_planner")
        planner_version = (
            str(planner_metadata.get("planner_version", "unknown"))
            if isinstance(planner_metadata, dict)
            else "unknown"
        )
        temporal_metadata = plan.intent.contract.extensions.get("temporal")
        temporal_version = (
            str(temporal_metadata.get("normalizer_version"))
            if isinstance(temporal_metadata, dict)
            and temporal_metadata.get("normalizer_version")
            else None
        )
        metric_versions = {
            metric.metric_id: metric.metric_version
            for metric in plan.metric_refs
            if metric.metric_id in query.metric_ids
        }
        public = ExecutionProvenance(
            tenant_id=context.tenant_id,
            source_id=query.source_id,
            source_kind=DataSourceKind.ANALYTICAL_CLONE,
            view_ids=[query.source_id],
            metric_versions=metric_versions,
            filter_fingerprint=stable_fingerprint(
                [item.model_dump(mode="json") for item in query.logical_filters]
            ),
            periods=list(query.time_windows),
            executed_at=datetime.now(timezone.utc),
            sync_version=context.sync_version or context.source_version,
            cache_status=cache_status,
            pipeline=plan.contract.pipeline,
            query_fingerprint=query.query_fingerprint,
            reconciliation_status="NOT_REQUESTED",
            tenant_isolation_verified=True,
            tenant_isolation_evidence=self._runner.isolation_evidence,
        )
        return ComparisonExecutionProvenance(
            public=public,
            plan_fingerprint=plan_fingerprint,
            graph_fingerprint=graph_fingerprint,
            operand_fingerprints={query.operand_id: query.query_fingerprint},
            planner_version=planner_version,
            temporal_version=temporal_version,
            validation_version=VALIDATION_VERSION,
            source_version=context.source_version,
            source_isolation=self._runner.isolation_evidence,
        )

    def _failure_issue(
        self,
        operand: OperandExecutionResult,
    ) -> ComparisonExecutionIssue:
        code = (
            "OPERAND_TIMEOUT"
            if operand.status == OperandExecutionStatus.TIMED_OUT
            else "OPERAND_EXECUTION_FAILED"
        )
        return ComparisonExecutionIssue(
            issue_id=f"execution:{operand.operand_id}:{code.lower()}",
            code=code,
            severity="ERROR",
            message=f"Operando {operand.operand_id} nao foi concluido.",
            node_id=f"query:{operand.operand_id}",
            operand_id=operand.operand_id,
            blocks_result=True,
            public_message="Uma parte obrigatoria da comparacao nao pode ser calculada.",
            evidence_reference=f"operand:{operand.operand_id}",
        )


def _normalize_row(
    row: dict[str, Any],
    metric_ids: tuple[str, ...],
    expected_columns: tuple[str, ...],
) -> dict[str, Any]:
    missing = set(expected_columns) - set(row)
    if missing:
        raise ValueError("Analytical source omitted expected governed columns")
    normalized: dict[str, Any] = {}
    for key in expected_columns:
        value = row[key]
        if key in metric_ids:
            if value is None:
                normalized[key] = None
            elif isinstance(value, Decimal):
                normalized[key] = value
            elif isinstance(value, int):
                normalized[key] = Decimal(value)
            elif isinstance(value, str):
                normalized[key] = Decimal(value)
            else:
                raise ValueError("Metric source returned an inexact numeric type")
        else:
            normalized[key] = None if value is None else str(value)
    return normalized


def _summary_values(
    calculations: tuple[Any, ...],
) -> dict[str, Decimal | str | None]:
    summary: dict[str, Decimal | str | None] = {}
    for item in calculations:
        key = (
            f"{item.metric_id}:{item.target_operand_id}:"
            f"{item.calculation.value}:{'|'.join(item.alignment_key)}"
        )
        summary[key] = (
            item.direction.value
            if item.calculation.value == "DIRECTION"
            else item.result_value
        )
    return summary
