from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from contracts.user_analytical_profile_v2 import RetentionSelectionV2

from .repository import UserAnalyticalProfileRepository


@dataclass(frozen=True)
class UserProfileRetentionPolicy:
    expired_preference_days: int = 90
    export_days: int = 30
    deletion_request_days: int = 365
    batch_size: int = 500


class UserProfileRetentionService:
    def __init__(
        self,
        repository: UserAnalyticalProfileRepository,
        *,
        policy: UserProfileRetentionPolicy | None = None,
        clock,
    ) -> None:
        self.repository = repository
        self.policy = policy or UserProfileRetentionPolicy()
        self.clock = clock

    async def select(self) -> RetentionSelectionV2:
        now: datetime = self.clock()
        return RetentionSelectionV2(
            expired_preference_ids=await self.repository.expirable_preference_ids(
                now=now,
                limit=self.policy.batch_size,
            ),
            stale_export_ids=await self.repository.stale_export_ids(
                now=now,
                limit=self.policy.batch_size,
            ),
            stale_deletion_request_ids=await self.repository.stale_deletion_request_ids(
                cutoff=now - timedelta(days=self.policy.deletion_request_days),
                limit=self.policy.batch_size,
            ),
            evaluated_at=now,
        )
