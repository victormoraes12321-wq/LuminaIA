from __future__ import annotations

import copy
import time
import uuid
from dataclasses import dataclass

from contracts.user_analytical_profile_v2 import UserAnalyticalProfileV2


@dataclass
class _Entry:
    expires_at: float
    profile: UserAnalyticalProfileV2


class UserProfileCache:
    def __init__(self, *, enabled: bool = False, ttl_seconds: int = 30) -> None:
        self.enabled = enabled
        self.ttl_seconds = ttl_seconds
        self._items: dict[tuple[uuid.UUID, uuid.UUID, int, str], _Entry] = {}

    def get(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        profile_version: int,
        checksum: str,
    ) -> UserAnalyticalProfileV2 | None:
        if not self.enabled:
            return None
        key = (tenant_id, user_id, profile_version, checksum)
        entry = self._items.get(key)
        if entry is None:
            return None
        if entry.expires_at <= time.monotonic():
            self._items.pop(key, None)
            return None
        return copy.deepcopy(entry.profile)

    def put(self, profile: UserAnalyticalProfileV2) -> None:
        if not self.enabled:
            return
        key = (
            profile.tenant_id,
            profile.user_id,
            profile.profile_version,
            profile.checksum,
        )
        self._items[key] = _Entry(
            expires_at=time.monotonic() + self.ttl_seconds,
            profile=copy.deepcopy(profile),
        )

    def invalidate(self, *, tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
        for key in list(self._items):
            if key[0] == tenant_id and key[1] == user_id:
                self._items.pop(key, None)
