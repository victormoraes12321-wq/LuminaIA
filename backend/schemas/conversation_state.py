from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ConversationCreateRequest(BaseModel):
    session_id: str | None = Field(
        default=None,
        min_length=16,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]+$",
    )


class ConversationMutationRequest(BaseModel):
    client_message_id: uuid.UUID | None = None


class ConversationSessionPublic(BaseModel):
    session_id: str
    status: str
    context_version: int
    context_epoch: int
    head_node_id: uuid.UUID | None
    created_at: datetime
    last_activity_at: datetime
    expires_at: datetime


class ConversationSessionPage(BaseModel):
    items: list[ConversationSessionPublic]
    next_cursor_activity: datetime | None = None
    next_cursor_id: uuid.UUID | None = None


class ConversationNodePublic(BaseModel):
    node_id: uuid.UUID
    sequence_number: int
    parent_node_id: uuid.UUID | None
    role: str
    node_type: str
    status: str
    created_at: datetime
    completed_at: datetime | None
    failed_at: datetime | None


class ConversationNodePage(BaseModel):
    items: list[ConversationNodePublic]
    next_sequence: int | None = None
