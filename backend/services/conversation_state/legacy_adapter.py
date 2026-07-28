from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import select

from config import settings
from contracts.conversation_state_v2 import (
    CONVERSATION_STATE_VERSION,
    ConversationEventType,
    ConversationImportResult,
    ConversationStateV2,
)
from models.conversation_state import ConversationLegacyImport
from models.new_pipeline_contracts import ConversationGraph
from services.conversation_state.repository import ConversationStateRepository
from services.conversation_state.service import ConversationStateError, ConversationStateService


MAX_LEGACY_FILE_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True)
class LegacyNode:
    legacy_id: str
    parent_legacy_id: str | None
    content: str


@dataclass(frozen=True)
class AdaptedLegacyGraph:
    nodes: tuple[LegacyNode, ...]
    current_legacy_id: str | None
    warnings: tuple[str, ...]


class LegacyConversationGraphAdapter:
    """Validates the current JSON format without inferring tenant or user."""

    def read(self, path: Path) -> tuple[AdaptedLegacyGraph, str]:
        path = path.resolve(strict=True)
        if not path.is_file() or path.suffix.lower() != ".json":
            raise ValueError("legacy import requires one explicit JSON file")
        size = path.stat().st_size
        if size <= 0 or size > MAX_LEGACY_FILE_BYTES:
            raise ValueError("legacy conversation file is outside the size policy")
        raw = path.read_bytes()
        checksum = hashlib.sha256(raw).hexdigest()
        try:
            graph = ConversationGraph.model_validate_json(raw)
        except (ValidationError, ValueError) as exc:
            raise ValueError("invalid legacy conversation schema") from exc
        pending = dict(graph.nodes)
        ordered: list[LegacyNode] = []
        emitted: set[str] = set()
        while pending:
            progressed = False
            for node_id, node in list(pending.items()):
                if node.parent_id is None or node.parent_id in emitted:
                    ordered.append(LegacyNode(node_id, node.parent_id, node.user_query))
                    emitted.add(node_id)
                    pending.pop(node_id)
                    progressed = True
            if not progressed:
                raise ValueError("legacy graph contains missing parents or a cycle")
        warnings = (
            "LEGACY_ADAPTER: analytical datasets, SQL, binds and debug payloads were not imported",
        )
        return AdaptedLegacyGraph(tuple(ordered), graph.current_node_id, warnings), checksum


class LegacyConversationImporter:
    def __init__(
        self,
        service: ConversationStateService,
        adapter: LegacyConversationGraphAdapter | None = None,
        *,
        allow_apply: bool | None = None,
    ) -> None:
        self.service = service
        self.adapter = adapter or LegacyConversationGraphAdapter()
        self.allow_apply = (
            settings.CONVERSATION_LEGACY_IMPORT_ENABLED
            if allow_apply is None
            else allow_apply
        )

    async def import_file(
        self,
        *,
        path: Path,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        public_session_id: str | None,
        dry_run: bool = True,
    ) -> ConversationImportResult:
        graph, checksum = self.adapter.read(path)
        if dry_run:
            return ConversationImportResult(
                source_checksum=checksum,
                public_session_id=public_session_id,
                imported_nodes=len(graph.nodes),
                dry_run=True,
                warnings=list(graph.warnings),
            )
        if not self.allow_apply:
            raise ConversationStateError(
                "LEGACY_IMPORT_DISABLED",
                "A importacao legada real esta desabilitada; use dry-run ou habilite a flag governada.",
                http_status=403,
            )
        row = await self.service.resolve_or_create_session(
            tenant_id=tenant_id,
            user_id=user_id,
            public_session_id=public_session_id,
        )
        async with self.service.session_factory() as db, db.begin():
            duplicate = await db.scalar(
                select(ConversationLegacyImport.id).where(
                    ConversationLegacyImport.tenant_id == tenant_id,
                    ConversationLegacyImport.user_id == user_id,
                    ConversationLegacyImport.source_checksum == checksum,
                )
            )
            if duplicate:
                return ConversationImportResult(
                    source_checksum=checksum,
                    public_session_id=row.public_session_id,
                    imported_nodes=0,
                    dry_run=False,
                    duplicate=True,
                    warnings=list(graph.warnings),
                )
            repo = ConversationStateRepository(db)
            locked = await repo.get_session_by_id(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=row.id,
                for_update=True,
            )
            if locked is None:
                raise ConversationStateError("SESSION_NOT_FOUND", "Conversa nao encontrada.", http_status=404)
            id_map: dict[str, uuid.UUID] = {}
            for legacy in graph.nodes:
                protected = self.service.protector.protect(legacy.content)
                node = await repo.append_node(
                    row=locked,
                    parent_node_id=id_map.get(legacy.parent_legacy_id or ""),
                    role="user",
                    node_type="USER_QUERY",
                    status="COMPLETED",
                    base_context_version=locked.context_version,
                    content_ciphertext=protected.ciphertext,
                    content_key_version=protected.key_version,
                    content_fingerprint=protected.fingerprint,
                )
                id_map[legacy.legacy_id] = node.id
            head_id = id_map.get(graph.current_legacy_id or "")
            locked.active_head_node_id = head_id
            locked.context_version += 1
            state = ConversationStateV2(
                context_epoch=locked.context_epoch,
                context_version=locked.context_version,
                last_query_node_id=head_id,
                field_origins={},
                context_markers=["LEGACY_ADAPTER"],
            )
            await repo.create_snapshot(row=locked, head_node_id=head_id, state=state)
            await repo.record_event(
                row=locked,
                event_type=ConversationEventType.LEGACY_IMPORTED,
                node_id=head_id,
                fingerprint=checksum,
                metadata={"node_count": len(graph.nodes), "source": "EXPLICIT_JSON"},
            )
            db.add(ConversationLegacyImport(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=locked.id,
                source_checksum=checksum,
                schema_version=CONVERSATION_STATE_VERSION,
                source_format="LEGACY_CONVERSATION_GRAPH_JSON",
                imported_nodes=len(graph.nodes),
                warnings=list(graph.warnings),
            ))
        return ConversationImportResult(
            source_checksum=checksum,
            public_session_id=row.public_session_id,
            imported_nodes=len(graph.nodes),
            dry_run=False,
            warnings=list(graph.warnings),
        )
