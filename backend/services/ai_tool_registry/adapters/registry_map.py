from __future__ import annotations

from typing import Dict, Type
from services.ai_tool_registry.adapters.base import GovernedToolAdapter
from services.ai_tool_registry.adapters.knowledge_adapters import (
    EnterpriseKnowledgeGetMetricDefinitionToolAdapter,
    EnterpriseKnowledgeSearchToolAdapter,
)
from services.ai_tool_registry.adapters.temporal_adapter import (
    TemporalNormalizeToolAdapter,
)
from services.ai_tool_registry.adapters.semantic_adapters import (
    SemanticResolveEntityToolAdapter,
    SemanticSearchToolAdapter,
)
from services.ai_tool_registry.adapters.context_adapter import (
    ContextGetPublicSummaryToolAdapter,
)
from services.ai_tool_registry.adapters.profile_adapter import (
    ProfileGetApplicationSummaryToolAdapter,
)
from services.ai_tool_registry.adapters.intent_and_planner_adapters import (
    ClarificationBuildOptionsToolAdapter,
    ComparisonPlanToolAdapter,
    ComparisonValidatePlanToolAdapter,
    IntentValidateToolAdapter,
    ProvenanceGetPublicSummaryToolAdapter,
)
from services.ai_tool_registry.adapters.analytical_postgresql_adapter import (
    AnalyticalPostgreSQLQueryToolAdapter,
)

# STATIC ALLOWLISTED MAP OF GOVERNED TOOL ADAPTERS.
# Dynamic imports, eval, exec, and getattr on user/LLM text ARE ABSOLUTELY FORBIDDEN.
REGISTERED_TOOL_ADAPTERS: Dict[str, Type[GovernedToolAdapter]] = {
    "enterprise_knowledge.search.v1": EnterpriseKnowledgeSearchToolAdapter,
    "enterprise_knowledge.get_metric_definition.v1": EnterpriseKnowledgeGetMetricDefinitionToolAdapter,
    "temporal.normalize.v1": TemporalNormalizeToolAdapter,
    "semantic.search.v1": SemanticSearchToolAdapter,
    "semantic.resolve_entity.v1": SemanticResolveEntityToolAdapter,
    "context.get_public_summary.v1": ContextGetPublicSummaryToolAdapter,
    "profile.get_application_summary.v1": ProfileGetApplicationSummaryToolAdapter,
    "intent.validate.v1": IntentValidateToolAdapter,
    "comparison.plan.v1": ComparisonPlanToolAdapter,
    "comparison.validate_plan.v1": ComparisonValidatePlanToolAdapter,
    "clarification.build_options.v1": ClarificationBuildOptionsToolAdapter,
    "provenance.get_public_summary.v1": ProvenanceGetPublicSummaryToolAdapter,
    "analytical_postgresql.query.v1": AnalyticalPostgreSQLQueryToolAdapter,
}


def get_adapter_class(adapter_id: str) -> Type[GovernedToolAdapter]:
    """
    Returns the statically registered GovernedToolAdapter class for the given adapter_id.
    Raises ValueError if adapter_id is not present in the static allowlist.
    """
    if adapter_id not in REGISTERED_TOOL_ADAPTERS:
        raise ValueError(f"AI_TOOL_ADAPTER_NOT_REGISTERED: Adapter '{adapter_id}' is not allowlisted.")
    return REGISTERED_TOOL_ADAPTERS[adapter_id]
