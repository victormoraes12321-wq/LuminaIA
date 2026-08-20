from __future__ import annotations

import json
from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from contracts.analytical_v2 import (
    AnalyticalColumn,
    AnalyticalDataset,
    AnalyticalResponseV2,
    ColumnDataType,
    ComparisonCalculation,
    ComparisonKind,
    ComparisonOperand,
    ComparisonSpecification,
    ConfidenceAssessment,
    ConfidenceLevel,
    ContractMetadata,
    DataClassification,
    DataSourceKind,
    ExecutionProvenance,
    ExecutionReadiness,
    FieldOrigin,
    FilterOperator,
    FilterSpecification,
    PipelineKind,
    QueryPlanV2,
    SourceReference,
    TemporalGranularity,
    TimeWindow,
    ValidationCheck,
    ValidationReport,
    ValidationSeverity,
    ValidationStatus,
    VisualizationKind,
    VisualizationSpecification,
    build_intent_v2,
    build_plan_v2,
    extract_time_windows,
    extract_visualizations,
    legacy_payload_to_v2,
)


pytestmark = [pytest.mark.unit, pytest.mark.no_database]
TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")


def _confidence() -> ConfidenceAssessment:
    return ConfidenceAssessment(
        level=ConfidenceLevel.HIGH,
        score=Decimal("1"),
        reasons=["Campo reconhecido por regra deterministica."],
        requires_confirmation=False,
    )


def _window(month: int, *, window_id: str) -> TimeWindow:
    return TimeWindow(
        window_id=window_id,
        label=f"Mes {month}",
        start=date(2026, month, 1),
        end=date(2026, month, 30 if month == 6 else 31),
        end_inclusive=True,
        granularity=TemporalGranularity.MONTH,
        timezone="America/Sao_Paulo",
        origin=FieldOrigin.EXPLICIT_USER,
        confidence=_confidence(),
        raw_expression=f"{month:02d}/2026",
    )


def _legacy_payload(
    question: str = "Faturamento de 06/2026 em tabela",
    *,
    status: str = "FULL_RENDERING",
    chart_type: str = "TABLE",
) -> dict[str, object]:
    return {
        "query_id": "33333333-3333-3333-3333-333333333333",
        "pergunta_original": question,
        "status": status,
        "view_name": "VW_VENDAS_LM",
        "chart_type": chart_type,
        "chart_data": {
            "columns": [{"key": "valor", "label": "Valor", "type": "currency"}],
            "rows": [{"valor": 300}],
            "total_rows": 1,
            "resumo": {},
        },
        "visualizations": [{"chart_type": chart_type, "chart_data": {}}],
        "validation_summary": {
            "checks": [{"code": "TOTAL_VALIDADO", "status": "PASS", "required": True}]
        },
    }


def _response(question: str = "Faturamento de 06/2026 em tabela") -> AnalyticalResponseV2:
    return legacy_payload_to_v2(
        _legacy_payload(question),
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        user_role="CONSULTA",
        session_id="session-1",
        pipeline=PipelineKind.NEW,
    )


def test_contract_version_and_round_trip_are_stable() -> None:
    response = _response()
    encoded = response.model_dump_json()
    decoded = AnalyticalResponseV2.model_validate_json(encoded)
    assert decoded == response
    assert decoded.contract.schema_name == "lumina.analytics"
    assert decoded.contract.schema_version == "2.0"


@pytest.mark.parametrize("version", ["1", "1.0", "2.1", "unknown"])
def test_unknown_contract_versions_are_rejected(version: str) -> None:
    with pytest.raises(ValidationError, match="Unsupported analytical contract version"):
        ContractMetadata(
            schema_name="lumina.analytics",
            schema_version=version,
            pipeline=PipelineKind.NEW,
        )


def test_contract_rejects_non_utc_timestamp() -> None:
    with pytest.raises(ValidationError, match="created_at must use UTC"):
        ContractMetadata(
            pipeline=PipelineKind.NEW,
            created_at=datetime.now().astimezone(),
        )


def test_contract_rejects_sensitive_extensions() -> None:
    with pytest.raises(ValidationError, match="forbidden key"):
        ContractMetadata(
            pipeline=PipelineKind.NEW,
            extensions={"api_key": "not-allowed"},
        )


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Compare o faturamento do Mes 06/2026 e 07/2026", [(6, 2026), (7, 2026)]),
        ("Compare junho e julho de 2026", [(6, 2026), (7, 2026)]),
        ("Compare 06/2026 com 07/2026", [(6, 2026), (7, 2026)]),
        ("Faturamento de junho versus julho de 2026", [(6, 2026), (7, 2026)]),
        ("Compare 07/2026 com 06/2026", [(7, 2026), (6, 2026)]),
        ("Compare 05/2026, 06/2026 e 07/2026", [(5, 2026), (6, 2026), (7, 2026)]),
    ],
)
def test_plural_period_parser_preserves_every_occurrence(
    question: str,
    expected: list[tuple[int, int]],
) -> None:
    windows = extract_time_windows(question)
    assert [(window.start.month, window.start.year) for window in windows] == expected
    assert [window.window_id for window in windows] == [
        f"period_{index}" for index in range(1, len(expected) + 1)
    ]


def test_exact_comparison_contract_preserves_semantics() -> None:
    intent = build_intent_v2(
        "Compare o faturamento do Mes 06/2026 e 07/2026 em tabela e grafico",
        pipeline=PipelineKind.NEW,
    )
    plan = build_plan_v2(
        intent,
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        user_role="CONSULTA",
        session_id="session-1",
        allowed_source_ids=["vw_vendas_lm"],
        pipeline=PipelineKind.NEW,
    )
    assert intent.readiness == ExecutionReadiness.READY
    assert [window.start.month for window in intent.time_windows] == [6, 7]
    assert intent.comparison is not None
    assert len(intent.comparison.operands) == 2
    assert [operand.time_windows[0].start.month for operand in intent.comparison.operands] == [6, 7]
    assert intent.comparison.calculations == [
        ComparisonCalculation.VALUE,
        ComparisonCalculation.ABSOLUTE_DIFFERENCE,
        ComparisonCalculation.PERCENTAGE_DIFFERENCE,
        ComparisonCalculation.DIRECTION,
    ]
    assert [item.kind for item in plan.visualizations] == [
        VisualizationKind.DATA_TABLE,
        VisualizationKind.BAR_CHART,
    ]
    assert plan.scope is not None and plan.scope.tenant_id == TENANT_ID


def test_comparison_with_one_operand_is_rejected() -> None:
    operand = ComparisonOperand(
        operand_id="only",
        label="Junho",
        metric_refs=[],
        time_windows=[_window(6, window_id="june")],
        filters=[],
        entity_refs=[],
        origin=FieldOrigin.EXPLICIT_USER,
    )
    with pytest.raises(ValidationError):
        ComparisonSpecification(
            comparison_id="invalid",
            kind=ComparisonKind.PERIOD_VS_PERIOD,
            operands=[operand],
            calculations=[ComparisonCalculation.VALUE],
            baseline_operand_id="only",
            alignment_dimensions=[],
            origin=FieldOrigin.EXPLICIT_USER,
            confidence=_confidence(),
        )


def test_repeated_comparison_period_is_rejected() -> None:
    windows = [_window(6, window_id="a"), _window(6, window_id="b")]
    operands = [
        ComparisonOperand(
            operand_id=f"operand_{index}",
            label=window.label,
            metric_refs=[],
            time_windows=[window],
            filters=[],
            entity_refs=[],
            origin=FieldOrigin.EXPLICIT_USER,
        )
        for index, window in enumerate(windows, start=1)
    ]
    with pytest.raises(ValidationError, match="distinguishable periods"):
        ComparisonSpecification(
            comparison_id="invalid",
            kind=ComparisonKind.PERIOD_VS_PERIOD,
            operands=operands,
            calculations=[ComparisonCalculation.VALUE],
            baseline_operand_id="operand_1",
            alignment_dimensions=[],
            origin=FieldOrigin.EXPLICIT_USER,
            confidence=_confidence(),
        )


def test_duplicate_operand_ids_and_unknown_baseline_are_rejected() -> None:
    operands = [
        ComparisonOperand(
            operand_id="duplicate",
            label=window.label,
            metric_refs=[],
            time_windows=[window],
            filters=[],
            entity_refs=[],
            origin=FieldOrigin.EXPLICIT_USER,
        )
        for window in (_window(6, window_id="june"), _window(7, window_id="july"))
    ]
    with pytest.raises(ValidationError, match="duplicate IDs"):
        ComparisonSpecification(
            comparison_id="invalid",
            kind=ComparisonKind.PERIOD_VS_PERIOD,
            operands=operands,
            calculations=[ComparisonCalculation.VALUE],
            baseline_operand_id="duplicate",
            alignment_dimensions=[],
            origin=FieldOrigin.EXPLICIT_USER,
            confidence=_confidence(),
        )
    operands[1] = operands[1].model_copy(update={"operand_id": "other"})
    with pytest.raises(ValidationError, match="baseline_operand_id"):
        ComparisonSpecification(
            comparison_id="invalid",
            kind=ComparisonKind.PERIOD_VS_PERIOD,
            operands=operands,
            calculations=[ComparisonCalculation.VALUE],
            baseline_operand_id="missing",
            alignment_dimensions=[],
            origin=FieldOrigin.EXPLICIT_USER,
            confidence=_confidence(),
        )


def test_inverted_period_is_rejected() -> None:
    with pytest.raises(ValidationError, match="cannot precede"):
        TimeWindow(
            window_id="invalid",
            label="Invalido",
            start=date(2026, 7, 31),
            end=date(2026, 7, 1),
            granularity=TemporalGranularity.MONTH,
            timezone="America/Sao_Paulo",
            origin=FieldOrigin.EXPLICIT_USER,
            confidence=_confidence(),
        )


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("mostre em tabela e grafico", ["DATA_TABLE", "BAR_CHART"]),
        ("quero grafico e tabela", ["BAR_CHART", "DATA_TABLE"]),
        ("mostre tabela, grafico de barras e KPI", ["DATA_TABLE", "BAR_CHART", "KPI_CARD"]),
        ("tabela, tabela e grafico", ["DATA_TABLE", "BAR_CHART"]),
        ("use uma visualizacao desconhecida", []),
    ],
)
def test_visualization_parser_preserves_order_and_deduplicates(
    question: str,
    expected: list[str],
) -> None:
    visualizations = extract_visualizations(question, metric_ids=["faturamento_comercial"])
    assert [item.kind.value for item in visualizations] == expected
    assert sum(item.is_primary for item in visualizations) <= 1
    assert [item.priority for item in visualizations] == sorted(
        [item.priority for item in visualizations],
        reverse=True,
    )


@pytest.mark.parametrize(
    ("operator", "value", "values"),
    [
        (FilterOperator.BETWEEN, None, [1]),
        (FilterOperator.IN, None, []),
        (FilterOperator.IS_NULL, "unexpected", []),
        (FilterOperator.EQ, None, []),
    ],
)
def test_filter_cardinality_is_strict(
    operator: FilterOperator,
    value: object,
    values: list[object],
) -> None:
    with pytest.raises(ValidationError):
        FilterSpecification(
            filter_id="filter_1",
            field_id="filial",
            operator=operator,
            value=value,
            values=values,
            origin=FieldOrigin.EXPLICIT_USER,
            confidence=_confidence(),
            is_explicit=True,
        )


def test_ready_plan_requires_tenant_scope() -> None:
    intent = build_intent_v2(
        "Faturamento de 06/2026 em tabela",
        pipeline=PipelineKind.NEW,
    )
    valid = build_plan_v2(
        intent,
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        user_role="CONSULTA",
        session_id="session-1",
        allowed_source_ids=["vw_vendas_lm"],
        pipeline=PipelineKind.NEW,
    )
    payload = valid.model_dump(mode="python")
    payload["scope"] = None
    with pytest.raises(ValidationError, match="tenant scope"):
        QueryPlanV2.model_validate(payload)


def test_oracle_is_not_a_valid_user_query_source() -> None:
    with pytest.raises(ValidationError):
        SourceReference(
            source_id="oracle",
            source_kind="ORACLE",
            origin=FieldOrigin.SYSTEM_GENERATED,
        )


def test_plan_rejects_visualization_with_unknown_metric() -> None:
    intent = build_intent_v2(
        "Faturamento de 06/2026 em tabela",
        pipeline=PipelineKind.NEW,
    )
    plan = build_plan_v2(
        intent,
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        user_role="CONSULTA",
        session_id="session-1",
        allowed_source_ids=["vw_vendas_lm"],
        pipeline=PipelineKind.NEW,
    )
    payload = plan.model_dump(mode="python")
    payload["visualizations"][0]["metric_ids"] = ["unknown_metric"]
    with pytest.raises(ValidationError, match="unknown metric"):
        QueryPlanV2.model_validate(payload)


def test_validation_cannot_pass_without_checks() -> None:
    with pytest.raises(ValidationError, match="executed checks"):
        ValidationReport(
            status=ValidationStatus.PASSED,
            checks=[],
            validated_at=datetime.now(timezone.utc),
            validator_version="2.0",
        )


def test_required_failed_check_fails_report() -> None:
    check = ValidationCheck(
        check_id="math",
        name="Consistencia matematica",
        status=ValidationStatus.FAILED,
        severity=ValidationSeverity.ERROR,
        message="A soma nao confere.",
        evidence_reference=None,
        required=True,
    )
    with pytest.raises(ValidationError, match="must fail"):
        ValidationReport(
            status=ValidationStatus.WARNING,
            checks=[check],
            validated_at=datetime.now(timezone.utc),
            validator_version="2.0",
        )


def test_verified_tenant_isolation_requires_evidence() -> None:
    with pytest.raises(ValidationError, match="requires evidence"):
        ExecutionProvenance(
            tenant_id=TENANT_ID,
            source_id="clone",
            source_kind=DataSourceKind.ANALYTICAL_CLONE,
            view_ids=[],
            metric_versions={},
            periods=[],
            cache_status="MISS",
            pipeline=PipelineKind.NEW,
            tenant_isolation_verified=True,
        )


def test_response_rejects_unknown_dataset_reference() -> None:
    response = _response()
    payload = response.model_dump(mode="python")
    payload["visualizations"][0]["data_reference"] = "missing_dataset"
    with pytest.raises(ValidationError, match="unknown dataset"):
        AnalyticalResponseV2.model_validate(payload)


def test_response_rejects_multiple_primary_visualizations() -> None:
    response = _response("Faturamento de 06/2026 em tabela e grafico")
    payload = response.model_dump(mode="python")
    for visualization in payload["visualizations"]:
        visualization["is_primary"] = True
    with pytest.raises(ValidationError, match="only one"):
        AnalyticalResponseV2.model_validate(payload)


def test_dataset_rejects_non_json_and_inconsistent_count() -> None:
    column = AnalyticalColumn(
        column_id="value",
        label="Valor",
        data_type=ColumnDataType.DECIMAL,
    )
    with pytest.raises(ValidationError, match="smaller"):
        AnalyticalDataset(
            dataset_id="dataset",
            columns=[column],
            rows=[{"value": 1}],
            row_count=0,
            truncated=False,
            numeric_metadata={},
            data_classification=DataClassification.INTERNAL,
        )


def test_strict_models_forbid_unknown_fields() -> None:
    payload = _response().model_dump(mode="python")
    payload["unexpected"] = True
    with pytest.raises(ValidationError, match="Extra inputs"):
        AnalyticalResponseV2.model_validate(payload)


def test_adapter_does_not_mutate_input() -> None:
    payload = _legacy_payload()
    original = deepcopy(payload)
    _response_from_payload = legacy_payload_to_v2(
        payload,
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        user_role="CONSULTA",
        session_id="session-1",
        pipeline=PipelineKind.NEW,
    )
    assert payload == original


def test_serialization_is_deterministic_after_creation() -> None:
    response = _response()
    assert response.model_dump_json() == response.model_dump_json()


def test_schema_exports_match_versioned_files() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    schema_directory = repository_root / "docs" / "contracts" / "schemas"
    models = (
        build_intent_v2("Faturamento 06/2026", pipeline=PipelineKind.NEW).__class__,
        QueryPlanV2,
        ComparisonSpecification,
        VisualizationSpecification,
        AnalyticalResponseV2,
    )
    for model in models:
        path = schema_directory / f"{model.__name__}.schema.json"
        expected = json.dumps(
            model.model_json_schema(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n"
        assert path.read_text(encoding="utf-8") == expected
