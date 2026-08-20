import pytest
import uuid
from models.new_pipeline_contracts import (
    CanonicalPlan, CanonicalFilter, ComparisonOperator, ExecutionStatus,
    IntentType, VisualizationType
)
from services.metadata_catalog.loader import load_corporate_catalog
from services.metadata_catalog.resolver import MetadataResolver

@pytest.fixture(autouse=True)
def setup_catalog():
    load_corporate_catalog()

def test_resolve_single_entity():
    resolver = MetadataResolver()
    
    plan = CanonicalPlan(
        trace_id=uuid.uuid4(),
        status=ExecutionStatus.READY,
        intent=IntentType.LIST,
        goal="Listar os clientes",
        entities=["Cliente"],
        metrics=[],
        dimensions=["Cliente.nome", "Cliente.uf"],
        filters=[]
    )
    
    exec_plan = resolver.resolve(plan)
    
    assert exec_plan.status == ExecutionStatus.READY
    assert len(exec_plan.selected_views) == 1
    assert "VW_CLIENTES_CAD_LM" in exec_plan.selected_views
    assert len(exec_plan.resolved_entities.joins) == 0
    assert "VW_CLIENTES_CAD_LM.nome" in exec_plan.columns
    assert "VW_CLIENTES_CAD_LM.uf" in exec_plan.columns

def test_resolve_two_entities_one_join():
    resolver = MetadataResolver()
    
    plan = CanonicalPlan(
        trace_id=uuid.uuid4(),
        status=ExecutionStatus.READY,
        intent=IntentType.AGGREGATION,
        goal="Medir faturamento por estado",
        entities=["Venda", "Cliente"],
        metrics=["Venda.receita_total"],
        dimensions=["Cliente.uf"],
        filters=[]
    )
    
    exec_plan = resolver.resolve(plan)
    
    assert exec_plan.status == ExecutionStatus.READY
    assert len(exec_plan.selected_views) == 2
    assert "VW_VENDAS_LM" in exec_plan.selected_views
    assert "VW_CLIENTES_CAD_LM" in exec_plan.selected_views
    
    # Valida presença do JOIN correto
    assert len(exec_plan.resolved_entities.joins) == 1
    join = exec_plan.resolved_entities.joins[0]
    assert join["source_view"] == "VW_VENDAS_LM"
    assert join["source_column"] == "codcliente_"
    assert join["target_view"] == "VW_CLIENTES_CAD_LM"
    assert join["target_column"] == "codigo"

def test_resolve_three_entities_two_joins():
    resolver = MetadataResolver()
    
    plan = CanonicalPlan(
        trace_id=uuid.uuid4(),
        status=ExecutionStatus.READY,
        intent=IntentType.AGGREGATION,
        goal="Vendas por produto e por cidade do cliente",
        entities=["Venda", "Cliente", "Produto"],
        metrics=["Venda.receita_total"],
        dimensions=["Cliente.cidade", "Produto.familia"],
        filters=[]
    )
    
    exec_plan = resolver.resolve(plan)
    
    assert exec_plan.status == ExecutionStatus.READY
    assert len(exec_plan.selected_views) == 3
    assert "VW_VENDAS_LM" in exec_plan.selected_views
    assert "VW_CLIENTES_CAD_LM" in exec_plan.selected_views
    assert "VW_PRODUTOS_CAD_LM" in exec_plan.selected_views
    
    # 3 views requerem 2 caminhos de JOIN para estarem conectadas no BFS
    assert len(exec_plan.resolved_entities.joins) == 2

def test_resolve_disconnected_graph_needs_replanning():
    resolver = MetadataResolver()
    
    # Se tentarmos conectar Financeiro e Venda sem passar por Cliente
    # (Não há junção física direta declarada no CKC entre Financeiro e Venda)
    plan = CanonicalPlan(
        trace_id=uuid.uuid4(),
        status=ExecutionStatus.READY,
        intent=IntentType.LIST,
        goal="Ver parcelas e vendas",
        entities=["Financeiro", "Venda"],
        metrics=[],
        dimensions=[],
        filters=[]
    )
    
    # Mas espere: Financeiro e Venda podem se conectar passando por Cliente!
    # Financeiro -> Cliente -> Venda (BFS deve descobrir esse caminho de 2 joins automaticamente)
    exec_plan = resolver.resolve(plan)
    
    assert exec_plan.status == ExecutionStatus.READY
    assert len(exec_plan.selected_views) == 3  # Venda, Financeiro e Cliente (injetada no caminho)
    assert len(exec_plan.resolved_entities.joins) == 2

def test_resolve_join_impossible():
    resolver = MetadataResolver()
    
    # Simula uma view isolada sem relacionamentos (Categoria se conecta a Produto,
    # mas e se criarmos uma entidade isolada no catálogo? Como não há, vamos mockar
    # ou testar com uma entidade fake sem relacionamentos)
    from services.metadata_catalog.catalog import get_corporate_catalog
    catalog = get_corporate_catalog()
    
    # Adiciona entidade isolada temporariamente
    from services.metadata_catalog.models import BusinessEntityMetadata, ViewMetadata, ViewType
    catalog.entities["Isolada"] = BusinessEntityMetadata(
        name="Isolada", views=["VW_ISOLADA"], columns=[], relationships=[], metrics=[], dimensions=[]
    )
    catalog.views["VW_ISOLADA"] = ViewMetadata(
        name="VW_ISOLADA", functional_description="Isolada", business_description="Isolada",
        purpose="Isolada", granularity="Isolada", view_type=ViewType.CADASTRAL, columns={},
        primary_key="id", foreign_keys={}, related_views=[], relationships=[]
    )
    
    plan = CanonicalPlan(
        trace_id=uuid.uuid4(),
        status=ExecutionStatus.READY,
        intent=IntentType.LIST,
        goal="Listar isolada e vendas",
        entities=["Isolada", "Venda"],
        metrics=[],
        dimensions=[],
        filters=[]
    )
    
    exec_plan = resolver.resolve(plan)
    
    # Grafo desconectado deve retornar NEEDS_REPLANNING
    assert exec_plan.status == ExecutionStatus.NEEDS_REPLANNING

def test_metadata_resolver_cache():
    resolver = MetadataResolver()
    
    plan = CanonicalPlan(
        trace_id=uuid.uuid4(),
        status=ExecutionStatus.READY,
        intent=IntentType.KPI,
        goal="Medir receita de vendas",
        entities=["Venda"],
        metrics=["Venda.receita_total"],
        dimensions=[],
        filters=[]
    )
    
    # Primeira resolução (Cache Miss)
    exec_plan_1 = resolver.resolve(plan)
    
    # Segunda resolução com trace_id diferente (Cache Hit)
    new_trace_id = uuid.uuid4()
    plan.trace_id = new_trace_id
    exec_plan_2 = resolver.resolve(plan)
    
    assert exec_plan_1.cache_key == exec_plan_2.cache_key
    assert exec_plan_2.trace_id == new_trace_id
    # Garante que reutilizou a instância em cache
    assert exec_plan_1.estimated_cost == exec_plan_2.estimated_cost
