from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TypeAlias

from pydantic import BaseModel, TypeAdapter


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
OUTPUT_DIRECTORY = REPOSITORY_ROOT / "docs" / "contracts" / "schemas"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from contracts.analytical_v2 import (  # noqa: E402
    AnalyticalResponseV2,
    ComparisonSpecification,
    QueryIntentV2,
    QueryPlanV2,
    VisualizationSpecification,
)
from contracts.enterprise_knowledge_v2 import (  # noqa: E402
    EnterpriseKnowledgeAssetV2,
    EnterpriseKnowledgeVersionV2,
    KnowledgeAccessDecisionV2,
    KnowledgeApprovalV2,
    KnowledgeAuditEventV2,
    KnowledgeDiffV2,
    KnowledgeExportV2,
    KnowledgeImportRequestV2,
    KnowledgeImportResultV2,
    KnowledgePublicationV2,
    KnowledgeResolutionResultV2,
    KnowledgeSearchRequestV2,
    KnowledgeSearchResultV2,
)
from contracts.user_analytical_profile_v2 import (  # noqa: E402
    AccessibilityPreferenceV2,
    AnalyticalDefaultPreferenceV2,
    FavoriteAssetPreferenceV2,
    InteractionPreferenceV2,
    LocalePreferenceV2,
    PreferenceApplicationDecisionV2,
    PreferenceApplicationResultV2,
    PreferenceAuditEventV2,
    PreferenceConflictV2,
    PreferenceConsentV2,
    PreferenceOriginV2,
    PresentationPreferenceV2,
    PrivacyPreferenceV2,
    ProfileAccessDecisionV2,
    ProfileDeletionRequestV2,
    ProfileExportV2,
    ProfilePatchV2,
    PublicAppliedPreferenceSummaryV2,
    RetentionPreferenceV2,
    SavedReferencePreferenceV2,
    UserAnalyticalProfileSummaryV2,
    UserAnalyticalProfileV2,
    UserPreferenceItemV2,
)
from contracts.supervised_feedback_v2 import (  # noqa: E402
    ApprovedTrainingExampleV2,
    EvaluationCaseV2,
    EvaluationResultV2,
    FeedbackAccessDecisionV2,
    FeedbackAuditEventV2,
    FeedbackCategoryV2,
    FeedbackCorrectionV2,
    FeedbackDeletionRequestV2,
    FeedbackDisagreementV2,
    FeedbackEvidenceReferenceV2,
    FeedbackExportV2,
    GovernedImportDryRunRequestV2,
    GovernedImportDryRunResultV2,
    FeedbackRecordV2,
    FeedbackRedactionManifestV2,
    FeedbackReviewDecisionV2,
    FeedbackReviewV2,
    FeedbackSubmissionV2,
    FeedbackShadowEvaluationV2,
    FeedbackTargetV2,
    FeedbackTriageResultV2,
    StructuredCorrectionV2,
    TrainingDatasetExportV2,
    TrainingDatasetManifestV2,
    TrainingDatasetSnapshotV2,
    TrainingExampleCandidateV2,
    TrainingExampleExpectedOutputV2,
    TrainingExampleInputV2,
)
from contracts.semantic_retrieval_v2 import (  # noqa: E402
    EntityResolutionPatchV2,
    EntityResolutionRequestV2,
    EntityResolutionResultV2,
    IndexAuditEventV2,
    IndexBuildRequestV2,
    IndexBuildResultV2,
    IndexDiffV2,
    IndexPublicationV2,
    IndexRollbackV2,
    SemanticCacheKeyV2,
    SemanticClarificationV2,
    SemanticDocumentV2,
    SemanticEvaluationCaseV2,
    SemanticEvaluationResultV2,
    SemanticIndexDefinitionV2,
    SemanticIndexVersionV2,
    SemanticSearchRequestV2,
    SemanticSearchResultV2,
)


ContractModel: TypeAlias = type[BaseModel]
SCHEMA_MODELS: tuple[ContractModel, ...] = (
    QueryIntentV2,
    QueryPlanV2,
    ComparisonSpecification,
    VisualizationSpecification,
    AnalyticalResponseV2,
    EnterpriseKnowledgeAssetV2,
    EnterpriseKnowledgeVersionV2,
    KnowledgeAccessDecisionV2,
    KnowledgeApprovalV2,
    KnowledgeAuditEventV2,
    KnowledgeDiffV2,
    KnowledgeExportV2,
    KnowledgeImportRequestV2,
    KnowledgeImportResultV2,
    KnowledgePublicationV2,
    KnowledgeResolutionResultV2,
    KnowledgeSearchRequestV2,
    KnowledgeSearchResultV2,
    UserAnalyticalProfileV2,
    UserAnalyticalProfileSummaryV2,
    UserPreferenceItemV2,
    PresentationPreferenceV2,
    LocalePreferenceV2,
    AccessibilityPreferenceV2,
    AnalyticalDefaultPreferenceV2,
    FavoriteAssetPreferenceV2,
    SavedReferencePreferenceV2,
    InteractionPreferenceV2,
    PrivacyPreferenceV2,
    RetentionPreferenceV2,
    PreferenceOriginV2,
    PreferenceConsentV2,
    PreferenceApplicationDecisionV2,
    PreferenceApplicationResultV2,
    PreferenceConflictV2,
    PreferenceAuditEventV2,
    ProfileExportV2,
    ProfileDeletionRequestV2,
    ProfileAccessDecisionV2,
    ProfilePatchV2,
    PublicAppliedPreferenceSummaryV2,
    FeedbackSubmissionV2,
    FeedbackRecordV2,
    FeedbackTargetV2,
    FeedbackCorrectionV2,
    FeedbackEvidenceReferenceV2,
    FeedbackRedactionManifestV2,
    FeedbackTriageResultV2,
    FeedbackShadowEvaluationV2,
    FeedbackReviewV2,
    FeedbackDisagreementV2,
    TrainingExampleCandidateV2,
    ApprovedTrainingExampleV2,
    TrainingExampleInputV2,
    TrainingExampleExpectedOutputV2,
    TrainingDatasetSnapshotV2,
    TrainingDatasetManifestV2,
    TrainingDatasetExportV2,
    EvaluationCaseV2,
    EvaluationResultV2,
    FeedbackAuditEventV2,
    FeedbackAccessDecisionV2,
    FeedbackExportV2,
    FeedbackDeletionRequestV2,
    GovernedImportDryRunRequestV2,
    GovernedImportDryRunResultV2,
    SemanticIndexDefinitionV2,
    SemanticIndexVersionV2,
    SemanticDocumentV2,
    SemanticSearchRequestV2,
    SemanticSearchResultV2,
    EntityResolutionRequestV2,
    EntityResolutionResultV2,
    EntityResolutionPatchV2,
    SemanticClarificationV2,
    IndexBuildRequestV2,
    IndexBuildResultV2,
    IndexPublicationV2,
    IndexRollbackV2,
    IndexDiffV2,
    IndexAuditEventV2,
    SemanticCacheKeyV2,
    SemanticEvaluationCaseV2,
    SemanticEvaluationResultV2,
)

SCHEMA_ADAPTERS: tuple[tuple[str, TypeAdapter], ...] = (
    ("FeedbackCategoryV2", TypeAdapter(FeedbackCategoryV2)),
    ("FeedbackReviewDecisionV2", TypeAdapter(FeedbackReviewDecisionV2)),
    ("StructuredCorrectionV2", TypeAdapter(StructuredCorrectionV2)),
)


def render_schema(model: ContractModel) -> str:
    payload = model.model_json_schema()
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def export_schemas(output_directory: Path = OUTPUT_DIRECTORY) -> list[Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for model in SCHEMA_MODELS:
        target = output_directory / f"{model.__name__}.schema.json"
        target.write_text(render_schema(model), encoding="utf-8", newline="\n")
        written.append(target)
    for name, adapter in SCHEMA_ADAPTERS:
        target = output_directory / f"{name}.schema.json"
        payload = adapter.json_schema()
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        written.append(target)
    return written


def main() -> int:
    try:
        for path in export_schemas():
            print(path.relative_to(REPOSITORY_ROOT))
    except Exception as exc:
        print(f"schema export failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
