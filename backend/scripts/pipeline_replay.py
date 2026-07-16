import asyncio
import os
import sys
import argparse
import json
import uuid
import time
from sqlalchemy import text

# Adiciona o diretório backend ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.new_pipeline_contracts import (
    SemanticPlan, CanonicalPlan, ExecutionPlan, CanonicalFilter, ComparisonOperator, IntentType, VisualizationType
)
from services.new_query_orchestrator import NewQueryOrchestrator, ExecutiveExplanation
from services.metadata_catalog.resolver import metadata_resolver
from services.metadata_catalog.executor import database_executor
from services.metadata_catalog.loader import load_corporate_catalog
from services.data_transformer import transform_data

async def run_replay():
    # Inicializa o catálogo de metadados
    load_corporate_catalog()
    
    parser = argparse.ArgumentParser(description="Replay granular de execução de pipeline analítico")
    parser.add_argument("--trace_id", type=str, required=True, help="ID do trace do log de debug (ex: debug_steps ou UUID)")
    parser.add_argument("--start_step", type=str, default="resolver", choices=["semantic", "canonical", "resolver", "sql", "banco", "transformer"], help="Passo inicial do replay")
    parser.add_argument("--call_ai", action="store_true", help="Forçar chamadas à OpenAI para o Explainability/Intent Engine")
    
    args = parser.parse_args()
    trace_id_str = args.trace_id
    start_step = args.start_step.lower()
    
    # 1. Localiza e carrega o arquivo de debug JSON
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runtime-logs", "debug")
    filename = f"debug_{trace_id_str}.json" if "-" in trace_id_str else f"{trace_id_str}.json"
    filepath = os.path.join(log_dir, filename)
    
    if not os.path.exists(filepath):
        # Tenta fallback para debug_steps.json se não achar o UUID
        filepath = os.path.join(log_dir, "debug_steps.json")
        if not os.path.exists(filepath):
            print(f"[!] Arquivo de debug não localizado: {filepath}")
            sys.exit(1)
            
    print(f"[*] Carregando trace de debug: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        debug_data = json.load(f)

    print("=" * 80)
    print(f"REPLAY ANALÍTICO - TRACE ID: {debug_data.get('payload_frontend', {}).get('trace_id', 'N/A')}")
    print(f"Pergunta Original: '{debug_data.get('pergunta')}'")
    print(f"Passo Inicial Selecionado: {start_step.upper()}")
    print("=" * 80)

    orchestrator = NewQueryOrchestrator()
    
    # Resolução do tenant_id local
    tenant_id_raw = None
    if "payload_frontend" in debug_data:
        pf = debug_data["payload_frontend"]
        if isinstance(pf, dict):
            tenant_id_raw = pf.get("telemetry", {}).get("tenant_id") if isinstance(pf.get("telemetry"), dict) else pf.get("tenant_id")
            
    tenant_id = tenant_id_raw or "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"

    # ── PASSO 1: Plano Semântico (NLU) ──
    semantic_plan_dict = debug_data.get("semantic_plan")
    semantic_plan = None
    if start_step == "semantic":
        if args.call_ai:
            print("[*] Chamando OpenAI (Intent Engine) para gerar um novo Plano Semântico...")
            try:
                from services.ai_credential_manager import ai_credential_manager
                from services.metadata_catalog.intent_engine import intent_engine
                lease = await ai_credential_manager.resolve_client(tenant_id=uuid.UUID(tenant_id))
                intent_output = await intent_engine.classify_intent(
                    query=debug_data.get("pergunta"),
                    client=lease.client,
                    model=lease.model
                )
                semantic_plan = intent_output.plan
                print("    -> Novo Plano Semântico gerado via OpenAI com sucesso!")
            except Exception as e:
                print(f"    [!] Falha ao chamar OpenAI para Semantic Plan: {e}. Usando plano em cache...")
                semantic_plan = SemanticPlan.model_validate(semantic_plan_dict) if semantic_plan_dict else None
        else:
            print("[*] Reexecutando a partir do Semantic Plan em cache...")
            semantic_plan = SemanticPlan.model_validate(semantic_plan_dict) if semantic_plan_dict else None
    else:
        if semantic_plan_dict:
            semantic_plan = SemanticPlan.model_validate(semantic_plan_dict)

    # ── PASSO 2: Canonicalizer ──
    canonical_plan_dict = debug_data.get("canonical_plan")
    if start_step in ("semantic", "canonical"):
        print("[*] Reexecutando Canonicalizer...")
        canonical_plan = orchestrator.resolver.canonicalize(semantic_plan)
    else:
        if canonical_plan_dict:
            canonical_plan = CanonicalPlan.model_validate(canonical_plan_dict)
        else:
            canonical_plan = None

    # ── PASSO 3: Metadata Resolver (Plano Físico) ──
    exec_plan_dict = debug_data.get("execution_plan")
    if start_step in ("semantic", "canonical", "resolver"):
        print("[*] Reexecutando Metadata Resolver (Cálculo de Scores e Views)...")
        exec_plan = orchestrator.planner.resolve(canonical_plan)
        print(f"    -> Views Escolhidas: {exec_plan.selected_views}")
        print(f"    -> Scores: {exec_plan.resolution_justification}")
    else:
        if exec_plan_dict:
            exec_plan = ExecutionPlan.model_validate(exec_plan_dict)
        else:
            exec_plan = None

    # ── PASSO 4: SQL Generator ──
    sql = debug_data.get("sql", {}).get("raw_sql")
    binds = debug_data.get("sql", {}).get("parameters", {})
    if start_step in ("semantic", "canonical", "resolver", "sql"):
        print("[*] Recompilando e otimizando SQL...")
        optimized_plan = orchestrator.optimizer.optimize_plan(exec_plan)
        sql, binds = orchestrator.generator.generate_sql(optimized_plan)
        print("    -> SQL Compilado:")
        print(sql)
        print(f"    -> Parâmetros: {binds}")

    # ── PASSO 5: Execução no Banco PostgreSQL Clone ──
    normalized_rows = debug_data.get("sample_rows", [])
    db_metrics = {}
    if start_step in ("semantic", "canonical", "resolver", "sql", "banco"):
        print("[*] Reexecutando query física no banco PostgreSQL clone...")
        db_start = time.perf_counter()
        
        # Executa consulta física
        result_dataset = await database_executor.execute_query(
            plan=exec_plan,
            sql=sql,
            binds=binds,
            tenant_id=tenant_id
        )
        normalized_rows = result_dataset.get("values", [])
        db_metrics = {
            "execution_time_ms": result_dataset.get("db_time_ms", 0.0),
            "explain": result_dataset.get("explain", "N/A"),
            "explain_analyze": result_dataset.get("explain_analyze", "N/A")
        }
        print(f"    -> {len(normalized_rows)} registros retornados.")
        print(f"    -> Tempo de banco: {db_metrics['execution_time_ms']:.2f}ms")
        print("    -> EXPLAIN ANALYZE:")
        print(db_metrics["explain_analyze"])

    # ── PASSO 6: Transformer ──
    transformed_chart_data = debug_data.get("transformer", {}).get("output", {})
    if start_step in ("semantic", "canonical", "resolver", "sql", "banco", "transformer"):
        print("[*] Reexecutando Data Transformer...")
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
        v_type_str = canonical_plan.suggested_visualization.value.upper() if canonical_plan else "TABLE"
        target_chart_type = vis_map.get(v_type_str, SchemaChartType.TABLE)
        
        transformed_chart_data = transform_data(normalized_rows, target_chart_type)
        print("    -> Saída do Transformer (Estrutura de Gráfico):")
        print(json.dumps(transformed_chart_data, indent=2, default=str))

    # ── PASSO 7: Explainability (IA) ──
    explanation_summary = debug_data.get("llm_response")
    if args.call_ai:
        print("[*] Executando chamada real à OpenAI para Explainability...")
        from services.ai_credential_manager import ai_credential_manager
        lease = await ai_credential_manager.resolve_client(tenant_id=uuid.UUID(tenant_id))
        
        from services.metadata_catalog.explainability import explainability_engine
        from models.new_pipeline_contracts import DashboardState
        explanation, _ = await explainability_engine.generate_explanation(
            query=debug_data.get("pergunta"),
            plan=canonical_plan,
            dataset=normalized_rows,
            db_state=DashboardState(chart_type=VisualizationType.TABLE),
            client=lease.client,
            model=lease.model
        )
        explanation_summary = explanation.summary
    else:
        print("[*] Reutilizando resposta da IA salva no trace de debug (call_ai=False)...")
        
    print("\n" + "=" * 80)
    print("REPLAY CONCLUÍDO COM SUCESSO!")
    print(f"Resposta IA: {explanation_summary}")
    print("=" * 80)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_replay())
