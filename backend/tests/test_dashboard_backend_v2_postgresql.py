from __future__ import annotations

import importlib.util
import inspect as pyinspect
import json
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError

from contracts.dashboard_backend_v2 import (
    DashboardCacheIndicatorV2,
    DashboardArchiveRequestV2,
    DashboardCloneRequestV2,
    DashboardCollaboratorCreateRequestV2,
    DashboardCollaboratorRoleV2,
    DashboardCreateRequestV2,
    DashboardPublicationRequestV2,
    DashboardRevisionCreateRequestV2,
    DashboardRollbackRequestV2,
    DashboardRuntimeRequestV2,
    DashboardRuntimeStatusV2,
    DashboardScalarDataV2,
    DashboardUpdateDraftRequestV2,
    DashboardVisualPatchRequestV2,
)
from contracts.dashboard_blueprint_v2 import DashboardOriginV2, DashboardVisualPatchV2
from database import AsyncSessionLocal, engine
from services.dashboard_backend_v2.application import (
    DashboardActorContextV2,
    DashboardAuthoringServiceV2,
    DashboardPublicationServiceV2,
    DashboardRevisionServiceV2,
    DashboardReviewServiceV2,
    DashboardRollbackServiceV2,
    DashboardEvaluationServiceV2,
    DashboardCloneServiceV2,
    DashboardPatchServiceV2,
)
from services.dashboard_backend_v2.collaboration import DashboardAccessServiceV2
from services.dashboard_backend_v2.errors import DashboardBackendError
from services.dashboard_backend_v2.repositories import DashboardRepositoryV2
from services.dashboard_backend_v2.runtime import CertifiedWidgetPayloadV2, DashboardRuntimeExecutionServiceV2
from services.dashboard_blueprint_v2.fixtures import build_executive_dashboard, golden_cases
from testing.test_database import ADMIN_A, ADMIN_B, CONSULTA_A, CONSULTA_B, GESTOR_A, TENANT_A, TENANT_B, TECH_ADMIN_A


def _migration():
    path = Path(__file__).resolve().parents[1] / "database" / "migration_v22_0.py"
    spec = importlib.util.spec_from_file_location("migration_v22_0_integration", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _migration_version(version: int):
    path = Path(__file__).resolve().parents[1] / "database" / f"migration_v{version}_0.py"
    spec = importlib.util.spec_from_file_location(f"migration_v{version}_chain_prompt20", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def _run_down(module) -> None:
    parameters = pyinspect.signature(module.run_down).parameters
    if "confirm_test_only" in parameters:
        await module.run_down(confirm_test_only=True)
    else:
        await module.run_down()


@pytest_asyncio.fixture(autouse=True)
async def v22_schema():
    migration = _migration()
    await migration.run_up()
    async with engine.begin() as connection:
        names = ", ".join(f'"{name}"' for name in reversed(migration.TABLES))
        await connection.execute(text(f"TRUNCATE TABLE {names} CASCADE"))
    try:
        yield migration
    finally:
        v23 = _migration_version(23)
        await _run_down(v23)
        await migration.run_down(confirm_test_only=True)
        await migration.run_up()
        await v23.run_up()


def _actor(tenant: uuid.UUID, user: uuid.UUID, role: str) -> DashboardActorContextV2:
    return DashboardActorContextV2(tenant_id=str(tenant), user_id=str(user), global_role=role)


async def _create_dashboard(session, *, actor=None, suffix="primary"):
    actor = actor or _actor(TENANT_A, GESTOR_A, "GESTOR")
    blueprint = build_executive_dashboard()
    if suffix != "primary":
        identity = blueprint.identity.model_copy(update={"blueprint_id": f"dashboard.synthetic.{suffix}", "canonical_name": f"dashboard.synthetic.{suffix}"})
        blueprint = blueprint.model_copy(update={"identity": identity})
    request = DashboardCreateRequestV2(
        canonical_name=blueprint.identity.canonical_name, title=blueprint.identity.title,
        description=blueprint.identity.description, blueprint=blueprint,
        origin=DashboardOriginV2.HUMAN_AUTHORED, reason="Fixture sintética governada",
    )
    return await DashboardAuthoringServiceV2(session).create(actor=actor, request=request, idempotency_key=f"create-{suffix}-0001")


async def _approve_and_publish(session, created, *, version="1.0.0", generation=0):
    owner = _actor(TENANT_A, GESTOR_A, "GESTOR")
    reviewer = _actor(TENANT_A, TECH_ADMIN_A, "ADMIN")
    await DashboardReviewServiceV2(session).decide(actor=owner, dashboard_id=created.dashboard.identity.dashboard_id, revision_id=created.revision.revision_id, expected_lock=created.dashboard.lock_version, action="SUBMITTED", comment="Submeter revisão sintética", idempotency_key=f"review-{version}-0001")
    approval = await DashboardReviewServiceV2(session).decide(actor=reviewer, dashboard_id=created.dashboard.identity.dashboard_id, revision_id=created.revision.revision_id, expected_lock=created.dashboard.lock_version + 1, action="APPROVED", comment="Aprovação independente sintética", idempotency_key=f"approve-{version}-0001")
    assert approval is not None
    result = await DashboardPublicationServiceV2(session).publish(actor=reviewer, dashboard_id=created.dashboard.identity.dashboard_id, request=DashboardPublicationRequestV2(revision_id=created.revision.revision_id, expected_dashboard_lock_version=created.dashboard.lock_version + 2, expected_active_generation=generation, publication_version=version, confirmation="PUBLISH_APPROVED_REVISION"), idempotency_key=f"publish-{version}-0001")
    return result


class _FakeWidgetAuthority:
    def __init__(self, fail_widget: str | None = None):
        self.fail_widget = fail_widget
        self.calls: list[str] = []

    async def execute(self, *, actor, plan):
        self.calls.append(plan.widget_id)
        if plan.widget_id == self.fail_widget:
            raise DashboardBackendError("DASHBOARD_WIDGET_EXECUTION_FAILED", "Falha sintética", 503)
        from decimal import Decimal
        return CertifiedWidgetPayloadV2(
            data=DashboardScalarDataV2(value=Decimal("300.00"), unit="BRL", currency="BRL"),
            fact_references=(f"fact.{plan.widget_id}",), certification_reference=f"cert.{plan.widget_id}",
            source_freshness="2026-07-31", warnings=(), cache_indicator=DashboardCacheIndicatorV2.MISS,
        )


@pytest.mark.asyncio
async def test_migration_up_second_up_schema_indexes_and_down(v22_schema) -> None:
    second = await v22_schema.run_up()
    assert second["status"] == "SUCCESS"
    async with engine.connect() as connection:
        tables = await connection.run_sync(lambda sync: set(inspect(sync).get_table_names()))
        assert set(v22_schema.TABLES).issubset(tables)
        indexes = await connection.run_sync(lambda sync: {name: inspect(sync).get_indexes(name) for name in v22_schema.TABLES})
        assert all(indexes[name] for name in v22_schema.TABLES if name not in {"dashboard_access_policies_v2"})
    try:
        v23 = _migration_version(23)
        await _run_down(v23)
        down = await v22_schema.run_down(confirm_test_only=True)
        assert down["status"] == "SUCCESS"
    finally:
        await v22_schema.run_up()
        v23 = _migration_version(23)
        await v23.run_up()


from testing.test_database import reset_and_seed_test_database


@pytest.mark.asyncio
async def test_complete_chain_v22_to_v12_and_v12_to_v22() -> None:
    modules = {version: _migration_version(version) for version in range(13, 24)}
    try:
        for version in range(13, 24):
            await modules[version].run_up()
        for version in range(23, 12, -1):
            await _run_down(modules[version])
    finally:
        for version in range(13, 24):
            await modules[version].run_up()
        await reset_and_seed_test_database(engine)

    async with engine.connect() as connection:
        tables = await connection.run_sync(lambda sync: set(inspect(sync).get_table_names()))
    assert set(modules[22].TABLES) <= tables
    assert "smart_cache_entries" in tables
    assert "validation_policies" in tables


@pytest.mark.asyncio
async def test_create_revision_review_approval_publication_and_idempotency() -> None:
    async with AsyncSessionLocal() as session:
        created = await _create_dashboard(session)
        replay = await _create_dashboard(session)
        assert replay.replayed is True
        assert replay.dashboard.identity.dashboard_id == created.dashboard.identity.dashboard_id
        assert created.dashboard.lifecycle.value == "DRAFT"
        assert created.dashboard.head_lifecycle.value == "DRAFT"
        published = await _approve_and_publish(session, created)
        await session.commit()
        assert published.publication.generation == 1
        assert published.publication.status == "PUBLISHED"
        assert published.publication.revision.blueprint_checksum == created.revision.blueprint_checksum


@pytest.mark.asyncio
async def test_second_revision_supersession_and_rollback_create_new_publication() -> None:
    async with AsyncSessionLocal() as session:
        created = await _create_dashboard(session)
        first = await _approve_and_publish(session, created)
        dashboard = await DashboardRepositoryV2(session).get(str(TENANT_A), created.dashboard.identity.dashboard_id)
        blueprint = created.revision.blueprint
        revised = blueprint.model_copy(update={
            "identity": blueprint.identity.model_copy(update={"title": "Executivo revisado"}),
            "version": blueprint.version.model_copy(update={"revision": blueprint.version.revision.model_copy(update={"visual_revision": 2})}),
        })
        row, draft, _ = await DashboardRevisionServiceV2(session).create(actor=_actor(TENANT_A, GESTOR_A, "GESTOR"), dashboard=dashboard, request=DashboardRevisionCreateRequestV2(blueprint=revised, base_revision_id=created.revision.revision_id, expected_dashboard_lock_version=dashboard.lock_version, reason="Nova revisão visual"), idempotency_key="second-revision-0001")
        assert draft.lifecycle == "PUBLISHED" and draft.head_lifecycle == "DRAFT"
        second_created = created.model_copy(update={"dashboard": created.dashboard.model_copy(update={"lock_version": draft.lock_version}), "revision": __import__("services.dashboard_backend_v2.application", fromlist=["revision_contract"]).revision_contract(row)})
        second = await _approve_and_publish(session, second_created, version="2.0.0", generation=1)
        current = await DashboardRepositoryV2(session).get(str(TENANT_A), created.dashboard.identity.dashboard_id)
        rollback = await DashboardRollbackServiceV2(session).rollback(actor=_actor(TENANT_A, TECH_ADMIN_A, "ADMIN"), dashboard_id=created.dashboard.identity.dashboard_id, request=DashboardRollbackRequestV2(target_publication_id=first.publication.publication_id, expected_dashboard_lock_version=current.lock_version, expected_active_generation=2, publication_version="3.0.0", confirmation="CREATE_ROLLBACK_PUBLICATION", reason="Rollback sintético validado"), idempotency_key="rollback-0001")
        await session.commit()
        assert second.superseded_publication_id == first.publication.publication_id
        assert rollback.publication.generation == 3
        assert rollback.publication.publication_id != first.publication.publication_id
        assert rollback.publication.revision.revision_id == first.publication.revision.revision_id


@pytest.mark.asyncio
async def test_cross_tenant_is_not_disclosed_and_collaborator_fk_is_tenant_scoped() -> None:
    async with AsyncSessionLocal() as session:
        created = await _create_dashboard(session)
        with pytest.raises(DashboardBackendError) as hidden:
            await DashboardRepositoryV2(session).get(str(TENANT_B), created.dashboard.identity.dashboard_id)
        assert hidden.value.code == "DASHBOARD_NOT_FOUND"
        with pytest.raises(DashboardBackendError) as cross_collaborator:
            await DashboardAccessServiceV2(session).add(actor=_actor(TENANT_A, ADMIN_A, "ADMIN"), dashboard_id=created.dashboard.identity.dashboard_id, request=DashboardCollaboratorCreateRequestV2(user_reference=str(CONSULTA_B), role=DashboardCollaboratorRoleV2.VIEWER))
        assert cross_collaborator.value.code == "DASHBOARD_NOT_FOUND"
        valid = await DashboardAccessServiceV2(session).add(actor=_actor(TENANT_A, ADMIN_A, "ADMIN"), dashboard_id=created.dashboard.identity.dashboard_id, request=DashboardCollaboratorCreateRequestV2(user_reference=str(CONSULTA_A), role=DashboardCollaboratorRoleV2.VIEWER))
        assert valid.user_reference == str(CONSULTA_A)


@pytest.mark.asyncio
async def test_revision_and_publication_rows_are_database_immutable() -> None:
    async with AsyncSessionLocal() as session:
        created = await _create_dashboard(session)
        published = await _approve_and_publish(session, created)
        await session.commit()
    with pytest.raises(DBAPIError):
        async with engine.begin() as connection:
            await connection.execute(text("UPDATE dashboard_revisions_v2 SET reason='mutated' WHERE id=:id"), {"id": uuid.UUID(created.revision.revision_id)})
    with pytest.raises(DBAPIError):
        async with engine.begin() as connection:
            await connection.execute(text("DELETE FROM dashboard_publications_v2 WHERE id=:id"), {"id": uuid.UUID(published.publication.publication_id)})


@pytest.mark.asyncio
async def test_stale_cas_loses_without_silent_overwrite() -> None:
    async with AsyncSessionLocal() as session:
        created = await _create_dashboard(session)
        repository = DashboardRepositoryV2(session)
        updated = await repository.update_metadata_cas(str(TENANT_A), created.dashboard.identity.dashboard_id, created.dashboard.lock_version, title="Primeiro vencedor", description=None)
        assert updated.title == "Primeiro vencedor"
        with pytest.raises(DashboardBackendError) as stale:
            await repository.update_metadata_cas(str(TENANT_A), created.dashboard.identity.dashboard_id, created.dashboard.lock_version, title="Perdedor obsoleto", description=None)
        assert stale.value.code == "DASHBOARD_VERSION_CONFLICT"


@pytest.mark.asyncio
async def test_runtime_decimal_certification_and_execution_metadata() -> None:
    async with AsyncSessionLocal() as session:
        created = await _create_dashboard(session)
        await _approve_and_publish(session, created)
        authority = _FakeWidgetAuthority()
        result = await DashboardRuntimeExecutionServiceV2(session, authority).execute(
            actor=_actor(TENANT_A, ADMIN_A, "ADMIN"), dashboard_id=created.dashboard.identity.dashboard_id,
            request=DashboardRuntimeRequestV2(requested_widget_ids=("widget.revenue",)),
            idempotency_key="runtime-decimal-0001",
        )
        await session.commit()
        assert result.status.value == "COMPLETE"
        assert result.widgets[0].data.value.is_finite()  # type: ignore[union-attr]
        assert str(result.widgets[0].data.value) == "300.00"  # type: ignore[union-attr]
        assert result.widgets[0].certification_reference
        assert authority.calls == ["widget.revenue"]


@pytest.mark.asyncio
async def test_runtime_partial_preserves_valid_widgets_without_synthesizing_zero() -> None:
    async with AsyncSessionLocal() as session:
        created = await _create_dashboard(session)
        await _approve_and_publish(session, created)
        authority = _FakeWidgetAuthority(fail_widget="widget.average.ticket")
        result = await DashboardRuntimeExecutionServiceV2(session, authority).execute(
            actor=_actor(TENANT_A, ADMIN_A, "ADMIN"), dashboard_id=created.dashboard.identity.dashboard_id,
            request=DashboardRuntimeRequestV2(requested_widget_ids=("widget.revenue", "widget.average.ticket"), allow_partial=True),
            idempotency_key="runtime-partial-0001",
        )
        assert result.status.value == "PARTIAL"
        assert [item.widget_id for item in result.widgets] == ["widget.revenue"]
        assert result.warnings[0].code == "WIDGET_UNAVAILABLE"


@pytest.mark.asyncio
async def test_evaluation_tables_have_a_tenant_scoped_service_consumer() -> None:
    async with AsyncSessionLocal() as session:
        service = DashboardEvaluationServiceV2(session)
        case = await service.create_case(
            tenant_id=str(TENANT_A), case_key="runtime-complete-001",
            name="Runtime completo sintético", category="RUNTIME",
            fixture={"dashboard": "synthetic"},
            expected_status=DashboardRuntimeStatusV2.COMPLETE,
        )
        result = await service.record_result(
            tenant_id=str(TENANT_A), case_id=case.case_id,
            actual_status=DashboardRuntimeStatusV2.COMPLETE,
            evidence={"status": "COMPLETE"},
        )
        await session.commit()
        assert result.passed is True
        with pytest.raises(DashboardBackendError) as hidden:
            await service.record_result(
                tenant_id=str(TENANT_B), case_id=case.case_id,
                actual_status=DashboardRuntimeStatusV2.COMPLETE,
                evidence={"status": "COMPLETE"},
            )
        assert hidden.value.code == "DASHBOARD_NOT_FOUND"


@pytest.mark.asyncio
async def test_update_draft_is_idempotent_without_extra_lock_increment() -> None:
    async with AsyncSessionLocal() as session:
        created = await _create_dashboard(session)
        request = DashboardUpdateDraftRequestV2(
            expected_lock_version=created.dashboard.lock_version,
            title="Executivo visual revisado", reason="Atualização visual sintética",
        )
        service = DashboardAuthoringServiceV2(session)
        first = await service.update_draft(
            actor=_actor(TENANT_A, GESTOR_A, "GESTOR"),
            dashboard_id=created.dashboard.identity.dashboard_id,
            request=request, idempotency_key="update-draft-idem-0001",
        )
        second = await service.update_draft(
            actor=_actor(TENANT_A, GESTOR_A, "GESTOR"),
            dashboard_id=created.dashboard.identity.dashboard_id,
            request=request, idempotency_key="update-draft-idem-0001",
        )
        assert second.replayed is True
        assert second.revision.revision_id == first.revision.revision_id
        assert second.dashboard.lock_version == first.dashboard.lock_version


@pytest.mark.asyncio
async def test_visual_collaborator_can_patch_but_cannot_change_semantics() -> None:
    async with AsyncSessionLocal() as session:
        created = await _create_dashboard(session)
        collaborator = _actor(TENANT_A, CONSULTA_A, "GESTOR")
        await DashboardAccessServiceV2(session).add(
            actor=_actor(TENANT_A, ADMIN_A, "ADMIN"),
            dashboard_id=created.dashboard.identity.dashboard_id,
            request=DashboardCollaboratorCreateRequestV2(
                user_reference=str(CONSULTA_A),
                role=DashboardCollaboratorRoleV2.EDITOR_VISUAL,
            ),
        )
        raw_patch = golden_cases()["12_valid_visual_patch"]["payload"]
        request = DashboardVisualPatchRequestV2(
            patch=DashboardVisualPatchV2.model_validate_json(json.dumps(raw_patch)),
            expected_dashboard_lock_version=created.dashboard.lock_version,
            expected_revision_lock_version=created.revision.lock_version,
            reason="Patch visual por colaborador sintético",
        )
        revised = await DashboardPatchServiceV2(session).apply_visual(
            actor=collaborator, dashboard_id=created.dashboard.identity.dashboard_id,
            request=request, idempotency_key="visual-collaborator-0001",
        )
        replay = await DashboardPatchServiceV2(session).apply_visual(
            actor=collaborator, dashboard_id=created.dashboard.identity.dashboard_id,
            request=request, idempotency_key="visual-collaborator-0001",
        )
        assert revised.semantic.checksum == created.revision.semantic.checksum
        assert replay.revision_id == revised.revision_id


@pytest.mark.asyncio
async def test_clone_is_idempotent_and_archive_blocks_published_runtime() -> None:
    async with AsyncSessionLocal() as session:
        created = await _create_dashboard(session)
        await _approve_and_publish(session, created)
        clone_request = DashboardCloneRequestV2(
            canonical_name="dashboard.synthetic.cloned", title="Clone sintético",
            description="Clone governado para teste sintético.",
            reason="Validar clone sem autoridade herdada",
        )
        clone_service = DashboardCloneServiceV2(session)
        first_clone = await clone_service.clone(
            actor=_actor(TENANT_A, GESTOR_A, "GESTOR"),
            dashboard_id=created.dashboard.identity.dashboard_id,
            request=clone_request, idempotency_key="clone-idem-0001",
        )
        replay_clone = await clone_service.clone(
            actor=_actor(TENANT_A, GESTOR_A, "GESTOR"),
            dashboard_id=created.dashboard.identity.dashboard_id,
            request=clone_request, idempotency_key="clone-idem-0001",
        )
        assert replay_clone.replayed is True
        assert replay_clone.dashboard.identity.dashboard_id == first_clone.dashboard.identity.dashboard_id
        assert first_clone.dashboard.lifecycle.value == "DRAFT"
        current = await DashboardRepositoryV2(session).get(
            str(TENANT_A), created.dashboard.identity.dashboard_id
        )
        archived = await DashboardAuthoringServiceV2(session).archive(
            actor=_actor(TENANT_A, ADMIN_A, "ADMIN"),
            dashboard_id=created.dashboard.identity.dashboard_id,
            request=DashboardArchiveRequestV2(
                expected_dashboard_lock_version=current.lock_version,
                confirmation="ARCHIVE_DASHBOARD", reason="Archive sintético governado",
            ),
            idempotency_key="archive-idem-0001",
        )
        assert archived.lifecycle.value == "ARCHIVED"
        with pytest.raises(DashboardBackendError) as unavailable:
            await DashboardRuntimeExecutionServiceV2(session, _FakeWidgetAuthority()).execute(
                actor=_actor(TENANT_A, ADMIN_A, "ADMIN"),
                dashboard_id=created.dashboard.identity.dashboard_id,
                request=DashboardRuntimeRequestV2(requested_widget_ids=("widget.revenue",)),
                idempotency_key="runtime-archived-0001",
            )
        assert unavailable.value.code == "DASHBOARD_RUNTIME_UNAVAILABLE"
