from __future__ import annotations

from contracts.analytical_v2 import (
    AnalyticalColumn,
    AnalyticalDataset,
    AnalyticalResponseV2,
    ColumnDataType,
    ContractMetadata,
    DataClassification,
    LegacyCompatibility,
    PlanSummary,
    ScopeSummary,
    v2_response_to_legacy,
)

from .models import ComparisonExecutionResult, ComparisonExecutionStatus


def execution_result_to_v2(
    result: ComparisonExecutionResult,
    plan,
) -> AnalyticalResponseV2:
    if result.status != ComparisonExecutionStatus.READY:
        raise ValueError("Only a complete validated execution can produce a READY V2 response")
    rows = [
        {
            "metric_id": item.metric_id,
            "alignment_key": "|".join(item.alignment_key),
            "calculation": item.calculation.value,
            "baseline_operand_id": item.baseline_operand_id,
            "target_operand_id": item.target_operand_id,
            "baseline_value": str(item.baseline_value) if item.baseline_value is not None else None,
            "target_value": str(item.target_value) if item.target_value is not None else None,
            "result_value": str(item.result_value) if item.result_value is not None else None,
            "direction": item.direction.value,
            "status": item.status,
        }
        for item in result.calculations
    ]
    dataset_id = "comparison_result"
    dataset = AnalyticalDataset(
        dataset_id=dataset_id,
        columns=[
            AnalyticalColumn(column_id="metric_id", label="Metrica", data_type=ColumnDataType.STRING),
            AnalyticalColumn(column_id="alignment_key", label="Alinhamento", data_type=ColumnDataType.STRING),
            AnalyticalColumn(column_id="calculation", label="Calculo", data_type=ColumnDataType.STRING),
            AnalyticalColumn(column_id="baseline_operand_id", label="Base", data_type=ColumnDataType.STRING),
            AnalyticalColumn(column_id="target_operand_id", label="Comparado", data_type=ColumnDataType.STRING),
            AnalyticalColumn(column_id="baseline_value", label="Valor base", data_type=ColumnDataType.DECIMAL),
            AnalyticalColumn(column_id="target_value", label="Valor comparado", data_type=ColumnDataType.DECIMAL),
            AnalyticalColumn(column_id="result_value", label="Resultado", data_type=ColumnDataType.DECIMAL),
            AnalyticalColumn(column_id="direction", label="Direcao", data_type=ColumnDataType.STRING),
            AnalyticalColumn(column_id="status", label="Status", data_type=ColumnDataType.STRING),
        ],
        rows=rows,
        row_count=len(rows),
        numeric_metadata={
            key: value
            for key, value in result.summary_values.items()
            if hasattr(value, "as_tuple")
        },
        data_classification=DataClassification.INTERNAL,
    )
    visualizations = [
        item.model_copy(update={"data_reference": dataset_id})
        for item in plan.visualizations
    ]
    compatible = len(plan.comparison.operands) == 2
    return AnalyticalResponseV2(
        contract=ContractMetadata(
            pipeline=plan.contract.pipeline,
            adapter_used="comparison_execution_v2",
            request_id=plan.contract.request_id,
            trace_id=plan.contract.trace_id,
            extensions={
                "comparison_executor": {
                    "executor_version": result.executor_version,
                    "strategy": result.strategy_used.value,
                    "cache_status": result.cache_status,
                    "partial": result.partial,
                    "aligned_datasets": [
                        {
                            "dataset_id": item.dataset_id,
                            "metric_id": item.metric_id,
                            "alignment_keys": list(item.alignment_keys),
                            "series": list(item.series),
                            "row_count": item.row_count,
                            "truncated": item.truncated,
                            "missing_bucket_count": len(item.missing_buckets),
                            "null_bucket_count": len(item.null_buckets),
                            "alignment_policy": item.alignment_policy,
                        }
                        for item in result.aligned_datasets
                    ],
                    "calculation_count": len(result.calculations),
                    "zero_denominator_count": sum(
                        1 for item in result.calculations if item.zero_denominator
                    ),
                    "not_applicable_count": sum(
                        1 for item in result.calculations if item.status == "NOT_APPLICABLE"
                    ),
                    "validation_status": result.validation.status.value,
                    "provenance_count": len(result.provenance),
                }
            },
        ),
        scope_summary=ScopeSummary(
            tenant_id=plan.scope.tenant_id,
            user_role=plan.scope.user_role,
            session_id=plan.scope.session_id,
        ),
        intent=plan.intent,
        plan_summary=PlanSummary(
            operation=plan.operation,
            metric_ids=[item.metric_id for item in plan.metric_refs],
            dimension_ids=[item.dimension_id for item in plan.dimension_refs],
            source_ids=[item.source_id for item in plan.source_refs],
            periods=list(plan.time_windows),
        ),
        datasets=[dataset],
        visualizations=visualizations,
        provenance=[item.public for item in result.provenance],
        validation=result.validation,
        summary=_deterministic_summary(result),
        warnings=list(result.warnings),
        legacy_compatibility=LegacyCompatibility(
            compatible=compatible,
            primary_chart_type=None,
            warnings=(
                []
                if compatible
                else ["O payload V1 usa tabela sem reduzir os operandos canonicos V2."]
            ),
        ),
    )


def execution_result_to_legacy(
    result: ComparisonExecutionResult,
    plan,
    *,
    legacy_payload=None,
):
    return v2_response_to_legacy(
        execution_result_to_v2(result, plan),
        legacy_payload=legacy_payload,
    )


def _deterministic_summary(result: ComparisonExecutionResult) -> str:
    ready = [item for item in result.calculations if item.status == "READY"]
    if not ready:
        return "Comparacao executada sem valor comparativo aplicavel."
    first = ready[0]
    value = (
        first.direction.value
        if first.result_value is None
        else str(first.result_value)
    )
    return (
        f"Comparacao {first.metric_id}: {first.calculation.value} "
        f"para {first.target_operand_id} = {value}."
    )
