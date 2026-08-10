from __future__ import annotations

import inspect
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from contracts.observability_v2 import EvaluationSuiteKindV2
from config import settings
from routers import observability_v2, validation_provenance
from routers.safe_analytical_postgresql import _require_admin_or_gestor
from services.observability_v2.evaluations import GovernedEvaluationRunnerV2

pytestmark = pytest.mark.no_database

TENANT_A = UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")
TENANT_B = UUID("b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22")
USER_A = UUID("11111111-1111-4111-8111-111111111111")


@pytest.mark.asyncio
async def test_validation_tenant_is_derived_from_authenticated_user_only() -> None:
    signature = inspect.signature(validation_provenance.get_current_user_tenant)
    assert "x_tenant_id" not in signature.parameters and "x_user_id" not in signature.parameters
    tenant_id, user_id = await validation_provenance.get_current_user_tenant(
        current_user=SimpleNamespace(tenant_id=TENANT_A, id=USER_A)
    )
    assert tenant_id == TENANT_A and user_id == USER_A


def test_safe_postgresql_role_guard_uses_user_model_attributes() -> None:
    assert _require_admin_or_gestor(SimpleNamespace(role="GESTOR")).role == "GESTOR"
    with pytest.raises(HTTPException) as exc:
        _require_admin_or_gestor(SimpleNamespace(role="CONSULTA"))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_evaluation_run_id_is_concealed_across_tenants() -> None:
    observability_v2._eval_runs_store.clear()
    run = GovernedEvaluationRunnerV2().run_suite(EvaluationSuiteKindV2.SECURITY)
    observability_v2._eval_runs_store.append((str(TENANT_B), run))
    user_a = SimpleNamespace(tenant_id=TENANT_A)
    with pytest.raises(HTTPException) as exc:
        await observability_v2.get_evaluation_run(run.run_id, user=user_a)
    assert exc.value.status_code == 404
    assert run.run_id not in str(exc.value.detail)


@pytest.mark.asyncio
async def test_unscoped_in_memory_trace_is_always_concealed() -> None:
    with pytest.raises(HTTPException) as exc:
        await observability_v2.get_observability_trace("trc_foreign", user=SimpleNamespace(tenant_id=TENANT_A))
    assert exc.value.status_code == 404
    assert "trc_foreign" not in str(exc.value.detail)


def test_cookie_mutation_requires_allowed_origin_and_request_id_is_server_owned() -> None:
    from main import app

    client = TestClient(app)
    denied = client.post("/api/v1/auth/logout", headers={"Cookie": "lumina-token=synthetic-cookie"})
    assert denied.status_code == 403
    allowed = client.post(
        "/api/v1/auth/logout",
        headers={"Origin": settings.CORS_ORIGINS[0], "Cookie": "lumina-token=synthetic-cookie"},
    )
    assert allowed.status_code == 200
    forged = client.get("/health", headers={"X-Request-ID": "forged-admin-correlation"})
    assert forged.headers["X-Request-ID"] != "forged-admin-correlation"
    assert forged.headers["X-Content-Type-Options"] == "nosniff"
    assert forged.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in forged.headers["Content-Security-Policy"]
