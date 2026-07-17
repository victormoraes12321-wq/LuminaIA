import os
import json
import pytest
import uuid
from database import AsyncSessionLocal
from services.ai.csie import csie

# Descobre o caminho do arquivo de treinamento semântico
JSON_PATH = os.path.join(os.path.dirname(__file__), "knowledge_training.json")

def load_training_data():
    if not os.path.exists(JSON_PATH):
        return []
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", load_training_data())
async def test_semantic_knowledge_intelligence(scenario):
    """
    Valida a inteligência semântica do sistema traduzindo a pergunta analítica
    e verificando se os conceitos corporativos esperados (métricas, dimensões, período)
    são identificados corretamente pelo CSIE.
    """
    question = scenario["question"]
    expected_metrics = scenario.get("expected_metrics", [])
    expected_dimensions = scenario.get("expected_dimensions", [])
    expected_period = scenario.get("expected_period")

    async with AsyncSessionLocal() as db_session:
        tenant_id = uuid.uuid4()
        cip, score, origin = await csie.generate_corporate_intent_plan(
            pergunta=question,
            tenant_id=tenant_id,
            db=db_session
        )

        legacy_plan = cip.to_legacy_semantic_plan()

        # Valida as métricas
        for m in expected_metrics:
            assert m in legacy_plan["metrics"], f"Métrica esperada '{m}' ausente para a pergunta '{question}'"

        # Valida as dimensões
        for d in expected_dimensions:
            assert d in legacy_plan["dimensions"], f"Dimensão esperada '{d}' ausente para a pergunta '{question}'"

        # Valida o período
        if expected_period:
            assert legacy_plan["period"] == expected_period, f"Período esperado '{expected_period}' diferente de '{legacy_plan['period']}' para a pergunta '{question}'"
