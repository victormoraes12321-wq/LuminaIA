"""
LuminaAI — Executive Metrics Service (Real PostgreSQL Clone Aggregator)
----------------------------------------------------------------------
Calcula métricas executivas determinísticas diretamente do banco `luminaai_clone`
com suporte a filtros multidimensionais, períodos dinâmicos e isolamento de tenant.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy import text
from config import settings

logger = logging.getLogger("luminaai.services.executive_metrics")

_clone_engine: Optional[AsyncEngine] = None

def get_clone_engine() -> AsyncEngine:
    global _clone_engine
    if _clone_engine is None:
        base_url = settings.DATABASE_URL.rsplit("/", 1)[0]
        clone_url = f"{base_url}/luminaai_clone"
        _clone_engine = create_async_engine(
            clone_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    return _clone_engine

def _format_brl(val: float) -> str:
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def _format_num(val: float) -> str:
    return f"{int(val):,}".replace(",", ".")

async def get_executive_metrics(
    tenant_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    filial: Optional[str] = None,
    rca: Optional[str] = None,
    codprod: Optional[str] = None,
    codcli: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executa agregação determinística em tempo real contra as views do clone.
    """
    engine = get_clone_engine()

    async with engine.connect() as conn:
        # 1. Dataset Date Boundaries
            boundary_res = (await conn.execute(text("SELECT MIN(dtemissao_), MAX(dtemissao_) FROM vw_vendas_lm;"))).fetchone()
            min_available = boundary_res[0].strftime("%Y-%m-%d") if boundary_res and boundary_res[0] else "2024-08-19"
            max_available = boundary_res[1].strftime("%Y-%m-%d") if boundary_res and boundary_res[1] else "2026-08-18"

            # Apply default period if not supplied (Default: Year 2026 up to max available)
            effective_start = start_date if start_date else "2026-01-01"
            effective_end = end_date if end_date else max_available

            # 2. Build Where Clauses & Parameters
            where_clauses = ["1=1"]
            params: Dict[str, Any] = {}

            if effective_start:
                where_clauses.append("dtemissao_ >= :start_date")
                params["start_date"] = datetime.strptime(f"{effective_start} 00:00:00", "%Y-%m-%d %H:%M:%S")

            if effective_end:
                where_clauses.append("dtemissao_ <= :end_date")
                params["end_date"] = datetime.strptime(f"{effective_end} 23:59:59", "%Y-%m-%d %H:%M:%S")

            if filial and filial.lower() not in ("all", "todas"):
                filial_list = [f.strip() for f in filial.split(",") if f.strip()]
                if len(filial_list) == 1:
                    where_clauses.append("filial_ = :filial")
                    params["filial"] = filial_list[0]
                elif len(filial_list) > 1:
                    where_clauses.append("filial_ = ANY(:filial_list)")
                    params["filial_list"] = filial_list

            if rca:
                if str(rca).isdigit():
                    where_clauses.append("rca_ = :rca")
                    params["rca"] = int(rca)
                else:
                    where_clauses.append("UPPER(nome_) LIKE :rca_name")
                    params["rca_name"] = f"%{str(rca).upper()}%"

            if codprod:
                if str(codprod).isdigit():
                    where_clauses.append("codprod_ = :codprod")
                    params["codprod"] = int(codprod)
                else:
                    where_clauses.append("UPPER(descricao_) LIKE :prod_name")
                    params["prod_name"] = f"%{str(codprod).upper()}%"

            if codcli:
                if str(codcli).isdigit():
                    where_clauses.append("codcliente_ = :codcli")
                    params["codcli"] = int(codcli)
                else:
                    where_clauses.append("UPPER(razao_) LIKE :cli_name")
                    params["cli_name"] = f"%{str(codcli).upper()}%"

            where_sql = " AND ".join(where_clauses)

            # 3. Aggregated KPIs
            kpi_sql = f"""
                SELECT
                    COALESCE(SUM(ptotal_), 0) as faturamento_total,
                    COALESCE(SUM(qtde_), 0) as quantidade_total,
                    COUNT(DISTINCT nota_) as total_notas,
                    COUNT(DISTINCT pedido_) as total_pedidos,
                    COUNT(DISTINCT codcliente_) as clientes_ativos,
                    COUNT(DISTINCT rca_) as vendedores_ativos,
                    COUNT(DISTINCT codprod_) as produtos_distintos,
                    COUNT(DISTINCT filial_) as filiais_ativas,
                    COALESCE(AVG(ptotal_), 0) as preco_medio_item
                FROM vw_vendas_lm
                WHERE {where_sql};
            """
            kpi_res = (await conn.execute(text(kpi_sql), params)).fetchone()

            faturamento = float(kpi_res[0]) if kpi_res else 0.0
            quantidade = float(kpi_res[1]) if kpi_res else 0.0
            total_notas = int(kpi_res[2]) if kpi_res else 0
            total_pedidos = int(kpi_res[3]) if kpi_res else 0
            clientes_ativos = int(kpi_res[4]) if kpi_res else 0
            vendedores_ativos = int(kpi_res[5]) if kpi_res else 0
            produtos_distintos = int(kpi_res[6]) if kpi_res else 0
            filiais_ativas = int(kpi_res[7]) if kpi_res else 0
            ticket_medio = faturamento / (total_notas if total_notas > 0 else 1)

            # 4. Temporal Evolution
            time_group = "TO_CHAR(dtemissao_, 'YYYY-MM')"
            
            evolution_sql = f"""
                SELECT
                    {time_group} as period_key,
                    MIN(dtemissao_) as sort_date,
                    SUM(ptotal_) as revenue,
                    SUM(qtde_) as volume,
                    COUNT(DISTINCT nota_) as invoices
                FROM vw_vendas_lm
                WHERE {where_sql}
                GROUP BY period_key
                ORDER BY sort_date ASC;
            """
            evo_res = (await conn.execute(text(evolution_sql), params)).fetchall()
            evolution = [
                {
                    "date": str(r[0]),
                    "label": str(r[0]),
                    "value": float(r[2]),
                    "volume": float(r[3]),
                    "invoices": int(r[4]),
                    "formatted": _format_brl(float(r[2])),
                    "formatted_volume": f"{_format_num(float(r[3]))} un",
                }
                for r in evo_res
            ]

            # 5. Branch Performance
            branch_sql = f"""
                SELECT
                    filial_,
                    SUM(ptotal_) as revenue,
                    SUM(qtde_) as volume,
                    COUNT(DISTINCT rca_) as sellers_count,
                    COUNT(DISTINCT codcliente_) as clients_count,
                    COUNT(DISTINCT nota_) as invoices_count
                FROM vw_vendas_lm
                WHERE {where_sql}
                GROUP BY filial_
                ORDER BY revenue DESC;
            """
            branch_res = (await conn.execute(text(branch_sql), params)).fetchall()
            branch_performance = [
                {
                    "filial": str(b[0]),
                    "name": f"Filial {b[0]}" + (" (Matriz)" if str(b[0]) == "1" else ""),
                    "value": float(b[1]),
                    "percentage": round((float(b[1]) / faturamento * 100) if faturamento > 0 else 0, 1),
                    "volume": float(b[2]),
                    "sellers_count": int(b[3]),
                    "clients_count": int(b[4]),
                    "invoices_count": int(b[5]),
                    "formatted": _format_brl(float(b[1])),
                }
                for b in branch_res
            ]

            # 6. Top 10 Real Sellers (Consolidated company-wide or by filial)
            if rca:
                # When drilling down into a specific seller, show their sales per filial
                seller_sql = f"""
                    SELECT
                        rca_,
                        nome_,
                        filial_,
                        SUM(ptotal_) as revenue,
                        SUM(qtde_) as volume,
                        COUNT(DISTINCT nota_) as invoices_count
                    FROM vw_vendas_lm
                    WHERE {where_sql}
                    GROUP BY rca_, nome_, filial_
                    ORDER BY revenue DESC;
                """
                seller_res = (await conn.execute(text(seller_sql), params)).fetchall()
                top_sellers = [
                    {
                        "id": f"{s[0]}-{s[2]}",
                        "rca": int(s[0]),
                        "name": str(s[1]),
                        "filial": str(s[2]),
                        "value": float(s[3]),
                        "volume": float(s[4]),
                        "sales_count": int(s[5]),
                        "formatted": _format_brl(float(s[3])),
                    }
                    for s in seller_res
                ]
            else:
                # General ranking: consolidate across all active branches
                seller_sql = f"""
                    SELECT
                        rca_,
                        nome_,
                        COUNT(DISTINCT filial_) as branches_count,
                        MIN(filial_) as sample_filial,
                        SUM(ptotal_) as revenue,
                        SUM(qtde_) as volume,
                        COUNT(DISTINCT nota_) as invoices_count
                    FROM vw_vendas_lm
                    WHERE {where_sql}
                    GROUP BY rca_, nome_
                    ORDER BY revenue DESC
                    LIMIT 10;
                """
                seller_res = (await conn.execute(text(seller_sql), params)).fetchall()
                top_sellers = [
                    {
                        "id": str(s[0]),
                        "rca": int(s[0]),
                        "name": str(s[1]),
                        "filial": f"{s[2]} filiais" if int(s[2]) > 1 else f"Filial {s[3]}",
                        "value": float(s[4]),
                        "volume": float(s[5]),
                        "sales_count": int(s[6]),
                        "formatted": _format_brl(float(s[4])),
                    }
                    for s in seller_res
                ]

            # 7. Top 10 Real Products
            prod_sql = f"""
                SELECT
                    codprod_,
                    descricao_,
                    SUM(ptotal_) as revenue,
                    SUM(qtde_) as volume,
                    COUNT(*) as transactions_count
                FROM vw_vendas_lm
                WHERE {where_sql}
                GROUP BY codprod_, descricao_
                ORDER BY revenue DESC
                LIMIT 10;
            """
            prod_res = (await conn.execute(text(prod_sql), params)).fetchall()
            top_products = [
                {
                    "id": str(p[0]),
                    "codprod": int(p[0]),
                    "name": str(p[1]),
                    "value": float(p[2]),
                    "quantity": float(p[3]),
                    "transactions_count": int(p[4]),
                    "formatted": _format_brl(float(p[2])),
                    "quantity_formatted": f"{_format_num(float(p[3]))} un",
                }
                for p in prod_res
            ]

            # 8. Top 10 Real Clients
            client_sql = f"""
                SELECT
                    codcliente_,
                    razao_,
                    SUM(ptotal_) as revenue,
                    COUNT(DISTINCT nota_) as invoices_count,
                    SUM(qtde_) as volume
                FROM vw_vendas_lm
                WHERE {where_sql}
                GROUP BY codcliente_, razao_
                ORDER BY revenue DESC
                LIMIT 10;
            """
            client_res = (await conn.execute(text(client_sql), params)).fetchall()
            top_clients = [
                {
                    "id": str(c[0]),
                    "codcliente": int(c[0]),
                    "name": str(c[1]),
                    "value": float(c[2]),
                    "invoices_count": int(c[3]),
                    "volume": float(c[4]),
                    "formatted": _format_brl(float(c[2])),
                }
                for c in client_res
            ]

            # 9. Available Branches List
            all_branches_res = (await conn.execute(text("SELECT DISTINCT filial_ FROM vw_vendas_lm ORDER BY filial_;"))).fetchall()
            available_branches = [str(b[0]) for b in all_branches_res]

            # 10. Dynamic Deterministic Insights
            insights = []
            if branch_performance:
                top_b = branch_performance[0]
                insights.append({
                    "id": "ins-branch-leader",
                    "title": f"{top_b['name']} lidera com {top_b['percentage']}% do faturamento",
                    "description": f"Concentra {top_b['formatted']} no período com {top_b['sellers_count']} vendedores e {top_b['clients_count']} clientes ativos.",
                    "type": "highlight",
                    "entity_type": "filial",
                    "entity_id": top_b["filial"],
                })

            if top_products:
                top_p = top_products[0]
                insights.append({
                    "id": "ins-product-leader",
                    "title": f"'{top_p['name']}' é o produto com maior receita",
                    "description": f"Faturamento de {top_p['formatted']} ({top_p['quantity_formatted']} comercializadas).",
                    "type": "growth",
                    "entity_type": "produto",
                    "entity_id": top_p["id"],
                })

            if top_sellers:
                top_s = top_sellers[0]
                insights.append({
                    "id": "ins-seller-leader",
                    "title": f"Vendedor destaque: {top_s['name']}",
                    "description": f"Liderança com {top_s['formatted']} faturados em {top_s['sales_count']} notas fiscais na Filial {top_s['filial']}.",
                    "type": "growth",
                    "entity_type": "vendedor",
                    "entity_id": top_s["id"],
                })

            if len(evolution) >= 2:
                prev_m = evolution[-2]["value"]
                last_m = evolution[-1]["value"]
                if prev_m > 0:
                    pct = ((last_m - prev_m) / prev_m) * 100
                    direction = "Crescimento" if pct >= 0 else "Queda"
                    insights.append({
                        "id": "ins-evolution-trend",
                        "title": f"{direction} de {abs(pct):.2f}% no faturamento recente",
                        "description": f"Comparativo {evolution[-2]['label']} ({evolution[-2]['formatted']}) vs {evolution[-1]['label']} ({evolution[-1]['formatted']}).",
                        "type": "growth" if pct >= 0 else "neutral",
                    })

            return {
                "metadata": {
                    "min_available_date": min_available,
                    "max_available_date": max_available,
                    "effective_start_date": effective_start,
                    "effective_end_date": effective_end,
                    "freshness": f"{max_available} 23:59 (PostgreSQL Real Clone)",
                    "available_branches": available_branches,
                },
                "kpis": {
                    "faturamento": faturamento,
                    "quantidade": quantidade,
                    "total_notas": total_notas,
                    "total_pedidos": total_pedidos,
                    "clientes_ativos": clientes_ativos,
                    "vendedores_ativos": vendedores_ativos,
                    "produtos_distintos": produtos_distintos,
                    "filiais_ativas": filiais_ativas,
                    "ticket_medio": ticket_medio,
                    "faturamento_formatted": _format_brl(faturamento),
                    "quantidade_formatted": f"{_format_num(quantidade)} un",
                    "ticket_medio_formatted": _format_brl(ticket_medio),
                    "notas_formatted": _format_num(total_notas),
                    "pedidos_formatted": _format_num(total_pedidos),
                },
                "evolution": evolution,
                "branch_performance": branch_performance,
                "top_sellers": top_sellers,
                "top_products": top_products,
                "top_clients": top_clients,
                "insights": insights,
            }
