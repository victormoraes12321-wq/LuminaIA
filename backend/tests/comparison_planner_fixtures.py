from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from contracts.analytical_v2 import (
    ComparisonCalculation,
    ComparisonKind,
    ComparisonOperand,
    ComparisonSpecification,
    ConfidenceAssessment,
    ConfidenceLevel,
    ContractMetadata,
    DimensionReference,
    DimensionRole,
    EntityReference,
    ExecutionReadiness,
    FieldOrigin,
    FilterOperator,
    FilterSpecification,
    IntentKind,
    MetricReference,
    PipelineKind,
    QueryIntentV2,
    TemporalGranularity,
    TimeWindow,
)
from services.comparison_planning import (
    ComparisonPlanningContext,
    DimensionCatalogEntry,
    EntityCatalogEntry,
    MetricCatalogEntry,
    StaticComparisonCatalog,
    TargetCatalogEntry,
)


TENANT_A = UUID("11111111-1111-1111-1111-111111111111")
TENANT_B = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
USER_A = UUID("22222222-2222-2222-2222-222222222222")
REFERENCE = datetime(
    2026,
    7,
    27,
    12,
    tzinfo=timezone(timedelta(hours=-3)),
)
SOURCE_SALES = "vw_vendas_lm"
SOURCE_TARGET = "metas_oficiais"


def confidence(
    level: ConfidenceLevel = ConfidenceLevel.HIGH,
    score: str = "1",
) -> ConfidenceAssessment:
    return ConfidenceAssessment(
        level=level,
        score=Decimal(score),
        reasons=["Referência resolvida pelo catálogo sintético governado."],
        requires_confirmation=level == ConfidenceLevel.LOW,
    )


def metric(
    metric_id: str,
    *,
    unit: str = "BRL",
    aggregation: str = "SUM",
) -> MetricReference:
    return MetricReference(
        metric_id=metric_id,
        metric_version="test-registry/1",
        display_name=metric_id.replace("_", " ").title(),
        unit=unit,
        aggregation=aggregation,
        origin=FieldOrigin.EXPLICIT_USER,
        confidence=confidence(),
    )


def window(
    year: int,
    month: int,
    *,
    window_id: str | None = None,
    granularity: TemporalGranularity = TemporalGranularity.MONTH,
) -> TimeWindow:
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return TimeWindow(
        window_id=window_id or f"period_{year}_{month:02d}",
        label=f"{month:02d}/{year}",
        start=date(year, month, 1),
        end=end,
        end_inclusive=True,
        granularity=granularity,
        timezone="America/Sao_Paulo",
        origin=FieldOrigin.EXPLICIT_USER,
        confidence=confidence(),
        raw_expression=f"{month:02d}/{year}",
    )


def entity(entity_id: str, label: str) -> EntityReference:
    return EntityReference(
        entity_id=entity_id,
        display_name=label,
        origin=FieldOrigin.EXPLICIT_USER,
    )


def dimension(
    dimension_id: str,
    role: DimensionRole = DimensionRole.GROUPING,
) -> DimensionReference:
    return DimensionReference(
        dimension_id=dimension_id,
        display_name=dimension_id.title(),
        role=role,
        origin=FieldOrigin.EXPLICIT_USER,
        confidence=confidence(),
    )


def filter_spec(
    filter_id: str,
    field_id: str,
    value: object,
    *,
    origin: FieldOrigin = FieldOrigin.EXPLICIT_USER,
) -> FilterSpecification:
    return FilterSpecification(
        filter_id=filter_id,
        field_id=field_id,
        operator=FilterOperator.EQ,
        value=value,
        values=[],
        origin=origin,
        confidence=confidence(),
        is_explicit=origin == FieldOrigin.EXPLICIT_USER,
    )


def operand(
    operand_id: str,
    label: str,
    *,
    metrics: list[MetricReference] | None = None,
    windows: list[TimeWindow] | None = None,
    entities: list[EntityReference] | None = None,
    filters: list[FilterSpecification] | None = None,
) -> ComparisonOperand:
    return ComparisonOperand(
        operand_id=operand_id,
        label=label,
        metric_refs=metrics or [],
        time_windows=windows or [],
        filters=filters or [],
        entity_refs=entities or [],
        origin=FieldOrigin.EXPLICIT_USER,
    )


def comparison(
    kind: ComparisonKind,
    operands: list[ComparisonOperand],
    *,
    calculations: list[ComparisonCalculation] | None = None,
    baseline: str | None = None,
    alignment_dimensions: list[str] | None = None,
    requested_sort: str | None = None,
) -> ComparisonSpecification:
    return ComparisonSpecification(
        comparison_id="comparison_1",
        kind=kind,
        operands=operands,
        calculations=calculations
        or [
            ComparisonCalculation.VALUE,
            ComparisonCalculation.ABSOLUTE_DIFFERENCE,
            ComparisonCalculation.PERCENTAGE_DIFFERENCE,
            ComparisonCalculation.DIRECTION,
        ],
        baseline_operand_id=baseline,
        alignment_dimensions=alignment_dimensions or [],
        requested_sort=requested_sort,
        origin=FieldOrigin.EXPLICIT_USER,
        confidence=confidence(),
    )


def intent(
    comparison_spec: ComparisonSpecification,
    *,
    metrics: list[MetricReference],
    windows: list[TimeWindow] | None = None,
    dimensions: list[DimensionReference] | None = None,
    filters: list[FilterSpecification] | None = None,
    question: str = "Compare os valores solicitados",
    readiness: ExecutionReadiness = ExecutionReadiness.READY,
) -> QueryIntentV2:
    return QueryIntentV2(
        contract=ContractMetadata(
            pipeline=PipelineKind.NEW,
            extensions={
                "temporal": {
                    "normalizer_version": "lumina.temporal.pt-BR/1.0",
                }
            },
        ),
        intent_kind=IntentKind.COMPARISON,
        readiness=readiness,
        raw_question=question,
        normalized_question=question.lower(),
        metric_refs=metrics,
        dimension_refs=dimensions or [],
        filters=filters or [],
        time_windows=windows or [],
        comparison=comparison_spec,
        requested_visualizations=[],
        confidence=confidence(),
        clarification=None,
        out_of_scope_reason=None,
        field_origins={
            "raw_question": FieldOrigin.EXPLICIT_USER,
            "intent_kind": FieldOrigin.SYSTEM_GENERATED,
        },
    )


def catalog(
    *,
    include_target: bool = True,
    target_tenant: UUID = TENANT_A,
) -> StaticComparisonCatalog:
    metric_entries = {
        "faturamento_comercial": MetricCatalogEntry(
            metric_id="faturamento_comercial",
            metric_version="test-registry/1",
            unit="BRL",
            aggregation="SUM",
            allowed_dimension_ids=(
                "filial",
                "produto",
                "categoria",
                "vendedor",
                "cliente",
                "mes",
                "dia",
                "ano",
            ),
            allowed_source_ids=(SOURCE_SALES,),
            comparability_group="currency",
        ),
        "faturamento_bruto": MetricCatalogEntry(
            metric_id="faturamento_bruto",
            metric_version="test-registry/1",
            unit="BRL",
            aggregation="SUM",
            allowed_dimension_ids=("filial", "mes"),
            allowed_source_ids=(SOURCE_SALES,),
            comparability_group="currency",
        ),
        "quantidade_vendida": MetricCatalogEntry(
            metric_id="quantidade_vendida",
            metric_version="test-registry/1",
            unit="UNITS",
            aggregation="SUM",
            allowed_dimension_ids=("filial", "produto", "mes"),
            allowed_source_ids=(SOURCE_SALES,),
            comparability_group="quantity",
        ),
        "saida_rb": MetricCatalogEntry(
            metric_id="saida_rb",
            metric_version="test-registry/1",
            unit="BRL",
            aggregation="SUM",
            allowed_dimension_ids=("filial", "vendedor", "mes"),
            allowed_source_ids=(SOURCE_SALES,),
            comparability_group="currency",
        ),
        "meta_faturamento": MetricCatalogEntry(
            metric_id="meta_faturamento",
            metric_version="test-registry/1",
            unit="BRL",
            aggregation="SUM",
            allowed_dimension_ids=("filial", "mes"),
            allowed_source_ids=(SOURCE_TARGET,),
            comparability_group="currency",
        ),
    }
    dimensions = {
        item: DimensionCatalogEntry(
            dimension_id=item,
            allowed_source_ids=(SOURCE_SALES,),
            supported_granularities=(
                "DAY",
                "MONTH",
                "YEAR",
                "CUSTOM",
            ),
        )
        for item in (
            "filial",
            "produto",
            "categoria",
            "vendedor",
            "cliente",
            "mes",
            "dia",
            "ano",
        )
    }
    entities = {
        (TENANT_A, "filial:centro"): EntityCatalogEntry(
            entity_id="filial:centro",
            tenant_id=TENANT_A,
            entity_type="filial",
            allowed_source_ids=(SOURCE_SALES,),
        ),
        (TENANT_A, "filial:sul"): EntityCatalogEntry(
            entity_id="filial:sul",
            tenant_id=TENANT_A,
            entity_type="filial",
            allowed_source_ids=(SOURCE_SALES,),
        ),
        (TENANT_A, "filial:norte"): EntityCatalogEntry(
            entity_id="filial:norte",
            tenant_id=TENANT_A,
            entity_type="filial",
            allowed_source_ids=(SOURCE_SALES,),
        ),
        (TENANT_A, "produto:a"): EntityCatalogEntry(
            entity_id="produto:a",
            tenant_id=TENANT_A,
            entity_type="produto",
            allowed_source_ids=(SOURCE_SALES,),
        ),
        (TENANT_A, "produto:b"): EntityCatalogEntry(
            entity_id="produto:b",
            tenant_id=TENANT_A,
            entity_type="produto",
            allowed_source_ids=(SOURCE_SALES,),
        ),
        (TENANT_B, "filial:centro"): EntityCatalogEntry(
            entity_id="filial:centro",
            tenant_id=TENANT_B,
            entity_type="filial",
            allowed_source_ids=(SOURCE_SALES,),
        ),
    }
    targets = {}
    if include_target:
        targets[(target_tenant, "faturamento_comercial")] = TargetCatalogEntry(
            tenant_id=target_tenant,
            actual_metric_id="faturamento_comercial",
            target_metric_id="meta_faturamento",
            unit="BRL",
            granularity="MONTH",
            source_id=SOURCE_TARGET,
            official=True,
        )
    return StaticComparisonCatalog(
        metrics=metric_entries,
        dimensions=dimensions,
        entities=entities,
        targets=targets,
    )


def context(
    *,
    tenant_id: UUID | None = TENANT_A,
    maximum_operands: int = 20,
    maximum_metrics: int = 10,
    maximum_dimensions: int = 5,
    maximum_plan_complexity: int = 500,
    maximum_series: int = 250,
    allowed_sources: tuple[str, ...] = (SOURCE_SALES, SOURCE_TARGET),
    permission_fingerprint: str = "permission:test:a",
) -> ComparisonPlanningContext:
    return ComparisonPlanningContext(
        tenant_id=tenant_id,
        user_id=USER_A,
        user_role="CONSULTA",
        session_id="comparison-session",
        timezone="America/Sao_Paulo",
        locale="pt-BR",
        allowed_metric_ids=(
            "faturamento_comercial",
            "faturamento_bruto",
            "quantidade_vendida",
            "saida_rb",
            "meta_faturamento",
        ),
        allowed_dimension_ids=(
            "filial",
            "produto",
            "categoria",
            "vendedor",
            "cliente",
            "mes",
            "dia",
            "ano",
        ),
        allowed_entity_types=(
            "filial",
            "produto",
            "categoria",
            "vendedor",
            "cliente",
        ),
        allowed_source_ids=allowed_sources,
        permission_fingerprint=permission_fingerprint,
        maximum_operands=maximum_operands,
        maximum_metrics=maximum_metrics,
        maximum_dimensions=maximum_dimensions,
        maximum_plan_complexity=maximum_plan_complexity,
        maximum_series=maximum_series,
        maximum_text_length=4000,
        reference_datetime=REFERENCE,
        feature_flags={"enabled": True, "shadow_mode": True},
        source="test_trusted_backend",
    )
