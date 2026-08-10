"""Unit tests for async context propagation of request context and correlation IDs."""
from __future__ import annotations

import asyncio
import pytest
from contracts.observability_v2 import ObservabilityContextV2
from services.observability_v2.context import ObservabilityContextService

pytestmark = pytest.mark.no_database


@pytest.mark.asyncio
async def test_context_propagation_async_isolation():
    ObservabilityContextService.clear_context()
    assert ObservabilityContextService.get_current_context() is None

    obs_ctx, corr_ctx = ObservabilityContextService.create_request_context(
        route_template="/api/v1/query",
        method="POST",
        tenant_id="tenant-a",
    )

    assert obs_ctx.route_template == "/api/v1/query"
    assert corr_ctx.trace_id == obs_ctx.trace_id

    async def subtask():
        ctx = ObservabilityContextService.get_current_context()
        assert ctx is not None
        assert ctx.tenant_id == "tenant-a"
        return ctx.request_id

    res = await asyncio.create_task(subtask())
    assert res == obs_ctx.request_id

    ObservabilityContextService.clear_context()
    assert ObservabilityContextService.get_current_context() is None
