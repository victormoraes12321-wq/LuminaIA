from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SUPERVISED_FEEDBACK_VERSION = "lumina.supervised-feedback/1.0"


class StrictFeedbackModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )


class FeedbackCategoryV2(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    PARTIALLY_CORRECT = "PARTIALLY_CORRECT"
    INCORRECT_VALUE = "INCORRECT_VALUE"
    INCORRECT_FILTER = "INCORRECT_FILTER"
    INCORRECT_PERIOD = "INCORRECT_PERIOD"
    INCORRECT_METRIC = "INCORRECT_METRIC"
    INCORRECT_ENTITY = "INCORRECT_ENTITY"
    INCORRECT_DIMENSION = "INCORRECT_DIMENSION"
    INCORRECT_COMPARISON = "INCORRECT_COMPARISON"
    INCORRECT_VISUALIZATION = "INCORRECT_VISUALIZATION"
    MISSING_CONTEXT = "MISSING_CONTEXT"
    UNWANTED_INHERITANCE = "UNWANTED_INHERITANCE"
    MISSING_INHERITANCE = "MISSING_INHERITANCE"
    AMBIGUOUS = "AMBIGUOUS"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    UNSAFE_OUTPUT = "UNSAFE_OUTPUT"
    PERFORMANCE = "PERFORMANCE"
    OTHER = "OTHER"


class FeedbackLifecycle(str, Enum):
    RECEIVED = "RECEIVED"
    VALIDATED = "VALIDATED"
    TRIAGED = "TRIAGED"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_INFORMATION = "NEEDS_INFORMATION"
    WITHDRAWN = "WITHDRAWN"
    EXPIRED = "EXPIRED"
    ARCHIVED = "ARCHIVED"


class FeedbackReviewDecisionV2(str, Enum):
    CORRECT = "CORRECT"
    ACCEPTABLE = "ACCEPTABLE"
    PARTIALLY_CORRECT = "PARTIALLY_CORRECT"
    INCORRECT = "INCORRECT"
    UNVERIFIABLE = "UNVERIFIABLE"
    AMBIGUOUS = "AMBIGUOUS"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    UNSAFE = "UNSAFE"
    TECHNICAL_FAILURE = "TECHNICAL_FAILURE"


class FeedbackSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FeedbackPriority(str, Enum):
    P4 = "P4"
    P3 = "P3"
    P2 = "P2"
    P1 = "P1"


class CandidateStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    IN_DATASET = "IN_DATASET"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"


class DatasetStatus(str, Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"


class ExampleQualityStatus(str, Enum):
    VALID = "VALID"
    INCOMPLETE = "INCOMPLETE"
    AMBIGUOUS = "AMBIGUOUS"
    SENSITIVE = "SENSITIVE"
    CONFLICTING = "CONFLICTING"
    OUTDATED_CONTRACT = "OUTDATED_CONTRACT"
    BLOCKED = "BLOCKED"


class EvaluationKind(str, Enum):
    REGRESSION = "REGRESSION"
    CLASSIFICATION = "CLASSIFICATION"
    CONTEXT = "CONTEXT"
    COMPARISON = "COMPARISON"
    RENDERING = "RENDERING"
    SECURITY = "SECURITY"
    MULTITENANCY = "MULTITENANCY"


class FeedbackPermission(str, Enum):
    CREATE_OWN = "feedback:create_own"
    READ_OWN = "feedback:read_own"
    UPDATE_OWN = "feedback:update_own"
    WITHDRAW_OWN = "feedback:withdraw_own"
    EXPORT_OWN = "feedback:export_own"
    TRIAGE = "feedback:triage"
    REVIEW = "feedback:review"
    APPROVE = "feedback:approve"
    REJECT = "feedback:reject"
    REQUEST_INFORMATION = "feedback:request_information"
    CURATE_TRAINING = "feedback:curate_training"
    PUBLISH_DATASET = "feedback:publish_dataset"
    EXPORT_DATASET = "feedback:export_dataset"
    AUDIT_READ = "feedback:audit_read"
    MANAGE_RETENTION = "feedback:manage_retention"
    SUPPORT_READ_REDACTED = "feedback:support_read_redacted"


class FeedbackTargetV2(StrictFeedbackModel):
    response_node_id: uuid.UUID
    session_id: str = Field(min_length=1, max_length=128)
    response_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    query_node_id: uuid.UUID | None = None
    response_contract_version: str = Field(default="lumina.query-response/1.0", max_length=64)


class ExpectedMetricCorrectionV2(StrictFeedbackModel):
    kind: Literal["EXPECTED_METRIC"] = "EXPECTED_METRIC"
    canonical_metric_id: str = Field(min_length=1, max_length=128)
    label: str | None = Field(default=None, max_length=256)


class ExpectedPeriodCorrectionV2(StrictFeedbackModel):
    kind: Literal["EXPECTED_PERIOD"] = "EXPECTED_PERIOD"
    start_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    timezone: str = Field(default="America/Sao_Paulo", max_length=64)


class ExpectedFilterCorrectionV2(StrictFeedbackModel):
    kind: Literal["EXPECTED_FILTER"] = "EXPECTED_FILTER"
    canonical_field_id: str = Field(min_length=1, max_length=128)
    operator: Literal["EQ", "NE", "IN", "NOT_IN", "GT", "GTE", "LT", "LTE", "BETWEEN"]
    values: list[str | int | float | bool] = Field(min_length=1, max_length=100)


class ExpectedEntityCorrectionV2(StrictFeedbackModel):
    kind: Literal["EXPECTED_ENTITY"] = "EXPECTED_ENTITY"
    canonical_entity_id: str = Field(min_length=1, max_length=128)


class ExpectedDimensionCorrectionV2(StrictFeedbackModel):
    kind: Literal["EXPECTED_DIMENSION"] = "EXPECTED_DIMENSION"
    canonical_dimension_id: str = Field(min_length=1, max_length=128)


class ExpectedComparisonCorrectionV2(StrictFeedbackModel):
    kind: Literal["EXPECTED_COMPARISON"] = "EXPECTED_COMPARISON"
    comparison_kind: Literal["PERIOD_OVER_PERIOD", "ENTITY", "TARGET", "RANKING", "PARTICIPATION"]
    baseline_label: str | None = Field(default=None, max_length=128)
    target_label: str | None = Field(default=None, max_length=128)


class ExpectedVisualizationCorrectionV2(StrictFeedbackModel):
    kind: Literal["EXPECTED_VISUALIZATION"] = "EXPECTED_VISUALIZATION"
    visualization: Literal["AUTO", "TABLE", "BAR_CHART", "LINE_CHART", "PIE_CHART", "KPI_CARD"]


class ExpectedRelationshipCorrectionV2(StrictFeedbackModel):
    kind: Literal["EXPECTED_RELATIONSHIP"] = "EXPECTED_RELATIONSHIP"
    relationship: Literal["FOLLOW_UP", "REFINEMENT", "COMPARISON", "RESET", "NEW_TOPIC"]


class ExpectedClarificationCorrectionV2(StrictFeedbackModel):
    kind: Literal["EXPECTED_CLARIFICATION"] = "EXPECTED_CLARIFICATION"
    missing_field: str = Field(min_length=1, max_length=128)
    expected_question: str = Field(min_length=1, max_length=500)


class ExpectedScopeCorrectionV2(StrictFeedbackModel):
    kind: Literal["EXPECTED_SCOPE"] = "EXPECTED_SCOPE"
    scope: Literal["IN_SCOPE", "OUT_OF_SCOPE", "REQUIRES_SPECIALIST"]
    reason: str = Field(min_length=1, max_length=500)


class FreeTextExplanationCorrectionV2(StrictFeedbackModel):
    kind: Literal["FREE_TEXT_EXPLANATION"] = "FREE_TEXT_EXPLANATION"
    explanation: str = Field(min_length=1, max_length=2000)


StructuredCorrectionV2 = Annotated[
    ExpectedMetricCorrectionV2
    | ExpectedPeriodCorrectionV2
    | ExpectedFilterCorrectionV2
    | ExpectedEntityCorrectionV2
    | ExpectedDimensionCorrectionV2
    | ExpectedComparisonCorrectionV2
    | ExpectedVisualizationCorrectionV2
    | ExpectedRelationshipCorrectionV2
    | ExpectedClarificationCorrectionV2
    | ExpectedScopeCorrectionV2
    | FreeTextExplanationCorrectionV2,
    Field(discriminator="kind"),
]


class FeedbackCorrectionV2(StrictFeedbackModel):
    items: list[StructuredCorrectionV2] = Field(default_factory=list, max_length=20)


class FeedbackSubmissionV2(StrictFeedbackModel):
    target: FeedbackTargetV2
    category: FeedbackCategoryV2
    correction: FeedbackCorrectionV2 | None = None
    explanation: str | None = Field(default=None, max_length=2000)
    idempotency_key: str = Field(min_length=8, max_length=128)
    contract_version: Literal[SUPERVISED_FEEDBACK_VERSION] = SUPERVISED_FEEDBACK_VERSION

    @model_validator(mode="after")
    def validate_negative_detail(self) -> "FeedbackSubmissionV2":
        if self.category not in {FeedbackCategoryV2.POSITIVE, FeedbackCategoryV2.PERFORMANCE}:
            if self.correction is None and not self.explanation:
                raise ValueError("non-positive feedback requires correction or explanation")
        return self


class FeedbackEvidenceReferenceV2(StrictFeedbackModel):
    reference_type: Literal[
        "RESPONSE_NODE",
        "QUERY_NODE",
        "SEARCH_HISTORY",
        "VALIDATION_CHECK",
        "KNOWLEDGE_ASSET",
        "CONTRACT",
    ]
    reference_id: str = Field(min_length=1, max_length=256)
    checksum: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    description: str | None = Field(default=None, max_length=500)


class RedactedFieldV2(StrictFeedbackModel):
    field_name: str = Field(min_length=1, max_length=128)
    reason_code: str = Field(min_length=1, max_length=64)


class FeedbackRedactionManifestV2(StrictFeedbackModel):
    manifest_id: uuid.UUID
    policy_version: str = Field(min_length=1, max_length=64)
    removed_fields: list[RedactedFieldV2] = Field(default_factory=list, max_length=100)
    transformed_fields: list[RedactedFieldV2] = Field(default_factory=list, max_length=100)
    original_size_bytes: int = Field(ge=0)
    redacted_size_bytes: int = Field(ge=0)
    sensitive_content_detected: bool
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")


class FeedbackTriageResultV2(StrictFeedbackModel):
    triage_id: uuid.UUID
    category: FeedbackCategoryV2
    severity: FeedbackSeverity
    priority: FeedbackPriority
    review_queue: Literal["GENERAL", "DATA_INTEGRITY", "SECURITY", "CONTEXT", "VISUALIZATION", "PERFORMANCE"]
    duplicate_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    suspected_security: bool = False
    suspected_formula_conflict: bool = False
    suspected_tenant_issue: bool = False
    needs_specialist: bool = False
    classification_confidence: int = Field(ge=0, le=100)
    rule_ids: list[str] = Field(default_factory=list, max_length=50)
    warnings: list[str] = Field(default_factory=list, max_length=50)
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")


class FeedbackShadowEvaluationV2(StrictFeedbackModel):
    target_authorized: bool
    checksum_matches: bool
    category: FeedbackCategoryV2
    severity: FeedbackSeverity | None = None
    redaction_detected: bool
    duplicate_fingerprint: str | None = Field(
        default=None, pattern=r"^[a-f0-9]{64}$"
    )
    eligible_for_collection: bool
    persisted: Literal[False] = False
    reason_codes: list[str] = Field(default_factory=list, max_length=20)
    contract_version: Literal[SUPERVISED_FEEDBACK_VERSION] = (
        SUPERVISED_FEEDBACK_VERSION
    )
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")


class FeedbackReviewV2(StrictFeedbackModel):
    review_id: uuid.UUID
    feedback_id: uuid.UUID
    reviewer_user_id: uuid.UUID
    decision: FeedbackReviewDecisionV2
    rationale: str = Field(min_length=1, max_length=2000)
    evidence: list[FeedbackEvidenceReferenceV2] = Field(default_factory=list, max_length=50)
    expected_lock_version: int = Field(ge=0)
    created_at: datetime
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")


class FeedbackDisagreementV2(StrictFeedbackModel):
    disagreement_id: uuid.UUID
    feedback_id: uuid.UUID
    first_review_id: uuid.UUID
    second_review_id: uuid.UUID
    resolution: FeedbackReviewDecisionV2 | None = None
    rationale: str | None = Field(default=None, max_length=2000)


class FeedbackRecordV2(StrictFeedbackModel):
    feedback_id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    target: FeedbackTargetV2
    category: FeedbackCategoryV2
    correction: FeedbackCorrectionV2 | None = None
    explanation: str | None = None
    lifecycle: FeedbackLifecycle
    triage: FeedbackTriageResultV2 | None = None
    reviewer_user_id: uuid.UUID | None = None
    review_decision: FeedbackReviewDecisionV2 | None = None
    duplicate_group: str = Field(pattern=r"^[a-f0-9]{64}$")
    redaction_manifest_id: uuid.UUID
    lock_version: int = Field(ge=0)
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    created_at: datetime
    updated_at: datetime
    contract_version: Literal[SUPERVISED_FEEDBACK_VERSION] = SUPERVISED_FEEDBACK_VERSION


class CanonicalFilterSnapshotV2(StrictFeedbackModel):
    field_id: str = Field(min_length=1, max_length=128)
    operator: str = Field(min_length=1, max_length=32)
    values: list[str | int | float | bool] = Field(default_factory=list, max_length=100)


class TrainingExampleInputV2(StrictFeedbackModel):
    minimized_question: str = Field(min_length=1, max_length=2000)
    intent_kind: str = Field(min_length=1, max_length=64)
    metric_ids: list[str] = Field(default_factory=list, max_length=50)
    dimension_ids: list[str] = Field(default_factory=list, max_length=50)
    entity_ids: list[str] = Field(default_factory=list, max_length=50)
    time_windows: list[str] = Field(default_factory=list, max_length=20)
    filters: list[CanonicalFilterSnapshotV2] = Field(default_factory=list, max_length=100)
    requested_visualizations: list[str] = Field(default_factory=list, max_length=20)
    relationship: str | None = Field(default=None, max_length=64)
    locale: str = Field(default="pt-BR", max_length=16)
    timezone: str = Field(default="America/Sao_Paulo", max_length=64)


class TrainingExampleExpectedOutputV2(StrictFeedbackModel):
    expected_classification: FeedbackReviewDecisionV2
    expected_corrections: FeedbackCorrectionV2 | None = None
    expected_readiness: str | None = Field(default=None, max_length=32)
    expected_response_shape: str | None = Field(default=None, max_length=64)
    expected_error_code: str | None = Field(default=None, max_length=128)


class TrainingExampleCandidateV2(StrictFeedbackModel):
    candidate_id: uuid.UUID
    feedback_id: uuid.UUID
    tenant_id: uuid.UUID
    status: CandidateStatus
    input: TrainingExampleInputV2
    expected_output: TrainingExampleExpectedOutputV2
    quality_status: ExampleQualityStatus
    quality_rule_ids: list[str] = Field(default_factory=list, max_length=100)
    lock_version: int = Field(ge=0)
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    created_at: datetime


class ApprovedTrainingExampleV2(StrictFeedbackModel):
    example_id: uuid.UUID
    candidate_id: uuid.UUID
    tenant_scope: uuid.UUID | None
    input: TrainingExampleInputV2
    expected_output: TrainingExampleExpectedOutputV2
    classification: FeedbackReviewDecisionV2
    applicable_contract_versions: list[str] = Field(min_length=1, max_length=50)
    domain: str = Field(min_length=1, max_length=128)
    locale: str = Field(default="pt-BR", max_length=16)
    source_feedback_ids: list[uuid.UUID] = Field(min_length=1, max_length=50)
    redaction_manifest_id: uuid.UUID
    reviewer_user_id: uuid.UUID
    curator_user_id: uuid.UUID
    quality_score: int = Field(ge=0, le=100)
    restrictions: list[str] = Field(default_factory=list, max_length=50)
    review_after: datetime | None = None
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")


class TrainingDatasetManifestV2(StrictFeedbackModel):
    dataset_id: uuid.UUID
    version: int = Field(ge=1)
    schema_version: str = Field(min_length=1, max_length=64)
    contract_version: Literal[SUPERVISED_FEEDBACK_VERSION] = SUPERVISED_FEEDBACK_VERSION
    example_checksums: list[str] = Field(default_factory=list, max_length=100000)
    redaction_policy_version: str = Field(min_length=1, max_length=64)
    inclusion_criteria: list[str] = Field(default_factory=list, max_length=100)
    exclusion_criteria: list[str] = Field(default_factory=list, max_length=100)
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")


class TrainingDatasetSnapshotV2(StrictFeedbackModel):
    snapshot_id: uuid.UUID
    dataset_id: uuid.UUID
    tenant_id: uuid.UUID | None
    version: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=1000)
    purpose: str = Field(min_length=1, max_length=500)
    status: DatasetStatus
    example_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100000)
    manifest: TrainingDatasetManifestV2
    created_by_user_id: uuid.UUID
    reviewed_by_user_id: uuid.UUID | None = None
    approved_by_user_id: uuid.UUID | None = None
    created_at: datetime
    published_at: datetime | None = None
    lock_version: int = Field(ge=0)
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")


class TrainingDatasetExportV2(StrictFeedbackModel):
    export_id: uuid.UUID
    snapshot_id: uuid.UUID
    format: Literal["JSONL", "CSV"]
    purpose: str = Field(min_length=1, max_length=500)
    record_count: int = Field(ge=0)
    payload_size_bytes: int = Field(ge=0)
    manifest_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    content_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    created_at: datetime


class EvaluationCaseV2(StrictFeedbackModel):
    evaluation_id: uuid.UUID
    kind: EvaluationKind
    name: str = Field(min_length=1, max_length=128)
    input: TrainingExampleInputV2
    expected_output: TrainingExampleExpectedOutputV2
    runner_id: str = Field(min_length=1, max_length=128)
    tolerance: str | None = Field(default=None, max_length=64)
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")


class EvaluationResultV2(StrictFeedbackModel):
    evaluation_id: uuid.UUID
    status: Literal["PASSED", "FAILED", "BLOCKED"]
    structural_match: bool
    rule_ids: list[str] = Field(default_factory=list, max_length=100)
    executed_at: datetime
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")


class FeedbackAuditEventV2(StrictFeedbackModel):
    event_id: uuid.UUID
    feedback_id: uuid.UUID | None = None
    tenant_id: uuid.UUID
    actor_user_id: uuid.UUID
    event_type: str = Field(min_length=1, max_length=64)
    reason_code: str = Field(min_length=1, max_length=128)
    request_id: str | None = Field(default=None, max_length=128)
    structural_metadata: list[str] = Field(default_factory=list, max_length=100)
    created_at: datetime
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")


class FeedbackAccessDecisionV2(StrictFeedbackModel):
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    permission: FeedbackPermission
    allowed: bool
    reason_code: str = Field(min_length=1, max_length=64)


class FeedbackExportV2(StrictFeedbackModel):
    export_id: uuid.UUID
    feedback_ids: list[uuid.UUID] = Field(default_factory=list, max_length=10000)
    format: Literal["JSON", "JSONL"]
    record_count: int = Field(ge=0)
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    created_at: datetime


class GovernedImportDryRunRequestV2(StrictFeedbackModel):
    source_kind: Literal[
        "GOVERNED_DATASET_EXPORT",
        "VERSIONED_EVALUATION_CASE",
        "SYNTHETIC_FIXTURE",
    ]
    format: Literal["JSONL"] = "JSONL"
    schema_version: str = Field(min_length=1, max_length=64)
    lines: list[str] = Field(default_factory=list, max_length=10000)
    content_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    idempotency_key: str = Field(min_length=8, max_length=128)
    dry_run: Literal[True] = True


class GovernedImportDryRunResultV2(StrictFeedbackModel):
    source_kind: Literal[
        "GOVERNED_DATASET_EXPORT",
        "VERSIONED_EVALUATION_CASE",
        "SYNTHETIC_FIXTURE",
    ]
    record_count: int = Field(ge=0)
    valid_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    issues: list[str] = Field(default_factory=list, max_length=100)
    dry_run: Literal[True] = True
    persisted: Literal[False] = False
    published: Literal[False] = False
    content_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    result_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_counts(self) -> "GovernedImportDryRunResultV2":
        if self.valid_count + self.rejected_count != self.record_count:
            raise ValueError("valid and rejected counts must equal record count")
        return self


class FeedbackDeletionRequestV2(StrictFeedbackModel):
    request_id: uuid.UUID
    feedback_id: uuid.UUID
    status: Literal["PENDING", "COMPLETED", "REJECTED"]
    reason: str | None = Field(default=None, max_length=500)
    requested_at: datetime
    completed_at: datetime | None = None
