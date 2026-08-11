from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ParityStage(str, Enum):
    HTTP_ACCEPTED = "HTTP_ACCEPTED"
    AUTH_RESOLVED = "AUTH_RESOLVED"
    TENANT_RESOLVED = "TENANT_RESOLVED"
    CONTEXT_RESOLVED = "CONTEXT_RESOLVED"
    INTENT_RESOLVED = "INTENT_RESOLVED"
    SEMANTIC_RESOLVED = "SEMANTIC_RESOLVED"
    PLAN_CREATED = "PLAN_CREATED"
    EXECUTION_STARTED = "EXECUTION_STARTED"
    EXECUTION_COMPLETED = "EXECUTION_COMPLETED"
    VALIDATED = "VALIDATED"
    RESPONSE_RENDERED = "RESPONSE_RENDERED"
    PROVIDER_REQUIRED = "PROVIDER_REQUIRED"
    BLOCKED = "BLOCKED"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    ERROR = "ERROR"


class ParityFailureCause(str, Enum):
    ROUTING = "ROUTING"
    AUTH_CONTEXT = "AUTH_CONTEXT"
    TENANT_CONTEXT = "TENANT_CONTEXT"
    CONVERSATION_CONTEXT = "CONVERSATION_CONTEXT"
    TEMPORAL_RESOLUTION = "TEMPORAL_RESOLUTION"
    INTENT_RESOLUTION = "INTENT_RESOLUTION"
    SEMANTIC_RESOLUTION = "SEMANTIC_RESOLUTION"
    ENTITY_RESOLUTION = "ENTITY_RESOLUTION"
    METRIC_RESOLUTION = "METRIC_RESOLUTION"
    PLANNER = "PLANNER"
    EXECUTOR = "EXECUTOR"
    VALIDATION = "VALIDATION"
    RESPONSE_ADAPTER = "RESPONSE_ADAPTER"
    ZERO_DEFAULT = "ZERO_DEFAULT"
    PROVIDER_FALLBACK = "PROVIDER_FALLBACK"
    SEED_OR_DATASET = "SEED_OR_DATASET"
    CONFIGURATION = "CONFIGURATION"
    UNKNOWN = "UNKNOWN"


class ExpectedResolutionPath(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"
    PROVIDER_ALLOWED = "PROVIDER_ALLOWED"
    CLARIFICATION = "CLARIFICATION"
    REJECT = "REJECT"


class StageOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stage: ParityStage
    outcome: str = Field(min_length=1, max_length=64)
    fingerprint: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class AnalyticalParityTrace(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(min_length=1, max_length=64)
    expected_resolution_path: ExpectedResolutionPath
    stages: list[StageOutcome]
    normalized_input_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    temporal_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    entity_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    context_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    intent_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    selected_capability: str
    plan_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    execution_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    response_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    provider_invoked: bool = False


_VOLATILE_KEYS = {
    "trace_id",
    "query_id",
    "request_id",
    "execution_time_ms",
    "duration_ms",
    "validated_at",
    "intent_fingerprint",
}
_SENSITIVE_KEYS = {"raw_sql", "parameters", "binds", "sample_rows"}


def canonical_fingerprint(value: Any) -> str:
    sanitized = _sanitize(value)
    encoded = json.dumps(
        sanitized,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _sanitize(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if str(key) not in _VOLATILE_KEYS | _SENSITIVE_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    return value


def trace_from_pipeline_payload(
    *,
    case_id: str,
    question: str,
    expected_resolution_path: ExpectedResolutionPath,
    payload: dict[str, Any],
    provider_invoked: bool = False,
) -> AnalyticalParityTrace:
    debug = payload.get("debug_info") if isinstance(payload.get("debug_info"), dict) else {}
    temporal = debug.get("temporal_normalization") or {}
    intent = debug.get("deterministic_intent") or {}
    plan = debug.get("canonical_plan") or {}
    chart_data = payload.get("chart_data") if isinstance(payload.get("chart_data"), dict) else {}
    response_facts = chart_data.get("resumo") if isinstance(chart_data.get("resumo"), dict) else {}
    execution_facts = {
        "facts": response_facts,
        "row_count": debug.get("rows"),
        "status": payload.get("status"),
    }
    completed = payload.get("status") in {"FULL_RENDERING", "NO_ROWS"}
    stages = [
        StageOutcome(stage=ParityStage.HTTP_ACCEPTED, outcome="ACCEPTED"),
        StageOutcome(stage=ParityStage.AUTH_RESOLVED, outcome="RESOLVED"),
        StageOutcome(stage=ParityStage.TENANT_RESOLVED, outcome="SERVER_DERIVED"),
        StageOutcome(stage=ParityStage.CONTEXT_RESOLVED, outcome="EMPTY_OR_LEGACY_COMPATIBLE"),
        StageOutcome(
            stage=ParityStage.INTENT_RESOLVED,
            outcome=str(intent.get("readiness") or "UNRESOLVED"),
            fingerprint=canonical_fingerprint(intent),
        ),
        StageOutcome(stage=ParityStage.SEMANTIC_RESOLVED, outcome="GOVERNED_ADAPTER"),
        StageOutcome(
            stage=ParityStage.PLAN_CREATED,
            outcome="CREATED" if plan else "ABSENT",
            fingerprint=canonical_fingerprint(plan),
        ),
        StageOutcome(stage=ParityStage.EXECUTION_STARTED, outcome="STARTED" if completed else "NOT_STARTED"),
        StageOutcome(
            stage=ParityStage.EXECUTION_COMPLETED,
            outcome="COMPLETED" if completed else "NOT_COMPLETED",
            fingerprint=canonical_fingerprint(execution_facts),
        ),
        StageOutcome(stage=ParityStage.VALIDATED, outcome="PASSED" if completed else "NOT_RUN"),
        StageOutcome(stage=ParityStage.RESPONSE_RENDERED, outcome=str(payload.get("status") or "ERROR")),
    ]
    return AnalyticalParityTrace(
        case_id=case_id,
        expected_resolution_path=expected_resolution_path,
        stages=stages,
        normalized_input_fingerprint=canonical_fingerprint(question.casefold()),
        temporal_fingerprint=canonical_fingerprint(temporal),
        entity_fingerprint=canonical_fingerprint(intent.get("filter_ids") or []),
        context_fingerprint=canonical_fingerprint("EMPTY_OR_LEGACY_COMPATIBLE"),
        intent_fingerprint=canonical_fingerprint(intent),
        selected_capability="DETERMINISTIC_CORE_SUMMARY" if completed else "NONE",
        plan_fingerprint=canonical_fingerprint(plan),
        execution_fingerprint=canonical_fingerprint(execution_facts),
        response_fingerprint=canonical_fingerprint(response_facts),
        provider_invoked=provider_invoked,
    )
