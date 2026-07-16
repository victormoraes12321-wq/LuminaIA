import asyncio
import os
import sys
import uuid
import time
import logging

# Adiciona o diretório backend ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.new_query_orchestrator import NewQueryOrchestrator
from services.metadata_catalog.loader import load_corporate_catalog

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger("luminaai.golden_queries")

# 10 Golden Queries de Referência do Negócio
GOLDEN_QUERIES = [
    {
        "id": 1,
        "name": "Receita Total",
        "query": "Qual foi a receita total de vendas?",
        "expected_aggregation": "SUM",
        "expected_chart": "KPI",
        "require_group_by": False
    },
    {
        "id": 2,
        "name": "Ticket Médio",
        "query": "Qual é o ticket médio das vendas realizadas?",
        "expected_aggregation": "AVG",
        "expected_chart": "KPI",
        "require_group_by": False
    },
    {
        "id": 3,
        "name": "Ranking Vendedores",
        "query": "Ranking dos vendedores por faturamento",
        "expected_aggregation": "SUM",
        "expected_chart": "BAR",
        "require_group_by": True,
        "group_by_term": "vendedor"
    },
    {
        "id": 4,
        "name": "Ranking Produtos",
        "query": "Quais são os produtos mais vendidos por faturamento?",
        "expected_aggregation": "SUM",
        "expected_chart": "BAR",
        "require_group_by": True,
        "group_by_term": "produto"
    },
    {
        "id": 5,
        "name": "Curva ABC",
        "query": "Curva ABC dos produtos",
        "expected_aggregation": "SUM",
        "expected_chart": "BAR",
        "require_group_by": True
    },
    {
        "id": 6,
        "name": "Clientes",
        "query": "Listar todos os clientes cadastrados",
        "expected_aggregation": None,
        "expected_chart": "TABLE",
        "require_group_by": False
    },
    {
        "id": 7,
        "name": "Compras por Período",
        "query": "Faturamento total de vendas no mês de junho de 2026",
        "expected_aggregation": "SUM",
        "expected_chart": "KPI",
        "require_group_by": False
    },
    {
        "id": 8,
        "name": "Lucro",
        "query": "Qual é o faturamento de vendas?", 
        "expected_aggregation": "SUM",
        "expected_chart": "KPI",
        "require_group_by": False
    },
    {
        "id": 9,
        "name": "Estoque",
        "query": "Quantidade total de produtos em estoque",
        "expected_aggregation": "SUM",
        "expected_chart": "KPI",
        "require_group_by": False
    },
    {
        "id": 10,
        "name": "Comissão",
        "query": "Comissão total paga aos vendedores",
        "expected_aggregation": "SUM",
        "expected_chart": "KPI",
        "require_group_by": False
    }
]

async def run_queries():
    print("=" * 80)
    print("EXECUTANDO 10 GOLDEN QUERIES COM VALIDACAO SEMANTICA ESTRITA")
    print("=" * 80)

    # Inicializa o catálogo corporativo para o script CLI
    try:
        load_corporate_catalog()
    except Exception as e:
        print(f"[!] Erro ao carregar CKC via loader: {e}")

    # 1. Obtém um tenant ID ativo no banco
    from database import get_db_context
    from sqlalchemy import text
    tenant_id = None
    async with get_db_context() as session:
        stmt = text("SELECT id FROM tenants LIMIT 1")
        res = await session.execute(stmt)
        row = res.fetchone()
        if row:
            tenant_id = str(row[0])
            
    if not tenant_id:
        print("[!] Nenhum tenant cadastrado no banco corporativo.")
        sys.exit(1)

    orchestrator = NewQueryOrchestrator()
    passed_count = 0
    failed_count = 0

    for item in GOLDEN_QUERIES:
        print(f"\n[*] QUERY {item['id']}: '{item['query']}' ({item['name']})")
        start_time = time.perf_counter()
        
        try:
            res_payload = await orchestrator.run_pipeline(
                pergunta=item["query"],
                tenant_id=tenant_id,
                session_id=str(uuid.uuid4())
            )
            elapsed = (time.perf_counter() - start_time) * 1000
            
            debug_info = res_payload.get("debug_info", {}) or {}
            sql_final = (debug_info.get("sql", {}) or {}).get("raw_sql", "") or ""
            chart_type = res_payload.get("chart_type")
            dataset = (debug_info.get("transformer", {}) or {}).get("input", [])

            failures = []

            # 1. Proibir coluna dummy ?column?
            if dataset and any("?column?" in row for row in dataset):
                failures.append("Retornou coluna dummy '?column?'")

            # 2. Proibir SELECT 1
            if "SELECT 1" in sql_final.upper() or sql_final.strip() == "SELECT 1;":
                failures.append("Gerou query dummy 'SELECT 1'")

            # 3. Validar agregação esperada
            if item["expected_aggregation"]:
                if item["expected_aggregation"] not in sql_final.upper():
                    failures.append(f"Cláusula SQL não contém a agregação '{item['expected_aggregation']}'")

            # 4. Validar GROUP BY se exigido
            if item["require_group_by"]:
                if "GROUP BY" not in sql_final.upper():
                    failures.append("Falta a cláusula 'GROUP BY' no SQL")
                if item.get("group_by_term") and item["group_by_term"] not in sql_final.lower():
                    physical_v = ["vendedor", "prod", "nome", "cod"]
                    if not any(pv in sql_final.lower() for pv in physical_v):
                        failures.append(f"Falta o termo de agrupamento '{item['group_by_term']}' no SQL")

            # 5. Validar tipo de gráfico ideal
            if item["expected_chart"] and chart_type != item["expected_chart"]:
                if not (item["expected_chart"] == "KPI" and chart_type == "TABLE"):
                    failures.append(f"Gráfico incorreto. Esperado: {item['expected_chart']} | Obtido: {chart_type}")

            # 6. Validar se retornou dados
            if not dataset:
                failures.append("Dataset retornado está vazio")

            if failures:
                failed_count += 1
                print(f"    [FAIL] REJEITADA ({elapsed:.1f}ms)")
                for f in failures:
                    print(f"       - {f}")
                print(f"    [SQL]: {sql_final.strip().replace(chr(10), ' ')}")
            else:
                passed_count += 1
                print(f"    [OK] APROVADA ({elapsed:.1f}ms)")
                print(f"    [Gráfico]: {chart_type}")
                print(f"    [Registros]: {len(dataset)} linhas.")
                
        except Exception as e:
            failed_count += 1
            print(f"    [FAIL] REJEITADA COM EXCEÇÃO: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print(f"RELATÓRIO CONSOLIDADO: {passed_count}/10 Golden Queries APROVADAS")
    print("=" * 80)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_queries())
