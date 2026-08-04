from __future__ import annotations

import pytest
from contracts.ai_tool_registry_v2 import (
    AIToolCapability,
    AIToolInvocationContextV2,
    AIToolInvocationRequestV2,
    AIToolRegistrationRequestV2,
)
from services.ai_tool_registry.exceptions import (
    AIToolAccessDeniedException,
    AIToolAdapterNotRegisteredException,
    AIToolNotFoundException,
    AIToolReservedCapabilityUnavailableException,
)
from services.ai_tool_registry.invocation_service import governed_ai_tool_invocation_service
from services.ai_tool_registry.registry_service import governed_ai_tool_registry_service
from testing.test_database import CONSULTA_A, TENANT_A

TENANT_ID = str(TENANT_A)
USER_ID = str(CONSULTA_A)


@pytest.mark.asyncio
async def test_register_tool_identity_access_control() -> None:
    req = AIToolRegistrationRequestV2(
        tool_id="lumina.test.tool",
        canonical_name="lumina.test.tool",
        display_name="Test Tool",
        description="Test Tool",
        capabilities=[AIToolCapability.READ_ENTERPRISE_KNOWLEDGE],
        version="1.0.0",
        adapter_id="enterprise_knowledge.search.v1",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
    )
    with pytest.raises(AIToolAccessDeniedException):
        await governed_ai_tool_registry_service.register_tool_identity(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            user_permissions=["ai_tool:read_only"],
            request=req,
        )


@pytest.mark.asyncio
async def test_register_tool_unregistered_adapter_fails() -> None:
    req = AIToolRegistrationRequestV2(
        tool_id="lumina.test.tool",
        canonical_name="lumina.test.tool",
        display_name="Test Tool",
        description="Test Tool",
        capabilities=[AIToolCapability.READ_ENTERPRISE_KNOWLEDGE],
        version="1.0.0",
        adapter_id="unregistered.fake.adapter.v1",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
    )
    with pytest.raises(AIToolAdapterNotRegisteredException):
        await governed_ai_tool_registry_service.register_tool_identity(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            user_permissions=["admin"],
            request=req,
        )


@pytest.mark.asyncio
async def test_register_tool_reserved_capability_blocked() -> None:
    req = AIToolRegistrationRequestV2(
        tool_id="lumina.test.tool",
        canonical_name="lumina.test.tool",
        display_name="Test Tool",
        description="Test Tool",
        capabilities=[AIToolCapability.ANALYTICAL_POSTGRESQL_READ],
        version="1.0.0",
        adapter_id="enterprise_knowledge.search.v1",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
    )
    with pytest.raises(AIToolReservedCapabilityUnavailableException):
        await governed_ai_tool_registry_service.register_tool_identity(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            user_permissions=["admin"],
            request=req,
        )


@pytest.mark.asyncio
async def test_invoke_governed_tool_success() -> None:
    req = AIToolInvocationRequestV2(
        tool_id="lumina.temporal.normalize",
        raw_arguments={"expression": "este mes"},
    )
    ctx = AIToolInvocationContextV2(
        request_id="req_test",
        correlation_id="corr_test",
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        user_role="CONSULTA",
        session_id="sess_test",
        reference_time="2026-07-30T10:00:00Z",
        snapshot_version="1.0.0",
        timezone="America/Sao_Paulo",
        tool_id="lumina.temporal.normalize",
        tool_version="1.0.0",
    )

    envelope = await governed_ai_tool_invocation_service.invoke_tool(req, ctx)
    assert envelope.tool_id == "lumina.temporal.normalize"
    assert envelope.result.success is True
    assert envelope.result.data["success"] is True


@pytest.mark.asyncio
async def test_invoke_unregistered_tool_fails() -> None:
    req = AIToolInvocationRequestV2(
        tool_id="lumina.unregistered.tool",
        raw_arguments={},
    )
    ctx = AIToolInvocationContextV2(
        request_id="req_test",
        correlation_id="corr_test",
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        user_role="CONSULTA",
        session_id="sess_test",
        reference_time="2026-07-30T10:00:00Z",
        snapshot_version="1.0.0",
        tool_id="lumina.unregistered.tool",
        tool_version="1.0.0",
    )
    with pytest.raises(AIToolNotFoundException):
        await governed_ai_tool_invocation_service.invoke_tool(req, ctx)
