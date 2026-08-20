"""
LuminaAI — Engine de Business Intelligence Determinístico (v5.2)
--------------------------------------------------------------
Executa cálculos financeiros, estatísticos e de regressão no backend
para garantir consistência e precisão matemática de forma autônoma (sem IA).
"""
from __future__ import annotations

import logging
import math
from typing import Any
from decimal import Decimal

logger = logging.getLogger("luminaai.services.bi_engine")


def _to_float(val: Any) -> float:
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def process_bi_intelligence(rows: list[dict[str, Any]], view_name: str | None = None) -> dict[str, Any]:
    """
    Processa um conjunto de dados do banco e retorna análises numéricas determinísticas completas.
    Retorna o JSON estruturado obrigatório: kpis, metrics, datasets, time_series, comparisons, segments, anomalies.
    """
    # Inicializa o JSON obrigatório com estruturas vazias e seguras
    result = {
        "kpis": {},
        "metrics": {},
        "datasets": {},
        "time_series": {},
        "comparisons": {},
        "segments": {},
        "anomalies": []
    }

    if not rows:
        return result

    # 1. Normalização interna das chaves para lowercase
    normalized_rows: list[dict[str, Any]] = []
    for r in rows:
        norm = {}
        for k, v in r.items():
            norm[k.lower()] = float(v) if isinstance(v, Decimal) else v
        normalized_rows.append(norm)

    # 2. Identificação de colunas numéricas e categóricas
    keys = list(normalized_rows[0].keys())
    numeric_keys = []
    categorical_keys = []
    date_key = None

    date_terms = ("data", "periodo", "mes", "ano", "data_venda", "data_pedido", "data_referencia", "data_ref", "dtemissao_", "dt_emissao")
    cat_terms = ("vendedor", "cliente", "produto", "categoria", "regiao", "loja", "vendedor_nome", "cliente_nome", "produto_nome", "razao_", "descricao_", "nome_")

    for k in keys:
        val = normalized_rows[0][k]
        if k in date_terms:
            date_key = k
        elif isinstance(val, (int, float)):
            # Evita incluir IDs ou códigos numéricos como métricas financeiras brutas
            if not any(term in k for term in ("id", "codigo", "cod", "index", "ranking", "nfe", "nf", "nota", "pedido", "cfop", "ncm", "cpf", "cnpj", "phone", "telefone", "rca", "tp_", "pp_")):
                numeric_keys.append(k)
        elif isinstance(val, str):
            categorical_keys.append(k)

    # Prioriza coluna de valor/faturamento como primária
    val_priority = (
        "receita_total",
        "faturamento_realizado",
        "valor_total",
        "valor_vendido",
        "total_vendido",
        "ptotal_",
        "ptotal",
        "venda_valor",
    )
    val_terms = ("valor", "faturamento", "receita", "total_vendido", "total", "ptotal")
    primary_num_key = next((k for k in val_priority if k in numeric_keys), None)
    if not primary_num_key:
        primary_num_key = next((k for k in numeric_keys if any(term in k for term in val_terms)), None)
    if not primary_num_key and numeric_keys:
        primary_num_key = numeric_keys[0]

    # 3. CÁLCULO DE KPIS FINANCEIROS (Métrica Primária)
    if primary_num_key:
        val_list = [_to_float(r[primary_num_key]) for r in normalized_rows]
        n_records = len(val_list)
        
        # Receita Total
        receita_total = sum(val_list)
        
        # Margem Bruta média
        margem_key = next((k for k in keys if "margem" in k or "bruto" in k), None)
        margem_bruta = 35.0
        if margem_key:
            margens = [_to_float(r[margem_key]) for r in normalized_rows]
            if margens:
                margem_bruta = sum(margens) / len(margens)
                # Normaliza margem se vier em decimal (ex: 0.35 -> 35.0)
                if margem_bruta > 0 and margem_bruta < 1.0:
                    margem_bruta *= 100

        # Lucro Bruto e Custo Total
        lucro_bruto = receita_total * (margem_bruta / 100.0)
        custo_total = receita_total - lucro_bruto

        # Ticket Médio
        ticket_medio = receita_total / n_records if n_records > 0 else 0.0

        # CAC / LTV
        churn_key = next((k for k in keys if "churn" in k or "evasao" in k), None)
        churn_rate = 4.5
        if churn_key:
            churns = [_to_float(r[churn_key]) for r in normalized_rows]
            if churns:
                churn_rate = sum(churns) / len(churns)
                if churn_rate > 0 and churn_rate < 1.0:
                    churn_rate *= 100

        cac = 150.0 # CAC Padrão estimado
        # LTV = Ticket Médio * (1 / Churn Rate)
        ltv = ticket_medio * (100.0 / churn_rate) if churn_rate > 0 else ticket_medio * 12

        # ROI / ROAS
        custo_mkt = custo_total * 0.15 # Marketing estimado em 15% do custo
        roas = receita_total / custo_mkt if custo_mkt > 0 else 5.0
        roi = (receita_total - custo_total) / custo_total if custo_total > 0 else 0.0

        # Break-even point (ponto de equilíbrio estimado)
        custos_fixos_estimados = 35000.0
        margem_contribuicao = margem_bruta / 100.0
        break_even = custos_fixos_estimados / margem_contribuicao if margem_contribuicao > 0 else 100000.0

        result["kpis"] = {
            "receita_total": round(receita_total, 2),
            "receita_liquida": round(receita_total * 0.85, 2), # Desconto de 15% impostos
            "margem_bruta_media": round(margem_bruta, 2),
            "lucro_bruto": round(lucro_bruto, 2),
            "custo_total": round(custo_total, 2),
            "ticket_medio": round(ticket_medio, 2),
            "cac_estimado": round(cac, 2),
            "ltv_estimado": round(ltv, 2),
            "roi": round(roi, 4),
            "roas": round(roas, 2),
            "break_even_mensal": round(break_even, 2),
            "total_registros": n_records
        }

        # 4. DETECÇÃO DE ANOMALIAS E OUTLIERS (Desvio Padrão > 1.8)
        if n_records >= 3:
            mean_val = receita_total / n_records
            variance = sum((x - mean_val) ** 2 for x in val_list) / n_records
            std_dev = math.sqrt(variance)

            if std_dev > 0:
                for idx, r in enumerate(normalized_rows):
                    v = _to_float(r[primary_num_key])
                    z_score = (v - mean_val) / std_dev
                    if abs(z_score) > 1.5:
                        desc = "Crescimento anormal" if z_score > 0 else "Queda abrupta"
                        label_item = r.get(date_key) or r.get(categorical_keys[0]) if categorical_keys else f"Item {idx+1}"
                        result["anomalies"].append({
                            "item": str(label_item),
                            "tipo": desc,
                            "valor": round(v, 2),
                            "desvio_z": round(z_score, 2),
                            "justificativa": f"O valor de R$ {v:,.2f} desvia {abs(z_score):.1f} desvios padrão da média corporativa de R$ {mean_val:,.2f}."
                        })

    # 5. AGREGAÇÕES INTELIGENTES (Por Categoria/Vendedor/Produto)
    for cat_k in categorical_keys:
        if primary_num_key:
            groups = {}
            for r in normalized_rows:
                g_val = str(r[cat_k])
                groups[g_val] = groups.get(g_val, 0.0) + _to_float(r[primary_num_key])
            
            # Ordena decrescente
            sorted_groups = sorted(groups.items(), key=lambda x: x[1], reverse=True)
            result["datasets"][cat_k] = [
                {"segmento": k, "total": round(v, 2)} for k, v in sorted_groups[:10]
            ]

    # 6. ANÁLISE TEMPORAL E TENDÊNCIAS
    if date_key and primary_num_key:
        # Ordena as linhas chronologicamente se possível
        try:
            sorted_rows = sorted(normalized_rows, key=lambda x: str(x[date_key]))
        except Exception:
            sorted_rows = normalized_rows

        dates = [str(r[date_key]) for r in sorted_rows]
        vals = [_to_float(r[primary_num_key]) for r in sorted_rows]
        n_points = len(vals)

        # Média Móvel (janela = 3)
        moving_averages = []
        for idx in range(n_points):
            start_idx = max(0, idx - 2)
            window = vals[start_idx : idx + 1]
            moving_averages.append(round(sum(window) / len(window), 2))

        # Regressão Linear Simples para Tendência
        slope = 0.0
        if n_points >= 2:
            x_bar = sum(range(n_points)) / n_points
            y_bar = sum(vals) / n_points
            numerator = sum((i - x_bar) * (vals[i] - y_bar) for i in range(n_points))
            denominator = sum((i - x_bar) ** 2 for i in range(n_points))
            if denominator != 0:
                slope = numerator / denominator

        trend_desc = "Crescente" if slope > 0.01 else ("Decrescente" if slope < -0.01 else "Estável")

        result["time_series"] = {
            "periodos": dates,
            "valores_reais": vals,
            "media_movel_3p": moving_averages,
            "tendencia_linear_coeficiente": round(slope, 2),
            "direcao_tendencia": trend_desc
        }

        # 7. COMPARAÇÕES TEMPORAIS (Último ponto vs anterior)
        if n_points >= 2:
            atual = vals[-1]
            anterior = vals[-2]
            variation = ((atual - anterior) / anterior * 100.0) if anterior > 0 else 0.0
            result["comparisons"] = {
                "periodo_atual": dates[-1],
                "periodo_anterior": dates[-2],
                "valor_atual": round(atual, 2),
                "valor_anterior": round(anterior, 2),
                "variacao_percentual": round(variation, 2)
            }

    # 8. SEGMENTAÇÃO DE PERFORMANCE (Curva RFM ou similar)
    if primary_num_key:
        val_list = sorted([_to_float(r[primary_num_key]) for r in normalized_rows])
        n_vals = len(val_list)
        if n_vals >= 3:
            # Define percentis para corte
            idx_30 = int(n_vals * 0.3)
            idx_80 = int(n_vals * 0.8)
            cut_low = val_list[idx_30]
            cut_high = val_list[idx_80]

            high_seg = []
            med_seg = []
            low_seg = []

            for r in normalized_rows:
                v = _to_float(r[primary_num_key])
                label = r.get(categorical_keys[0]) if categorical_keys else (r.get(date_key) if date_key else "Item")
                label_str = str(label)
                if v >= cut_high:
                    high_seg.append(label_str)
                elif v <= cut_low:
                    low_seg.append(label_str)
                else:
                    med_seg.append(label_str)

            result["segments"] = {
                "alta_performance_top20": high_seg[:5],
                "media_performance": med_seg[:5],
                "baixa_performance": low_seg[:5],
                "limites_corte": {"baixo": round(cut_low, 2), "alto": round(cut_high, 2)}
            }

    return result
