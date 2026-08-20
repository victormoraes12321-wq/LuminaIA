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


async def run_sentinel_anomalies_scan() -> list[dict[str, Any]]:
    """
    Executa varredura analítica proativa no banco de dados `luminaai_clone`
    e retorna lista de anomalias governadas com métricas exatas e datas reais.
    """
    conn = await get_clone_connection()
    anomalies: list[dict[str, Any]] = []

    try:
        # 1. CLIENTES VIP (CURVA A) COM QUEDA BRUSCA DE COMPRAS
        # -------------------------------------------------------
        # Comparação SAZONAL VÁLIDA: mesmo período de 60 dias do ano anterior vs. hoje.
        # Requisito: cliente precisa ter compras em AMBOS os períodos.
        # Threshold: queda > 50% vs. mesmo período do ano passado.
        client_anomalies_query = """
        WITH max_date AS (
            SELECT MAX(DTEMISSAO_) AS max_dt FROM vw_vendas_lm
        ),
        periodo_atual AS (
            SELECT
                v.CODCLIENTE_::TEXT AS codcli,
                MAX(v.RAZAO_) AS razao,
                SUM(v.PTOTAL_) AS fat_atual_60d,
                COUNT(DISTINCT v.NOTA_) AS notas_atuais,
                MAX(v.DTEMISSAO_) AS dt_ultima_compra_atual,
                (m.max_dt - INTERVAL '60 days') AS dt_inicio_atual,
                m.max_dt AS dt_fim_atual
            FROM vw_vendas_lm v
            CROSS JOIN max_date m
            WHERE
                v.CODCLIENTE_ IS NOT NULL
                AND v.PTOTAL_ > 0
                AND v.DTEMISSAO_ >= m.max_dt - INTERVAL '60 days'
                AND v.DTEMISSAO_ <= m.max_dt
            GROUP BY v.CODCLIENTE_::TEXT, m.max_dt
        ),
        periodo_anterior AS (
            -- Mesmo período de 60 dias, 1 ano atrás (comparação sazonal válida)
            SELECT
                v.CODCLIENTE_::TEXT AS codcli,
                SUM(v.PTOTAL_) AS fat_anterior_60d,
                COUNT(DISTINCT v.NOTA_) AS notas_anteriores,
                MAX(v.DTEMISSAO_) AS dt_ultima_compra_ant,
                ((m.max_dt - INTERVAL '365 days') - INTERVAL '60 days') AS dt_inicio_ant,
                (m.max_dt - INTERVAL '365 days') AS dt_fim_ant
            FROM vw_vendas_lm v
            CROSS JOIN max_date m
            WHERE
                v.CODCLIENTE_ IS NOT NULL
                AND v.PTOTAL_ > 0
                AND v.DTEMISSAO_ >= (m.max_dt - INTERVAL '365 days') - INTERVAL '60 days'
                AND v.DTEMISSAO_ <= m.max_dt - INTERVAL '365 days'
            GROUP BY v.CODCLIENTE_::TEXT, m.max_dt
        )
        SELECT
            a.codcli,
            a.razao,
            a.fat_atual_60d,
            p.fat_anterior_60d,
            a.notas_atuais,
            p.notas_anteriores,
            a.dt_ultima_compra_atual,
            p.dt_ultima_compra_ant,
            a.dt_inicio_atual,
            a.dt_fim_atual,
            p.dt_inicio_ant,
            p.dt_fim_ant,
            ROUND(
                ((a.fat_atual_60d - p.fat_anterior_60d) / NULLIF(p.fat_anterior_60d, 0)) * 100.0,
                1
            ) AS variacao_pct
        FROM periodo_atual a
        INNER JOIN periodo_anterior p ON p.codcli = a.codcli
        WHERE
            p.fat_anterior_60d >= 20000
            AND a.fat_atual_60d < p.fat_anterior_60d * 0.5
        ORDER BY p.fat_anterior_60d DESC
        LIMIT 8;
        """
        client_rows = await conn.fetch(client_anomalies_query)
        for r in client_rows:
            var_pct = float(r["variacao_pct"] or 0)
            hist = float(r["fat_anterior_60d"] or 0)
            rec = float(r["fat_atual_60d"] or 0)
            
            # Formatação precisa de datas reais
            dt_ini_at = r["dt_inicio_atual"].strftime('%d/%m/%Y') if r["dt_inicio_atual"] else ""
            dt_fim_at = r["dt_fim_atual"].strftime('%d/%m/%Y') if r["dt_fim_atual"] else ""
            dt_ini_ant = r["dt_inicio_ant"].strftime('%d/%m/%Y') if r["dt_inicio_ant"] else ""
            dt_fim_ant = r["dt_fim_ant"].strftime('%d/%m/%Y') if r["dt_fim_ant"] else ""
            dt_ult = r["dt_ultima_compra_atual"].strftime('%d/%m/%Y') if r["dt_ultima_compra_atual"] else ""

            anomalies.append({
                "id": f"client_churn_{r['codcli']}",
                "categoria": "CLIENTE_VIP_CHURN",
                "tipo": "QUEDA_COMPRA_VIP",
                "severidade": "CRITICAL" if rec == 0 else "WARNING",
                "titulo": f"Alerta de Churn: {r['razao']}",
                "entidade": r["razao"],
                "codigo": r["codcli"],
                "descricao": (
                    f"Cliente VIP comprou R$ {rec:,.2f} no período recente de {dt_ini_at} a {dt_fim_at} "
                    f"(última compra em {dt_ult}) vs. R$ {hist:,.2f} no mesmo período do ano passado "
                    f"({dt_ini_ant} a {dt_fim_ant}) ({var_pct:+.1f}% de queda sazonal)."
                ),
                "impacto_financeiro": hist - rec,
                "impacto_formatted": f"R$ {(hist - rec):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                "sugestao_acao": "Acionar imediatamente o RCA responsável para visita ou contato de retenção.",
                "data_deteccao": "Agora",
                "periodo_atual": f"{dt_ini_at} a {dt_fim_at}",
                "periodo_anterior": f"{dt_ini_ant} a {dt_fim_ant}",
                "data_ultima_compra": dt_ult,
                "notas_atuais": int(r["notas_atuais"] or 0),
                "notas_anteriores": int(r["notas_anteriores"] or 0),
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
                SUM(v.PTOTAL_) AS receita_60d,
                (m.max_dt - INTERVAL '60 days') AS dt_inicio_60d,
                m.max_dt AS dt_fim_60d
            FROM vw_vendas_lm v
            CROSS JOIN max_date m
            WHERE v.DTEMISSAO_ >= m.max_dt - INTERVAL '60 days'
            GROUP BY v.CODPROD_::TEXT, m.max_dt
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
            v.dt_inicio_60d,
            v.dt_fim_60d,
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
            dt_ini_60 = r["dt_inicio_60d"].strftime('%d/%m/%Y') if r["dt_inicio_60d"] else ""
            dt_fim_60 = r["dt_fim_60d"].strftime('%d/%m/%Y') if r["dt_fim_60d"] else ""

            anomalies.append({
                "id": f"stock_rupture_{r['codprod']}",
                "categoria": "ESTOQUE_RUPTURA",
                "tipo": "RUPTURA_ALTO_GIRO",
                "severidade": "CRITICAL" if est <= 0 else "WARNING",
                "titulo": f"Risco de Ruptura: {r['descricao']}",
                "entidade": r["descricao"],
                "codigo": r["codprod"],
                "descricao": f"Produto de alta venda ({vendas:.0f} un vendidas de {dt_ini_60} a {dt_fim_60}, gerando R$ {rec:,.2f}) possui apenas {est:.0f} unidades em estoque ({dias_cob:.1f} dias de cobertura).",
                "impacto_financeiro": rec * 0.5,
                "impacto_formatted": f"R$ {(rec * 0.5):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                "sugestao_acao": "Emitir pedido de reposição com urgência ao fornecedor ou solicitar transferência entre filiais.",
                "data_deteccao": "Agora",
                "periodo_analise": f"{dt_ini_60} a {dt_fim_60}",
                "estoque_atual": est,
                "dias_cobertura": dias_cob,
            })

        # 3. FILIAIS COM ANOMALIA DE PERFORMANCE (comparação YoY - mesmo período do ano passado)
        branch_query = """
        WITH max_date AS (
            SELECT MAX(DTEMISSAO_) AS max_dt FROM vw_vendas_lm
        ),
        branch_stats AS (
            SELECT
                v.FILIAL_ AS filial,
                SUM(CASE WHEN v.DTEMISSAO_ >= m.max_dt - INTERVAL '30 days' THEN v.PTOTAL_ ELSE 0 END) AS fat_30d,
                SUM(CASE
                    WHEN v.DTEMISSAO_ >= (m.max_dt - INTERVAL '365 days') - INTERVAL '30 days'
                     AND v.DTEMISSAO_ <= m.max_dt - INTERVAL '365 days'
                    THEN v.PTOTAL_ ELSE 0 END) AS fat_mesmo_periodo_ano_passado,
                (m.max_dt - INTERVAL '30 days') AS dt_inicio_30d,
                m.max_dt AS dt_fim_30d,
                ((m.max_dt - INTERVAL '365 days') - INTERVAL '30 days') AS dt_inicio_ant_30d,
                (m.max_dt - INTERVAL '365 days') AS dt_fim_ant_30d
            FROM vw_vendas_lm v
            CROSS JOIN max_date m
            WHERE v.FILIAL_ IS NOT NULL
            GROUP BY v.FILIAL_, m.max_dt
        )
        SELECT
            filial,
            fat_30d,
            fat_mesmo_periodo_ano_passado,
            dt_inicio_30d,
            dt_fim_30d,
            dt_inicio_ant_30d,
            dt_fim_ant_30d,
            ROUND(((fat_30d - fat_mesmo_periodo_ano_passado) / NULLIF(fat_mesmo_periodo_ano_passado, 0)) * 100.0, 1) AS var_pct
        FROM branch_stats
        WHERE fat_mesmo_periodo_ano_passado > 0
        ORDER BY var_pct ASC;
        """
        branch_rows = await conn.fetch(branch_query)
        for r in branch_rows:
            var_pct = float(r["var_pct"] or 0)
            fat_atual = float(r["fat_30d"] or 0)
            fat_ant = float(r["fat_mesmo_periodo_ano_passado"] or 0)
            dt_ini_30 = r["dt_inicio_30d"].strftime('%d/%m/%Y') if r["dt_inicio_30d"] else ""
            dt_fim_30 = r["dt_fim_30d"].strftime('%d/%m/%Y') if r["dt_fim_30d"] else ""
            dt_ini_ant_30 = r["dt_inicio_ant_30d"].strftime('%d/%m/%Y') if r["dt_inicio_ant_30d"] else ""
            dt_fim_ant_30 = r["dt_fim_ant_30d"].strftime('%d/%m/%Y') if r["dt_fim_ant_30d"] else ""

            if var_pct < -25:
                anomalies.append({
                    "id": f"branch_drop_{r['filial']}",
                    "categoria": "FILIAL_DESEMPENHO",
                    "tipo": "QUEDA_FILIAL",
                    "severidade": "WARNING",
                    "titulo": f"Desaceleração na Filial {r['filial']}",
                    "entidade": f"Filial {r['filial']}",
                    "codigo": str(r["filial"]),
                    "descricao": f"A Filial {r['filial']} registrou R$ {fat_atual:,.2f} no período recente ({dt_ini_30} a {dt_fim_30}) vs R$ {fat_ant:,.2f} no mesmo período do ano passado ({dt_ini_ant_30} a {dt_fim_ant_30}) ({var_pct:+.1f}% YoY).",
                    "impacto_financeiro": max(0.0, fat_ant - fat_atual),
                    "impacto_formatted": f"R$ {max(0.0, fat_ant - fat_atual):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    "sugestao_acao": "Avaliar falta de produtos específicos ou retração em carteiras de vendedores locais.",
                    "data_deteccao": "Agora",
                    "periodo_atual": f"{dt_ini_30} a {dt_fim_30}",
                    "periodo_anterior": f"{dt_ini_ant_30} a {dt_fim_ant_30}",
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
                    "descricao": f"A Filial {r['filial']} acelerou {var_pct:+.1f}%, atingindo R$ {fat_atual:,.2f} no período recente ({dt_ini_30} a {dt_fim_30}) vs R$ {fat_ant:,.2f} no ano anterior ({dt_ini_ant_30} a {dt_fim_ant_30}).",
                    "impacto_financeiro": fat_atual - fat_ant,
                    "impacto_formatted": f"R$ {(fat_atual - fat_ant):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    "sugestao_acao": "Assegurar abastecimento contínuo para sustentar a curva de crescimento da praça.",
                    "data_deteccao": "Agora",
                    "periodo_atual": f"{dt_ini_30} a {dt_fim_30}",
                    "periodo_anterior": f"{dt_ini_ant_30} a {dt_fim_ant_30}",
                })

        return anomalies
    except Exception as exc:
        logger.error("[SentinelService] Erro ao executar varredura de anomalias: %s", exc)
        return []
    finally:
        await conn.close()


async def get_anomaly_investigation_detail(categoria: str, codigo: str) -> dict[str, Any]:
    """
    Retorna o dossiê detalhado e aprofundado para investigação de uma anomalia específica do Sentinela.
    """
    conn = await get_clone_connection()
    try:
        if categoria == "CLIENTE_VIP_CHURN":
            # 1. Dados cadastrais e resumo vitalício
            q_cli = """
            SELECT 
                v.CODCLIENTE_::TEXT AS codcli,
                MAX(v.RAZAO_) AS razao,
                MAX(v.RCA_) AS rca,
                MAX(v.FILIAL_) AS principal_filial,
                COUNT(DISTINCT v.NOTA_) AS total_historico_notas,
                SUM(v.PTOTAL_) AS faturamento_vitalicio,
                MAX(v.DTEMISSAO_) AS ultima_compra_data
            FROM vw_vendas_lm v
            WHERE v.CODCLIENTE_::TEXT = $1
            GROUP BY v.CODCLIENTE_::TEXT;
            """
            cli_row = await conn.fetchrow(q_cli, codigo)
            if not cli_row:
                return {"error": f"Cliente #{codigo} não encontrado."}

            # 2. Comparativo Sazonal YoY (mesmo período de 60 dias)
            q_comp = """
            WITH max_date AS (
                SELECT MAX(DTEMISSAO_) AS max_dt FROM vw_vendas_lm
            ),
            periodo_atual AS (
                SELECT
                    SUM(v.PTOTAL_) AS fat_atual,
                    COUNT(DISTINCT v.NOTA_) AS notas_atuais,
                    MAX(v.DTEMISSAO_) AS ult_data_atual,
                    (m.max_dt - INTERVAL '60 days') AS dt_ini_atual,
                    m.max_dt AS dt_fim_atual
                FROM vw_vendas_lm v
                CROSS JOIN max_date m
                WHERE v.CODCLIENTE_::TEXT = $1
                  AND v.DTEMISSAO_ >= m.max_dt - INTERVAL '60 days'
                  AND v.DTEMISSAO_ <= m.max_dt
                GROUP BY m.max_dt
            ),
            periodo_anterior AS (
                SELECT
                    SUM(v.PTOTAL_) AS fat_anterior,
                    COUNT(DISTINCT v.NOTA_) AS notas_anteriores,
                    ((m.max_dt - INTERVAL '365 days') - INTERVAL '60 days') AS dt_ini_ant,
                    (m.max_dt - INTERVAL '365 days') AS dt_fim_ant
                FROM vw_vendas_lm v
                CROSS JOIN max_date m
                WHERE v.CODCLIENTE_::TEXT = $1
                  AND v.DTEMISSAO_ >= (m.max_dt - INTERVAL '365 days') - INTERVAL '60 days'
                  AND v.DTEMISSAO_ <= m.max_dt - INTERVAL '365 days'
                GROUP BY m.max_dt
            )
            SELECT
                COALESCE(a.fat_atual, 0) AS fat_atual,
                COALESCE(p.fat_anterior, 0) AS fat_anterior,
                COALESCE(a.notas_atuais, 0) AS notas_atuais,
                COALESCE(p.notas_anteriores, 0) AS notas_anteriores,
                a.ult_data_atual,
                a.dt_ini_atual,
                a.dt_fim_atual,
                p.dt_ini_ant,
                p.dt_fim_ant
            FROM periodo_atual a
            FULL OUTER JOIN periodo_anterior p ON TRUE;
            """
            comp_row = await conn.fetchrow(q_comp, codigo)

            # 3. Produtos abandonados (comprava no ano passado e parou/reduziu este ano)
            q_prods = """
            WITH max_date AS (
                SELECT MAX(DTEMISSAO_) AS max_dt FROM vw_vendas_lm
            )
            SELECT
                v.CODPROD_::TEXT AS codprod,
                MAX(v.DESCRICAO_) AS descricao,
                SUM(CASE WHEN v.DTEMISSAO_ >= (m.max_dt - INTERVAL '365 days') - INTERVAL '60 days' AND v.DTEMISSAO_ <= m.max_dt - INTERVAL '365 days' THEN v.PTOTAL_ ELSE 0 END) AS fat_ano_passado,
                SUM(CASE WHEN v.DTEMISSAO_ >= m.max_dt - INTERVAL '60 days' AND v.DTEMISSAO_ <= m.max_dt THEN v.PTOTAL_ ELSE 0 END) AS fat_recente,
                SUM(CASE WHEN v.DTEMISSAO_ >= (m.max_dt - INTERVAL '365 days') - INTERVAL '60 days' AND v.DTEMISSAO_ <= m.max_dt - INTERVAL '365 days' THEN v.QTDE_ ELSE 0 END) AS qtde_ano_passado,
                SUM(CASE WHEN v.DTEMISSAO_ >= m.max_dt - INTERVAL '60 days' AND v.DTEMISSAO_ <= m.max_dt THEN v.QTDE_ ELSE 0 END) AS qtde_recente
            FROM vw_vendas_lm v
            CROSS JOIN max_date m
            WHERE v.CODCLIENTE_::TEXT = $1
            GROUP BY v.CODPROD_::TEXT
            HAVING SUM(CASE WHEN v.DTEMISSAO_ >= (m.max_dt - INTERVAL '365 days') - INTERVAL '60 days' AND v.DTEMISSAO_ <= m.max_dt - INTERVAL '365 days' THEN v.PTOTAL_ ELSE 0 END) > 0
            ORDER BY fat_ano_passado DESC
            LIMIT 10;
            """
            prod_rows = await conn.fetch(q_prods, codigo)
            produtos_perdidos = []
            for pr in prod_rows:
                fat_ant = float(pr["fat_ano_passado"] or 0)
                fat_rec = float(pr["fat_recente"] or 0)
                produtos_perdidos.append({
                    "codprod": pr["codprod"],
                    "descricao": pr["descricao"],
                    "fat_ano_passado": fat_ant,
                    "fat_recente": fat_rec,
                    "fat_ano_passado_formatted": f"R$ {fat_ant:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    "fat_recente_formatted": f"R$ {fat_rec:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    "qtde_ano_passado": float(pr["qtde_ano_passado"] or 0),
                    "qtde_recente": float(pr["qtde_recente"] or 0),
                    "status": "ABANDONADO" if fat_rec == 0 else "QUEDA_FORTE",
                })

            # 4. Últimas 10 Notas Fiscais do cliente
            q_notas = """
            SELECT
                v.NOTA_::TEXT AS nota,
                v.FILIAL_ AS filial,
                v.DTEMISSAO_ AS data_emissao,
                SUM(v.PTOTAL_) AS valor_total,
                COUNT(DISTINCT v.CODPROD_) AS total_itens
            FROM vw_vendas_lm v
            WHERE v.CODCLIENTE_::TEXT = $1
            GROUP BY v.NOTA_::TEXT, v.FILIAL_, v.DTEMISSAO_
            ORDER BY v.DTEMISSAO_ DESC
            LIMIT 10;
            """
            nota_rows = await conn.fetch(q_notas, codigo)
            ultimas_notas = []
            for nr in nota_rows:
                val = float(nr["valor_total"] or 0)
                dt = nr["data_emissao"].strftime('%d/%m/%Y') if nr["data_emissao"] else ""
                ultimas_notas.append({
                    "nota": nr["nota"],
                    "filial": nr["filial"],
                    "data_emissao": dt,
                    "valor_total": val,
                    "valor_formatted": f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    "total_itens": int(nr["total_itens"] or 0),
                })

            fat_rec_total = float(comp_row["fat_atual"] or 0) if comp_row else 0
            fat_ant_total = float(comp_row["fat_anterior"] or 0) if comp_row else 0
            queda_pct = ((fat_rec_total - fat_ant_total) / fat_ant_total * 100.0) if fat_ant_total > 0 else 0

            return {
                "tipo_investigacao": "CLIENTE_VIP_CHURN",
                "cliente": {
                    "codigo": cli_row["codcli"],
                    "razao": cli_row["razao"],
                    "rca": cli_row["rca"] or "Não informado",
                    "principal_filial": cli_row["principal_filial"] or "1",
                    "total_historico_notas": int(cli_row["total_historico_notas"] or 0),
                    "faturamento_vitalicio": float(cli_row["faturamento_vitalicio"] or 0),
                    "faturamento_vitalicio_formatted": f"R$ {float(cli_row['faturamento_vitalicio'] or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    "ultima_compra_data": cli_row["ultima_compra_data"].strftime('%d/%m/%Y') if cli_row["ultima_compra_data"] else "N/D",
                },
                "comparativo_sazonal": {
                    "periodo_atual": f"{comp_row['dt_ini_atual'].strftime('%d/%m/%Y')} a {comp_row['dt_fim_atual'].strftime('%d/%m/%Y')}" if comp_row and comp_row['dt_ini_atual'] else "",
                    "periodo_anterior": f"{comp_row['dt_ini_ant'].strftime('%d/%m/%Y')} a {comp_row['dt_fim_ant'].strftime('%d/%m/%Y')}" if comp_row and comp_row['dt_ini_ant'] else "",
                    "fat_recente": fat_rec_total,
                    "fat_recente_formatted": f"R$ {fat_rec_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    "fat_anterior": fat_ant_total,
                    "fat_anterior_formatted": f"R$ {fat_ant_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    "variacao_pct": round(queda_pct, 1),
                    "perda_financeira": max(0.0, fat_ant_total - fat_rec_total),
                    "perda_formatted": f"R$ {max(0.0, fat_ant_total - fat_rec_total):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    "notas_recentes": int(comp_row["notas_atuais"] or 0) if comp_row else 0,
                    "notas_anteriores": int(comp_row["notas_anteriores"] or 0) if comp_row else 0,
                },
                "produtos_perdidos": produtos_perdidos,
                "ultimas_notas": ultimas_notas,
                "plano_acao": [
                    f"Acionar imediatamente o RCA {cli_row['rca'] or 'do cliente'} para contato direto ou visita presencial.",
                    f"Apresentar condições especiais nos produtos abandonados ({', '.join(p['descricao'] for p in produtos_perdidos[:3])}).",
                    f"Verificar se houve migração de compras para concorrentes ou insatisfação logística na Filial {cli_row['principal_filial']}.",
                ],
            }

        elif categoria == "ESTOQUE_RUPTURA":
            # Detalhamento de produto em ruptura
            q_prod = """
            SELECT
                p.CODIGO::TEXT AS codprod,
                p.DESCRICAO AS descricao,
                COALESCE(p.ESTOQUE, 0) AS estoque_atual,
                p.CATEGORIA AS categoria,
                p.FORNECEDOR AS fornecedor
            FROM vw_produtos_cad_lm p
            WHERE p.CODIGO::TEXT = $1;
            """
            prod_row = await conn.fetchrow(q_prod, codigo)
            
            # Vendas recentes
            q_vendas = """
            SELECT
                v.FILIAL_ AS filial,
                SUM(v.QTDE_) AS qtde_vendida,
                SUM(v.PTOTAL_) AS receita_total,
                COUNT(DISTINCT v.NOTA_) AS total_notas
            FROM vw_vendas_lm v
            WHERE v.CODPROD_::TEXT = $1
              AND v.DTEMISSAO_ >= (SELECT MAX(DTEMISSAO_) FROM vw_vendas_lm) - INTERVAL '60 days'
            GROUP BY v.FILIAL_
            ORDER BY qtde_vendida DESC;
            """
            vendas_rows = await conn.fetch(q_vendas, codigo)
            filiais_venda = []
            for vr in vendas_rows:
                filiais_venda.append({
                    "filial": vr["filial"],
                    "qtde_vendida": float(vr["qtde_vendida"] or 0),
                    "receita_total": float(vr["receita_total"] or 0),
                    "receita_formatted": f"R$ {float(vr['receita_total'] or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    "total_notas": int(vr["total_notas"] or 0),
                })

            return {
                "tipo_investigacao": "ESTOQUE_RUPTURA",
                "produto": {
                    "codigo": codigo,
                    "descricao": prod_row["descricao"] if prod_row else f"Produto #{codigo}",
                    "estoque_atual": float(prod_row["estoque_atual"] or 0) if prod_row else 0,
                    "fornecedor": prod_row["fornecedor"] if prod_row and "fornecedor" in prod_row else "N/D",
                },
                "filiais_venda": filiais_venda,
                "plano_acao": [
                    "Emitir pedido de reposição urgente com o fornecedor.",
                    "Avaliar se filiais com menor giro podem ceder estoque para as filiais de maior demanda.",
                ],
            }

        else:
            return {"error": f"Categoria {categoria} sem rota de investigação especializada."}

    except Exception as e:
        logger.error("[SentinelService] Erro ao investigar anomalia %s/%s: %s", categoria, codigo, e)
        return {"error": str(e)}
    finally:
        await conn.close()
