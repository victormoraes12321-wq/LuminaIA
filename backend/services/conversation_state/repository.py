from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from contracts.conversation_state_v2 import (
    CONVERSATION_STATE_VERSION,
    ConversationEventType,
    ConversationStateV2,
    compute_state_checksum,
)
from models.conversation_state import (
    ConversationEvent,
    ConversationNodeRecord,
    ConversationSession,
    ConversationStateSnapshot,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ConversationStateRepository:
    """Tenant and user scoped persistence primitives. Transaction ownership is external."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def owner_predicate(tenant_id: uuid.UUID, user_id: uuid.UUID):
        return and_(
            ConversationSession.tenant_id == tenant_id,
            ConversationSession.user_id == user_id,
        )

    async def create_session(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        public_session_id: str,
        expires_at: datetime,
    ) -> ConversationSession:
        row = ConversationSession(
            tenant_id=tenant_id,
            user_id=user_id,
            public_session_id=public_session_id,
            expires_at=expires_at,
            schema_version=CONVERSATION_STATE_VERSION,
        )
        self.db.add(row)
        await self.db.flush()
        await self.record_event(
            row=row,
            event_type=ConversationEventType.SESSION_CREATED,
        )
        return row

    async def get_session(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        public_session_id: str,
        for_update: bool = False,
    ) -> ConversationSession | None:
        stmt = select(ConversationSession).where(
            self.owner_predicate(tenant_id, user_id),
            ConversationSession.public_session_id == public_session_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_session_by_id(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        for_update: bool = False,
    ) -> ConversationSession | None:
        stmt = select(ConversationSession).where(
            self.owner_predicate(tenant_id, user_id),
            ConversationSession.id == session_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_sessions(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int,
        cursor_activity: datetime | None = None,
        cursor_id: uuid.UUID | None = None,
    ) -> list[ConversationSession]:
        stmt = select(ConversationSession).where(
            self.owner_predicate(tenant_id, user_id),
            ConversationSession.status != "DELETED",
        )
        if cursor_activity is not None and cursor_id is not None:
            stmt = stmt.where(
                or_(
                    ConversationSession.last_activity_at < cursor_activity,
                    and_(
                        ConversationSession.last_activity_at == cursor_activity,
                        ConversationSession.id < cursor_id,
                    ),
                )
            )
        stmt = stmt.order_by(
            ConversationSession.last_activity_at.desc(),
            ConversationSession.id.desc(),
        ).limit(limit)
        return list((await self.db.execute(stmt)).scalars())

    async def get_node(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        node_id: uuid.UUID,
    ) -> ConversationNodeRecord | None:
        stmt = select(ConversationNodeRecord).where(
            ConversationNodeRecord.tenant_id == tenant_id,
            ConversationNodeRecord.user_id == user_id,
            ConversationNodeRecord.session_id == session_id,
            ConversationNodeRecord.id == node_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def find_by_client_message(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        client_message_id: uuid.UUID,
    ) -> ConversationNodeRecord | None:
        stmt = select(ConversationNodeRecord).where(
            ConversationNodeRecord.tenant_id == tenant_id,
            ConversationNodeRecord.user_id == user_id,
            ConversationNodeRecord.session_id == session_id,
            ConversationNodeRecord.client_message_id == client_message_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_response_for_query(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        query_node_id: uuid.UUID,
    ) -> ConversationNodeRecord | None:
        stmt = (
            select(ConversationNodeRecord)
            .where(
                ConversationNodeRecord.tenant_id == tenant_id,
                ConversationNodeRecord.user_id == user_id,
                ConversationNodeRecord.session_id == session_id,
                ConversationNodeRecord.parent_node_id == query_node_id,
                ConversationNodeRecord.role == "assistant",
            )
            .order_by(ConversationNodeRecord.sequence_number.desc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def append_node(
        self,
        *,
        row: ConversationSession,
        parent_node_id: uuid.UUID | None,
        role: str,
        node_type: str,
        status: str,
        base_context_version: int,
        content_ciphertext: bytes | None,
        content_key_version: str | None,
        content_fingerprint: str,
        client_message_id: uuid.UUID | None = None,
        search_history_id: uuid.UUID | None = None,
        plan_fingerprint: str | None = None,
        response_fingerprint: str | None = None,
        flush: bool = True,
    ) -> ConversationNodeRecord:
        created_at = utc_now()
        node_id = uuid.uuid4()
        node = ConversationNodeRecord(
            id=node_id,
            session_id=row.id,
            tenant_id=row.tenant_id,
            user_id=row.user_id,
            sequence_number=row.next_sequence,
            parent_node_id=parent_node_id,
            role=role,
            node_type=node_type,
            status=status,
            client_message_id=client_message_id,
            idempotency_key_hash=(
                hashlib.sha256(f"{row.id}:{client_message_id}".encode()).hexdigest()
                if client_message_id else None
            ),
            content_ciphertext=content_ciphertext,
            content_key_version=content_key_version,
            content_fingerprint=content_fingerprint,
            search_history_id=search_history_id,
            plan_fingerprint=plan_fingerprint,
            response_fingerprint=response_fingerprint,
            base_context_version=base_context_version,
            created_at=created_at,
            completed_at=created_at if status == "COMPLETED" else None,
            failed_at=created_at if status == "FAILED" else None,
        )
        row.next_sequence += 1
        row.lock_version += 1
        row.updated_at = utc_now()
        self.db.add(node)
        if flush:
            await self.db.flush()
        return node

    async def load_snapshot(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> ConversationStateSnapshot | None:
        stmt = (
            select(ConversationStateSnapshot)
            .where(
                ConversationStateSnapshot.tenant_id == tenant_id,
                ConversationStateSnapshot.user_id == user_id,
                ConversationStateSnapshot.session_id == session_id,
            )
            .order_by(
                ConversationStateSnapshot.context_epoch.desc(),
                ConversationStateSnapshot.context_version.desc(),
            )
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def load_snapshot_for_head(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        head_node_id: uuid.UUID,
    ) -> ConversationStateSnapshot | None:
        stmt = (
            select(ConversationStateSnapshot)
            .where(
                ConversationStateSnapshot.tenant_id == tenant_id,
                ConversationStateSnapshot.user_id == user_id,
                ConversationStateSnapshot.session_id == session_id,
                ConversationStateSnapshot.head_node_id == head_node_id,
            )
            .order_by(
                ConversationStateSnapshot.context_epoch.desc(),
                ConversationStateSnapshot.context_version.desc(),
            )
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def create_snapshot(
        self,
        *,
        row: ConversationSession,
        head_node_id: uuid.UUID | None,
        state: ConversationStateV2,
    ) -> ConversationStateSnapshot:
        snapshot = ConversationStateSnapshot(
            session_id=row.id,
            tenant_id=row.tenant_id,
            user_id=row.user_id,
            context_epoch=state.context_epoch,
            context_version=state.context_version,
            head_node_id=head_node_id,
            schema_version=CONVERSATION_STATE_VERSION,
            state_json=state.model_dump(mode="json"),
            state_checksum=compute_state_checksum(state),
        )
        self.db.add(snapshot)
        await self.db.flush()
        return snapshot

    async def list_nodes(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        after_sequence: int | None,
        limit: int,
    ) -> list[ConversationNodeRecord]:
        stmt = select(ConversationNodeRecord).where(
            ConversationNodeRecord.tenant_id == tenant_id,
            ConversationNodeRecord.user_id == user_id,
            ConversationNodeRecord.session_id == session_id,
        )
        if after_sequence is not None:
            stmt = stmt.where(ConversationNodeRecord.sequence_number > after_sequence)
        stmt = stmt.order_by(ConversationNodeRecord.sequence_number).limit(limit)
        return list((await self.db.execute(stmt)).scalars())

    async def compare_and_swap(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        expected_context_version: int,
        expected_context_epoch: int,
        new_context_version: int,
        new_context_epoch: int,
        head_node_id: uuid.UUID,
        expires_at: datetime,
    ) -> bool:
        stmt = (
            update(ConversationSession)
            .where(
                ConversationSession.id == session_id,
                ConversationSession.tenant_id == tenant_id,
                ConversationSession.user_id == user_id,
                ConversationSession.status == "ACTIVE",
                ConversationSession.context_epoch == expected_context_epoch,
                ConversationSession.context_version == expected_context_version,
            )
            .values(
                context_epoch=new_context_epoch,
                context_version=new_context_version,
                active_head_node_id=head_node_id,
                last_activity_at=utc_now(),
                updated_at=utc_now(),
                expires_at=expires_at,
                lock_version=ConversationSession.lock_version + 1,
            )
        )
        return (await self.db.execute(stmt)).rowcount == 1

    async def record_event(
        self,
        *,
        row: ConversationSession,
        event_type: ConversationEventType,
        node_id: uuid.UUID | None = None,
        fingerprint: str | None = None,
        metadata: dict | None = None,
    ) -> ConversationEvent:
        event = ConversationEvent(
            session_id=row.id,
            tenant_id=row.tenant_id,
            user_id=row.user_id,
            event_type=event_type.value,
            schema_version=CONVERSATION_STATE_VERSION,
            context_epoch=row.context_epoch,
            context_version=row.context_version,
            node_id=node_id,
            fingerprint=fingerprint,
            event_metadata=metadata or {},
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def mark_expired_batch(self, *, now: datetime, limit: int) -> int:
        ids = list((await self.db.execute(
            select(ConversationSession.id)
            .where(
                ConversationSession.status == "ACTIVE",
                ConversationSession.expires_at <= now,
            )
            .order_by(ConversationSession.expires_at, ConversationSession.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )).scalars())
        if not ids:
            return 0
        result = await self.db.execute(
            update(ConversationSession)
            .where(ConversationSession.id.in_(ids))
            .values(status="EXPIRED", updated_at=now, lock_version=ConversationSession.lock_version + 1)
        )
        return result.rowcount

    async def count_expired_candidates(self, *, now: datetime, limit: int) -> int:
        candidate_ids = (
            select(ConversationSession.id)
            .where(
                ConversationSession.status == "ACTIVE",
                ConversationSession.expires_at <= now,
            )
            .order_by(ConversationSession.expires_at, ConversationSession.id)
            .limit(limit)
            .subquery()
        )
        return int(await self.db.scalar(select(func.count()).select_from(candidate_ids)) or 0)

    async def purge_deleted_batch(
        self,
        *,
        cutoff: datetime,
        limit: int,
        dry_run: bool,
    ) -> list[uuid.UUID]:
        ids = list((await self.db.execute(
            select(ConversationSession.id)
            .where(
                ConversationSession.status == "DELETED",
                ConversationSession.deleted_at.is_not(None),
                ConversationSession.deleted_at <= cutoff,
            )
            .order_by(ConversationSession.deleted_at, ConversationSession.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )).scalars())
        if ids and not dry_run:
            await self.db.execute(delete(ConversationSession).where(ConversationSession.id.in_(ids)))
        return ids
