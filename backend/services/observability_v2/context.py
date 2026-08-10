"""Async context propagation for correlation IDs, request context, and trace spans."""
from __future__ import annotations

import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

from contracts.observability_v2 import CorrelationContextV2, ObservabilityContextV2

_OBSERVABILITY_CONTEXT: ContextVar[ObservabilityContextV2 | None] = ContextVar("_OBSERVABILITY_CONTEXT", default=None)
_CORRELATION_CONTEXT: ContextVar[CorrelationContextV2 | None] = ContextVar("_CORRELATION_CONTEXT", default=None)


class ObservabilityContextService:
    @staticmethod
    def get_current_context() -> ObservabilityContextV2 | None:
        return _OBSERVABILITY_CONTEXT.get()

    @staticmethod
    def get_correlation_context() -> CorrelationContextV2 | None:
        return _CORRELATION_CONTEXT.get()

    @staticmethod
    def set_current_context(ctx: ObservabilityContextV2) -> None:
        _OBSERVABILITY_CONTEXT.set(ctx)

    @staticmethod
    def set_correlation_context(ctx: CorrelationContextV2) -> None:
        _CORRELATION_CONTEXT.set(ctx)

    @staticmethod
    def create_request_context(
        *,
        request_id: str | None = None,
        tenant_id: str | None = None,
        user_id: str | None = None,
        route_template: str = "/unknown",
        method: str = "GET",
        external_correlation_reference: str | None = None,
    ) -> tuple[ObservabilityContextV2, CorrelationContextV2]:
        req_id = request_id or f"req_{uuid.uuid4().hex}"
        trace_id = f"trc_{uuid.uuid4().hex}"
        span_id = f"spn_{uuid.uuid4().hex}"
        now = datetime.now(timezone.utc)

        obs_ctx = ObservabilityContextV2(
            request_id=req_id,
            trace_id=trace_id,
            root_span_id=span_id,
            tenant_id=tenant_id,
            user_id=user_id,
            route_template=route_template,
            method=method,
            started_at=now,
        )
        corr_ctx = CorrelationContextV2(
            request_id=req_id,
            trace_id=trace_id,
            span_id=span_id,
            external_correlation_reference=external_correlation_reference,
        )
        _OBSERVABILITY_CONTEXT.set(obs_ctx)
        _CORRELATION_CONTEXT.set(corr_ctx)
        return obs_ctx, corr_ctx

    @staticmethod
    def clear_context() -> None:
        _OBSERVABILITY_CONTEXT.set(None)
        _CORRELATION_CONTEXT.set(None)
