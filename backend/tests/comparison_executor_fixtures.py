from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from contracts.analytical_v2 import (
    ComparisonCalculation,
    ComparisonKind,
    ComparisonOperand,
    ComparisonSpecification,
    ClarificationRequest,
    ConfidenceAssessment,
    ConfidenceLevel,
    ContractMetadata,
    DataSourceKind,
    DimensionReference,
    DimensionRole,
    ExecutionReadiness,
    ExecutionScope,
    FieldOrigin,
    IntentKind,
    MetricReference,
    PipelineKind,
    PlanOperation,
    QueryIntentV2,
    QueryPlanV2,
    SourceReference,
    TemporalGranularity,
    TimeWindow,
)
from services.comparison_execution import ComparisonExecutionContext


METRIC_VERSION = "2026-07-20-rb-devolucao-transferencias"
SOURCE_VERSION = METRIC_VERSION
PERMISSION = "permission:comparison:test"


def confidence() -> ConfidenceAssessment:
    return ConfidenceAssessment(
        level=ConfidenceLevel.HIGH,
        score=Decimal("1"),
        reasons=["Resolved by deterministic test fixture."],
        requires_confirmation=False,
    )


def metric(metric_id: str = "faturamento_comercial") -> MetricReference:
    return MetricReference(
        metric_id=metric_id,
        metric_version=METRIC_VERSION,
        display_name=metric_id.replace("_", " ").title(),
        unit="BRL",
        aggregation="SUM",
        origin=FieldOrigin.EXPLICIT_USER,
        confidence=confidence(),
    )


def month_window(year: int, month: int, window_id: str) -> TimeWindow:
    next_month = (
        date(year + 1, 1, 1)
        if month == 12
        else date(year, month + 1, 1)
    )
    return TimeWindow(
        window_id=window_id,
        label=f"{month:02d}/{year}",
        start=date(year, month, 1),
        end=next_month - timedelta(days=1),
        end_inclusive=True,
        granularity=TemporalGranularity.MONTH,
        timezone="America/Sao_Paulo",
        origin=FieldOrigin.EXPLICIT_USER,
        confidence=confidence(),
        raw_expression=f"{month:02d}/{year}",
    )


def make_plan(
    tenant_id: UUID,
    *,
    periods: tuple[tuple[str, int, int], ...] = (
        ("june", 2026, 6),
        ("july", 2026, 7),
    ),
    metric_ids: tuple[str, ...] = ("faturamento_comercial",),
    calculations: tuple[ComparisonCalculation, ...] = (
        ComparisonCalculation.VALUE,
        ComparisonCalculation.ABSOLUTE_DIFFERENCE,
        ComparisonCalculation.PERCENTAGE_DIFFERENCE,
        ComparisonCalculation.DIRECTION,
    ),
    kind: ComparisonKind = ComparisonKind.PERIOD_VS_PERIOD,
    baseline: str | None = "june",
    dimensions: tuple[str, ...] = (),
    readiness: ExecutionReadiness = ExecutionReadiness.READY,
    source_ids: tuple[str, ...] = ("vw_vendas_lm",),
    permission_fingerprint: str = PERMISSION,
) -> QueryPlanV2:
    metric_refs = [metric(item) for item in metric_ids]
    windows = [
        month_window(year, month, f"window_{operand_id}")
        for operand_id, year, month in periods
    ]
    operands = [
        ComparisonOperand(
            operand_id=operand_id,
            label=operand_id.title(),
            metric_refs=metric_refs if len(metric_ids) > 1 else [],
            time_windows=[window],
            origin=FieldOrigin.EXPLICIT_USER,
        )
        for (operand_id, _, _), window in zip(periods, windows, strict=True)
    ]
    comparison = ComparisonSpecification(
        comparison_id="comparison_test",
        kind=kind,
        operands=operands,
        calculations=list(calculations),
        baseline_operand_id=baseline,
        alignment_dimensions=list(dimensions),
        origin=FieldOrigin.EXPLICIT_USER,
        confidence=confidence(),
    )
    dimension_refs = [
        DimensionReference(
            dimension_id=item,
            display_name=item.title(),
            role=DimensionRole.GROUPING,
            origin=FieldOrigin.EXPLICIT_USER,
            confidence=confidence(),
        )
        for item in dimensions
    ]
    intent = QueryIntentV2(
        contract=ContractMetadata(
            pipeline=PipelineKind.NEW,
            extensions={
                "temporal": {
                    "normalizer_version": "lumina.temporal.pt-BR/1.0"
                }
            },
        ),
        intent_kind=IntentKind.COMPARISON,
        readiness=readiness,
        raw_question="Compare junho com julho de 2026",
        normalized_question="compare junho com julho de 2026",
        metric_refs=metric_refs,
        dimension_refs=dimension_refs,
        filters=[],
        time_windows=windows,
        comparison=comparison,
        requested_visualizations=[],
        confidence=confidence(),
        clarification=(
            ClarificationRequest(
                question="Qual periodo deve ser comparado?",
                missing_fields=["comparison_period"],
                candidate_options=["Junho", "Julho"],
                reason="O periodo comparativo precisa ser confirmado.",
                confidence=confidence(),
            )
            if readiness == ExecutionReadiness.CLARIFICATION_REQUIRED
            else None
        ),
        field_origins={
            "raw_question": FieldOrigin.EXPLICIT_USER,
            "intent_kind": FieldOrigin.SYSTEM_GENERATED,
        },
    )
    return QueryPlanV2(
        contract=ContractMetadata(
            pipeline=PipelineKind.NEW,
            adapter_used="comparison_planner_v2",
            extensions={
                "comparison_planner": {
                    "planner_version": "lumina.comparison-planner/1.0",
                    "strategy_hint": "CONDITIONAL_AGGREGATION",
                }
            },
        ),
        scope=ExecutionScope(
            tenant_id=tenant_id,
            user_role="CONSULTA",
            session_id="comparison-test",
            allowed_source_ids=list(source_ids),
            permission_fingerprint=permission_fingerprint,
            origin=FieldOrigin.SYSTEM_GENERATED,
        ),
        intent=intent,
        operation=PlanOperation.COMPARE if readiness == ExecutionReadiness.READY else PlanOperation.NONE,
        metric_refs=metric_refs,
        dimension_refs=dimension_refs,
        filters=[],
        time_windows=windows,
        comparison=comparison,
        visualizations=[],
        source_refs=[
            SourceReference(
                source_id=item,
                source_kind=DataSourceKind.ANALYTICAL_CLONE,
                origin=FieldOrigin.SYSTEM_GENERATED,
            )
            for item in source_ids
        ],
        confidence=confidence(),
        validation_requirements=[
            "tenant_scope",
            "metric_registry",
            "mathematical_consistency",
        ],
    )


def execution_context(
    tenant_id: UUID,
    *,
    metric_ids: tuple[str, ...] = (
        "faturamento_comercial",
        "total_bruto",
        "faturamento_bruto",
        "saida_rb",
        "devolucao",
        "venda_bonificada",
        "transferencias",
        "desconto_total",
        "desconto_medio",
        "ticket_medio",
        "ranking_vendedores",
        "ranking_clientes",
    ),
    permission_fingerprint: str = PERMISSION,
    **updates,
) -> ComparisonExecutionContext:
    values = {
        "tenant_id": tenant_id,
        "user_role": "CONSULTA",
        "session_id": "comparison-test",
        "permission_fingerprint": permission_fingerprint,
        "allowed_source_ids": ("vw_vendas_lm",),
        "allowed_metric_ids": metric_ids,
        "allowed_dimension_ids": (
            "filial",
            "produto",
            "vendedor",
            "cliente",
            "mes",
            "dia",
            "ano",
        ),
        "source_version": SOURCE_VERSION,
    }
    values.update(updates)
    return ComparisonExecutionContext(**values)
