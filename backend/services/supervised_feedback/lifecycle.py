from __future__ import annotations

from contracts.supervised_feedback_v2 import CandidateStatus, DatasetStatus, FeedbackLifecycle
from services.supervised_feedback.errors import FeedbackInvalidTransitionError


FEEDBACK_TRANSITIONS: dict[FeedbackLifecycle, frozenset[FeedbackLifecycle]] = {
    FeedbackLifecycle.RECEIVED: frozenset(
        {
            FeedbackLifecycle.VALIDATED,
            FeedbackLifecycle.WITHDRAWN,
            FeedbackLifecycle.EXPIRED,
        }
    ),
    FeedbackLifecycle.VALIDATED: frozenset(
        {
            FeedbackLifecycle.TRIAGED,
            FeedbackLifecycle.WITHDRAWN,
            FeedbackLifecycle.EXPIRED,
        }
    ),
    FeedbackLifecycle.TRIAGED: frozenset(
        {
            FeedbackLifecycle.IN_REVIEW,
            FeedbackLifecycle.WITHDRAWN,
            FeedbackLifecycle.EXPIRED,
        }
    ),
    FeedbackLifecycle.IN_REVIEW: frozenset(
        {
            FeedbackLifecycle.APPROVED,
            FeedbackLifecycle.REJECTED,
            FeedbackLifecycle.NEEDS_INFORMATION,
            FeedbackLifecycle.EXPIRED,
        }
    ),
    FeedbackLifecycle.NEEDS_INFORMATION: frozenset(
        {FeedbackLifecycle.IN_REVIEW, FeedbackLifecycle.EXPIRED}
    ),
    FeedbackLifecycle.APPROVED: frozenset({FeedbackLifecycle.ARCHIVED}),
    FeedbackLifecycle.REJECTED: frozenset({FeedbackLifecycle.ARCHIVED}),
    FeedbackLifecycle.WITHDRAWN: frozenset({FeedbackLifecycle.ARCHIVED}),
    FeedbackLifecycle.EXPIRED: frozenset({FeedbackLifecycle.ARCHIVED}),
    FeedbackLifecycle.ARCHIVED: frozenset(),
}

CANDIDATE_TRANSITIONS: dict[CandidateStatus, frozenset[CandidateStatus]] = {
    CandidateStatus.CANDIDATE: frozenset(
        {CandidateStatus.VALIDATED, CandidateStatus.REJECTED, CandidateStatus.ARCHIVED}
    ),
    CandidateStatus.VALIDATED: frozenset(
        {CandidateStatus.APPROVED, CandidateStatus.REJECTED, CandidateStatus.ARCHIVED}
    ),
    CandidateStatus.APPROVED: frozenset(
        {CandidateStatus.IN_DATASET, CandidateStatus.DEPRECATED, CandidateStatus.ARCHIVED}
    ),
    CandidateStatus.IN_DATASET: frozenset(
        {CandidateStatus.DEPRECATED, CandidateStatus.ARCHIVED}
    ),
    CandidateStatus.REJECTED: frozenset({CandidateStatus.ARCHIVED}),
    CandidateStatus.DEPRECATED: frozenset({CandidateStatus.ARCHIVED}),
    CandidateStatus.ARCHIVED: frozenset(),
}

DATASET_TRANSITIONS: dict[DatasetStatus, frozenset[DatasetStatus]] = {
    DatasetStatus.DRAFT: frozenset(
        {DatasetStatus.IN_REVIEW, DatasetStatus.REJECTED, DatasetStatus.ARCHIVED}
    ),
    DatasetStatus.IN_REVIEW: frozenset(
        {DatasetStatus.APPROVED, DatasetStatus.REJECTED, DatasetStatus.DRAFT}
    ),
    DatasetStatus.APPROVED: frozenset(
        {DatasetStatus.PUBLISHED, DatasetStatus.REJECTED}
    ),
    DatasetStatus.PUBLISHED: frozenset(
        {DatasetStatus.DEPRECATED, DatasetStatus.ARCHIVED}
    ),
    DatasetStatus.REJECTED: frozenset({DatasetStatus.ARCHIVED}),
    DatasetStatus.DEPRECATED: frozenset({DatasetStatus.ARCHIVED}),
    DatasetStatus.ARCHIVED: frozenset(),
}


def require_transition(current: FeedbackLifecycle, target: FeedbackLifecycle) -> None:
    if target not in FEEDBACK_TRANSITIONS[current]:
        raise FeedbackInvalidTransitionError(
            "Transicao de feedback nao permitida.",
            details={"current": current.value, "target": target.value},
        )


def require_candidate_transition(
    current: CandidateStatus, target: CandidateStatus
) -> None:
    if target not in CANDIDATE_TRANSITIONS[current]:
        raise FeedbackInvalidTransitionError(
            "Transicao de candidato nao permitida.",
            details={"current": current.value, "target": target.value},
        )
