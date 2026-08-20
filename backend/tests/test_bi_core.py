"""
LuminaAI — Testes do Motor Executivo de Business Intelligence (BI Core)

Valida:
  1. Comportamento e a estrutura obrigatória de 8 tópicos de generate_data_insights.
  2. Extração de preferências da sessão de histórico (detect_user_session_profile).
  3. Injeção de instruções e histórico nas chamadas de insights de IA.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch, AsyncMock
from services.ai_service import generate_data_insights, detect_user_session_profile

@pytest.mark.asyncio(loop_scope="session")
async def test_generate_data_insights_structure():
    mock_response = AsyncMock()
    mock_choice = AsyncMock()
    mock_choice.message.content = (
        "## 1. RESUMO EXECUTIVO\n"
        "As vendas apresentaram um comportamento de crescimento estável.\n\n"
        "## 2. PRINCIPAIS INDICADORES\n"
        "- **Faturamento:** R$ 150.000\n\n"
        "## 3. ANÁLISE COMPARATIVA\n"
        "Crescimento de 15% em relação ao período anterior.\n\n"
        "## 4. INSIGHTS ESTRATÉGICOS\n"
        "A região Sul liderou a expansão de receitas.\n\n"
        "## 5. RISCOS IDENTIFICADOS\n"
        "Foi detectado risco de ruptura de estoque para o produto principal.\n\n"
        "## 6. OPORTUNIDADES IDENTIFICADAS\n"
        "Oportunidade de alavancar o mercado do Norte com campanhas locais.\n\n"
        "## 7. RECOMENDAÇÕES EXECUTIVAS\n"
        "1. Reforçar o estoque do produto principal.\n\n"
        "## 8. OBSERVAÇÕES FINAIS\n"
        "Reunião trimestral agendada para alinhar as metas."
    )
    mock_response.choices = [mock_choice]

    # Patch do singleton getter
    with patch("services.ai_service.ai_invocation_manager.invoke") as mock_execute:
        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response

        async def _execute_with_mock(**kwargs):
            return await kwargs["operation"](mock_client, "gpt-4o-mini", None)

        mock_execute.side_effect = _execute_with_mock

        # Executa a geração de insights
        pergunta = "Como foram as vendas de Junho?"
        dados = [{"id": 1, "mes": "Junho", "faturamento": 150000}]
        view_name = "VW_PERFORMANCE_VENDEDORES"
        
        analise = await generate_data_insights(
            pergunta=pergunta,
            dados=dados,
            view_name=view_name
        )

        # Asserta presença de todos os cabeçalhos obrigatórios
        assert "## 1. RESUMO EXECUTIVO" in analise
        assert "## 2. PRINCIPAIS INDICADORES" in analise
        assert "## 3. ANÁLISE COMPARATIVA" in analise
        assert "## 4. INSIGHTS ESTRATÉGICOS" in analise
        assert "## 5. RISCOS IDENTIFICADOS" in analise
        assert "## 6. OPORTUNIDADES IDENTIFICADAS" in analise
        assert "## 7. RECOMENDAÇÕES EXECUTIVAS" in analise
        assert "## 8. OBSERVAÇÕES FINAIS" in analise


def test_detect_user_session_profile():
    # Caso 1: Sem histórico
    assert detect_user_session_profile([]) == ""
    assert detect_user_session_profile(None) == ""

    # Caso 2: Histórico com preferências de tabelas e vendedores
    history = [
        {"role": "user", "content": "Quero ver a tabela de performance dos vendedores"},
        {"role": "assistant", "content": "## 1. RESUMO EXECUTIVO..."},
        {"role": "user", "content": "Mostre os detalhes de metas do vendedor João"},
    ]
    profile = detect_user_session_profile(history)
    assert "## MEMORIA DINAMICA DA SESSAO ATUAL:" in profile
    assert "TABLE" in profile
    assert "VENDEDOR" in profile


@pytest.mark.asyncio(loop_scope="session")
async def test_generate_data_insights_with_memory_and_context():
    mock_response = AsyncMock()
    mock_choice = AsyncMock()
    mock_choice.message.content = "## 1. RESUMO EXECUTIVO\nSucesso."
    mock_response.choices = [mock_choice]

    # Patch do singleton getter
    with patch("services.ai_service.ai_invocation_manager.invoke") as mock_execute:
        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response

        async def _execute_with_mock(**kwargs):
            return await kwargs["operation"](mock_client, "gpt-4o-mini", None)

        mock_execute.side_effect = _execute_with_mock

        history = [
            {"role": "user", "content": "Quero ver a tabela de performance dos vendedores"},
        ]
        custom_instructions = "Empresa vende fertilizantes e defensivos agrícolas."

        await generate_data_insights(
            pergunta="E as vendas de soja?",
            dados=[{"produto": "Soja", "faturamento": 200000}],
            view_name="VW_VENDAS_POR_PRODUTO",
            history=history,
            custom_instructions=custom_instructions
        )

        # Verifica se o prompt final injetou a memória da sessão e as regras de negócio
        called_args = mock_client.chat.completions.create.call_args[1]
        system_prompt = next(msg["content"] for msg in called_args["messages"] if msg["role"] == "system")
        
        assert "fertilizantes e defensivos agrícolas" in system_prompt
        assert "MEMORIA DINAMICA DA SESSAO ATUAL:" in system_prompt
        assert "TABLE" in system_prompt
        assert "VENDEDOR" in system_prompt
