from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.dashboard_ai_assistance_v2 import (
    DashboardAiAuditEventModelV2,
    DashboardAiClarificationModelV2,
    DashboardAiDecisionModelV2,
    DashboardAiEvidenceModelV2,
    DashboardAiProposalModelV2,
    DashboardAiProposalVersionModelV2,
    DashboardAiRunModelV2,
)

from .errors import DashboardAiAssistanceError


class DashboardAiProposalRepositoryV2:
    def __init__(self, session: AsyncSession): self.session = session

    async def create(self, **values) -> DashboardAiProposalModelV2:
        row = DashboardAiProposalModelV2(**values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def get(self, tenant_id: str, proposal_id: str, *, user_id: str | None = None) -> DashboardAiProposalModelV2:
        clauses = [DashboardAiProposalModelV2.tenant_id == uuid.UUID(tenant_id), DashboardAiProposalModelV2.id == uuid.UUID(proposal_id)]
        if user_id is not None:
            clauses.append(DashboardAiProposalModelV2.created_by_user_id == uuid.UUID(user_id))
        row = await self.session.scalar(select(DashboardAiProposalModelV2).where(*clauses))
        if row is None:
            raise DashboardAiAssistanceError("DASHBOARD_AI_PROPOSAL_NOT_FOUND", "Proposta não encontrada.", 404)
        return row

    async def find_replay(self, tenant_id: str, scope: str, request_checksum: str) -> DashboardAiProposalModelV2 | None:
        row = await self.session.scalar(select(DashboardAiProposalModelV2).where(DashboardAiProposalModelV2.tenant_id == uuid.UUID(tenant_id), DashboardAiProposalModelV2.idempotency_scope == scope))
        if row and row.request_checksum != request_checksum:
            raise DashboardAiAssistanceError("DASHBOARD_AI_IDEMPOTENCY_CONFLICT", "Chave de idempotência reutilizada com outro payload.", 409)
        return row

    async def transition_cas(self, *, tenant_id: str, proposal_id: str, expected_lock: int, current_status: str, target_status: str, **extra) -> DashboardAiProposalModelV2:
        values = {"status": target_status, "lock_version": expected_lock + 1, "updated_at": datetime.now(timezone.utc), **extra}
        result = await self.session.execute(update(DashboardAiProposalModelV2).where(
            DashboardAiProposalModelV2.tenant_id == uuid.UUID(tenant_id), DashboardAiProposalModelV2.id == uuid.UUID(proposal_id),
            DashboardAiProposalModelV2.lock_version == expected_lock, DashboardAiProposalModelV2.status == current_status,
        ).values(**values).returning(DashboardAiProposalModelV2))
        row = result.scalar_one_or_none()
        if row is None:
            raise DashboardAiAssistanceError("DASHBOARD_AI_VERSION_CONFLICT", "A proposta foi alterada por outro processo.", 409)
        return row

    async def begin_revision_cas(
        self,
        *,
        tenant_id: str,
        proposal_id: str,
        expected_lock: int,
        expected_version: int,
        instruction_fingerprint: str,
        intent_json: dict[str, object],
    ) -> DashboardAiProposalModelV2:
        result = await self.session.execute(
            update(DashboardAiProposalModelV2)
            .where(
                DashboardAiProposalModelV2.tenant_id == uuid.UUID(tenant_id),
                DashboardAiProposalModelV2.id == uuid.UUID(proposal_id),
                DashboardAiProposalModelV2.lock_version == expected_lock,
                DashboardAiProposalModelV2.current_version == expected_version,
                DashboardAiProposalModelV2.status == "READY_FOR_REVIEW",
            )
            .values(
                status="ANALYZING",
                current_version=expected_version + 1,
                lock_version=expected_lock + 1,
                instruction_fingerprint=instruction_fingerprint,
                intent_json=intent_json,
                updated_at=datetime.now(timezone.utc),
            )
            .returning(DashboardAiProposalModelV2)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise DashboardAiAssistanceError(
                "DASHBOARD_AI_REVISION_STALE",
                "A proposta foi alterada antes da revisÃ£o.",
                409,
            )
        return row

    async def list(self, tenant_id: str, user_id: str, *, limit: int, cursor: str | None = None) -> tuple[DashboardAiProposalModelV2, ...]:
        statement = select(DashboardAiProposalModelV2).where(DashboardAiProposalModelV2.tenant_id == uuid.UUID(tenant_id), DashboardAiProposalModelV2.created_by_user_id == uuid.UUID(user_id))
        if cursor:
            cursor_id = uuid.UUID(cursor)
            statement = statement.where(DashboardAiProposalModelV2.id < cursor_id)
        rows = await self.session.scalars(statement.order_by(DashboardAiProposalModelV2.id.desc()).limit(limit))
        return tuple(rows)


class DashboardAiProposalVersionRepositoryV2:
    def __init__(self, session: AsyncSession): self.session = session

    async def append(self, **values) -> DashboardAiProposalVersionModelV2:
        row = DashboardAiProposalVersionModelV2(**values); self.session.add(row); await self.session.flush(); return row

    async def latest(self, tenant_id: str, proposal_id: str) -> DashboardAiProposalVersionModelV2 | None:
        return await self.session.scalar(select(DashboardAiProposalVersionModelV2).where(
            DashboardAiProposalVersionModelV2.tenant_id == uuid.UUID(tenant_id), DashboardAiProposalVersionModelV2.proposal_id == uuid.UUID(proposal_id),
        ).order_by(DashboardAiProposalVersionModelV2.version.desc()).limit(1))

    async def get(self, tenant_id: str, proposal_id: str, version: int) -> DashboardAiProposalVersionModelV2:
        row = await self.session.scalar(select(DashboardAiProposalVersionModelV2).where(
            DashboardAiProposalVersionModelV2.tenant_id == uuid.UUID(tenant_id), DashboardAiProposalVersionModelV2.proposal_id == uuid.UUID(proposal_id), DashboardAiProposalVersionModelV2.version == version,
        ))
        if row is None: raise DashboardAiAssistanceError("DASHBOARD_AI_PROPOSAL_VERSION_NOT_FOUND", "Versão da proposta não encontrada.", 404)
        return row


class DashboardAiClarificationRepositoryV2:
    def __init__(self, session: AsyncSession): self.session = session
    async def create(self, **values) -> DashboardAiClarificationModelV2:
        row = DashboardAiClarificationModelV2(**values); self.session.add(row); await self.session.flush(); return row
    async def open_for(self, tenant_id: str, proposal_id: str) -> tuple[DashboardAiClarificationModelV2, ...]:
        rows = await self.session.scalars(select(DashboardAiClarificationModelV2).where(
            DashboardAiClarificationModelV2.tenant_id == uuid.UUID(tenant_id), DashboardAiClarificationModelV2.proposal_id == uuid.UUID(proposal_id), DashboardAiClarificationModelV2.status == "OPEN",
        ).order_by(DashboardAiClarificationModelV2.created_at, DashboardAiClarificationModelV2.id))
        return tuple(rows)
    async def answer_cas(self, *, tenant_id: str, proposal_id: str, clarification_id: str, expected_lock: int, user_id: str, response_json: dict[str, object]) -> DashboardAiClarificationModelV2:
        result = await self.session.execute(update(DashboardAiClarificationModelV2).where(
            DashboardAiClarificationModelV2.tenant_id == uuid.UUID(tenant_id), DashboardAiClarificationModelV2.proposal_id == uuid.UUID(proposal_id), DashboardAiClarificationModelV2.id == uuid.UUID(clarification_id),
            DashboardAiClarificationModelV2.status == "OPEN", DashboardAiClarificationModelV2.lock_version == expected_lock, DashboardAiClarificationModelV2.expires_at > datetime.now(timezone.utc),
        ).values(status="ANSWERED", response_json=response_json, answered_by_user_id=uuid.UUID(user_id), answered_at=datetime.now(timezone.utc), lock_version=expected_lock + 1).returning(DashboardAiClarificationModelV2))
        row = result.scalar_one_or_none()
        if row is None: raise DashboardAiAssistanceError("DASHBOARD_AI_CLARIFICATION_STALE", "Esclarecimento expirado ou obsoleto.", 409)
        return row


class DashboardAiEvidenceRepositoryV2:
    def __init__(self, session: AsyncSession): self.session = session
    async def append(self, **values) -> DashboardAiEvidenceModelV2:
        row = DashboardAiEvidenceModelV2(**values); self.session.add(row); await self.session.flush(); return row
    async def list(self, tenant_id: str, proposal_id: str) -> tuple[DashboardAiEvidenceModelV2, ...]:
        rows = await self.session.scalars(select(DashboardAiEvidenceModelV2).where(DashboardAiEvidenceModelV2.tenant_id == uuid.UUID(tenant_id), DashboardAiEvidenceModelV2.proposal_id == uuid.UUID(proposal_id)).order_by(DashboardAiEvidenceModelV2.proposal_version, DashboardAiEvidenceModelV2.id))
        return tuple(rows)


class DashboardAiDecisionRepositoryV2:
    def __init__(self, session: AsyncSession): self.session = session
    async def append(self, **values) -> DashboardAiDecisionModelV2:
        row = DashboardAiDecisionModelV2(**values); self.session.add(row); await self.session.flush(); return row
    async def for_version(self, tenant_id: str, proposal_id: str, version: int) -> DashboardAiDecisionModelV2 | None:
        return await self.session.scalar(select(DashboardAiDecisionModelV2).where(DashboardAiDecisionModelV2.tenant_id == uuid.UUID(tenant_id), DashboardAiDecisionModelV2.proposal_id == uuid.UUID(proposal_id), DashboardAiDecisionModelV2.proposal_version == version))


class DashboardAiRunRepositoryV2:
    def __init__(self, session: AsyncSession): self.session = session
    async def append(self, **values) -> DashboardAiRunModelV2:
        row = DashboardAiRunModelV2(**values); self.session.add(row); await self.session.flush(); return row


class DashboardAiAuditRepositoryV2:
    def __init__(self, session: AsyncSession): self.session = session
    async def append(self, **values) -> DashboardAiAuditEventModelV2:
        row = DashboardAiAuditEventModelV2(**values); self.session.add(row); await self.session.flush(); return row
    async def list(self, tenant_id: str, proposal_id: str) -> tuple[DashboardAiAuditEventModelV2, ...]:
        rows = await self.session.scalars(select(DashboardAiAuditEventModelV2).where(DashboardAiAuditEventModelV2.tenant_id == uuid.UUID(tenant_id), DashboardAiAuditEventModelV2.proposal_id == uuid.UUID(proposal_id)).order_by(DashboardAiAuditEventModelV2.occurred_at, DashboardAiAuditEventModelV2.id))
        return tuple(rows)


class DashboardAiEvaluationRepositoryV2:
    def __init__(self, session: AsyncSession): self.session = session
