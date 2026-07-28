from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from config import settings
from contracts.conversation_state_v2 import (
    CONVERSATION_STATE_VERSION,
    ConversationEventType,
    ConversationRetentionPolicy,
    ConversationRolloutMode,
    ConversationStateV2,
    ConversationTurnCompletion,
    ConversationTurnFailure,
    ConversationTurnStart,
)
from database import AsyncSessionLocal
from models.conversation_state import ConversationNodeRecord, ConversationSession
from models.user import User
from services.conversation_state.content_protector import (
    ConversationContentError,
    ConversationContentProtector,
)
from services.conversation_state.repository import ConversationStateRepository


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ConversationStateError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 409,
        actual_context_version: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.actual_context_version = actual_context_version


@dataclass(frozen=True)
class StartedTurn:
    public_session_id: str
    session_id: uuid.UUID
    query_node_id: uuid.UUID
    parent_node_id: uuid.UUID | None
    base_context_version: int
    context_epoch: int
    idempotent_replay: bool = False
    response_node_id: uuid.UUID | None = None


@dataclass(frozen=True)
class CompletedTurn:
    public_session_id: str
    query_node_id: uuid.UUID
    response_node_id: uuid.UUID
    parent_node_id: uuid.UUID | None
    context_version: int
    context_epoch: int
    idempotent_replay: bool = False


class ConversationStateService:
    """Transactional conversation persistence. It never calls analytical systems or AI."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] = AsyncSessionLocal,
        *,
        protector: ConversationContentProtector | None = None,
        retention: ConversationRetentionPolicy | None = None,
        mode: ConversationRolloutMode | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.mode = mode or ConversationRolloutMode(settings.CONVERSATION_STATE_MODE)
        self.retention = retention or ConversationRetentionPolicy(
            active_ttl_hours=settings.CONVERSATION_ACTIVE_TTL_HOURS,
            archive_after_days=settings.CONVERSATION_ARCHIVE_AFTER_DAYS,
            soft_delete_after_days=settings.CONVERSATION_SOFT_DELETE_AFTER_DAYS,
            purge_after_days=settings.CONVERSATION_PURGE_AFTER_DAYS,
            max_content_bytes=settings.CONVERSATION_MAX_CONTENT_BYTES,
            max_nodes=settings.CONVERSATION_MAX_NODES,
            purge_batch_size=settings.CONVERSATION_PURGE_BATCH_SIZE,
        )
        self.protector = protector or ConversationContentProtector(
            key=settings.ENCRYPTION_KEY,
            key_version=settings.CONVERSATION_CONTENT_KEY_VERSION,
            persist_content=settings.CONVERSATION_PERSIST_CONTENT,
            max_content_bytes=self.retention.max_content_bytes,
        )

    @property
    def postgres_writes_enabled(self) -> bool:
        return self.mode != ConversationRolloutMode.LEGACY_ONLY

    @property
    def postgres_is_authority(self) -> bool:
        return self.mode in {
            ConversationRolloutMode.POSTGRES_READ_WRITE,
            ConversationRolloutMode.POSTGRES_ONLY,
        }

    @staticmethod
    def new_public_session_id() -> str:
        return f"lumina-{uuid.uuid4()}"

    def _expires_at(self) -> datetime:
        return utc_now() + timedelta(hours=self.retention.active_ttl_hours)

    async def resolve_or_create_session(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        public_session_id: str | None,
    ) -> ConversationSession:
        candidate = public_session_id or self.new_public_session_id()
        expired_version: int | None = None
        try:
            async with self.session_factory() as db, db.begin():
                repo = ConversationStateRepository(db)
                valid_identity = await db.scalar(
                    select(User.id).where(
                        User.id == user_id,
                        User.tenant_id == tenant_id,
                    )
                )
                if valid_identity is None:
                    raise ConversationStateError(
                        "INVALID_CONVERSATION_IDENTITY",
                        "Tenant e usuario nao formam uma identidade valida.",
                        http_status=403,
                    )
                row = await repo.get_session(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    public_session_id=candidate,
                    for_update=True,
                )
                if row is None:
                    row = await repo.create_session(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        public_session_id=candidate,
                        expires_at=self._expires_at(),
                    )
                if row.status == "ACTIVE" and row.expires_at <= utc_now():
                    row.status = "EXPIRED"
                    row.updated_at = utc_now()
                    row.lock_version += 1
                    await repo.record_event(
                        row=row,
                        event_type=ConversationEventType.SESSION_EXPIRED,
                    )
                    expired_version = row.context_version
                else:
                    self._assert_accessible(row)
            if expired_version is not None:
                raise ConversationStateError(
                    "CONVERSATION_EXPIRED",
                    "A conversa expirou. Inicie uma nova sessao.",
                    actual_context_version=expired_version,
                )
            return row
        except IntegrityError as exc:
            # A concurrent creator with the same owner is a valid resume.
            async with self.session_factory() as db:
                row = await ConversationStateRepository(db).get_session(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    public_session_id=candidate,
                )
                if row is not None:
                    self._assert_accessible(row)
                    return row
            raise ConversationStateError(
                "SESSION_ID_ALREADY_BOUND",
                "A sessao informada ja pertence a outra identidade.",
                http_status=403,
            ) from exc

    def _assert_accessible(self, row: ConversationSession) -> None:
        now = utc_now()
        if row.status == "ACTIVE" and row.expires_at <= now:
            raise ConversationStateError(
                "CONVERSATION_EXPIRED",
                "A conversa expirou. Inicie uma nova sessao.",
                actual_context_version=row.context_version,
            )
        if row.status != "ACTIVE":
            raise ConversationStateError(
                f"CONVERSATION_{row.status}",
                "A conversa nao aceita novos turnos neste estado.",
                actual_context_version=row.context_version,
            )

    async def start_turn(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        turn: ConversationTurnStart,
    ) -> StartedTurn:
        row = await self.resolve_or_create_session(
            tenant_id=tenant_id,
            user_id=user_id,
            public_session_id=turn.public_session_id,
        )
        protected = self.protector.protect(turn.content)
        async with self.session_factory() as db, db.begin():
            repo = ConversationStateRepository(db)
            locked = await repo.get_session_by_id(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=row.id,
                for_update=True,
            )
            if locked is None:
                raise ConversationStateError("SESSION_NOT_FOUND", "Conversa nao encontrada.", http_status=404)
            self._assert_accessible(locked)
            if locked.next_sequence > self.retention.max_nodes:
                raise ConversationStateError(
                    "CONVERSATION_NODE_LIMIT",
                    "A conversa atingiu o limite de tamanho. Inicie uma nova sessao.",
                )
            existing = await repo.find_by_client_message(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=locked.id,
                client_message_id=turn.client_message_id,
            )
            if existing is not None:
                if existing.content_fingerprint != protected.fingerprint:
                    raise ConversationStateError(
                        "IDEMPOTENCY_CONTENT_CONFLICT",
                        "O identificador da mensagem foi reutilizado com outro conteudo.",
                    )
                response = await repo.get_response_for_query(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    session_id=locked.id,
                    query_node_id=existing.id,
                )
                return StartedTurn(
                    public_session_id=locked.public_session_id,
                    session_id=locked.id,
                    query_node_id=existing.id,
                    parent_node_id=existing.parent_node_id,
                    base_context_version=existing.base_context_version,
                    context_epoch=locked.context_epoch,
                    idempotent_replay=True,
                    response_node_id=response.id if response else None,
                )
            if (
                turn.expected_context_version is not None
                and turn.expected_context_version != locked.context_version
            ):
                raise ConversationStateError(
                    "CONTEXT_VERSION_CONFLICT",
                    "A conversa foi atualizada em outra janela.",
                    actual_context_version=locked.context_version,
                )
            parent = turn.parent_node_id or locked.active_head_node_id
            if parent is not None and await repo.get_node(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=locked.id,
                node_id=parent,
            ) is None:
                raise ConversationStateError("INVALID_PARENT", "O ponto de continuacao nao pertence a conversa.")
            node = await repo.append_node(
                row=locked,
                parent_node_id=parent,
                role="user",
                node_type="USER_QUERY",
                status="IN_PROGRESS",
                base_context_version=locked.context_version,
                content_ciphertext=protected.ciphertext,
                content_key_version=protected.key_version,
                content_fingerprint=protected.fingerprint,
                client_message_id=turn.client_message_id,
            )
            await repo.record_event(
                row=locked,
                event_type=ConversationEventType.TURN_STARTED,
                node_id=node.id,
                fingerprint=protected.fingerprint,
                metadata={"base_context_version": locked.context_version},
            )
            return StartedTurn(
                public_session_id=locked.public_session_id,
                session_id=locked.id,
                query_node_id=node.id,
                parent_node_id=parent,
                base_context_version=locked.context_version,
                context_epoch=locked.context_epoch,
            )

    async def complete_turn(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        completion: ConversationTurnCompletion,
    ) -> CompletedTurn:
        protected = self.protector.protect(completion.response_content)
        async with self.session_factory() as db, db.begin():
            repo = ConversationStateRepository(db)
            row = await repo.get_session_by_id(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=completion.session_id,
                for_update=True,
            )
            if row is None:
                raise ConversationStateError("SESSION_NOT_FOUND", "Conversa nao encontrada.", http_status=404)
            self._assert_accessible(row)
            query_node = await repo.get_node(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=row.id,
                node_id=completion.query_node_id,
            )
            if query_node is None or query_node.node_type != "USER_QUERY":
                raise ConversationStateError("QUERY_NODE_NOT_FOUND", "Turno de origem nao encontrado.", http_status=404)
            existing = await repo.get_response_for_query(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=row.id,
                query_node_id=query_node.id,
            )
            if existing is not None:
                return CompletedTurn(
                    public_session_id=row.public_session_id,
                    query_node_id=query_node.id,
                    response_node_id=existing.id,
                    parent_node_id=query_node.parent_node_id,
                    context_version=row.context_version,
                    context_epoch=row.context_epoch,
                    idempotent_replay=True,
                )
            if row.context_version != completion.base_context_version:
                await repo.record_event(
                    row=row,
                    event_type=ConversationEventType.CONTEXT_CONFLICT,
                    node_id=query_node.id,
                    metadata={
                        "expected": completion.base_context_version,
                        "actual": row.context_version,
                    },
                )
                raise ConversationStateError(
                    "CONTEXT_VERSION_CONFLICT",
                    "Outro turno foi concluido antes deste. A resposta nao substituiu o estado atual.",
                    actual_context_version=row.context_version,
                )
            next_version = row.context_version + 1
            state = ConversationStateV2.model_validate({
                **completion.state.model_dump(mode="python"),
                "context_epoch": row.context_epoch,
                "context_version": next_version,
                "last_query_node_id": query_node.id,
                "updated_at": utc_now(),
            })
            response = await repo.append_node(
                row=row,
                parent_node_id=query_node.id,
                role="assistant",
                node_type="ASSISTANT_RESPONSE",
                status="COMPLETED",
                base_context_version=completion.base_context_version,
                content_ciphertext=protected.ciphertext,
                content_key_version=protected.key_version,
                content_fingerprint=protected.fingerprint,
                search_history_id=completion.search_history_id,
                response_fingerprint=completion.response_fingerprint or protected.fingerprint,
            )
            state = ConversationStateV2.model_validate({
                **state.model_dump(mode="python"),
                "last_response_node_id": response.id,
            })
            swapped = await repo.compare_and_swap(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=row.id,
                expected_context_version=completion.base_context_version,
                new_context_version=next_version,
                head_node_id=response.id,
                expires_at=self._expires_at(),
            )
            if not swapped:
                raise ConversationStateError(
                    "CONTEXT_VERSION_CONFLICT",
                    "O estado mudou durante a conclusao do turno.",
                    actual_context_version=row.context_version,
                )
            row.context_version = next_version
            row.active_head_node_id = response.id
            await repo.create_snapshot(row=row, head_node_id=response.id, state=state)
            query_node.status = "COMPLETED"
            query_node.completed_at = utc_now()
            await repo.record_event(
                row=row,
                event_type=ConversationEventType.TURN_COMPLETED,
                node_id=response.id,
                fingerprint=completion.response_fingerprint or protected.fingerprint,
            )
            await repo.record_event(
                row=row,
                event_type=ConversationEventType.CONTEXT_UPDATED,
                node_id=response.id,
            )
            return CompletedTurn(
                public_session_id=row.public_session_id,
                query_node_id=query_node.id,
                response_node_id=response.id,
                parent_node_id=query_node.parent_node_id,
                context_version=next_version,
                context_epoch=row.context_epoch,
            )

    async def fail_turn(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        failure: ConversationTurnFailure,
    ) -> uuid.UUID:
        protected = self.protector.protect(failure.safe_message)
        async with self.session_factory() as db, db.begin():
            repo = ConversationStateRepository(db)
            row = await repo.get_session_by_id(
                tenant_id=tenant_id, user_id=user_id, session_id=failure.session_id, for_update=True,
            )
            if row is None:
                raise ConversationStateError("SESSION_NOT_FOUND", "Conversa nao encontrada.", http_status=404)
            query_node = await repo.get_node(
                tenant_id=tenant_id, user_id=user_id, session_id=row.id, node_id=failure.query_node_id,
            )
            if query_node is None:
                raise ConversationStateError("QUERY_NODE_NOT_FOUND", "Turno nao encontrado.", http_status=404)
            existing = await repo.get_response_for_query(
                tenant_id=tenant_id, user_id=user_id, session_id=row.id, query_node_id=query_node.id,
            )
            if existing:
                return existing.id
            error_node = await repo.append_node(
                row=row,
                parent_node_id=query_node.id,
                role="assistant",
                node_type="ERROR",
                status="FAILED",
                base_context_version=failure.base_context_version,
                content_ciphertext=protected.ciphertext,
                content_key_version=protected.key_version,
                content_fingerprint=protected.fingerprint,
                response_fingerprint=failure.error_code,
            )
            query_node.status = "FAILED"
            query_node.failed_at = utc_now()
            await repo.record_event(
                row=row,
                event_type=ConversationEventType.TURN_FAILED,
                node_id=error_node.id,
                fingerprint=failure.error_code,
            )
            return error_node.id

    async def load_state(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        public_session_id: str,
    ) -> tuple[ConversationSession, ConversationStateV2]:
        expired = False
        async with self.session_factory() as db, db.begin():
            repo = ConversationStateRepository(db)
            row = await repo.get_session(
                tenant_id=tenant_id,
                user_id=user_id,
                public_session_id=public_session_id,
                for_update=True,
            )
            if row is None:
                raise ConversationStateError("SESSION_NOT_FOUND", "Conversa nao encontrada.", http_status=404)
            if row.status == "ACTIVE" and row.expires_at <= utc_now():
                row.status = "EXPIRED"
                row.updated_at = utc_now()
                row.lock_version += 1
                await repo.record_event(
                    row=row,
                    event_type=ConversationEventType.SESSION_EXPIRED,
                )
                expired = True
        if expired:
            raise ConversationStateError(
                "CONVERSATION_EXPIRED",
                "A conversa expirou. Inicie uma nova sessao.",
                actual_context_version=row.context_version,
            )
        async with self.session_factory() as db:
            repo = ConversationStateRepository(db)
            snapshot = await repo.load_snapshot(
                tenant_id=tenant_id, user_id=user_id, session_id=row.id,
            )
            if snapshot is None:
                return row, ConversationStateV2(
                    context_epoch=row.context_epoch,
                    context_version=row.context_version,
                )
            state = ConversationStateV2.model_validate_json(json.dumps(snapshot.state_json))
            from contracts.conversation_state_v2 import compute_state_checksum
            if compute_state_checksum(state) != snapshot.state_checksum:
                raise ConversationStateError(
                    "SNAPSHOT_CHECKSUM_MISMATCH",
                    "O estado da conversa falhou na verificacao de integridade.",
                    http_status=500,
                )
            return row, state

    async def mutate_session(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        public_session_id: str,
        action: str,
        client_message_id: uuid.UUID | None = None,
    ) -> ConversationSession:
        async with self.session_factory() as db, db.begin():
            repo = ConversationStateRepository(db)
            row = await repo.get_session(
                tenant_id=tenant_id, user_id=user_id, public_session_id=public_session_id, for_update=True,
            )
            if row is None:
                raise ConversationStateError("SESSION_NOT_FOUND", "Conversa nao encontrada.", http_status=404)
            now = utc_now()
            event: ConversationEventType
            if action == "archive":
                if row.status != "ACTIVE":
                    raise ConversationStateError("INVALID_SESSION_STATUS", "Somente conversa ativa pode ser arquivada.")
                row.status, row.archived_at = "ARCHIVED", now
                event = ConversationEventType.SESSION_ARCHIVED
            elif action == "reopen":
                if row.status != "ARCHIVED":
                    raise ConversationStateError("INVALID_SESSION_STATUS", "Somente conversa arquivada pode ser reaberta.")
                row.status, row.archived_at, row.expires_at = "ACTIVE", None, self._expires_at()
                event = ConversationEventType.SESSION_REOPENED
            elif action == "delete":
                if row.status == "DELETED":
                    return row
                row.status, row.deleted_at = "DELETED", now
                event = ConversationEventType.SESSION_DELETED
            elif action == "reset":
                if row.status != "ACTIVE":
                    raise ConversationStateError("INVALID_SESSION_STATUS", "Somente conversa ativa pode ser reiniciada.")
                marker = f"reset:{client_message_id}" if client_message_id else None
                if marker:
                    existing = await repo.find_by_client_message(
                        tenant_id=tenant_id, user_id=user_id, session_id=row.id,
                        client_message_id=client_message_id,
                    )
                    if existing:
                        return row
                protected = self.protector.protect("CONTEXT_RESET")
                reset = await repo.append_node(
                    row=row,
                    parent_node_id=row.active_head_node_id,
                    role="system",
                    node_type="RESET",
                    status="COMPLETED",
                    base_context_version=row.context_version,
                    content_ciphertext=protected.ciphertext,
                    content_key_version=protected.key_version,
                    content_fingerprint=protected.fingerprint,
                    client_message_id=client_message_id,
                )
                row.context_epoch += 1
                row.context_version += 1
                row.active_head_node_id = reset.id
                state = ConversationStateV2(
                    context_epoch=row.context_epoch,
                    context_version=row.context_version,
                    last_response_node_id=reset.id,
                )
                await repo.create_snapshot(row=row, head_node_id=reset.id, state=state)
                event = ConversationEventType.SESSION_RESET
            else:
                raise ValueError("unsupported session action")
            row.updated_at = now
            row.lock_version += 1
            await repo.record_event(row=row, event_type=event, node_id=row.active_head_node_id)
            return row

    async def run_retention(self, *, dry_run: bool = True) -> dict[str, int]:
        now = utc_now()
        cutoff = now - timedelta(days=self.retention.purge_after_days)
        async with self.session_factory() as db, db.begin():
            repo = ConversationStateRepository(db)
            expiration_candidates = await repo.count_expired_candidates(
                now=now, limit=self.retention.purge_batch_size,
            )
            expired = (
                0
                if dry_run
                else await repo.mark_expired_batch(
                    now=now, limit=self.retention.purge_batch_size,
                )
            )
            purged = await repo.purge_deleted_batch(
                cutoff=cutoff,
                limit=self.retention.purge_batch_size,
                dry_run=dry_run,
            )
            return {
                "expiration_candidates": expiration_candidates,
                "expired": expired,
                "purge_candidates": len(purged),
                "purged": 0 if dry_run else len(purged),
            }


conversation_state_service = ConversationStateService()
