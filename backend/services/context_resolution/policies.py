from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class InheritanceMode(str, Enum):
    NEVER = "NEVER"
    SAME_SUBJECT = "SAME_SUBJECT"
    FOLLOW_UP = "FOLLOW_UP"
    ALWAYS = "ALWAYS"


class ContextFieldPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    field: str
    inheritance_mode: InheritanceMode
    replacement_mode: str
    removal_mode: str
    topic_change_behavior: str
    reset_behavior: str
    maximum_age_turns: int = Field(ge=0, le=100)
    requires_same_subject: bool
    requires_same_branch: bool
    deduplication_key: str
    conflict_behavior: str


def _policy(
    field: str,
    inheritance: InheritanceMode,
    replacement: str,
    removal: str,
    topic_change: str,
    *,
    maximum_age_turns: int = 20,
    same_subject: bool = True,
    conflict: str = "KEEP_EXPLICIT",
) -> ContextFieldPolicy:
    return ContextFieldPolicy(
        field=field,
        inheritance_mode=inheritance,
        replacement_mode=replacement,
        removal_mode=removal,
        topic_change_behavior=topic_change,
        reset_behavior="CLEAR",
        maximum_age_turns=maximum_age_turns,
        requires_same_subject=same_subject,
        requires_same_branch=True,
        deduplication_key={
            "metrics": "metric_id",
            "dimensions": "dimension_id",
            "filters": "field_id",
            "periods": "window_id",
            "comparison": "comparison_id",
            "visualizations": "visualization_id",
            "subject": "fingerprint",
            "ordering": "field_id",
            "limit": "value",
            "clarification": "question",
        }[field],
        conflict_behavior=conflict,
    )


FIELD_POLICIES: dict[str, ContextFieldPolicy] = {
    "metrics": _policy(
        "metrics", InheritanceMode.FOLLOW_UP, "REPLACE_EXPLICIT",
        "CLEAR_EXPLICIT", "CLEAR_INCOMPATIBLE", conflict="CLARIFY",
    ),
    "dimensions": _policy(
        "dimensions", InheritanceMode.SAME_SUBJECT, "APPEND_ON_DRILL_DOWN",
        "REMOVE_MATCHING", "CLEAR",
    ),
    "filters": _policy(
        "filters", InheritanceMode.SAME_SUBJECT, "REPLACE_SAME_FIELD",
        "REMOVE_MATCHING", "CLEAR", conflict="CLARIFY",
    ),
    "periods": _policy(
        "periods", InheritanceMode.FOLLOW_UP, "REPLACE_EXPLICIT",
        "CLEAR_EXPLICIT", "CLEAR", conflict="CLARIFY",
    ),
    "comparison": _policy(
        "comparison", InheritanceMode.SAME_SUBJECT, "REPLACE_EXPLICIT",
        "CLEAR_EXPLICIT", "CLEAR", conflict="CLARIFY",
    ),
    "visualizations": _policy(
        "visualizations", InheritanceMode.SAME_SUBJECT, "REPLACE_EXPLICIT",
        "CLEAR_EXPLICIT", "DEFAULT",
    ),
    "subject": _policy(
        "subject", InheritanceMode.FOLLOW_UP, "REPLACE_EXPLICIT",
        "CLEAR_EXPLICIT", "REPLACE", same_subject=False, conflict="CLARIFY",
    ),
    "ordering": _policy(
        "ordering", InheritanceMode.SAME_SUBJECT, "REPLACE_EXPLICIT",
        "CLEAR_EXPLICIT", "CLEAR", maximum_age_turns=10,
    ),
    "limit": _policy(
        "limit", InheritanceMode.SAME_SUBJECT, "REPLACE_EXPLICIT",
        "CLEAR_EXPLICIT", "CLEAR", maximum_age_turns=10,
    ),
    "clarification": _policy(
        "clarification", InheritanceMode.ALWAYS, "RESOLVE_OR_REPLACE",
        "RESOLVE", "CLEAR", maximum_age_turns=3, same_subject=False, conflict="BLOCK",
    ),
}
