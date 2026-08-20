import pytest
import uuid
from models.new_pipeline_contracts import (
    SemanticPlan, SemanticFilter, ComparisonOperator, ExecutionStatus, IntentType, VisualizationType
)
from services.metadata_catalog.loader import load_corporate_catalog
from services.metadata_catalog.canonicalizer import SemanticCanonicalizer

@pytest.fixture(autouse=True)
def setup_catalog():
    # Inicializa o catálogo corporativo estático antes dos testes
    load_corporate_catalog()

def test_resolve_aliases():
    canonicalizer = SemanticCanonicalizer()
    
    # Plano semântico utilizando aliases ("compradores", "faturamento")
    sem_plan = SemanticPlan(
        trace_id=uuid.uuid4(),
        status=ExecutionStatus.READY,
        intent=IntentType.KPI,
        goal="Medir o faturamento dos compradores",
        entities=["compradores", "venda"],
        metrics=["faturamento"],
        dimensions=[],
        filters=[],
        suggested_visualization=VisualizationType.KPI_CARD
    )
    
    canon_plan = canonicalizer.canonicalize(sem_plan)
    
    assert canon_plan.status == ExecutionStatus.READY
    # Alias "compradores" resolvido para "Cliente"
    assert "Cliente" in canon_plan.entities
    # Alias "faturamento" resolvido para "Venda.Receita"
    assert "Venda.Receita" in canon_plan.metrics

def test_resolve_entities():
    canonicalizer = SemanticCanonicalizer()
    
    # Teste de normalização case-insensitive e aliases de entidades
    sem_plan = SemanticPlan(
        trace_id=uuid.uuid4(),
        status=ExecutionStatus.READY,
        intent=IntentType.LIST,
        goal="Listar os rcas e produtos",
        entities=["rcas", "produtos"],
        metrics=[],
        dimensions=[],
        filters=[]
    )
    
    canon_plan = canonicalizer.canonicalize(sem_plan)
    
    assert canon_plan.status == ExecutionStatus.READY
    assert "Vendedor" in canon_plan.entities
    assert "Produto" in canon_plan.entities

def test_resolve_metrics():
    canonicalizer = SemanticCanonicalizer()
    
    # Teste de resolução de métricas canônicas qualificadas
    sem_plan = SemanticPlan(
        trace_id=uuid.uuid4(),
        status=ExecutionStatus.READY,
        intent=IntentType.KPI,
        goal="Ver receita e quantidade de estoque",
        entities=["Venda", "Produto"],
        metrics=["receita", "quantidade", "estoque"],
        dimensions=[],
        filters=[]
    )
    
    canon_plan = canonicalizer.canonicalize(sem_plan)
    
    assert canon_plan.status == ExecutionStatus.READY
    assert "Venda.Receita" in canon_plan.metrics
    assert "Venda.Quantidade" in canon_plan.metrics
    assert "Produto.Estoque" in canon_plan.metrics

def test_resolve_dimensions():
    canonicalizer = SemanticCanonicalizer()
    
    # Teste de dimensões conceituais
    sem_plan = SemanticPlan(
        trace_id=uuid.uuid4(),
        status=ExecutionStatus.READY,
        intent=IntentType.LIST,
        goal="Vendas agrupadas por cidade e categoria de produto",
        entities=["Cliente", "Produto", "Venda"],
        metrics=[],
        dimensions=["cidade", "categoria"],
        filters=[]
    )
    
    canon_plan = canonicalizer.canonicalize(sem_plan)
    
    assert canon_plan.status == ExecutionStatus.READY
    assert "Cliente.cidade" in canon_plan.dimensions
    assert "Produto.familia" in canon_plan.dimensions

def test_resolve_filters():
    canonicalizer = SemanticCanonicalizer()
    
    # Teste de filtros com aliases resolvidos e nomes de campos qualificados
    sem_filter = SemanticFilter(
        field="cidade",
        operator=ComparisonOperator.EQUALS,
        value="Ataléia"
    )
    
    sem_plan = SemanticPlan(
        trace_id=uuid.uuid4(),
        status=ExecutionStatus.READY,
        intent=IntentType.LIST,
        goal="Filtrar por cidade",
        entities=["Cliente"],
        metrics=[],
        dimensions=[],
        filters=[sem_filter]
    )
    
    canon_plan = canonicalizer.canonicalize(sem_plan)
    
    assert canon_plan.status == ExecutionStatus.READY
    assert len(canon_plan.filters) == 1
    assert canon_plan.filters[0].field == "Cliente.cidade"
    assert canon_plan.filters[0].value == "Ataléia"

def test_resolve_ambiguity():
    canonicalizer = SemanticCanonicalizer()
    
    # Campo "nome" é ambíguo entre Cliente, Produto e Vendedor
    sem_plan = SemanticPlan(
        trace_id=uuid.uuid4(),
        status=ExecutionStatus.READY,
        intent=IntentType.LIST,
        goal="Filtrar por nome",
        entities=["Cliente", "Vendedor"],
        metrics=[],
        dimensions=["nome"],
        filters=[]
    )
    
    canon_plan = canonicalizer.canonicalize(sem_plan)
    
    assert canon_plan.status == ExecutionStatus.AMBIGUOUS

def test_resolve_unsupported():
    canonicalizer = SemanticCanonicalizer()
    
    # Conceito inexistente "churn_rate" (não suportado)
    sem_plan = SemanticPlan(
        trace_id=uuid.uuid4(),
        status=ExecutionStatus.READY,
        intent=IntentType.KPI,
        goal="Chur rate de clientes",
        entities=["Cliente"],
        metrics=["churn_rate"],
        dimensions=[],
        filters=[]
    )
    
    canon_plan = canonicalizer.canonicalize(sem_plan)
    
    assert canon_plan.status == ExecutionStatus.UNSUPPORTED

def test_missing_information():
    canonicalizer = SemanticCanonicalizer()
    
    # Objetivo analítico (goal) ausente
    sem_plan = SemanticPlan(
        trace_id=uuid.uuid4(),
        status=ExecutionStatus.READY,
        intent=IntentType.LIST,
        goal="",
        entities=["Cliente"],
        metrics=[],
        dimensions=[],
        filters=[]
    )
    
    canon_plan = canonicalizer.canonicalize(sem_plan)
    
    assert canon_plan.status == ExecutionStatus.MISSING_INFORMATION

