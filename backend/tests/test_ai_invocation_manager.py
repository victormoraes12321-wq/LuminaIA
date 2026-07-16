from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from services.ai_invocation_manager import AIInvocationManager


class _FakeAIResponse:
    usage = SimpleNamespace(total_tokens=42)


@pytest.mark.asyncio
async def test_aim_reuses_cache_only_when_low_risk_and_safe():
    manager = AIInvocationManager()
    operation = AsyncMock(return_value=_FakeAIResponse())
    lease = SimpleNamespace(provider_id="openai")

    async def _execute_with_mock(**kwargs):
        return await kwargs["operation"](AsyncMock(), "gpt-4o-mini", lease)

    context = {
        "query": "associe semanticamente receita",
        "fresh_data_required": False,
        "expected_confidence": 90,
        "estimated_tokens": 220,
    }

    with patch("services.ai_invocation_manager.ai_credential_manager.execute_with_fallback") as mock_execute:
        mock_execute.side_effect = _execute_with_mock
        first = await manager.invoke(
            tenant_id=None,
            purpose="iar_semantic_fallback",
            requested_model="gpt-4o-mini",
            context=context,
            allow_response_reuse=True,
            operation=operation,
        )
        second = await manager.invoke(
            tenant_id=None,
            purpose="iar_semantic_fallback",
            requested_model="gpt-4o-mini",
            context=context,
            allow_response_reuse=True,
            operation=operation,
        )

    assert first is second
    assert mock_execute.call_count == 1
    status = manager.get_status()
    assert status["cache_hit_rate"] > 0
    assert status["ai_calls_avoided"] == 1


@pytest.mark.asyncio
async def test_aim_prioritizes_precision_for_high_risk_queries():
    manager = AIInvocationManager()
    operation = AsyncMock(return_value=_FakeAIResponse())
    lease = SimpleNamespace(provider_id="openai")

    async def _execute_with_mock(**kwargs):
        return await kwargs["operation"](AsyncMock(), "gpt-4o-mini", lease)

    context = {
        "query": "qual foi o faturamento e lucro por produto?",
        "fresh_data_required": False,
        "expected_confidence": 95,
        "estimated_tokens": 220,
    }

    with patch("services.ai_invocation_manager.ai_credential_manager.execute_with_fallback") as mock_execute:
        mock_execute.side_effect = _execute_with_mock
        await manager.invoke(
            tenant_id=None,
            purpose="iar_semantic_fallback",
            requested_model="gpt-4o-mini",
            context=context,
            allow_response_reuse=True,
            operation=operation,
        )
        await manager.invoke(
            tenant_id=None,
            purpose="iar_semantic_fallback",
            requested_model="gpt-4o-mini",
            context=context,
            allow_response_reuse=True,
            operation=operation,
        )

    assert mock_execute.call_count == 2
    status = manager.get_status()
    assert status["ai_calls"] == 2
    assert status["ai_calls_avoided"] == 0


def test_aim_decision_scores_are_bounded():
    manager = AIInvocationManager()
    decision = manager.decide(
        tenant_id="tenant-1",
        purpose="intent_detection",
        force_ai=True,
        context={
            "query": "ranking dos vendedores no mes",
            "semantic_similarity_score": 150,
            "blueprint_compatibility_score": -10,
            "expected_confidence": 0.91,
        },
    )

    scores = decision.scores
    assert decision.should_invoke_ai is True
    assert decision.strategy == "FULL_AI"
    assert scores.semantic_similarity_score == 100.0
    assert scores.blueprint_compatibility_score == 0.0
    assert scores.expected_confidence == 91.0
