from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest

from contracts.analytical_v2 import (
    ComparisonCalculation,
    ComparisonKind,
    ComparisonOperand,
    ComparisonSpecification,
    DataSourceKind,
    EntityReference,
    FieldOrigin,
    FilterOperator,
    FilterSpecification,
    QueryIntentV2,
    QueryPlanV2,
    SourceReference,
)
from services.comparison_execution import (
    ComparisonExecutionRejected,
    ComparisonExecutionStatus,
    ComparisonExecutionStrategy,
    GovernedComparisonQueryCompiler,
    MetricExecutionDefinition,
    SourceExecutionDefinition,
    StaticComparisonExecutionCatalog,
    UniversalComparisonExecutor,
    default_comparison_execution_catalog,
    select_execution_strategy,
)
from services.comparison_execution.models import (
    ComparisonExecutionContext,
)

from comparison_executor_fixtures import (
    METRIC_VERSION,
    confidence,
    execution_context,
    make_plan,
    metric,
    month_window,
)


TENANT_A = UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")
TENANT_B = UUID("b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22")


class MatrixRunner:
    source_kind = "ANALYTICAL_CLONE"
    tenant_isolation_verified = True
    isolation_evidence = "matrix runner with tenant-scoped fixtures"

    def __init__(self, *, rows_per_query=1):
        self.calls = []
        self.rows_per_query = rows_per_query

    async def execute(self, query):
        self.calls.append(query)
        month = query.binds.get("window_start_0").month
        rows = []
        for index in range(self.rows_per_query):
            rows.append(
                {
                    **{
                        dimension: (
                            str(index + 1)
                            if dimension != "mes"
                            else f"2026-{month:02d}"
                        )
                        for dimension in query.dimension_ids
                    },
                    **{
                        metric_id: Decimal(month * 100 + index)
                        for metric_id in query.metric_ids
                    },
                }
            )
        return rows


PERIOD_CASES = [
    ((("p1", 2024, 1), ("p2", 2024, 2)), "p1"),
    ((("p1", 2024, 2), ("p2", 2024, 3)), "p1"),
    ((("p1", 2024, 12), ("p2", 2025, 1)), "p1"),
    ((("p1", 2025, 1), ("p2", 2025, 12)), "p1"),
    ((("p1", 2025, 6), ("p2", 2026, 6)), "p1"),
    ((("p1", 2026, 1), ("p2", 2026, 2)), "p1"),
    ((("p1", 2026, 2), ("p2", 2026, 3)), "p1"),
    ((("p1", 2026, 3), ("p2", 2026, 4)), "p1"),
    ((("p1", 2026, 4), ("p2", 2026, 5)), "p1"),
    ((("p1", 2026, 5), ("p2", 2026, 6)), "p1"),
    ((("p1", 2026, 6), ("p2", 2026, 7)), "p1"),
    ((("p1", 2026, 7), ("p2", 2026, 8)), "p1"),
    ((("p1", 2026, 8), ("p2", 2026, 9)), "p1"),
    ((("p1", 2026, 9), ("p2", 2026, 10)), "p1"),
    ((("p1", 2026, 10), ("p2", 2026, 11)), "p1"),
    ((("p1", 2026, 11), ("p2", 2026, 12)), "p1"),
    ((("p1", 2026, 12), ("p2", 2027, 1)), "p1"),
]


@pytest.mark.no_database
@pytest.mark.asyncio
@pytest.mark.parametrize(("periods", "baseline"), PERIOD_CASES)
async def test_period_matrix_executes_exact_windows(periods, baseline):
    result = await UniversalComparisonExecutor(MatrixRunner()).execute(
        make_plan(TENANT_A, periods=periods, baseline=baseline),
        execution_context(TENANT_A),
    )
    assert result.status == ComparisonExecutionStatus.READY
    assert tuple(item.operand_id for item in result.operands) == tuple(
        item[0] for item in periods
    )
    assert [
        item.public.periods[0].start.month for item in result.provenance
    ] == [item[2] for item in periods]


@pytest.mark.no_database
@pytest.mark.asyncio
@pytest.mark.parametrize("operand_count", range(3, 17))
async def test_multi_period_matrix_preserves_all_operands(operand_count):
    periods = tuple(
        (f"period_{index}", 2025 + (index // 12), (index % 12) + 1)
        for index in range(operand_count)
    )
    result = await UniversalComparisonExecutor(MatrixRunner()).execute(
        make_plan(
            TENANT_A,
            periods=periods,
            kind=ComparisonKind.MULTI_PERIOD,
            baseline=None,
            calculations=(ComparisonCalculation.VALUE,),
        ),
        execution_context(TENANT_A, maximum_operands=20, maximum_queries=20),
    )
    assert len(result.operands) == operand_count
    assert tuple(item.operand_id for item in result.operands) == tuple(
        item[0] for item in periods
    )


ENTITY_CASES = [
    ("filial", "1"),
    ("filial", "2"),
    ("produto", "100"),
    ("produto", "200"),
    ("vendedor", "1"),
    ("vendedor", "2"),
    ("cliente", "10"),
    ("cliente", "20"),
    ("filial", "CENTRO"),
    ("produto", "SKU-01"),
    ("vendedor", "RCA-9"),
    ("cliente", "C-100"),
    ("filial", "05"),
    ("produto", "0001"),
]


@pytest.mark.no_database
@pytest.mark.asyncio
@pytest.mark.parametrize(("entity_type", "entity_value"), ENTITY_CASES)
async def test_entity_matrix_uses_governed_bind(entity_type, entity_value):
    plan = make_plan(TENANT_A)
    comparison = plan.comparison
    changed_operands = [
        operand.model_copy(
            update={
                "entity_refs": [
                    EntityReference(
                        entity_id=f"{entity_type}:selected",
                        display_name="Selected entity",
                        origin=FieldOrigin.EXPLICIT_USER,
                    )
                ]
            }
        )
        for operand in comparison.operands
    ]
    plan = _replace_comparison(
        plan,
        comparison.model_copy(update={"operands": changed_operands}),
    )
    runner = MatrixRunner()
    await UniversalComparisonExecutor(runner).execute(
        plan,
        execution_context(
            TENANT_A,
            entity_values={f"{entity_type}:selected": entity_value},
        ),
    )
    assert all(query.binds["entity_0"] == entity_value for query in runner.calls)
    assert all(" = :entity_0" in query.statement for query in runner.calls)


SUPPORTED_METRICS = (
    "faturamento_comercial",
    "total_bruto",
    "faturamento_bruto",
    "total_movimentos_view",
    "saida_rb",
    "devolucao",
    "venda_bonificada",
    "transferencias",
    "desconto_total",
    "desconto_medio",
    "ticket_medio",
    "ranking_vendedores",
    "ranking_clientes",
)


@pytest.mark.no_database
@pytest.mark.asyncio
@pytest.mark.parametrize("metric_id", SUPPORTED_METRICS)
async def test_metric_matrix_uses_registry_backed_expression(metric_id):
    result = await UniversalComparisonExecutor(MatrixRunner()).execute(
        make_plan(TENANT_A, metric_ids=(metric_id,)),
        execution_context(TENANT_A, metric_ids=SUPPORTED_METRICS),
    )
    assert result.aligned_datasets[0].metric_id == metric_id
    assert all(
        isinstance(item.dataset[0][metric_id], Decimal)
        for item in result.operands
    )


MATH_CASES = [
    ("0.00", "0.00"),
    ("0.00", "1.00"),
    ("1.00", "0.00"),
    ("1.00", "1.00"),
    ("1.00", "2.00"),
    ("2.00", "1.00"),
    ("-1.00", "1.00"),
    ("1.00", "-1.00"),
    ("-2.00", "-1.00"),
    ("-1.00", "-2.00"),
    ("0.01", "0.02"),
    ("0.02", "0.01"),
    ("10.005", "10.015"),
    ("100", "133.333"),
    ("100", "66.667"),
    ("999999", "1000000"),
    ("1000000", "999999"),
    ("0.0001", "0.0002"),
    ("123456789.12", "234567890.23"),
    ("-123456789.12", "-234567890.23"),
    ("3", "4"),
]


class PairRunner(MatrixRunner):
    def __init__(self, baseline, target):
        super().__init__()
        self.baseline = Decimal(baseline)
        self.target = Decimal(target)

    async def execute(self, query):
        value = self.baseline if query.operand_id == "june" else self.target
        return [{metric_id: value for metric_id in query.metric_ids}]


@pytest.mark.no_database
@pytest.mark.asyncio
@pytest.mark.parametrize(("baseline", "target"), MATH_CASES)
async def test_math_property_matrix_uses_signed_decimal_delta(baseline, target):
    result = await UniversalComparisonExecutor(
        PairRunner(baseline, target)
    ).execute(
        make_plan(TENANT_A),
        execution_context(TENANT_A),
    )
    delta = next(
        item
        for item in result.calculations
        if item.calculation == ComparisonCalculation.ABSOLUTE_DIFFERENCE
    )
    assert delta.raw_result_value == Decimal(target) - Decimal(baseline)
    assert isinstance(delta.baseline_value, Decimal)
    assert isinstance(delta.target_value, Decimal)


SAFE_FILTER_VALUES = [
    "O'Reilly",
    "100% real",
    "_underscore_",
    "A;B",
    "x) OR (1=1",
    "quote\"double",
    "back\\slash",
    "line one line two",
    "acentuacao",
    "00001",
    "-10",
    "+10",
    "a_b_c",
    "50%%",
    "name--literal",
    "value/*literal",
    "value*/literal",
    "unicode-safe-value",
]


@pytest.mark.no_database
@pytest.mark.parametrize("value", SAFE_FILTER_VALUES)
def test_sql_security_matrix_keeps_filter_values_out_of_statement(value):
    plan = make_plan(TENANT_A, dimensions=("filial",))
    filter_item = FilterSpecification(
        filter_id="filial_filter",
        field_id="filial",
        operator=FilterOperator.EQ,
        value=value,
        values=[],
        origin=FieldOrigin.EXPLICIT_USER,
        confidence=confidence(),
        is_explicit=True,
    )
    intent = QueryIntentV2.model_validate(
        {**plan.intent.model_dump(mode="python"), "filters": [filter_item]}
    )
    plan = QueryPlanV2.model_validate(
        {
            **plan.model_dump(mode="python"),
            "intent": intent,
            "filters": [filter_item],
        }
    )
    queries = GovernedComparisonQueryCompiler(
        default_comparison_execution_catalog()
    ).compile(
        plan,
        execution_context(TENANT_A),
        select_execution_strategy(plan),
    )
    assert all(value not in query.statement for query in queries)
    assert all(value in query.binds.values() for query in queries)
    assert all(query.statement.lstrip().upper().startswith("SELECT") for query in queries)


@pytest.mark.no_database
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rows_per_query", "limit", "expected_status"),
    [
        (1, 1, ComparisonExecutionStatus.READY),
        (2, 1, ComparisonExecutionStatus.PARTIAL),
        (3, 2, ComparisonExecutionStatus.PARTIAL),
        (4, 3, ComparisonExecutionStatus.PARTIAL),
        (5, 4, ComparisonExecutionStatus.PARTIAL),
        (10, 9, ComparisonExecutionStatus.PARTIAL),
        (20, 19, ComparisonExecutionStatus.PARTIAL),
        (2, 2, ComparisonExecutionStatus.READY),
        (3, 3, ComparisonExecutionStatus.READY),
        (4, 4, ComparisonExecutionStatus.READY),
        (5, 5, ComparisonExecutionStatus.READY),
        (10, 10, ComparisonExecutionStatus.READY),
        (20, 20, ComparisonExecutionStatus.READY),
    ],
)
async def test_row_budget_and_truncation_matrix(
    rows_per_query, limit, expected_status
):
    result = await UniversalComparisonExecutor(
        MatrixRunner(rows_per_query=rows_per_query)
    ).execute(
        make_plan(TENANT_A, dimensions=("filial",)),
        execution_context(
            TENANT_A,
            maximum_rows_per_operand=limit,
            maximum_total_rows=max(100, limit * 2),
        ),
    )
    assert result.status == expected_status
    assert result.partial == (expected_status == ComparisonExecutionStatus.PARTIAL)


STRATEGIES = [
    "SINGLE_AGGREGATION",
    "CONDITIONAL_AGGREGATION",
    "MULTI_QUERY",
    "GROUPED_SERIES",
    "PIVOT",
    "LEGACY_COMPATIBILITY",
]


@pytest.mark.no_database
@pytest.mark.asyncio
@pytest.mark.parametrize("strategy", STRATEGIES)
async def test_strategy_matrix_is_explicit_and_stable(strategy):
    plan = make_plan(TENANT_A)
    contract = plan.contract.model_copy(
        update={
            "extensions": {
                "comparison_planner": {
                    "planner_version": "lumina.comparison-planner/1.0",
                    "strategy_hint": strategy,
                }
            }
        }
    )
    plan = QueryPlanV2.model_validate(
        {**plan.model_dump(mode="python"), "contract": contract}
    )
    result = await UniversalComparisonExecutor(MatrixRunner()).execute(
        plan, execution_context(TENANT_A)
    )
    assert result.strategy_used == ComparisonExecutionStrategy(strategy)


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_actual_vs_official_target_uses_separate_governed_source():
    actual = metric("faturamento_comercial")
    target = metric("meta_faturamento")
    july = month_window(2026, 7, "window_july")
    comparison = ComparisonSpecification(
        comparison_id="actual_target",
        kind=ComparisonKind.ACTUAL_VS_TARGET,
        operands=[
            ComparisonOperand(
                operand_id="actual",
                label="Realizado",
                metric_refs=[actual],
                time_windows=[july],
                origin=FieldOrigin.EXPLICIT_USER,
            ),
            ComparisonOperand(
                operand_id="target",
                label="Meta",
                metric_refs=[target],
                time_windows=[july],
                origin=FieldOrigin.TENANT_KNOWLEDGE,
            ),
        ],
        calculations=[
            ComparisonCalculation.VALUE,
            ComparisonCalculation.ABSOLUTE_DIFFERENCE,
            ComparisonCalculation.PERCENTAGE_DIFFERENCE,
            ComparisonCalculation.DIRECTION,
        ],
        baseline_operand_id="target",
        origin=FieldOrigin.EXPLICIT_USER,
        confidence=confidence(),
    )
    base = make_plan(TENANT_A)
    intent = QueryIntentV2.model_validate(
        {
            **base.intent.model_dump(mode="python"),
            "metric_refs": [actual, target],
            "time_windows": [july],
            "comparison": comparison,
        }
    )
    plan = QueryPlanV2.model_validate(
        {
            **base.model_dump(mode="python"),
            "intent": intent,
            "metric_refs": [actual, target],
            "time_windows": [july],
            "comparison": comparison,
            "source_refs": [
                SourceReference(
                    source_id="vw_vendas_lm",
                    source_kind=DataSourceKind.ANALYTICAL_CLONE,
                    origin=FieldOrigin.SYSTEM_GENERATED,
                ),
                SourceReference(
                    source_id="metas_oficiais",
                    source_kind=DataSourceKind.ANALYTICAL_CLONE,
                    origin=FieldOrigin.SYSTEM_GENERATED,
                ),
            ],
        }
    )
    sales_catalog = default_comparison_execution_catalog()
    target_source = SourceExecutionDefinition(
        source_id="metas_oficiais",
        relation="metas_oficiais",
        tenant_column="tenant_id",
        date_column="data_meta",
        source_version=METRIC_VERSION,
        metrics={
            "meta_faturamento": MetricExecutionDefinition(
                metric_id="meta_faturamento",
                expression="SUM(valor_meta)",
                version=METRIC_VERSION,
            )
        },
        dimensions={},
        permitted_tenant_ids=(TENANT_A,),
        target_source=True,
    )
    catalog = StaticComparisonExecutionCatalog(
        sources={**sales_catalog.sources, "metas_oficiais": target_source}
    )

    class TargetRunner(MatrixRunner):
        async def execute(self, query):
            return [
                {
                    query.metric_ids[0]: (
                        Decimal("400")
                        if query.source_id == "vw_vendas_lm"
                        else Decimal("500")
                    )
                }
            ]

    context = execution_context(
        TENANT_A,
        metric_ids=("faturamento_comercial", "meta_faturamento"),
        allowed_source_ids=("vw_vendas_lm", "metas_oficiais"),
    )
    result = await UniversalComparisonExecutor(
        TargetRunner(), catalog=catalog
    ).execute(plan, context)
    delta = next(
        item
        for item in result.calculations
        if item.calculation == ComparisonCalculation.ABSOLUTE_DIFFERENCE
    )
    assert result.strategy_used == ComparisonExecutionStrategy.TARGET_JOIN
    assert delta.baseline_operand_id == "target"
    assert delta.target_operand_id == "actual"
    assert delta.result_value == Decimal("-100.00")

    with pytest.raises(ComparisonExecutionRejected):
        await UniversalComparisonExecutor(TargetRunner()).execute(plan, context)


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_cross_tenant_target_source_is_rejected():
    target_source = SourceExecutionDefinition(
        source_id="metas_oficiais",
        relation="metas_oficiais",
        tenant_column="tenant_id",
        date_column="data_meta",
        source_version=METRIC_VERSION,
        metrics={
            "meta_faturamento": MetricExecutionDefinition(
                metric_id="meta_faturamento",
                expression="SUM(valor_meta)",
                version=METRIC_VERSION,
            )
        },
        dimensions={},
        permitted_tenant_ids=(TENANT_B,),
        target_source=True,
    )
    assert StaticComparisonExecutionCatalog(
        sources={"metas_oficiais": target_source}
    ).source("metas_oficiais", TENANT_A) is None


def _replace_comparison(
    plan: QueryPlanV2,
    comparison: ComparisonSpecification,
) -> QueryPlanV2:
    intent = QueryIntentV2.model_validate(
        {**plan.intent.model_dump(mode="python"), "comparison": comparison}
    )
    return QueryPlanV2.model_validate(
        {
            **plan.model_dump(mode="python"),
            "intent": intent,
            "comparison": comparison,
        }
    )
