from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from contracts.analytical_v2 import ComparisonCalculation, QueryPlanV2

from .models import (
    AlignedComparisonDataset,
    ComparisonCalculationResult,
    ComparisonDirection,
    ComparisonExecutionContext,
    ZeroDenominatorPolicy,
)


class ComparisonMathError(ValueError):
    pass


def calculate_comparison(
    plan: QueryPlanV2,
    datasets: tuple[AlignedComparisonDataset, ...],
    context: ComparisonExecutionContext,
) -> tuple[ComparisonCalculationResult, ...]:
    comparison = plan.comparison
    if comparison is None:
        raise ComparisonMathError("Comparison specification is required")
    operand_ids = tuple(item.operand_id for item in comparison.operands)
    baseline_id = comparison.baseline_operand_id or operand_ids[0]
    results: list[ComparisonCalculationResult] = []

    for dataset in datasets:
        for row in dataset.rows:
            for calculation in comparison.calculations:
                if calculation == ComparisonCalculation.RANK:
                    results.extend(
                        _rank_results(
                            dataset.metric_id,
                            row.alignment_key,
                            row.values,
                            operand_ids,
                        )
                    )
                    continue
                if calculation == ComparisonCalculation.SHARE:
                    results.extend(
                        _share_results(
                            dataset.metric_id,
                            row.alignment_key,
                            row.values,
                            operand_ids,
                            context,
                        )
                    )
                    continue
                for target_id in operand_ids:
                    if target_id == baseline_id:
                        continue
                    results.append(
                        _pair_result(
                            calculation=calculation,
                            metric_id=dataset.metric_id,
                            alignment_key=row.alignment_key,
                            baseline_id=baseline_id,
                            target_id=target_id,
                            baseline=row.values.get(baseline_id),
                            target=row.values.get(target_id),
                            context=context,
                        )
                    )
    return tuple(results)


def _pair_result(
    *,
    calculation: ComparisonCalculation,
    metric_id: str,
    alignment_key: tuple[str, ...],
    baseline_id: str,
    target_id: str,
    baseline: Decimal | None,
    target: Decimal | None,
    context: ComparisonExecutionContext,
) -> ComparisonCalculationResult:
    if baseline is None or target is None:
        return _not_applicable(
            calculation,
            metric_id,
            alignment_key,
            baseline_id,
            target_id,
            baseline,
            target,
            "MISSING_OPERAND_VALUE",
        )
    direction = _direction(baseline, target)
    raw: Decimal | None
    if calculation == ComparisonCalculation.VALUE:
        raw = target
    elif calculation == ComparisonCalculation.ABSOLUTE_DIFFERENCE:
        raw = target - baseline
    elif calculation == ComparisonCalculation.PERCENTAGE_DIFFERENCE:
        if baseline == 0:
            return _zero_denominator(
                calculation,
                metric_id,
                alignment_key,
                baseline_id,
                target_id,
                baseline,
                target,
                context,
            )
        raw = ((target - baseline) / abs(baseline)) * Decimal("100")
    elif calculation == ComparisonCalculation.DIRECTION:
        raw = None
    else:
        raise ComparisonMathError(f"Unsupported pair calculation: {calculation}")
    rounded = _round(raw, context) if raw is not None else None
    return ComparisonCalculationResult(
        calculation=calculation,
        baseline_operand_id=baseline_id,
        target_operand_id=target_id,
        metric_id=metric_id,
        alignment_key=alignment_key,
        baseline_value=baseline,
        target_value=target,
        raw_result_value=raw,
        result_value=rounded,
        direction=direction,
        status="READY",
        rounding_applied=raw is not None and rounded != raw,
        validation_checks=("decimal_math", "signed_delta", "final_rounding_only"),
    )


def _rank_results(
    metric_id: str,
    alignment_key: tuple[str, ...],
    values: dict[str, Decimal | None],
    operand_ids: tuple[str, ...],
) -> list[ComparisonCalculationResult]:
    ordered_values = sorted(
        {value for value in values.values() if value is not None},
        reverse=True,
    )
    ranks = {value: index + 1 for index, value in enumerate(ordered_values)}
    return [
        ComparisonCalculationResult(
            calculation=ComparisonCalculation.RANK,
            baseline_operand_id=None,
            target_operand_id=operand_id,
            metric_id=metric_id,
            alignment_key=alignment_key,
            baseline_value=None,
            target_value=values.get(operand_id),
            raw_result_value=(
                Decimal(ranks[values[operand_id]])
                if values.get(operand_id) is not None
                else None
            ),
            result_value=(
                Decimal(ranks[values[operand_id]])
                if values.get(operand_id) is not None
                else None
            ),
            direction=ComparisonDirection.NOT_APPLICABLE,
            status="READY" if values.get(operand_id) is not None else "NOT_APPLICABLE",
            not_applicable_reason=None if values.get(operand_id) is not None else "MISSING_OPERAND_VALUE",
            validation_checks=("dense_rank", "stable_operand_identity"),
        )
        for operand_id in operand_ids
    ]


def _share_results(
    metric_id: str,
    alignment_key: tuple[str, ...],
    values: dict[str, Decimal | None],
    operand_ids: tuple[str, ...],
    context: ComparisonExecutionContext,
) -> list[ComparisonCalculationResult]:
    available = [value for value in values.values() if value is not None]
    total = sum(available, Decimal("0"))
    output: list[ComparisonCalculationResult] = []
    for operand_id in operand_ids:
        value = values.get(operand_id)
        if value is None or total == 0:
            output.append(
                _not_applicable(
                    ComparisonCalculation.SHARE,
                    metric_id,
                    alignment_key,
                    None,
                    operand_id,
                    total,
                    value,
                    "ZERO_TOTAL" if total == 0 else "MISSING_OPERAND_VALUE",
                    zero_denominator=total == 0,
                )
            )
            continue
        raw = value / total * Decimal("100")
        rounded = _round(raw, context)
        output.append(
            ComparisonCalculationResult(
                calculation=ComparisonCalculation.SHARE,
                baseline_operand_id=None,
                target_operand_id=operand_id,
                metric_id=metric_id,
                alignment_key=alignment_key,
                baseline_value=total,
                target_value=value,
                raw_result_value=raw,
                result_value=rounded,
                direction=ComparisonDirection.NOT_APPLICABLE,
                status="READY",
                rounding_applied=raw != rounded,
                validation_checks=("share_denominator", "decimal_math"),
            )
        )
    return output


def _zero_denominator(
    calculation: ComparisonCalculation,
    metric_id: str,
    alignment_key: tuple[str, ...],
    baseline_id: str,
    target_id: str,
    baseline: Decimal,
    target: Decimal,
    context: ComparisonExecutionContext,
) -> ComparisonCalculationResult:
    policy = context.zero_denominator_policy
    if policy == ZeroDenominatorPolicy.ERROR:
        raise ComparisonMathError("Zero denominator is forbidden by execution policy")
    if policy == ZeroDenominatorPolicy.ZERO_WHEN_BOTH_ZERO and target == 0:
        return ComparisonCalculationResult(
            calculation=calculation,
            baseline_operand_id=baseline_id,
            target_operand_id=target_id,
            metric_id=metric_id,
            alignment_key=alignment_key,
            baseline_value=baseline,
            target_value=target,
            raw_result_value=Decimal("0"),
            result_value=Decimal("0"),
            direction=ComparisonDirection.STABLE,
            status="READY",
            zero_denominator=True,
            validation_checks=("zero_denominator_policy",),
        )
    reason = (
        "INFINITY_NOT_REPRESENTED"
        if policy == ZeroDenominatorPolicy.EXPLICIT_INFINITY_UNSUPPORTED
        else "ZERO_DENOMINATOR"
    )
    return _not_applicable(
        calculation,
        metric_id,
        alignment_key,
        baseline_id,
        target_id,
        baseline,
        target,
        reason,
        zero_denominator=True,
    )


def _not_applicable(
    calculation: ComparisonCalculation,
    metric_id: str,
    alignment_key: tuple[str, ...],
    baseline_id: str | None,
    target_id: str,
    baseline: Decimal | None,
    target: Decimal | None,
    reason: str,
    *,
    zero_denominator: bool = False,
) -> ComparisonCalculationResult:
    return ComparisonCalculationResult(
        calculation=calculation,
        baseline_operand_id=baseline_id,
        target_operand_id=target_id,
        metric_id=metric_id,
        alignment_key=alignment_key,
        baseline_value=baseline,
        target_value=target,
        raw_result_value=None,
        result_value=None,
        direction=ComparisonDirection.NOT_APPLICABLE,
        status="NOT_APPLICABLE",
        zero_denominator=zero_denominator,
        not_applicable_reason=reason,
        validation_checks=("not_applicable_explicit",),
    )


def _direction(baseline: Decimal, target: Decimal) -> ComparisonDirection:
    if target > baseline:
        return ComparisonDirection.INCREASE
    if target < baseline:
        return ComparisonDirection.DECREASE
    return ComparisonDirection.STABLE


def _round(value: Decimal, context: ComparisonExecutionContext) -> Decimal:
    quantum = Decimal("1").scaleb(-context.decimal_precision)
    return value.quantize(quantum, rounding=ROUND_HALF_UP)
