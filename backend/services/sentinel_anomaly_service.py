"""
LuminaAI — Sentinela Proativo de Anomalias (IA Autônoma de Negócios)
-------------------------------------------------------------------
Monitora a base transacional em segundo plano e gera alertas executivos prioritários:
1. Queda Repentina de Compras de Clientes VIP / Curva A (Risco de Perda/Churn).
2. Ruptura de Estoque em Itens de Alta Demanda (Risco de Perda de Faturamento).
3. Vendas com Margem Abaixo da Política Comercial.
4. Anomalias de Faturamento por Filial.
"""
from __future__ import annotations

import logging
from typing import Any
import asyncpg

from config import settings

logger = logging.getLogger("luminaai.services.sentinel")


async def get_clone_connection() -> asyncpg.Connection:
    base_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    clone_url = base_url.rsplit("/", 1)[0] + "/luminaai_clone"
    return await asyncpg.connect(clone_url)


async def run_sentinel_anomalies_scan(tenant_id: str | None = None) -> list[dict[str, Any]]:
    """
    Executa a varredura autônoma de anomalias na réplica de dados transacionais.
    """
    conn = await get_clone_connection()
    anomalies: list[dict[str, Any]] = []

    try:
        # 1. CLIENTES VIP (CURVA A) COM QUEDA BRUSCA DE COMPRAS NOS ÚLTIMOS 60 DIAS
        client_anomalies_query = """
        WITH max_date AS (
            SELECT MAX(DTEMISSAO_) AS max_dt FROM vw_vendas_lm
        ),
        compras_recentes AS (
            SELECT
                v.CODCLIENTE_::TEXT AS codcli,
                MAX(v.RAZAO_) AS razao,
                SUM(CASE WHEN v.DTEMISSAO_ >= m.max_dt - INTERVAL '60 days' THEN v.PTOTAL_ ELSE 0 END) AS fat_recente_60d,
                SUM(CASE WHEN v.DTEMISSAO_ < m.max_dt - INTERVAL '60 days' AND v.DTEMISSAO_ >= m.max_dt - INTERVAL '180 days' THEN v.PTOTAL_ ELSE 0 END) AS fat_anterior_120d,
                COUNT(DISTINCT CASE WHEN v.DTEMISSAO_ >= m.max_dt - INTERVAL '60 days' THEN v.NOTA_ ELSE NULL END) AS notas_recentes,
                COUNT(DISTINCT CASE WHEN v.DTEMISSAO_ < m.max_dt - INTERVAL '60 days' AND v.DTEMISSAO_ >= m.max_dt - INTERVAL '180 days' THEN v.NOTA_ ELSE NULL END) AS notas_anteriores
            FROM vw_vendas_lm v
            CROSS JOIN max_date m
            WHERE v.CODCLIENTE_ IS NOT NULL AND v.PTOTAL_ > 0
            GROUP BY v.CODCLIENTE_::TEXT
            HAVING SUM(CASE WHEN v.DTEMISSAO_ < m.max_dt - INTERVAL '60 days' AND v.DTEMISSAO_ >= m.max_dt - INTERVAL '180 days' THEN v.PTOTAL_ ELSE 0 END) >= 15000
        )
        SELECT
            c.codcli,
            c.razao,
            c.fat_recente_60d,
            (c.fat_anterior_120d / 2.0) AS media_bimestral_historica,
            c.notas_recentes,
            c.notas_anteriores,
            ROUND(((c.fat_recente_60d - (c.fat_anterior_120d / 2.0)) / NULLIF(c.fat_anterior_120d / 2.0, 0)) * 100.0, 1) AS variacao_pct
        FROM compras_recentes c
        WHERE c.fat_recente_60d < (c.fat_anterior_120d / 2.0) * 0.5
        ORDER BY (c.fat_anterior_120d / 2.0) DESC
        LIMIT 6;
        """
        client_rows = await conn.fetch(client_anomalies_query)
        for r in client_rows:
            var_pct = float(r["variacao_pct"] or 0)
            hist = float(r["media_bimestral_historica"] or 0)
            rec = float(r["fat_recente_60d"] or 0)
            anomalies.append({
                "id": f"client_churn_{r['codcli']}",
                "categoria": "CLIENTE_VIP_CHURN",
                "tipo": "QUEDA_COMPRA_VIP",
                "severidade": "CRITICAL" if rec == 0 else "WARNING",
                "titulo": f"Alerta de Churn: {r['razao']}",
                "entidade": r["razao"],
                "codigo": r["codcli"],
                "descricao": f"Cliente chave com faturamento bimestral histórico de R$ {hist:,.2f} comprou apenas R$ {rec:,.2f} nos últimos 60 dias ({var_pct:+.1f}% de queda).",
                "impacto_financeiro": hist - rec,
                "impacto_formatted": f"R$ {(hist - rec):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                "sugestao_acao": "Acionar imediatamente o RCA / consultor comercial responsável para visita ou contato direto de retenção.",
                "data_deteccao": "Agora",
            })

        # 2. PRODUTOS DE ALTA DEMANDA COM ESTOQUE ZERADO OU CRÍTICO
        stock_anomalies_query = """
        WITH max_date AS (
            SELECT MAX(DTEMISSAO_) AS max_dt FROM vw_vendas_lm
        ),
        vendas_top_produtos AS (
            SELECT
                v.CODPROD_::TEXT AS codprod,
                MAX(v.DESCRICAO_) AS descricao,
                SUM(v.QTDE_) AS qtde_vendida_60d,
                SUM(v.PTOTAL_) AS receita_60d
            FROM vw_vendas_lm v
            CROSS JOIN max_date m
            WHERE v.DTEMISSAO_ >= m.max_dt - INTERVAL '60 days'
            GROUP BY v.CODPROD_::TEXT
            HAVING SUM(v.QTDE_) >= 20
        ),
        estoque_produtos AS (
            SELECT
                p.CODIGO::TEXT AS codprod,
                COALESCE(p.ESTOQUE, 0) AS estoque_atual
            FROM vw_produtos_cad_lm p
        )
        SELECT
            v.codprod,
            v.descricao,
            v.qtde_vendida_60d,
            v.receita_60d,
            COALESCE(e.estoque_atual, 0) AS estoque_atual,
            ROUND(COALESCE(e.estoque_atual, 0) / NULLIF(v.qtde_vendida_60d / 60.0, 0), 1) AS dias_cobertura
        FROM vendas_top_produtos v
        LEFT JOIN estoque_produtos e ON e.codprod = v.codprod
        WHERE COALESCE(e.estoque_atual, 0) <= 5
        ORDER BY v.receita_60d DESC
        LIMIT 6;
        """
        stock_rows = await conn.fetch(stock_anomalies_query)
        for r in stock_rows:
            est = float(r["estoque_atual"] or 0)
            vendas = float(r["qtde_vendida_60d"] or 0)
            rec = float(r["receita_60d"] or 0)
            dias_cob = float(r["dias_cobertura"] or 0) if r["dias_cobertura"] is not None else 0
            anomalies.append({
                "id": f"stock_rupture_{r['codprod']}",
                "categoria": "ESTOQUE_RUPTURA",
                "tipo": "RUPTURA_ALTO_GIRO",
                "severidade": "CRITICAL" if est <= 0 else "WARNING",
                "titulo": f"Risco de Ruptura: {r['descricao']}",
                "entidade": r["descricao"],
                "codigo": r["codprod"],
                "descricao": f"Produto de alta venda ({vendas:.0f} un vendidas nos últimos 60 dias, gerando R$ {rec:,.2f}) possui apenas {est:.0f} unidades em estoque ({dias_cob:.1f} dias de cobertura).",
                "impacto_financeiro": rec * 0.5,
                "impacto_formatted": f"R$ {(rec * 0.5):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                "sugestao_acao": "Emitir pedido de reposição com urgência ao fornecedor ou solicitar transferência entre filiais.",
                "data_deteccao": "Agora",
            })

        # 3. FILIAIS COM ATINGIMENTO OU ANOMALIA DE PERFORMANCE
        branch_query = """
        WITH max_date AS (
            SELECT MAX(DTEMISSAO_) AS max_dt FROM vw_vendas_lm
        ),
        branch_stats AS (
            SELECT
                v.FILIAL_ AS filial,
                SUM(CASE WHEN v.DTEMISSAO_ >= m.max_dt - INTERVAL '30 days' THEN v.PTOTAL_ ELSE 0 END) AS fat_30d,
                SUM(CASE WHEN v.DTEMISSAO_ < m.max_dt - INTERVAL '30 days' AND v.DTEMISSAO_ >= m.max_dt - INTERVAL '60 days' THEN v.PTOTAL_ ELSE 0 END) AS fat_ant_30d
            FROM vw_vendas_lm v
            CROSS JOIN max_date m
            WHERE v.FILIAL_ IS NOT NULL
            GROUP BY v.FILIAL_
        )
        SELECT
            filial,
            fat_30d,
            fat_ant_30d,
            ROUND(((fat_30d - fat_ant_30d) / NULLIF(fat_ant_30d, 0)) * 100.0, 1) AS var_pct
        FROM branch_stats
        WHERE fat_ant_30d > 0
        ORDER BY var_pct ASC;
        """
        branch_rows = await conn.fetch(branch_query)
        for r in branch_rows:
            var_pct = float(r["var_pct"] or 0)
            fat_atual = float(r["fat_30d"] or 0)
            fat_ant = float(r["fat_ant_30d"] or 0)
            if var_pct < -25:
                anomalies.append({
                    "id": f"branch_drop_{r['filial']}",
                    "categoria": "FILIAL_DESEMPENHO",
                    "tipo": "QUEDA_FILIAL",
                    "severidade": "WARNING",
                    "titulo": f"Desaceleração na Filial {r['filial']}",
                    "entidade": f"Filial {r['filial']}",
                    "codigo": str(r["filial"]),
                    "descricao": f"A Filial {r['filial']} registrou R$ {fat_atual:,.2f} no último mês vs R$ {fat_ant:,.2f} no mês anterior ({var_pct:+.1f}% de variação).",
                    "impacto_financeiro": max(0.0, fat_ant - fat_atual),
                    "impacto_formatted": f"R$ {max(0.0, fat_ant - fat_atual):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    "sugestao_acao": "Avaliar se a queda foi provocada por falta de produtos específicos ou retração em carteiras de vendedores locais.",
                    "data_deteccao": "Agora",
                })
            elif var_pct > 30:
                anomalies.append({
                    "id": f"branch_growth_{r['filial']}",
                    "categoria": "OPORTUNIDADE_COMERCIAL",
                    "tipo": "CRESCIMENTO_FILIAL",
                    "severidade": "OPPORTUNITY",
                    "titulo": f"Crescimento Expressivo: Filial {r['filial']}",
                    "entidade": f"Filial {r['filial']}",
                    "codigo": str(r["filial"]),
                    "descricao": f"A Filial {r['filial']} acelerou {var_pct:+.1f}%, atingindo R$ {fat_atual:,.2f} no último mês.",
                    "impacto_financeiro": fat_atual - fat_ant,
                    "impacto_formatted": f"R$ {(fat_atual - fat_ant):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    "sugestao_acao": "Assegurar abastecimento contínuo para sustentar a curva de crescimento da praça.",
                    "data_deteccao": "Agora",
                })

        return anomalies
    except Exception as exc:
        logger.error("[SentinelService] Erro ao executar varredura de anomalias: %s", exc)
        return []
    finally:
        await conn.close()
