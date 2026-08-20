"""
LuminaAI — Serviço de Logística, Operações, Rebalanceamento de Filiais e Análise Geográfica
-----------------------------------------------------------------------------------------
Calcula:
1. Rebalanceamento de Estoque entre Filiais:
   Cruza velocidade de vendas com estoque cadastrado para identificar desbalanceamentos
   (ex: Filial 1 com excesso / sem giro vs Filial 2 com ruptura / alta demanda)
   e sugere transferências internas inteligentes antes de novas compras.
2. Análise Geográfica Regional (Mapa / Ranking de Calor):
   Agrupa vendas por Município, UF e Praça a partir de VW_CLIENTES_CAD_LM.
3. Segregação Analítica de Movimentos por CFOP (Vendas Reais vs Transferências / Remessas).
"""
from __future__ import annotations

import logging
from typing import Any
import asyncpg

from config import settings

logger = logging.getLogger("luminaai.services.logistics")


async def get_clone_connection() -> asyncpg.Connection:
    base_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    clone_url = base_url.rsplit("/", 1)[0] + "/luminaai_clone"
    return await asyncpg.connect(clone_url)


async def get_inventory_branch_rebalancing(limit: int = 50) -> list[dict[str, Any]]:
    """
    Identifica oportunidades de transferência de estoque entre filiais.
    """
    conn = await get_clone_connection()
    try:
        # Vendas por produto e filial nos últimos 90 dias
        query = """
        WITH vendas_filiais AS (
            SELECT
                v.CODPROD_::TEXT AS codprod,
                MAX(v.DESCRICAO_) AS descricao,
                v.FILIAL_ AS filial,
                COUNT(DISTINCT v.NOTA_) AS total_notas,
                SUM(v.QTDE_) AS qtde_vendida,
                SUM(v.PTOTAL_) AS receita_total
            FROM vw_vendas_lm v
            WHERE v.DTEMISSAO_ >= (SELECT MAX(DTEMISSAO_) - INTERVAL '90 days' FROM vw_vendas_lm)
              AND v.FILIAL_ IS NOT NULL
            GROUP BY v.CODPROD_::TEXT, v.FILIAL_
        ),
        produtos_agg AS (
            SELECT
                codprod,
                MAX(descricao) AS descricao,
                SUM(qtde_vendida) AS qtde_total_vendida,
                COUNT(DISTINCT filial) AS filiais_ativas
            FROM vendas_filiais
            GROUP BY codprod
            HAVING SUM(qtde_vendida) > 5 AND COUNT(DISTINCT filial) >= 2
        ),
        estoque_cad AS (
            SELECT
                p.CODIGO::TEXT AS codprod,
                COALESCE(p.ESTOQUE, 0) AS estoque_total,
                p.SITUACAO AS situacao
            FROM vw_produtos_cad_lm p
        )
        SELECT
            p.codprod,
            p.descricao,
            p.qtde_total_vendida,
            p.filiais_ativas,
            COALESCE(e.estoque_total, 0) AS estoque_total
        FROM produtos_agg p
        LEFT JOIN estoque_cad e ON e.codprod = p.codprod
        ORDER BY p.qtde_total_vendida DESC
        LIMIT $1;
        """
        rows = await conn.fetch(query, limit)
        
        # Agora busca a distribuição por filial dos produtos selecionados
        codprods = [r["codprod"] for r in rows]
        if not codprods:
            return []

        branch_details = await conn.fetch(
            """
            SELECT
                v.CODPROD_::TEXT AS codprod,
                v.FILIAL_ AS filial,
                SUM(v.QTDE_) AS qtde_vendida,
                SUM(v.PTOTAL_) AS receita_total,
                COUNT(DISTINCT v.NOTA_) AS pedidos
            FROM vw_vendas_lm v
            WHERE v.CODPROD_::TEXT = ANY($1::TEXT[])
              AND v.DTEMISSAO_ >= (SELECT MAX(DTEMISSAO_) - INTERVAL '90 days' FROM vw_vendas_lm)
            GROUP BY v.CODPROD_::TEXT, v.FILIAL_
            ORDER BY v.CODPROD_::TEXT, qtde_vendida DESC;
            """,
            codprods,
        )

        branch_map: dict[str, list[dict[str, Any]]] = {}
        for b in branch_details:
            branch_map.setdefault(b["codprod"], []).append({
                "filial": str(b["filial"]),
                "qtde_vendida": float(b["qtde_vendida"] or 0),
                "receita_total": float(b["receita_total"] or 0),
                "pedidos": int(b["pedidos"] or 0),
            })

        rebalancing_suggestions: list[dict[str, Any]] = []
        for r in rows:
            prod_id = r["codprod"]
            branches = branch_map.get(prod_id, [])
            if len(branches) < 2:
                continue

            # A filial com maior demanda (demanda alta)
            highest_demand = branches[0]
            # A filial com menor demanda (estoque ocioso potencial)
            lowest_demand = branches[-1]

            diff_qty = highest_demand["qtde_vendida"] - lowest_demand["qtde_vendida"]
            if diff_qty >= 3:
                sugestao_qtd = max(1, int(diff_qty * 0.4))
                rebalancing_suggestions.append({
                    "codigo_produto": prod_id,
                    "descricao": r["descricao"],
                    "filial_origem": lowest_demand["filial"],
                    "filial_destino": highest_demand["filial"],
                    "qtde_sugerida_transferencia": sugestao_qtd,
                    "demanda_destino_90d": highest_demand["qtde_vendida"],
                    "demanda_origem_90d": lowest_demand["qtde_vendida"],
                    "estoque_geral": float(r["estoque_total"]),
                    "impacto_estimado_brl": float(highest_demand["receita_total"] / max(1, highest_demand["qtde_vendida"])) * sugestao_qtd,
                    "motivo": f"Filial {highest_demand['filial']} possui demanda {highest_demand['qtde_vendida']:.0f} un vs {lowest_demand['qtde_vendida']:.0f} un na Filial {lowest_demand['filial']}. Transferência balanceia a cobertura sem nova compra.",
                    "prioridade": "ALTA" if diff_qty > 20 else "MEDIA",
                })

        return rebalancing_suggestions
    except Exception as exc:
        logger.error("[LogisticsService] Erro ao calcular rebalanceamento: %s", exc)
        return []
    finally:
        await conn.close()


async def get_regional_sales_heatmap(limit: int = 50) -> dict[str, Any]:
    """
    Calcula o mapa e ranking geográfico de vendas por Cidade, UF e Praça.
    """
    conn = await get_clone_connection()
    try:
        query = """
        SELECT
            COALESCE(NULLIF(TRIM(c.NOME_CIDADE), ''), 'Não Informada') AS cidade,
            COALESCE(NULLIF(TRIM(c.UF), ''), 'UF') AS uf,
            COALESCE(NULLIF(TRIM(c.PRACA), ''), 'Geral') AS praca,
            COUNT(DISTINCT v.NOTA_) AS total_notas,
            COUNT(DISTINCT v.CODCLIENTE_) AS clientes_distintos,
            SUM(v.QTDE_) AS unidades_vendidas,
            SUM(v.PTOTAL_) AS faturamento_total,
            AVG(v.PTOTAL_) AS ticket_medio_item
        FROM vw_vendas_lm v
        LEFT JOIN vw_clientes_cad_lm c ON c.CODIGO::TEXT = v.CODCLIENTE_::TEXT
        WHERE v.PTOTAL_ > 0
        GROUP BY c.NOME_CIDADE, c.UF, c.PRACA
        ORDER BY faturamento_total DESC
        LIMIT $1;
        """
        rows = await conn.fetch(query, limit)
        
        cidades_ranking = []
        uf_totals: dict[str, float] = {}
        for r in rows:
            fat = float(r["faturamento_total"] or 0)
            uf = r["uf"]
            uf_totals[uf] = uf_totals.get(uf, 0.0) + fat
            cidades_ranking.append({
                "cidade": r["cidade"],
                "uf": uf,
                "praca": r["praca"],
                "total_notas": int(r["total_notas"] or 0),
                "clientes_distintos": int(r["clientes_distintos"] or 0),
                "unidades_vendidas": float(r["unidades_vendidas"] or 0),
                "faturamento_total": fat,
                "faturamento_formatted": f"R$ {fat:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            })

        return {
            "total_cidades_analisadas": len(cidades_ranking),
            "distribuicao_por_uf": [
                {"uf": k, "faturamento": v, "faturamento_formatted": f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")}
                for k, v in sorted(uf_totals.items(), key=lambda x: x[1], reverse=True)
            ],
            "ranking_municipios": cidades_ranking,
        }
    except Exception as exc:
        logger.error("[LogisticsService] Erro ao calcular mapa regional: %s", exc)
        return {"total_cidades_analisadas": 0, "distribuicao_por_uf": [], "ranking_municipios": []}
    finally:
        await conn.close()


async def get_cfop_movement_distribution() -> dict[str, Any]:
    """
    Segregação analítica dos movimentos por CFOP e natureza de operação.
    """
    conn = await get_clone_connection()
    try:
        query = """
        SELECT
            COALESCE(v.CFOP_::TEXT, 'Outros') AS cfop,
            COUNT(DISTINCT v.NOTA_) AS total_notas,
            SUM(v.QTDE_) AS qtde_total,
            SUM(v.PTOTAL_) AS faturamento_total
        FROM vw_vendas_lm v
        WHERE v.PTOTAL_ > 0
        GROUP BY v.CFOP_
        ORDER BY faturamento_total DESC;
        """
        rows = await conn.fetch(query)

        vendas_reais = []
        outras_movimentacoes = []
        total_vendas_reais = 0.0
        total_outros = 0.0

        for r in rows:
            cfop = str(r["cfop"])
            fat = float(r["faturamento_total"] or 0)
            item = {
                "cfop": cfop,
                "total_notas": int(r["total_notas"] or 0),
                "qtde_total": float(r["qtde_total"] or 0),
                "faturamento_total": fat,
                "faturamento_formatted": f"R$ {fat:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                "natureza": (
                    "Venda Estadual (Produção/Revenda)" if cfop in ("5102", "5405", "5101")
                    else "Venda Interestadual (Revenda)" if cfop in ("6102", "6405", "6101")
                    else "Transferência entre Filiais" if cfop in ("5152", "5409", "6152")
                    else "Remessa / Bonificação" if cfop in ("5910", "5949", "6910")
                    else "Outras Saídas / Comercial"
                ),
            }

            if cfop.startswith(("510", "540", "610", "640")):
                vendas_reais.append(item)
                total_vendas_reais += fat
            else:
                outras_movimentacoes.append(item)
                total_outros += fat

        return {
            "total_faturamento_vendas_reais": total_vendas_reais,
            "total_faturamento_outros_movimentos": total_outros,
            "percentual_vendas_reais": round(total_vendas_reais / max(1.0, total_vendas_reais + total_outros) * 100, 2),
            "vendas_comerciais": vendas_reais,
            "outras_movimentacoes": outras_movimentacoes,
        }
    except Exception as exc:
        logger.error("[LogisticsService] Erro ao calcular distribuição CFOP: %s", exc)
        return {"total_faturamento_vendas_reais": 0, "total_faturamento_outros_movimentos": 0, "percentual_vendas_reais": 100, "vendas_comerciais": [], "outras_movimentacoes": []}
    finally:
        await conn.close()
