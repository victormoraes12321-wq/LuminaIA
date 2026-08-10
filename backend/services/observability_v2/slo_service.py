"""SLI calculation, SLO evaluation, and Error Budget tracking service."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from contracts.observability_v2 import (
    ErrorBudgetV2,
    SliDefinitionV2,
    SloDefinitionV2,
    SloEvaluationV2,
    SloStatusV2,
)
from services.observability_v2.telemetry_service import OperationalTelemetryService

_DEFAULT_SLIS: tuple[SliDefinitionV2, ...] = (
    SliDefinitionV2(
        sli_id="request_success_rate",
        name="Request Success Rate",
        description="Percentage of HTTP requests completed without 5xx errors",
        good_events_metric_id="http_requests_total",
        total_events_metric_id="http_requests_total",
    ),
    SliDefinitionV2(
        sli_id="query_execution_success",
        name="Query Execution Success",
        description="Percentage of analytical SQL queries executed without failure",
        good_events_metric_id="query_executions_total",
        total_events_metric_id="query_executions_total",
    ),
    SliDefinitionV2(
        sli_id="validation_success",
        name="Validation Success",
        description="Percentage of validations completed without security/integrity block",
        good_events_metric_id="validation_completions_total",
        total_events_metric_id="validation_completions_total",
    ),
    SliDefinitionV2(
        sli_id="tenant_isolation_correctness",
        name="Tenant Isolation Correctness",
        description="Zero tenant isolation breach events",
        good_events_metric_id="http_requests_total",
        total_events_metric_id="http_requests_total",
    ),
    SliDefinitionV2(
        sli_id="dashboard_runtime_availability",
        name="Dashboard Runtime Availability",
        description="Percentage of dashboard runtime requests completed successfully",
        good_events_metric_id="dashboard_runtime_requests_total",
        total_events_metric_id="dashboard_runtime_requests_total",
    ),
    SliDefinitionV2(
        sli_id="post_sync_insight_run_success",
        name="Post-Sync Insight Run Success",
        description="Percentage of post-sync insight runs completed without error",
        good_events_metric_id="post_sync_insight_runs_total",
        total_events_metric_id="post_sync_insight_runs_total",
    ),
    SliDefinitionV2(
        sli_id="evaluation_pass_rate",
        name="Evaluation Pass Rate",
        description="Percentage of evaluation test cases passed",
        good_events_metric_id="evaluation_cases_passed_total",
        total_events_metric_id="evaluation_runs_total",
    ),
)

_DEFAULT_SLOS: tuple[SloDefinitionV2, ...] = (
    SloDefinitionV2(
        slo_id="slo_request_success",
        sli_id="request_success_rate",
        target_percentage=Decimal("99.90"),
        window_days=30,
        is_provisional=False,
    ),
    SloDefinitionV2(
        slo_id="slo_query_execution",
        sli_id="query_execution_success",
        target_percentage=Decimal("99.50"),
        window_days=30,
        is_provisional=False,
    ),
    SloDefinitionV2(
        slo_id="slo_validation",
        sli_id="validation_success",
        target_percentage=Decimal("99.90"),
        window_days=30,
        is_provisional=False,
    ),
    SloDefinitionV2(
        slo_id="slo_tenant_isolation",
        sli_id="tenant_isolation_correctness",
        target_percentage=Decimal("100.00"),
        window_days=30,
        is_provisional=False,
    ),
    SloDefinitionV2(
        slo_id="slo_dashboard_runtime",
        sli_id="dashboard_runtime_availability",
        target_percentage=Decimal("99.00"),
        window_days=30,
        is_provisional=True,
    ),
    SloDefinitionV2(
        slo_id="slo_post_sync_insights",
        sli_id="post_sync_insight_run_success",
        target_percentage=Decimal("99.00"),
        window_days=30,
        is_provisional=True,
    ),
    SloDefinitionV2(
        slo_id="slo_evaluations",
        sli_id="evaluation_pass_rate",
        target_percentage=Decimal("98.00"),
        window_days=30,
        is_provisional=True,
    ),
)


class SloEvaluationService:
    def __init__(self, telemetry_service: OperationalTelemetryService) -> None:
        self.telemetry = telemetry_service

    def list_slis(self) -> tuple[SliDefinitionV2, ...]:
        return _DEFAULT_SLIS

    def list_slos(self) -> tuple[SloDefinitionV2, ...]:
        return _DEFAULT_SLOS

    def evaluate_slo(self, slo_id: str) -> SloEvaluationV2 | None:
        slo_defn = next((s for s in _DEFAULT_SLOS if s.slo_id == slo_id), None)
        if slo_defn is None:
            return None

        sli_defn = next((s for s in _DEFAULT_SLIS if s.sli_id == slo_defn.sli_id), None)
        if sli_defn is None:
            return None

        rollups = self.telemetry.compute_rollups()
        good_pts = [r for r in rollups if r.metric_id == sli_defn.good_events_metric_id]
        total_pts = [r for r in rollups if r.metric_id == sli_defn.total_events_metric_id]

        total_cnt = sum(r.count for r in total_pts)
        good_cnt = sum(r.count for r in good_pts)

        if total_cnt == 0:
            current_pct = Decimal("100.00")
            status = SloStatusV2.INSUFFICIENT_DATA
            bad_cnt = 0
            consumed = Decimal("0.00")
            remaining = Decimal("100.00")
        else:
            good_cnt = min(good_cnt, total_cnt)
            bad_cnt = total_cnt - good_cnt
            current_pct = (Decimal(good_cnt) / Decimal(total_cnt)) * Decimal("100.00")
            allowed_error_rate = Decimal("100.00") - slo_defn.target_percentage

            if allowed_error_rate == Decimal("0.00"):
                consumed = Decimal("100.00") if bad_cnt > 0 else Decimal("0.00")
            else:
                error_rate = (Decimal(bad_cnt) / Decimal(total_cnt)) * Decimal("100.00")
                consumed = min(Decimal("100.00"), (error_rate / allowed_error_rate) * Decimal("100.00"))

            remaining = max(Decimal("0.00"), Decimal("100.00") - consumed)

            if consumed >= Decimal("100.00"):
                status = SloStatusV2.EXHAUSTED
            elif consumed >= Decimal("80.00"):
                status = SloStatusV2.AT_RISK
            else:
                status = SloStatusV2.HEALTHY

        budget = ErrorBudgetV2(
            slo_id=slo_id,
            total_events=total_cnt,
            good_events=good_cnt,
            bad_events=bad_cnt,
            target_percentage=slo_defn.target_percentage,
            consumed_budget_percentage=consumed.quantize(Decimal("0.01")),
            remaining_budget_percentage=remaining.quantize(Decimal("0.01")),
            status=status,
        )

        return SloEvaluationV2(
            evaluation_id=f"slo_eval_{uuid.uuid4().hex}",
            slo_id=slo_id,
            evaluated_at=datetime.now(timezone.utc),
            current_percentage=current_pct.quantize(Decimal("0.01")),
            target_percentage=slo_defn.target_percentage,
            error_budget=budget,
            status=status,
        )

    def evaluate_all_slos(self) -> tuple[SloEvaluationV2, ...]:
        evals: list[SloEvaluationV2] = []
        for slo in _DEFAULT_SLOS:
            ev = self.evaluate_slo(slo.slo_id)
            if ev is not None:
                evals.append(ev)
        return tuple(evals)
