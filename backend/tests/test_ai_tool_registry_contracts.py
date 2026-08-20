from __future__ import annotations

import pytest
from pydantic import ValidationError

from contracts.ai_tool_registry_v2 import (
    AIToolCapability,
    AIToolCatalogItemV2,
    AIToolCatalogV2,
    AIToolDataClass,
    AIToolIdentityV2,
    AIToolInputContractV2,
    AIToolInvocationContextV2,
    AIToolInvocationRequestV2,
    AIToolOutputContractV2,
    AIToolRiskClass,
    AIToolSideEffect,
    AIToolType,
)


def test_ai_tool_identity_contract_validation() -> None:
    identity = AIToolIdentityV2(
        tool_id="lumina.temporal.normalize",
        canonical_name="lumina.temporal.normalize",
        display_name="Temporal Expression Normalizer",
        description="Normalizes natural language time expressions into deterministic time windows.",
        capabilities=[AIToolCapability.NORMALIZE_TEMPORAL_EXPRESSION],
        risk_class=AIToolRiskClass.LOW,
        side_effect=AIToolSideEffect.READ_ONLY,
        created_at="2026-07-30T00:00:00Z",
        checksum="hash_123",
    )

    assert identity.tool_id == "lumina.temporal.normalize"
    assert identity.risk_class == AIToolRiskClass.LOW
    assert identity.side_effect == AIToolSideEffect.READ_ONLY
    assert identity.contract_version == "lumina.ai-tool-registry/1.0"


def test_ai_tool_contract_forbid_extra_fields() -> None:
    with pytest.raises(ValidationError):
        AIToolIdentityV2(
            tool_id="lumina.test",
            canonical_name="lumina.test",
            display_name="Test Tool",
            description="Test Tool Description",
            capabilities=[AIToolCapability.READ_ENTERPRISE_KNOWLEDGE],
            created_at="2026-07-30T00:00:00Z",
            checksum="hash_123",
            extra_forbidden_field="malicious_payload",
        )


def test_ai_tool_catalog_minimized_structure() -> None:
    item = AIToolCatalogItemV2(
        tool_id="lumina.temporal.normalize",
        canonical_name="lumina.temporal.normalize",
        display_name="Temporal Normalizer",
        description="Normalizes temporal expressions",
        version="1.0.0",
        tool_type=AIToolType.DOMAIN_READ,
        capabilities=[AIToolCapability.NORMALIZE_TEMPORAL_EXPRESSION],
        risk_class=AIToolRiskClass.LOW,
        side_effect=AIToolSideEffect.READ_ONLY,
        input_json_schema={"type": "object", "properties": {"expression": {"type": "string"}}},
    )

    catalog = AIToolCatalogV2(
        snapshot_version="1.0.0",
        items=[item],
        catalog_checksum="cat_hash",
    )

    assert len(catalog.items) == 1
    assert catalog.items[0].tool_id == "lumina.temporal.normalize"
    # Verify no python module or internal adapter ID in catalog item
    item_dict = catalog.items[0].model_dump()
    assert "adapter_id" not in item_dict
    assert "python_module" not in item_dict
