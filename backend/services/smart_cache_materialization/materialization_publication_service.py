"""
LuminaAI — Materialization Publication Service
lumina.smart-cache-materialization/1.0
"""
import logging
from typing import Optional
from contracts.smart_cache_materialization_v2 import MaterializationPublicationV2
from .repository import MaterializationRepository

logger = logging.getLogger(__name__)


class MaterializationPublicationService:
    def __init__(self, repository: MaterializationRepository):
        self.repository = repository

    async def publish(
        self,
        tenant_id: str,
        definition_id: str,
        snapshot_id: str,
        published_by: str,
        *,
        expected_lock_version: int,
        permissions: list[str],
    ) -> MaterializationPublicationV2:
        if "materialization:publish" not in permissions:
            raise PermissionError("materialization:publish permission is required")
        pub_model = await self.repository.publish_snapshot(
            tenant_id,
            definition_id,
            snapshot_id,
            published_by,
            expected_lock_version=expected_lock_version,
        )
        return MaterializationPublicationV2(
            publication_id=str(pub_model.id),
            definition_id=definition_id,
            tenant_id=tenant_id,
            active_snapshot_id=pub_model.active_snapshot_id,
            previous_snapshot_id=pub_model.previous_snapshot_id,
            published_by=str(pub_model.published_by),
            published_at=pub_model.published_at.isoformat(),
            lock_version=pub_model.lock_version,
        )
