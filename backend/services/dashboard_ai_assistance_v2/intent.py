from __future__ import annotations

from contracts.dashboard_ai_assistance_v2 import (
    DashboardAiAudienceV2,
    DashboardAiDesignIntentV2,
    DashboardAiObjectiveV2,
    DashboardAiOperationV2,
    DashboardAiSemanticChangeIntentV2,
)
from contracts.ai_orchestration_v2.identity import AIModelPurposeV2
from contracts.ai_orchestration_v2.registry import AIModelPolicyV2
from services.ai_orchestration.model_registry_service import GovernedAIModelRouter

from .integrity import assert_safe_untrusted_text, normalized_key


class DashboardAiIntentExtractionServiceV2:
    """Bounded deterministic fake-provider adapter; output is intent only."""

    def __init__(self) -> None:
        policy = AIModelPolicyV2(
            policy_id="dashboard-ai-intent-fake-policy", tenant_id="system",
            purpose_map={AIModelPurposeV2.INTENT_ASSISTANCE.value: "fake-deterministic-v1"},
            fallback_chain=["fake-deterministic-v1"], checksum="dashboard-ai-intent-policy-v1",
        )
        model, adapter = GovernedAIModelRouter().route_model(AIModelPurposeV2.INTENT_ASSISTANCE, policy)
        if adapter.provider_id != "fake_provider":
            raise RuntimeError("DASHBOARD_AI_PROVIDER_NOT_GOVERNED")
        self.model_id = model.canonical_model_id
        self.provider_id = adapter.provider_id

    def extract_design(self, instruction: str) -> DashboardAiDesignIntentV2:
        safe = assert_safe_untrusted_text(instruction)
        key = normalized_key(safe)
        metrics: list[str] = []
        for token in ("faturamento", "ticket medio", "desconto total", "desconto medio", "contas em aberto", "estoque", "lucro"):
            if token in key:
                metrics.append(token)
        dimensions = [token for token in ("produto", "filial", "vendedor", "categoria", "cliente", "mes") if token in key]
        periods = [token for token in ("hoje", "ontem", "este mes", "mes atual", "ultimo mes", "junho", "julho", "2026") if token in key]
        template = (
            "EXECUTIVE_OVERVIEW" if "executiv" in key else
            "PRODUCT_RANKING" if "ranking" in key else
            "COMPARATIVE_ANALYSIS" if "compar" in key else
            "RECEIVABLES" if "contas em aberto" in key else
            "INVENTORY" if "estoque" in key else
            "SALES_PERFORMANCE"
        )
        return DashboardAiDesignIntentV2(
            objective=DashboardAiObjectiveV2(summary=safe, template_hint=template),
            audience=DashboardAiAudienceV2(audience_type="EXECUTIVE" if "executiv" in key else "MANAGEMENT"),
            metric_mentions=tuple(metrics),
            dimension_mentions=tuple(dimensions),
            period_mentions=tuple(periods),
        )

    def extract_semantic(self, instruction: str, *, dashboard_id: str, revision_id: str) -> DashboardAiSemanticChangeIntentV2:
        design = self.extract_design(instruction)
        return DashboardAiSemanticChangeIntentV2(
            objective=design.objective.summary,
            target_dashboard_id=dashboard_id,
            target_revision_id=revision_id,
            metric_mentions=design.metric_mentions,
            dimension_mentions=design.dimension_mentions,
            period_mentions=design.period_mentions,
        )

    @staticmethod
    def assert_model_operation(operation: DashboardAiOperationV2) -> None:
        if operation not in {DashboardAiOperationV2.CREATE_DASHBOARD, DashboardAiOperationV2.PROPOSE_SEMANTIC_CHANGE, DashboardAiOperationV2.PROPOSE_VISUAL_CHANGE, DashboardAiOperationV2.REVISE_PROPOSAL}:
            raise ValueError("DASHBOARD_AI_MODEL_OPERATION_FORBIDDEN")
