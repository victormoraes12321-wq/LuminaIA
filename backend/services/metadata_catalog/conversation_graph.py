import json
import logging
import os
import time
import uuid
from typing import Dict, Any, Optional, List
from models.new_pipeline_contracts import (
    ConversationGraph, ConversationNode, DashboardState, QueryContext,
    ExecutionResult, CanonicalPlan, VisualizationType, ExecutionStatus,
    ComparisonOperator
)

logger = logging.getLogger("luminaai.services.metadata_catalog.conversation_graph")

# Diretório para persistência local segura de estados conversacionais
STORAGE_DIR = os.path.join(os.getcwd(), ".lumina_conversations")
os.makedirs(STORAGE_DIR, exist_ok=True)

class ConversationGraphManager:
    """
    O ConversationGraphManager substitui a memória linear clássica por uma árvore de nós persistente.
    Gerencia ramificações de conversa, reutilização de datasets locais (Drill-Down),
    e interceptação de comandos puramente visuais sem tocar no banco de dados analítico.
    """
    
    def __init__(self):
        self._memory_graphs: Dict[str, ConversationGraph] = {}

    def _get_filepath(self, session_id: str) -> str:
        # Sanitização simples de nome de arquivo
        safe_session = "".join([c for c in session_id if c.isalnum() or c in ("-", "_")])
        return os.path.join(STORAGE_DIR, f"graph_{safe_session}.json")

    def get_graph(self, session_id: str) -> ConversationGraph:
        # 1. Tenta recuperar da memória RAM
        if session_id in self._memory_graphs:
            return self._memory_graphs[session_id]

        # 2. Tenta restaurar do arquivo local persistente
        filepath = self._get_filepath(session_id)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    graph = ConversationGraph.model_validate(data)
                    self._memory_graphs[session_id] = graph
                    logger.info(f"[ConversationGraph] Sessão restaurada com sucesso do disco: {session_id}")
                    return graph
            except Exception as e:
                logger.error(f"[ConversationGraph] Falha ao restaurar sessão {session_id} do disco: {e}")

        # 3. Cria um novo grafo vazio
        graph = ConversationGraph(nodes={}, current_node_id=None)
        self._memory_graphs[session_id] = graph
        return graph

    def save_graph(self, session_id: str, graph: ConversationGraph):
        self._memory_graphs[session_id] = graph
        filepath = self._get_filepath(session_id)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(graph.model_dump_json(indent=2))
        except Exception as e:
            logger.error(f"[ConversationGraph] Falha ao persistir sessão {session_id} no disco: {e}")

    def add_node(self, session_id: str, node: ConversationNode):
        graph = self.get_graph(session_id)
        
        # Conecta o novo nó ao pai
        if graph.current_node_id and graph.current_node_id in graph.nodes:
            parent = graph.nodes[graph.current_node_id]
            node.parent_id = parent.node_id
            if node.node_id not in parent.children_ids:
                parent.children_ids.append(node.node_id)

        graph.nodes[node.node_id] = node
        graph.current_node_id = node.node_id
        
        self.save_graph(session_id, graph)
        logger.info(f"[ConversationGraph] Novo nó '{node.node_id}' adicionado à árvore conversacional.")

    def try_visual_only_update(
        self, pergunta: str, graph: ConversationGraph, session_id: str, trace_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Detecta se a pergunta solicita apenas mudanças puramente visuais na UI
        (ex: mudar tipo de gráfico ou ordenação).
        Atualiza o DashboardState do nó ativo e retorna imediatamente, sem tocar no banco ou na IA.
        """
        if not graph.current_node_id or graph.current_node_id not in graph.nodes:
            return None

        current_node = graph.nodes[graph.current_node_id]
        if not current_node.execution_result or not current_node.execution_result.dataset:
            return None

        p_lower = pergunta.lower()
        new_chart_type: Optional[VisualizationType] = None
        
        # Mapeamento tolerante a erros de digitação (ex: baaras, piza, linas)
        if any(w in p_lower for w in ["pizza", "piza", "pisa", "pissa", "pie", "rosca", "donut"]):
            new_chart_type = VisualizationType.PIE
        elif any(w in p_lower for w in ["barra", "barras", "baara", "baaras", "bara", "baras", "bar", "coluna", "colunas"]):
            new_chart_type = VisualizationType.BAR
        elif any(w in p_lower for w in ["linha", "linhas", "lina", "linas", "evolucao", "historico", "serie"]):
            new_chart_type = VisualizationType.LINE
        elif any(w in p_lower for w in ["tabela", "tabelas", "tabua", "tabella", "grade", "planilha", "lista"]):
            new_chart_type = VisualizationType.TABLE
        elif any(w in p_lower for w in ["card", "kpi", "cartao", "indicador"]):
            new_chart_type = VisualizationType.KPI_CARD

        # Mapeamento de ordenação local
        sort_col = None
        sort_dir = None
        if "ordene" in p_lower or "ordenar" in p_lower:
            # Tenta encontrar alguma coluna do dataset para ordenar
            dataset = current_node.execution_result.dataset
            if dataset:
                for col in dataset[0].keys():
                    if col.lower() in p_lower:
                        sort_col = col
                        sort_dir = "DESC" if "inverso" in p_lower or "contrario" in p_lower or "desc" in p_lower else "ASC"
                        break

        # Se encontrou mudança puramente visual
        if new_chart_type or sort_col:
            start_time = time.perf_counter()
            
            # Cria novo estado do dashboard mantendo as referências
            state = current_node.dashboard_state
            if new_chart_type:
                state.chart_type = new_chart_type
            if sort_col:
                state.sort_column = sort_col
                state.sort_direction = sort_dir
                
            # Ordena localmente em memória se solicitado
            rows = list(current_node.execution_result.dataset)
            if sort_col:
                rows.sort(
                    key=lambda x: x.get(sort_col, 0) or 0,
                    reverse=(sort_dir == "DESC")
                )

            # Cria um novo nó ramificado para manter histórico limpo do grafo
            node_id = f"node_{uuid.uuid4().hex[:8]}"
            new_node = ConversationNode(
                node_id=node_id,
                parent_id=current_node.node_id,
                children_ids=[],
                user_query=pergunta,
                canonical_plan=current_node.canonical_plan,
                execution_result=ExecutionResult(
                    status=current_node.execution_result.status,
                    dataset=rows,
                    metadata={"visual_update_only": True},
                    execution_time_ms=current_node.execution_result.execution_time_ms,
                    row_count=len(rows)
                ),
                query_context=current_node.query_context,
                dashboard_state=state
            )
            
            self.add_node(session_id, new_node)
            elapsed = (time.perf_counter() - start_time) * 1000
            
            from services.data_transformer import transform_data
            from models.view_catalog import ChartType as SchemaChartType

            vis_map = {
                "TABLE": SchemaChartType.TABLE,
                "BAR": SchemaChartType.BAR,
                "LINE": SchemaChartType.LINE,
                "PIE": SchemaChartType.PIE,
                "KPI": SchemaChartType.KPI,
                "AREA": SchemaChartType.AREA,
                "SCATTER": SchemaChartType.SCATTER
            }
            s_type = vis_map.get(state.chart_type.value.upper(), SchemaChartType.TABLE)
            transformed_dataset = transform_data(rows, s_type)

            logger.info(f"[ConversationGraph] Operação visual local executada com sucesso. Tipo: {new_chart_type or 'Ordenação'}")
            return {
                "query_id": str(trace_id),
                "trace_id": str(trace_id),
                "request_id": str(trace_id),
                "status": "FULL_RENDERING",
                "pergunta_original": pergunta,
                "resposta_direta": f"Atualizei a visualização do dashboard para {state.chart_type.value} conforme solicitado.",
                "ia_justificativa": "Atualização visual executada localmente em memória RAM.",
                "chart_type": state.chart_type.value,
                "dataset": transformed_dataset,
                "chart_data": transformed_dataset,
                "insights": [],
                "recommendations": [],
                "warnings": [],
                "execution_time_ms": elapsed
            }

        return None

    def try_local_drilldown(
        self, pergunta: str, graph: ConversationGraph, session_id: str, trace_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Verifica se a pergunta é um drilldown (detalhamento) cuja coluna e valor
        já estão presentes no dataset do nó atual. Filtra localmente sem ir ao banco.
        """
        if not graph.current_node_id or graph.current_node_id not in graph.nodes:
            return None

        current_node = graph.nodes[graph.current_node_id]
        if not current_node.execution_result or not current_node.execution_result.dataset:
            return None

        p_lower = pergunta.lower()
        dataset = current_node.execution_result.dataset
        
        # Procura coluna e valor passados na pergunta
        drill_col = None
        drill_val = None
        
        for row in dataset:
            for col, val in row.items():
                if isinstance(val, str) and val.lower() in p_lower:
                    drill_col = col
                    drill_val = val
                    break
            if drill_col:
                break
                
        # Se encontramos correspondência para drilldown local
        if drill_col and drill_val:
            start_time = time.perf_counter()
            
            # Filtra o dataset localmente em memória
            filtered_rows = [r for r in dataset if r.get(drill_col) == drill_val]
            
            # Atualiza o stack de drilldown do DashboardState
            state = current_node.dashboard_state.model_copy()
            state.drilldown_stack.append(f"{drill_col}:{drill_val}")
            
            # Cria novo nó ramificado
            node_id = f"node_{uuid.uuid4().hex[:8]}"
            new_node = ConversationNode(
                node_id=node_id,
                parent_id=current_node.node_id,
                children_ids=[],
                user_query=pergunta,
                canonical_plan=current_node.canonical_plan,
                execution_result=ExecutionResult(
                    status=current_node.execution_result.status,
                    dataset=filtered_rows,
                    metadata={"local_drilldown": True},
                    execution_time_ms=0.0,
                    row_count=len(filtered_rows)
                ),
                query_context=current_node.query_context,
                dashboard_state=state
            )
            
            self.add_node(session_id, new_node)
            elapsed = (time.perf_counter() - start_time) * 1000
            
            logger.info(f"[ConversationGraph] Drill-down local em memória executado para a coluna '{drill_col}' = '{drill_val}'")
            return {
                "query_id": str(trace_id),
                "trace_id": str(trace_id),
                "request_id": str(trace_id),
                "status": "FULL_RENDERING",
                "pergunta_original": pergunta,
                "resposta_direta": f"Apliquei o detalhamento local para {drill_col} = {drill_val}.",
                "ia_justificativa": f"Drill-down aplicado localmente sobre o dataset em memória.",
                "chart_type": state.chart_type.value,
                "chart_data": {
                    "columns": [{"key": k, "label": k.replace("_", " ").title()} for k in filtered_rows[0].keys()] if filtered_rows else [],
                    "rows": filtered_rows
                },
                "insights": [f"Filtro aplicado localmente: {drill_col} = {drill_val}"],
                "recommendations": [],
                "warnings": [],
                "execution_time_ms": elapsed
            }

        return None

    def try_dataset_reuse(
        self, canonical_plan: CanonicalPlan, graph: ConversationGraph
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Verifica se o plano lógico solicita colunas/entidades compatíveis com as que já
        estão em memória no dataset do nó ativo atual. Se sim, projeta localmente.
        """
        if not graph.current_node_id or graph.current_node_id not in graph.nodes:
            return None

        current_node = graph.nodes[graph.current_node_id]
        if not current_node.execution_result or not current_node.execution_result.dataset:
            return None

        # Para reutilização completa, as entidades e dimensões lógicas requisitadas
        # devem ser um subconjunto ou estarem contidas no nó de partida
        current_plan = current_node.canonical_plan
        
        # Verifica compatibilidade de entidades do CKG
        if not set(canonical_plan.entities).issubset(set(current_plan.entities)):
            return None

        # Verifica se as colunas e dimensões do novo plano podem ser extraídas do dataset existente
        # Extrai chaves físicas das colunas no CKG
        from services.metadata_catalog.catalog import get_corporate_catalog
        catalog = get_corporate_catalog()
        
        required_cols = []
        for d in canonical_plan.dimensions:
            parts = d.split(".")
            if len(parts) == 2:
                # Se for a cidade, por exemplo
                required_cols.append(parts[1])
                
        # Garante que todas as colunas físicas mapeadas estão presentes na primeira linha do dataset
        dataset = current_node.execution_result.dataset
        if not dataset:
            return None
            
        dataset_cols = {k.lower() for k in dataset[0].keys()}
        
        # Traduz required_cols para ver se bate com as do dataset
        matched_all = True
        projected_keys = []
        for rc in required_cols:
            found = False
            for dc in dataset_cols:
                if rc.lower() in dc or dc in rc.lower():
                    projected_keys.append(dc)
                    found = True
                    break
            if not found:
                matched_all = False
                break
                
        if matched_all:
            logger.info(f"[ConversationGraph] Reutilizando dataset analítico em memória RAM para o plano.")
            # Projeta apenas as chaves correspondentes
            projected_rows = []
            for row in dataset:
                proj = {}
                for k, v in row.items():
                    if k.lower() in projected_keys or not projected_keys:
                        proj[k] = v
                projected_rows.append(proj)
            return projected_rows

        return None

conversation_graph_manager = ConversationGraphManager()
