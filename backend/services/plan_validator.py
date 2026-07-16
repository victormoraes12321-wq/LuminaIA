"""
LuminaAI â€” Plan Validator, Corrector, and Normalization Layer (v5.6)
------------------------------------------------------------------
Esta camada intermediÃ¡ria valida, corrige e normaliza qualquer plano de consulta
antes de sua execuÃ§Ã£o no backend.
"""
from __future__ import annotations

import logging
import re
import uuid
import json
import unicodedata
from datetime import date, datetime, timedelta
from typing import Any, Final

from pydantic import BaseModel, Field

logger = logging.getLogger("luminaai.services.plan_validator")

# Ã‚ncora temporal oficial do sistema para resoluÃ§Ã£o de datas relativas
ANCHOR_DATE: Final[date] = date(2026, 7, 3)

_OPERATIONAL_PSEUDO_METRICS: Final[set[str]] = {
    "select",
    "consulta",
    "listagem",
    "listar",
    "lista",
    "detalhamento",
    "detalhar",
    "resumo",
    "table",
    "tabela",
    "soma",
    "media",
    "total",
    "quantidade",
    "count",
    "maximo",
    "minimo",
}

_DEFAULT_SALES_METRICS: Final[set[str]] = {
    "receita_total",
    "faturamento_realizado",
    "quantidade_pedidos",
    "unidades_vendidas",
    "ticket_medio",
    "lucro_bruto",
    "margem_lucro",
}

_FINANCIAL_OR_SALES_TERMS: Final[tuple[str, ...]] = (
    "venda",
    "vendas",
    "vendido",
    "vendida",
    "vendidos",
    "vendidas",
    "vendeu",
    "venderam",
    "unidade vendida",
    "unidades vendidas",
    "pedido",
    "pedidos",
    "compra",
    "comprou",
    "compraram",
    "faturamento",
    "faturou",
    "receita",
    "lucro",
    "margem",
    "retorno financeiro",
    "rentabilidade",
)

_REGISTRY_LISTING_TERMS: Final[tuple[str, ...]] = (
    "lista",
    "listar",
    "listagem",
    "procure",
    "buscar",
    "busque",
    "encontre",
    "todos",
    "todas",
    "cadastro",
    "cadastrado",
    "cadastrados",
    "reside",
    "residem",
    "mora",
    "moram",
    "cidade",
    "municipio",
    "endereco",
    "telefone",
    "email",
    "codigo",
    "descri",
    "descricao",
    "descrição",
    "estoque",
    "risco de estoque",
)

_REGISTRY_ENTITY_TERMS: Final[tuple[str, ...]] = (
    "cliente",
    "clientes",
    "comprador",
    "compradores",
    "vendedor",
    "vendedores",
    "representante",
    "representantes",
    "consultor",
    "consultores",
    "produto",
    "produtos",
    "item",
    "itens",
    "sku",
    "fornecedor",
    "fornecedores",
)

_MONTH_NAME_TO_NUMBER: Final[dict[str, int]] = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "março": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}


class ValidatedPlanResponse(BaseModel):
    """
    Formato de saÃ­da do validador de planos estruturados.
    """
    request_id: str | None = None
    intent: str | None = None
    validated: bool
    corrected: bool = False
    metrics: list[str] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)
    group_by: list[str] = Field(default_factory=list)
    visualization: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    fallback_applied: bool = False
    error: str | None = None
    suggested_refinement: str | None = None


def normalize_text_key(text: str) -> str:
    """Sanitiza e normaliza texto para comparaÃ§Ã£o case-insensitive sem acentos."""
    if not text:
        return ""
    text = text.lower().strip()
    replacements = {
        "Ã¡": "a", "Ã ": "a", "Ã¢": "a", "Ã£": "a", "Ã¤": "a",
        "Ã©": "e", "Ã¨": "e", "Ãª": "e", "Ã«": "e",
        "Ã­": "i", "Ã¬": "i", "Ã®": "i", "Ã¯": "i",
        "Ã³": "o", "Ã²": "o", "Ã´": "o", "Ãµ": "o", "Ã¶": "o",
        "Ãº": "u", "Ã¹": "u", "Ã»": "u", "Ã¼": "u",
        "Ã§": "c",
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text


def _is_customer_registry_view(view_name: str) -> bool:
    name = (view_name or "").upper()
    return (
        "CLIENTES_CADASTRAD" in name
        or "CLIENTES_CAD_LM" in name
        or "CADASTRO_CLIENT" in name
        or ("CLIENTE" in name and "_CAD" in name)
    )


def _has_financial_or_sales_context(q_norm: str) -> bool:
    """Evita falsos positivos como 'comprador' contendo 'compra'."""
    patterns = (
        r"\bvendas?\b",
        r"\bvendid[oa]s?\b",
        r"\bvendeu\b",
        r"\bpedidos?\b",
        r"\bcompras?\b",
        r"\bcomprou\b",
        r"\bcompraram\b",
        r"\bfatur",
        r"\breceita\b",
        r"\blucro\b",
        r"\bmargem\b",
        r"\bretorno financeiro\b",
        r"\brentabilidade\b",
    )
    return any(re.search(pattern, q_norm) for pattern in patterns)


def _is_registry_view(view_name: str) -> bool:
    name = (view_name or "").upper()
    if _is_customer_registry_view(name):
        return True
    return any(
        marker in name
        for marker in (
            "VENDEDOR_CAD",
            "VENDEDORES_CAD",
            "PRODUTOS_CAD",
            "PRODUTO_CAD",
            "FORNECEDOR_CAD",
            "FORNECEDORES_CAD",
        )
    )


def _is_customer_registry_listing_query(q_norm: str, view_name: str) -> bool:
    """Cadastro/listagem de clientes nao deve herdar metricas financeiras."""
    if "cliente" not in q_norm and "clientes" not in q_norm:
        return False
    if _has_financial_or_sales_context(q_norm):
        return False
    return _is_customer_registry_view(view_name) or any(term in q_norm for term in _REGISTRY_LISTING_TERMS)


def _is_registry_listing_query(q_norm: str, view_name: str) -> bool:
    """Views cadastrais de qualquer entidade nao devem herdar metricas financeiras."""
    if not _is_registry_view(view_name):
        return False
    if "sem compras" in q_norm or "sem compra" in q_norm or "sem venda" in q_norm or "sem vendas" in q_norm:
        return True
    if _has_financial_or_sales_context(q_norm):
        return False
    if re.match(r"^\s*e\s+[a-z0-9\s]{2,}\??\s*$", q_norm):
        return True
    return any(term in q_norm for term in _REGISTRY_LISTING_TERMS + _REGISTRY_ENTITY_TERMS)


def resolve_relative_date_range(date_range_str: str, anchor: date = ANCHOR_DATE) -> tuple[str, str] | None:
    """
    Resolve uma expressÃ£o de data relativa ou formato ISO em um intervalo de strings YYYY-MM-DD.
    """
    if not date_range_str:
        return None

    br_dates = re.findall(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", date_range_str)
    if br_dates:
        try:
            parsed = [date(int(year), int(month), int(day)) for day, month, year in br_dates[:2]]
            start = parsed[0]
            end = parsed[1] if len(parsed) > 1 else parsed[0]
            if start > end:
                start, end = end, start
            return start.isoformat(), end.isoformat()
        except ValueError:
            return None

    normalized_for_multi_month = normalize_text_key(date_range_str)
    multi_months = re.search(r"\bmeses?\s+([0-9,\se]+?)\s+de\s+(\d{4})\b", normalized_for_multi_month)
    if multi_months:
        try:
            months = [int(m) for m in re.findall(r"\d{1,2}", multi_months.group(1))]
            valid_months = sorted({m for m in months if 1 <= m <= 12})
            if valid_months:
                year = int(multi_months.group(2))
                start = date(year, valid_months[0], 1)
                last_month = valid_months[-1]
                if last_month == 12:
                    end = date(year, 12, 31)
                else:
                    end = date(year, last_month + 1, 1) - timedelta(days=1)
                return start.isoformat(), end.isoformat()
        except ValueError:
            return None

    month_name_pattern = "|".join(sorted(_MONTH_NAME_TO_NUMBER, key=len, reverse=True))
    month_name_match = re.search(
        rf"\b({month_name_pattern})\s+(?:de\s+)?(\d{{4}})\b",
        normalized_for_multi_month,
    )
    if month_name_match:
        try:
            month = _MONTH_NAME_TO_NUMBER[month_name_match.group(1)]
            year = int(month_name_match.group(2))
            start = date(year, month, 1)
            end = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
            return start.isoformat(), end.isoformat()
        except (KeyError, ValueError):
            return None

    numeric_month_text = re.search(
        r"\b(?:mes\s+)?(0?[1-9]|1[0-2])\s+de\s+(\d{4})\b",
        normalized_for_multi_month,
    )
    if numeric_month_text:
        try:
            month = int(numeric_month_text.group(1))
            year = int(numeric_month_text.group(2))
            start = date(year, month, 1)
            end = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
            return start.isoformat(), end.isoformat()
        except ValueError:
            return None

    month_year = re.search(r"\b(0?[1-9]|1[0-2])/(\d{4})\b", date_range_str)
    if month_year:
        try:
            month = int(month_year.group(1))
            year = int(month_year.group(2))
            start = date(year, month, 1)
            if month == 12:
                end = date(year, 12, 31)
            else:
                end = date(year, month + 1, 1) - timedelta(days=1)
            return start.isoformat(), end.isoformat()
        except ValueError:
            return None
    abs_pattern = r"(\d{4}-\d{2}-\d{2})\s*(?:to|ate|a|-)\s*(\d{4}-\d{2}-\d{2})"
    match = re.search(abs_pattern, date_range_str)
    if match:
        return match.group(1), match.group(2)

    single_iso = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", date_range_str)
    if single_iso:
        iso_str = single_iso.group(1)
        return iso_str, iso_str

    # Normaliza a string para comparaÃ§Ã£o
    normalized = normalize_text_key(date_range_str)


    rolling_match = re.search(
        r"\bultim[oa]s?\s+(\d+)\s+(dia|dias|semana|semanas|mes|meses|ano|anos)\b",
        normalized,
    )
    if rolling_match:
        amount = int(rolling_match.group(1))
        unit = rolling_match.group(2)
        if unit.startswith("dia"):
            total_days = amount
        elif unit.startswith("semana"):
            total_days = amount * 7
        elif unit.startswith("mes"):
            total_days = amount * 30
        else:
            total_days = amount * 365
        return (anchor - timedelta(days=max(total_days - 1, 0))).isoformat(), anchor.isoformat()
    # DicionÃ¡rio de termos mapeados
    if normalized in ("hoje", "today", "current_day", "dia atual", "data_atual"):
        iso_str = anchor.isoformat()
        return iso_str, iso_str
    elif normalized in ("ontem", "yesterday", "previous_day", "dia_anterior"):
        prev_str = (anchor - timedelta(days=1)).isoformat()
        return prev_str, prev_str
    elif normalized in ("este mes", "mes atual", "mÃªs atual", "current_month", "this_month"):
        start = date(anchor.year, anchor.month, 1)
        # Calcula o Ãºltimo dia do mÃªs
        if anchor.month == 12:
            end = date(anchor.year, 12, 31)
        else:
            end = date(anchor.year, anchor.month + 1, 1) - timedelta(days=1)
        return start.isoformat(), end.isoformat()
    elif normalized in ("mes passado", "mÃªs passado", "ultimo mes", "Ãºltimo mÃªs", "last_month", "previous_month"):
        if anchor.month == 1:
            start = date(anchor.year - 1, 12, 1)
            end = date(anchor.year - 1, 12, 31)
        else:
            start = date(anchor.year, anchor.month - 1, 1)
            end = date(anchor.year, anchor.month, 1) - timedelta(days=1)
        return start.isoformat(), end.isoformat()
    elif normalized in ("este ano", "ano atual", "current_year", "this_year"):
        return date(anchor.year, 1, 1).isoformat(), date(anchor.year, 12, 31).isoformat()
    elif normalized in ("ano passado", "ultimo ano", "Ãºltimo ano", "last_year", "previous_year"):
        return date(anchor.year - 1, 1, 1).isoformat(), date(anchor.year - 1, 12, 31).isoformat()
    elif normalized in ("ultimos 7 dias", "last_7_days"):
        return (anchor - timedelta(days=6)).isoformat(), anchor.isoformat()
    elif normalized in ("ultimos 30 dias", "last_30_days"):
        return (anchor - timedelta(days=29)).isoformat(), anchor.isoformat()
    elif normalized in ("ultimos 90 dias", "last_90_days"):
        return (anchor - timedelta(days=89)).isoformat(), anchor.isoformat()
    elif normalized in ("primeiro trimestre", "q1", "1o trimestre", "first_quarter"):
        return date(anchor.year, 1, 1).isoformat(), date(anchor.year, 3, 31).isoformat()
    elif normalized in ("segundo trimestre", "q2", "2o trimestre", "second_quarter"):
        return date(anchor.year, 4, 1).isoformat(), date(anchor.year, 6, 30).isoformat()
    elif normalized in ("terceiro trimestre", "q3", "3o trimestre", "third_quarter"):
        return date(anchor.year, 7, 1).isoformat(), date(anchor.year, 9, 30).isoformat()
    elif normalized in ("quarto trimestre", "q4", "4o trimestre", "fourth_quarter"):
        return date(anchor.year, 10, 1).isoformat(), date(anchor.year, 12, 31).isoformat()

    return None


def validate_and_normalize_plan(
    plan: Any,
    query_text: str = "",
    view_name: str = "",
    catalog: list[Any] | None = None,
    tenant_id: uuid.UUID | None = None,
) -> ValidatedPlanResponse:
    """
    Valida estruturalmente e semanticamente o plano e retorna um plano corrigido
    e normalizado, ou sinaliza rejeiÃ§Ã£o caso falte informaÃ§Ãµes cruciais.
    """
    # â”€â”€ 1. EstruturaÃ§Ã£o do input (plan pode ser dict ou StructuredPlanSchema) â”€â”€
    raw_plan: dict[str, Any] = {}
    if hasattr(plan, "model_dump"):
        raw_plan = plan.model_dump()
    elif isinstance(plan, dict):
        raw_plan = plan
    else:
        return ValidatedPlanResponse(
            validated=False,
            error="INSUFFICIENT_INFORMATION",
            suggested_refinement="O plano de consulta fornecido Ã© invÃ¡lido ou nulo."
        )

    # â”€â”€ 2. ValidaÃ§Ã£o Estrutural BÃ¡sica â”€â”€
    request_id = raw_plan.get("request_id")
    intent = raw_plan.get("intent", "")
    
    if not request_id:
        # Gera se ausente em testes
        request_id = str(uuid.uuid4())

    if not intent or len(intent.strip()) < 3:
        return ValidatedPlanResponse(
            validated=False,
            error="INSUFFICIENT_INFORMATION",
            suggested_refinement="A pergunta do usuÃ¡rio Ã© vaga ou nÃ£o pÃ´de ser interpretada."
        )

    corrected = False
    warnings = []
    fallback_applied = False

    metrics: list[str] = list(raw_plan.get("metrics", []))
    group_by: list[str] = list(raw_plan.get("group_by", []))
    view_upper = (view_name or "").upper()
    
    # Normaliza filtros
    filters_raw = raw_plan.get("filters", {})
    if hasattr(filters_raw, "model_dump"):
        filters_raw = filters_raw.model_dump()
    elif not isinstance(filters_raw, dict):
        filters_raw = {}
        
    date_range = filters_raw.get("date_range", "")
    products = list(filters_raw.get("products", []))
    customers = list(filters_raw.get("customers", []))
    regions = list(filters_raw.get("regions", []))

    # Normaliza visualizaÃ§Ã£o
    vis_raw = raw_plan.get("visualization", {})
    if hasattr(vis_raw, "model_dump"):
        vis_raw = vis_raw.model_dump()
    elif not isinstance(vis_raw, dict):
        vis_raw = {}
    
    vis_type = vis_raw.get("type", "")
    layout_priority = vis_raw.get("layout_priority", "ALTA")

    # Mapeamento do tipo de consulta
    query_type = raw_plan.get("query_type", "SELECT")

    # â”€â”€ 3. ExpansÃ£o de IntenÃ§Ãµes Vagas â”€â”€
    # Se pedir algo geral como "vendas hoje" sem mÃ©tricas
    q_norm = normalize_text_key(query_text)
    is_customer_registry_listing = _is_customer_registry_listing_query(q_norm, view_name)
    is_registry_listing = _is_registry_listing_query(q_norm, view_name) or is_customer_registry_listing

    if is_registry_listing:
        original_metrics = list(metrics)
        metrics = [
            m for m in metrics
            if normalize_text_key(str(m)) not in _DEFAULT_SALES_METRICS
            and normalize_text_key(str(m)) not in _OPERATIONAL_PSEUDO_METRICS
        ]
        query_type = "SELECT"
        vis_type = "TABLE"
        if date_range:
            date_range = ""
            corrected = True
            warnings.append("PerÃ­odo removido: views cadastrais nÃ£o possuem recorte temporal obrigatÃ³rio.")
        if original_metrics != metrics:
            corrected = True
            warnings.append(
                "Consulta cadastral normalizada como listagem: "
                "mÃ©tricas financeiras inferidas foram removidas."
            )

    if ("venda" in q_norm or "faturamento" in q_norm) and not metrics and not is_registry_listing:
        metrics = ["receita_total", "quantidade_pedidos", "ticket_medio"]
        corrected = True
        warnings.append("Consulta de vendas vaga expandida para mÃ©tricas essenciais (receita, pedidos e ticket mÃ©dio).")

    seller_ranking_terms = (
        "quem vendeu mais",
        "quem mais vendeu",
        "quem faturou mais",
        "vendedor lider",
        "lider em faturamento",
        "lider de vendas",
    )
    if any(term in q_norm for term in seller_ranking_terms):
        if "receita_total" not in metrics:
            metrics.append("receita_total")
        if not any("vendedor" in g or "representante" in g for g in group_by):
            group_by.append("vendedor_nome")
        query_type = "RANKING"
        if not vis_type or vis_type.upper() in ("KPI", "CARD", "TABLE"):
            vis_type = "BAR"
        corrected = True
        warnings.append("Pergunta 'quem vendeu mais' interpretada como ranking de vendedores por receita.")

    # Se as mÃ©tricas continuarem vazias, infere faturamento
    if not metrics and not is_registry_listing:
        metrics = ["receita_total"]
        corrected = True
        warnings.append("Nenhuma mÃ©trica solicitada. Inferida 'receita_total' como padrÃ£o.")

    # Mapeia somente termos informais de lucro, preservando metricas oficiais.
    if "lucro" in q_norm or any(normalize_text_key(str(m)) in {"lucro", "profit"} for m in metrics):
        metrics = [m for m in metrics if normalize_text_key(str(m)) not in {"lucro", "profit"}]
        if "lucro_bruto" not in metrics:
            metrics.append("lucro_bruto")
        if "margem_lucro" not in metrics:
            metrics.append("margem_lucro")
        corrected = True
        warnings.append("Termo informal 'lucro' mapeado para 'lucro_bruto' e 'margem_lucro'.")

    product_terms = ("produto", "produtos", "item", "itens", "sku", "mercadoria", "mercadorias", "insumo", "insumos")
    product_margin_terms = (
        "margem",
        "lucro",
        "rentabilidade",
        "rentavel",
        "rentaveis",
        "lucratividade",
        "lucrativo",
        "lucrativos",
        "retorno financeiro",
        "resultado financeiro",
    )
    if any(term in q_norm for term in product_terms) and any(term in q_norm for term in product_margin_terms):
        preferred_metrics = ["margem_lucro", "lucro_bruto", "receita_total"]
        metrics = preferred_metrics + [m for m in metrics if m not in preferred_metrics]
        metrics = list(dict.fromkeys(metrics))
        if not any("produto" in g for g in group_by):
            group_by.append("produto_nome")
        vis_type = "BAR"
        query_type = "RANKING"
        corrected = True
        warnings.append("Consulta de margem/lucro por produto interpretada como ranking financeiro por produto.")

    financial_return_terms = (
        "retorno financeiro",
        "resultado financeiro",
        "maior retorno",
        "retorno para empresa",
        "rentabilidade",
        "rentavel",
        "rentaveis",
        "lucratividade",
        "lucrativo",
        "lucrativos",
    )
    if any(term in q_norm for term in product_terms) and any(term in q_norm for term in financial_return_terms):
        if "receita_total" not in metrics:
            metrics.append("receita_total")
        if "VW_VENDAS_LM" not in view_upper and "margem_lucro" not in metrics:
            metrics.append("margem_lucro")
        if not any("produto" in g for g in group_by):
            group_by.append("produto_nome")
        vis_type = "BAR"
        query_type = "RANKING"
        corrected = True
        warnings.append("Retorno financeiro por produto interpretado como ranking por receita e margem.")

    # Mapeia "top produto" -> garante group_by por produto_nome
    if ("top produto" in q_norm or "melhor produto" in q_norm or "produto mais vendido" in q_norm) and not any("produto" in g for g in group_by):
        group_by.append("produto_nome")
        corrected = True
        warnings.append("Ranking de produtos configurado; agrupamento automÃ¡tico por 'produto_nome' adicionado.")

    # â”€â”€ 4.5. ValidaÃ§Ã£o com a Camada SemÃ¢ntica de NegÃ³cio â”€â”€
    from services.semantic_layer import canonicalize_metric_name, resolve_metric_for_view, validate_metrics_and_sources
    
    # Normaliza nomes de mÃ©tricas comuns antes de validar
    normalized_metrics = []
    for m in metrics:
        m_key = normalize_text_key(str(m))
        if m_key in _OPERATIONAL_PSEUDO_METRICS:
            if is_registry_listing or m_key in {
                "select",
                "consulta",
                "listagem",
                "listar",
                "lista",
                "detalhamento",
                "detalhar",
                "resumo",
                "table",
                "tabela",
            }:
                corrected = True
                continue
        if m in ("revenue", "receita", "soma", "media", "total", "quantidade", "maximo", "minimo", "count", "vendas", "kpi", "ranking", "top", "bottom", "comparacao", "tendencia"):
            normalized = "receita_total"
        elif m in ("lucro", "profit"):
            normalized = "lucro_bruto"
        elif m in ("margem", "margem_bruta", "margem_bruta_media"):
            normalized = "margem_lucro"
        elif m in ("churn", "taxa_churn"):
            normalized = "churn_rate"
        elif m in ("ltv"):
            normalized = "ltv_estimado"
        elif m in ("cac"):
            normalized = "cac_estimado"
        elif m in ("conversao"):
            normalized = "taxa_conversao"
        else:
            normalized = m

        canonical = resolve_metric_for_view(canonicalize_metric_name(normalized), view_name)
        if canonical != m:
            corrected = True
        normalized_metrics.append(canonical)
            
    metrics = list(dict.fromkeys(normalized_metrics))

    errors_semanticos = validate_metrics_and_sources(metrics, view_name)
    if errors_semanticos:
        from services.ai.csie import csie
        corrected_metrics = []
        has_fixes = False
        
        for m in metrics:
            temp_err = validate_metrics_and_sources([m], view_name)
            if temp_err:
                resolved_phys = csie.resolve_metric_fallback(m)
                if resolved_phys:
                    corrected_metrics.append(resolved_phys)
                    corrected = True
                    has_fixes = True
                    warnings.append(f"MÃ©trica invÃ¡lida '{m}' resolvida dinamicamente via CSIE para '{resolved_phys}'.")
                else:
                    corrected_metrics.append(m)
            else:
                corrected_metrics.append(m)
                
        if has_fixes:
            metrics = list(dict.fromkeys(corrected_metrics))
            errors_semanticos = validate_metrics_and_sources(metrics, view_name)
            
        if errors_semanticos:
            if catalog and tenant_id:
                from services.aqd_service import aqd
                aqd_res = aqd.decompose(query_text, catalog, tenant_id)
                if aqd_res.decomposed:
                    logger.info("[Validator] Incompatibilidade detectada. Acionada re-decomposiÃ§Ã£o via AQD com sucesso.")
                    return ValidatedPlanResponse(
                        validated=True,
                        corrected=True,
                        metrics=metrics,
                        filters={"date_range": "este mÃªs"},
                        warnings=["Incompatibilidade de mÃ©trica analÃ­tica. Acionada decomposiÃ§Ã£o reativa via AQD."],
                        suggested_refinement="AQD_DECOMPOSITION_TRIGGERED"
                    )
            
            return ValidatedPlanResponse(
                validated=False,
                error="INVALID_METRIC",
                suggested_refinement=f"InconsistÃªncia de mÃ©trica corporativa: {'; '.join(errors_semanticos)}"
            )

    # â”€â”€ 5. NormalizaÃ§Ã£o de Datas Relativas â”€â”€
    resolved_dates = None
    if date_range:
        resolved_dates = resolve_relative_date_range(date_range)
        if resolved_dates:
            start_date, end_date = resolved_dates
            # Se for data relativa resolvida, atualizamos o date_range para o formato absoluto
            new_range = f"{start_date} to {end_date}"
            if date_range != new_range:
                date_range = new_range
                corrected = True
                warnings.append(f"Data relativa resolvida para intervalo absoluto: {new_range}")

    explicit_query_dates = resolve_relative_date_range(query_text)
    if explicit_query_dates:
        start_date, end_date = explicit_query_dates
        explicit_range = f"{start_date} to {end_date}"
        if date_range != explicit_range:
            date_range = explicit_range
            corrected = True
            fallback_applied = False
            warnings.append(f"Data explicita da pergunta priorizada sobre periodo inferido: {date_range}")
    
    # Se nÃ£o houver perÃ­odo (Caso 2), aplica o mÃªs atual por padrÃ£o
    if not date_range:
        resolved_dates = resolve_relative_date_range(query_text)
        if resolved_dates:
            start_date, end_date = resolved_dates
            date_range = f"{start_date} to {end_date}"
            corrected = True
            warnings.append(f"Data absoluta extraida da pergunta: {date_range}")

    if not date_range and not is_registry_listing:
        resolved_dates = resolve_relative_date_range("este mes")
        if resolved_dates:
            start_date, end_date = resolved_dates
            date_range = f"{start_date} to {end_date}"
            corrected = True
            fallback_applied = True
            warnings.append(f"PerÃ­odo ausente. Aplicado mÃªs atual por padrÃ£o: {date_range}")

    # â”€â”€ 6. DetecÃ§Ã£o de Conflitos e InconsistÃªncias â”€â”€
    # Verifica se as datas no date_range sÃ£o contraditÃ³rias (ex: data_inicio > data_fim)
    if date_range:
        match = re.search(r"(\d{4}-\d{2}-\d{2})\s*(?:to|ate|a|-)\s*(\d{4}-\d{2}-\d{2})", date_range)
        if match:
            try:
                d1 = datetime.strptime(match.group(1), "%Y-%m-%d").date()
                d2 = datetime.strptime(match.group(2), "%Y-%m-%d").date()
                if d1 > d2:
                    # Corrige invertendo as datas
                    date_range = f"{d2.isoformat()} to {d1.isoformat()}"
                    corrected = True
                    warnings.append(f"Datas de inÃ­cio e fim invertidas foram auto-corrigidas: {date_range}")
            except Exception:
                pass

    # â”€â”€ 7. Auto-CorreÃ§Ã£o de VisualizaÃ§Ã£o â”€â”€
    tipos_validos = {"BAR", "LINE", "PIE", "TABLE", "KPI", "AREA", "SCATTER", "HEATMAP", "TREEMAP", "FUNNEL"}
    if not vis_type or vis_type not in tipos_validos:
        old_vis = vis_type
        # Analisa o tipo de intenÃ§Ã£o semÃ¢ntica
        is_comparacao = raw_plan.get("is_comparacao", False) or "comparativo" in q_norm or len(group_by) > 1 or len(metrics) > 1
        is_tendencia = query_type == "TIME_SERIES" or "tendencia" in q_norm or "evolucao" in q_norm or "mes" in group_by or "data" in group_by
        is_ranking = "top" in q_norm or "ranking" in q_norm or "melhor" in q_norm or "pior" in q_norm
        is_distribuicao = "distribuicao" in q_norm or "participacao" in q_norm or "categoria" in group_by

        if is_comparacao or is_ranking:
            vis_type = "BAR"
        elif is_tendencia:
            vis_type = "LINE"
        elif is_distribuicao:
            vis_type = "PIE"
        else:
            vis_type = "TABLE"

        corrected = True
        warnings.append(f"VisualizaÃ§Ã£o '{old_vis}' corrigida automaticamente para '{vis_type}' com base na intenÃ§Ã£o.")

    # â”€â”€ 8. Montagem do Plano Validado â”€â”€
    validated_filters = {
        "date_range": date_range,
        "products": products,
        "customers": customers,
        "regions": regions
    }
    
    validated_visualization = {
        "type": vis_type,
        "layout_priority": layout_priority
    }

    return ValidatedPlanResponse(
        request_id=request_id,
        intent=intent,
        validated=True,
        corrected=corrected,
        metrics=metrics,
        filters=validated_filters,
        group_by=group_by,
        visualization=validated_visualization,
        warnings=warnings,
        fallback_applied=fallback_applied
    )
