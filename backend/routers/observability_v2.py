"""FastAPI router for experimental V2 Observability, Metrics, SLOs, and Evaluations endpoints."""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from config import settings
from contracts.observability_v2 import EvaluationSuiteKindV2, FeatureModeV2
from models.user import User
from routers.auth import get_current_user
from services.observability_v2 import (
    ObservabilityContextService,
    OperationalMetricRegistryV2,
    OperationalTelemetryService,
    SloEvaluationService,
)
from services.observability_v2.evaluations import (
    EvaluationBaselineServiceV2,
    EvaluationCorpusServiceV2,
    EvaluationRegressionServiceV2,
    EvaluationSuiteRegistryV2,
    GovernedEvaluationRunnerV2,
)

router = APIRouter(prefix="/api/v2", tags=["Observability V2"])

_telemetry_service = OperationalTelemetryService()
_slo_service = SloEvaluationService(_telemetry_service)
_eval_runner = GovernedEvaluationRunnerV2()
_eval_runs_store: list[tuple[str, Any]] = []


def _require_observability_enabled() -> None:
    if settings.OBSERVABILITY_MODE == "LEGACY_ONLY" or not settings.OBSERVABILITY_APIS_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "OBSERVABILITY_NOT_AVAILABLE", "message": "Observability V2 is disabled in current mode."},
        )


def _require_admin(user: User = Depends(get_current_user)) -> User:
    _require_observability_enabled()
    if user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCESS_DENIED", "message": "Admin role required for observability operations."},
        )
    return user


def _require_gestor_or_admin(user: User = Depends(get_current_user)) -> User:
    _require_observability_enabled()
    if user.role not in {"ADMIN", "GESTOR"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCESS_DENIED", "message": "Admin or Gestor role required for observability summary."},
        )
    return user


@router.get("/observability/summary")
async def get_observability_summary(user: User = Depends(_require_gestor_or_admin)) -> dict[str, Any]:
    health = _telemetry_service.get_health()
    readiness = _telemetry_service.get_readiness(FeatureModeV2(settings.OBSERVABILITY_MODE))
    slos = _slo_service.evaluate_all_slos()
    return {
        "contract_version": "lumina.observability-metrics-evaluations/1.0",
        "mode": settings.OBSERVABILITY_MODE,
        "health": health.model_dump(),
        "readiness": readiness.model_dump(),
        "slo_count": len(slos),
        "evaluation_runs_count": sum(tenant_id == str(user.tenant_id) for tenant_id, _ in _eval_runs_store),
    }


@router.get("/observability/metrics")
async def get_observability_metrics(user: User = Depends(_require_admin)) -> dict[str, Any]:
    rollups = _telemetry_service.compute_rollups()
    definitions = OperationalMetricRegistryV2.list_metrics()
    return {
        "definitions": [d.model_dump() for d in definitions],
        "rollups": [r.model_dump() for r in rollups],
    }


@router.get("/observability/traces/{trace_id}")
async def get_observability_trace(trace_id: str, user: User = Depends(_require_admin)) -> dict[str, Any]:
    # The current in-memory buffer has no tenant ownership column. Conceal all
    # trace IDs until Prompt 24 storage provides a tenant-scoped lookup.
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "TRACE_NOT_FOUND", "message": "Trace not found."},
    )


@router.get("/observability/slos")
async def get_observability_slos(user: User = Depends(_require_admin)) -> dict[str, Any]:
    slis = _slo_service.list_slis()
    slos = _slo_service.list_slos()
    evaluations = _slo_service.evaluate_all_slos()
    return {
        "slis": [s.model_dump() for s in slis],
        "slos": [s.model_dump() for s in slos],
        "evaluations": [e.model_dump() for e in evaluations],
    }


@router.get("/observability/slos/{slo_id}")
async def get_observability_slo_detail(slo_id: str, user: User = Depends(_require_admin)) -> dict[str, Any]:
    evaluation = _slo_service.evaluate_slo(slo_id)
    if evaluation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SLO_NOT_FOUND", "message": f"SLO {slo_id} not found."},
        )
    return evaluation.model_dump()


@router.get("/evaluations/suites")
async def list_evaluation_suites(user: User = Depends(_require_admin)) -> dict[str, Any]:
    suites = EvaluationSuiteRegistryV2.list_suites()
    return {"suites": [s.model_dump() for s in suites]}


@router.post("/evaluations/runs")
async def run_evaluation_suite(
    suite: EvaluationSuiteKindV2 = Query(...),
    user: User = Depends(_require_admin),
) -> dict[str, Any]:
    run = _eval_runner.run_suite(suite)
    _eval_runs_store.append((str(user.tenant_id), run))
    return run.model_dump()


@router.get("/evaluations/runs")
async def list_evaluation_runs(user: User = Depends(_require_admin)) -> dict[str, Any]:
    return {"runs": [r.model_dump() for tenant_id, r in _eval_runs_store if tenant_id == str(user.tenant_id)]}


@router.get("/evaluations/runs/{run_id}")
async def get_evaluation_run(run_id: str, user: User = Depends(_require_admin)) -> dict[str, Any]:
    run = next((r for tenant_id, r in _eval_runs_store if tenant_id == str(user.tenant_id) and r.run_id == run_id), None)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RUN_NOT_FOUND", "message": "Evaluation run not found."},
        )
    return run.model_dump()


@router.get("/evaluations/runs/{run_id}/results")
async def get_evaluation_run_results(run_id: str, user: User = Depends(_require_admin)) -> dict[str, Any]:
    run = next((r for tenant_id, r in _eval_runs_store if tenant_id == str(user.tenant_id) and r.run_id == run_id), None)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RUN_NOT_FOUND", "message": "Evaluation run not found."},
        )
    return {"results": [res.model_dump() for res in run.results]}


@router.get("/evaluations/regressions")
async def list_evaluation_regressions(user: User = Depends(_require_admin)) -> dict[str, Any]:
    all_regressions = [reg for tenant_id, run in _eval_runs_store if tenant_id == str(user.tenant_id) for reg in run.regressions]
    return {"regressions": [r.model_dump() for r in all_regressions]}
