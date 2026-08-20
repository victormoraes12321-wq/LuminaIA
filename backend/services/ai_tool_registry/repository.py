from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update, delete
from database import get_db_context
from models.ai_tool_registry import (
    AIToolCircuitStateRecord,
    AIToolDependency,
    AIToolEvaluationCaseRecord,
    AIToolEvaluationResultRecord,
    AIToolEvent,
    AIToolIdentity,
    AIToolInvocationRecord,
    AIToolPublication,
    AIToolRegistryMember,
    AIToolRegistrySnapshot,
    AIToolReview,
    AIToolVersion,
)


class AIToolRegistryRepository:
    """
    Repository for PostgreSQL persistence of AI tool identities, versions, snapshots, and audit events.
    """

    def compute_hash(self, data: Dict[str, Any]) -> str:
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    async def get_tool_identity_by_id(self, tenant_id: str | uuid.UUID, tool_id: str) -> Optional[AIToolIdentity]:
        async with get_db_context() as session:
            stmt = select(AIToolIdentity).where(
                AIToolIdentity.tool_id == tool_id,
                AIToolIdentity.tenant_id.in_([str(tenant_id), "system"]),
            )
            res = await session.execute(stmt)
            return res.scalars().first()

    async def get_tool_identity_by_canonical_name(self, tenant_id: str | uuid.UUID, canonical_name: str) -> Optional[AIToolIdentity]:
        async with get_db_context() as session:
            stmt = select(AIToolIdentity).where(
                AIToolIdentity.canonical_name == canonical_name,
                AIToolIdentity.tenant_id.in_([str(tenant_id), "system"]),
            )
            res = await session.execute(stmt)
            return res.scalars().first()

    async def create_tool_identity(
        self,
        tool_id: str,
        canonical_name: str,
        display_name: str,
        description: str,
        capabilities: List[str],
        domain: str = "business_intelligence",
        tool_type: str = "DOMAIN_READ",
        risk_class: str = "LOW",
        side_effect: str = "READ_ONLY",
        network_class: str = "INTERNAL_SERVICE_ONLY",
        data_class: str = "TENANT_BUSINESS_DATA",
        owner_id: str | uuid.UUID = "system",
        tenant_id: str | uuid.UUID = "system",
        scope: str = "SYSTEM",
    ) -> AIToolIdentity:
        checksum_payload = {
            "tool_id": tool_id,
            "canonical_name": canonical_name,
            "tenant_id": str(tenant_id),
            "capabilities": sorted(capabilities),
        }
        checksum = self.compute_hash(checksum_payload)
        identity = AIToolIdentity(
            id=uuid.uuid4(),
            tool_id=tool_id,
            canonical_name=canonical_name,
            display_name=display_name,
            description=description,
            domain=domain,
            tool_type=tool_type,
            capabilities=capabilities,
            risk_class=risk_class,
            side_effect=side_effect,
            network_class=network_class,
            data_class=data_class,
            owner_id=str(owner_id),
            tenant_id=str(tenant_id),
            scope=scope,
            checksum=checksum,
        )
        async with get_db_context() as session:
            session.add(identity)
            await session.commit()
            await session.refresh(identity)
            return identity

    async def list_tool_identities(self, tenant_id: str | uuid.UUID) -> List[AIToolIdentity]:
        async with get_db_context() as session:
            stmt = select(AIToolIdentity).where(
                AIToolIdentity.tenant_id.in_([str(tenant_id), "system"])
            )
            res = await session.execute(stmt)
            return list(res.scalars().all())

    async def create_tool_version(
        self,
        tool_identity_id: uuid.UUID,
        tool_id: str,
        version: str,
        adapter_id: str,
        input_contract: Dict[str, Any],
        output_contract: Dict[str, Any],
        execution_policy: Dict[str, Any],
        author_id: str | uuid.UUID,
        tenant_id: str | uuid.UUID = "system",
        dependencies: Optional[List[Dict[str, Any]]] = None,
        lifecycle: str = "DRAFT",
    ) -> AIToolVersion:
        checksum_payload = {
            "tool_id": tool_id,
            "version": version,
            "adapter_id": adapter_id,
            "input_contract": input_contract,
            "output_contract": output_contract,
            "execution_policy": execution_policy,
        }
        checksum = self.compute_hash(checksum_payload)
        tool_ver = AIToolVersion(
            id=uuid.uuid4(),
            tool_identity_id=tool_identity_id,
            tool_id=tool_id,
            version=version,
            adapter_id=adapter_id,
            input_contract=input_contract,
            output_contract=output_contract,
            execution_policy=execution_policy,
            dependencies=dependencies or [],
            lifecycle=lifecycle,
            author_id=str(author_id),
            tenant_id=str(tenant_id),
            lock_version=1,
            checksum=checksum,
        )
        async with get_db_context() as session:
            session.add(tool_ver)
            await session.commit()
            await session.refresh(tool_ver)
            return tool_ver

    async def get_tool_version(self, tool_id: str, version: str, tenant_id: str | uuid.UUID) -> Optional[AIToolVersion]:
        async with get_db_context() as session:
            stmt = select(AIToolVersion).where(
                AIToolVersion.tool_id == tool_id,
                AIToolVersion.version == version,
                AIToolVersion.tenant_id.in_([str(tenant_id), "system"]),
            )
            res = await session.execute(stmt)
            return res.scalars().first()

    async def list_tool_versions(self, tool_id: str, tenant_id: str | uuid.UUID) -> List[AIToolVersion]:
        async with get_db_context() as session:
            stmt = select(AIToolVersion).where(
                AIToolVersion.tool_id == tool_id,
                AIToolVersion.tenant_id.in_([str(tenant_id), "system"]),
            ).order_by(AIToolVersion.created_at.desc())
            res = await session.execute(stmt)
            return list(res.scalars().all())

    async def update_tool_version_lifecycle(
        self, version_id: uuid.UUID, expected_lock_version: int, new_lifecycle: str, reviewer_or_publisher_id: Optional[str] = None
    ) -> bool:
        async with get_db_context() as session:
            values: Dict[str, Any] = {
                "lifecycle": new_lifecycle,
                "lock_version": AIToolVersion.lock_version + 1,
            }
            if new_lifecycle == "APPROVED":
                values["reviewer_id"] = reviewer_or_publisher_id
            elif new_lifecycle == "ACTIVE":
                values["published_by"] = reviewer_or_publisher_id
                values["effective_from"] = datetime.now(timezone.utc)

            stmt = (
                update(AIToolVersion)
                .where(
                    AIToolVersion.id == version_id,
                    AIToolVersion.lock_version == expected_lock_version,
                )
                .values(**values)
            )
            res = await session.execute(stmt)
            await session.commit()
            return res.rowcount == 1

    async def add_review(
        self, tool_version_id: uuid.UUID, reviewer_id: str, tenant_id: str, approved: bool, review_notes: str = ""
    ) -> AIToolReview:
        review = AIToolReview(
            id=uuid.uuid4(),
            tool_version_id=tool_version_id,
            reviewer_id=reviewer_id,
            tenant_id=tenant_id,
            approved=approved,
            review_notes=review_notes,
        )
        async with get_db_context() as session:
            session.add(review)
            await session.commit()
            await session.refresh(review)
            return review

    async def create_snapshot(
        self,
        snapshot_id: str,
        version: str,
        active_tool_versions: Dict[str, str],
        created_by: str,
        disabled_tool_ids: Optional[List[str]] = None,
        previous_snapshot_id: Optional[str] = None,
    ) -> AIToolRegistrySnapshot:
        dep_checksum = self.compute_hash(active_tool_versions)
        checksum_payload = {
            "snapshot_id": snapshot_id,
            "version": version,
            "active_tool_versions": active_tool_versions,
            "disabled_tool_ids": disabled_tool_ids or [],
        }
        checksum = self.compute_hash(checksum_payload)
        snapshot = AIToolRegistrySnapshot(
            id=uuid.uuid4(),
            snapshot_id=snapshot_id,
            version=version,
            status="PUBLISHED",
            active_tool_versions=active_tool_versions,
            disabled_tool_ids=disabled_tool_ids or [],
            dependency_graph_checksum=dep_checksum,
            created_by=created_by,
            published_by=created_by,
            previous_snapshot_id=previous_snapshot_id,
            checksum=checksum,
            published_at=datetime.now(timezone.utc),
        )
        async with get_db_context() as session:
            session.add(snapshot)
            await session.commit()
            await session.refresh(snapshot)
            return snapshot

    async def get_active_snapshot(self) -> Optional[AIToolRegistrySnapshot]:
        async with get_db_context() as session:
            stmt = (
                select(AIToolRegistrySnapshot)
                .where(AIToolRegistrySnapshot.status == "PUBLISHED")
                .order_by(AIToolRegistrySnapshot.published_at.desc())
            )
            res = await session.execute(stmt)
            return res.scalars().first()

    async def get_snapshot_by_id(self, snapshot_id: str) -> Optional[AIToolRegistrySnapshot]:
        async with get_db_context() as session:
            stmt = select(AIToolRegistrySnapshot).where(AIToolRegistrySnapshot.snapshot_id == snapshot_id)
            res = await session.execute(stmt)
            return res.scalars().first()

    async def list_snapshots(self) -> List[AIToolRegistrySnapshot]:
        async with get_db_context() as session:
            stmt = select(AIToolRegistrySnapshot).order_by(AIToolRegistrySnapshot.created_at.desc())
            res = await session.execute(stmt)
            return list(res.scalars().all())

    async def log_event(
        self, tenant_id: str, user_id: str, event_type: str, tool_id: str, version: Optional[str] = None, payload: Optional[Dict[str, Any]] = None
    ) -> AIToolEvent:
        event = AIToolEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            tool_id=tool_id,
            version=version,
            payload=payload or {},
        )
        async with get_db_context() as session:
            session.add(event)
            await session.commit()
            await session.refresh(event)
            return event

    async def log_invocation_record(
        self,
        request_id: str,
        tenant_id: str,
        user_id: str,
        tool_id: str,
        version: str,
        snapshot_id: str,
        duration_ms: float,
        status: str,
        input_checksum: str,
        output_checksum: str,
        error_code: Optional[str] = None,
        cache_hit: bool = False,
        circuit_state: str = "CLOSED",
    ) -> AIToolInvocationRecord:
        record = AIToolInvocationRecord(
            id=uuid.uuid4(),
            request_id=request_id,
            tenant_id=tenant_id,
            user_id=user_id,
            tool_id=tool_id,
            version=version,
            snapshot_id=snapshot_id,
            duration_ms=duration_ms,
            status=status,
            error_code=error_code,
            input_checksum=input_checksum,
            output_checksum=output_checksum,
            cache_hit=cache_hit,
            circuit_state=circuit_state,
        )
        async with get_db_context() as session:
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return record


ai_tool_registry_repository = AIToolRegistryRepository()
