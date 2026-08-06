from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from contracts.dashboard_ai_assistance_v2 import (
    DashboardAiApplyRequestV2,
    DashboardAiAssistanceContextV2,
    DashboardAiAssistanceRequestV2,
    DashboardAiClarificationResponseV2,
    DashboardAiOperationV2,
    DashboardAiRequestOriginV2,
    DashboardAiReviseRequestV2,
)
from database import AsyncSessionLocal, engine
from services.dashboard_ai_assistance_v2.errors import DashboardAiAssistanceError
from services.dashboard_ai_assistance_v2.service import DashboardAiAssistanceServiceV2, DashboardAiProposalApplicationServiceV2
from services.dashboard_backend_v2 import DashboardActorContextV2
from testing.test_database import GESTOR_A, GESTOR_B, TENANT_A, TENANT_B


def _migration(version: int):
    path = Path(__file__).resolve().parents[1] / "database" / f"migration_v{version}_0.py"
    spec = importlib.util.spec_from_file_location(f"migration_v{version}_prompt22", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


@pytest_asyncio.fixture(autouse=True)
async def v22_v23_schema():
    v22, v23 = _migration(22), _migration(23)
    await v22.run_up(); await v23.run_up()
    async with engine.begin() as connection:
        names = ", ".join(f'"{name}"' for name in reversed(v23.TABLES + v22.TABLES))
        await connection.execute(text(f"TRUNCATE TABLE {names} CASCADE"))
    try:
        yield
    finally:
        await v23.run_down(confirm_test_only=True); await v22.run_down(confirm_test_only=True)


def _actor(tenant, user) -> DashboardActorContextV2:
    return DashboardActorContextV2(tenant_id=str(tenant), user_id=str(user), global_role="GESTOR")


def _request(text_value: str, request_id: str) -> DashboardAiAssistanceRequestV2:
    return DashboardAiAssistanceRequestV2(
        operation=DashboardAiOperationV2.CREATE_DASHBOARD,
        origin=DashboardAiRequestOriginV2.CREATION_WIZARD,
        instruction=text_value,
        context=DashboardAiAssistanceContextV2(),
        client_request_id=request_id,
    )


@pytest.mark.asyncio
async def test_proposal_human_acceptance_creates_draft_and_is_idempotent() -> None:
    actor = _actor(TENANT_A, GESTOR_A)
    async with AsyncSessionLocal() as session, session.begin():
        service = DashboardAiAssistanceServiceV2(session)
        request = _request("Painel de ticket médio por mês em julho", "request.postgres.001")
        proposal = await service.create(actor=actor, request=request, idempotency_key="proposal-create-0001")
        replay = await service.create(actor=actor, request=request, idempotency_key="proposal-create-0001")
        assert proposal.proposal_id == replay.proposal_id
        assert proposal.status.value == "READY_FOR_REVIEW"
        assert proposal.latest and proposal.latest.blueprint_proposal
        assert proposal.latest.blueprint_proposal.blueprint.lifecycle.value == "DRAFT"
        decision = await service.decide(actor=actor, proposal_id=proposal.proposal_id, version=proposal.current_version, decision="ACCEPT", comment="Confirmo a proposta governada.", expected_lock=proposal.lock_version, idempotency_key="proposal-accept-0001")
        assert decision.decision == "ACCEPT"
        accepted = await service.proposals.get(actor.tenant_id, proposal.proposal_id, user_id=actor.user_id)
        result = await DashboardAiProposalApplicationServiceV2(session).apply(
            actor=actor, proposal_id=proposal.proposal_id,
            request=DashboardAiApplyRequestV2(proposal_version=proposal.current_version, expected_lock_version=accepted.lock_version, confirmation="APPLY_ACCEPTED_DASHBOARD_AI_PROPOSAL"),
            idempotency_key="proposal-apply-0001",
        )
        assert result.status == "APPLIED"
        assert result.dashboard_id and result.revision_id
        stored = await service.proposals.get(actor.tenant_id, proposal.proposal_id, user_id=actor.user_id)
        assert stored.status == "APPLIED"


@pytest.mark.asyncio
async def test_clarification_is_typed_and_cross_tenant_is_hidden() -> None:
    actor = _actor(TENANT_A, GESTOR_A)
    async with AsyncSessionLocal() as session, session.begin():
        service = DashboardAiAssistanceServiceV2(session)
        proposal = await service.create(actor=actor, request=_request("Painel de faturamento", "request.postgres.002"), idempotency_key="proposal-create-0002")
        assert proposal.status.value == "NEEDS_CLARIFICATION"
        assert proposal.clarification
        question = proposal.clarification.questions[0]
        resolved = await service.answer_clarification(
            actor=actor, proposal_id=proposal.proposal_id,
            response=DashboardAiClarificationResponseV2(question_id=question.question_id, selected_option_ids=(question.options[0].option_id,), expected_lock_version=1),
        )
        assert resolved.status.value == "READY_FOR_REVIEW"
        with pytest.raises(DashboardAiAssistanceError, match="Proposta não encontrada"):
            await service.proposals.get(str(TENANT_B), proposal.proposal_id, user_id=str(GESTOR_B))


@pytest.mark.asyncio
async def test_cas_rejects_stale_decision_and_immutable_version_rejects_update() -> None:
    actor = _actor(TENANT_A, GESTOR_A)
    async with AsyncSessionLocal() as session, session.begin():
        service = DashboardAiAssistanceServiceV2(session)
        proposal = await service.create(actor=actor, request=_request("Painel de desconto total", "request.postgres.003"), idempotency_key="proposal-create-0003")
        with pytest.raises(DashboardAiAssistanceError, match="alterada por outro processo"):
            await service.proposals.transition_cas(
                tenant_id=actor.tenant_id, proposal_id=proposal.proposal_id,
                expected_lock=proposal.lock_version - 1, current_status="READY_FOR_REVIEW", target_status="ACCEPTED",
            )
    async with engine.begin() as connection:
        row_id = await connection.scalar(text("SELECT id FROM dashboard_ai_proposal_versions_v2 LIMIT 1"))
        if row_id is not None:
            with pytest.raises(DBAPIError):
                await connection.execute(text("UPDATE dashboard_ai_proposal_versions_v2 SET status='REJECTED' WHERE id=:id"), {"id": row_id})


@pytest.mark.asyncio
async def test_revision_appends_immutable_version_with_cas_and_replay() -> None:
    actor = _actor(TENANT_A, GESTOR_A)
    async with AsyncSessionLocal() as session, session.begin():
        service = DashboardAiAssistanceServiceV2(session)
        proposal = await service.create(
            actor=actor,
            request=_request("Painel de desconto total", "request.postgres.004"),
            idempotency_key="proposal-create-0004",
        )
        request = DashboardAiReviseRequestV2(
            instruction="Painel de ticket médio em julho",
            expected_proposal_version=proposal.current_version,
            expected_lock_version=proposal.lock_version,
            client_request_id="request.revise.004",
        )
        revised = await service.revise(
            actor=actor, proposal_id=proposal.proposal_id, request=request,
            idempotency_key="proposal-revise-0004",
        )
        assert revised.current_version == 2
        assert revised.status.value == "READY_FOR_REVIEW"
        assert revised.latest and revised.latest.version == 2
        replay = await service.revise(
            actor=actor, proposal_id=proposal.proposal_id, request=request,
            idempotency_key="proposal-revise-0004",
        )
        assert replay.current_version == 2
        count = await session.scalar(
            text("SELECT count(*) FROM dashboard_ai_proposal_versions_v2 WHERE proposal_id=:id"),
            {"id": uuid.UUID(proposal.proposal_id)},
        )
        assert count == 2
