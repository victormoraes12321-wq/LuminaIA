from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.user_analytical_profile import (
    UserAnalyticalProfile,
    UserPreferenceConsent,
    UserPreferenceItem,
    UserProfileDeletionRequest,
    UserProfileEvent,
    UserProfileExport,
)


class UserAnalyticalProfileRepository:
    """Tenant-user scoped PostgreSQL repository."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_profile(self, row: UserAnalyticalProfile) -> UserAnalyticalProfile:
        self.db.add(row)
        await self.db.flush()
        return row

    async def get_profile(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        for_update: bool = False,
    ) -> UserAnalyticalProfile | None:
        stmt = select(UserAnalyticalProfile).where(
            UserAnalyticalProfile.tenant_id == tenant_id,
            UserAnalyticalProfile.user_id == user_id,
            UserAnalyticalProfile.status != "DELETED",
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def bump_profile_cas(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        expected_lock_version: int,
        status: str | None,
        checksum: str,
        updated_at: datetime,
        disabled_at: datetime | None,
    ) -> bool:
        values: dict[str, object] = {
            "profile_version": UserAnalyticalProfile.profile_version + 1,
            "lock_version": UserAnalyticalProfile.lock_version + 1,
            "checksum": checksum,
            "updated_at": updated_at,
        }
        if status is not None:
            values["status"] = status
            values["disabled_at"] = disabled_at
        result = await self.db.execute(
            update(UserAnalyticalProfile)
            .where(
                UserAnalyticalProfile.tenant_id == tenant_id,
                UserAnalyticalProfile.user_id == user_id,
                UserAnalyticalProfile.lock_version == expected_lock_version,
                UserAnalyticalProfile.status != "DELETED",
            )
            .values(**values)
        )
        return bool(result.rowcount)

    async def list_items(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        include_inactive: bool = True,
        limit: int = 100,
        after_id: uuid.UUID | None = None,
    ) -> list[UserPreferenceItem]:
        stmt = select(UserPreferenceItem).where(
            UserPreferenceItem.tenant_id == tenant_id,
            UserPreferenceItem.user_id == user_id,
            UserPreferenceItem.status != "DELETED",
        )
        if not include_inactive:
            stmt = stmt.where(UserPreferenceItem.status == "ACTIVE")
        if after_id is not None:
            stmt = stmt.where(UserPreferenceItem.id > after_id)
        stmt = stmt.order_by(UserPreferenceItem.id).limit(limit)
        return list((await self.db.execute(stmt)).scalars())

    async def get_item(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        preference_id: uuid.UUID,
        for_update: bool = False,
    ) -> UserPreferenceItem | None:
        stmt = select(UserPreferenceItem).where(
            UserPreferenceItem.tenant_id == tenant_id,
            UserPreferenceItem.user_id == user_id,
            UserPreferenceItem.id == preference_id,
            UserPreferenceItem.status != "DELETED",
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_item_by_key(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        preference_type: str,
        preference_key: str,
    ) -> UserPreferenceItem | None:
        return (
            await self.db.execute(
                select(UserPreferenceItem).where(
                    UserPreferenceItem.tenant_id == tenant_id,
                    UserPreferenceItem.user_id == user_id,
                    UserPreferenceItem.preference_type == preference_type,
                    UserPreferenceItem.preference_key == preference_key,
                    UserPreferenceItem.status != "DELETED",
                )
            )
        ).scalar_one_or_none()

    async def create_item(self, row: UserPreferenceItem) -> UserPreferenceItem:
        self.db.add(row)
        await self.db.flush()
        return row

    async def update_item_cas(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        preference_id: uuid.UUID,
        expected_lock_version: int,
        values: dict[str, object],
    ) -> bool:
        result = await self.db.execute(
            update(UserPreferenceItem)
            .where(
                UserPreferenceItem.tenant_id == tenant_id,
                UserPreferenceItem.user_id == user_id,
                UserPreferenceItem.id == preference_id,
                UserPreferenceItem.lock_version == expected_lock_version,
                UserPreferenceItem.status != "DELETED",
            )
            .values(**values)
        )
        return bool(result.rowcount)

    async def get_consent(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        preference_id: uuid.UUID,
        for_update: bool = False,
    ) -> UserPreferenceConsent | None:
        stmt = select(UserPreferenceConsent).where(
            UserPreferenceConsent.tenant_id == tenant_id,
            UserPreferenceConsent.user_id == user_id,
            UserPreferenceConsent.preference_id == preference_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def create_consent(self, row: UserPreferenceConsent) -> UserPreferenceConsent:
        self.db.add(row)
        await self.db.flush()
        return row

    async def update_consent_cas(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        preference_id: uuid.UUID,
        expected_lock_version: int,
        values: dict[str, object],
    ) -> bool:
        result = await self.db.execute(
            update(UserPreferenceConsent)
            .where(
                UserPreferenceConsent.tenant_id == tenant_id,
                UserPreferenceConsent.user_id == user_id,
                UserPreferenceConsent.preference_id == preference_id,
                UserPreferenceConsent.lock_version == expected_lock_version,
            )
            .values(**values)
        )
        return bool(result.rowcount)

    async def add_event(self, row: UserProfileEvent) -> UserProfileEvent:
        self.db.add(row)
        await self.db.flush()
        return row

    async def add_export(self, row: UserProfileExport) -> UserProfileExport:
        self.db.add(row)
        await self.db.flush()
        return row

    async def get_deletion_request(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        idempotency_key_hash: str,
    ) -> UserProfileDeletionRequest | None:
        return (
            await self.db.execute(
                select(UserProfileDeletionRequest).where(
                    UserProfileDeletionRequest.tenant_id == tenant_id,
                    UserProfileDeletionRequest.user_id == user_id,
                    UserProfileDeletionRequest.idempotency_key_hash == idempotency_key_hash,
                )
            )
        ).scalar_one_or_none()

    async def add_deletion_request(
        self, row: UserProfileDeletionRequest
    ) -> UserProfileDeletionRequest:
        self.db.add(row)
        await self.db.flush()
        return row

    async def expirable_preference_ids(
        self,
        *,
        now: datetime,
        limit: int,
    ) -> list[uuid.UUID]:
        rows = await self.db.scalars(
            select(UserPreferenceItem.id)
            .where(
                UserPreferenceItem.status == "ACTIVE",
                UserPreferenceItem.expires_at.is_not(None),
                UserPreferenceItem.expires_at <= now,
            )
            .order_by(UserPreferenceItem.expires_at, UserPreferenceItem.id)
            .limit(limit)
        )
        return list(rows)

    async def stale_export_ids(
        self,
        *,
        now: datetime,
        limit: int,
    ) -> list[uuid.UUID]:
        rows = await self.db.scalars(
            select(UserProfileExport.id)
            .where(
                UserProfileExport.expires_at.is_not(None),
                UserProfileExport.expires_at <= now,
            )
            .order_by(UserProfileExport.expires_at, UserProfileExport.id)
            .limit(limit)
        )
        return list(rows)

    async def stale_deletion_request_ids(
        self,
        *,
        cutoff: datetime,
        limit: int,
    ) -> list[uuid.UUID]:
        rows = await self.db.scalars(
            select(UserProfileDeletionRequest.id)
            .where(
                UserProfileDeletionRequest.status.in_(("COMPLETED", "REJECTED")),
                UserProfileDeletionRequest.requested_at <= cutoff,
            )
            .order_by(
                UserProfileDeletionRequest.requested_at,
                UserProfileDeletionRequest.id,
            )
            .limit(limit)
        )
        return list(rows)
