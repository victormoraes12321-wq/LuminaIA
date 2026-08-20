from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from contracts.supervised_feedback_v2 import (
    CandidateStatus,
    DatasetStatus,
    FeedbackCategoryV2,
    FeedbackCorrectionV2,
    FeedbackLifecycle,
    FeedbackReviewDecisionV2,
    FeedbackSubmissionV2,
    FeedbackTargetV2,
)
from contracts.supervised_feedback_v2.models import (
    FreeTextExplanationCorrectionV2,
)
from database import AsyncSessionLocal
from models.conversation_state import ConversationNodeRecord, ConversationSession
from models.supervised_feedback import GovernedFeedbackEvent, GovernedFeedbackRecord
from models.user import User
from services.conversation_state.content_protector import ConversationContentProtector
from services.supervised_feedback.checksums import content_sha256
from services.supervised_feedback.errors import (
    FeedbackSelfReviewForbiddenError,
    FeedbackTargetNotFoundError,
    TrainingCandidateInvalidError,
)
from services.supervised_feedback.service import GovernedFeedbackService, utc_now


pytestmark = [pytest.mark.integration, pytest.mark.database, pytest.mark.security]


async def seeded_user(db, email: str) -> User:
    user = (
        await db.execute(select(User).where(User.email == email))
    ).scalar_one()
    return user


async def create_target(db, *, user: User) -> tuple[FeedbackTargetV2, ConversationContentProtector]:
    protector = ConversationContentProtector(
        key="MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
        persist_content=True,
        max_content_bytes=12000,
    )
    public_id = f"lumina-{uuid.uuid4()}"
    session = ConversationSession(
        public_session_id=public_id,
        tenant_id=user.tenant_id,
        user_id=user.id,
        expires_at=utc_now() + timedelta(days=1),
    )
    db.add(session)
    await db.flush()
    protected_query = protector.protect("Qual foi o faturamento de julho de 2026?")
    query = ConversationNodeRecord(
        session_id=session.id,
        tenant_id=user.tenant_id,
        user_id=user.id,
        sequence_number=1,
        role="user",
        node_type="USER_QUERY",
        status="COMPLETED",
        content_ciphertext=protected_query.ciphertext,
        content_key_version=protected_query.key_version,
        content_fingerprint=protected_query.fingerprint,
        base_context_version=0,
        completed_at=utc_now(),
    )
    db.add(query)
    await db.flush()
    protected_response = protector.protect("O faturamento validado foi apresentado no painel.")
    response_checksum = "a" * 64
    response = ConversationNodeRecord(
        session_id=session.id,
        tenant_id=user.tenant_id,
        user_id=user.id,
        sequence_number=2,
        parent_node_id=query.id,
        role="assistant",
        node_type="ASSISTANT_RESPONSE",
        status="COMPLETED",
        content_ciphertext=protected_response.ciphertext,
        content_key_version=protected_response.key_version,
        content_fingerprint=protected_response.fingerprint,
        response_fingerprint=response_checksum,
        base_context_version=0,
        completed_at=utc_now(),
    )
    db.add(response)
    session.next_sequence = 3
    session.active_head_node_id = response.id
    await db.flush()
    return (
        FeedbackTargetV2(
            response_node_id=response.id,
            session_id=public_id,
            response_checksum=response_checksum,
            query_node_id=query.id,
        ),
        protector,
    )


def submission(target: FeedbackTargetV2, key: str = "idempotency-0001") -> FeedbackSubmissionV2:
    explanation = "O total parece incorreto e precisa de conferência."
    return FeedbackSubmissionV2(
        target=target,
        category=FeedbackCategoryV2.INCORRECT_VALUE,
        correction=FeedbackCorrectionV2(
            items=[FreeTextExplanationCorrectionV2(explanation=explanation)]
        ),
        explanation=explanation,
        idempotency_key=key,
    )


@pytest.mark.asyncio
async def test_feedback_end_to_end_review_candidate_dataset_and_export() -> None:
    async with AsyncSessionLocal() as db:
        author = await seeded_user(db, "consulta.a@lumina.internal")
        reviewer = await seeded_user(db, "gestor.a@lumina.internal")
        curator = await seeded_user(db, "technical.admin@lumina.internal")
        target, protector = await create_target(db, user=author)
        service = GovernedFeedbackService(db, protector=protector)

        created = await service.submit(user=author, request=submission(target))
        assert created.lifecycle is FeedbackLifecycle.TRIAGED
        assert created.triage is not None
        assert created.triage.review_queue == "DATA_INTEGRITY"
        assert created.user_id == author.id

        replay = await service.submit(user=author, request=submission(target))
        assert replay.feedback_id == created.feedback_id
        event_count = await db.scalar(
            select(func.count(GovernedFeedbackEvent.id)).where(
                GovernedFeedbackEvent.feedback_id == created.feedback_id
            )
        )
        assert event_count == 3

        assigned = await service.assign_reviewer(
            user=curator,
            feedback_id=created.feedback_id,
            reviewer_user_id=reviewer.id,
            expected_lock_version=0,
        )
        assert assigned.lifecycle is FeedbackLifecycle.IN_REVIEW
        review = await service.review(
            user=reviewer,
            feedback_id=created.feedback_id,
            decision=FeedbackReviewDecisionV2.INCORRECT,
            rationale="A evidência estrutural confirma que o valor requer correção.",
            expected_lock_version=1,
        )
        assert review.decision is FeedbackReviewDecisionV2.INCORRECT
        approved = await service.finalize(
            user=curator,
            feedback_id=created.feedback_id,
            target=FeedbackLifecycle.APPROVED,
            expected_lock_version=2,
        )
        assert approved.lifecycle is FeedbackLifecycle.APPROVED

        candidate = await service.create_candidate(
            user=curator, feedback_id=created.feedback_id
        )
        assert candidate.quality_status.value == "VALID"
        with pytest.raises(TrainingCandidateInvalidError):
            await service.approve_candidate(
                user=curator,
                candidate_id=candidate.candidate_id,
                expected_lock_version=candidate.lock_version,
                domain="SALES",
            )
        validated_candidate = await service.validate_candidate(
            user=curator,
            candidate_id=candidate.candidate_id,
            expected_lock_version=candidate.lock_version,
        )
        assert validated_candidate.status is CandidateStatus.VALIDATED
        example = await service.approve_candidate(
            user=curator,
            candidate_id=candidate.candidate_id,
            expected_lock_version=validated_candidate.lock_version,
            domain="SALES",
        )
        assert example.tenant_scope == author.tenant_id
        assert "OFFLINE_ONLY" in example.restrictions

        snapshot = await service.create_dataset_snapshot(
            user=curator,
            dataset_id=None,
            version=1,
            name="Correções comerciais aprovadas",
            description="Casos revisados para avaliação offline.",
            purpose="REGRESSION_EVAL",
            example_ids=[example.example_id],
        )
        assert snapshot.status is DatasetStatus.DRAFT
        in_review = await service.review_snapshot(
            user=curator,
            snapshot_id=snapshot.snapshot_id,
            target=DatasetStatus.IN_REVIEW,
            expected_lock_version=0,
        )
        approved_snapshot = await service.review_snapshot(
            user=curator,
            snapshot_id=snapshot.snapshot_id,
            target=DatasetStatus.APPROVED,
            expected_lock_version=in_review.lock_version,
        )
        published = await service.publish_snapshot(
            user=curator,
            snapshot_id=snapshot.snapshot_id,
            expected_lock_version=approved_snapshot.lock_version,
        )
        assert published.status is DatasetStatus.PUBLISHED
        export, payload = await service.export_dataset(
            user=curator,
            snapshot_id=snapshot.snapshot_id,
            purpose="OFFLINE_REGRESSION",
        )
        assert export.record_count == 1
        assert payload.endswith(b"\n")
        assert export.content_checksum == content_sha256(payload)
        assert b"password" not in payload.lower()
        await db.commit()


@pytest.mark.asyncio
async def test_feedback_target_is_owner_scoped_and_self_review_is_blocked() -> None:
    async with AsyncSessionLocal() as db:
        author = await seeded_user(db, "consulta.a@lumina.internal")
        other = await seeded_user(db, "consulta.b@lumina.internal")
        admin = await seeded_user(db, "technical.admin@lumina.internal")
        target, protector = await create_target(db, user=author)
        service = GovernedFeedbackService(db, protector=protector)
        with pytest.raises(FeedbackTargetNotFoundError):
            await service.submit(user=other, request=submission(target, "idempotency-other"))

        created = await service.submit(user=author, request=submission(target))
        with pytest.raises(FeedbackSelfReviewForbiddenError):
            await service.assign_reviewer(
                user=admin,
                feedback_id=created.feedback_id,
                reviewer_user_id=author.id,
                expected_lock_version=0,
            )
        count = await db.scalar(
            select(func.count(GovernedFeedbackRecord.id)).where(
                GovernedFeedbackRecord.tenant_id == author.tenant_id
            )
        )
        assert count == 1


@pytest.mark.asyncio
async def test_shadow_evaluation_is_structural_and_does_not_persist() -> None:
    async with AsyncSessionLocal() as db:
        author = await seeded_user(db, "consulta.a@lumina.internal")
        target, protector = await create_target(db, user=author)
        service = GovernedFeedbackService(db, protector=protector)
        before = await db.scalar(select(func.count(GovernedFeedbackRecord.id)))

        result = await service.shadow_evaluate(
            user=author,
            request=submission(target, "shadow-evaluation-0001"),
        )

        after = await db.scalar(select(func.count(GovernedFeedbackRecord.id)))
        assert result.target_authorized is True
        assert result.checksum_matches is True
        assert result.eligible_for_collection is True
        assert result.persisted is False
        assert before == after


@pytest.mark.asyncio
async def test_user_can_answer_a_governed_information_request() -> None:
    async with AsyncSessionLocal() as db:
        author = await seeded_user(db, "consulta.a@lumina.internal")
        reviewer = await seeded_user(db, "gestor.a@lumina.internal")
        admin = await seeded_user(db, "technical.admin@lumina.internal")
        target, protector = await create_target(db, user=author)
        service = GovernedFeedbackService(db, protector=protector)

        created = await service.submit(
            user=author,
            request=submission(target, "information-request-0001"),
        )
        assigned = await service.assign_reviewer(
            user=admin,
            feedback_id=created.feedback_id,
            reviewer_user_id=reviewer.id,
            expected_lock_version=created.lock_version,
        )
        await service.review(
            user=reviewer,
            feedback_id=created.feedback_id,
            decision=FeedbackReviewDecisionV2.UNVERIFIABLE,
            rationale="Falta a referencia empresarial usada pelo autor.",
            expected_lock_version=assigned.lock_version,
        )
        requested = await service.finalize(
            user=reviewer,
            feedback_id=created.feedback_id,
            target=FeedbackLifecycle.NEEDS_INFORMATION,
            expected_lock_version=assigned.lock_version + 1,
        )
        assert requested.lifecycle is FeedbackLifecycle.NEEDS_INFORMATION

        answered = await service.respond_to_information_request(
            user=author,
            feedback_id=created.feedback_id,
            explanation="A referencia e o fechamento mensal homologado.",
            expected_lock_version=requested.lock_version,
        )
        assert answered.lifecycle is FeedbackLifecycle.IN_REVIEW
        assert answered.explanation == "A referencia e o fechamento mensal homologado."


@pytest.mark.asyncio
async def test_retention_expires_pending_feedback_without_deleting_audit() -> None:
    async with AsyncSessionLocal() as db:
        author = await seeded_user(db, "consulta.a@lumina.internal")
        admin = await seeded_user(db, "technical.admin@lumina.internal")
        target, protector = await create_target(db, user=author)
        service = GovernedFeedbackService(db, protector=protector)
        created = await service.submit(
            user=author,
            request=submission(target, "retention-expire-0001"),
        )
        row = await service.repo.get_feedback(
            tenant_id=author.tenant_id,
            feedback_id=created.feedback_id,
        )
        assert row is not None
        retention_at = row.created_at + timedelta(days=1)
        assert await service.repo.compare_and_swap(
            tenant_id=author.tenant_id,
            feedback_id=row.id,
            expected_lock_version=row.lock_version,
            values={"retention_at": retention_at},
        )
        await db.refresh(row)

        processed = await service.expire_due(
            user=admin,
            at=row.created_at + timedelta(days=2),
            limit=10,
        )
        assert processed == [created.feedback_id]
        await db.refresh(row)
        assert row.lifecycle == FeedbackLifecycle.EXPIRED.value
        event_count = await db.scalar(
            select(func.count(GovernedFeedbackEvent.id)).where(
                GovernedFeedbackEvent.feedback_id == created.feedback_id
            )
        )
        assert event_count == 4
