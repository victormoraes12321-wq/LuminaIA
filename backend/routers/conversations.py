from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from database import AsyncSessionLocal
from models.user import User
from routers.dependencies import get_current_user
from schemas.conversation_state import (
    ConversationCreateRequest,
    ConversationMutationRequest,
    ConversationNodePage,
    ConversationNodePublic,
    ConversationSessionPage,
    ConversationSessionPublic,
)
from services.conversation_state.repository import ConversationStateRepository
from services.conversation_state.service import (
    ConversationStateError,
    conversation_state_service,
)


router = APIRouter(prefix="/conversations", tags=["Conversation State"])


def _session_public(row) -> ConversationSessionPublic:
    return ConversationSessionPublic(
        session_id=row.public_session_id,
        status=row.status,
        context_version=row.context_version,
        context_epoch=row.context_epoch,
        head_node_id=row.active_head_node_id,
        created_at=row.created_at,
        last_activity_at=row.last_activity_at,
        expires_at=row.expires_at,
    )


def _raise_service_error(exc: ConversationStateError) -> None:
    raise HTTPException(
        status_code=exc.http_status,
        detail={
            "code": exc.code,
            "message": str(exc),
            "actual_context_version": exc.actual_context_version,
        },
    ) from exc


@router.post("", response_model=ConversationSessionPublic, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreateRequest,
    current_user: User = Depends(get_current_user),
) -> ConversationSessionPublic:
    try:
        row = await conversation_state_service.resolve_or_create_session(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            public_session_id=payload.session_id,
        )
        return _session_public(row)
    except ConversationStateError as exc:
        _raise_service_error(exc)


@router.get("", response_model=ConversationSessionPage)
async def list_conversations(
    limit: int = Query(default=25, ge=1, le=100),
    cursor_activity: datetime | None = None,
    cursor_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
) -> ConversationSessionPage:
    if (cursor_activity is None) != (cursor_id is None):
        raise HTTPException(status_code=422, detail="Os dois campos do cursor sao obrigatorios.")
    async with AsyncSessionLocal() as db:
        rows = await ConversationStateRepository(db).list_sessions(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            limit=limit + 1,
            cursor_activity=cursor_activity,
            cursor_id=cursor_id,
        )
    has_more = len(rows) > limit
    rows = rows[:limit]
    tail = rows[-1] if rows and has_more else None
    return ConversationSessionPage(
        items=[_session_public(row) for row in rows],
        next_cursor_activity=tail.last_activity_at if tail else None,
        next_cursor_id=tail.id if tail else None,
    )


@router.get("/{session_id}", response_model=ConversationSessionPublic)
async def get_conversation(
    session_id: str,
    current_user: User = Depends(get_current_user),
) -> ConversationSessionPublic:
    try:
        row, _ = await conversation_state_service.load_state(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            public_session_id=session_id,
        )
        return _session_public(row)
    except ConversationStateError as exc:
        _raise_service_error(exc)


@router.get("/{session_id}/nodes", response_model=ConversationNodePage)
async def list_conversation_nodes(
    session_id: str,
    after_sequence: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
) -> ConversationNodePage:
    try:
        row, _ = await conversation_state_service.load_state(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            public_session_id=session_id,
        )
    except ConversationStateError as exc:
        _raise_service_error(exc)
    async with AsyncSessionLocal() as db:
        rows = await ConversationStateRepository(db).list_nodes(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            session_id=row.id,
            after_sequence=after_sequence,
            limit=limit + 1,
        )
    has_more = len(rows) > limit
    rows = rows[:limit]
    return ConversationNodePage(
        items=[
            ConversationNodePublic(
                node_id=node.id,
                sequence_number=node.sequence_number,
                parent_node_id=node.parent_node_id,
                role=node.role,
                node_type=node.node_type,
                status=node.status,
                created_at=node.created_at,
                completed_at=node.completed_at,
                failed_at=node.failed_at,
            )
            for node in rows
        ],
        next_sequence=rows[-1].sequence_number if rows and has_more else None,
    )


async def _mutate(
    action: str,
    session_id: str,
    payload: ConversationMutationRequest,
    current_user: User,
) -> ConversationSessionPublic:
    try:
        row = await conversation_state_service.mutate_session(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            public_session_id=session_id,
            action=action,
            client_message_id=payload.client_message_id,
        )
        return _session_public(row)
    except ConversationStateError as exc:
        _raise_service_error(exc)


@router.post("/{session_id}/reset", response_model=ConversationSessionPublic)
async def reset_conversation(
    session_id: str,
    payload: ConversationMutationRequest,
    current_user: User = Depends(get_current_user),
) -> ConversationSessionPublic:
    return await _mutate("reset", session_id, payload, current_user)


@router.post("/{session_id}/archive", response_model=ConversationSessionPublic)
async def archive_conversation(
    session_id: str,
    payload: ConversationMutationRequest,
    current_user: User = Depends(get_current_user),
) -> ConversationSessionPublic:
    return await _mutate("archive", session_id, payload, current_user)


@router.post("/{session_id}/reopen", response_model=ConversationSessionPublic)
async def reopen_conversation(
    session_id: str,
    payload: ConversationMutationRequest,
    current_user: User = Depends(get_current_user),
) -> ConversationSessionPublic:
    return await _mutate("reopen", session_id, payload, current_user)


@router.delete("/{session_id}", response_model=ConversationSessionPublic)
async def delete_conversation(
    session_id: str,
    current_user: User = Depends(get_current_user),
) -> ConversationSessionPublic:
    return await _mutate("delete", session_id, ConversationMutationRequest(), current_user)
