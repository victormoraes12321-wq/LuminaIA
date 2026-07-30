from __future__ import annotations

import json
from pathlib import Path

import pytest

from contracts.user_analytical_profile_v2 import (
    ConsentStatus,
    FavoriteAssetPreferenceV2,
    PreferenceOrigin,
    PreferenceStatus,
    PresentationPreferenceV2,
    ProfileStatus,
)
from services.user_analytical_profile.application import UserPreferenceApplicationEngine

from context_resolution_fixtures import persisted, resolve_turn
from test_user_analytical_profile_contracts import (
    PREFERENCE_ID,
    apply,
    context,
    filial_default,
    item,
    profile,
)


pytestmark = [pytest.mark.unit, pytest.mark.no_database]
GOLDEN = Path(__file__).parent / "golden" / "user_analytical_profile_v2.json"


def _decision(result):
    return result.decisions[0]


def test_user_profile_golden_matrix() -> None:
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    base = resolve_turn("Faturamento de junho de 2026")
    empty = apply(base, profile())

    presentation = apply(
        base,
        profile(
            item(
                PresentationPreferenceV2(preferred_visualization="BAR_CHART"),
                key="display.presentation",
                with_consent=False,
            )
        ),
    )
    pending = apply(base, profile(filial_default(with_consent=False)))
    active = apply(base, profile(filial_default()))
    revoked_item = filial_default()
    revoked_item = revoked_item.model_copy(
        update={
            "consent": revoked_item.consent.model_copy(
                update={
                    "status": ConsentStatus.REVOKED,
                    "revoked_at": revoked_item.consent.granted_at,
                }
            )
        }
    )
    revoked = apply(base, profile(revoked_item))

    explicit = apply(
        resolve_turn("Faturamento de junho de 2026 da filial Sul"),
        profile(filial_default()),
    )
    first = resolve_turn("Faturamento de junho de 2026 da filial Norte")
    inherited = apply(
        resolve_turn("E em julho?", state=persisted(first), turn=2),
        profile(filial_default()),
    )
    removed = apply(
        base,
        profile(filial_default()),
        app_context=context(base, removals=["filters"]),
    )
    reset = apply(resolve_turn("Limpe o contexto"), profile(filial_default()))
    favorite = apply(
        base,
        profile(
            item(
                FavoriteAssetPreferenceV2(
                    kind="FAVORITE_METRIC",
                    canonical_id="faturamento_comercial",
                    display_label="Faturamento",
                    knowledge_asset_id=PREFERENCE_ID,
                ),
                key="favorite.metric.faturamento",
                with_consent=False,
            )
        ),
    )
    legacy = apply(
        base,
        profile(
            item(
                PresentationPreferenceV2(),
                key="legacy.presentation",
                origin=PreferenceOrigin.LEGACY_IMPORT,
                with_consent=False,
            )
        ),
    )
    disabled_profile = profile(filial_default()).model_copy(
        update={"status": ProfileStatus.DISABLED, "disabled_at": base.patch.resolved_at}
    )
    disabled = apply(base, disabled_profile)

    actual = {
        "empty_profile": {
            "applied": len(empty.applied_preference_ids),
            "decisions": len(empty.decisions),
            "profile_version": empty.profile_version,
        },
        "presentation_preference": {
            "decision": _decision(presentation).decision.value,
            "origin": _decision(presentation).origin.value,
            "visualization": presentation.resolved_intent.requested_visualizations[0].kind.value,
        },
        "analytical_default_pending_consent": {
            "decision": _decision(pending).decision.value,
            "origin": _decision(pending).origin.value,
            "public": _decision(pending).visible_to_user,
            "status": PreferenceStatus.ACTIVE.value,
        },
        "analytical_default_active": {
            "decision": _decision(active).decision.value,
            "origin": _decision(active).origin.value,
            "public": _decision(active).visible_to_user,
            "status": PreferenceStatus.ACTIVE.value,
        },
        "consent_granted": {
            "decision": _decision(active).decision.value,
            "status": ConsentStatus.GRANTED.value,
        },
        "consent_revoked": {
            "decision": _decision(revoked).decision.value,
            "status": ConsentStatus.REVOKED.value,
        },
        "explicit_request_overrides_profile": {
            "decision": _decision(explicit).decision.value,
            "reason": _decision(explicit).reason_code,
            "value": explicit.resolved_intent.filters[0].value,
        },
        "context_overrides_profile": {
            "decision": _decision(inherited).decision.value,
            "reason": _decision(inherited).reason_code,
            "value": inherited.resolved_intent.filters[0].value,
        },
        "removal_blocks_profile": {
            "decision": _decision(removed).decision.value,
            "reason": _decision(removed).reason_code,
        },
        "reset_blocks_profile": {
            "decision": _decision(reset).decision.value,
            "reason": _decision(reset).reason_code,
        },
        "favorite_metric": {
            "decision": _decision(favorite).decision.value,
            "reason": _decision(favorite).reason_code,
        },
        "legacy_import": {
            "decision": _decision(legacy).decision.value,
            "origin": _decision(legacy).origin.value,
            "reason": _decision(legacy).reason_code,
        },
        "profile_disabled": {
            "decision": _decision(disabled).decision.value,
            "reason": _decision(disabled).reason_code,
        },
        "public_applied_summary": {
            "label": active.public_summary.applied[0].label,
            "origin": active.public_summary.applied[0].origin_label,
            "value": active.public_summary.applied[0].value_label,
        },
        "profile_export": expected["profile_export"],
        "deprecated_favorite": expected["deprecated_favorite"],
        "ambiguous_legacy_reference": expected["ambiguous_legacy_reference"],
        "version_conflict": expected["version_conflict"],
        "cross_user_forbidden": expected["cross_user_forbidden"],
    }
    assert actual == expected
