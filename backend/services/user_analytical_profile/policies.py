from __future__ import annotations

from dataclasses import dataclass

from contracts.user_analytical_profile_v2 import (
    PreferenceOrigin,
    PreferenceRisk,
    UserPreferenceItemV2,
    UserPreferenceType,
)


@dataclass(frozen=True)
class UserProfileFieldPolicy:
    field: str
    preference_types: frozenset[UserPreferenceType]
    risk: PreferenceRisk
    auto_apply: bool
    consent_required: bool
    prompt_allowed: bool
    frontend_allowed: bool
    planner_allowed: bool
    renderer_allowed: bool
    context_allowed: bool
    conflict_policy: str
    expiration_required: bool
    retention_days: int
    allowed_origins: frozenset[PreferenceOrigin]
    required_permission: str


_AUTO_ORIGINS = frozenset(
    {
        PreferenceOrigin.USER_EXPLICIT,
        PreferenceOrigin.SYSTEM_DEFAULT,
        PreferenceOrigin.ADMIN_POLICY,
    }
)


def _policy(
    field: str,
    types: tuple[UserPreferenceType, ...],
    risk: PreferenceRisk,
    *,
    auto: bool,
    consent: bool,
    planner: bool = False,
    renderer: bool = False,
    context: bool = False,
    expiration: bool = False,
    retention_days: int = 365,
) -> UserProfileFieldPolicy:
    return UserProfileFieldPolicy(
        field=field,
        preference_types=frozenset(types),
        risk=risk,
        auto_apply=auto,
        consent_required=consent,
        prompt_allowed=False,
        frontend_allowed=True,
        planner_allowed=planner,
        renderer_allowed=renderer,
        context_allowed=context,
        conflict_policy="CURRENT_REQUEST_AND_CONTEXT_WIN",
        expiration_required=expiration,
        retention_days=retention_days,
        allowed_origins=_AUTO_ORIGINS,
        required_permission="profile:read_own",
    )


USER_PROFILE_FIELD_POLICIES: dict[str, UserProfileFieldPolicy] = {
    "locale": _policy(
        "locale", (UserPreferenceType.LOCALE,), PreferenceRisk.SAFE_PRESENTATION,
        auto=True, consent=False, renderer=True,
    ),
    "timezone": _policy(
        "timezone", (UserPreferenceType.LOCALE,), PreferenceRisk.SAFE_PRESENTATION,
        auto=True, consent=False, renderer=True,
    ),
    "currency_display": _policy(
        "currency_display", (UserPreferenceType.LOCALE,), PreferenceRisk.SAFE_PRESENTATION,
        auto=True, consent=False, renderer=True,
    ),
    "date_format": _policy(
        "date_format", (UserPreferenceType.LOCALE,), PreferenceRisk.SAFE_PRESENTATION,
        auto=True, consent=False, renderer=True,
    ),
    "number_format": _policy(
        "number_format", (UserPreferenceType.LOCALE,), PreferenceRisk.SAFE_PRESENTATION,
        auto=True, consent=False, renderer=True,
    ),
    "visualization": _policy(
        "visualization", (UserPreferenceType.PRESENTATION,), PreferenceRisk.SAFE_PRESENTATION,
        auto=True, consent=False, renderer=True,
    ),
    "table_density": _policy(
        "table_density", (UserPreferenceType.PRESENTATION,), PreferenceRisk.SAFE_PRESENTATION,
        auto=True, consent=False, renderer=True,
    ),
    "page_size": _policy(
        "page_size", (UserPreferenceType.PRESENTATION,), PreferenceRisk.SAFE_PRESENTATION,
        auto=True, consent=False, renderer=True,
    ),
    "decimal_places": _policy(
        "decimal_places", (UserPreferenceType.PRESENTATION,), PreferenceRisk.SAFE_PRESENTATION,
        auto=True, consent=False, renderer=True,
    ),
    "ordering": _policy(
        "ordering",
        (UserPreferenceType.PRESENTATION, UserPreferenceType.ANALYTICAL_DEFAULT),
        PreferenceRisk.VISIBLE_ANALYTICAL_DEFAULT,
        auto=True, consent=True, planner=True, renderer=True,
    ),
    "limit": _policy(
        "limit", (UserPreferenceType.ANALYTICAL_DEFAULT,),
        PreferenceRisk.VISIBLE_ANALYTICAL_DEFAULT,
        auto=True, consent=True, planner=True,
    ),
    "metrics": _policy(
        "metrics",
        (UserPreferenceType.ANALYTICAL_DEFAULT, UserPreferenceType.FAVORITE_METRIC),
        PreferenceRisk.VISIBLE_ANALYTICAL_DEFAULT,
        auto=True, consent=True, planner=True,
    ),
    "dimensions": _policy(
        "dimensions",
        (UserPreferenceType.ANALYTICAL_DEFAULT, UserPreferenceType.FAVORITE_DIMENSION),
        PreferenceRisk.VISIBLE_ANALYTICAL_DEFAULT,
        auto=True, consent=True, planner=True,
    ),
    "entities": _policy(
        "entities",
        (UserPreferenceType.ANALYTICAL_DEFAULT, UserPreferenceType.FAVORITE_ENTITY),
        PreferenceRisk.VISIBLE_ANALYTICAL_DEFAULT,
        auto=True, consent=True, planner=True,
    ),
    "filters": _policy(
        "filters",
        (UserPreferenceType.ANALYTICAL_DEFAULT, UserPreferenceType.SAVED_FILTER_REFERENCE),
        PreferenceRisk.VISIBLE_ANALYTICAL_DEFAULT,
        auto=True, consent=True, planner=True, context=True, expiration=True, retention_days=180,
    ),
    "default_period": _policy(
        "default_period", (UserPreferenceType.ANALYTICAL_DEFAULT,),
        PreferenceRisk.VISIBLE_ANALYTICAL_DEFAULT,
        auto=True, consent=True, planner=True, context=True,
    ),
    "accessibility": _policy(
        "accessibility", (UserPreferenceType.ACCESSIBILITY,), PreferenceRisk.SAFE_PRESENTATION,
        auto=True, consent=False, renderer=True,
    ),
    "saved_references": _policy(
        "saved_references",
        (
            UserPreferenceType.SAVED_FILTER_REFERENCE,
            UserPreferenceType.SAVED_QUERY_REFERENCE,
            UserPreferenceType.SAVED_DASHBOARD_REFERENCE,
        ),
        PreferenceRisk.REFERENCE_ONLY,
        auto=False, consent=False,
    ),
}


def classify_preference(item_type: UserPreferenceType) -> PreferenceRisk:
    if item_type in {
        UserPreferenceType.PRESENTATION,
        UserPreferenceType.LOCALE,
        UserPreferenceType.ACCESSIBILITY,
        UserPreferenceType.INTERACTION,
        UserPreferenceType.PRIVACY,
        UserPreferenceType.RETENTION,
    }:
        return PreferenceRisk.SAFE_PRESENTATION
    if item_type == UserPreferenceType.ANALYTICAL_DEFAULT:
        return PreferenceRisk.VISIBLE_ANALYTICAL_DEFAULT
    if item_type in {
        UserPreferenceType.FAVORITE_METRIC,
        UserPreferenceType.FAVORITE_DIMENSION,
        UserPreferenceType.FAVORITE_ENTITY,
        UserPreferenceType.SAVED_FILTER_REFERENCE,
        UserPreferenceType.SAVED_QUERY_REFERENCE,
        UserPreferenceType.SAVED_DASHBOARD_REFERENCE,
    }:
        return PreferenceRisk.REFERENCE_ONLY
    return PreferenceRisk.FORBIDDEN


def policy_for_item(item: UserPreferenceItemV2) -> UserProfileFieldPolicy | None:
    if item.preference_type == UserPreferenceType.ANALYTICAL_DEFAULT:
        target = getattr(item.content, "target_field", "")
        key = {
            "metric": "metrics",
            "dimension": "dimensions",
            "entity": "entities",
            "filter": "filters",
            "period": "default_period",
            "ordering": "ordering",
            "limit": "limit",
        }.get(target)
        return USER_PROFILE_FIELD_POLICIES.get(key or "")
    if item.preference_type == UserPreferenceType.PRESENTATION:
        return USER_PROFILE_FIELD_POLICIES["visualization"]
    if item.preference_type == UserPreferenceType.LOCALE:
        return USER_PROFILE_FIELD_POLICIES["locale"]
    if item.preference_type == UserPreferenceType.ACCESSIBILITY:
        return USER_PROFILE_FIELD_POLICIES["accessibility"]
    if item.preference_type in {
        UserPreferenceType.FAVORITE_METRIC,
        UserPreferenceType.FAVORITE_DIMENSION,
        UserPreferenceType.FAVORITE_ENTITY,
        UserPreferenceType.SAVED_FILTER_REFERENCE,
        UserPreferenceType.SAVED_QUERY_REFERENCE,
        UserPreferenceType.SAVED_DASHBOARD_REFERENCE,
    }:
        return USER_PROFILE_FIELD_POLICIES["saved_references"]
    return None
