"""
LuminaAI — Pipeline de Tradução Dinâmica e Otimização de Dados
------------------------------------------------------------
Este módulo é responsável por:
1. Normalizar as chaves dos dicionários vindas do banco de dados (que geralmente
   são retornadas em CAIXA ALTA pelo Oracle) para minúsculo, de modo a bater
   com o formato snake_case esperado e tipado pelo frontend do LuminaAI.
2. Tratar tipos de dados de banco não serializáveis em JSON nativo, como
   Decimal (convertendo para float/int) e objetos de data e hora (convertendo
   para string em formato ISO 8601).
3. Estruturar os datasets e metadados de acordo com o ChartType do catálogo,
   garantindo o empacotamento exato de gráficos (BAR, LINE, AREA, PIE),
   tabelas completas (TABLE) ou cartões de KPIs estratégicos (KPI).
"""

from __future__ import annotations

import datetime
import logging
from decimal import Decimal
from typing import Any

from models.view_catalog import ChartType

# Logger específico do pipeline de dados
logger = logging.getLogger("luminaai.services.transformer")


def is_numeric_value(val: Any) -> bool:
    """Verifica de forma resiliente se um valor é numérico (int, float, Decimal ou string conversível)."""
    if isinstance(val, (int, float, Decimal)):
        return True
    if isinstance(val, str):
        try:
            float(val)
            return True
        except ValueError:
            return False
    return False


def to_float(val: Any) -> float:
    """Converte com segurança qualquer valor numérico ou string numérica para float."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


_VALUE_KEY_PRIORITY = (
    "ticket_medio",
    "desconto_total",
    "desconto_medio",
    "receita_total",
    "faturamento_realizado",
    "valor_total",
    "valor_vendido",
    "total_vendido",
    "ptotal_",
    "ptotal",
    "venda_valor",
    "unidades_vendidas",
    "quantidade_vendida",
    "qtde_",
    "qtde",
)

_LABEL_KEY_PRIORITY = (
    "vendedor_nome",
    "nome_ved",
    "nome_vendedor",
    "produto_nome",
    "nome_produto",
    "cliente_nome",
    "nome_cliente",
    "nome",
    "nome_",
    "descricao_",
    "razao_",
    "tpcli",
    "status_pagamento",
    "filial",
    "filial_",
    "data_ref",
    "dtemissao_",
    "periodo",
    "mes",
    "ano",
)

_NUMERIC_EXCLUDED_TERMS = (
    "id",
    "codigo",
    "cod",
    "filial",
    "filial_",
    "cod_filial",
    "ranking",
    "index",
    "nfe",
    "nf",
    "nota",
    "pedido",
    "cfop",
    "ncm",
    "cpf",
    "cnpj",
    "telefone",
    "phone",
    "rca",
    "tp_",
    "pp_",
)

_CURRENCY_VALUE_KEYS = {
    "faturamento_comercial",
    "saida_rb",
    "devolucao",
    "saida_rb_devolucao",
    "venda_bonificada",
    "transferencias",
    "outras_vendas",
    "remessa_uso_consumo",
    "outros_movimentos",
    "total_bruto",
    "total_movimentos_view",
    "valor_filial",
    "faturamento_comercial_total",
    "total_bruto_total",
    "total_movimentos_view_total",
    "ticket_medio_comercial",
    "ticket_medio_bruto",
    "desconto_medio_comercial",
    "desconto_medio_total",
    "desconto_total_periodo",
}

_DISPLAY_LABELS = {
    "indicador": "Indicador",
    "posicao": "Posição",
    "vendedor": "Vendedor",
    "cliente": "Cliente",
    "filial": "Filial",
    "tipo_linha": "Tipo de linha",
    "pedidos": "Pedidos",
    "valor": "Valor",
    "valor_formatado": "Valor formatado",
    "observacao": "Observação",
    "faturamento_total": "Faturamento total",
    "ticket_medio_comercial": "Ticket medio comercial",
    "ticket_medio_bruto": "Ticket medio bruto",
    "ticket_medio": "Ticket médio",
    "desconto_total": "Desconto total",
    "desconto_medio_comercial": "Desconto medio comercial",
    "desconto_medio_total": "Desconto medio total",
    "desconto_medio": "Desconto médio",
    "desconto_formatado": "Desconto formatado",
    "desconto_comercial": "Desconto comercial",
    "desconto_fonte_tipo": "Fonte do desconto",
    "desconto_fonte_coluna": "Coluna de desconto",
    "desconto_fonte_confianca": "Confianca do desconto",
    "desconto_fonte_observacao": "Observacao do desconto",
    "valor_total": "Valor total",
    "valor_filial": "Valor da filial",
    "valor_filial_formatado": "Valor da filial formatado",
    "faturamento_comercial": "Faturamento comercial",
    "faturamento_comercial_total": "Faturamento comercial total",
    "saida_rb": "Saida RB",
    "saida_rb_total": "Saida RB total",
    "devolucao": "Devolucao",
    "devolucao_total": "Devolucao total",
    "saida_rb_devolucao": "Saida RB + Devolucao",
    "venda_bonificada": "Venda bonificada",
    "transferencias": "Transferencias",
    "outras_vendas": "Outras vendas",
    "remessa_uso_consumo": "Remessa / uso e consumo",
    "outros_movimentos": "Outros movimentos",
    "total_bruto": "Total bruto sem transferencias",
    "total_bruto_total": "Total bruto total sem transferencias",
    "total_movimentos_view": "Total geral de movimentos",
    "total_movimentos_view_total": "Total geral de movimentos total",
    "pedidos_comerciais": "Pedidos comerciais",
    "pedidos_comerciais_total": "Pedidos comerciais total",
    "pedidos_saida_rb": "Pedidos saida RB",
    "pedidos_saida_rb_total": "Pedidos saida RB total",
    "pedidos_devolucao": "Pedidos devolucao",
    "pedidos_devolucao_total": "Pedidos devolucao total",
    "pedidos_saida_rb_devolucao": "Pedidos saida RB + devolucao",
    "pedidos_bonificados": "Pedidos bonificados",
    "pedidos_transferencias": "Pedidos transferencias",
    "pedidos_outras_vendas": "Pedidos outras vendas",
    "pedidos_remessa_uso_consumo": "Pedidos remessa / uso",
    "pedidos_outros": "Pedidos outros",
    "pedidos_total": "Pedidos total",
    "pedidos_total_periodo": "Pedidos total periodo",
    "pedidos_movimentos_view": "Pedidos movimentos",
    "pedidos_movimentos_view_periodo": "Pedidos movimentos periodo",
    "desconto_total_periodo": "Desconto total periodo",
    "tipo_valor": "Tipo valor",
    "quantidade": "Quantidade",
    "preco_unitario": "Preço unitário",
    "periodo": "Período",
}


def _is_currency_key(key: str) -> bool:
    key_lower = str(key).lower()
    if (
        key_lower.startswith("pedidos")
        or "_pedidos_" in key_lower
        or key_lower.endswith("_pedidos")
        or "quantidade" in key_lower
        or key_lower.startswith("qtde")
        or "_qtde" in key_lower
    ):
        return False
    if key_lower in _CURRENCY_VALUE_KEYS:
        return True
    if any(key_lower.endswith(f"_{known_key}") for known_key in _CURRENCY_VALUE_KEYS):
        return True
    return any(
        term in key_lower
        for term in ("valor", "faturamento", "receita", "ticket", "desconto", "preco", "custo", "comissao", "ptotal", "lucro")
    )


def _humanize_key(key: str) -> str:
    normalized = str(key).strip().lower()
    if normalized in _DISPLAY_LABELS:
        return _DISPLAY_LABELS[normalized]
    return normalized.replace("_", " ").title()


def _is_metric_key(key: str, value: Any) -> bool:
    if not is_numeric_value(value):
        return False
    if key in _VALUE_KEY_PRIORITY:
        return True
    return not any(term in key for term in _NUMERIC_EXCLUDED_TERMS)


def _preferred_numeric_keys(keys: list[str], row: dict[str, Any], *, max_items: int | None = None) -> list[str]:
    preferred = [key for key in _VALUE_KEY_PRIORITY if key in keys and _is_metric_key(key, row.get(key))]
    remaining = [key for key in keys if key not in preferred and _is_metric_key(key, row.get(key))]
    result = list(dict.fromkeys(preferred + remaining))
    return result[:max_items] if max_items else result


def _preferred_label_key(keys: list[str], row: dict[str, Any]) -> str:
    for key in _LABEL_KEY_PRIORITY:
        if key in keys and not is_numeric_value(row.get(key)):
            return key
    for key in keys:
        if isinstance(row.get(key), str):
            return key
    return keys[0]


def _ordered_union_keys(rows: list[dict[str, Any]]) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key in seen:
                continue
            seen.add(key)
            keys.append(key)
    return keys


def _first_non_empty_value(rows: list[dict[str, Any]], key: str) -> Any:
    for row in rows:
        value = row.get(key)
        if value is not None:
            return value
    return None


def clean_row_data(row: dict[str, Any]) -> dict[str, Any]:
    """
    Limpa e converte os tipos de dados de uma linha de registro do Oracle para JSON puro.

    Executa duas normalizações críticas:
    - Transforma as chaves para caixa baixa (lower_case), permitindo que campos
      como 'VALOR_TOTAL' fiquem disponíveis como 'valor_total'.
      Isso alinha a saída com a tipagem estrita declarada no frontend.
    - Converte instâncias de Decimal (do banco de dados) para primitivos nativos
      Python (float ou int) e instâncias de Date/Datetime para string ISO 8601.

    Parâmetros:
    -----------
    row : dict[str, Any]
        Dicionário representando um registro cru retornado pelo banco de dados Oracle.

    Retorno:
    --------
    dict[str, Any]
        Registro normalizado com chaves em minúsculo e valores compatíveis com JSON.
    """
    cleaned = {}
    for key, val in row.items():
        # Converte a chave da coluna para minúsculo
        new_key = key.lower()

        # Tratamento de decimais do banco Oracle
        if isinstance(val, Decimal):
            # Se a divisão por 1 não tiver resto, é um inteiro, senão um float de dupla precisão
            if val % 1 == 0:
                cleaned[new_key] = int(val)
            else:
                cleaned[new_key] = float(val)
        # Tratamento de datas do banco
        elif isinstance(val, (datetime.datetime, datetime.date)):
            # Formata a data no padrão ISO 8601 (YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS)
            cleaned[new_key] = val.isoformat()
        else:
            # Caso contrário, mantém o tipo nativo (string, booleano, nulo, etc.)
            cleaned[new_key] = val

    return cleaned


def transform_data(rows: list[dict[str, Any]], chart_type: ChartType) -> dict[str, Any]:
    """
    Encaminha a lista de registros normalizados para o tradutor adequado ao ChartType.

    Parâmetros:
    -----------
    rows : list[dict[str, Any]]
        Lista de dicionários contendo os registros retornados pelo banco.
    chart_type : ChartType
        O tipo de gráfico configurado no catálogo para esta view (ex: BAR, KPI, TABLE).

    Retorno:
    --------
    dict[str, Any]
        Estrutura de dados traduzida correspondente ao tipo de visualização desejada.
    """
    # Se a query não retornou registros, inicializa estruturas vazias seguras
    if not rows:
        logger.warning("Lista de registros vazia enviada para transformação.")
        return {
            "labels": [],
            "datasets": [],
            "resumo": {},
            "columns": [],
            "rows": [],
            "kpis": [],
        }

    # Executa a limpeza básica de caixa e tipagem para cada linha do resultado
    cleaned_rows = [clean_row_data(r) for r in rows]

    # Distribui para o transformador de acordo com o contrato esperado pelo frontend
    if chart_type in (ChartType.BAR, ChartType.LINE, ChartType.AREA):
        return transform_chart_data(cleaned_rows, chart_type)
    elif chart_type == ChartType.PIE:
        return transform_pie_data(cleaned_rows)
    elif chart_type == ChartType.TABLE:
        return transform_table_data(cleaned_rows)
    elif chart_type == ChartType.KPI:
        return transform_kpi_data(cleaned_rows)
    elif chart_type == ChartType.SCATTER:
        return transform_scatter_data(cleaned_rows)

    # Fallback genérico retornando as linhas limpas
    return {"rows": cleaned_rows}


def transform_chart_data(rows: list[dict[str, Any]], chart_type: ChartType) -> dict[str, Any]:
    """
    Traduz dados para exibição em gráficos cartesianos de linha, barra ou área.

    Determina automaticamente o eixo X (labels) localizando colunas de calendário
    ou texto, e constrói as séries numéricas de dados (datasets) no eixo Y.

    Parâmetros:
    -----------
    rows : list[dict[str, Any]]
        Registros limpos.
    chart_type : ChartType
        O tipo do gráfico para aplicar regras específicas de preenchimento/interpolação.

    Retorno:
    --------
    dict[str, Any]
        Objeto contendo labels (list[str]), datasets (list[dict]) e resumo estatístico.
    """
    keys = list(rows[0].keys())

    # 1. Determinação inteligente da coluna do eixo horizontal (Labels)
    label_col = None
    time_keys = ("mes", "ano", "data", "periodo", "data_venda", "data_pedido", "data_referencia")
    
    # Prioriza chaves temporais para o eixo X
    for k in keys:
        if k in time_keys:
            label_col = k
            break
            
    # Se não houver temporal, busca o primeiro campo tipo string
    if not label_col:
        for k in keys:
            if isinstance(rows[0][k], str):
                label_col = k
                break
                
    # Fallback se não encontrar nada: primeira coluna
    if not label_col:
        label_col = keys[0]

    label_col = _preferred_label_key(keys, rows[0])
    labels = [str(r[label_col]) for r in rows]

    # 2. Identificação das dimensões numéricas (datasets)
    numeric_cols = []
    for k in keys:
        if k != label_col and is_numeric_value(rows[0][k]):
            numeric_cols.append(k)

    numeric_cols = [k for k in _preferred_numeric_keys(keys, rows[0], max_items=4) if k != label_col] or numeric_cols
    if not numeric_cols:
        # Se não achou colunas numéricas nativas, faz fallback pegando até 2 colunas não-label
        numeric_cols = [k for k in keys if k != label_col][:2]

    # Cores sofisticadas para manter a estética premium
    palette = [
        {"border": "#6C63FF", "bg": "rgba(108, 99, 255, 0.8)", "bg_light": "rgba(108, 99, 255, 0.15)"},
        {"border": "#00D2D3", "bg": "rgba(0, 210, 211, 0.8)", "bg_light": "rgba(0, 210, 211, 0.15)"},
        {"border": "#FF6B6B", "bg": "rgba(255, 107, 107, 0.8)", "bg_light": "rgba(255, 107, 107, 0.15)"},
        {"border": "#FECA57", "bg": "rgba(254, 202, 87, 0.8)", "bg_light": "rgba(254, 202, 87, 0.15)"},
    ]

    datasets = []
    seen_data_vectors = []
    for i, col in enumerate(numeric_cols):
        data_values = [r[col] for r in rows]

        # Deduplicação de séries idênticas: evita duplicar legendas/métricas quando os valores numéricos são idênticos
        vector_tuple = tuple(data_values)
        if vector_tuple in seen_data_vectors:
            logger.info("[Transformer] Ignorando série duplicada '%s' (dados idênticos a métrica anterior).", col)
            continue
        seen_data_vectors.append(vector_tuple)

        color = palette[len(datasets) % len(palette)]
        dataset = {
            "label": _humanize_key(col),
            "data": data_values,
            "borderColor": color["border"],
            "backgroundColor": color["bg_light"] if chart_type in (ChartType.LINE, ChartType.AREA) else color["bg"],
            "borderWidth": 2,
        }

        # Aplica flag de fill e suavização no caso de gráfico de linha/área
        if chart_type == ChartType.AREA:
            dataset["fill"] = True

        if chart_type in (ChartType.LINE, ChartType.AREA):
            dataset["tension"] = 0.4
            dataset["pointRadius"] = 4
            dataset["pointHoverRadius"] = 6

        datasets.append(dataset)

    # 3. Cálculo de KPIs agregados da série temporal (resumo)
    resumo = {}
    if numeric_cols:
        primary_col = numeric_cols[0]
        primary_values = [to_float(r[primary_col]) for r in rows if is_numeric_value(r[primary_col])]
        
        if primary_values:
            total = sum(primary_values)
            avg = total / len(primary_values)
            max_val = max(primary_values)
            min_val = min(primary_values)
            idx_max = primary_values.index(max_val)
            idx_min = primary_values.index(min_val)

            # Calcula percentual de variação do primeiro ao último ponto do gráfico
            variation = 0.0
            if primary_values[0] != 0:
                variation = ((primary_values[-1] - primary_values[0]) / primary_values[0]) * 100

            resumo = {
                "total_periodo": round(total, 2),
                "media_mensal": round(avg, 2),
                "melhor_mes": labels[idx_max],
                "pior_mes": labels[idx_min],
                "variacao_percentual": round(variation, 2),
            }

    return {
        "labels": labels,
        "datasets": datasets,
        "resumo": resumo,
    }


def transform_pie_data(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Traduz registros para gráficos circulares de Pizza ou Rosca (Pie/Donut).
    """
    if not rows:
        return {"labels": [], "values": [], "valores_brutos": [], "colors": [], "resumo": {}}

    keys = list(rows[0].keys())

    # Separa chave categórica de chave de valor
    str_col = None
    num_col = None

    for k in keys:
        if isinstance(rows[0][k], str):
            str_col = k
            break
    str_col = _preferred_label_key(keys, rows[0]) if keys else str_col
    if not str_col:
        str_col = keys[0]

    for k in keys:
        if k != str_col and is_numeric_value(rows[0][k]):
            num_col = k
            break
    preferred_num_cols = [k for k in _preferred_numeric_keys(keys, rows[0], max_items=1) if k != str_col]
    num_col = preferred_num_cols[0] if (preferred_num_cols and is_numeric_value(rows[0].get(preferred_num_cols[0]))) else num_col
    if not num_col:
        num_col = keys[1] if len(keys) > 1 else keys[0]

    labels = []
    for r in rows:
        val = r.get(str_col)
        if val is None:
            continue
        val_str = str(val).strip()
        if str_col.lower() in ("filial", "cod_filial", "filial_") or (val_str.isdigit() and len(val_str) <= 2):
            labels.append(f"Filial {val_str}")
        else:
            labels.append(val_str)

    raw_values = [to_float(r.get(num_col)) for r in rows if r.get(str_col) is not None]

    # Normalização em percentual
    total = sum(raw_values)
    values = []
    if total > 0:
        values = [round((v / total) * 100, 2) for v in raw_values]
    else:
        values = [round(100.0 / len(raw_values), 2) for _ in raw_values] if raw_values else []

    # Cores correspondentes
    palette = ["#6C63FF", "#00D2D3", "#FF6B6B", "#FECA57", "#48DBFB", "#FF9FF3", "#54A0FF", "#10B981", "#F59E0B", "#6366F1"]
    colors = [palette[i % len(palette)] for i in range(len(labels))]

    resumo = {}
    if raw_values:
        max_v = max(raw_values)
        idx_max = raw_values.index(max_v) if max_v in raw_values else 0
        sorted_vals = sorted(values, reverse=True)
        resumo = {
            "total_geral": total,
            "total_geral_formatado": f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "maior_participacao": labels[idx_max] if idx_max < len(labels) else "",
            "maior_participacao_percentual": values[idx_max] if idx_max < len(values) else 0.0,
            "total_linhas": len(labels),
            "concentracao_top3": round(sum(sorted_vals[:3]), 2),
        }

    return {
        "labels": labels,
        "values": values,
        "valores_brutos": raw_values,
        "colors": colors,
        "resumo": resumo,
    }


def transform_table_data(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Traduz dados para tabelas corporativas dinâmicas.

    Gera dinamicamente os cabeçalhos de coluna tipados e atribui flags de
    colorações semânticas (success, warning, danger) para células de 'status'.

    Parâmetros:
    -----------
    rows : list[dict[str, Any]]
        Registros limpos.

    Retorno:
    --------
    dict[str, Any]
        Estrutura contendo columns, rows, total_rows e resumo financeiro.
    """
    keys = _ordered_union_keys(rows)

    # 1. Cria definição de cabeçalho dinâmico baseado nos tipos dos campos da primeira linha
    columns = []
    for k in keys:
        label = _humanize_key(k)
        key_lower = str(k).lower()
        col_type = "string"
        width = None

        val = _first_non_empty_value(rows, k)
        if is_numeric_value(val):
            # Formata moeda se remeter a termos financeiros
            if _is_currency_key(key_lower):
                col_type = "currency"
            elif any(term in key_lower for term in ("margem", "percentual", "taxa")):
                col_type = "number"
            else:
                col_type = "number"
            width = "140px"
        elif isinstance(val, bool):
            col_type = "boolean"
            width = "80px"
        elif k == "status":
            col_type = "badge"
            width = "160px"
        elif any(term in k for term in ("data", "prazo", "criado_em")):
            col_type = "date"
            width = "120px"

        columns.append({
            "key": k,
            "label": label,
            "type": col_type,
            "sortable": True,
            "width": width,
        })

    # Dicionário de colorações semânticas
    status_colors = {
        "APROVADO": "success",
        "FIRMADO": "success",
        "PAGO": "success",
        "ATIVO": "success",
        "PENDENTE": "warning",
        "ATRASADO": "danger",
        "CANCELADO": "danger",
        "INATIVO": "danger",
        "EM_PROCESSAMENTO": "info",
        "ANALISE": "info",
    }

    # 2. Processa cada linha formatando valores de moeda e atribuindo badges de status
    processed_rows = []
    for r in rows:
        p_row = {key: r.get(key) for key in keys}
        for k, v in r.items():
            key_lower = str(k).lower()
            # Injeta representação em formato de moeda nacional
            if is_numeric_value(v) and _is_currency_key(key_lower):
                val_f = to_float(v)
                p_row[f"{k}_formatado"] = f"R$ {val_f:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            elif is_numeric_value(v) and any(term in key_lower for term in ("margem", "percentual", "taxa")):
                p_row[f"{k}_formatado"] = f"{to_float(v):.2f}%"

        # Se houver coluna de status, injeta a cor correspondente
        if "status" in r and r["status"]:
            st_upper = str(r["status"]).upper()
            p_row["status_color"] = status_colors.get(st_upper, "neutral")

        processed_rows.append(p_row)

    # 3. Calcula estatísticas para o sumário da tabela
    numeric_keys = [k for k in keys if any(is_numeric_value(row.get(k)) for row in rows)]
    resumo = {}
    if numeric_keys:
        # Prioriza colunas monetárias/financeiras
        FINANCIAL_KEYWORDS = ("VALOR", "FATURAMENTO", "RECEITA", "TOTAL", "VALOR_VENDIDO", "VENDIDO", "TICKET", "COMISSAO", "LUCRO", "MARGEM")
        primary_key = next((k for k in numeric_keys if any(term in k.upper() for term in FINANCIAL_KEYWORDS)), None)
        
        # Se não achar, tenta pegar uma coluna numérica que não seja chave temporal ou ID
        if not primary_key:
            EXCLUDED_KEYWORDS = ("MES", "ANO", "CODIGO", "ID", "RANKING", "INDEX", "NUMERO", "TELEFONE", "STATUS")
            primary_key = next((k for k in numeric_keys if not any(term in k.upper() for term in EXCLUDED_KEYWORDS)), None)
            
        # Fallback para a primeira chave numérica se nada bater
        if not primary_key:
            primary_key = numeric_keys[0]
            
        vals = [to_float(r.get(primary_key)) for r in rows if is_numeric_value(r.get(primary_key))]
        if vals:
            resumo = {
                "valor_total": round(sum(vals), 2),
                "ticket_medio": round(sum(vals) / len(vals), 2),
                "max_valor": max(vals),
                "total_registros": len(rows),
            }

    return {
        "columns": columns,
        "rows": processed_rows,
        "total_rows": len(rows),
        "resumo": resumo,
    }


def transform_kpi_data(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Traduz registros de KPIs em painéis de cartões de KPI corporativos.
    Suporta tanto a estrutura horizontal (colunas são métricas) quanto a
    estrutura vertical (cada linha é um registro contendo metrica e valor).
    """
    first_row = rows[0]
    keys = list(first_row.keys())

    # 1. Identifica se a estrutura é vertical (metrica e valor)
    METRIC_COLS = ("METRICA", "METRIC", "KPI", "NOME_METRICA", "CHAVE")
    VALUE_COLS = ("VALOR", "VALUE", "VAL")
    FORMAT_COLS = ("VALOR_FORMATADO", "FORMATADO", "VALUE_FORMATADO")
    TREND_COLS = ("TENDENCIA", "TREND")
    LABEL_TREND_COLS = ("TREND_LABEL", "TREND_VALUE", "VARIACOES", "VARIACAO", "VARIACAO_PERCENTUAL", "COMPARATIVO_ANTERIOR")

    metric_key = next((k for k in keys if k.upper() in METRIC_COLS), None)
    value_key = next((k for k in keys if k.upper() in VALUE_COLS), None)

    # Dicionário do ícone correspondente à métrica
    icon_map = {
        "receita": "currency",
        "faturamento": "currency",
        "vendas": "currency",
        "margem": "chart",
        "nps": "star",
        "clientes": "users",
        "ticket": "ticket",
        "pedido": "shopping-bag",
    }

    def detect_icon(text_val: str) -> str:
        lower_text = str(text_val).lower()
        for word, icon in icon_map.items():
            if word in lower_text:
                return icon
        return "chart"

    if metric_key and value_key:
        # A. ESTRUTURA VERTICAL DE KPIS (Cálculos e formatos predefinidos no banco)
        kpis = []
        format_key = next((k for k in keys if k.upper() in FORMAT_COLS), None)
        trend_key = next((k for k in keys if k.upper() in TREND_COLS), None)
        label_trend_key = next((k for k in keys if k.upper() in LABEL_TREND_COLS), None)

        for r in rows:
            metrica_nome = str(r[metric_key])
            val_cru = to_float(r[value_key])

            # Formatação
            if format_key and r[format_key]:
                val_formatado = str(r[format_key])
            else:
                if any(term in metrica_nome.lower() for term in ("valor", "receita", "faturamento", "ticket", "desconto", "comissao")):
                    val_formatado = f"R$ {val_cru:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                elif "%" in metrica_nome or any(term in metrica_nome.lower() for term in ("percent", "margem", "taxa", "churn")):
                    val_formatado = f"{val_cru:.1f}%"
                else:
                    val_formatado = f"{val_cru:g}"

            # Tendência (up, down, stable)
            t_val = "stable"
            if trend_key and r[trend_key]:
                t_val_raw = str(r[trend_key]).lower()
                if any(term in t_val_raw for term in ("up", "subiu", "alta", "crescimento", "positivo")):
                    t_val = "up"
                elif any(term in t_val_raw for term in ("down", "caiu", "queda", "reducao", "negativo")):
                    t_val = "down"

            # Rótulo de variação (ex: +15% vs ano anterior)
            t_label = "vs. período anterior"
            t_value = 0.0
            if label_trend_key and r[label_trend_key]:
                t_label = str(r[label_trend_key])
                # Tenta extrair número decimal do label
                import re
                nums = re.findall(r"[-+]\d*\.\d+|\d+", t_label)
                if nums:
                    t_value = float(nums[0])

            kpis.append({
                "id": metrica_nome.lower().replace(" ", "_"),
                "label": metrica_nome,
                "value": val_cru,
                "value_formatado": val_formatado,
                "unit": "BRL" if "R$" in val_formatado else ("percent" if "%" in val_formatado else "count"),
                "trend": t_val,
                "trend_value": t_value,
                "trend_label": t_label,
                "icon": detect_icon(metrica_nome),
                "sparkline": [val_cru] * 7,  # Sparkline flat
            })

        return {
            "kpis": kpis,
            "periodo": "Visão Executiva Atual",
            "gerado_em": datetime.date.today().isoformat(),
        }
    else:
        # B. ESTRUTURA HORIZONTAL (Métricas em colunas, linhas representam tempo)
        numeric_keys = _preferred_numeric_keys(keys, first_row, max_items=6)

        def get_trend(atual: float, anterior: float) -> str:
            if atual > anterior * 1.01:
                return "up"
            if atual < anterior * 0.99:
                return "down"
            return "stable"

        def get_variation(atual: float, anterior: float) -> float:
            if anterior == 0:
                return 0.0
            return round(((atual - anterior) / anterior) * 100, 2)

        seen_values = set()
        kpis = []
        for k in numeric_keys:
            if any(term in k.lower() for term in ("filial", "cod_filial", "filial_", "id", "codigo", "cod")):
                continue
            values = [to_float(r[k]) for r in rows if isinstance(r, dict) and k in r and is_numeric_value(r[k])]
            if not values:
                continue

            atual = values[-1]
            if atual in seen_values and len(seen_values) > 0:
                continue
            seen_values.add(atual)
            anterior = values[-2] if len(values) > 1 else atual

            sparkline = values[-7:] if len(values) >= 7 else values
            if len(sparkline) < 7:
                sparkline = [sparkline[0]] * (7 - len(sparkline)) + sparkline

            unit = "count"
            value_formatado = f"{atual:g}"

            if any(term in k for term in ("percent", "margem", "taxa", "churn")):
                unit = "percent"
                value_formatado = f"{atual:.1f}%"
            elif any(term in k for term in ("valor", "receita", "faturamento", "ticket", "desconto", "ptotal")):
                unit = "BRL"
                value_formatado = f"R$ {atual:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            elif any(term in k for term in ("nps", "score")):
                unit = "score"
                value_formatado = f"{atual:.1f}"

            trend_val = get_variation(atual, anterior)
            if unit == "percent":
                trend_val = round(atual - anterior, 2)

            kpis.append({
                "id": k,
                "label": _humanize_key(k),
                "value": atual,
                "value_formatado": value_formatado,
                "unit": unit,
                "trend": get_trend(atual, anterior),
                "trend_value": trend_val,
                "trend_label": "vs. período anterior" if unit != "percent" else "vs. período anterior (pp)",
                "icon": detect_icon(k),
                "sparkline": sparkline,
            })

        return {
            "kpis": kpis,
            "periodo": "Visão Executiva Atual",
            "gerado_em": datetime.date.today().isoformat(),
        }


def transform_scatter_data(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Traduz registros para gráficos de dispersão (Scatter Plot) com agrupamento por segmentos.

    Parâmetros:
    -----------
    rows : list[dict[str, Any]]
        Registros limpos.

    Retorno:
    --------
    dict[str, Any]
        Dicionário com eixo_x_label, eixo_y_label, datasets e resumo.
    """
    keys = list(rows[0].keys())
    numeric_keys = [k for k in keys if isinstance(rows[0][k], (int, float))]

    if len(numeric_keys) < 2:
        return {"rows": rows}

    x_key = numeric_keys[0]
    y_key = numeric_keys[1]

    # Busca a primeira coluna tipo string para agrupar as coordenadas (ex: Enterprise, SMB)
    seg_key = None
    for k in keys:
        if isinstance(rows[0][k], str) and k not in (x_key, y_key):
            seg_key = k
            break

    if seg_key:
        segments = {}
        for r in rows:
            seg = str(r[seg_key])
            if seg not in segments:
                segments[seg] = []
            segments[seg].append({
                "x": float(r[x_key]) if isinstance(r[x_key], (int, float)) else 0.0,
                "y": float(r[y_key]) if isinstance(r[y_key], (int, float)) else 0.0,
            })

        palette = ["rgba(108, 99, 255, 0.7)", "rgba(0, 210, 211, 0.7)", "rgba(255, 107, 107, 0.7)"]
        datasets = []
        for i, (seg, data) in enumerate(segments.items()):
            color = palette[i % len(palette)]
            datasets.append({
                "label": seg,
                "data": data,
                "backgroundColor": color,
                "borderColor": color.replace("0.7", "1.0"),
                "pointRadius": 6,
                "pointHoverRadius": 9,
            })

        return {
            "datasets": datasets,
            "eixo_x_label": _humanize_key(x_key),
            "eixo_y_label": _humanize_key(y_key),
            "resumo": {
                "total_pontos": len(rows),
                "segmentos": list(segments.keys()),
            },
        }
    else:
        points = [{
            "x": float(r[x_key]) if isinstance(r[x_key], (int, float)) else 0.0,
            "y": float(r[y_key]) if isinstance(r[y_key], (int, float)) else 0.0,
        } for r in rows]

        return {
            "datasets": [{
                "label": "Geral",
                "data": points,
                "backgroundColor": "rgba(108, 99, 255, 0.7)",
                "borderColor": "#6C63FF",
                "pointRadius": 6,
                "pointHoverRadius": 9,
            }],
            "eixo_x_label": _humanize_key(x_key),
            "eixo_y_label": _humanize_key(y_key),
            "resumo": {
                "total_pontos": len(rows),
            },
        }

