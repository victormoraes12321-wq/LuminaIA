"""Tenant-scoped PostgreSQL repositories for smart cache/materializations."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import JsonValue
from sqlalchemy import and_, delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.smart_cache_materialization import (
    MaterializationBuildModel,
    MaterializationDefinitionModel,
    MaterializationDependencyModel,
    MaterializationEventModel,
    MaterializationPublicationModel,
    MaterializationSnapshotModel,
    SmartCacheEntryDependencyModel,
    SmartCacheEntryModel,
    SmartCacheEventModel,
    SmartCacheGenerationModel,
    SmartCacheLeaseModel,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def trusted_tenant_uuid(tenant_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(tenant_id))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError("trusted tenant id must be a UUID") from exc


def _owner_checksum(owner_token: str) -> str:
    if len(owner_token) < 16:
        raise ValueError("internal lease owner token is too short")
    return hashlib.sha256(owner_token.encode("utf-8")).hexdigest()


class SmartCacheRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_generation(self, tenant_id: str, target_scope: str) -> int:
        result = await self.session.execute(
            select(SmartCacheGenerationModel.generation).where(
                SmartCacheGenerationModel.tenant_id == trusted_tenant_uuid(tenant_id),
                SmartCacheGenerationModel.target_scope == target_scope,
            )
        )
        return result.scalar_one_or_none() or 1

    async def increment_generation(self, tenant_id: str, target_scope: str, reason: str) -> int:
        tenant_uuid = trusted_tenant_uuid(tenant_id)
        result = await self.session.execute(
            text(
                """
                INSERT INTO smart_cache_generations
                    (id, tenant_id, target_scope, generation, reason)
                VALUES (:id, :tenant_id, :target_scope, 1, :reason)
                ON CONFLICT (tenant_id, target_scope) DO UPDATE
                SET generation = smart_cache_generations.generation + 1,
                    reason = EXCLUDED.reason,
                    updated_at = NOW()
                RETURNING generation
                """
            ),
            {"id": uuid.uuid4(), "tenant_id": tenant_uuid, "target_scope": target_scope, "reason": reason},
        )
        generation = int(result.scalar_one())
        await self.session.commit()
        return generation

    async def get_entry_by_key_checksum(
        self, tenant_id: str, cache_key_checksum: str
    ) -> Optional[SmartCacheEntryModel]:
        result = await self.session.execute(
            select(SmartCacheEntryModel).where(
                SmartCacheEntryModel.tenant_id == trusted_tenant_uuid(tenant_id),
                SmartCacheEntryModel.cache_key_checksum == cache_key_checksum,
                SmartCacheEntryModel.status == "ACTIVE",
            )
        )
        return result.scalar_one_or_none()

    async def get_dependency_tags(self, tenant_id: str, entry_id: uuid.UUID) -> list[str]:
        result = await self.session.execute(
            select(SmartCacheEntryDependencyModel.tag)
            .where(
                SmartCacheEntryDependencyModel.tenant_id == trusted_tenant_uuid(tenant_id),
                SmartCacheEntryDependencyModel.entry_id == entry_id,
            )
            .order_by(SmartCacheEntryDependencyModel.tag)
        )
        return list(result.scalars())

    async def save_entry(
        self,
        *,
        entry_id: uuid.UUID,
        tenant_id: str,
        cache_type: str,
        cache_key_checksum: str,
        scope_fingerprint: str,
        permission_fingerprint: str,
        query_fingerprint: str,
        analytical_catalog_version: str,
        source_sync_version: str,
        source_watermark: str,
        validation_policy_version: str,
        compiler_version: str,
        tool_registry_snapshot: str,
        certification_id: str,
        tenant_proof_id: str,
        generation: int,
        payload_size_bytes: int,
        classification: str,
        payload_json: dict[str, JsonValue],
        payload_checksum: str,
        dependency_tags: list[str],
        entry_checksum: str,
        expires_at: datetime,
    ) -> SmartCacheEntryModel:
        tenant_uuid = trusted_tenant_uuid(tenant_id)
        existing = await self.get_entry_by_key_checksum(tenant_id, cache_key_checksum)
        if existing is not None:
            entry = existing
            entry.payload_json = payload_json
            entry.payload_checksum = payload_checksum
            entry.generation = generation
            entry.payload_size_bytes = payload_size_bytes
            entry.entry_checksum = entry_checksum
            entry.expires_at = expires_at
            entry.status = "ACTIVE"
            entry.freshness = "FRESH"
            entry.invalidated_at = None
            entry.certification_id = certification_id
            entry.tenant_proof_id = tenant_proof_id
            await self.session.execute(
                delete(SmartCacheEntryDependencyModel).where(
                    SmartCacheEntryDependencyModel.tenant_id == tenant_uuid,
                    SmartCacheEntryDependencyModel.entry_id == entry.id,
                )
            )
        else:
            entry = SmartCacheEntryModel(
                id=entry_id,
                tenant_id=tenant_uuid,
                cache_type=cache_type,
                cache_key_checksum=cache_key_checksum,
                scope_fingerprint=scope_fingerprint,
                permission_fingerprint=permission_fingerprint,
                query_fingerprint=query_fingerprint,
                analytical_catalog_version=analytical_catalog_version,
                source_sync_version=source_sync_version,
                source_watermark=source_watermark,
                validation_policy_version=validation_policy_version,
                compiler_version=compiler_version,
                tool_registry_snapshot=tool_registry_snapshot,
                certification_id=certification_id,
                tenant_proof_id=tenant_proof_id,
                generation=generation,
                payload_size_bytes=payload_size_bytes,
                classification=classification,
                payload_json=payload_json,
                payload_checksum=payload_checksum,
                entry_checksum=entry_checksum,
                expires_at=expires_at,
            )
            self.session.add(entry)
            await self.session.flush()
        for tag in sorted(set(dependency_tags)):
            self.session.add(
                SmartCacheEntryDependencyModel(tenant_id=tenant_uuid, entry_id=entry.id, tag=tag)
            )
        await self.session.commit()
        return entry

    async def increment_hit_count(self, tenant_id: str, entry_id: uuid.UUID) -> None:
        await self.session.execute(
            update(SmartCacheEntryModel)
            .where(
                SmartCacheEntryModel.tenant_id == trusted_tenant_uuid(tenant_id),
                SmartCacheEntryModel.id == entry_id,
            )
            .values(hit_count=SmartCacheEntryModel.hit_count + 1)
        )
        await self.session.commit()

    async def mark_entry(self, tenant_id: str, entry_id: uuid.UUID, *, status: str, freshness: str) -> None:
        await self.session.execute(
            update(SmartCacheEntryModel)
            .where(
                SmartCacheEntryModel.tenant_id == trusted_tenant_uuid(tenant_id),
                SmartCacheEntryModel.id == entry_id,
            )
            .values(status=status, freshness=freshness, invalidated_at=utc_now())
        )
        await self.session.commit()

    async def invalidate_entries_by_tag(self, tenant_id: str, tag: str) -> int:
        tenant_uuid = trusted_tenant_uuid(tenant_id)
        subquery = select(SmartCacheEntryDependencyModel.entry_id).where(
            SmartCacheEntryDependencyModel.tenant_id == tenant_uuid,
            SmartCacheEntryDependencyModel.tag == tag,
        )
        result = await self.session.execute(
            update(SmartCacheEntryModel)
            .where(
                SmartCacheEntryModel.tenant_id == tenant_uuid,
                SmartCacheEntryModel.id.in_(subquery),
                SmartCacheEntryModel.status == "ACTIVE",
            )
            .values(status="INVALIDATED", freshness="INVALIDATED", invalidated_at=utc_now())
        )
        await self.session.commit()
        return int(result.rowcount or 0)

    async def acquire_lease(
        self, tenant_id: str, cache_key_checksum: str, owner_token: str, ttl_seconds: int
    ) -> bool:
        if ttl_seconds < 1 or ttl_seconds > 300:
            raise ValueError("lease TTL must be between 1 and 300 seconds")
        result = await self.session.execute(
            text(
                """
                INSERT INTO smart_cache_leases
                    (id, tenant_id, cache_key_checksum, owner_token_checksum, status, expires_at)
                VALUES (:id, :tenant_id, :cache_key, :owner, 'HELD', NOW() + (:ttl * INTERVAL '1 second'))
                ON CONFLICT (tenant_id, cache_key_checksum) DO UPDATE
                SET owner_token_checksum = EXCLUDED.owner_token_checksum,
                    status = 'HELD', acquired_at = NOW(), expires_at = EXCLUDED.expires_at,
                    lock_version = smart_cache_leases.lock_version + 1
                WHERE smart_cache_leases.expires_at <= NOW()
                   OR smart_cache_leases.status IN ('RELEASED', 'EXPIRED')
                RETURNING id
                """
            ),
            {
                "id": uuid.uuid4(),
                "tenant_id": trusted_tenant_uuid(tenant_id),
                "cache_key": cache_key_checksum,
                "owner": _owner_checksum(owner_token),
                "ttl": ttl_seconds,
            },
        )
        acquired = result.scalar_one_or_none() is not None
        await self.session.commit()
        return acquired

    async def release_lease(self, tenant_id: str, cache_key_checksum: str, owner_token: str) -> bool:
        result = await self.session.execute(
            update(SmartCacheLeaseModel)
            .where(
                SmartCacheLeaseModel.tenant_id == trusted_tenant_uuid(tenant_id),
                SmartCacheLeaseModel.cache_key_checksum == cache_key_checksum,
                SmartCacheLeaseModel.owner_token_checksum == _owner_checksum(owner_token),
                SmartCacheLeaseModel.status == "HELD",
            )
            .values(status="RELEASED", lock_version=SmartCacheLeaseModel.lock_version + 1)
        )
        await self.session.commit()
        return bool(result.rowcount)

    async def log_event(
        self,
        tenant_id: str,
        event_type: str,
        reason_code: str,
        cache_key_checksum: Optional[str] = None,
        user_id: Optional[str] = None,
        decision: Optional[str] = None,
        details: Optional[dict[str, JsonValue]] = None,
    ) -> None:
        self.session.add(
            SmartCacheEventModel(
                tenant_id=trusted_tenant_uuid(tenant_id),
                event_type=event_type,
                reason_code=reason_code,
                cache_key_checksum=cache_key_checksum,
                user_id=uuid.UUID(user_id) if user_id else None,
                decision=decision,
                details_json=details or {},
            )
        )
        await self.session.commit()

    async def delete_expired_entries(
        self, tenant_id: str, *, dry_run: bool = True, limit: int = 100, cursor: str | None = None
    ) -> tuple[int, int, str | None]:
        if limit < 1 or limit > 1000:
            raise ValueError("GC limit must be between 1 and 1000")
        tenant_uuid = trusted_tenant_uuid(tenant_id)
        clauses = [
            SmartCacheEntryModel.tenant_id == tenant_uuid,
            SmartCacheEntryModel.expires_at < utc_now(),
        ]
        if cursor:
            clauses.append(SmartCacheEntryModel.id > uuid.UUID(cursor))
        result = await self.session.execute(
            select(SmartCacheEntryModel)
            .where(*clauses)
            .order_by(SmartCacheEntryModel.id)
            .limit(limit)
        )
        entries = list(result.scalars())
        count = len(entries)
        bytes_freed = sum(item.payload_size_bytes for item in entries)
        next_cursor = str(entries[-1].id) if count == limit else None
        if not dry_run and entries:
            ids = [item.id for item in entries]
            await self.session.execute(
                delete(SmartCacheEntryModel).where(
                    SmartCacheEntryModel.tenant_id == tenant_uuid,
                    SmartCacheEntryModel.id.in_(ids),
                )
            )
        if not dry_run:
            await self.session.execute(
                delete(SmartCacheLeaseModel).where(
                    SmartCacheLeaseModel.tenant_id == tenant_uuid,
                    SmartCacheLeaseModel.expires_at < utc_now(),
                )
            )
            await self.session.commit()
        return count, bytes_freed, next_cursor

    async def statistics(self, tenant_id: str) -> dict[str, int | float]:
        tenant_uuid = trusted_tenant_uuid(tenant_id)
        event_rows = await self.session.execute(
            select(SmartCacheEventModel.decision, func.count(SmartCacheEventModel.id))
            .where(SmartCacheEventModel.tenant_id == tenant_uuid)
            .group_by(SmartCacheEventModel.decision)
        )
        decisions = {str(name): int(count) for name, count in event_rows.all() if name}
        entry_row = await self.session.execute(
            select(
                func.count(SmartCacheEntryModel.id),
                func.coalesce(func.sum(SmartCacheEntryModel.payload_size_bytes), 0),
            ).where(
                SmartCacheEntryModel.tenant_id == tenant_uuid,
                SmartCacheEntryModel.status == "ACTIVE",
            )
        )
        active_entries, active_bytes = entry_row.one()
        leases = await self.session.scalar(
            select(func.count(SmartCacheLeaseModel.id)).where(
                SmartCacheLeaseModel.tenant_id == tenant_uuid,
                SmartCacheLeaseModel.status == "HELD",
                SmartCacheLeaseModel.expires_at > utc_now(),
            )
        )
        hits = decisions.get("HIT", 0)
        misses = decisions.get("MISS", 0)
        total = sum(decisions.values())
        return {
            "total_lookups": total,
            "hit_count": hits,
            "miss_count": misses,
            "bypass_count": decisions.get("BYPASS", 0),
            "stale_count": decisions.get("STALE", 0),
            "hit_rate": (hits / total) if total else 0.0,
            "active_entries_count": int(active_entries or 0),
            "active_payload_bytes": int(active_bytes or 0),
            "active_leases_count": int(leases or 0),
        }


class MaterializationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_definition(
        self, tenant_id: str, definition_id: str, version: int | None = None
    ) -> Optional[MaterializationDefinitionModel]:
        clauses = [
            MaterializationDefinitionModel.tenant_id == trusted_tenant_uuid(tenant_id),
            MaterializationDefinitionModel.definition_id == definition_id,
        ]
        if version is not None:
            clauses.append(MaterializationDefinitionModel.version == version)
        result = await self.session.execute(
            select(MaterializationDefinitionModel)
            .where(*clauses)
            .order_by(MaterializationDefinitionModel.version.desc())
        )
        return result.scalars().first()

    async def save_definition(
        self,
        *,
        tenant_id: str,
        definition_id: str,
        canonical_name: str,
        materialization_type: str,
        classification: str,
        query_json: dict[str, JsonValue],
        source_json: dict[str, JsonValue],
        query_fingerprint: str,
        checksum: str,
        version: int = 1,
    ) -> MaterializationDefinitionModel:
        definition = MaterializationDefinitionModel(
            tenant_id=trusted_tenant_uuid(tenant_id),
            definition_id=definition_id,
            canonical_name=canonical_name,
            materialization_type=materialization_type,
            classification=classification,
            lifecycle="DRAFT",
            version=version,
            query_json=query_json,
            source_json=source_json,
            query_fingerprint=query_fingerprint,
            checksum=checksum,
        )
        self.session.add(definition)
        await self.session.commit()
        return definition

    async def transition_definition(
        self,
        tenant_id: str,
        definition_id: str,
        version: int,
        *,
        expected_lock_version: int,
        expected_lifecycle: str,
        new_lifecycle: str,
    ) -> MaterializationDefinitionModel:
        result = await self.session.execute(
            update(MaterializationDefinitionModel)
            .where(
                MaterializationDefinitionModel.tenant_id == trusted_tenant_uuid(tenant_id),
                MaterializationDefinitionModel.definition_id == definition_id,
                MaterializationDefinitionModel.version == version,
                MaterializationDefinitionModel.lock_version == expected_lock_version,
                MaterializationDefinitionModel.lifecycle == expected_lifecycle,
            )
            .values(
                lifecycle=new_lifecycle,
                lock_version=MaterializationDefinitionModel.lock_version + 1,
                updated_at=utc_now(),
            )
            .returning(MaterializationDefinitionModel.id)
        )
        if result.scalar_one_or_none() is None:
            await self.session.rollback()
            raise RuntimeError("materialization lifecycle CAS conflict")
        await self.session.commit()
        definition = await self.get_definition(tenant_id, definition_id, version)
        assert definition is not None
        return definition

    async def mark_definition_failed(
        self, tenant_id: str, definition_id: str, version: int
    ) -> None:
        await self.session.execute(
            update(MaterializationDefinitionModel)
            .where(
                MaterializationDefinitionModel.tenant_id == trusted_tenant_uuid(tenant_id),
                MaterializationDefinitionModel.definition_id == definition_id,
                MaterializationDefinitionModel.version == version,
                MaterializationDefinitionModel.lifecycle.in_(["BUILDING", "VALIDATING"]),
            )
            .values(
                lifecycle="FAILED",
                lock_version=MaterializationDefinitionModel.lock_version + 1,
                updated_at=utc_now(),
            )
        )
        await self.session.commit()

    async def save_build(
        self,
        *,
        tenant_id: str,
        build_id: str,
        definition_id: str,
        definition_version: int,
        status: str,
        snapshot_id: str | None = None,
        duration_ms: float = 0.0,
        error_code: str | None = None,
    ) -> MaterializationBuildModel:
        build = MaterializationBuildModel(
            tenant_id=trusted_tenant_uuid(tenant_id),
            build_id=build_id,
            definition_id=definition_id,
            definition_version=definition_version,
            status=status,
            snapshot_id=snapshot_id,
            build_duration_ms=duration_ms,
            error_code=error_code,
            completed_at=utc_now() if status in {"READY", "FAILED", "CANCELLED"} else None,
        )
        self.session.add(build)
        await self.session.commit()
        return build

    async def save_snapshot(
        self,
        *,
        tenant_id: str,
        snapshot_id: str,
        definition_id: str,
        definition_version: int,
        row_count: int,
        fact_count: int,
        payload_size_bytes: int,
        certification_id: str,
        certification_status: str,
        tenant_proof_id: str,
        watermark: str,
        source_sync_version: str,
        payload_json: dict[str, JsonValue],
        payload_checksum: str,
        checksum: str,
    ) -> MaterializationSnapshotModel:
        snapshot = MaterializationSnapshotModel(
            tenant_id=trusted_tenant_uuid(tenant_id),
            snapshot_id=snapshot_id,
            definition_id=definition_id,
            definition_version=definition_version,
            row_count=row_count,
            fact_count=fact_count,
            payload_size_bytes=payload_size_bytes,
            certification_id=certification_id,
            certification_status=certification_status,
            tenant_proof_id=tenant_proof_id,
            watermark=watermark,
            source_sync_version=source_sync_version,
            freshness="FRESH",
            payload_json=payload_json,
            payload_checksum=payload_checksum,
            checksum=checksum,
        )
        self.session.add(snapshot)
        await self.session.commit()
        return snapshot

    async def get_snapshot_by_id(
        self, tenant_id: str, snapshot_id: str
    ) -> Optional[MaterializationSnapshotModel]:
        result = await self.session.execute(
            select(MaterializationSnapshotModel).where(
                MaterializationSnapshotModel.tenant_id == trusted_tenant_uuid(tenant_id),
                MaterializationSnapshotModel.snapshot_id == snapshot_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_active_publication(
        self, tenant_id: str, definition_id: str
    ) -> Optional[MaterializationPublicationModel]:
        result = await self.session.execute(
            select(MaterializationPublicationModel).where(
                MaterializationPublicationModel.tenant_id == trusted_tenant_uuid(tenant_id),
                MaterializationPublicationModel.definition_id == definition_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_published_snapshot(
        self, tenant_id: str, definition_id: str
    ) -> Optional[MaterializationSnapshotModel]:
        publication = await self.get_active_publication(tenant_id, definition_id)
        if publication is None:
            return None
        return await self.get_snapshot_by_id(tenant_id, publication.active_snapshot_id)

    async def publish_snapshot(
        self,
        tenant_id: str,
        definition_id: str,
        snapshot_id: str,
        published_by: str,
        *,
        expected_lock_version: int,
    ) -> MaterializationPublicationModel:
        tenant_uuid = trusted_tenant_uuid(tenant_id)
        snapshot = await self.get_snapshot_by_id(tenant_id, snapshot_id)
        definition = await self.get_definition(tenant_id, definition_id)
        if snapshot is None or definition is None or snapshot.definition_id != definition_id:
            raise ValueError("snapshot does not belong to the trusted tenant and definition")
        if snapshot.freshness != "FRESH" or snapshot.certification_status != "VALID":
            raise ValueError("only fresh and validly certified snapshots can be published")
        if definition.lifecycle != "READY":
            raise ValueError("materialization definition must be READY")

        result = await self.session.execute(
            select(MaterializationPublicationModel)
            .where(
                MaterializationPublicationModel.tenant_id == tenant_uuid,
                MaterializationPublicationModel.definition_id == definition_id,
            )
            .with_for_update()
        )
        publication = result.scalar_one_or_none()
        if publication is not None:
            if publication.lock_version != expected_lock_version:
                raise RuntimeError("materialization publication CAS conflict")
            publication.previous_snapshot_id = publication.active_snapshot_id
            publication.active_snapshot_id = snapshot_id
            publication.definition_version = snapshot.definition_version
            publication.published_by = uuid.UUID(published_by)
            publication.published_at = utc_now()
            publication.lock_version += 1
        else:
            if expected_lock_version != 0:
                raise RuntimeError("first publication requires lock version zero")
            publication = MaterializationPublicationModel(
                tenant_id=tenant_uuid,
                definition_id=definition_id,
                definition_version=snapshot.definition_version,
                active_snapshot_id=snapshot_id,
                published_by=uuid.UUID(published_by),
                lock_version=1,
            )
            self.session.add(publication)
        definition.lifecycle = "PUBLISHED"
        definition.lock_version += 1
        definition.updated_at = utc_now()
        self.session.add(
            MaterializationEventModel(
                tenant_id=tenant_uuid,
                definition_id=definition_id,
                event_type="PUBLISHED",
                user_id=uuid.UUID(published_by),
                details_json={"snapshot_id": snapshot_id},
            )
        )
        await self.session.commit()
        return publication

    async def rollback_publication(
        self,
        tenant_id: str,
        definition_id: str,
        to_snapshot_id: str,
        rolled_back_by: str,
        *,
        expected_lock_version: int,
    ) -> tuple[str, MaterializationPublicationModel]:
        publication = await self.get_active_publication(tenant_id, definition_id)
        target = await self.get_snapshot_by_id(tenant_id, to_snapshot_id)
        if publication is None or target is None or target.definition_id != definition_id:
            raise ValueError("rollback target is not available for this tenant and definition")
        if target.certification_status != "VALID":
            raise ValueError("rollback target certification is not valid")
        if publication.lock_version != expected_lock_version:
            raise RuntimeError("materialization rollback CAS conflict")
        from_snapshot = publication.active_snapshot_id
        publication.previous_snapshot_id = from_snapshot
        publication.active_snapshot_id = to_snapshot_id
        publication.definition_version = target.definition_version
        publication.published_by = uuid.UUID(rolled_back_by)
        publication.published_at = utc_now()
        publication.lock_version += 1
        self.session.add(
            MaterializationEventModel(
                tenant_id=trusted_tenant_uuid(tenant_id),
                definition_id=definition_id,
                event_type="ROLLED_BACK",
                user_id=uuid.UUID(rolled_back_by),
                details_json={"from_snapshot_id": from_snapshot, "to_snapshot_id": to_snapshot_id},
            )
        )
        await self.session.commit()
        return from_snapshot, publication

    async def garbage_collect_retained_artifacts(
        self,
        tenant_id: str,
        *,
        dry_run: bool = True,
        limit: int = 100,
        failed_build_retention_days: int = 30,
    ) -> tuple[int, int]:
        """Remove only bounded, non-published artifacts for one trusted tenant."""
        if limit < 1 or limit > 1000:
            raise ValueError("materialization GC limit must be between 1 and 1000")
        if failed_build_retention_days < 1 or failed_build_retention_days > 3650:
            raise ValueError("materialization build retention must be bounded")
        tenant_uuid = trusted_tenant_uuid(tenant_id)
        protected_snapshots = select(MaterializationPublicationModel.active_snapshot_id).where(
            MaterializationPublicationModel.tenant_id == tenant_uuid
        ).union(
            select(MaterializationPublicationModel.previous_snapshot_id).where(
                MaterializationPublicationModel.tenant_id == tenant_uuid,
                MaterializationPublicationModel.previous_snapshot_id.is_not(None),
            )
        )
        snapshots_result = await self.session.execute(
            select(MaterializationSnapshotModel)
            .where(
                MaterializationSnapshotModel.tenant_id == tenant_uuid,
                MaterializationSnapshotModel.expires_at.is_not(None),
                MaterializationSnapshotModel.expires_at < utc_now(),
                MaterializationSnapshotModel.snapshot_id.not_in(protected_snapshots),
            )
            .order_by(MaterializationSnapshotModel.id)
            .limit(limit)
        )
        snapshots = list(snapshots_result.scalars())
        remaining = limit - len(snapshots)
        builds: list[MaterializationBuildModel] = []
        if remaining:
            cutoff = utc_now() - timedelta(days=failed_build_retention_days)
            builds_result = await self.session.execute(
                select(MaterializationBuildModel)
                .where(
                    MaterializationBuildModel.tenant_id == tenant_uuid,
                    MaterializationBuildModel.status.in_(["FAILED", "CANCELLED"]),
                    MaterializationBuildModel.completed_at.is_not(None),
                    MaterializationBuildModel.completed_at < cutoff,
                )
                .order_by(MaterializationBuildModel.id)
                .limit(remaining)
            )
            builds = list(builds_result.scalars())
        count = len(snapshots) + len(builds)
        bytes_freed = sum(snapshot.payload_size_bytes for snapshot in snapshots)
        if not dry_run and count:
            if snapshots:
                await self.session.execute(
                    delete(MaterializationSnapshotModel).where(
                        MaterializationSnapshotModel.tenant_id == tenant_uuid,
                        MaterializationSnapshotModel.id.in_([item.id for item in snapshots]),
                    )
                )
            if builds:
                await self.session.execute(
                    delete(MaterializationBuildModel).where(
                        MaterializationBuildModel.tenant_id == tenant_uuid,
                        MaterializationBuildModel.id.in_([item.id for item in builds]),
                    )
                )
            await self.session.commit()
        return count, bytes_freed

    async def statistics(self, tenant_id: str) -> dict[str, int]:
        tenant_uuid = trusted_tenant_uuid(tenant_id)
        total = await self.session.scalar(
            select(func.count(MaterializationDefinitionModel.id)).where(
                MaterializationDefinitionModel.tenant_id == tenant_uuid
            )
        )
        published = await self.session.scalar(
            select(func.count(MaterializationPublicationModel.id)).where(
                MaterializationPublicationModel.tenant_id == tenant_uuid
            )
        )
        stale = await self.session.scalar(
            select(func.count(MaterializationSnapshotModel.id)).where(
                MaterializationSnapshotModel.tenant_id == tenant_uuid,
                MaterializationSnapshotModel.freshness.in_(["STALE_SOFT", "STALE_HARD"]),
            )
        )
        build_rows = await self.session.execute(
            select(MaterializationBuildModel.status, func.count(MaterializationBuildModel.id))
            .where(MaterializationBuildModel.tenant_id == tenant_uuid)
            .group_by(MaterializationBuildModel.status)
        )
        builds = {str(name): int(count) for name, count in build_rows.all()}
        return {
            "total_definitions": int(total or 0),
            "published_definitions": int(published or 0),
            "stale_snapshots": int(stale or 0),
            "total_builds": sum(builds.values()),
            "successful_builds": builds.get("READY", 0),
            "failed_builds": builds.get("FAILED", 0),
        }
