"""Static registry of allowlisted operational events for LuminaAI."""
from __future__ import annotations

from contracts.observability_v2 import OperationalEventTypeV2, TelemetryClassificationV2

_EVENT_CLASSIFICATIONS: dict[OperationalEventTypeV2, TelemetryClassificationV2] = {
    OperationalEventTypeV2.REQUEST_STARTED: TelemetryClassificationV2.PUBLIC_OPERATIONAL,
    OperationalEventTypeV2.REQUEST_COMPLETED: TelemetryClassificationV2.PUBLIC_OPERATIONAL,
    OperationalEventTypeV2.REQUEST_FAILED: TelemetryClassificationV2.PUBLIC_OPERATIONAL,
    OperationalEventTypeV2.REQUEST_CANCELLED: TelemetryClassificationV2.PUBLIC_OPERATIONAL,
    OperationalEventTypeV2.REQUEST_BLOCKED: TelemetryClassificationV2.PUBLIC_OPERATIONAL,

    OperationalEventTypeV2.AUTH_ALLOWED: TelemetryClassificationV2.RESTRICTED_OPERATIONAL,
    OperationalEventTypeV2.AUTH_DENIED: TelemetryClassificationV2.RESTRICTED_OPERATIONAL,
    OperationalEventTypeV2.TENANT_ISOLATION_BLOCKED: TelemetryClassificationV2.RESTRICTED_OPERATIONAL,

    OperationalEventTypeV2.QUERY_PLAN_CREATED: TelemetryClassificationV2.TENANT_OPERATIONAL,
    OperationalEventTypeV2.QUERY_EXECUTION_STARTED: TelemetryClassificationV2.TENANT_OPERATIONAL,
    OperationalEventTypeV2.QUERY_EXECUTION_COMPLETED: TelemetryClassificationV2.TENANT_OPERATIONAL,
    OperationalEventTypeV2.QUERY_EXECUTION_FAILED: TelemetryClassificationV2.TENANT_OPERATIONAL,

    OperationalEventTypeV2.VALIDATION_COMPLETED: TelemetryClassificationV2.TENANT_OPERATIONAL,
    OperationalEventTypeV2.VALIDATION_BLOCKED: TelemetryClassificationV2.RESTRICTED_OPERATIONAL,

    OperationalEventTypeV2.CACHE_HIT: TelemetryClassificationV2.INTERNAL_OPERATIONAL,
    OperationalEventTypeV2.CACHE_MISS: TelemetryClassificationV2.INTERNAL_OPERATIONAL,
    OperationalEventTypeV2.CACHE_WRITE: TelemetryClassificationV2.INTERNAL_OPERATIONAL,
    OperationalEventTypeV2.CACHE_INVALIDATED: TelemetryClassificationV2.INTERNAL_OPERATIONAL,
    OperationalEventTypeV2.MATERIALIZATION_HIT: TelemetryClassificationV2.INTERNAL_OPERATIONAL,
    OperationalEventTypeV2.MATERIALIZATION_MISS: TelemetryClassificationV2.INTERNAL_OPERATIONAL,

    OperationalEventTypeV2.AI_RUN_STARTED: TelemetryClassificationV2.TENANT_OPERATIONAL,
    OperationalEventTypeV2.AI_RUN_COMPLETED: TelemetryClassificationV2.TENANT_OPERATIONAL,
    OperationalEventTypeV2.AI_RUN_CANCELLED: TelemetryClassificationV2.TENANT_OPERATIONAL,
    OperationalEventTypeV2.AI_BUDGET_EXCEEDED: TelemetryClassificationV2.RESTRICTED_OPERATIONAL,
    OperationalEventTypeV2.AI_TOOL_CALLED: TelemetryClassificationV2.TENANT_OPERATIONAL,
    OperationalEventTypeV2.AI_TOOL_BLOCKED: TelemetryClassificationV2.RESTRICTED_OPERATIONAL,

    OperationalEventTypeV2.DASHBOARD_RUNTIME_STARTED: TelemetryClassificationV2.TENANT_OPERATIONAL,
    OperationalEventTypeV2.DASHBOARD_RUNTIME_COMPLETED: TelemetryClassificationV2.TENANT_OPERATIONAL,
    OperationalEventTypeV2.DASHBOARD_RUNTIME_PARTIAL: TelemetryClassificationV2.TENANT_OPERATIONAL,
    OperationalEventTypeV2.DASHBOARD_MUTATION_CONFLICT: TelemetryClassificationV2.TENANT_OPERATIONAL,

    OperationalEventTypeV2.SYNC_STARTED: TelemetryClassificationV2.INTERNAL_OPERATIONAL,
    OperationalEventTypeV2.SYNC_COMPLETED: TelemetryClassificationV2.INTERNAL_OPERATIONAL,
    OperationalEventTypeV2.SYNC_FAILED: TelemetryClassificationV2.RESTRICTED_OPERATIONAL,
    OperationalEventTypeV2.RECONCILIATION_COMPLETED: TelemetryClassificationV2.INTERNAL_OPERATIONAL,

    OperationalEventTypeV2.POST_SYNC_INSIGHT_RUN_STARTED: TelemetryClassificationV2.TENANT_OPERATIONAL,
    OperationalEventTypeV2.POST_SYNC_INSIGHT_RUN_COMPLETED: TelemetryClassificationV2.TENANT_OPERATIONAL,
    OperationalEventTypeV2.POST_SYNC_INSIGHT_RUN_BLOCKED: TelemetryClassificationV2.RESTRICTED_OPERATIONAL,
    OperationalEventTypeV2.POST_SYNC_INSIGHT_PUBLISHED: TelemetryClassificationV2.TENANT_OPERATIONAL,

    OperationalEventTypeV2.EVALUATION_RUN_STARTED: TelemetryClassificationV2.INTERNAL_OPERATIONAL,
    OperationalEventTypeV2.EVALUATION_RUN_COMPLETED: TelemetryClassificationV2.INTERNAL_OPERATIONAL,
    OperationalEventTypeV2.EVALUATION_REGRESSION_DETECTED: TelemetryClassificationV2.RESTRICTED_OPERATIONAL,
    OperationalEventTypeV2.SECURITY_CONTROL_FAILED: TelemetryClassificationV2.RESTRICTED_OPERATIONAL,
    OperationalEventTypeV2.CONFIGURATION_READINESS_BLOCKED: TelemetryClassificationV2.RESTRICTED_OPERATIONAL,
    OperationalEventTypeV2.MIGRATION_COMPATIBILITY_BLOCKED: TelemetryClassificationV2.RESTRICTED_OPERATIONAL,
    OperationalEventTypeV2.ROLLOUT_GATE_BLOCKED: TelemetryClassificationV2.RESTRICTED_OPERATIONAL,
    OperationalEventTypeV2.KILL_SWITCH_ACTIVE: TelemetryClassificationV2.RESTRICTED_OPERATIONAL,
    OperationalEventTypeV2.ROLLBACK_DECISION: TelemetryClassificationV2.RESTRICTED_OPERATIONAL,
}


class OperationalEventRegistryV2:
    @staticmethod
    def get_classification(event_type: OperationalEventTypeV2) -> TelemetryClassificationV2:
        return _EVENT_CLASSIFICATIONS.get(event_type, TelemetryClassificationV2.INTERNAL_OPERATIONAL)

    @staticmethod
    def is_allowlisted(event_type: OperationalEventTypeV2) -> bool:
        return event_type in _EVENT_CLASSIFICATIONS
