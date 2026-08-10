"""Sanitized audit service for security and administrative observability events."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Mapping

from contracts.observability_v2 import OperationalEventTypeV2
from services.observability_v2.event_registry import OperationalEventRegistryV2
from services.observability_v2.redaction import ObservabilityRedactionService

logger = logging.getLogger("luminaai.observability.audit")


class ObservabilityAuditService:
    def __init__(self, redaction_service: ObservabilityRedactionService | None = None) -> None:
        self.redaction = redaction_service or ObservabilityRedactionService()

    def audit_security_event(
        self,
        event_type: OperationalEventTypeV2,
        *,
        trace_id: str,
        span_id: str,
        reason: str,
        details: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        sanitized_details = self.redaction.redact_dict(dict(details or {}))
        cls = OperationalEventRegistryV2.get_classification(event_type)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type.value,
            "classification": cls.value,
            "trace_id": trace_id,
            "span_id": span_id,
            "reason": self.redaction.redact_string(reason[:128]),
            "details": sanitized_details,
        }
        logger.warning("AUDIT_SECURITY_EVENT | %s | trace_id=%s | reason=%s", event_type.value, trace_id, entry["reason"])
        return entry
