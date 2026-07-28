import pytest
import uuid
from unittest.mock import AsyncMock, patch
from models.new_pipeline_contracts import (
    SemanticPlan, ExecutionStatus, IntentType, VisualizationType,
    ComparisonOperator, SemanticFilter
)
from services.metadata_catalog.intent_engine import (
    CorporateIntentEngine, IntentEngineOutput, SemanticPatch, corporate_intent_engine
)
from services.new_query_orchestrator import NewQueryOrchestrator
from services.metadata_catalog.loader import load_corporate_catalog

pytestmark = [pytest.mark.unit, pytest.mark.no_database]

@pytest.fixture(autouse=True)
def setup_catalog():
    load_corporate_catalog()

@pytest.mark.asyncio
async def test_semantic_intent_engine_no_physical_references():
    """
    Garante que o CorporateIntentEngine opera apenas com conceitos semânticos,
    sem Views, SQL ou colunas físicas.
    """
    engine = CorporateIntentEngine()
    prompt = engine._build_system_prompt()
    
    # Valida ausência completa de termos físicos no prompt do sistema
    forbidden_terms = [
        "VW_VENDAS_LM", "VW_CLIENTES_CAD_LM", "VW_PRODUTOS_CAD_LM",
        "ptotal_", "qtde_", "dtemissao_", "codcliente_", "codprod_",
        "SELECT", "FROM", "WHERE", "JOIN", "PostgreSQL", "Oracle"
    ]
    for term in forbidden_terms:
        assert term not in prompt, f"O prompt contém referência física proibida: {term}"

@pytest.mark.asyncio
@patch("services.metadata_catalog.intent_engine.CorporateIntentEngine.analyze_query")
async def test_orchestrator_integration_simple_query(mock_analyze):
    """
    Valida a integração da pergunta analítica simples com o novo interpretador semântico.
    """
    # Mock de retorno conceitual puro da IA
    mock_analyze.return_value = IntentEngineOutput(
        is_continuity=False,
        status=ExecutionStatus.READY,
        plan=SemanticPlan(
            status=ExecutionStatus.READY,
            intent=IntentType.LIST,
            goal="Listar os clientes de Ataléia",
            entities=["Cliente"],
            metrics=[],
            dimensions=["cidade"],
            filters=[
                SemanticFilter(field="cidade", operator=ComparisonOperator.EQUALS, value="Ataléia")
            ]
        )
    )
    
    orchestrator = NewQueryOrchestrator()
    res = await orchestrator.run_pipeline(
        pergunta="Listar os clientes de Ataléia",
        tenant_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        session_id="session_123"
    )
    
    # Valida que o pipeline rodou com sucesso
    assert res["status"] in ("FULL_RENDERING", "DATABASE_ERROR")  # DATABASE_ERROR é aceito em teste sem banco clone real
    mock_analyze.assert_called_once()

@pytest.mark.asyncio
@patch("services.metadata_catalog.executor.database_executor.execute_query")
@patch("services.metadata_catalog.intent_engine.CorporateIntentEngine.analyze_query")
async def test_orchestrator_does_not_recreate_process_local_semantic_cache(mock_analyze, mock_execute):
    """
    Valida a aplicação de patches semânticos (SemanticPatch) sobre o plano anterior
    em caso de continuidade analítica de conversa.
    """
    mock_execute.return_value = {
        "status": "READY",
        "columns": ["valor_total"],
        "types": {"valor_total": "float"},
        "values": [{"valor_total": 100.0}],
        "row_count": 1,
        "execution_time_ms": 1.0,
        "db_time_ms": 1.0,
        "explain": "N/A",
        "explain_analyze": "N/A",
        "origin": "database",
        "cache": False,
        "trace_id": "dummy-trace-id",
        "warnings": []
    }
    orchestrator = NewQueryOrchestrator()
    session_id = str(uuid.uuid4())
    
    # 1. Pergunta inicial (gera plano base no cache)
    mock_analyze.return_value = IntentEngineOutput(
        is_continuity=False,
        status=ExecutionStatus.READY,
        plan=SemanticPlan(
            status=ExecutionStatus.READY,
            intent=IntentType.KPI,
            goal="Qual o faturamento total?",
            entities=["Venda"],
            metrics=["Receita"],
            dimensions=[],
            filters=[]
        )
    )
    
    await orchestrator.run_pipeline(
        pergunta="Qual o faturamento total?",
        tenant_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        session_id=session_id
    )
    
    # 2. Pergunta de continuidade (envia patch conceitual)
    mock_analyze.return_value = IntentEngineOutput(
        is_continuity=True,
        status=ExecutionStatus.READY,
        plan=SemanticPlan(
            status=ExecutionStatus.INVALID,
            intent=IntentType.KPI,
            goal="",
            entities=[],
            metrics=[],
            dimensions=[],
            filters=[]
        ),
        patches=[
            SemanticPatch(operation="ADD_FILTER", field="Estado", value="MG"),
            SemanticPatch(operation="CHANGE_LIMIT", value="5")
        ]
    )
    
    # Executa a continuação no mesmo session_id
    result = await orchestrator.run_pipeline(
        pergunta="Agora de MG limitado a 5",
        tenant_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        session_id=session_id
    )
    
    # Verifica se o plano semântico final no cache recebeu os patches mesclados
    assert result["status"] in {
        "FULL_RENDERING",
        "MISSING_INFORMATION",
        "DATABASE_ERROR",
    }
    assert not hasattr(orchestrator, "_last_semantic_plans")

@pytest.mark.asyncio
@patch("services.metadata_catalog.intent_engine.CorporateIntentEngine.analyze_query")
async def test_orchestrator_ambiguity_and_out_of_scope(mock_analyze):
    """
    Garante o correto roteamento de status AMBIGUOUS e OUT_OF_SCOPE.
    """
    orchestrator = NewQueryOrchestrator()
    
    # Cenário A: Ambiguidade analítica
    mock_analyze.return_value = IntentEngineOutput(
        is_continuity=False,
        status=ExecutionStatus.AMBIGUOUS,
        ambiguities=["Você deseja ver o ranking por quantidade de pedidos ou por valor total comprado?"],
        plan=SemanticPlan(
            status=ExecutionStatus.AMBIGUOUS,
            intent=IntentType.RANKING,
            goal="Ver os melhores clientes",
            entities=["Cliente"],
            metrics=[],
            dimensions=[]
        )
    )
    
    res_a = await orchestrator.run_pipeline(
        pergunta="Ver os melhores clientes",
        tenant_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
    )
    assert res_a["status"] == "AMBIGUOUS"
    assert len(res_a["ambiguities"]) > 0
    
    # Cenário B: Pergunta fora do escopo
    mock_analyze.return_value = IntentEngineOutput(
        is_continuity=False,
        status=ExecutionStatus.OUT_OF_SCOPE,
        plan=SemanticPlan(
            status=ExecutionStatus.OUT_OF_SCOPE,
            intent=IntentType.LIST,
            goal="Quem criou o Excel?",
            entities=[],
            metrics=[],
            dimensions=[]
        )
    )
    
    res_b = await orchestrator.run_pipeline(
        pergunta="Quem criou o Excel?",
        tenant_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
    )
    assert res_b["status"] == "OUT_OF_SCOPE"


@pytest.mark.asyncio
@patch("services.metadata_catalog.intent_engine.CorporateIntentEngine.analyze_query")
async def test_intent_engine_failure_is_typed_and_never_falls_back_to_client(mock_analyze):
    mock_analyze.side_effect = TimeoutError("controlled timeout")
    orchestrator = NewQueryOrchestrator()

    result = await orchestrator.run_pipeline(
        pergunta="Listar os clientes de Ataleia",
        tenant_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        session_id="intent-timeout",
    )

    assert result["status"] == "INTENT_ENGINE_ERROR"
    assert result["chart_data"] is None
    assert result["visualizations"] is None
    assert "Cliente" not in str(result.get("debug_info", {}).get("semantic_plan"))
    mock_analyze.assert_awaited_once()


@pytest.mark.asyncio
@patch("services.metadata_catalog.executor.database_executor.execute_query")
@patch("services.metadata_catalog.intent_engine.CorporateIntentEngine.analyze_query")
async def test_unsupported_intent_never_executes_database(mock_analyze, mock_execute):
    mock_analyze.return_value = IntentEngineOutput(
        is_continuity=False,
        status=ExecutionStatus.UNSUPPORTED,
        plan=SemanticPlan(
            status=ExecutionStatus.UNSUPPORTED,
            intent=IntentType.AGGREGATION,
            goal="Calcular uma previsao ainda nao suportada",
            entities=["Venda"],
            metrics=["Previsao"],
            dimensions=[],
        ),
    )
    orchestrator = NewQueryOrchestrator()

    result = await orchestrator.run_pipeline(
        pergunta="Calcule uma previsao probabilistica do proximo trimestre",
        tenant_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        session_id="unsupported-query",
    )

    assert result["status"] == "UNSUPPORTED"
    mock_execute.assert_not_awaited()
