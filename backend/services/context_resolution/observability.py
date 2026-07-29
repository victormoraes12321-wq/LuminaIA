from __future__ import annotations

from .models import ContextResolutionResult


def safe_resolution_metadata(result: ContextResolutionResult) -> dict[str, object]:
    """Structural telemetry only: no question, values, SQL, binds, or datasets."""
    return {
        "resolution_version": result.resolution_version,
        "relationship": result.relationship.value,
        "readiness": result.readiness.value,
        "field_decision_count": len(result.field_decisions),
        "conflict_count": len(result.conflicts),
        "operation_count": len(result.patch.operations),
        "warning_count": len(result.warnings),
        "clarification_required": result.clarification is not None,
        "rule_ids": list(result.rule_ids),
        "patch_fingerprint": result.patch.idempotency_fingerprint,
    }
