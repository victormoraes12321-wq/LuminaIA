from __future__ import annotations

from typing import Any, Dict, List
from contracts.ai_tool_registry_v2 import (
    AIToolCapability,
    AIToolInvocationContextV2,
    AIToolValidatedArgumentsV2,
)
from services.ai_tool_registry.adapters.base import GovernedToolAdapter


class SemanticSearchToolAdapter(GovernedToolAdapter):
    """Adapter for searching published semantic retrieval index."""

    @property
    def adapter_id(self) -> str:
        return "semantic.search.v1"

    @property
    def tool_id(self) -> str:
        return "lumina.semantic.search"

    @property
    def tool_version(self) -> str:
        return "1.0.0"

    async def validate_registration(self) -> None:
        pass

    async def validate_context(self, context: AIToolInvocationContextV2) -> None:
        if not context.tenant_id:
            raise ValueError("Tenant authentication context required.")

    async def validate_arguments(self, raw_args: Dict[str, Any]) -> AIToolValidatedArgumentsV2:
        query_text = str(raw_args.get("query_text") or "").strip()
        if not query_text:
            raise ValueError("Argument 'query_text' is required.")
        top_k = int(raw_args.get("top_k", 5))
        if top_k < 1 or top_k > 20:
            top_k = 5
        clean_args = {"query_text": query_text, "top_k": top_k}
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
        from services.semantic_retrieval import get_semantic_retrieval_service

        service = get_semantic_retrieval_service()
        query_text = valid_args.validated_args["query_text"]
        top_k = valid_args.validated_args["top_k"]

        res = await service.search_index(
            tenant_id=context.tenant_id,
            query_text=query_text,
            top_k=top_k,
        )
        hits = []
        for h in res.get("hits", []):
            hits.append({
                "canonical_id": h.get("canonical_id"),
                "label": h.get("label"),
                "entity_type": h.get("entity_type"),
                "score": float(h.get("score", 1.0)),
            })

        return {
            "query_text": query_text,
            "hits": hits,
            "total_hits": len(hits),
        }

    async def validate_output(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        if "hits" not in raw_result:
            raise ValueError("Output missing 'hits' field.")
        return raw_result

    async def redact_output(
        self, raw_result: Dict[str, Any], context: AIToolInvocationContextV2
    ) -> Dict[str, Any]:
        return raw_result

    async def health_check(self) -> bool:
        return True

    def capabilities(self) -> List[AIToolCapability]:
        return [AIToolCapability.SEARCH_SEMANTIC_INDEX]


class SemanticResolveEntityToolAdapter(GovernedToolAdapter):
    """Adapter for entity resolution and ambiguity detection."""

    @property
    def adapter_id(self) -> str:
        return "semantic.resolve_entity.v1"

    @property
    def tool_id(self) -> str:
        return "lumina.semantic.resolve_entity"

    @property
    def tool_version(self) -> str:
        return "1.0.0"

    async def validate_registration(self) -> None:
        pass

    async def validate_context(self, context: AIToolInvocationContextV2) -> None:
        if not context.tenant_id:
            raise ValueError("Tenant authentication context required.")

    async def validate_arguments(self, raw_args: Dict[str, Any]) -> AIToolValidatedArgumentsV2:
        mention = str(raw_args.get("mention") or "").strip()
        if not mention:
            raise ValueError("Argument 'mention' is required.")
        clean_args = {"mention": mention}
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
        from services.semantic_retrieval import get_semantic_retrieval_service

        service = get_semantic_retrieval_service()
        mention = valid_args.validated_args["mention"]

        res = await service.resolve_entity_mention(
            tenant_id=context.tenant_id,
            mention=mention,
        )
        return {
            "mention": mention,
            "resolved": res.get("resolved", False),
            "is_ambiguous": res.get("is_ambiguous", False),
            "canonical_entity": res.get("canonical_entity"),
            "candidates": res.get("candidates", []),
        }

    async def validate_output(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        if "resolved" not in raw_result:
            raise ValueError("Output missing 'resolved' field.")
        return raw_result

    async def redact_output(
        self, raw_result: Dict[str, Any], context: AIToolInvocationContextV2
    ) -> Dict[str, Any]:
        return raw_result

    async def health_check(self) -> bool:
        return True

    def capabilities(self) -> List[AIToolCapability]:
        return [AIToolCapability.RESOLVE_ENTITY]
