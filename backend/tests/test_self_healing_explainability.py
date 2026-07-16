import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from models.new_pipeline_contracts import (
    SemanticPlan, CanonicalPlan, ExecutionPlan, ExecutionStatus, EmptyDatasetPolicy,
    IntentType, QueryCost, DashboardState, ConversationNode, ExecutionResult, QueryContext,
    VisualizationType, ResolvedEntities
)
from services.new_query_orchestrator import ExecutiveExplanation
from services.metadata_catalog.self_healing import SelfHealingEngine
from services.metadata_catalog.explainability import ExplainabilityEngine
from services.metadata_catalog.loader import load_corporate_catalog

@pytest.fixture(autouse=True)
def setup_catalog():
    load_corporate_catalog()

def test_self_healing_should_heal_unexpected_empty():
    engine = SelfHealingEngine()
    trace_id = str(uuid.uuid4())
    
    plan = ExecutionPlan(
        trace_id=uuid.uuid4(),
        status=ExecutionStatus.READY,
        resolved_entities=ResolvedEntities(entities={}, joins=[]),
        selected_views=["VW_VENDAS_LM"],
        columns=[],
        filters=[],
        group_by=[],
        order_by=[],
        having=[],
        cte=[],
        parameters={},
        estimated_cost=QueryCost.LOW,
        estimated_rows=10,
        execution_priority=1,
        cacheable=True,
        cache_key="key",
        required_permissions=[],
        timeout=30,
        empty_dataset_policy=EmptyDatasetPolicy.EMPTY_UNEXPECTED
    )
    
    # Dataset vazio + EMPTY_UNEXPECTED -> Deve curar!
    assert engine.should_heal(trace_id, ExecutionStatus.READY, [], plan) is True
    
    # Se já curou uma vez, bloqueia loop
    engine.mark_healed(trace_id)
    assert engine.should_heal(trace_id, ExecutionStatus.READY, [], plan) is False

def test_self_healing_should_not_heal_expected_empty():
    engine = SelfHealingEngine()
    trace_id = str(uuid.uuid4())
    
    plan = ExecutionPlan(
        trace_id=uuid.uuid4(),
        status=ExecutionStatus.READY,
        resolved_entities=ResolvedEntities(entities={}, joins=[]),
        selected_views=["VW_VENDAS_LM"],
        columns=[],
        filters=[],
        group_by=[],
        order_by=[],
        having=[],
        cte=[],
        parameters={},
        estimated_cost=QueryCost.LOW,
        estimated_rows=10,
        execution_priority=1,
        cacheable=True,
        cache_key="key",
        required_permissions=[],
        timeout=30,
        empty_dataset_policy=EmptyDatasetPolicy.EMPTY_EXPECTED
    )
    
    # Dataset vazio + EMPTY_EXPECTED -> Não deve curar (vazio legítimo)
    assert engine.should_heal(trace_id, ExecutionStatus.READY, [], plan) is False

@pytest.mark.asyncio
async def test_explainability_engine_avoids_hallucination():
    engine = ExplainabilityEngine()
    client_mock = AsyncMock()
    
    # Mock da resposta estruturada da OpenAI
    mock_choice = MagicMock()
    mock_choice.message.parsed = ExecutiveExplanation(
        summary="O faturamento total em vendas foi de 5000 reais.",
        insights=["Os dados demonstram crescimento linear."],
        recommendations=["Investigar a região Sul."],
        warnings=[]
    )
    client_mock.beta.chat.completions.parse.return_value.choices = [mock_choice]
    
    plan = CanonicalPlan(
        status=ExecutionStatus.READY, intent=IntentType.KPI, goal="Faturamento total",
        entities=["Venda"], metrics=[], dimensions=[]
    )
    
    explanation = await engine.generate_explanation(
        query="Qual o faturamento?",
        plan=plan,
        dataset=[{"ptotal_": 5000}],
        db_state=DashboardState(chart_type=VisualizationType.KPI_CARD),
        client=client_mock,
        model="gpt-4o"
    )
    
    assert "5000" in explanation.summary
    assert len(explanation.insights) == 1
    # Verifica que o prompt proíbe alucinação
    args = client_mock.beta.chat.completions.parse.call_args[1]
    assert "NÃO tente calcular novos valores" in args["messages"][1]["content"]

@pytest.mark.asyncio
async def test_explain_local_dataset_no_db_call():
    engine = ExplainabilityEngine()
    client_mock = AsyncMock()
    
    # Mock da resposta do GPT
    mock_choice = MagicMock()
    mock_choice.message.parsed = ExecutiveExplanation(
        summary="A barra é maior porque as vendas em MG representam 80% do total.",
        insights=[],
        recommendations=[],
        warnings=[]
    )
    client_mock.beta.chat.completions.parse.return_value.choices = [mock_choice]
    
    # Grafo contendo o nó ativo atual populado
    from models.new_pipeline_contracts import ConversationGraph
    graph = ConversationGraph(current_node_id="node_1", nodes={
        "node_1": ConversationNode(
            node_id="node_1",
            user_query="Vendas por estado",
            canonical_plan=CanonicalPlan(
                status=ExecutionStatus.READY, intent=IntentType.LIST, goal="Listar vendas",
                entities=["Venda"], metrics=[], dimensions=[]
            ),
            dashboard_state=DashboardState(chart_type=VisualizationType.BAR),
            execution_result=ExecutionResult(status=ExecutionStatus.READY, dataset=[{"uf": "MG", "ptotal_": 1000}], row_count=1, execution_time_ms=10.0),
            query_context=QueryContext(dataset_id="node_1", row_count=1, execution_time_ms=10.0)
        )
    })
    
    res = await engine.explain_local_dataset("Por que essa barra é maior?", graph, client_mock, "gpt-4o")
    
    assert res is not None
    assert res["status"] == "FULL_RENDERING"
    assert "barra é maior" in res["resposta_direta"]
    # Valida que não houve nova query de SQL (tempo de execução é 0)
    assert res["execution_time_ms"] == 0.0
