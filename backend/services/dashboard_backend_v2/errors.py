"""Typed fail-closed errors for the governed dashboard backend."""
from __future__ import annotations

from dataclasses import dataclass


ERROR_CODES = frozenset(
    {
        "DASHBOARD_NOT_FOUND", "DASHBOARD_ACCESS_DENIED", "DASHBOARD_TENANT_MISMATCH",
        "DASHBOARD_VERSION_CONFLICT", "DASHBOARD_IDEMPOTENCY_CONFLICT",
        "DASHBOARD_INVALID_LIFECYCLE_TRANSITION", "DASHBOARD_BLUEPRINT_INVALID",
        "DASHBOARD_BLUEPRINT_BLOCKED", "DASHBOARD_REVISION_NOT_FOUND",
        "DASHBOARD_REVISION_STALE", "DASHBOARD_PATCH_INVALID",
        "DASHBOARD_VISUAL_PATCH_SEMANTIC_CHANGE",
        "DASHBOARD_SEMANTIC_PATCH_REVALIDATION_REQUIRED", "DASHBOARD_REVIEW_REQUIRED",
        "DASHBOARD_APPROVAL_REQUIRED", "DASHBOARD_PUBLICATION_NOT_FOUND",
        "DASHBOARD_PUBLICATION_CONFLICT", "DASHBOARD_ROLLBACK_INVALID",
        "DASHBOARD_ARCHIVED", "DASHBOARD_CLASSIFICATION_BLOCKED",
        "DASHBOARD_PERMISSION_INSUFFICIENT", "DASHBOARD_FILTER_INVALID",
        "DASHBOARD_INTERACTION_INVALID", "DASHBOARD_RUNTIME_UNAVAILABLE",
        "DASHBOARD_WIDGET_EXECUTION_FAILED", "DASHBOARD_CERTIFICATION_INVALID",
        "DASHBOARD_PAYLOAD_TOO_LARGE", "DASHBOARD_BACKUP_VALIDATION_FAILED",
    }
)


@dataclass(slots=True)
class DashboardBackendError(Exception):
    code: str
    message: str
    status_code: int = 400

    def __post_init__(self) -> None:
        if self.code not in ERROR_CODES:
            raise ValueError("unknown dashboard backend error code")
        Exception.__init__(self, self.message)

    def public_payload(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


def not_found() -> DashboardBackendError:
    # The same response is used for missing and cross-tenant resources.
    return DashboardBackendError("DASHBOARD_NOT_FOUND", "Dashboard não encontrado.", 404)

