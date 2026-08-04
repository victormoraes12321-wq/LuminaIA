from __future__ import annotations

import pytest
from contracts.ai_tool_registry_v2 import AIToolInvocationContextV2
from services.ai_tool_registry.adapters import REGISTERED_TOOL_ADAPTERS, get_adapter_class
from testing.test_database import CONSULTA_A, TENANT_A

TENANT_ID = str(TENANT_A)
USER_ID = str(CONSULTA_A)


def test_static_adapter_registry_contains_13_adapters() -> None:
    assert len(REGISTERED_TOOL_ADAPTERS) == 13
    expected_ids = [
        "enterprise_knowledge.search.v1",
        "enterprise_knowledge.get_metric_definition.v1",
        "temporal.normalize.v1",
        "semantic.search.v1",
        "semantic.resolve_entity.v1",
        "context.get_public_summary.v1",
        "profile.get_application_summary.v1",
        "intent.validate.v1",
        "comparison.plan.v1",
        "comparison.validate_plan.v1",
        "clarification.build_options.v1",
        "provenance.get_public_summary.v1",
        "analytical_postgresql.query.v1",
    ]
    for adapter_id in expected_ids:
        assert adapter_id in REGISTERED_TOOL_ADAPTERS
        cls = get_adapter_class(adapter_id)
        assert cls is not None


@pytest.mark.asyncio
async def test_temporal_normalize_adapter_execution() -> None:
    cls = get_adapter_class("temporal.normalize.v1")
    adapter = cls()

    ctx = AIToolInvocationContextV2(
        request_id="req_1",
        correlation_id="corr_1",
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        user_role="CONSULTA",
        session_id="sess_1",
        reference_time="2026-07-30T10:00:00Z",
        snapshot_version="1.0.0",
        timezone="America/Sao_Paulo",
        tool_id="lumina.temporal.normalize",
        tool_version="1.0.0",
    )

    valid_args = await adapter.validate_arguments({"expression": "hoje"})
    result = await adapter.execute(valid_args, ctx)
    assert result["expression"] == "hoje"
    assert result["success"] is True
    assert "time_window" in result


@pytest.mark.asyncio
async def test_metric_definition_adapter_execution() -> None:
    cls = get_adapter_class("enterprise_knowledge.get_metric_definition.v1")
    adapter = cls()

    ctx = AIToolInvocationContextV2(
        request_id="req_1",
        correlation_id="corr_1",
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        user_role="CONSULTA",
        session_id="sess_1",
        reference_time="2026-07-30T10:00:00Z",
        snapshot_version="1.0.0",
        tool_id="lumina.enterprise_knowledge.get_metric_definition",
        tool_version="1.0.0",
    )

    valid_args = await adapter.validate_arguments({"metric_name": "faturamento"})
    result = await adapter.execute(valid_args, ctx)
    assert result["found"] is True
    assert result["definition"]["canonical_name"] == "faturamento"
