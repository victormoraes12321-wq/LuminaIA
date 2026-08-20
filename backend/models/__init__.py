"""
LuminaAI — ORM Models Package

Importa e expõe todos os modelos ORM para uso centralizado.
Garante que todos os models são registrados na metadata do SQLAlchemy
antes de qualquer operação de banco (ex: create_all, Alembic migrations).

Uso:
    from models import Tenant, User, ViewCatalog, SearchHistory, Favorite
"""
from models.tenant import Tenant
from models.user import User, UserRole
from models.view_catalog import ViewCatalog, ChartType
from models.search_history import SearchHistory
from models.favorite import Favorite
from models.blueprint import Blueprint
from models.metadata_catalog import MetadataCatalog
from models.dataset import Dataset
from models.data_platform_history import DataPlatformHistory
from models.semantic_catalog import SemanticCatalog
from models.metadata_catalog_version import MetadataCatalogVersion
from models.sync_queue import SyncQueue
from models.analytical_package import AnalyticalPackage, PackageStatus
from models.package_dashboard_instance import PackageDashboardInstance
from models.dashboard_template import DashboardTemplate
from models.dashboard_instance import DashboardInstance
from models.dashboard_preference import DashboardPreference
from models.dashboard_studio_version import DashboardStudioVersion
from models.dashboard_backend_v2 import (
    DashboardAccessPolicyModelV2,
    DashboardActivePublicationModelV2,
    DashboardApprovalModelV2,
    DashboardAuditEventModelV2,
    DashboardCollaboratorModelV2,
    DashboardEvaluationCaseModelV2,
    DashboardEvaluationResultModelV2,
    DashboardModelV2,
    DashboardPublicationModelV2,
    DashboardRevisionModelV2,
    DashboardReviewModelV2,
    DashboardRuntimeExecutionModelV2,
    DashboardWidgetExecutionModelV2,
)
from models.dashboard_ai_assistance_v2 import (
    DashboardAiAuditEventModelV2,
    DashboardAiClarificationModelV2,
    DashboardAiDecisionModelV2,
    DashboardAiEvaluationCaseModelV2,
    DashboardAiEvaluationResultModelV2,
    DashboardAiEvidenceModelV2,
    DashboardAiProposalModelV2,
    DashboardAiProposalVersionModelV2,
    DashboardAiRunModelV2,
)
from models.business_concept import BusinessConcept
from models.business_kpi import BusinessKPI
from models.business_formula import BusinessFormula
from models.business_relationship import BusinessRelationship
from models.business_governance_log import BusinessGovernanceLog
from models.semantic_memory import SemanticMemory
from models.svr import SVRConcept, SVRVersion, SVRCompatibilityMatrix, SVRAuditLog
from models.conversation_state import (
    ConversationEvent,
    ConversationLegacyImport,
    ConversationNodeRecord,
    ConversationSession,
    ConversationStateSnapshot,
)
from models.enterprise_knowledge import (
    EnterpriseKnowledgeAlias,
    EnterpriseKnowledgeApproval,
    EnterpriseKnowledgeAsset,
    EnterpriseKnowledgeEvent,
    EnterpriseKnowledgeImport,
    EnterpriseKnowledgePublication,
    EnterpriseKnowledgeRelation,
    EnterpriseKnowledgeVersion,
)
from models.user_analytical_profile import (
    UserAnalyticalProfile,
    UserPreferenceConsent,
    UserPreferenceItem,
    UserProfileDeletionRequest,
    UserProfileEvent,
    UserProfileExport,
)
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
from models.semantic_retrieval import (
    SemanticClarification,
    SemanticDocument,
    SemanticDocumentAlias,
    SemanticDocumentRelation,
    SemanticDocumentRepresentation,
    SemanticDocumentTerm,
    SemanticEvaluationCase,
    SemanticEvaluationResult,
    SemanticIndexDefinition,
    SemanticIndexEvent,
    SemanticIndexPublication,
    SemanticIndexVersion,
)
from models.ai_tool_registry import (
    AIToolCircuitStateRecord,
    AIToolDependency,
    AIToolEvaluationCaseRecord,
    AIToolEvaluationResultRecord,
    AIToolEvent,
    AIToolIdentity,
    AIToolInvocationRecord,
    AIToolPublication,
    AIToolRegistryMember,
    AIToolRegistrySnapshot,
    AIToolReview,
    AIToolVersion,
)
from models.ai_orchestration import (
    AIEvaluationCaseModel,
    AIEvaluationResultModel,
    AIModelDefinitionModel,
    AIModelInvocationRecordModel,
    AIOrchestrationPolicyModel,
    AIOrchestrationRunModel,
    AIOrchestrationStepModel,
    AIPromptTemplateVersionModel,
    AIProviderDefinitionModel,
    AIToolCallRecordModel,
    AIUsageRecordModel,
)

from models.validation_provenance import (
    AnalyticalClaimBindingModel,
    AnalyticalClaimModel,
    AnalyticalFactModel,
    ProvenanceManifestModel,
    ResponseCertificationModel,
    ResultCertificationModel,
    ValidationEventModel,
    ValidationPolicyModel,
    ValidationRunModel,
)
__all__: list[str] = [
    "Tenant",
    "User",
    "UserRole",
    "ViewCatalog",
    "ChartType",
    "SearchHistory",
    "Favorite",
    "Blueprint",
    "MetadataCatalog",
    "MetadataCatalogVersion",
    "Dataset",
    "DataPlatformHistory",
    "SemanticCatalog",
    "SyncQueue",
    "AnalyticalPackage",
    "PackageStatus",
    "PackageDashboardInstance",
    "DashboardTemplate",
    "DashboardInstance",
    "DashboardPreference",
    "DashboardStudioVersion",
    "DashboardModelV2",
    "DashboardRevisionModelV2",
    "DashboardReviewModelV2",
    "DashboardApprovalModelV2",
    "DashboardPublicationModelV2",
    "DashboardActivePublicationModelV2",
    "DashboardCollaboratorModelV2",
    "DashboardAccessPolicyModelV2",
    "DashboardAuditEventModelV2",
    "DashboardRuntimeExecutionModelV2",
    "DashboardWidgetExecutionModelV2",
    "DashboardEvaluationCaseModelV2",
    "DashboardEvaluationResultModelV2",
    "DashboardAiProposalModelV2",
    "DashboardAiProposalVersionModelV2",
    "DashboardAiClarificationModelV2",
    "DashboardAiEvidenceModelV2",
    "DashboardAiDecisionModelV2",
    "DashboardAiRunModelV2",
    "DashboardAiAuditEventModelV2",
    "DashboardAiEvaluationCaseModelV2",
    "DashboardAiEvaluationResultModelV2",
    "BusinessConcept",
    "BusinessKPI",
    "BusinessFormula",
    "BusinessRelationship",
    "BusinessGovernanceLog",
    "SemanticMemory",
    "SVRConcept",
    "SVRVersion",
    "SVRCompatibilityMatrix",
    "SVRAuditLog",
    "ConversationSession",
    "ConversationNodeRecord",
    "ConversationStateSnapshot",
    "ConversationEvent",
    "ConversationLegacyImport",
    "EnterpriseKnowledgeAlias",
    "EnterpriseKnowledgeApproval",
    "EnterpriseKnowledgeAsset",
    "EnterpriseKnowledgeEvent",
    "EnterpriseKnowledgeImport",
    "EnterpriseKnowledgePublication",
    "EnterpriseKnowledgeRelation",
    "EnterpriseKnowledgeVersion",
    "UserAnalyticalProfile",
    "UserPreferenceItem",
    "UserPreferenceConsent",
    "UserProfileEvent",
    "UserProfileExport",
    "UserProfileDeletionRequest",
    "GovernedFeedbackRecord",
    "GovernedFeedbackCorrection",
    "GovernedFeedbackRedaction",
    "GovernedFeedbackReview",
    "GovernedFeedbackEvent",
    "SupervisedTrainingCandidate",
    "SupervisedTrainingExample",
    "TrainingDatasetSnapshot",
    "TrainingDatasetMember",
    "TrainingDatasetExport",
    "FeedbackDeletionRequest",
    "SemanticIndexDefinition",
    "SemanticIndexVersion",
    "SemanticDocument",
    "SemanticDocumentAlias",
    "SemanticDocumentRelation",
    "SemanticDocumentTerm",
    "SemanticDocumentRepresentation",
    "SemanticIndexPublication",
    "SemanticIndexEvent",
    "SemanticEvaluationCase",
    "SemanticEvaluationResult",
    "SemanticClarification",
    "AIToolIdentity",
    "AIToolVersion",
    "AIToolReview",
    "AIToolPublication",
    "AIToolRegistrySnapshot",
    "AIToolRegistryMember",
    "AIToolDependency",
    "AIToolEvent",
    "AIToolInvocationRecord",
    "AIToolCircuitStateRecord",
    "AIToolEvaluationCaseRecord",
    "AIToolEvaluationResultRecord",
    "AIOrchestrationPolicyModel",
    "AIModelDefinitionModel",
    "AIProviderDefinitionModel",
    "AIPromptTemplateVersionModel",
    "AIOrchestrationRunModel",
    "AIOrchestrationStepModel",
    "AIModelInvocationRecordModel",
    "AIToolCallRecordModel",
    "AIUsageRecordModel",
    "AIEvaluationCaseModel",
    "AIEvaluationResultModel",
    "ValidationPolicyModel",
    "ValidationRunModel",
    "AnalyticalFactModel",
    "AnalyticalClaimModel",
    "AnalyticalClaimBindingModel",
    "ProvenanceManifestModel",
    "ResultCertificationModel",
    "ResponseCertificationModel",
    "ValidationEventModel",
]
