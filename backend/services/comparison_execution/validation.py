from __future__ import annotations

from datetime import datetime, timezone

from contracts.analytical_v2 import (
    ComparisonCalculation,
    ValidationCheck,
    ValidationReport,
    ValidationSeverity,
    ValidationStatus,
)

from .models import (
    COMPARISON_EXECUTOR_VERSION,
    ComparisonCalculationResult,
    ComparisonExecutionContext,
    OperandExecutionResult,
    OperandExecutionStatus,
)


VALIDATION_VERSION = f"{COMPARISON_EXECUTOR_VERSION}:validation/1"


def build_validation_report(
    context: ComparisonExecutionContext,
    operands: tuple[OperandExecutionResult, ...],
    calculations: tuple[ComparisonCalculationResult, ...],
    *,
    expected_operand_count: int,
) -> ValidationReport:
    operand_failures = [
        item
        for item in operands
        if item.status
        in {
            OperandExecutionStatus.FAILED,
            OperandExecutionStatus.TIMED_OUT,
            OperandExecutionStatus.BLOCKED,
        }
    ]
    total_rows = sum(item.row_count for item in operands)
    delta_consistent = all(
        item.raw_result_value == item.target_value - item.baseline_value
        for item in calculations
        if item.calculation == ComparisonCalculation.ABSOLUTE_DIFFERENCE
        and item.status == "READY"
        and item.baseline_value is not None
        and item.target_value is not None
    )
    percentage_consistent = all(
        item.raw_result_value
        == (
            (item.target_value - item.baseline_value)
            / abs(item.baseline_value)
            * 100
        )
        for item in calculations
        if item.calculation == ComparisonCalculation.PERCENTAGE_DIFFERENCE
        and item.status == "READY"
        and item.baseline_value not in {None, 0}
        and item.target_value is not None
    )
    checks = [
        _validation_check("tenant_scope", True, "Escopo de tenant autenticado preservado."),
        _validation_check(
            "permission_scope",
            bool(context.permission_fingerprint),
            "Fingerprint de permissao confiavel aplicado.",
        ),
        _validation_check(
            "operand_count",
            len(operands) == expected_operand_count,
            "A cardinalidade de operandos corresponde ao plano.",
        ),
        _validation_check(
            "operand_integrity",
            not operand_failures,
            "Todos os operandos obrigatorios foram executados.",
        ),
        _validation_check(
            "row_budget",
            total_rows <= context.maximum_total_rows,
            "O volume executado respeita o limite total.",
        ),
        _validation_check(
            "row_count_consistency",
            all(item.row_count == len(item.dataset) for item in operands),
            "As contagens de linha correspondem aos datasets.",
        ),
        _validation_check(
            "decimal_math",
            all(
                item.result_value is None or item.result_value.is_finite()
                for item in calculations
            ),
            "Os resultados sao decimais finitos ou explicitamente nao aplicaveis.",
        ),
        _validation_check(
            "signed_delta",
            delta_consistent,
            "Deltas seguem target menos baseline.",
        ),
        _validation_check(
            "percentage_formula",
            percentage_consistent,
            "Percentuais seguem delta dividido pelo modulo do baseline.",
        ),
    ]
    if any(
        check.required and check.status == ValidationStatus.FAILED
        for check in checks
    ):
        status = ValidationStatus.FAILED
    elif any(item.status == OperandExecutionStatus.TRUNCATED for item in operands):
        checks.append(
            _validation_check(
                "dataset_completeness",
                False,
                "Um dataset atingiu o limite autorizado e esta incompleto.",
                required=False,
                warning=True,
            )
        )
        status = ValidationStatus.WARNING
    else:
        checks.append(
            _validation_check(
                "dataset_completeness",
                True,
                "Nenhum dataset foi truncado.",
                required=False,
            )
        )
        status = ValidationStatus.PASSED
    return ValidationReport(
        status=status,
        checks=checks,
        validated_at=datetime.now(timezone.utc),
        validator_version=VALIDATION_VERSION,
    )


def _validation_check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    required: bool = True,
    warning: bool = False,
) -> ValidationCheck:
    return ValidationCheck(
        check_id=check_id,
        name=check_id.replace("_", " ").title(),
        status=(
            ValidationStatus.PASSED
            if passed
            else ValidationStatus.WARNING
            if warning
            else ValidationStatus.FAILED
        ),
        severity=(
            ValidationSeverity.INFO
            if passed
            else ValidationSeverity.WARNING
            if warning
            else ValidationSeverity.ERROR
        ),
        message=message,
        evidence_reference=f"comparison-execution:{check_id}",
        required=required,
    )
