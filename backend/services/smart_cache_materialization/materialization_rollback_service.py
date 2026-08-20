"""CAS-governed materialization rollback preserving publication history."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from contracts.smart_cache_materialization_v2 import MaterializationRollbackV2

from .repository import MaterializationRepository


class MaterializationRollbackService:
    def __init__(self, repository: MaterializationRepository):
        self.repository = repository

    async def rollback(
        self,
        tenant_id: str,
        definition_id: str,
        to_snapshot_id: str,
        rolled_back_by: str,
        *,
        expected_lock_version: int,
        permissions: list[str],
    ) -> MaterializationRollbackV2:
        if "materialization:rollback" not in permissions:
            raise PermissionError("materialization:rollback permission is required")
        from_snapshot, _publication = await self.repository.rollback_publication(
            tenant_id,
            definition_id,
            to_snapshot_id,
            rolled_back_by,
            expected_lock_version=expected_lock_version,
        )
        return MaterializationRollbackV2(
            rollback_id=f"rb_{uuid.uuid4().hex}",
            definition_id=definition_id,
            tenant_id=tenant_id,
            from_snapshot_id=from_snapshot,
            to_snapshot_id=to_snapshot_id,
            rolled_back_by=rolled_back_by,
            rolled_back_at=datetime.now(timezone.utc).isoformat(),
        )
