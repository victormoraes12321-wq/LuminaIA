import pytest
from unittest.mock import AsyncMock, patch

from schemas.query import QueryRequest
from services.ai_service import generate_data_insights


def test_query_request_schema():
    req = QueryRequest(
        pergunta="Qual o faturamento?",
        tenant_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    )
    assert req.mode == "analytical"
    assert req.session_id is None

    req_exec = QueryRequest(
        pergunta="Qual o faturamento?",
        tenant_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        mode="executive",
        session_id="chat-1",
    )
    assert req_exec.mode == "executive"
    assert req_exec.session_id == "chat-1"


@pytest.mark.asyncio
@patch("services.ai_service.ai_invocation_manager.invoke")
async def test_generate_data_insights_modes(mock_execute):
    mock_client = AsyncMock()
    mock_completions = AsyncMock()
    mock_response = AsyncMock()
    mock_response.choices = [
        AsyncMock(message=AsyncMock(content="Mocked response content"))
    ]
    mock_completions.create.return_value = mock_response
    mock_client.chat.completions = mock_completions

    async def _execute_with_mock(**kwargs):
        return await kwargs["operation"](mock_client, "gpt-4o-mini", None)

    mock_execute.side_effect = _execute_with_mock

    quick_response = await generate_data_insights(
        pergunta="vendas",
        dados={"calculos_bi_deterministicos": {}},
        view_name="VW_VENDAS",
        mode="operational",
    )
    assert "Dashboard" in quick_response
    mock_completions.create.assert_not_called()

    await generate_data_insights(
        pergunta="vendas",
        dados={"calculos_bi_deterministicos": {}},
        view_name="VW_VENDAS",
        mode="analytical",
    )
    _, kwargs = mock_completions.create.call_args
    messages = kwargs["messages"]
    system_msg = next(m["content"] for m in messages if m["role"] == "system")
    assert "Analista de Business Intelligence" in system_msg
    assert "## 2. COMPARACOES DISPONIVEIS" in system_msg

    await generate_data_insights(
        pergunta="vendas",
        dados={"calculos_bi_deterministicos": {}},
        view_name="VW_VENDAS",
        mode="executive",
    )
    _, kwargs = mock_completions.create.call_args
    messages = kwargs["messages"]
    system_msg = next(m["content"] for m in messages if m["role"] == "system")
    assert "Diretor Executivo" in system_msg
    assert "## 8. OBSERVACOES FINAIS" in system_msg
