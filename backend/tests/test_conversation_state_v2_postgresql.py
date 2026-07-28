from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import func, select

from config import settings
from contracts.conversation_state_v2 import (
    ConversationRetentionPolicy,
    ConversationRolloutMode,
    ConversationStateV2,
    ConversationTurnCompletion,
    ConversationTurnFailure,
    ConversationTurnStart,
)
from database import AsyncSessionLocal
from models.conversation_state import (
    ConversationEvent,
    ConversationLegacyImport,
    ConversationNodeRecord,
    ConversationSession,
    ConversationStateSnapshot,
)
from services.conversation_state.content_protector import ConversationContentProtector
from services.conversation_state.legacy_adapter import LegacyConversationImporter
from services.conversation_state.repository import ConversationStateRepository
from services.conversation_state.service import ConversationStateError, ConversationStateService
from testing.test_database import CONSULTA_A, CONSULTA_B, GESTOR_A, TENANT_A, TENANT_B


pytestmark = [pytest.mark.integration, pytest.mark.database, pytest.mark.security]


def _service() -> ConversationStateService:
    return ConversationStateService(
        AsyncSessionLocal,
        protector=ConversationContentProtector(
            key=settings.ENCRYPTION_KEY,
            key_version="test-v1",
        ),
        mode=ConversationRolloutMode.POSTGRES_READ_WRITE,
    )


async def _start(service: ConversationStateService, session_id: str, content: str, *, client_id=None):
    return await service.start_turn(
        tenant_id=TENANT_A,
        user_id=CONSULTA_A,
        turn=ConversationTurnStart(
            public_session_id=session_id,
            client_message_id=client_id or uuid.uuid4(),
            content=content,
        ),
    )


async def _complete(service: ConversationStateService, started, state=None):
    return await service.complete_turn(
        tenant_id=TENANT_A,
        user_id=CONSULTA_A,
        completion=ConversationTurnCompletion(
            session_id=started.session_id,
            query_node_id=started.query_node_id,
            base_context_version=started.base_context_version,
            response_content="Resposta sintetica validada.",
            state=state or ConversationStateV2(),
        ),
    )


@pytest.mark.asyncio
async def test_session_round_trip_restart_and_idempotent_replay() -> None:
    service_a = _service()
    public_id = f"lumina-{uuid.uuid4()}"
    client_id = uuid.uuid4()
    started = await _start(service_a, public_id, "Faturamento de junho", client_id=client_id)
    completed = await _complete(service_a, started)
    assert completed.context_version == 1

    service_b = _service()
    row, state = await service_b.load_state(
        tenant_id=TENANT_A,
        user_id=CONSULTA_A,
        public_session_id=public_id,
    )
    assert row.active_head_node_id == completed.response_node_id
    assert state.context_version == 1

    replay = await _start(service_b, public_id, "Faturamento de junho", client_id=client_id)
    assert replay.idempotent_replay is True
    assert replay.response_node_id == completed.response_node_id
    with pytest.raises(ConversationStateError, match="reutilizado"):
        await _start(service_b, public_id, "Conteudo diferente", client_id=client_id)


@pytest.mark.asyncio
async def test_four_turn_state_and_parentage_survive_service_recreation() -> None:
    public_id = f"lumina-{uuid.uuid4()}"
    questions = [
        "Qual foi o faturamento de junho de 2026 da filial Centro?",
        "E em julho?",
        "Agora compare os dois meses.",
        "Separe por produto.",
    ]
    parent = None
    version = 0
    for index, question in enumerate(questions, start=1):
        service = _service()
        started = await service.start_turn(
            tenant_id=TENANT_A,
            user_id=CONSULTA_A,
            turn=ConversationTurnStart(
                public_session_id=public_id,
                client_message_id=uuid.uuid4(),
                parent_node_id=parent,
                expected_context_version=version,
                content=question,
            ),
        )
        state = ConversationStateV2(
            active_subject="faturamento",
            context_markers=[
                "filial:Centro",
                "periodo:2026-06",
                *([] if index < 2 else ["periodo:2026-07"]),
                *([] if index < 3 else ["comparacao:junho-julho"]),
                *([] if index < 4 else ["dimensao:produto"]),
            ],
        )
        completed = await _complete(service, started, state)
        parent = completed.response_node_id
        version = completed.context_version

    _, restored = await _service().load_state(
        tenant_id=TENANT_A,
        user_id=CONSULTA_A,
        public_session_id=public_id,
    )
    assert restored.context_version == 4
    assert restored.context_epoch == 0
    assert restored.context_markers[-1] == "dimensao:produto"
    assert restored.last_response_node_id == parent
    async with AsyncSessionLocal() as db:
        versions = list((await db.execute(
            select(ConversationStateSnapshot.context_version)
            .join(ConversationSession)
            .where(ConversationSession.public_session_id == public_id)
            .order_by(ConversationStateSnapshot.context_version)
        )).scalars())
        assert versions == [1, 2, 3, 4]


@pytest.mark.asyncio
async def test_owner_scope_parent_scope_and_unpredictable_session_binding() -> None:
    service = _service()
    public_id = f"lumina-{uuid.uuid4()}"
    started = await _start(service, public_id, "Consulta isolada")
    with pytest.raises(ConversationStateError) as wrong_user:
        await service.load_state(
            tenant_id=TENANT_A,
            user_id=uuid.uuid4(),
            public_session_id=public_id,
        )
    assert wrong_user.value.code == "SESSION_NOT_FOUND"
    with pytest.raises(ConversationStateError):
        await service.resolve_or_create_session(
            tenant_id=TENANT_B,
            user_id=CONSULTA_B,
            public_session_id=public_id,
        )
    other = await _start(service, f"lumina-{uuid.uuid4()}", "Outra conversa")
    with pytest.raises(ConversationStateError) as invalid_parent:
        await service.start_turn(
            tenant_id=TENANT_A,
            user_id=CONSULTA_A,
            turn=ConversationTurnStart(
                public_session_id=public_id,
                client_message_id=uuid.uuid4(),
                parent_node_id=other.query_node_id,
                content="Parent forjado",
            ),
        )
    assert invalid_parent.value.code == "INVALID_PARENT"


@pytest.mark.asyncio
async def test_out_of_order_completion_returns_typed_conflict() -> None:
    service_a = _service()
    service_b = _service()
    public_id = f"lumina-{uuid.uuid4()}"
    first, second = await asyncio.gather(
        _start(service_a, public_id, "Primeiro writer"),
        _start(service_b, public_id, "Segundo writer"),
    )
    winner = await _complete(service_a, first)
    assert winner.context_version == 1
    with pytest.raises(ConversationStateError) as conflict:
        await _complete(service_b, second)
    assert conflict.value.code == "CONTEXT_VERSION_CONFLICT"


@pytest.mark.asyncio
async def test_branch_from_older_head_and_archive_during_active_turn() -> None:
    service = _service()
    public_id = f"lumina-{uuid.uuid4()}"
    first = await _start(service, public_id, "Primeiro turno")
    first_completed = await _complete(service, first)
    second = await service.start_turn(
        tenant_id=TENANT_A,
        user_id=CONSULTA_A,
        turn=ConversationTurnStart(
            public_session_id=public_id,
            client_message_id=uuid.uuid4(),
            parent_node_id=first_completed.response_node_id,
            expected_context_version=1,
            content="Segundo turno linear",
        ),
    )
    await _complete(service, second)
    branch = await service.start_turn(
        tenant_id=TENANT_A,
        user_id=CONSULTA_A,
        turn=ConversationTurnStart(
            public_session_id=public_id,
            client_message_id=uuid.uuid4(),
            parent_node_id=first_completed.response_node_id,
            expected_context_version=2,
            content="Branch alternativo",
        ),
    )
    branch_completed = await _complete(service, branch)
    assert branch_completed.parent_node_id == first_completed.response_node_id
    pending = await _start(service, public_id, "Turno ainda em andamento")
    await service.mutate_session(
        tenant_id=TENANT_A,
        user_id=CONSULTA_A,
        public_session_id=public_id,
        action="archive",
    )
    with pytest.raises(ConversationStateError) as archived:
        await _complete(service, pending)
    assert archived.value.code == "CONVERSATION_ARCHIVED"


@pytest.mark.asyncio
async def test_reset_archive_reopen_delete_and_keyset_pagination() -> None:
    service = _service()
    public_id = f"lumina-{uuid.uuid4()}"
    started = await _start(service, public_id, "Consulta")
    await _complete(service, started)
    reset = await service.mutate_session(
        tenant_id=TENANT_A,
        user_id=CONSULTA_A,
        public_session_id=public_id,
        action="reset",
        client_message_id=uuid.uuid4(),
    )
    assert reset.context_epoch == 1
    assert reset.context_version == 2
    async with AsyncSessionLocal() as db:
        reset_node = await db.get(ConversationNodeRecord, reset.active_head_node_id)
        assert reset_node is not None
        assert reset_node.completed_at is not None
        assert reset_node.completed_at >= reset_node.created_at
    archived = await service.mutate_session(
        tenant_id=TENANT_A, user_id=CONSULTA_A, public_session_id=public_id, action="archive",
    )
    assert archived.status == "ARCHIVED"
    reopened = await service.mutate_session(
        tenant_id=TENANT_A, user_id=CONSULTA_A, public_session_id=public_id, action="reopen",
    )
    assert reopened.status == "ACTIVE"
    deleted = await service.mutate_session(
        tenant_id=TENANT_A, user_id=CONSULTA_A, public_session_id=public_id, action="delete",
    )
    assert deleted.status == "DELETED"

    async with AsyncSessionLocal() as db:
        sessions = await ConversationStateRepository(db).list_sessions(
            tenant_id=TENANT_A, user_id=CONSULTA_A, limit=25,
        )
        assert all(row.status != "DELETED" for row in sessions)


@pytest.mark.asyncio
async def test_retention_dry_run_never_deletes() -> None:
    service = _service()
    public_id = f"lumina-{uuid.uuid4()}"
    row = await service.resolve_or_create_session(
        tenant_id=TENANT_A, user_id=CONSULTA_A, public_session_id=public_id,
    )
    await service.mutate_session(
        tenant_id=TENANT_A, user_id=CONSULTA_A, public_session_id=public_id, action="delete",
    )
    async with AsyncSessionLocal() as db, db.begin():
        stored = await ConversationStateRepository(db).get_session_by_id(
            tenant_id=TENANT_A, user_id=CONSULTA_A, session_id=row.id, for_update=True,
        )
        stored.deleted_at = datetime.now(timezone.utc) - timedelta(days=1000)
    report = await service.run_retention(dry_run=True)
    assert report["purged"] == 0
    loaded, _ = await service.load_state(
        tenant_id=TENANT_A, user_id=CONSULTA_A, public_session_id=public_id,
    )
    assert loaded.status == "DELETED"


@pytest.mark.asyncio
async def test_expiration_is_persisted_and_blocks_new_turns() -> None:
    service = _service()
    public_id = f"lumina-{uuid.uuid4()}"
    row = await service.resolve_or_create_session(
        tenant_id=TENANT_A, user_id=CONSULTA_A, public_session_id=public_id,
    )
    async with AsyncSessionLocal() as db, db.begin():
        stored = await db.get(ConversationSession, row.id)
        assert stored is not None
        now = datetime.now(timezone.utc)
        stored.created_at = now - timedelta(days=2)
        stored.updated_at = now - timedelta(days=2)
        stored.last_activity_at = now - timedelta(days=2)
        stored.expires_at = now - timedelta(days=1)

    with pytest.raises(ConversationStateError) as expired:
        await service.load_state(
            tenant_id=TENANT_A, user_id=CONSULTA_A, public_session_id=public_id,
        )
    assert expired.value.code == "CONVERSATION_EXPIRED"
    async with AsyncSessionLocal() as db:
        stored = await db.get(ConversationSession, row.id)
        assert stored is not None and stored.status == "EXPIRED"
        event_count = await db.scalar(
            select(func.count()).select_from(ConversationEvent).where(
                ConversationEvent.session_id == row.id,
                ConversationEvent.event_type == "SESSION_EXPIRED",
            )
        )
        assert event_count == 1
    with pytest.raises(ConversationStateError) as blocked:
        await _start(service, public_id, "Novo turno apos expiracao")
    assert blocked.value.code == "CONVERSATION_EXPIRED"


@pytest.mark.asyncio
async def test_effective_purge_respects_cutoff_batch_and_cascades_content() -> None:
    retention = ConversationRetentionPolicy(
        active_ttl_hours=24,
        archive_after_days=1,
        soft_delete_after_days=1,
        purge_after_days=2,
        max_content_bytes=12000,
        max_nodes=10000,
        purge_batch_size=1,
    )
    service = ConversationStateService(
        AsyncSessionLocal,
        protector=ConversationContentProtector(
            key=settings.ENCRYPTION_KEY, key_version="test-v1",
        ),
        retention=retention,
        mode=ConversationRolloutMode.POSTGRES_READ_WRITE,
    )
    eligible_ids: list[uuid.UUID] = []
    for suffix in ("one", "two"):
        public_id = f"lumina-{uuid.uuid4()}"
        started = await _start(service, public_id, f"Consulta {suffix}")
        await _complete(service, started)
        deleted = await service.mutate_session(
            tenant_id=TENANT_A,
            user_id=CONSULTA_A,
            public_session_id=public_id,
            action="delete",
        )
        eligible_ids.append(deleted.id)
    active = await service.resolve_or_create_session(
        tenant_id=TENANT_A,
        user_id=CONSULTA_A,
        public_session_id=f"lumina-{uuid.uuid4()}",
    )
    async with AsyncSessionLocal() as db, db.begin():
        rows = list((await db.execute(
            select(ConversationSession).where(ConversationSession.id.in_(eligible_ids))
        )).scalars())
        for row in rows:
            row.deleted_at = datetime.now(timezone.utc) - timedelta(days=10)

    first = await service.run_retention(dry_run=False)
    assert first["purge_candidates"] == 1
    assert first["purged"] == 1
    second = await service.run_retention(dry_run=False)
    assert second["purged"] == 1
    third = await service.run_retention(dry_run=False)
    assert third["purged"] == 0
    async with AsyncSessionLocal() as db:
        assert await db.get(ConversationSession, active.id) is not None
        for session_id in eligible_ids:
            assert await db.get(ConversationSession, session_id) is None
            assert await db.scalar(
                select(func.count()).select_from(ConversationNodeRecord).where(
                    ConversationNodeRecord.session_id == session_id
                )
            ) == 0
            assert await db.scalar(
                select(func.count()).select_from(ConversationStateSnapshot).where(
                    ConversationStateSnapshot.session_id == session_id
                )
            ) == 0


@pytest.mark.asyncio
async def test_legacy_import_dry_run_real_import_and_duplicate(
    tmp_path: Path,
) -> None:
    plan = {
        "status": "READY",
        "intent": "KPI",
        "goal": "Fixture sintetica",
        "entities": ["Venda"],
        "metrics": ["receita_total"],
        "dimensions": [],
    }
    dashboard = {"chart_type": "KPI_CARD"}
    source = tmp_path / "legacy.json"
    source.write_text(json.dumps({
        "nodes": {
            "root": {
                "node_id": "root",
                "user_query": "Faturamento de junho",
                "canonical_plan": plan,
                "dashboard_state": dashboard,
            },
            "child": {
                "node_id": "child",
                "parent_id": "root",
                "user_query": "E julho?",
                "canonical_plan": plan,
                "dashboard_state": dashboard,
            },
        },
        "current_node_id": "child",
    }), encoding="utf-8")
    disabled_importer = LegacyConversationImporter(_service())
    dry_run = await disabled_importer.import_file(
        path=source,
        tenant_id=TENANT_A,
        user_id=CONSULTA_A,
        public_session_id=None,
        dry_run=True,
    )
    assert dry_run.dry_run is True
    assert dry_run.imported_nodes == 2
    assert dry_run.public_session_id is None
    with pytest.raises(ConversationStateError) as disabled:
        await disabled_importer.import_file(
            path=source,
            tenant_id=TENANT_A,
            user_id=CONSULTA_A,
            public_session_id=None,
            dry_run=False,
        )
    assert disabled.value.code == "LEGACY_IMPORT_DISABLED"

    importer = LegacyConversationImporter(_service(), allow_apply=True)
    imported = await importer.import_file(
        path=source,
        tenant_id=TENANT_A,
        user_id=CONSULTA_A,
        public_session_id=None,
        dry_run=False,
    )
    assert imported.dry_run is False
    assert imported.imported_nodes == 2
    assert imported.public_session_id is not None
    row, state = await _service().load_state(
        tenant_id=TENANT_A,
        user_id=CONSULTA_A,
        public_session_id=imported.public_session_id,
    )
    assert state.context_markers == ["LEGACY_ADAPTER"]
    async with AsyncSessionLocal() as db:
        nodes = await ConversationStateRepository(db).list_nodes(
            tenant_id=TENANT_A,
            user_id=CONSULTA_A,
            session_id=row.id,
            after_sequence=None,
            limit=10,
        )
        assert [node.sequence_number for node in nodes] == [1, 2]
        assert nodes[1].parent_node_id == nodes[0].id
        assert all(node.content_ciphertext for node in nodes)
        ledger_count = await db.scalar(
            select(func.count()).select_from(ConversationLegacyImport).where(
                ConversationLegacyImport.session_id == row.id
            )
        )
        assert ledger_count == 1

    duplicate = await importer.import_file(
        path=source,
        tenant_id=TENANT_A,
        user_id=CONSULTA_A,
        public_session_id=imported.public_session_id,
        dry_run=False,
    )
    assert duplicate.duplicate is True
    assert duplicate.imported_nodes == 0


@pytest.mark.asyncio
async def test_failure_recovery_and_snapshot_checksum_tampering() -> None:
    service = _service()
    public_id = f"lumina-{uuid.uuid4()}"
    started = await _start(service, public_id, "Consulta que falhara")
    error_node_id = await service.fail_turn(
        tenant_id=TENANT_A,
        user_id=CONSULTA_A,
        failure=ConversationTurnFailure(
            session_id=started.session_id,
            query_node_id=started.query_node_id,
            base_context_version=started.base_context_version,
            error_code="SYNTHETIC_TIMEOUT",
            safe_message="Falha sintetica segura.",
        ),
    )
    replay = await _start(
        service,
        public_id,
        "Consulta que falhara",
        client_id=(await _client_id_for_node(started.query_node_id)),
    )
    assert replay.idempotent_replay is True
    assert replay.response_node_id == error_node_id

    next_turn = await _start(service, public_id, "Consulta recuperada")
    await _complete(service, next_turn, ConversationStateV2(context_markers=["recovered"]))
    async with AsyncSessionLocal() as db, db.begin():
        snapshot = (await db.execute(
            select(ConversationStateSnapshot)
            .where(ConversationStateSnapshot.session_id == started.session_id)
            .order_by(ConversationStateSnapshot.context_version.desc())
            .limit(1)
        )).scalar_one()
        snapshot.state_checksum = "0" * 64
    with pytest.raises(ConversationStateError) as mismatch:
        await service.load_state(
            tenant_id=TENANT_A, user_id=CONSULTA_A, public_session_id=public_id,
        )
    assert mismatch.value.code == "SNAPSHOT_CHECKSUM_MISMATCH"


async def _client_id_for_node(node_id: uuid.UUID) -> uuid.UUID:
    async with AsyncSessionLocal() as db:
        node = await db.get(ConversationNodeRecord, node_id)
        assert node is not None and node.client_message_id is not None
        return node.client_message_id


@pytest.mark.asyncio
async def test_twenty_concurrent_operations_have_unique_sequence_and_one_cas_winner() -> None:
    services = [_service() for _ in range(20)]
    public_id = f"lumina-{uuid.uuid4()}"
    starts = await asyncio.gather(*[
        _start(service, public_id, f"Writer {index}")
        for index, service in enumerate(services)
    ])
    assert len({started.query_node_id for started in starts}) == 20
    outcomes = await asyncio.gather(*[
        _complete(service, started)
        for service, started in zip(services, starts)
    ], return_exceptions=True)
    winners = [outcome for outcome in outcomes if not isinstance(outcome, BaseException)]
    conflicts = [outcome for outcome in outcomes if isinstance(outcome, ConversationStateError)]
    assert len(winners) == 1
    assert len(conflicts) == 19
    assert all(conflict.code == "CONTEXT_VERSION_CONFLICT" for conflict in conflicts)
    async with AsyncSessionLocal() as db:
        row = await ConversationStateRepository(db).get_session(
            tenant_id=TENANT_A,
            user_id=CONSULTA_A,
            public_session_id=public_id,
        )
        assert row is not None
        nodes = await ConversationStateRepository(db).list_nodes(
            tenant_id=TENANT_A,
            user_id=CONSULTA_A,
            session_id=row.id,
            after_sequence=None,
            limit=100,
        )
        sequences = [node.sequence_number for node in nodes]
        assert sequences == list(range(1, len(nodes) + 1))
        assert len(nodes) == 21


@pytest.mark.asyncio
async def test_thousand_nodes_append_and_keyset_pagination_remain_bounded() -> None:
    service = _service()
    row = await service.resolve_or_create_session(
        tenant_id=TENANT_A,
        user_id=CONSULTA_A,
        public_session_id=f"lumina-{uuid.uuid4()}",
    )
    protected = service.protector.protect("Evento sintetico de volume")
    started_at = time.perf_counter()
    async with AsyncSessionLocal() as db, db.begin():
        repo = ConversationStateRepository(db)
        locked = await repo.get_session_by_id(
            tenant_id=TENANT_A,
            user_id=CONSULTA_A,
            session_id=row.id,
            for_update=True,
        )
        assert locked is not None
        parent_id = None
        for _ in range(1000):
            node = await repo.append_node(
                row=locked,
                parent_node_id=parent_id,
                role="system",
                node_type="SYSTEM_EVENT",
                status="COMPLETED",
                base_context_version=0,
                content_ciphertext=protected.ciphertext,
                content_key_version=protected.key_version,
                content_fingerprint=protected.fingerprint,
            )
            parent_id = node.id
    append_seconds = time.perf_counter() - started_at
    assert append_seconds < 30

    async with AsyncSessionLocal() as db:
        repo = ConversationStateRepository(db)
        first = await repo.list_nodes(
            tenant_id=TENANT_A,
            user_id=CONSULTA_A,
            session_id=row.id,
            after_sequence=None,
            limit=100,
        )
        second = await repo.list_nodes(
            tenant_id=TENANT_A,
            user_id=CONSULTA_A,
            session_id=row.id,
            after_sequence=first[-1].sequence_number,
            limit=100,
        )
        assert [node.sequence_number for node in first] == list(range(1, 101))
        assert [node.sequence_number for node in second] == list(range(101, 201))
        assert await db.scalar(
            select(func.count()).select_from(ConversationNodeRecord).where(
                ConversationNodeRecord.session_id == row.id
            )
        ) == 1000


@pytest.mark.asyncio
async def test_invalid_parent_rolls_back_and_cross_user_mutations_are_hidden() -> None:
    service = _service()
    public_id = f"lumina-{uuid.uuid4()}"
    row = await service.resolve_or_create_session(
        tenant_id=TENANT_A, user_id=CONSULTA_A, public_session_id=public_id,
    )
    with pytest.raises(ConversationStateError) as invalid_parent:
        await service.start_turn(
            tenant_id=TENANT_A,
            user_id=CONSULTA_A,
            turn=ConversationTurnStart(
                public_session_id=public_id,
                client_message_id=uuid.uuid4(),
                parent_node_id=uuid.uuid4(),
                content="Parent inexistente",
            ),
        )
    assert invalid_parent.value.code == "INVALID_PARENT"
    async with AsyncSessionLocal() as db:
        assert await db.scalar(
            select(func.count()).select_from(ConversationNodeRecord).where(
                ConversationNodeRecord.session_id == row.id
            )
        ) == 0
    for action in ("archive", "delete", "reset"):
        with pytest.raises(ConversationStateError) as hidden:
            await service.mutate_session(
                tenant_id=TENANT_A,
                user_id=GESTOR_A,
                public_session_id=public_id,
                action=action,
                client_message_id=uuid.uuid4(),
            )
        assert hidden.value.code == "SESSION_NOT_FOUND"
