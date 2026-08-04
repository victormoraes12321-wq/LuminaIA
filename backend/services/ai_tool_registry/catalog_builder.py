from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional
from contracts.ai_tool_registry_v2 import (
    AIToolCatalogItemV2,
    AIToolCatalogV2,
    AIToolDefinitionV2,
    AIToolRiskClass,
    AIToolSideEffect,
    AIToolType,
)


class AIToolCatalogBuilder:
    """
    Builds public, sanitized, minimized tool catalogs for LLM/Orchestrator consumption.
    Excludes internal implementation details, secrets, adapter IDs, and forbidden tools.
    """

    def build_catalog(
        self,
        snapshot_version: str,
        tool_definitions: List[AIToolDefinitionV2],
        allowed_capabilities: Optional[List[str]] = None,
        max_allowed_risk: AIToolRiskClass = AIToolRiskClass.HIGH,
    ) -> AIToolCatalogV2:
        items: List[AIToolCatalogItemV2] = []

        risk_order = {
            AIToolRiskClass.LOW: 1,
            AIToolRiskClass.MODERATE: 2,
            AIToolRiskClass.HIGH: 3,
            AIToolRiskClass.CRITICAL: 4,
            AIToolRiskClass.FORBIDDEN: 5,
        }
        max_risk_num = risk_order.get(max_allowed_risk, 3)

        for tool_def in tool_definitions:
            identity = tool_def.identity
            active_ver = tool_def.active_version
            if not active_ver or active_ver.lifecycle.value != "ACTIVE":
                continue

            # Check risk ceiling
            tool_risk_num = risk_order.get(identity.risk_class, 1)
            if tool_risk_num > max_risk_num or identity.risk_class == AIToolRiskClass.FORBIDDEN:
                continue

            # Check side effects
            if identity.side_effect in (AIToolSideEffect.FORBIDDEN, AIToolSideEffect.DESTRUCTIVE):
                continue

            # Check capabilities matching if specified
            if allowed_capabilities is not None:
                tool_caps = [c.value if hasattr(c, "value") else str(c) for c in identity.capabilities]
                if not any(cap in allowed_capabilities for cap in tool_caps):
                    continue

            # Construct minimized public catalog item
            items.append(
                AIToolCatalogItemV2(
                    tool_id=identity.tool_id,
                    canonical_name=identity.canonical_name,
                    display_name=identity.display_name,
                    description=identity.description,
                    version=active_ver.version,
                    tool_type=identity.tool_type,
                    capabilities=identity.capabilities,
                    risk_class=identity.risk_class,
                    side_effect=identity.side_effect,
                    input_json_schema=active_ver.input_contract.json_schema,
                )
            )

        serialized = json.dumps([item.model_dump() for item in items], sort_keys=True, default=str)
        checksum = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        return AIToolCatalogV2(
            snapshot_version=snapshot_version,
            items=items,
            catalog_checksum=checksum,
        )


ai_tool_catalog_builder = AIToolCatalogBuilder()
