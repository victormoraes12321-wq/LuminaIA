import uuid
import time
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from openai import AsyncOpenAI

from models.new_pipeline_contracts import (
    SemanticPlan, CanonicalPlan, ExecutionPlan, ExecutionResult, QueryContext,
    DashboardState, ConversationNode, ConversationGraph, ExecutionStatus,
    IntentType, VisualizationType, ComparisonOperator, EmptyDatasetPolicy,
    SemanticFilter
)
from services.metadata_catalog import (
    SemanticCanonicalizer, MetadataResolver, QueryOptimizer, SQLGenerator, SecurityValidator
)
from services.security_and_normalization_engine import EmptyDatasetAnomalyError
from services.ai_credential_manager import ai_credential_manager
from database import get_db_context
from sqlalchemy import text

logger = logging.getLogger("luminaai.services.new_query_orchestrator")

# ── A) Contrato Estruturado de Explicação da IA ─────────────────────

class ExecutiveExplanation(BaseModel):
    summary: str = Field(..., description="Resumo executivo em linguagem de negócios simples dos resultados.")
    insights: List[str] = Field(default_factory=list, description="Lista de insights analíticos identificados nos dados.")
    recommendations: List[str] = Field(default_factory=list, description="Recomendações comerciais acionáveis com base nos dados.")
    warnings: List[str] = Field(default_factory=list, description="Alertas ou limitações identificadas na análise.")

# ── B) Orquestrador Unificado do Novo Pipeline ──────────────────────

class NewQueryOrchestrator:
    """
    Orquestrador central unificado do novo pipeline cognitivo (Decoupled NLU-SQL) do LuminaAI.
    """
    def __init__(self, provider: Optional[Any] = None):
        self.resolver = SemanticCanonicalizer()
        self.planner = MetadataResolver()
        self.optimizer = QueryOptimizer()
        self.generator = SQLGenerator()
        self.validator = SecurityValidator()

    async def run_pipeline(
        self,
        pergunta: str,
        tenant_id: str,
        session_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        dashboard_state_override: Optional[DashboardState] = None,
        parent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        trace_id = uuid.uuid4()
        history = history or []
        session_key = session_id or tenant_id

        # ── Inicialização do PIPELINE DEBUG ──
        debug_data = {
            "pergunta": pergunta,
            "resposta_bruta_llm": None,
            "semantic_plan": None,
            "canonical_plan": None,
            "execution_plan": None,
            "selected_views": [],
            "joins": [],
            "sql": {
                "raw_sql": None,
                "parameters": {}
            },
            "execution_time_ms": 0.0,
            "rows": 0,
            "sample_rows": [],
            "transformer": {
                "input": [],
                "output": {}
            },
            "chart": None,
            "llm_prompt": None,
            "llm_response": None,
            "error_traceback": None,
            "timeline": {}
        }
        
        from datetime import datetime
        def get_timestamp() -> str:
            return datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
        debug_data["timeline"]["1. Pergunta Recebida"] = get_timestamp()

        def save_debug_logs(payload: dict):
            try:
                import os
                import json
                
                # Popula o payload final no debug
                debug_data["payload_frontend"] = payload
                debug_data["timeline"]["16. Frontend Retornado"] = get_timestamp()
                
                # Se houver erro ou exceção no status do payload
                if payload.get("status") in ("AMBIGUOUS", "MISSING_INFORMATION", "OUT_OF_SCOPE", "SECURITY_VIOLATION", "DATABASE_ERROR", "EMPTY_ANOMALY"):
                    if not debug_data.get("error_traceback"):
                        debug_data["error_traceback"] = payload.get("message")
                
                # Latência total
                debug_data["timeline"]["Total Processamento"] = f"{(time.perf_counter() - start_time) * 1000:.2f}ms"
                
                # Formata SQL com quebras de linha estéticas para legibilidade no trace
                if debug_data["sql"]["raw_sql"]:
                    raw = debug_data["sql"]["raw_sql"]
                    formatted = raw.replace(" SELECT ", "\nSELECT\n  ").replace(" FROM ", "\nFROM\n  ").replace(" LEFT JOIN ", "\nLEFT JOIN\n  ").replace(" INNER JOIN ", "\nINNER JOIN\n  ").replace(" JOIN ", "\nJOIN\n  ").replace(" WHERE ", "\nWHERE\n  ").replace(" GROUP BY ", "\nGROUP BY\n  ").replace(" HAVING ", "\nHAVING\n  ").replace(" ORDER BY ", "\nORDER BY\n  ").replace(" LIMIT ", "\nLIMIT\n  ")
                    debug_data["sql"]["raw_sql"] = formatted
                
                log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runtime-logs", "debug")
                os.makedirs(log_dir, exist_ok=True)
                
                debug_json = json.dumps(debug_data, indent=4, default=str, ensure_ascii=False)
                
                # Salva trace persistente por trace_id
                with open(os.path.join(log_dir, f"debug_{trace_id}.json"), "w", encoding="utf-8") as f:
                    f.write(debug_json)
                # Sobrescreve trace global da última execução
                with open(os.path.join(log_dir, "debug_steps.json"), "w", encoding="utf-8") as f:
                    f.write(debug_json)
            except Exception as e_log:
                logger.error("Erro ao salvar log de debug em disco: %s", e_log)

        def write_debug_and_return(payload: dict) -> dict:
            payload["trace_id"] = str(trace_id)
            payload["query_id"] = str(trace_id)
            payload["request_id"] = str(trace_id)
            save_debug_logs(payload)
            payload["debug_info"] = debug_data
            return payload

        # ── 1. Conversation Graph Recuperação ─────────────────────────
        from services.metadata_catalog.conversation_graph import conversation_graph_manager
        graph = conversation_graph_manager.get_graph(session_key)

        # Se o parent_id foi fornecido explicitamente, navega/muda o nó ativo para ele
        if parent_id and parent_id in graph.nodes:
            graph.current_node_id = parent_id
            conversation_graph_manager.save_graph(session_key, graph)

        # Adquire cliente OpenAI correspondente ao tenant usando o resolve_client correto
        lease = await ai_credential_manager.resolve_client(tenant_id=uuid.UUID(tenant_id))
        client = lease.client
        model = lease.model

        # ── 2. Intercepção Local: Operações Visuais, Drill-down e Explicações ──────
        # A) Operações de UI / Visuais sem tocar no banco ou na IA
        visual_res = conversation_graph_manager.try_visual_only_update(
            pergunta=pergunta, graph=graph, session_id=session_key, trace_id=trace_id
        )
        if visual_res:
            debug_data["timeline"]["Local UI Interception"] = get_timestamp()
            return write_debug_and_return(visual_res)

        # B) Drill-down local em memória se os dados estiverem disponíveis
        drilldown_res = conversation_graph_manager.try_local_drilldown(
            pergunta=pergunta, graph=graph, session_id=session_key, trace_id=trace_id
        )
        if drilldown_res:
            debug_data["timeline"]["Local Drill-Down Interception"] = get_timestamp()
            return write_debug_and_return(drilldown_res)

        # C) Perguntas explicativas locais sobre os dados já carregados
        from services.metadata_catalog.explainability import explainability_engine
        explain_local_res = await explainability_engine.explain_local_dataset(
            query=pergunta, graph=graph, client=client, model=model
        )
        if explain_local_res:
            debug_data["timeline"]["Local Explainability Interception"] = get_timestamp()
            return write_debug_and_return(explain_local_res)

        # Inicializa o cache de planos na classe se necessário
        if not hasattr(self, "_last_semantic_plans"):
            self._last_semantic_plans = {}

        # Extrai contexto conversacional estruturado do nó ativo atual para guiar a IA
        last_plan = None
        last_db_state = None
        last_q_context = None
        
        if graph.current_node_id and graph.current_node_id in graph.nodes:
            active_node = graph.nodes[graph.current_node_id]
            last_plan = SemanticPlan(
                status=active_node.canonical_plan.status,
                intent=active_node.canonical_plan.intent,
                goal=active_node.canonical_plan.goal,
                entities=active_node.canonical_plan.entities,
                metrics=active_node.canonical_plan.metrics,
                dimensions=active_node.canonical_plan.dimensions,
                filters=[],  # IA analisa o plano limpo
                trace_id=active_node.canonical_plan.trace_id
            )
            last_db_state = active_node.dashboard_state
            last_q_context = active_node.query_context

        # ── 2. LLM Intent Engine (Fase de Entrada Refatorada) ─────────
        semantic_plan = None
        debug_data["timeline"]["2. Intent Engine Iniciado"] = get_timestamp()
        try:
            from services.metadata_catalog.intent_engine import corporate_intent_engine
            intent_output = await corporate_intent_engine.analyze_query(
                query=pergunta,
                tenant_id=tenant_id,
                history=history,
                last_plan=last_plan,
                dashboard_state=last_db_state,
                query_context=last_q_context
            )
            debug_data["timeline"]["3. Intent Engine Concluído"] = get_timestamp()
            debug_data["resposta_bruta_llm"] = getattr(intent_output, "raw_response", None) or intent_output.model_dump_json()
            
            # Se for continuidade e houver plano anterior no cache, aplica os patches
            cache_key = session_id or tenant_id
            if intent_output.is_continuity and last_plan:
                base_plan = last_plan
                
                # Importa copy localmente para segurança
                import copy
                semantic_plan = copy.deepcopy(base_plan)
                semantic_plan.trace_id = trace_id
                
                # Aplica cada patch semântico gerado pelo interpretador conceitual
                for patch in intent_output.patches:
                    op = patch.operation.upper()
                    if op == "ADD_FILTER" and patch.field and patch.value is not None:
                        semantic_plan.filters.append(
                            SemanticFilter(
                                field=patch.field,
                                operator=ComparisonOperator.EQUALS,
                                value=patch.value
                            )
                        )
                    elif op == "CHANGE_PERIOD" and patch.value:
                        # Limpa datas antigas
                        semantic_plan.filters = [f for f in semantic_plan.filters if f.field.lower() not in ("periodo", "data", "date", "dtemissao", "dtemissao_")]
                        semantic_plan.filters.append(
                            SemanticFilter(
                                field="Periodo",
                                operator=ComparisonOperator.EQUALS,
                                value=patch.value
                            )
                        )
                    elif op == "REMOVE_FILTER" and patch.field:
                        semantic_plan.filters = [f for f in semantic_plan.filters if f.field.lower() != patch.field.lower()]
                    elif op == "ADD_METRIC" and patch.field:
                        if patch.field not in semantic_plan.metrics:
                            semantic_plan.metrics.append(patch.field)
                    elif op == "CHANGE_LIMIT" and patch.value is not None:
                        try:
                            semantic_plan.limit = int(patch.value)
                        except ValueError:
                            pass
                debug_data["timeline"]["4. Patches Semânticos Aplicados"] = get_timestamp()
                logger.info("[Orchestrator] Patches semânticos aplicados com sucesso sobre o plano anterior.")
            else:
                if intent_output.plan:
                    semantic_plan = intent_output.plan
                    semantic_plan.trace_id = trace_id
                else:
                    raise ValueError("Plano semântico não gerado pela IA no modo normal.")
                    
            # Auto-cura de status analítico: se a LLM classificar pessimistamente como MISSING_INFORMATION,
            # mas termos ou entidades válidos estão presentes no plano, coage o status para READY para viabilizar a execução.
            if intent_output.status in (ExecutionStatus.MISSING_INFORMATION, ExecutionStatus.UNSUPPORTED):
                if semantic_plan.intent in (IntentType.LIST, IntentType.AGGREGATION, IntentType.RANKING, IntentType.TREND) or len(semantic_plan.entities) > 0:
                    logger.info("[Orchestrator] Auto-cura: Coagindo status de %s para READY para viabilizar execucao.", intent_output.status)
                    intent_output.status = ExecutionStatus.READY
                    semantic_plan.status = ExecutionStatus.READY
                    
            # Trata status não-prontos
            semantic_plan.status = intent_output.status
            debug_data["semantic_plan"] = semantic_plan.model_dump()

            if intent_output.status in (ExecutionStatus.AMBIGUOUS, ExecutionStatus.MISSING_INFORMATION, ExecutionStatus.OUT_OF_SCOPE):
                elapsed = (time.perf_counter() - start_time) * 1000
                res = {
                    "status": intent_output.status.value,
                    "goal": semantic_plan.goal or pergunta,
                    "ambiguities": intent_output.ambiguities,
                    "missing_information": intent_output.missing_information,
                    "resposta_direta": "Identifiquei termos ambíguos ou informações ausentes na pergunta analítica.",
                    "pergunta_original": pergunta,
                    "execution_time_ms": elapsed
                }
                return write_debug_and_return(res)
                
            # Salva o plano semântico bem-sucedido no cache para futuras continuidades
            self._last_semantic_plans[cache_key] = semantic_plan

        except Exception as exc:
            import traceback
            debug_data["error_traceback"] = traceback.format_exc()
            logger.error("[Orchestrator] Falha no Motor de Intenções Refatorado: %s", exc, exc_info=True)
            # Fallback determinístico seguro
            semantic_plan = SemanticPlan(
                status=ExecutionStatus.READY,
                intent=IntentType.LIST,
                goal=pergunta,
                entities=["Cliente"],
                metrics=[],
                dimensions=[],
                trace_id=trace_id
            )
            debug_data["semantic_plan"] = semantic_plan.model_dump()

        # ── 3. Query Intent Resolver ──────────────────────────────────
        debug_data["timeline"]["5. Canonicalizer Iniciado"] = get_timestamp()
        canonical_plan = self.resolver.canonicalize(semantic_plan)
        debug_data["timeline"]["6. Canonicalizer Concluído"] = get_timestamp()
        debug_data["canonical_plan"] = canonical_plan.model_dump()

        # ── 4. Reutilização de Dataset em Memória RAM ─────────────────
        # Desabilitado para garantir execução analítica fresca e evitar contaminação entre perguntas consecutivas
        reused_rows = None
        
        # Mapeia optimized_plan como exec_plan para compatibilidade posterior no fluxo de salvamento do nó
        optimized_plan = None
        sql = ""
        binds = {}
        
        if reused_rows is not None:
            logger.info("[Orchestrator] Poupando execução de query física: dataset compatível reutilizado do Conversation Graph.")
            normalized_rows = reused_rows
            sql = "REUSED_FROM_MEMORY"
            binds = {}
            debug_data["sql"]["raw_sql"] = sql
            debug_data["sql"]["parameters"] = binds
            debug_data["rows"] = len(normalized_rows)
            debug_data["sample_rows"] = normalized_rows[:20]
            debug_data["timeline"]["Reuso de Dataset em RAM"] = get_timestamp()
        else:
            # ── 5. Planner Engine (BFS Dijkstra) ──────────────────────────
            debug_data["timeline"]["7. Metadata Resolver Iniciado"] = get_timestamp()
            exec_plan = self.planner.resolve(canonical_plan)
            debug_data["timeline"]["8. Metadata Resolver Concluído"] = get_timestamp()
            debug_data["execution_plan"] = exec_plan.model_dump()
            
            # Coleta as views candidatas avaliadas com os scores e joins
            debug_data["selected_views"] = getattr(exec_plan, "selected_views", [])
            debug_data["joins"] = getattr(exec_plan.resolved_entities, "joins", []) if getattr(exec_plan, "resolved_entities", None) else []
            
            if canonical_plan.intent in (IntentType.KPI, IntentType.AGGREGATION):
                exec_plan.empty_dataset_policy = EmptyDatasetPolicy.EMPTY_UNEXPECTED
                
            if exec_plan.status == ExecutionStatus.NEEDS_REPLANNING:
                elapsed = (time.perf_counter() - start_time) * 1000
                res = {
                    "status": "NEEDS_REPLANNING",
                    "message": "Nao foi possivel estabelecer relacionamentos fisicos de JOIN no catalogo de views.",
                    "pergunta_original": pergunta,
                    "execution_time_ms": elapsed
                }
                return write_debug_and_return(res)

            # ── 6. Query Optimizer & SQL Generator ────────────────────────
            debug_data["timeline"]["9. SQL Generator Iniciado"] = get_timestamp()
            optimized_plan = self.optimizer.optimize_plan(exec_plan)
            sql, binds = self.generator.generate_sql(optimized_plan)
            if not sql or not sql.strip():
                logger.warning("[Orchestrator] SQL gerado está vazio. Retornando erro de plano analítico.")
                elapsed = (time.perf_counter() - start_time) * 1000
                res = {
                    "status": "INVALID_PLAN",
                    "message": "Não foi possível gerar uma consulta estruturada a partir dos conceitos fornecidos. Certifique-se de que a pergunta analítica se refere a entidades e dimensões válidas do catálogo.",
                    "pergunta_original": pergunta,
                    "execution_time_ms": elapsed
                }
                return write_debug_and_return(res)
                
            debug_data["timeline"]["10. SQL Generator Concluído"] = get_timestamp()
            debug_data["sql"]["raw_sql"] = sql
            debug_data["sql"]["parameters"] = binds

            # ── 7. Security Validator ─────────────────────────────────────
            debug_data["timeline"]["11. Security Validator Iniciado"] = get_timestamp()
            try:
                self.validator.validate_sql_safety(sql, tenant_id)
                debug_data["timeline"]["12. Security Validator Concluído"] = get_timestamp()
            except Exception as sec_exc:
                import traceback
                debug_data["error_traceback"] = traceback.format_exc()
                logger.error("[Orchestrator] SQL bloqueado pelo validador de seguranca: %s", sec_exc)
                elapsed = (time.perf_counter() - start_time) * 1000
                res = {
                    "status": "SECURITY_VIOLATION",
                    "message": f"Erro de seguranca analitica: {sec_exc}",
                    "pergunta_original": pergunta,
                    "execution_time_ms": elapsed
                }
                return write_debug_and_return(res)

            # ── 8. Execution & Result Normalizer (Self-Healing Loop) ──────
            debug_data["timeline"]["13. Database Executor Iniciado"] = get_timestamp()
            execution_success = False
            attempts = 2
            normalized_rows = []
            
            while attempts > 0 and not execution_success:
                attempts -= 1
                try:
                    # Executa a query física usando o novo DatabaseExecutor unificado do CKG
                    from services.metadata_catalog.executor import database_executor
                    from services.security_and_normalization_engine import EmptyDatasetAnomalyError
                    from services.metadata_catalog.self_healing import self_healing_engine
                    
                    result_dataset = await database_executor.execute_query(
                        plan=optimized_plan,
                        sql=sql,
                        binds=binds,
                        tenant_id=tenant_id
                    )
                    
                    # Dispara anomalia caso o status indique necessidade de replanejamento ou dataset vazio
                    if result_dataset.get("status") == "NEEDS_REPLANNING" or (not result_dataset.get("values") and self_healing_engine.should_heal(str(trace_id), exec_plan.status, [], optimized_plan)):
                        raise EmptyDatasetAnomalyError("Dataset vazio inesperado detectado durante a execução analítica.")
                        
                    normalized_rows = result_dataset.get("values", [])
                    execution_success = True
                    debug_data["rows"] = len(normalized_rows)
                    debug_data["sample_rows"] = normalized_rows[:20]
                    debug_data["timeline"]["13. Database Executor Concluído"] = get_timestamp()
                except EmptyDatasetAnomalyError as anomaly_exc:
                    logger.warning("[Orchestrator] Loop de Auto-Cura acionado por anomalia: %s", anomaly_exc)
                    if attempts > 0 and self_healing_engine.should_heal(str(trace_id), exec_plan.status, [], optimized_plan):
                        self_healing_engine.mark_healed(str(trace_id))
                        feedback_prompt = self_healing_engine.generate_healing_feedback(str(anomaly_exc), optimized_plan)
                        try:
                            # Re-planeja utilizando o Intent Engine conceitual
                            from services.metadata_catalog.intent_engine import corporate_intent_engine
                            intent_output = await corporate_intent_engine.analyze_query(
                                query=feedback_prompt,
                                tenant_id=tenant_id,
                                history=history,
                                last_plan=last_plan,
                                dashboard_state=last_db_state,
                                query_context=last_q_context
                            )
                            
                            if intent_output.plan:
                                semantic_plan = intent_output.plan
                                semantic_plan.trace_id = trace_id
                                
                                # Re-planeja e re-otimiza
                                canonical_plan = self.resolver.canonicalize(semantic_plan)
                                exec_plan = self.planner.resolve(canonical_plan)
                                optimized_plan = self.optimizer.optimize_plan(exec_plan)
                                sql, binds = self.generator.generate_sql(optimized_plan)
                                debug_data["sql"]["raw_sql"] = sql
                                debug_data["sql"]["parameters"] = binds
                            else:
                                break
                        except Exception as regen_exc:
                            logger.error("[Orchestrator] Falha ao regenerar plano na auto-cura: %s", regen_exc)
                            break
                    else:
                        elapsed = (time.perf_counter() - start_time) * 1000
                        res = {
                            "status": "EMPTY_ANOMALY",
                            "message": "Nao foram encontrados dados nos registros desta empresa para o periodo solicitado.",
                            "pergunta_original": pergunta,
                            "execution_time_ms": elapsed
                        }
                        return write_debug_and_return(res)
                except Exception as db_exc:
                    import traceback
                    debug_data["error_traceback"] = traceback.format_exc()
                    logger.error("[Orchestrator] Erro na execucao fisica do SQL: %s", db_exc)
                    elapsed = (time.perf_counter() - start_time) * 1000
                    res = {
                        "status": "DATABASE_ERROR",
                        "message": f"Erro de processamento assincrono de dados no servidor: {db_exc}",
                        "pergunta_original": pergunta,
                        "execution_time_ms": elapsed
                    }
                    return write_debug_and_return(res)

        # ── 8. LLM Explainability (Fase de Saída) ─────────────────────
        debug_data["timeline"]["13. Explainability Iniciado"] = get_timestamp()
        from services.metadata_catalog.explainability import explainability_engine
        explanation, explain_prompt = await explainability_engine.generate_explanation(
            query=pergunta,
            plan=canonical_plan,
            dataset=normalized_rows,
            db_state=dashboard_state_override or DashboardState(chart_type=VisualizationType.TABLE),
            client=client,
            model=model
        )
        debug_data["timeline"]["13. Explainability Concluído"] = get_timestamp()
        debug_data["llm_prompt"] = explain_prompt
        debug_data["llm_response"] = explanation.summary

        # ── 11. Transformer Integration & Graph Update ────────────────
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
        
        v_type_str = canonical_plan.suggested_visualization.value.upper() if hasattr(canonical_plan.suggested_visualization, 'value') else str(canonical_plan.suggested_visualization).upper()
        target_chart_type = vis_map.get(v_type_str, SchemaChartType.TABLE)
        
        # Coerção inteligente baseada na intenção analítica do negócio
        intent_str = canonical_plan.intent.value.upper() if hasattr(canonical_plan.intent, 'value') else str(canonical_plan.intent).upper()
        if "curva abc" in pergunta.lower():
            target_chart_type = SchemaChartType.BAR
        elif intent_str == "RANKING":
            target_chart_type = SchemaChartType.BAR
        elif intent_str == "TREND":
            target_chart_type = SchemaChartType.LINE
        elif intent_str in ("KPI", "AGGREGATION") and len(normalized_rows) == 1:
            target_chart_type = SchemaChartType.KPI
            
        debug_data["timeline"]["14. Data Transformer Iniciado"] = get_timestamp()
        debug_data["transformer"]["input"] = normalized_rows[:50]
        
        # Converte o dataset para o formato Chart.js do frontend
        transformed_chart_data = transform_data(normalized_rows, target_chart_type)
        debug_data["transformer"]["output"] = transformed_chart_data
        debug_data["chart"] = {
            "type": target_chart_type.value,
            "data": transformed_chart_data
        }
        debug_data["timeline"]["15. Data Transformer Concluído"] = get_timestamp()

        elapsed = (time.perf_counter() - start_time) * 1000

        # Mapeia de volta para VisualizationType correspondente
        vis_reverse_map = {
            "TABLE": VisualizationType.TABLE,
            "BAR": VisualizationType.BAR,
            "LINE": VisualizationType.LINE,
            "PIE": VisualizationType.PIE,
            "KPI": VisualizationType.KPI_CARD,
            "KPI_CARD": VisualizationType.KPI_CARD,
            "SCATTER": VisualizationType.SCATTER
        }
        
        # ── 9. Conversation Graph Update & Return ─────────────────────
        db_state = DashboardState(
            chart_type=vis_reverse_map.get(target_chart_type.value.upper(), VisualizationType.TABLE),
            selected_filters={"tenant_id": tenant_id}
        )
        
        node_id = f"node_{uuid.uuid4().hex[:8]}"
        exec_res = ExecutionResult(
            status=ExecutionStatus.READY,
            dataset=normalized_rows,
            metadata={"sql": sql, "binds": str(binds)},
            execution_time_ms=elapsed,
            row_count=len(normalized_rows)
        )
        
        query_context = QueryContext(
            dataset_id=node_id,
            row_count=len(normalized_rows),
            execution_time_ms=elapsed
        )
        
        conv_node = ConversationNode(
            node_id=node_id,
            user_query=pergunta,
            canonical_plan=canonical_plan,
            execution_result=exec_res,
            query_context=query_context,
            dashboard_state=db_state
        )
        
        # Persiste o nó conversacional no grafo de sessão
        conversation_graph_manager.add_node(session_key, conv_node)

        # Monta payload final
        final_payload = {
            "status": "FULL_RENDERING",
            "pergunta_original": pergunta,
            "resposta_direta": explanation.summary,
            "ia_justificativa": explanation.summary,
            "chart_type": target_chart_type.value,
            "chart_data": transformed_chart_data,
            "insights": explanation.insights,
            "recommendations": explanation.recommendations,
            "warnings": explanation.warnings,
            "execution_time_ms": elapsed,
            "telemetry": {
                "sql": sql,
                "timings": {"total_pipeline": elapsed}
            }
        }

        return write_debug_and_return(final_payload)

new_query_orchestrator = NewQueryOrchestrator()
