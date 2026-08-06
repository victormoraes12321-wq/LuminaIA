"""Governed dashboard AI assistance, version 1.0."""
from .intent import DashboardAiIntentExtractionServiceV2
from .lifecycle import DashboardAiProposalStateMachineV2
from .policy import DashboardAiCapabilityV2, DashboardAiPolicyV2
from .rationale import DashboardAiRationaleServiceV2
from .resolution import DashboardDesignSpecServiceV2
from .semantic_compiler import DashboardAiSemanticPatchCompilerV2
from .synthesis import DashboardBlueprintSynthesisService
from .tool_registry import DashboardAiToolPolicyV2
from .validation import DashboardAiProposalValidationServiceV2
from .visual_proposal import DashboardAiVisualProposalServiceV2
from .errors import DashboardAiAssistanceError
from .repositories import *
from .service import DashboardAiAssistanceServiceV2, DashboardAiProposalApplicationServiceV2
from .facades import *

__all__ = [name for name in globals() if name.startswith("Dashboard")]
