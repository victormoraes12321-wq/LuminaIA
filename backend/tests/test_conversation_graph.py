import pytest
import uuid
import os
import shutil
from unittest.mock import AsyncMock, MagicMock, patch
from models.new_pipeline_contracts import (
    CanonicalPlan, ExecutionPlan, ResolvedEntities, ExecutionStatus,
    IntentType, VisualizationType, ComparisonOperator, DashboardState,
    ConversationNode, ExecutionResult, QueryContext
)
from services.metadata_catalog.conversation_graph import (
    ConversationGraphManager, conversation_graph_manager, STORAGE_DIR
)
from services.new_query_orchestrator import NewQueryOrchestrator
from services.metadata_catalog.loader import load_corporate_catalog

@pytest.fixture(autouse=True)
def setup_catalog_and_clean_disk():
    load_corporate_catalog()
    # Limpa diretório de persistência temporário de testes
    if os.path.exists(STORAGE_DIR):
        shutil.rmtree(STORAGE_DIR)
    os.makedirs(STORAGE_DIR, exist_ok=True)
    yield
    if os.path.exists(STORAGE_DIR):
        shutil.rmtree(STORAGE_DIR)

def test_conversation_graph_creation_and_node_connections():
    manager = ConversationGraphManager()
    session_id = "test_session_1"
    
    # 1. Criação do primeiro nó (Entrada da conversa)
    node_id_1 = "node_abc123"
    node_1 = ConversationNode(
        node_id=node_id_1,
        parent_id=None,
        children_ids=[],
        user_query="Qual o faturamento?",
        canonical_plan=CanonicalPlan(
            status=ExecutionStatus.READY, intent=IntentType.KPI, goal="Qual o faturamento?",
            entities=["Venda"], metrics=["Venda.receita_total"], dimensions=[]
        ),
        dashboard_state=DashboardState(chart_type=VisualizationType.KPI_CARD),
        execution_result=ExecutionResult(status=ExecutionStatus.READY, dataset=[{"ptotal_": 1000}], row_count=1, execution_time_ms=10.0),
        query_context=QueryContext(dataset_id=node_id_1, row_count=1, execution_time_ms=10.0)
    )
    
    manager.add_node(session_id, node_1)
    graph = manager.get_graph(session_id)
    
    assert graph.current_node_id == node_id_1
    assert len(graph.nodes) == 1
    assert node_id_1 in graph.nodes
    
    # 2. Criação do segundo nó (Continuidade/Filho do primeiro nó)
    node_id_2 = "node_xyz789"
    node_2 = ConversationNode(
        node_id=node_id_2,
        parent_id=None,  # Será preenchido automaticamente pelo manager
        children_ids=[],
        user_query="Agora de MG",
        canonical_plan=CanonicalPlan(
            status=ExecutionStatus.READY, intent=IntentType.KPI, goal="Faturamento em MG",
            entities=["Venda"], metrics=["Venda.receita_total"], dimensions=[]
        ),
        dashboard_state=DashboardState(chart_type=VisualizationType.KPI_CARD),
        execution_result=ExecutionResult(status=ExecutionStatus.READY, dataset=[{"ptotal_": 400}], row_count=1, execution_time_ms=8.0),
        query_context=QueryContext(dataset_id=node_id_2, row_count=1, execution_time_ms=8.0)
    )
    
    manager.add_node(session_id, node_2)
    graph_updated = manager.get_graph(session_id)
    
    # Valida o encadeamento e navegação
    assert graph_updated.current_node_id == node_id_2
    assert len(graph_updated.nodes) == 2
    assert graph_updated.nodes[node_id_2].parent_id == node_id_1
    assert node_id_2 in graph_updated.nodes[node_id_1].children_ids

def test_visual_only_update_intercepts_correctly():
    manager = ConversationGraphManager()
    session_id = "test_session_2"
    trace_id = uuid.uuid4()
    
    # Cria nó de faturamento com dataset em memória
    node_id = "node_initial"
    node = ConversationNode(
        node_id=node_id,
        parent_id=None,
        children_ids=[],
        user_query="Faturamento mensal",
        canonical_plan=CanonicalPlan(
            status=ExecutionStatus.READY, intent=IntentType.LIST, goal="Listar faturamento",
            entities=["Venda"], metrics=["Venda.receita_total"], dimensions=[]
        ),
        dashboard_state=DashboardState(chart_type=VisualizationType.TABLE),
        execution_result=ExecutionResult(status=ExecutionStatus.READY, dataset=[{"mes": "Jan", "ptotal_": 1500}], row_count=1, execution_time_ms=5.0),
        query_context=QueryContext(dataset_id=node_id, row_count=1, execution_time_ms=5.0)
    )
    manager.add_node(session_id, node)
    
    # Pergunta de UI que não deve tocar o banco (mudar para barras)
    res = manager.try_visual_only_update("mudar para grafico de barras", manager.get_graph(session_id), session_id, trace_id)
    
    assert res is not None
    assert res["status"] == "UI_MODIFIED"
    assert res["chart_type"] == VisualizationType.BAR.value
    
    # Garante que adicionou um novo nó no grafo para a operação visual
    new_graph = manager.get_graph(session_id)
    assert len(new_graph.nodes) == 2
    assert new_graph.nodes[node_id].dashboard_state.chart_type == VisualizationType.TABLE
    assert new_graph.nodes[new_graph.current_node_id].execution_result.metadata == {
        "visual_update_only": True
    }


def test_visual_only_update_does_not_intercept_semantic_change():
    manager = ConversationGraphManager()
    session_id = "test_session_visual_semantic_negative"
    node = ConversationNode(
        node_id="node_semantic_source",
        user_query="Faturamento mensal",
        canonical_plan=CanonicalPlan(
            status=ExecutionStatus.READY,
            intent=IntentType.LIST,
            goal="Listar faturamento",
            entities=["Venda"],
            metrics=["Venda.receita_total"],
            dimensions=[],
        ),
        dashboard_state=DashboardState(chart_type=VisualizationType.TABLE),
        execution_result=ExecutionResult(
            status=ExecutionStatus.READY,
            dataset=[{"mes": "Jan", "ptotal_": 1500}],
            row_count=1,
            execution_time_ms=5.0,
        ),
        query_context=QueryContext(
            dataset_id="node_semantic_source",
            row_count=1,
            execution_time_ms=5.0,
        ),
    )
    manager.add_node(session_id, node)

    result = manager.try_visual_only_update(
        "troque a metrica para margem liquida",
        manager.get_graph(session_id),
        session_id,
        uuid.uuid4(),
    )

    assert result is None
    graph = manager.get_graph(session_id)
    assert graph.current_node_id == "node_semantic_source"
    assert len(graph.nodes) == 1


def test_visual_only_update_requires_an_active_certified_dataset():
    manager = ConversationGraphManager()
    session_id = "test_session_visual_without_dataset"
    node = ConversationNode(
        node_id="node_without_dataset",
        user_query="Faturamento mensal",
        canonical_plan=CanonicalPlan(
            status=ExecutionStatus.READY,
            intent=IntentType.LIST,
            goal="Listar faturamento",
            entities=["Venda"],
            metrics=["Venda.receita_total"],
            dimensions=[],
        ),
        dashboard_state=DashboardState(chart_type=VisualizationType.TABLE),
        execution_result=ExecutionResult(
            status=ExecutionStatus.READY,
            dataset=[],
            row_count=0,
            execution_time_ms=1.0,
        ),
        query_context=QueryContext(
            dataset_id="node_without_dataset",
            row_count=0,
            execution_time_ms=1.0,
        ),
    )
    manager.add_node(session_id, node)

    result = manager.try_visual_only_update(
        "mudar para grafico de barras",
        manager.get_graph(session_id),
        session_id,
        uuid.uuid4(),
    )

    assert result is None
    assert len(manager.get_graph(session_id).nodes) == 1

def test_drill_down_local_filter():
    manager = ConversationGraphManager()
    session_id = "test_session_3"
    trace_id = uuid.uuid4()
    
    # Dataset contendo cidades de MG e SP
    dataset = [
        {"nome": "Vendedor A", "uf": "MG"},
        {"nome": "Vendedor B", "uf": "SP"},
        {"nome": "Vendedor C", "uf": "MG"}
    ]
    
    node_id = "node_vendedores"
    node = ConversationNode(
        node_id=node_id,
        user_query="Listar vendedores",
        canonical_plan=CanonicalPlan(
            status=ExecutionStatus.READY, intent=IntentType.LIST, goal="Listar vendedores",
            entities=["Vendedor"], metrics=[], dimensions=["Vendedor.nome", "Vendedor.uf"]
        ),
        dashboard_state=DashboardState(chart_type=VisualizationType.TABLE),
        execution_result=ExecutionResult(status=ExecutionStatus.READY, dataset=dataset, row_count=3, execution_time_ms=5.0),
        query_context=QueryContext(dataset_id=node_id, row_count=3, execution_time_ms=5.0)
    )
    manager.add_node(session_id, node)
    
    # Executa drilldown local ("mostre apenas MG")
    res = manager.try_local_drilldown("filtrar apenas MG", manager.get_graph(session_id), session_id, trace_id)
    
    assert res is not None
    assert res["status"] == "FULL_RENDERING"
    # Deve filtrar os vendedores de MG (A e C)
    rows = res["chart_data"]["rows"]
    assert len(rows) == 2
    assert rows[0]["nome"] == "Vendedor A"
    assert rows[1]["nome"] == "Vendedor C"

def test_dataset_reuse():
    manager = ConversationGraphManager()
    session_id = "test_session_4"
    
    # Dataset inicial contendo vendedores e estados
    node_id = "node_vendedores"
    node = ConversationNode(
        node_id=node_id,
        user_query="Listar vendedores",
        canonical_plan=CanonicalPlan(
            status=ExecutionStatus.READY, intent=IntentType.LIST, goal="Listar vendedores",
            entities=["Vendedor"], metrics=[], dimensions=["Vendedor.nome", "Vendedor.uf"]
        ),
        dashboard_state=DashboardState(chart_type=VisualizationType.TABLE),
        execution_result=ExecutionResult(status=ExecutionStatus.READY, dataset=[{"nome": "A", "uf": "MG"}], row_count=1, execution_time_ms=5.0),
        query_context=QueryContext(dataset_id=node_id, row_count=1, execution_time_ms=5.0)
    )
    manager.add_node(session_id, node)
    
    # Novo plano que solicita apenas Vendedor.uf (subconjunto de Vendedor)
    new_plan = CanonicalPlan(
        status=ExecutionStatus.READY, intent=IntentType.LIST, goal="Listar estados",
        entities=["Vendedor"], metrics=[], dimensions=["Vendedor.uf"]
    )
    
    reused = manager.try_dataset_reuse(new_plan, manager.get_graph(session_id))
    assert reused is not None
    assert len(reused) == 1
    assert "uf" in reused[0]

def test_conversation_graph_persistence():
    manager = ConversationGraphManager()
    session_id = "test_session_persist_123"
    
    node_id = "node_persistent"
    node = ConversationNode(
        node_id=node_id,
        user_query="Faturamento",
        canonical_plan=CanonicalPlan(
            status=ExecutionStatus.READY, intent=IntentType.KPI, goal="Ver faturamento",
            entities=["Venda"], metrics=["Venda.receita_total"], dimensions=[]
        ),
        dashboard_state=DashboardState(chart_type=VisualizationType.KPI_CARD),
        execution_result=ExecutionResult(status=ExecutionStatus.READY, dataset=[{"ptotal_": 10}], row_count=1, execution_time_ms=1.0),
        query_context=QueryContext(dataset_id=node_id, row_count=1, execution_time_ms=1.0)
    )
    manager.add_node(session_id, node)
    
    # Instancia novo manager para forçar carregamento do disco
    new_manager = ConversationGraphManager()
    restored_graph = new_manager.get_graph(session_id)
    
    assert restored_graph.current_node_id == node_id
    assert node_id in restored_graph.nodes
    assert restored_graph.nodes[node_id].user_query == "Faturamento"
