from __future__ import annotations

import time
import uuid

import pytest

from contracts.user_analytical_profile_v2 import FavoriteAssetPreferenceV2
from services.user_analytical_profile.cache import UserProfileCache

from context_resolution_fixtures import resolve_turn
from test_user_analytical_profile_contracts import apply, item, profile


pytestmark = [pytest.mark.unit, pytest.mark.no_database]


def test_cache_handles_one_thousand_owner_scoped_profiles_without_cross_user_hits() -> None:
    cache = UserProfileCache(enabled=True, ttl_seconds=30)
    started = time.perf_counter()
    profiles = []
    for index in range(1000):
        user_id = uuid.UUID(f"20000000-0000-0000-0000-{index + 1:012d}")
        value = profile().model_copy(
            update={
                "user_id": user_id,
                "profile_id": uuid.UUID(f"50000000-0000-0000-0000-{index + 1:012d}"),
                "checksum": f"{index:064x}",
            }
        )
        profiles.append(value)
        cache.put(value)
    hits = sum(
        cache.get(
            tenant_id=value.tenant_id,
            user_id=value.user_id,
            profile_version=value.profile_version,
            checksum=value.checksum,
        )
        is not None
        for value in profiles
    )
    elapsed = time.perf_counter() - started
    assert hits == 1000
    assert elapsed < 5
    first = profiles[0]
    assert cache.get(
        tenant_id=first.tenant_id,
        user_id=profiles[1].user_id,
        profile_version=first.profile_version,
        checksum=first.checksum,
    ) is None


def test_application_engine_handles_one_hundred_preferences_deterministically() -> None:
    result = resolve_turn("Faturamento de junho de 2026")
    preferences = []
    for index in range(100):
        preferences.append(
            item(
                FavoriteAssetPreferenceV2(
                    kind="FAVORITE_METRIC",
                    canonical_id=f"metric_{index}",
                    display_label=f"Métrica {index}",
                    knowledge_asset_id=uuid.UUID(
                        f"80000000-0000-0000-0000-{index + 1:012d}"
                    ),
                ),
                preference_id=uuid.UUID(
                    f"60000000-0000-0000-0000-{index + 1:012d}"
                ),
                key=f"favorite.metric.{index:03d}",
                with_consent=False,
            )
        )
    value = profile(*preferences)
    started = time.perf_counter()
    first = apply(result, value)
    second = apply(result, value)
    elapsed = time.perf_counter() - started
    assert len(first.decisions) == 100
    assert first.deterministic_fingerprint == second.deterministic_fingerprint
    assert elapsed < 5
