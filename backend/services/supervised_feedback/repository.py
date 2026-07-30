from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.conversation_state import ConversationNodeRecord, ConversationSession
from models.supervised_feedback import (
    FeedbackDeletionRequest,
    GovernedFeedbackCorrection,
    GovernedFeedbackEvent,
    GovernedFeedbackRecord,
    GovernedFeedbackRedaction,
    GovernedFeedbackReview,
    SupervisedTrainingCandidate,
    SupervisedTrainingExample,
    TrainingDatasetExport,
    TrainingDatasetMember,
    TrainingDatasetSnapshot,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GovernedFeedbackRepository:
    """Tenant-scoped persistence. Transaction ownership remains with the service."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def validate_target(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        public_session_id: str,
        response_node_id: uuid.UUID,
    ) -> ConversationNodeRecord | None:
        stmt = (
            select(ConversationNodeRecord)
            .join(
                ConversationSession,
                ConversationSession.id == ConversationNodeRecord.session_id,
            )
            .where(
                ConversationNodeRecord.id == response_node_id,
                ConversationNodeRecord.tenant_id == tenant_id,
                ConversationNodeRecord.user_id == user_id,
                ConversationNodeRecord.role == "assistant",
                ConversationNodeRecord.node_type == "ASSISTANT_RESPONSE",
                ConversationNodeRecord.status == "COMPLETED",
                ConversationSession.tenant_id == tenant_id,
                ConversationSession.user_id == user_id,
                ConversationSession.public_session_id == public_session_id,
            )
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_query_node(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        query_node_id: uuid.UUID,
    ) -> ConversationNodeRecord | None:
        stmt = select(ConversationNodeRecord).where(
            ConversationNodeRecord.id == query_node_id,
            ConversationNodeRecord.session_id == session_id,
            ConversationNodeRecord.tenant_id == tenant_id,
            ConversationNodeRecord.user_id == user_id,
            ConversationNodeRecord.role == "user",
            ConversationNodeRecord.node_type == "USER_QUERY",
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def idempotent_record(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        idempotency_key_hash: str,
    ) -> GovernedFeedbackRecord | None:
        stmt = select(GovernedFeedbackRecord).where(
            GovernedFeedbackRecord.tenant_id == tenant_id,
            GovernedFeedbackRecord.user_id == user_id,
            GovernedFeedbackRecord.idempotency_key_hash == idempotency_key_hash,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def create_feedback(
        self,
        *,
        row: GovernedFeedbackRecord,
        correction: GovernedFeedbackCorrection | None,
        redaction: GovernedFeedbackRedaction,
    ) -> GovernedFeedbackRecord:
        self.db.add(row)
        await self.db.flush()
        if correction is not None:
            self.db.add(correction)
        self.db.add(redaction)
        await self.db.flush()
        return row

    async def get_feedback(
        self,
        *,
        tenant_id: uuid.UUID,
        feedback_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        for_update: bool = False,
    ) -> GovernedFeedbackRecord | None:
        stmt = select(GovernedFeedbackRecord).where(
            GovernedFeedbackRecord.tenant_id == tenant_id,
            GovernedFeedbackRecord.id == feedback_id,
        )
        if user_id is not None:
            stmt = stmt.where(GovernedFeedbackRecord.user_id == user_id)
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_correction(
        self,
        *,
        tenant_id: uuid.UUID,
        feedback_id: uuid.UUID,
    ) -> GovernedFeedbackCorrection | None:
        stmt = select(GovernedFeedbackCorrection).where(
            GovernedFeedbackCorrection.tenant_id == tenant_id,
            GovernedFeedbackCorrection.feedback_id == feedback_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_redaction(
        self,
        *,
        tenant_id: uuid.UUID,
        feedback_id: uuid.UUID,
    ) -> GovernedFeedbackRedaction | None:
        stmt = select(GovernedFeedbackRedaction).where(
            GovernedFeedbackRedaction.tenant_id == tenant_id,
            GovernedFeedbackRedaction.feedback_id == feedback_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_feedback(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID | None,
        lifecycle: str | None,
        review_queue: str | None,
        limit: int,
        after_created_at: datetime | None,
        after_id: uuid.UUID | None,
    ) -> list[GovernedFeedbackRecord]:
        stmt = select(GovernedFeedbackRecord).where(
            GovernedFeedbackRecord.tenant_id == tenant_id
        )
        if user_id is not None:
            stmt = stmt.where(GovernedFeedbackRecord.user_id == user_id)
        if lifecycle is not None:
            stmt = stmt.where(GovernedFeedbackRecord.lifecycle == lifecycle)
        if review_queue is not None:
            stmt = stmt.where(GovernedFeedbackRecord.review_queue == review_queue)
        if after_created_at is not None and after_id is not None:
            stmt = stmt.where(
                or_(
                    GovernedFeedbackRecord.created_at < after_created_at,
                    and_(
                        GovernedFeedbackRecord.created_at == after_created_at,
                        GovernedFeedbackRecord.id < after_id,
                    ),
                )
            )
        stmt = stmt.order_by(
            GovernedFeedbackRecord.created_at.desc(),
            GovernedFeedbackRecord.id.desc(),
        ).limit(limit)
        return list((await self.db.execute(stmt)).scalars())

    async def list_duplicate_group(
        self,
        *,
        tenant_id: uuid.UUID,
        duplicate_fingerprint: str,
        limit: int,
    ) -> list[GovernedFeedbackRecord]:
        stmt = (
            select(GovernedFeedbackRecord)
            .where(
                GovernedFeedbackRecord.tenant_id == tenant_id,
                GovernedFeedbackRecord.duplicate_fingerprint
                == duplicate_fingerprint,
            )
            .order_by(
                GovernedFeedbackRecord.created_at.desc(),
                GovernedFeedbackRecord.id.desc(),
            )
            .limit(limit)
        )
        return list((await self.db.execute(stmt)).scalars())

    async def compare_and_swap(
        self,
        *,
        tenant_id: uuid.UUID,
        feedback_id: uuid.UUID,
        expected_lock_version: int,
        values: dict[str, object],
    ) -> bool:
        stmt = (
            update(GovernedFeedbackRecord)
            .where(
                GovernedFeedbackRecord.tenant_id == tenant_id,
                GovernedFeedbackRecord.id == feedback_id,
                GovernedFeedbackRecord.lock_version == expected_lock_version,
            )
            .values(
                **values,
                lock_version=GovernedFeedbackRecord.lock_version + 1,
                updated_at=utc_now(),
            )
        )
        return (await self.db.execute(stmt)).rowcount == 1

    async def assign_reviewer(
        self,
        *,
        tenant_id: uuid.UUID,
        feedback_id: uuid.UUID,
        reviewer_user_id: uuid.UUID,
        expected_lock_version: int,
    ) -> bool:
        return await self.compare_and_swap(
            tenant_id=tenant_id,
            feedback_id=feedback_id,
            expected_lock_version=expected_lock_version,
            values={"reviewer_user_id": reviewer_user_id, "lifecycle": "IN_REVIEW"},
        )

    async def record_review(self, review: GovernedFeedbackReview) -> None:
        self.db.add(review)
        await self.db.flush()

    async def record_event(self, event: GovernedFeedbackEvent) -> None:
        self.db.add(event)
        await self.db.flush()

    async def create_candidate(
        self, candidate: SupervisedTrainingCandidate
    ) -> SupervisedTrainingCandidate:
        self.db.add(candidate)
        await self.db.flush()
        return candidate

    async def get_candidate(
        self,
        *,
        tenant_id: uuid.UUID,
        candidate_id: uuid.UUID,
        for_update: bool = False,
    ) -> SupervisedTrainingCandidate | None:
        stmt = select(SupervisedTrainingCandidate).where(
            SupervisedTrainingCandidate.tenant_id == tenant_id,
            SupervisedTrainingCandidate.id == candidate_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_candidate_by_feedback(
        self,
        *,
        tenant_id: uuid.UUID,
        feedback_id: uuid.UUID,
        for_update: bool = False,
    ) -> SupervisedTrainingCandidate | None:
        stmt = select(SupervisedTrainingCandidate).where(
            SupervisedTrainingCandidate.tenant_id == tenant_id,
            SupervisedTrainingCandidate.feedback_id == feedback_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def compare_and_swap_candidate(
        self,
        *,
        tenant_id: uuid.UUID,
        candidate_id: uuid.UUID,
        expected_lock_version: int,
        values: dict[str, object],
    ) -> bool:
        stmt = (
            update(SupervisedTrainingCandidate)
            .where(
                SupervisedTrainingCandidate.tenant_id == tenant_id,
                SupervisedTrainingCandidate.id == candidate_id,
                SupervisedTrainingCandidate.lock_version == expected_lock_version,
            )
            .values(
                **values,
                lock_version=SupervisedTrainingCandidate.lock_version + 1,
                updated_at=utc_now(),
            )
        )
        return (await self.db.execute(stmt)).rowcount == 1

    async def list_candidates(
        self, *, tenant_id: uuid.UUID, status: str | None, limit: int
    ) -> list[SupervisedTrainingCandidate]:
        stmt = select(SupervisedTrainingCandidate).where(
            SupervisedTrainingCandidate.tenant_id == tenant_id
        )
        if status:
            stmt = stmt.where(SupervisedTrainingCandidate.status == status)
        stmt = stmt.order_by(
            SupervisedTrainingCandidate.created_at.desc(),
            SupervisedTrainingCandidate.id.desc(),
        ).limit(limit)
        return list((await self.db.execute(stmt)).scalars())

    async def create_example(
        self, example: SupervisedTrainingExample
    ) -> SupervisedTrainingExample:
        self.db.add(example)
        await self.db.flush()
        return example

    async def get_examples(
        self, *, tenant_id: uuid.UUID, example_ids: list[uuid.UUID]
    ) -> list[SupervisedTrainingExample]:
        if not example_ids:
            return []
        stmt = select(SupervisedTrainingExample).where(
            SupervisedTrainingExample.tenant_id == tenant_id,
            SupervisedTrainingExample.id.in_(example_ids),
        )
        return list((await self.db.execute(stmt)).scalars())

    async def list_examples(
        self, *, tenant_id: uuid.UUID, limit: int
    ) -> list[SupervisedTrainingExample]:
        stmt = (
            select(SupervisedTrainingExample)
            .where(SupervisedTrainingExample.tenant_id == tenant_id)
            .order_by(
                SupervisedTrainingExample.created_at.desc(),
                SupervisedTrainingExample.id.desc(),
            )
            .limit(limit)
        )
        return list((await self.db.execute(stmt)).scalars())

    async def create_snapshot(
        self,
        *,
        snapshot: TrainingDatasetSnapshot,
        members: list[TrainingDatasetMember],
    ) -> TrainingDatasetSnapshot:
        self.db.add(snapshot)
        await self.db.flush()
        self.db.add_all(members)
        await self.db.flush()
        return snapshot

    async def get_snapshot(
        self,
        *,
        tenant_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        for_update: bool = False,
    ) -> TrainingDatasetSnapshot | None:
        stmt = select(TrainingDatasetSnapshot).where(
            TrainingDatasetSnapshot.tenant_id == tenant_id,
            TrainingDatasetSnapshot.id == snapshot_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_snapshots(
        self, *, tenant_id: uuid.UUID, dataset_id: uuid.UUID | None, limit: int
    ) -> list[TrainingDatasetSnapshot]:
        stmt = select(TrainingDatasetSnapshot).where(
            TrainingDatasetSnapshot.tenant_id == tenant_id
        )
        if dataset_id:
            stmt = stmt.where(TrainingDatasetSnapshot.dataset_id == dataset_id)
        stmt = stmt.order_by(
            TrainingDatasetSnapshot.created_at.desc(),
            TrainingDatasetSnapshot.id.desc(),
        ).limit(limit)
        return list((await self.db.execute(stmt)).scalars())

    async def get_members(
        self, *, tenant_id: uuid.UUID, snapshot_id: uuid.UUID
    ) -> list[TrainingDatasetMember]:
        stmt = (
            select(TrainingDatasetMember)
            .where(
                TrainingDatasetMember.tenant_id == tenant_id,
                TrainingDatasetMember.snapshot_id == snapshot_id,
            )
            .order_by(TrainingDatasetMember.position)
        )
        return list((await self.db.execute(stmt)).scalars())

    async def iter_snapshot_examples(
        self,
        *,
        tenant_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        batch_size: int = 500,
    ) -> AsyncIterator[SupervisedTrainingExample]:
        stmt = (
            select(SupervisedTrainingExample)
            .join(
                TrainingDatasetMember,
                and_(
                    TrainingDatasetMember.example_id
                    == SupervisedTrainingExample.id,
                    TrainingDatasetMember.tenant_id
                    == SupervisedTrainingExample.tenant_id,
                ),
            )
            .where(
                TrainingDatasetMember.tenant_id == tenant_id,
                TrainingDatasetMember.snapshot_id == snapshot_id,
                SupervisedTrainingExample.tenant_id == tenant_id,
            )
            .order_by(TrainingDatasetMember.position)
            .execution_options(yield_per=batch_size)
        )
        result = await self.db.stream_scalars(stmt)
        async for row in result:
            yield row

    async def record_dataset_export(self, row: TrainingDatasetExport) -> None:
        self.db.add(row)
        await self.db.flush()

    async def create_deletion_request(self, row: FeedbackDeletionRequest) -> None:
        self.db.add(row)
        await self.db.flush()

    async def retention_candidates(
        self, *, tenant_id: uuid.UUID, at: datetime, limit: int
    ) -> list[GovernedFeedbackRecord]:
        stmt = (
            select(GovernedFeedbackRecord)
            .where(
                GovernedFeedbackRecord.tenant_id == tenant_id,
                GovernedFeedbackRecord.retention_at.is_not(None),
                GovernedFeedbackRecord.retention_at <= at,
                GovernedFeedbackRecord.lifecycle != "ARCHIVED",
            )
            .order_by(GovernedFeedbackRecord.retention_at, GovernedFeedbackRecord.id)
            .limit(limit)
        )
        return list((await self.db.execute(stmt)).scalars())
