from __future__ import annotations

from http import HTTPStatus


class GovernedFeedbackError(Exception):
    code = "FEEDBACK_ERROR"
    status_code = HTTPStatus.UNPROCESSABLE_ENTITY

    def __init__(self, message: str, *, details: dict[str, str | int | bool] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


def _error(name: str, status_code: HTTPStatus):
    return type(name, (GovernedFeedbackError,), {"code": name, "status_code": status_code})


FeedbackNotFoundError = _error("FEEDBACK_NOT_FOUND", HTTPStatus.NOT_FOUND)
FeedbackAccessDeniedError = _error("FEEDBACK_ACCESS_DENIED", HTTPStatus.FORBIDDEN)
FeedbackTenantMismatchError = _error("FEEDBACK_TENANT_MISMATCH", HTTPStatus.NOT_FOUND)
FeedbackUserMismatchError = _error("FEEDBACK_USER_MISMATCH", HTTPStatus.NOT_FOUND)
FeedbackTargetNotFoundError = _error("FEEDBACK_TARGET_NOT_FOUND", HTTPStatus.NOT_FOUND)
FeedbackTargetForbiddenError = _error("FEEDBACK_TARGET_FORBIDDEN", HTTPStatus.NOT_FOUND)
FeedbackTargetChecksumMismatchError = _error(
    "FEEDBACK_TARGET_CHECKSUM_MISMATCH", HTTPStatus.CONFLICT
)
FeedbackInvalidCategoryError = _error("FEEDBACK_INVALID_CATEGORY", HTTPStatus.UNPROCESSABLE_ENTITY)
FeedbackInvalidCorrectionError = _error(
    "FEEDBACK_INVALID_CORRECTION", HTTPStatus.UNPROCESSABLE_ENTITY
)
FeedbackInvalidTransitionError = _error(
    "FEEDBACK_INVALID_TRANSITION", HTTPStatus.CONFLICT
)
FeedbackVersionConflictError = _error("FEEDBACK_VERSION_CONFLICT", HTTPStatus.CONFLICT)
FeedbackAlreadyWithdrawnError = _error("FEEDBACK_ALREADY_WITHDRAWN", HTTPStatus.CONFLICT)
FeedbackRedactionFailedError = _error(
    "FEEDBACK_REDACTION_FAILED", HTTPStatus.UNPROCESSABLE_ENTITY
)
FeedbackSensitiveContentError = _error(
    "FEEDBACK_SENSITIVE_CONTENT", HTTPStatus.UNPROCESSABLE_ENTITY
)
FeedbackPayloadTooLargeError = _error(
    "FEEDBACK_PAYLOAD_TOO_LARGE", HTTPStatus.REQUEST_ENTITY_TOO_LARGE
)
FeedbackSelfReviewForbiddenError = _error(
    "FEEDBACK_SELF_REVIEW_FORBIDDEN", HTTPStatus.FORBIDDEN
)
TrainingCandidateNotFoundError = _error("TRAINING_CANDIDATE_NOT_FOUND", HTTPStatus.NOT_FOUND)
TrainingCandidateInvalidError = _error(
    "TRAINING_CANDIDATE_INVALID", HTTPStatus.UNPROCESSABLE_ENTITY
)
TrainingExampleBlockedError = _error(
    "TRAINING_EXAMPLE_BLOCKED", HTTPStatus.UNPROCESSABLE_ENTITY
)
TrainingDatasetVersionConflictError = _error(
    "TRAINING_DATASET_VERSION_CONFLICT", HTTPStatus.CONFLICT
)
TrainingDatasetImmutableError = _error(
    "TRAINING_DATASET_IMMUTABLE", HTTPStatus.CONFLICT
)
TrainingDatasetExportForbiddenError = _error(
    "TRAINING_DATASET_EXPORT_FORBIDDEN", HTTPStatus.FORBIDDEN
)
TrainingDatasetImportInvalidError = _error(
    "TRAINING_DATASET_IMPORT_INVALID", HTTPStatus.UNPROCESSABLE_ENTITY
)
FeedbackFeatureDisabledError = _error("FEEDBACK_FEATURE_DISABLED", HTTPStatus.NOT_FOUND)
