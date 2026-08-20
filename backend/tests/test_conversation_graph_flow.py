import sys
import os
import uuid
import pytest
from typing import Optional, List, Dict

# Garante que o diretorio backend esta no PYTHONPATH para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.new_pipeline_contracts import (
    ConversationGraph, ConversationNode, CanonicalPlan, DashboardState,
    VisualizationType, ExecutionStatus, IntentType, CanonicalFilter, ComparisonOperator
)

class ConversationManager:
    """
    Simulador de gerenciador de grafo conversacional do LuminaAI.
    Orquestra a navegacao de estados, backtracking e quebras de escopo.
    """
    def __init__(self):
        self.graph = ConversationGraph()
        
    def add_query(self, query: str, plan: CanonicalPlan, parent_id: Optional[str] = None) -> ConversationNode:
        node_id = f"node_{uuid.uuid4().hex[:8]}"
        
        # Se houver pai, adiciona a relacao no pai
        if parent_id and parent_id in self.graph.nodes:
            self.graph.nodes[parent_id].children_ids.append(node_id)
            
        db_state = DashboardState(
            chart_type=plan.suggested_visualization,
            selected_filters={f.field: f.value for f in plan.filters}
        )
        
        node = ConversationNode(
            node_id=node_id,
            parent_id=parent_id,
            user_query=query,
            canonical_plan=plan,
            dashboard_state=db_state,
            children_ids=[]
        )
        
        self.graph.nodes[node_id] = node
        self.graph.current_node_id = node_id
        return node


def test_conversation_graph_branching_and_backtrack():
    """
    Simula uma arvore complexa de conversacao ramificada com backtracking e quebra de escopo.
    Verifica se a integridade matematica do parentesco e o isolamento de filtros sao mantidos.
    """
    manager = ConversationManager()
    
    # ── Passo 1: Nó Raiz A ("Quais são os top 10 vendedores deste ano?") ──
    plan_A = CanonicalPlan(
        status=ExecutionStatus.READY,
        intent=IntentType.RANKING,
        goal="Quais sao os top 10 vendedores deste ano?",
        entities=["Venda"],
        metrics=["valor_total"],
        dimensions=["Vendedor.nome"],
        filters=[
            CanonicalFilter(field="Venda.data_venda", operator=ComparisonOperator.GREATER_EQUAL, value="2026-01-01")
        ],
        limit=10,
        suggested_visualization=VisualizationType.BAR
    )
    node_A = manager.add_query(
        query="Quais são os top 10 vendedores deste ano?",
        plan=plan_A,
        parent_id=None
    )
    node_A_id = node_A.node_id
    
    # ── Passo 2: Ramificação B ("Filtre apenas o estado de Minas Gerais.") ──
    # Filho de A. Herda plano de A e adiciona filtro de estado.
    plan_B = plan_A.model_copy(deep=True)
    plan_B.goal = "Top 10 vendedores deste ano em Minas Gerais"
    plan_B.entities = ["Venda", "Cliente"]
    plan_B.filters.append(
        CanonicalFilter(field="Cliente.estado", operator=ComparisonOperator.EQUALS, value="MG")
    )
    node_B = manager.add_query(
        query="Filtre apenas o estado de Minas Gerais.",
        plan=plan_B,
        parent_id=node_A_id
    )
    node_B_id = node_B.node_id
    
    # ── Passo 3: Sub-ramificação C ("Agora mostre apenas a cidade de BH.") ──
    # Filho de B. Herda plano de B e adiciona filtro de cidade BH.
    plan_C = plan_B.model_copy(deep=True)
    plan_C.goal = "Top 10 vendedores deste ano em BH"
    plan_C.filters.append(
        CanonicalFilter(field="Cliente.cidade", operator=ComparisonOperator.EQUALS, value="BH")
    )
    node_C = manager.add_query(
        query="Agora mostre apenas a cidade de BH.",
        plan=plan_C,
        parent_id=node_B_id
    )
    node_C_id = node_C.node_id

    # ── Passo 4: Backtrack e Nova Ramificação D ("Esquece BH, filtre apenas a cidade de Contagem.") ──
    # Irmao de C, filho de B. Herda plano de B (pai) e adiciona Contagem (sem poluir com filtros de C).
    plan_D = plan_B.model_copy(deep=True)
    plan_D.goal = "Top 10 vendedores deste ano em Contagem"
    plan_D.filters.append(
        CanonicalFilter(field="Cliente.cidade", operator=ComparisonOperator.EQUALS, value="Contagem")
    )
    node_D = manager.add_query(
        query="Esquece BH, filtre apenas a cidade de Contagem.",
        plan=plan_D,
        parent_id=node_B_id
    )
    node_D_id = node_D.node_id
    
    # ── Passo 5: Mudança de Escopo E ("Agora me mostre a lista de produtos sem estoque.") ──
    # Novo assunto, quebra de escopo independente. parent_id = None.
    plan_E = CanonicalPlan(
        status=ExecutionStatus.READY,
        intent=IntentType.LIST,
        goal="Lista de produtos sem estoque",
        entities=["Produto"],
        metrics=[],
        dimensions=["Produto.nome_produto", "Produto.estoque_atual"],
        filters=[
            CanonicalFilter(field="Produto.estoque_atual", operator=ComparisonOperator.EQUALS, value=0.0)
        ],
        suggested_visualization=VisualizationType.TABLE
    )
    node_E = manager.add_query(
        query="Agora me mostre a lista de produtos sem estoque.",
        plan=plan_E,
        parent_id=None
    )
    node_E_id = node_E.node_id
    
    # ── REGRAS DE VALIDAÇÃO DE INTEGRIDADE MATEMÁTICA ──
    
    # 1. Total de nós criados
    assert len(manager.graph.nodes) == 5
    
    # 2. Integridade dos Trace IDs e tipos basicos
    for nid, node in manager.graph.nodes.items():
        assert isinstance(node.node_id, str)
        assert isinstance(node.canonical_plan.trace_id, uuid.UUID)
        
    # 3. Integridade do parentesco do No A (Raiz)
    assert manager.graph.nodes[node_A_id].parent_id is None
    assert manager.graph.nodes[node_A_id].children_ids == [node_B_id]
    
    # 4. Integridade do parentesco do No B (Ponto de Ramificacao)
    assert manager.graph.nodes[node_B_id].parent_id == node_A_id
    assert set(manager.graph.nodes[node_B_id].children_ids) == {node_C_id, node_D_id}
    
    # 5. Integridade do parentesco dos Nos C e D (Irmaos / Bifurcados)
    assert manager.graph.nodes[node_C_id].parent_id == node_B_id
    assert manager.graph.nodes[node_C_id].children_ids == []
    
    assert manager.graph.nodes[node_D_id].parent_id == node_B_id
    assert manager.graph.nodes[node_D_id].children_ids == []
    
    # 6. Integridade do parentesco do No E (Escopo Desconectado)
    assert manager.graph.nodes[node_E_id].parent_id is None
    assert manager.graph.nodes[node_E_id].children_ids == []
    
    # 7. Validação de Filtros Herdados e Isolamento do Backtrack
    # No B: Filtro original de A (data >= 2026) + Estado MG
    filters_B = manager.graph.nodes[node_B_id].canonical_plan.filters
    assert len(filters_B) == 2
    assert any(f.field == "Cliente.estado" and f.value == "MG" for f in filters_B)
    
    # No C: Filtros de B + Cidade BH
    filters_C = manager.graph.nodes[node_C_id].canonical_plan.filters
    assert len(filters_C) == 3
    assert any(f.field == "Cliente.estado" and f.value == "MG" for f in filters_C)
    assert any(f.field == "Cliente.cidade" and f.value == "BH" for f in filters_C)
    
    # No D (Irmao apos backtrack): Filtros de B + Cidade Contagem (sem poluir com BH)
    filters_D = manager.graph.nodes[node_D_id].canonical_plan.filters
    assert len(filters_D) == 3
    assert any(f.field == "Cliente.estado" and f.value == "MG" for f in filters_D)
    assert any(f.field == "Cliente.cidade" and f.value == "Contagem" for f in filters_D)
    assert not any(f.field == "Cliente.cidade" and f.value == "BH" for f in filters_D), "Backtrack poluído com estado de C!"
    
    # No E: Apenas filtros de estoque
    filters_E = manager.graph.nodes[node_E_id].canonical_plan.filters
    assert len(filters_E) == 1
    assert filters_E[0].field == "Produto.estoque_atual"
    assert filters_E[0].value == 0.0

    print("\n[SUCCESS] Integridade Matematica da Arvore de Conversacao Validada:")
    print("      Node_A (Raiz: Top 10 Vendedores)")
    print("           |")
    print("      Node_B (Minas Gerais)")
    print("      /        \\")
    print("Node_C (BH)  Node_D (Contagem)")
    print("\nNode_E (Mudanca de Escopo: Produtos sem estoque)")


if __name__ == "__main__":
    # Permite rodar o arquivo diretamente como script de teste
    try:
        test_conversation_graph_branching_and_backtrack()
        print("Todos os testes do ConversationGraph passaram com sucesso!")
    except AssertionError as e:
        print(f"Falha de assercao de integridade: {e}")
        sys.exit(1)
