from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.enterprise_knowledge import (
    EnterpriseKnowledgeAlias,
    EnterpriseKnowledgeApproval,
    EnterpriseKnowledgeAsset,
    EnterpriseKnowledgeEvent,
    EnterpriseKnowledgeImport,
    EnterpriseKnowledgePublication,
    EnterpriseKnowledgeRelation,
    EnterpriseKnowledgeVersion,
)


class EnterpriseKnowledgeRepository:
    """Persistence primitives with mandatory tenant scope and external transactions."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_asset(self, row: EnterpriseKnowledgeAsset) -> EnterpriseKnowledgeAsset:
        self.db.add(row)
        await self.db.flush()
        return row

    async def get_asset(
        self,
        *,
        tenant_id: uuid.UUID,
        asset_id: uuid.UUID,
        for_update: bool = False,
    ) -> EnterpriseKnowledgeAsset | None:
        stmt = select(EnterpriseKnowledgeAsset).where(
            EnterpriseKnowledgeAsset.tenant_id == tenant_id,
            EnterpriseKnowledgeAsset.id == asset_id,
            EnterpriseKnowledgeAsset.status != "DELETED",
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_asset_by_key(
        self,
        *,
        tenant_id: uuid.UUID,
        asset_type: str,
        canonical_key: str,
    ) -> EnterpriseKnowledgeAsset | None:
        stmt = select(EnterpriseKnowledgeAsset).where(
            EnterpriseKnowledgeAsset.tenant_id == tenant_id,
            EnterpriseKnowledgeAsset.asset_type == asset_type,
            EnterpriseKnowledgeAsset.canonical_key == canonical_key,
            EnterpriseKnowledgeAsset.status != "DELETED",
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def find_assets_by_canonical_key(
        self,
        *,
        tenant_id: uuid.UUID,
        canonical_key: str,
    ) -> list[EnterpriseKnowledgeAsset]:
        stmt = select(EnterpriseKnowledgeAsset).where(
            EnterpriseKnowledgeAsset.tenant_id == tenant_id,
            EnterpriseKnowledgeAsset.canonical_key == canonical_key,
            EnterpriseKnowledgeAsset.status == "ACTIVE",
        )
        return list((await self.db.execute(stmt)).scalars())

    async def list_assets(
        self,
        *,
        tenant_id: uuid.UUID,
        limit: int,
        lifecycle: str | None = None,
        asset_type: str | None = None,
        domain: str | None = None,
        cursor_updated_at: datetime | None = None,
        cursor_id: uuid.UUID | None = None,
        published_only: bool = False,
    ) -> list[tuple[EnterpriseKnowledgeAsset, EnterpriseKnowledgeVersion | None]]:
        stmt = (
            select(EnterpriseKnowledgeAsset, EnterpriseKnowledgeVersion)
            .outerjoin(
                EnterpriseKnowledgeVersion,
                and_(
                    EnterpriseKnowledgeVersion.asset_id == EnterpriseKnowledgeAsset.id,
                    EnterpriseKnowledgeVersion.tenant_id == EnterpriseKnowledgeAsset.tenant_id,
                    (
                        EnterpriseKnowledgeVersion.id
                        == EnterpriseKnowledgeAsset.current_published_version_id
                    ),
                ),
            )
            .where(
                EnterpriseKnowledgeAsset.tenant_id == tenant_id,
                EnterpriseKnowledgeAsset.status != "DELETED",
            )
        )
        if lifecycle is not None:
            version_ids = select(EnterpriseKnowledgeVersion.asset_id).where(
                EnterpriseKnowledgeVersion.tenant_id == tenant_id,
                EnterpriseKnowledgeVersion.lifecycle == lifecycle,
            )
            stmt = stmt.where(EnterpriseKnowledgeAsset.id.in_(version_ids))
        if asset_type is not None:
            stmt = stmt.where(EnterpriseKnowledgeAsset.asset_type == asset_type)
        if domain is not None:
            stmt = stmt.where(EnterpriseKnowledgeAsset.domain == domain)
        if published_only:
            stmt = stmt.where(EnterpriseKnowledgeAsset.current_published_version_id.is_not(None))
        if cursor_updated_at is not None and cursor_id is not None:
            stmt = stmt.where(
                or_(
                    EnterpriseKnowledgeAsset.updated_at < cursor_updated_at,
                    and_(
                        EnterpriseKnowledgeAsset.updated_at == cursor_updated_at,
                        EnterpriseKnowledgeAsset.id < cursor_id,
                    ),
                )
            )
        stmt = stmt.order_by(
            EnterpriseKnowledgeAsset.updated_at.desc(),
            EnterpriseKnowledgeAsset.id.desc(),
        ).limit(limit)
        return list((await self.db.execute(stmt)).tuples())

    async def create_version(
        self,
        row: EnterpriseKnowledgeVersion,
    ) -> EnterpriseKnowledgeVersion:
        self.db.add(row)
        await self.db.flush()
        return row

    async def next_version_number(
        self,
        *,
        tenant_id: uuid.UUID,
        asset_id: uuid.UUID,
    ) -> int:
        value = await self.db.scalar(
            select(func.coalesce(func.max(EnterpriseKnowledgeVersion.version_number), 0)).where(
                EnterpriseKnowledgeVersion.tenant_id == tenant_id,
                EnterpriseKnowledgeVersion.asset_id == asset_id,
            )
        )
        return int(value or 0) + 1

    async def get_version(
        self,
        *,
        tenant_id: uuid.UUID,
        asset_id: uuid.UUID,
        version_id: uuid.UUID,
        for_update: bool = False,
    ) -> EnterpriseKnowledgeVersion | None:
        stmt = select(EnterpriseKnowledgeVersion).where(
            EnterpriseKnowledgeVersion.tenant_id == tenant_id,
            EnterpriseKnowledgeVersion.asset_id == asset_id,
            EnterpriseKnowledgeVersion.id == version_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_versions(
        self,
        *,
        tenant_id: uuid.UUID,
        asset_id: uuid.UUID,
        include_private: bool,
        limit: int = 100,
    ) -> list[EnterpriseKnowledgeVersion]:
        stmt = select(EnterpriseKnowledgeVersion).where(
            EnterpriseKnowledgeVersion.tenant_id == tenant_id,
            EnterpriseKnowledgeVersion.asset_id == asset_id,
        )
        if not include_private:
            stmt = stmt.where(
                EnterpriseKnowledgeVersion.lifecycle.in_(("PUBLISHED", "DEPRECATED"))
            )
        stmt = stmt.order_by(EnterpriseKnowledgeVersion.version_number.desc()).limit(limit)
        return list((await self.db.execute(stmt)).scalars())

    async def update_draft_cas(
        self,
        *,
        tenant_id: uuid.UUID,
        asset_id: uuid.UUID,
        version_id: uuid.UUID,
        expected_lock_version: int,
        content: dict[str, object],
        checksum: str,
        effective_from: datetime | None,
        effective_to: datetime | None,
        updated_at: datetime,
    ) -> bool:
        result = await self.db.execute(
            update(EnterpriseKnowledgeVersion)
            .where(
                EnterpriseKnowledgeVersion.tenant_id == tenant_id,
                EnterpriseKnowledgeVersion.asset_id == asset_id,
                EnterpriseKnowledgeVersion.id == version_id,
                EnterpriseKnowledgeVersion.lifecycle == "DRAFT",
                EnterpriseKnowledgeVersion.lock_version == expected_lock_version,
            )
            .values(
                content=content,
                checksum=checksum,
                effective_from=effective_from,
                effective_to=effective_to,
                lock_version=EnterpriseKnowledgeVersion.lock_version + 1,
                updated_at=updated_at,
            )
        )
        return result.rowcount == 1

    async def get_approval(
        self,
        *,
        tenant_id: uuid.UUID,
        asset_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> EnterpriseKnowledgeApproval | None:
        stmt = (
            select(EnterpriseKnowledgeApproval)
            .where(
                EnterpriseKnowledgeApproval.tenant_id == tenant_id,
                EnterpriseKnowledgeApproval.asset_id == asset_id,
                EnterpriseKnowledgeApproval.version_id == version_id,
                EnterpriseKnowledgeApproval.decision == "APPROVED",
            )
            .order_by(EnterpriseKnowledgeApproval.created_at.desc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def add_approval(
        self,
        row: EnterpriseKnowledgeApproval,
    ) -> EnterpriseKnowledgeApproval:
        self.db.add(row)
        await self.db.flush()
        return row

    async def add_publication(
        self,
        row: EnterpriseKnowledgePublication,
    ) -> EnterpriseKnowledgePublication:
        self.db.add(row)
        await self.db.flush()
        return row

    async def replace_published_aliases(
        self,
        *,
        tenant_id: uuid.UUID,
        asset_id: uuid.UUID,
        version_id: uuid.UUID,
        aliases: list[tuple[str, str, str]],
    ) -> None:
        for alias, normalized_alias, locale in aliases:
            self.db.add(
                EnterpriseKnowledgeAlias(
                    tenant_id=tenant_id,
                    asset_id=asset_id,
                    version_id=version_id,
                    alias=alias,
                    normalized_alias=normalized_alias,
                    locale=locale,
                )
            )
        await self.db.flush()

    async def list_effective_published(
        self,
        *,
        tenant_id: uuid.UUID,
        at: datetime,
        asset_types: tuple[str, ...] = (),
        domains: tuple[str, ...] = (),
    ) -> list[tuple[EnterpriseKnowledgeAsset, EnterpriseKnowledgeVersion]]:
        stmt = (
            select(EnterpriseKnowledgeAsset, EnterpriseKnowledgeVersion)
            .join(
                EnterpriseKnowledgeVersion,
                and_(
                    EnterpriseKnowledgeVersion.tenant_id == EnterpriseKnowledgeAsset.tenant_id,
                    EnterpriseKnowledgeVersion.asset_id == EnterpriseKnowledgeAsset.id,
                    EnterpriseKnowledgeVersion.id
                    == EnterpriseKnowledgeAsset.current_published_version_id,
                ),
            )
            .where(
                EnterpriseKnowledgeAsset.tenant_id == tenant_id,
                EnterpriseKnowledgeAsset.status == "ACTIVE",
                EnterpriseKnowledgeVersion.lifecycle == "PUBLISHED",
                or_(
                    EnterpriseKnowledgeVersion.effective_from.is_(None),
                    EnterpriseKnowledgeVersion.effective_from <= at,
                ),
                or_(
                    EnterpriseKnowledgeVersion.effective_to.is_(None),
                    EnterpriseKnowledgeVersion.effective_to > at,
                ),
            )
        )
        if asset_types:
            stmt = stmt.where(EnterpriseKnowledgeAsset.asset_type.in_(asset_types))
        if domains:
            stmt = stmt.where(EnterpriseKnowledgeAsset.domain.in_(domains))
        stmt = stmt.order_by(EnterpriseKnowledgeAsset.canonical_key, EnterpriseKnowledgeAsset.id)
        return list((await self.db.execute(stmt)).tuples())

    async def aliases_for_versions(
        self,
        *,
        tenant_id: uuid.UUID,
        version_ids: tuple[uuid.UUID, ...],
        locale: str,
    ) -> dict[uuid.UUID, list[EnterpriseKnowledgeAlias]]:
        if not version_ids:
            return {}
        stmt = select(EnterpriseKnowledgeAlias).where(
            EnterpriseKnowledgeAlias.tenant_id == tenant_id,
            EnterpriseKnowledgeAlias.version_id.in_(version_ids),
            EnterpriseKnowledgeAlias.locale == locale,
        )
        grouped: dict[uuid.UUID, list[EnterpriseKnowledgeAlias]] = {}
        for row in (await self.db.execute(stmt)).scalars():
            grouped.setdefault(row.version_id, []).append(row)
        return grouped

    async def add_relation(
        self,
        row: EnterpriseKnowledgeRelation,
    ) -> EnterpriseKnowledgeRelation:
        self.db.add(row)
        await self.db.flush()
        return row

    async def add_event(self, row: EnterpriseKnowledgeEvent) -> EnterpriseKnowledgeEvent:
        self.db.add(row)
        await self.db.flush()
        return row

    async def list_events(
        self,
        *,
        tenant_id: uuid.UUID,
        asset_id: uuid.UUID,
        limit: int = 200,
    ) -> list[EnterpriseKnowledgeEvent]:
        stmt = (
            select(EnterpriseKnowledgeEvent)
            .where(
                EnterpriseKnowledgeEvent.tenant_id == tenant_id,
                EnterpriseKnowledgeEvent.asset_id == asset_id,
            )
            .order_by(EnterpriseKnowledgeEvent.created_at.desc(), EnterpriseKnowledgeEvent.id.desc())
            .limit(limit)
        )
        return list((await self.db.execute(stmt)).scalars())

    async def get_import(
        self,
        *,
        tenant_id: uuid.UUID,
        idempotency_key_hash: str,
    ) -> EnterpriseKnowledgeImport | None:
        stmt = select(EnterpriseKnowledgeImport).where(
            EnterpriseKnowledgeImport.tenant_id == tenant_id,
            EnterpriseKnowledgeImport.idempotency_key_hash == idempotency_key_hash,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_import_by_checksum(
        self,
        *,
        tenant_id: uuid.UUID,
        source_checksum: str,
        dry_run: bool,
    ) -> EnterpriseKnowledgeImport | None:
        stmt = select(EnterpriseKnowledgeImport).where(
            EnterpriseKnowledgeImport.tenant_id == tenant_id,
            EnterpriseKnowledgeImport.source_checksum == source_checksum,
            EnterpriseKnowledgeImport.dry_run == dry_run,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def add_import(
        self,
        row: EnterpriseKnowledgeImport,
    ) -> EnterpriseKnowledgeImport:
        self.db.add(row)
        await self.db.flush()
        return row
