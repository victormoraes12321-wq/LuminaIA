"""Refresh creates a new governed snapshot and never publishes it."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from contracts.smart_cache_materialization_v2 import (
    MaterializationRefreshV2,
    RefreshTrigger,
)

from .materialization_build_service import GovernedMaterializationBuildService


class MaterializationRefreshService:
    def __init__(self, build_service: GovernedMaterializationBuildService):
        self.build_service = build_service

    async def trigger_refresh(
        self,
        *,
        tenant_id: str,
        user_id: str,
        definition_id: str,
        expected_lock_version: int,
        permissions: list[str],
        request_id: str,
        trigger: RefreshTrigger,
    ) -> MaterializationRefreshV2:
        if "materialization:refresh" not in permissions:
            raise PermissionError("materialization:refresh permission is required")
        _build, snapshot = await self.build_service.build_snapshot(
            tenant_id=tenant_id,
            user_id=user_id,
            definition_id=definition_id,
            expected_lock_version=expected_lock_version,
            permissions=[*permissions, "materialization:build"],
            request_id=request_id,
        )
        return MaterializationRefreshV2(
            refresh_id=f"ref_{uuid.uuid4().hex}",
            definition_id=definition_id,
            tenant_id=tenant_id,
            trigger=trigger,
            new_snapshot_id=snapshot.snapshot_id,
            refreshed_at=datetime.now(timezone.utc).isoformat(),
        )
