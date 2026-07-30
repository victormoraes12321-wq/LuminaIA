from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from contracts.supervised_feedback_v2 import (
    CandidateStatus,
    DatasetStatus,
    FeedbackLifecycle,
    FeedbackRecordV2,
    FeedbackShadowEvaluationV2,
    FeedbackReviewDecisionV2,
    FeedbackReviewV2,
    FeedbackSubmissionV2,
    GovernedImportDryRunRequestV2,
    GovernedImportDryRunResultV2,
    TrainingDatasetSnapshotV2,
    TrainingExampleCandidateV2,
)
from contracts.supervised_feedback_v2.models import ApprovedTrainingExampleV2
from database import get_db
from models.user import User
from routers.dependencies import enforce_password_change
from services.supervised_feedback.errors import FeedbackFeatureDisabledError
from services.supervised_feedback.service import GovernedFeedbackService


router = APIRouter(prefix="/api/v2", tags=["Governed Feedback V2"])


class StrictAction(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class FeedbackCapabilities(StrictAction):
    contract_version: Literal["lumina.supervised-feedback/1.0"]
    mode: Literal[
        "LEGACY_ONLY",
        "SHADOW",
        "V2_COLLECT",
        "V2_REVIEW",
        "V2_CURATE",
    ]
    user_feedback_enabled: bool
    admin_enabled: bool
    dataset_enabled: bool
    export_enabled: bool
    automatic_training_enabled: Literal[False] = False


class ExplanationUpdate(StrictAction):
    explanation: str = Field(min_length=1, max_length=2000)
    expected_lock_version: int = Field(ge=0)


class LockAction(StrictAction):
    expected_lock_version: int = Field(ge=0)


class ReviewerAssignment(LockAction):
    reviewer_user_id: uuid.UUID


class ReviewAction(LockAction):
    decision: FeedbackReviewDecisionV2
    rationale: str = Field(min_length=1, max_length=2000)


class DeletionAction(StrictAction):
    reason: str | None = Field(default=None, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=128)


class DeletionResult(StrictAction):
    request_id: uuid.UUID
    status: Literal["PENDING"] = "PENDING"


class CandidateApproval(LockAction):
    domain: str = Field(min_length=1, max_length=128)


class DatasetCreate(StrictAction):
    dataset_id: uuid.UUID | None = None
    version: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=1000)
    purpose: str = Field(min_length=1, max_length=500)
    example_ids: list[uuid.UUID] = Field(default_factory=list, max_length=10000)


class DatasetTransition(LockAction):
    target: Literal["DRAFT", "IN_REVIEW", "APPROVED", "REJECTED"]


class DatasetExportAction(StrictAction):
    purpose: str = Field(min_length=1, max_length=500)


class RetentionAction(StrictAction):
    at: datetime
    limit: int = Field(default=100, ge=1, le=1000)


class RetentionResult(StrictAction):
    processed_feedback_ids: list[uuid.UUID]


def _service(db: AsyncSession) -> GovernedFeedbackService:
    return GovernedFeedbackService(db)


def _require_read() -> None:
    if settings.SUPERVISED_FEEDBACK_MODE not in {
        "V2_COLLECT",
        "V2_REVIEW",
        "V2_CURATE",
    }:
        raise FeedbackFeatureDisabledError(
            "O feedback governado esta desabilitado neste ambiente."
        )


def _require_write() -> None:
    _require_read()
    if not settings.SUPERVISED_FEEDBACK_FRONTEND_ENABLED:
        raise FeedbackFeatureDisabledError(
            "A escrita de feedback governado esta desabilitada."
        )


def _require_review() -> None:
    if settings.SUPERVISED_FEEDBACK_MODE not in {"V2_REVIEW", "V2_CURATE"}:
        raise FeedbackFeatureDisabledError(
            "A revisao governada esta desabilitada."
        )
    if not settings.SUPERVISED_FEEDBACK_ADMIN_ENABLED:
        raise FeedbackFeatureDisabledError("A fila administrativa esta desabilitada.")


def _require_curate() -> None:
    if settings.SUPERVISED_FEEDBACK_MODE != "V2_CURATE":
        raise FeedbackFeatureDisabledError(
            "A curadoria supervisionada esta desabilitada."
        )
    if not settings.SUPERVISED_FEEDBACK_DATASET_ENABLED:
        raise FeedbackFeatureDisabledError("A curadoria de dataset esta desabilitada.")


def _require_shadow() -> None:
    if (
        settings.SUPERVISED_FEEDBACK_MODE != "SHADOW"
        or not settings.SUPERVISED_FEEDBACK_SHADOW_ENABLED
    ):
        raise FeedbackFeatureDisabledError(
            "A avaliacao shadow de feedback esta desabilitada."
        )


@router.get("/feedback/capabilities", response_model=FeedbackCapabilities)
async def capabilities(
    _user: Annotated[User, Depends(enforce_password_change)],
) -> FeedbackCapabilities:
    return FeedbackCapabilities(
        contract_version="lumina.supervised-feedback/1.0",
        mode=settings.SUPERVISED_FEEDBACK_MODE,
        user_feedback_enabled=settings.SUPERVISED_FEEDBACK_FRONTEND_ENABLED,
        admin_enabled=settings.SUPERVISED_FEEDBACK_ADMIN_ENABLED,
        dataset_enabled=settings.SUPERVISED_FEEDBACK_DATASET_ENABLED,
        export_enabled=settings.SUPERVISED_FEEDBACK_EXPORT_ENABLED,
    )


@router.post(
    "/me/feedback",
    response_model=FeedbackRecordV2,
    status_code=status.HTTP_201_CREATED,
)
async def submit_feedback(
    body: FeedbackSubmissionV2,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeedbackRecordV2:
    _require_write()
    return await _service(db).submit(user=user, request=body)


@router.post(
    "/feedback/shadow-evaluate",
    response_model=FeedbackShadowEvaluationV2,
)
async def shadow_evaluate_feedback(
    body: FeedbackSubmissionV2,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeedbackShadowEvaluationV2:
    _require_shadow()
    return await _service(db).shadow_evaluate(user=user, request=body)


@router.get("/me/feedback", response_model=list[FeedbackRecordV2])
async def list_own_feedback(
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(50, ge=1, le=200),
    after_created_at: datetime | None = Query(None),
    after_id: uuid.UUID | None = Query(None),
) -> list[FeedbackRecordV2]:
    _require_read()
    return await _service(db).list_own(
        user=user,
        limit=limit,
        after_created_at=after_created_at,
        after_id=after_id,
    )


@router.get("/me/feedback/{feedback_id}", response_model=FeedbackRecordV2)
async def get_own_feedback(
    feedback_id: uuid.UUID,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeedbackRecordV2:
    _require_read()
    return await _service(db).get_own(user=user, feedback_id=feedback_id)


@router.patch("/me/feedback/{feedback_id}", response_model=FeedbackRecordV2)
async def update_feedback_explanation(
    feedback_id: uuid.UUID,
    body: ExplanationUpdate,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeedbackRecordV2:
    _require_write()
    return await _service(db).update_explanation(
        user=user,
        feedback_id=feedback_id,
        explanation=body.explanation,
        expected_lock_version=body.expected_lock_version,
    )


@router.post(
    "/me/feedback/{feedback_id}/information-response",
    response_model=FeedbackRecordV2,
)
async def respond_to_information_request(
    feedback_id: uuid.UUID,
    body: ExplanationUpdate,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeedbackRecordV2:
    _require_write()
    return await _service(db).respond_to_information_request(
        user=user,
        feedback_id=feedback_id,
        explanation=body.explanation,
        expected_lock_version=body.expected_lock_version,
    )


@router.post("/me/feedback/{feedback_id}/withdraw", response_model=FeedbackRecordV2)
async def withdraw_feedback(
    feedback_id: uuid.UUID,
    body: LockAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeedbackRecordV2:
    _require_write()
    return await _service(db).withdraw(
        user=user,
        feedback_id=feedback_id,
        expected_lock_version=body.expected_lock_version,
    )


@router.get("/me/feedback-export")
async def export_own_feedback(
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    _require_read()
    if not settings.SUPERVISED_FEEDBACK_EXPORT_ENABLED:
        raise FeedbackFeatureDisabledError("A exportacao de feedback esta desabilitada.")
    contract, payload = await _service(db).export_own(user=user)
    return Response(
        content=payload,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="feedback-{contract.export_id}.json"',
            "X-Content-Checksum": contract.checksum,
        },
    )


@router.post(
    "/me/feedback/{feedback_id}/deletion-request",
    response_model=DeletionResult,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_feedback_deletion(
    feedback_id: uuid.UUID,
    body: DeletionAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeletionResult:
    _require_write()
    request_id = await _service(db).request_deletion(
        user=user,
        feedback_id=feedback_id,
        reason=body.reason,
        idempotency_key=body.idempotency_key,
    )
    return DeletionResult(request_id=request_id)


@router.get("/feedback/review/queue", response_model=list[FeedbackRecordV2])
async def review_queue(
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
    lifecycle: FeedbackLifecycle | None = Query(None),
    review_queue_name: str | None = Query(None, max_length=32),
    limit: int = Query(50, ge=1, le=200),
    after_created_at: datetime | None = Query(None),
    after_id: uuid.UUID | None = Query(None),
) -> list[FeedbackRecordV2]:
    _require_review()
    return await _service(db).review_queue(
        user=user,
        lifecycle=lifecycle,
        review_queue=review_queue_name,
        limit=limit,
        after_created_at=after_created_at,
        after_id=after_id,
    )


@router.get(
    "/feedback/duplicate-groups/{duplicate_fingerprint}",
    response_model=list[FeedbackRecordV2],
)
async def duplicate_group(
    duplicate_fingerprint: str,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(50, ge=1, le=200),
) -> list[FeedbackRecordV2]:
    _require_review()
    return await _service(db).duplicate_group(
        user=user,
        duplicate_fingerprint=duplicate_fingerprint,
        limit=limit,
    )


@router.post(
    "/feedback/{feedback_id}/reviewer",
    response_model=FeedbackRecordV2,
)
async def assign_reviewer(
    feedback_id: uuid.UUID,
    body: ReviewerAssignment,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeedbackRecordV2:
    _require_review()
    return await _service(db).assign_reviewer(
        user=user,
        feedback_id=feedback_id,
        reviewer_user_id=body.reviewer_user_id,
        expected_lock_version=body.expected_lock_version,
    )


@router.post("/feedback/{feedback_id}/review", response_model=FeedbackReviewV2)
async def review_feedback(
    feedback_id: uuid.UUID,
    body: ReviewAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeedbackReviewV2:
    _require_review()
    return await _service(db).review(
        user=user,
        feedback_id=feedback_id,
        decision=body.decision,
        rationale=body.rationale,
        expected_lock_version=body.expected_lock_version,
    )


async def _finalize(
    *,
    feedback_id: uuid.UUID,
    body: LockAction,
    target: FeedbackLifecycle,
    user: User,
    db: AsyncSession,
) -> FeedbackRecordV2:
    _require_review()
    return await _service(db).finalize(
        user=user,
        feedback_id=feedback_id,
        target=target,
        expected_lock_version=body.expected_lock_version,
    )


@router.post("/feedback/{feedback_id}/approve", response_model=FeedbackRecordV2)
async def approve_feedback(
    feedback_id: uuid.UUID,
    body: LockAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeedbackRecordV2:
    return await _finalize(
        feedback_id=feedback_id,
        body=body,
        target=FeedbackLifecycle.APPROVED,
        user=user,
        db=db,
    )


@router.post("/feedback/{feedback_id}/reject", response_model=FeedbackRecordV2)
async def reject_feedback(
    feedback_id: uuid.UUID,
    body: LockAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeedbackRecordV2:
    return await _finalize(
        feedback_id=feedback_id,
        body=body,
        target=FeedbackLifecycle.REJECTED,
        user=user,
        db=db,
    )


@router.post(
    "/feedback/{feedback_id}/request-information",
    response_model=FeedbackRecordV2,
)
async def request_information(
    feedback_id: uuid.UUID,
    body: LockAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeedbackRecordV2:
    return await _finalize(
        feedback_id=feedback_id,
        body=body,
        target=FeedbackLifecycle.NEEDS_INFORMATION,
        user=user,
        db=db,
    )


@router.post(
    "/feedback/{feedback_id}/training-candidate",
    response_model=TrainingExampleCandidateV2,
    status_code=status.HTTP_201_CREATED,
)
async def create_training_candidate(
    feedback_id: uuid.UUID,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TrainingExampleCandidateV2:
    _require_curate()
    return await _service(db).create_candidate(user=user, feedback_id=feedback_id)


@router.get("/feedback/training-candidates", response_model=list[TrainingExampleCandidateV2])
async def list_training_candidates(
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
    candidate_status: CandidateStatus | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> list[TrainingExampleCandidateV2]:
    _require_curate()
    return await _service(db).list_candidates(
        user=user, status=candidate_status, limit=limit
    )


@router.get(
    "/feedback/training-examples",
    response_model=list[ApprovedTrainingExampleV2],
)
async def list_training_examples(
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(50, ge=1, le=200),
) -> list[ApprovedTrainingExampleV2]:
    _require_curate()
    return await _service(db).list_examples(user=user, limit=limit)


@router.post(
    "/feedback/training-candidates/{candidate_id}/validate",
    response_model=TrainingExampleCandidateV2,
)
async def validate_training_candidate(
    candidate_id: uuid.UUID,
    body: LockAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TrainingExampleCandidateV2:
    _require_curate()
    return await _service(db).validate_candidate(
        user=user,
        candidate_id=candidate_id,
        expected_lock_version=body.expected_lock_version,
    )


@router.post(
    "/feedback/training-candidates/{candidate_id}/reject",
    response_model=TrainingExampleCandidateV2,
)
async def reject_training_candidate(
    candidate_id: uuid.UUID,
    body: LockAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TrainingExampleCandidateV2:
    _require_curate()
    return await _service(db).reject_candidate(
        user=user,
        candidate_id=candidate_id,
        expected_lock_version=body.expected_lock_version,
    )


@router.post(
    "/feedback/training-candidates/{candidate_id}/approve",
    response_model=ApprovedTrainingExampleV2,
)
async def approve_training_candidate(
    candidate_id: uuid.UUID,
    body: CandidateApproval,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApprovedTrainingExampleV2:
    _require_curate()
    return await _service(db).approve_candidate(
        user=user,
        candidate_id=candidate_id,
        expected_lock_version=body.expected_lock_version,
        domain=body.domain,
    )


@router.post(
    "/feedback/datasets",
    response_model=TrainingDatasetSnapshotV2,
    status_code=status.HTTP_201_CREATED,
)
async def create_dataset(
    body: DatasetCreate,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TrainingDatasetSnapshotV2:
    _require_curate()
    return await _service(db).create_dataset_snapshot(
        user=user,
        dataset_id=body.dataset_id,
        version=body.version,
        name=body.name,
        description=body.description,
        purpose=body.purpose,
        example_ids=body.example_ids,
    )


@router.get(
    "/feedback/datasets",
    response_model=list[TrainingDatasetSnapshotV2],
)
async def list_datasets(
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
    dataset_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> list[TrainingDatasetSnapshotV2]:
    _require_curate()
    return await _service(db).list_dataset_snapshots(
        user=user,
        dataset_id=dataset_id,
        limit=limit,
    )


@router.get(
    "/feedback/datasets/snapshots/{snapshot_id}",
    response_model=TrainingDatasetSnapshotV2,
)
async def get_dataset_snapshot(
    snapshot_id: uuid.UUID,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TrainingDatasetSnapshotV2:
    _require_curate()
    return await _service(db).get_dataset_snapshot(
        user=user, snapshot_id=snapshot_id
    )


@router.post(
    "/feedback/datasets/{snapshot_id}/transition",
    response_model=TrainingDatasetSnapshotV2,
)
async def transition_dataset(
    snapshot_id: uuid.UUID,
    body: DatasetTransition,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TrainingDatasetSnapshotV2:
    _require_curate()
    return await _service(db).review_snapshot(
        user=user,
        snapshot_id=snapshot_id,
        target=DatasetStatus(body.target),
        expected_lock_version=body.expected_lock_version,
    )


@router.post(
    "/feedback/datasets/{snapshot_id}/publish",
    response_model=TrainingDatasetSnapshotV2,
)
async def publish_dataset(
    snapshot_id: uuid.UUID,
    body: LockAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TrainingDatasetSnapshotV2:
    _require_curate()
    return await _service(db).publish_snapshot(
        user=user,
        snapshot_id=snapshot_id,
        expected_lock_version=body.expected_lock_version,
    )


@router.post("/feedback/datasets/{snapshot_id}/export")
async def export_dataset(
    snapshot_id: uuid.UUID,
    body: DatasetExportAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    _require_curate()
    contract, stream = await _service(db).build_dataset_export(
        user=user, snapshot_id=snapshot_id, purpose=body.purpose
    )
    def chunks():
        try:
            while chunk := stream.read(64 * 1024):
                yield chunk
        finally:
            stream.close()

    return StreamingResponse(
        chunks(),
        media_type="application/x-ndjson",
        headers={
            "Content-Disposition": f'attachment; filename="dataset-{snapshot_id}.jsonl"',
            "X-Content-Checksum": contract.content_checksum,
            "X-Manifest-Checksum": contract.manifest_checksum,
        },
    )


@router.post(
    "/feedback/import/dry-run",
    response_model=GovernedImportDryRunResultV2,
)
async def dry_run_governed_import(
    body: GovernedImportDryRunRequestV2,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GovernedImportDryRunResultV2:
    _require_curate()
    return _service(db).dry_run_import(user=user, request=body)


@router.post(
    "/feedback/retention/expire",
    response_model=RetentionResult,
)
async def expire_feedback_by_retention(
    body: RetentionAction,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RetentionResult:
    _require_curate()
    processed = await _service(db).expire_due(
        user=user,
        at=body.at,
        limit=body.limit,
    )
    return RetentionResult(processed_feedback_ids=processed)


@router.get("/feedback/{feedback_id}", response_model=FeedbackRecordV2)
async def get_feedback_for_review(
    feedback_id: uuid.UUID,
    user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeedbackRecordV2:
    _require_review()
    return await _service(db).get_for_review(
        user=user, feedback_id=feedback_id
    )
