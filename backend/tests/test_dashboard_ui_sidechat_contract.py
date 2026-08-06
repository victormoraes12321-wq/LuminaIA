from __future__ import annotations

import json
import uuid

import pytest
from pydantic import TypeAdapter, ValidationError

from schemas.dashboard_ui_sidechat import (
    DASHBOARD_UI_SIDECHAT_CONTRACT_VERSION,
    DashboardSideChatActionV2,
    DashboardSideChatContextV2,
)
from schemas.query import QueryRequest, QueryResponse


def _context() -> dict[str, object]:
    return {
        "contract_version": DASHBOARD_UI_SIDECHAT_CONTRACT_VERSION,
        "dashboard_id": "dashboard.sales.001",
        "publication_id": "publication.sales.001",
        "revision_id": "revision.sales.001",
        "blueprint_semantic_checksum": "a" * 64,
        "visible_widget_ids": ["widget.revenue"],
        "selected_widget_id": "widget.revenue",
        "binding_ids": ["binding.revenue"],
        "metric_ids": ["metric.revenue"],
        "dimension_ids": ["dimension.month"],
        "filters": [{"filter_id": "filter.branch", "values": ["Centro"]}],
        "public_provenance_references": ["metric.revenue.public"],
        "certification_references": ["certification.revenue.001"],
        "conversation_session_id": "session.dashboard.001",
        "context_version": 2,
    }


def test_dashboard_sidechat_context_is_strict_and_contains_no_forbidden_fields():
    context = DashboardSideChatContextV2.model_validate_json(json.dumps(_context()))
    payload = context.model_dump(mode="json")
    serialized = context.model_dump_json()

    assert payload["dashboard_id"] == "dashboard.sales.001"
    for forbidden in ("sql", "binds", "dsn", "credentials", "tenant_id", "permissions", '"widgets"', "data_bindings", "rows"):
        assert forbidden not in serialized.lower()

    with pytest.raises(ValidationError):
        DashboardSideChatContextV2.model_validate_json(json.dumps({**_context(), "sql": "SELECT 1"}))


@pytest.mark.parametrize(
    "action",
    [
        {"action_type": "NO_ACTION"},
        {"action_type": "FOCUS_WIDGET", "widget_id": "widget.revenue"},
        {"action_type": "OPEN_PROVENANCE", "widget_id": "widget.revenue"},
        {"action_type": "APPLY_FILTER", "filter_id": "filter.branch", "values": ["Centro"]},
        {"action_type": "RESET_FILTERS"},
        {"action_type": "DRILLDOWN", "interaction_id": "interaction.product", "source_widget_id": "widget.revenue", "canonical_value": "product.001"},
        {
            "action_type": "VISUAL_PATCH_PROPOSAL",
            "dashboard_id": "dashboard.sales.001",
            "revision_id": "revision.sales.001",
            "semantic_checksum": "a" * 64,
            "operations": [{"operation": "REPLACE", "path": "/identity/title", "value": "Novo titulo"}],
            "summary": "Atualizar o titulo.",
        },
        {"action_type": "BLOCKED", "code": "SEMANTIC_EDIT_BLOCKED", "message": "Use o editor manual."},
    ],
)
def test_dashboard_sidechat_action_union_accepts_only_closed_actions(action: dict[str, object]):
    parsed = TypeAdapter(DashboardSideChatActionV2).validate_json(json.dumps(action))
    assert parsed.action_type == action["action_type"]


@pytest.mark.parametrize("action_type", ["PUBLISH_AI", "ROLLBACK_AI", "SEMANTIC_EDIT_AI", "OPEN_URL", "EXECUTE_SQL"])
def test_dashboard_sidechat_action_union_rejects_forbidden_actions(action_type: str):
    with pytest.raises(ValidationError):
        TypeAdapter(DashboardSideChatActionV2).validate_json(json.dumps({"action_type": action_type}))


def test_existing_query_contract_roundtrips_dashboard_context_and_typed_action():
    request = QueryRequest.model_validate_json(json.dumps({
        "pergunta": "Explique o widget de faturamento",
        "tenant_id": str(uuid.UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")),
        "dashboard_context": _context(),
    }))
    response = QueryResponse(
        query_id=uuid.uuid4(),
        pergunta_original=request.pergunta,
        dashboard_action={"action_type": "OPEN_PROVENANCE", "widget_id": "widget.revenue"},
    )

    assert request.dashboard_context is not None
    assert response.dashboard_action is not None
    assert response.dashboard_action.action_type == "OPEN_PROVENANCE"
