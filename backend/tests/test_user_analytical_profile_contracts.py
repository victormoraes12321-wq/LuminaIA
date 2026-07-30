from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import TypeAdapter, ValidationError

from contracts.user_analytical_profile_v2 import (
    AccessibilityPreferenceV2,
    AnalyticalDefaultPreferenceV2,
    ConsentStatus,
    LocalePreferenceV2,
    PreferenceApplicationContext,
    PreferenceConsentV2,
    PreferenceCreateV2,
    PreferenceOrigin,
    PreferenceOriginV2,
    PreferenceRisk,
    PreferenceStatus,
    PresentationPreferenceV2,
    ProfileStatus,
    UserAnalyticalProfileV2,
    UserPreferenceContentV2,
    UserPreferenceItemV2,
    UserPreferenceType,
    UserProfileRolloutMode,
)
from contracts.analytical_v2 import FieldOrigin
from contracts.conversation_state_v2 import ConversationStateV2
from services.user_analytical_profile.application import (
    UserPreferenceApplicationEngine,
    stable_fingerprint,
)
from services.user_analytical_profile.cache import UserProfileCache
from services.user_analytical_profile.legacy_adapter import LegacyUserPreferenceAdapter
from services.user_analytical_profile.policies import (
    USER_PROFILE_FIELD_POLICIES,
    classify_preference,
)

from context_resolution_fixtures import REFERENCE, TENANT_ID, USER_ID, persisted, resolve_turn


pytestmark = [pytest.mark.unit, pytest.mark.no_database]

PROFILE_ID = uuid.UUID("50000000-0000-0000-0000-000000000001")
PREFERENCE_ID = uuid.UUID("60000000-0000-0000-0000-000000000001")


def consent(preference_id: uuid.UUID) -> PreferenceConsentV2:
    return PreferenceConsentV2(
        consent_id=uuid.UUID("70000000-0000-0000-0000-000000000001"),
        preference_id=preference_id,
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        purpose="Usar filial padrão quando não houver filial explícita.",
        scope="filters.filial",
        status=ConsentStatus.GRANTED,
        granted_at=REFERENCE,
        policy_version="user-profile-consent/1.0",
        source="USER_ACTION",
        lock_version=0,
        checksum="a" * 64,
    )


def item(
    content,
    *,
    preference_id: uuid.UUID = PREFERENCE_ID,
    key: str = "default.filial",
    with_consent: bool = True,
    origin: PreferenceOrigin = PreferenceOrigin.USER_EXPLICIT,
    status: PreferenceStatus = PreferenceStatus.ACTIVE,
) -> UserPreferenceItemV2:
    preference_type = UserPreferenceType(content.kind)
    risk = classify_preference(preference_type)
    return UserPreferenceItemV2(
        preference_id=preference_id,
        profile_id=PROFILE_ID,
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        preference_type=preference_type,
        preference_key=key,
        content=content,
        risk=risk,
        origin=PreferenceOriginV2(
            kind=origin,
            source_label="Definido pelo usuário",
            confirmed_at=REFERENCE if origin == PreferenceOrigin.USER_EXPLICIT else None,
        ),
        status=status,
        consent=(
            consent(preference_id)
            if with_consent and risk == PreferenceRisk.VISIBLE_ANALYTICAL_DEFAULT
            else None
        ),
        version=1,
        lock_version=0,
        checksum="b" * 64,
        created_at=REFERENCE,
        updated_at=REFERENCE,
    )


def profile(*preferences: UserPreferenceItemV2) -> UserAnalyticalProfileV2:
    return UserAnalyticalProfileV2(
        profile_id=PROFILE_ID,
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        status=ProfileStatus.ACTIVE,
        profile_version=1,
        lock_version=0,
        checksum="c" * 64,
        preferences=list(preferences),
        created_at=REFERENCE,
        updated_at=REFERENCE,
    )


def filial_default(**kwargs) -> UserPreferenceItemV2:
    return item(
        AnalyticalDefaultPreferenceV2(
            target_field="filter",
            canonical_id="centro",
            display_label="Filial Centro",
            filter_field_id="filial",
            filter_operator="EQ",
            filter_values=["centro"],
            knowledge_asset_id=uuid.UUID("80000000-0000-0000-0000-000000000001"),
        ),
        **kwargs,
    )


def context(result, *, mode=UserProfileRolloutMode.V2_READ_WRITE, removals=None):
    return PreferenceApplicationContext(
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        request_id="request-profile-test",
        reference_datetime=REFERENCE,
        current_question=result.resolved_intent.raw_question,
        reset_explicit=result.relationship.value == "RESET",
        removal_fields=removals or [],
        pending_clarification=result.clarification is not None,
        allowed_canonical_ids=["centro", "sul", "norte"],
        allowed_filter_fields=["filial"],
        rollout_mode=mode,
    )


def apply(result, value: UserAnalyticalProfileV2, *, app_context=None):
    return UserPreferenceApplicationEngine().apply(
        current_intent=result.resolved_intent,
        current_question=result.resolved_intent.raw_question,
        conversation_state=result.resolved_state,
        context_resolution=result,
        profile=value,
        context=app_context or context(result),
    )


def test_discriminated_union_rejects_unknown_and_mismatched_content() -> None:
    adapter = TypeAdapter(UserPreferenceContentV2)
    assert isinstance(
        adapter.validate_python(
            {
                "kind": "LOCALE",
                "locale": "pt-BR",
                "timezone": "America/Fortaleza",
                "currency_display": "BRL",
                "date_format": "DD/MM/YYYY",
                "number_format": "pt-BR",
            }
        ),
        LocalePreferenceV2,
    )
    with pytest.raises(ValidationError):
        adapter.validate_python({"kind": "UNKNOWN"})
    with pytest.raises(ValidationError):
        PreferenceCreateV2.model_validate(
            {
                "preference_key": "unsafe",
                "content": {"kind": "PRESENTATION", "sql": "select * from users"},
            }
        )


def test_risk_classification_and_field_policies_are_central_and_complete() -> None:
    assert classify_preference(UserPreferenceType.PRESENTATION) == PreferenceRisk.SAFE_PRESENTATION
    assert classify_preference(UserPreferenceType.ANALYTICAL_DEFAULT) == PreferenceRisk.VISIBLE_ANALYTICAL_DEFAULT
    assert classify_preference(UserPreferenceType.SAVED_QUERY_REFERENCE) == PreferenceRisk.REFERENCE_ONLY
    required = {
        "locale", "timezone", "currency_display", "date_format", "number_format",
        "visualization", "table_density", "page_size", "decimal_places", "ordering",
        "limit", "metrics", "dimensions", "entities", "filters", "default_period",
        "accessibility", "saved_references",
    }
    assert required == set(USER_PROFILE_FIELD_POLICIES)
    assert USER_PROFILE_FIELD_POLICIES["filters"].consent_required
    assert USER_PROFILE_FIELD_POLICIES["filters"].context_allowed


def test_consented_visible_filter_fills_only_an_empty_gap_and_is_public() -> None:
    result = resolve_turn("Faturamento de junho de 2026")
    applied = apply(result, profile(filial_default()))
    assert applied.resolved_intent.filters[0].field_id == "filial"
    assert applied.resolved_intent.filters[0].value == "centro"
    assert applied.resolved_intent.filters[0].origin == FieldOrigin.USER_PREFERENCE
    assert applied.public_summary.has_visible_analytical_default
    assert applied.public_summary.applied[0].value_label == "Filial Centro"


def test_explicit_request_and_active_context_both_override_profile() -> None:
    explicit = resolve_turn("Faturamento de junho de 2026 da filial Sul")
    explicit_result = apply(explicit, profile(filial_default()))
    assert explicit_result.resolved_intent.filters[0].value == "sul"
    assert explicit_result.applied_preference_ids == []

    first = resolve_turn("Faturamento de junho de 2026 da filial Norte")
    follow_up = resolve_turn("E em julho?", state=persisted(first), turn=2)
    inherited = apply(follow_up, profile(filial_default()))
    assert inherited.resolved_intent.filters[0].value == "norte"
    assert inherited.resolved_intent.filters[0].origin == FieldOrigin.INHERITED_CONVERSATION
    assert inherited.applied_preference_ids == []


def test_four_turn_conversation_applies_profile_only_to_semantic_gaps() -> None:
    presentation = item(
        PresentationPreferenceV2(preferred_visualization="BAR_CHART"),
        preference_id=uuid.UUID("60000000-0000-0000-0000-000000000002"),
        key="display.presentation",
        with_consent=False,
    )
    value = profile(filial_default(), presentation)

    turn_1 = resolve_turn("Faturamento de junho de 2026")
    applied_1 = apply(turn_1, value)
    assert applied_1.resolved_intent.filters[0].value == "centro"
    assert applied_1.resolved_intent.requested_visualizations[0].kind.value == "BAR_CHART"

    turn_2 = resolve_turn("E em julho?", state=persisted(turn_1), turn=2)
    applied_2 = apply(turn_2, value)
    assert applied_2.resolved_intent.filters[0].value == "centro"
    assert applied_2.resolved_intent.time_windows[0].start.isoformat() == "2026-07-01"

    turn_3 = resolve_turn(
        "Agora use a filial Sul",
        state=persisted(turn_2),
        turn=3,
    )
    applied_3 = apply(turn_3, value)
    assert applied_3.resolved_intent.filters[0].value == "sul"
    assert applied_3.applied_preference_ids == [presentation.preference_id]

    turn_4 = resolve_turn(
        "Compare com junho e mantenha o gráfico",
        state=persisted(turn_3),
        turn=4,
    )
    applied_4 = apply(turn_4, value)
    assert applied_4.resolved_intent.filters[0].value == "sul"
    assert applied_4.resolved_intent.filters[0].origin == FieldOrigin.INHERITED_CONVERSATION
    assert applied_4.resolved_intent.requested_visualizations[0].kind.value == "BAR_CHART"


def test_removal_reset_and_missing_consent_block_default_without_deleting_it() -> None:
    result = resolve_turn("Faturamento de junho de 2026")
    removed = apply(
        result,
        profile(filial_default()),
        app_context=context(result, removals=["filters"]),
    )
    assert removed.resolved_intent.filters == []
    assert removed.conflicts[0].reason_code == "EXPLICIT_REMOVAL_WINS"

    reset = resolve_turn("Limpe o contexto")
    reset_result = apply(reset, profile(filial_default()))
    assert reset_result.resolved_intent.filters == []
    assert any(
        decision.reason_code == "RESET_BLOCKS_DEFAULTS_THIS_TURN"
        for decision in reset_result.decisions
    )

    no_consent = apply(result, profile(filial_default(with_consent=False)))
    assert no_consent.resolved_intent.filters == []
    assert no_consent.public_summary.consent_required == ["default.filial"]


def test_presentation_applies_without_changing_financial_metric_or_input() -> None:
    result = resolve_turn("Faturamento de junho de 2026")
    original = result.resolved_intent.model_dump(mode="json")
    preference = item(
        PresentationPreferenceV2(
            preferred_visualization="BAR_CHART",
            table_density="COMPACT",
            page_size=50,
            decimal_places=2,
        ),
        key="display.presentation",
        with_consent=False,
    )
    applied = apply(result, profile(preference))
    assert applied.resolved_intent.metric_refs == result.resolved_intent.metric_refs
    assert applied.resolved_intent.requested_visualizations[0].kind.value == "BAR_CHART"
    assert result.resolved_intent.model_dump(mode="json") == original


def test_shadow_mode_is_deterministic_and_never_mutates_intent() -> None:
    result = resolve_turn("Faturamento de junho de 2026")
    value = profile(filial_default())
    first = apply(result, value, app_context=context(result, mode=UserProfileRolloutMode.SHADOW))
    second = apply(result, value, app_context=context(result, mode=UserProfileRolloutMode.SHADOW))
    assert first.resolved_intent == result.resolved_intent
    assert first.applied_preference_ids == []
    assert first.deterministic_fingerprint == second.deterministic_fingerprint


def test_checksum_cache_identity_and_cross_user_are_isolated() -> None:
    assert stable_fingerprint({"b": 2, "a": 1}) == stable_fingerprint({"a": 1, "b": 2})
    assert stable_fingerprint({"a": 1}) != stable_fingerprint({"a": 2})
    value = profile(filial_default())
    cache = UserProfileCache(enabled=True, ttl_seconds=30)
    cache.put(value)
    assert cache.get(
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        profile_version=1,
        checksum=value.checksum,
    ) == value
    assert cache.get(
        tenant_id=TENANT_ID,
        user_id=uuid.uuid4(),
        profile_version=1,
        checksum=value.checksum,
    ) is None


def test_lifecycle_and_consent_contracts_fail_closed() -> None:
    with pytest.raises(ValidationError):
        item(
            LocalePreferenceV2(),
            status=PreferenceStatus.DELETED,
            with_consent=False,
        )
    with pytest.raises(ValidationError):
        PreferenceConsentV2(
            consent_id=uuid.uuid4(),
            preference_id=PREFERENCE_ID,
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            purpose="Teste",
            scope="filters",
            status=ConsentStatus.REVOKED,
            granted_at=REFERENCE,
            policy_version="v1",
            source="USER_ACTION",
            lock_version=0,
            checksum="d" * 64,
        )


def test_accessibility_is_typed_and_not_an_analytical_default() -> None:
    preference = item(
        AccessibilityPreferenceV2(reduced_motion=True, accessible_labels=True),
        key="display.accessibility",
        with_consent=False,
    )
    assert preference.risk == PreferenceRisk.SAFE_PRESENTATION


def test_legacy_adapter_imports_only_safe_presentation() -> None:
    class Legacy:
        tenant_id = TENANT_ID
        user_id = USER_ID
        scope = "default"
        format = "grafico"

    result = LegacyUserPreferenceAdapter().adapt_dashboard_preference(
        Legacy(), tenant_id=TENANT_ID, user_id=USER_ID
    )
    assert result.preferences[0].origin == PreferenceOrigin.LEGACY_IMPORT
    assert result.preferences[0].content.kind == "PRESENTATION"
    assert result.warnings
