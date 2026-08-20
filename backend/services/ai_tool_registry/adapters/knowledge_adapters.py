from __future__ import annotations

from typing import Any, Dict, List
from contracts.ai_tool_registry_v2 import (
    AIToolCapability,
    AIToolInvocationContextV2,
    AIToolValidatedArgumentsV2,
)
from services.ai_tool_registry.adapters.base import GovernedToolAdapter


class EnterpriseKnowledgeSearchToolAdapter(GovernedToolAdapter):
    """Adapter for searching published enterprise knowledge."""

    @property
    def adapter_id(self) -> str:
        return "enterprise_knowledge.search.v1"

    @property
    def tool_id(self) -> str:
        return "lumina.enterprise_knowledge.search"

    @property
    def tool_version(self) -> str:
        return "1.0.0"

    async def validate_registration(self) -> None:
        pass

    async def validate_context(self, context: AIToolInvocationContextV2) -> None:
        if not context.tenant_id:
            raise ValueError("Tenant authentication context required.")

    async def validate_arguments(self, raw_args: Dict[str, Any]) -> AIToolValidatedArgumentsV2:
        query = str(raw_args.get("query") or "").strip()
        if not query:
            raise ValueError("Argument 'query' is required and cannot be empty.")
        top_k = int(raw_args.get("top_k", 5))
        if top_k < 1 or top_k > 20:
            top_k = 5
        clean_args = {"query": query, "top_k": top_k}
        checksum = self.compute_args_checksum(clean_args)
        return AIToolValidatedArgumentsV2(
            tool_id=self.tool_id,
            version=self.tool_version,
            validated_args=clean_args,
            args_checksum=checksum,
        )

    async def execute(
        self, valid_args: AIToolValidatedArgumentsV2, context: AIToolInvocationContextV2
    ) -> Dict[str, Any]:
        from services.enterprise_knowledge import get_enterprise_knowledge_service

        service = get_enterprise_knowledge_service()
        query = valid_args.validated_args["query"]
        top_k = valid_args.validated_args["top_k"]

        raw_results = await service.search_published_assets(
            tenant_id=context.tenant_id,
            query=query,
            top_k=top_k,
        )
        items = []
        for res in raw_results.get("items", []):
            items.append({
                "asset_id": str(res.get("asset_id")),
                "title": res.get("title"),
                "summary": res.get("summary"),
                "asset_type": res.get("asset_type"),
                "score": float(res.get("score", 1.0)),
            })

        return {
            "query": query,
            "items": items,
            "total_count": len(items),
        }

    async def validate_output(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        if "items" not in raw_result:
            raise ValueError("Output missing 'items' field.")
        return raw_result

    async def redact_output(
        self, raw_result: Dict[str, Any], context: AIToolInvocationContextV2
    ) -> Dict[str, Any]:
        # Filter out internal/private fields if any
        return raw_result

    async def health_check(self) -> bool:
        return True

    def capabilities(self) -> List[AIToolCapability]:
        return [AIToolCapability.SEARCH_ENTERPRISE_KNOWLEDGE]


class EnterpriseKnowledgeGetMetricDefinitionToolAdapter(GovernedToolAdapter):
    """Adapter for retrieving canonical metric definition."""

    @property
    def adapter_id(self) -> str:
        return "enterprise_knowledge.get_metric_definition.v1"

    @property
    def tool_id(self) -> str:
        return "lumina.enterprise_knowledge.get_metric_definition"

    @property
    def tool_version(self) -> str:
        return "1.0.0"

    async def validate_registration(self) -> None:
        pass

    async def validate_context(self, context: AIToolInvocationContextV2) -> None:
        if not context.tenant_id:
            raise ValueError("Tenant authentication context required.")

    async def validate_arguments(self, raw_args: Dict[str, Any]) -> AIToolValidatedArgumentsV2:
        metric_name = str(raw_args.get("metric_name") or "").strip()
        if not metric_name:
            raise ValueError("Argument 'metric_name' is required.")
        clean_args = {"metric_name": metric_name}
        checksum = self.compute_args_checksum(clean_args)
        return AIToolValidatedArgumentsV2(
            tool_id=self.tool_id,
            version=self.tool_version,
            validated_args=clean_args,
            args_checksum=checksum,
        )

    async def execute(
        self, valid_args: AIToolValidatedArgumentsV2, context: AIToolInvocationContextV2
    ) -> Dict[str, Any]:
        from services.metric_registry import METRIC_DEFINITIONS

        metric_name = valid_args.validated_args["metric_name"]
        metric_def = METRIC_DEFINITIONS.get(metric_name)

        if not metric_def:
            # Fallback: check if metric_name contains key substring
            for k, v in METRIC_DEFINITIONS.items():
                if metric_name.lower() in k.lower() or k.lower() in metric_name.lower():
                    metric_def = v
                    break

        if not metric_def:
            return {
                "metric_name": metric_name,
                "found": False,
                "definition": None,
            }

        def_payload = metric_def.to_payload()
        return {
            "metric_name": metric_name,
            "found": True,
            "definition": {
                "canonical_name": metric_name,
                "display_name": def_payload.get("label", metric_name),
                "description": def_payload.get("formula", ""),
                "unit": "BRL",
                "formula_provenance": "MetricRegistry (Deterministic)",
            },
        }

    async def validate_output(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        if "found" not in raw_result:
            raise ValueError("Output missing 'found' field.")
        return raw_result

    async def redact_output(
        self, raw_result: Dict[str, Any], context: AIToolInvocationContextV2
    ) -> Dict[str, Any]:
        return raw_result

    async def health_check(self) -> bool:
        return True

    def capabilities(self) -> List[AIToolCapability]:
        return [AIToolCapability.READ_METRIC_DEFINITION]
