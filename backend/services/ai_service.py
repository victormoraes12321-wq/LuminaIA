"""
LuminaAI — Motor de Intenção (v4.0 CIE Bridge)
---------------------------------------------
Ponte de compatibilidade retroativa para redirecionar as chamadas de IA
ao Corporate Intelligence Engine (CIE).
"""
from __future__ import annotations

import logging
import calendar
import re
import unicodedata
import uuid
from datetime import date
from typing import Any, Final
from openai import AsyncOpenAI

from schemas.view_catalog import ViewCatalogSummary
from services.context_guard import sanitize_history, validate_user_query
from services.ai_credential_manager import (
    AICMError,
    AUTHORIZED_OPENAI_MODEL,
    ai_credential_manager,
)
from services.ai_invocation_manager import ai_invocation_manager
from services.ai.legacy_contracts import (
    AIServiceError,
    IntentionResponse,
    ModelViolationError,
    PlanFiltersSchema,
    PlanVisualizationSchema,
    StructuredPlanSchema,
)
logger = logging.getLogger(__name__)

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
_CITY_FALLBACK_STOP_TERMS: Final[set[str]] = {
    "aberto",
    "abertos",
    "ativo",
    "ativos",
    "geral",
    "todos",
    "todas",
    "mes",
    "ano",
    "periodo",
    "possui",
    "tem",
    "teve",
    "maior",
    "menor",
    "cresceu",
    "caiu",
    "faturamento",
    "receita",
    "vendedor",
    "vendedores",
    "produto",
    "produtos",
    *_MONTH_NAME_TO_NUMBER.keys(),
}
_SALES_CONTEXT_TERMS: Final[tuple[str, ...]] = (
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
    "comprou",
    "compraram",
    "fatura",
    "faturar",
    "faturado",
    "faturada",
    "faturamos",
    "faturamento",
    "faturou",
    "receita",
)

def _is_probably_invalid_openai_key(api_key: str | None) -> bool:
    """Compatibility wrapper: credential validation belongs to AICM."""
    return ai_credential_manager.is_probably_invalid_key(api_key)


def _is_openai_auth_error(exc: Exception) -> bool:
    """Compatibility wrapper: authentication classification belongs to AICM."""
    return ai_credential_manager.is_auth_error(exc)


def _normalize_fallback_text(value: str) -> str:
    text = (value or "").lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _find_catalog_view_for_fallback(
    catalog: list[ViewCatalogSummary],
    preferred_terms: list[str],
) -> ViewCatalogSummary | None:
    normalized_terms = [_normalize_fallback_text(term) for term in preferred_terms]

    for view in catalog:
        name = _normalize_fallback_text(getattr(view, "nome_view_oracle", ""))
        if any(term and term in name for term in normalized_terms):
            return view

    for view in catalog:
        haystack = _normalize_fallback_text(
            f"{getattr(view, 'nome_view_oracle', '')} {getattr(view, 'descricao_para_ia', '')}"
        )
        if any(term and term in haystack for term in normalized_terms):
            return view

    return catalog[0] if catalog else None


def _extract_limit_for_fallback(query_norm: str) -> int | None:
    match = re.search(r"\b(?:top|primeir[oa]s?|ranking)\s+(\d{1,3})\b", query_norm)
    if match:
        try:
            return max(1, int(match.group(1)))
        except ValueError:
            return None
    return None


def _extract_date_range_for_fallback(query: str) -> str:
    br_date = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", query or "")
    if br_date:
        day = int(br_date.group(1))
        month = int(br_date.group(2))
        year = int(br_date.group(3))
        try:
            explicit_day = date(year, month, day)
            return f"{explicit_day.isoformat()} to {explicit_day.isoformat()}"
        except ValueError:
            pass

    iso_date = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", query or "")
    if iso_date:
        return f"{iso_date.group(1)} to {iso_date.group(1)}"

    explicit_month_year_raw = re.search(r"\b(0?[1-9]|1[0-2])\s*/\s*(\d{4})\b", query or "")
    if explicit_month_year_raw:
        month = int(explicit_month_year_raw.group(1))
        year = int(explicit_month_year_raw.group(2))
        end = date(year, month, calendar.monthrange(year, month)[1])
        return f"{date(year, month, 1).isoformat()} to {end.isoformat()}"

    normalized = _normalize_fallback_text(query)

    multi_month_match = re.search(r"\bmeses?\s+([0-9,\se]+?)\s+de\s+(\d{4})\b", normalized)
    if multi_month_match:
        months = [int(m) for m in re.findall(r"\d{1,2}", multi_month_match.group(1))]
        valid_months = sorted({m for m in months if 1 <= m <= 12})
        if valid_months:
            year = int(multi_month_match.group(2))
            start = date(year, valid_months[0], 1)
            last_month = valid_months[-1]
            end = date(year, last_month, calendar.monthrange(year, last_month)[1])
            return f"{start.isoformat()} to {end.isoformat()}"

    explicit_month_year = re.search(r"\b(0?[1-9]|1[0-2])\s*/\s*(\d{4})\b", normalized)
    if explicit_month_year:
        month = int(explicit_month_year.group(1))
        year = int(explicit_month_year.group(2))
        end = date(year, month, calendar.monthrange(year, month)[1])
        return f"{date(year, month, 1).isoformat()} to {end.isoformat()}"

    month_name_pattern = "|".join(sorted(_MONTH_NAME_TO_NUMBER, key=len, reverse=True))
    month_name_year = re.search(rf"\b({month_name_pattern})\s+(?:de\s+)?(\d{{4}})\b", normalized)
    if month_name_year:
        month = _MONTH_NAME_TO_NUMBER[month_name_year.group(1)]
        year = int(month_name_year.group(2))
        end = date(year, month, calendar.monthrange(year, month)[1])
        return f"{date(year, month, 1).isoformat()} to {end.isoformat()}"

    numeric_month_text = re.search(r"\b(?:mes\s+)?(0?[1-9]|1[0-2])\s+de\s+(\d{4})\b", normalized)
    if numeric_month_text:
        month = int(numeric_month_text.group(1))
        year = int(numeric_month_text.group(2))
        end = date(year, month, calendar.monthrange(year, month)[1])
        return f"{date(year, month, 1).isoformat()} to {end.isoformat()}"

    if "ultimos 3 meses" in normalized:
        return "ultimos 3 meses"
    if "mes passado" in normalized or "ultimo mes" in normalized:
        return "mes passado"
    if "hoje" in normalized:
        return "hoje"
    if "ontem" in normalized:
        return "ontem"
    return "este mes"


def _extract_city_for_fallback(query_norm: str) -> str | None:
    city_stop = r"(?:e|com|que|onde|bairro|estado|uf|telefone|fone|celular|email|cep|classe|praca|vendedor|produto)"
    patterns = (
        rf"\bcidade\s+de\s+([a-z0-9\s]+?)(?:\s+{city_stop}\b|\s+(?:no|na)\s+(?:bairro|estado|uf)\b|$)",
        rf"\bcidade\s+([a-z0-9\s]+?)(?:\s+{city_stop}\b|\s+(?:no|na)\s+(?:bairro|estado|uf)\b|$)",
        rf"\b(?:em|na|no)\s+cidade\s+de\s+([a-z0-9\s]+?)(?:\s+{city_stop}\b|\s+(?:no|na)\s+(?:bairro|estado|uf)\b|$)",
        rf"\bmunicipio\s+de\s+([a-z0-9\s]+?)(?:\s+{city_stop}\b|\s+(?:no|na)\s+(?:bairro|estado|uf)\b|$)",
        rf"\bmunicipio\s+([a-z0-9\s]+?)(?:\s+{city_stop}\b|\s+(?:no|na)\s+(?:bairro|estado|uf)\b|$)",
        r"\b(?:em|na|no)\s+([a-z0-9\s]+?)\s+(?:cidade|municipio)\b",
        rf"\bclientes?\s+(?:de|do|da|dos|das)\s+([a-z0-9\s]+?)(?:\s+{city_stop}\b|\s+(?:no|na)\s+(?:bairro|estado|uf)\b|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, query_norm)
        if match:
            value = " ".join(match.group(1).split()).strip()
            first_token = value.split()[0] if value else ""
            if value and first_token not in _CITY_FALLBACK_STOP_TERMS and value not in _CITY_FALLBACK_STOP_TERMS:
                return value
    is_customer_registry_query = (
        any(term in query_norm for term in ("cliente", "clientes", "cadastro", "cadastrado", "cadastrados"))
        and not any(term in query_norm for term in _SALES_CONTEXT_TERMS)
    )
    if is_customer_registry_query:
        match = re.search(r"\b(?:em|na|no)\s+([a-z][a-z0-9\s]{2,})$", query_norm)
        if match:
            value = " ".join(match.group(1).split()).strip()
            if value and not any(ch.isdigit() for ch in value) and value not in _CITY_FALLBACK_STOP_TERMS:
                return value
    return None


def _extract_registry_params_for_fallback(query_norm: str) -> dict[str, str]:
    params: dict[str, str] = {}
    city = _extract_city_for_fallback(query_norm)
    if city:
        params["cidade"] = city

    doc_match = re.search(r"\b(?:cpf|cnpj|documento|cpf\s*cnpj)\s*(?:do|da|de|numero)?\s*([0-9.\-\/]{5,})", query_norm)
    if doc_match:
        params["documento"] = re.sub(r"\D+", "", doc_match.group(1)) or doc_match.group(1).strip()

    email_match = re.search(r"\b([a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,})\b", query_norm)
    if email_match:
        params["email"] = email_match.group(1)

    phone_match = re.search(r"\b(?:telefone|fone|celular|whatsapp)\s*(?:do|da|de)?\s*([0-9()\s.\-+]{8,})", query_norm)
    if phone_match:
        params["telefone"] = re.sub(r"\D+", "", phone_match.group(1)) or phone_match.group(1).strip()

    for key, pattern in {
        "bairro": r"\bbairro\s+(?:de|do|da)?\s*([a-z0-9\s]+?)(?:\s+(?:e|com|que|onde|cidade|municipio|estado|uf)\b|\s+(?:no|na|de|do|da)\s+(?:cidade|municipio|estado|uf)\b|$)",
        "praca": r"\bpraca\s+(?:de|do|da)?\s*([a-z0-9\s]+?)(?:\s+(?:e|com|que|onde|cidade|municipio|estado|uf)\b|\s+(?:no|na|de|do|da)\s+(?:cidade|municipio|estado|uf|bairro)\b|$)",
        "classe": r"\bclasse\s+([a-z0-9\s]+?)(?:\s+(?:e|com|que|onde|cidade|municipio|estado|uf)\b|\s+(?:no|na|de|do|da)\s+(?:cidade|municipio|estado|uf|bairro)\b|$)",
        "cep": r"\bcep\s+([0-9.\-]{5,})",
    }.items():
        match = re.search(pattern, query_norm)
        if match:
            value = " ".join(match.group(1).split()).strip()
            if value:
                params[key] = value

    state_match = re.search(r"\b(?:uf|estado)\s+(?:de|do|da)?\s*([a-z]{2,20})(?:\s+(?:e|com|que|onde)\b|$)", query_norm)
    if state_match:
        value = state_match.group(1).strip()
        params["uf" if len(value) == 2 else "estado"] = value

    return params


def _first_fallback_match(query_norm: str, patterns: tuple[str, ...]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, query_norm)
        if match:
            value = " ".join(match.group(1).split()).strip()
            if value:
                return value
    return None


def _extract_entity_registry_params_for_fallback(query_norm: str, entity: str) -> dict[str, str]:
    """Extrai filtros cadastrais por entidade sem depender da IA."""
    if entity in {"CLIENTE", "FORNECEDOR"}:
        params = _extract_registry_params_for_fallback(query_norm)
    else:
        params = {}

    if entity == "VENDEDOR":
        name = _first_fallback_match(
            query_norm,
            (
                r"\b(?:vendedor|representante|consultor)\s+(?:chamado|nome|de nome)?\s*([a-z0-9\s]{3,}?)(?:\s+(?:com|que|onde|em|na|no|codigo|cpf|email|telefone)\b|$)",
                r"\b(?:dados|cadastro|telefone|email)\s+(?:do|da|de)\s+(?:vendedor|representante|consultor)\s+([a-z0-9\s]{3,}?)(?:\s+(?:com|que|onde|em|na|no)\b|$)",
            ),
        )
        if name and name.split()[0] not in {"codigo", "cpf", "email", "telefone", "cidade"}:
            params["vendedor_nome"] = name
        code = _first_fallback_match(query_norm, (r"\b(?:codigo|cod|id)\s+(?:do|da|de)?\s*(?:vendedor|representante|consultor)?\s*([0-9]{1,})\b",))
        if code:
            params["codigo_vendedor"] = code
        doc = _first_fallback_match(query_norm, (r"\b(?:cpf|documento)\s*(?:do|da|de|numero)?\s*([0-9.\-\/]{5,})",))
        if doc:
            params["cpf"] = re.sub(r"\D+", "", doc) or doc
        city = _extract_city_for_fallback(query_norm)
        if city:
            params["cidade"] = city

    elif entity == "PRODUTO":
        product = _first_fallback_match(
            query_norm,
            (
                r"\b(?:produtos|produto|item|itens|pecas|peças)\s+(?:chamado|nome|descricao|descri[cç]ao|de nome)\s*([a-z0-9\s]{2,}?)(?:\s+(?:com|que|onde|em|na|no|codigo|ean|familia|categoria|fornecedor|situacao|por|para|orden)\b|$)",
                r"\b(?:produtos|produto|item|itens|pecas|peças)\s+(?:da|do|de|marca|fabricante)\s+([a-z0-9\s]{2,}?)(?:\s+(?:com|que|onde|em|na|no|codigo|ean|familia|categoria|fornecedor|situacao|por|para|orden|comprad|vendid|mais|menos)\b|$)",
                r"\b(?:marca|fabricante)\s+(?:da|do|de)?\s*([a-z0-9\s]{2,}?)(?:\s+(?:e|com|que|onde|familia|categoria|situacao|por|para|orden|comprad|vendid|mais|menos)\b|$)",
                r"\b(?:dados|cadastro|estoque)\s+(?:do|da|de)\s+(?:produto|item|sku)\s+([a-z0-9\s]{2,}?)(?:\s+(?:com|que|onde|em|na|no)\b|$)",
                r"\b(?:sobre|da|de|do)\s+(?:a|o)?\s*(husqvarna|stihl|tramontina|bristol|makita|bosch|toyama|trapp|buffalo)\b",
            ),
        )
        if product and product.split()[0] not in {"codigo", "ean", "familia", "categoria", "fornecedor", "situacao", "todos", "todas"}:
            clean_product = product.strip()
            params["produto_nome"] = clean_product
            params["marca"] = clean_product
            params["termo_busca"] = clean_product
        code = _first_fallback_match(query_norm, (r"\b(?:codigo|cod|sku)\s+(?:do|da|de)?\s*(?:produto|item)?\s*([a-z0-9.\-\/]{2,})\b",))
        if code:
            params["codigo_produto"] = code
        ean = _first_fallback_match(query_norm, (r"\b(?:ean|codigo de barras|cod barras)\s+([0-9]{5,})\b",))
        if ean:
            params["codigo_barras"] = ean
        family = _first_fallback_match(query_norm, (r"\b(?:familia|categoria|grupo)\s+(?:de|do|da)?\s*([a-z0-9\s]{2,}?)(?:\s+(?:e|com|que|onde|situacao|fornecedor)\b|$)",))
        if family:
            params["categoria"] = family
        supplier = _first_fallback_match(query_norm, (r"\bfornecedor\s+(?:de|do|da)?\s*([a-z0-9\s]{2,}?)(?:\s+(?:e|com|que|onde|familia|categoria|situacao)\b|$)",))
        if supplier:
            params["fornecedor_nome"] = supplier
        situation = _first_fallback_match(query_norm, (r"\b(?:situacao|status)\s+(ativo|inativo|bloqueado|suspenso|liberado)\b",))
        if situation:
            params["situacao"] = situation

    elif entity == "FORNECEDOR":
        supplier = _first_fallback_match(
            query_norm,
            (
                r"\b(?:fornecedor|fornecedores)\s+(?:chamado|nome|fantasia|de nome)?\s*([a-z0-9\s]{3,}?)(?:\s+(?:com|que|onde|em|na|no|codigo|cpf|cnpj|email|telefone|cidade)\b|$)",
                r"\b(?:dados|cadastro|telefone|email)\s+(?:do|da|de)\s+fornecedor\s+([a-z0-9\s]{3,}?)(?:\s+(?:com|que|onde|em|na|no)\b|$)",
            ),
        )
        if supplier and supplier.split()[0] not in {"codigo", "cpf", "cnpj", "email", "telefone", "cidade"}:
            params["fornecedor_nome"] = supplier
        code = _first_fallback_match(query_norm, (r"\b(?:codigo|cod|id)\s+(?:do|da|de)?\s*fornecedor?\s*([0-9]{1,})\b",))
        if code:
            params["codigo_fornecedor"] = code

    return params


def _build_deterministic_fallback_intention(
    pergunta: str,
    catalog: list[ViewCatalogSummary],
    request_id: str | None,
    reason: str,
) -> IntentionResponse:
    query_norm = _normalize_fallback_text(pergunta)
    limit = _extract_limit_for_fallback(query_norm)
    date_range = _extract_date_range_for_fallback(pergunta)

    is_ranking = any(
        term in query_norm
        for term in (
            "top",
            "ranking",
            "mais vender",
            "mais vendido",
            "mais vendidos",
            "mais vendida",
            "mais vendidas",
            "vendeu mais",
            "vendeu menos",
            "mais vendeu",
            "menos vendeu",
            "faturou mais",
            "faturou menos",
            "mais tem",
            "maior",
            "menor",
            "melhor",
            "melhores",
            "pior",
            "piores",
            "lider",
            "indo mal",
            "ficou em segundo",
        )
    )
    comparison_context = any(
        term in query_norm
        for term in (
            "compare",
            "comparar",
            "comparativo",
            "comparacao",
            "crescendo",
            "cresceu",
            "crescimento",
            "caiu",
            "queda",
            "anterior",
        )
    )
    quantity_sales_context = any(
        term in query_norm
        for term in (
            "quantas vendas",
            "quantidade de vendas",
            "numero de vendas",
            "número de vendas",
            "vendas realizadas",
            "vendas foram realizadas",
            "quantos pedidos",
            "quantidade de pedidos",
        )
    )
    ticket_context = "ticket" in query_norm or "valor medio" in query_norm or "valor médio" in query_norm
    customer_count_sales_context = (
        any(term in query_norm for term in ("quantos clientes", "quantidade de clientes", "numero de clientes", "número de clientes"))
        and any(term in query_norm for term in ("compraram", "comprou", "compras", "vendas", "faturamento"))
    )
    target_context = "meta" in query_norm or "bateu meta" in query_norm
    problem_or_recommendation_context = any(
        term in query_norm
        for term in (
            "problema",
            "problemas",
            "atencao",
            "atenção",
            "focar",
            "recomenda",
            "recomendacao",
            "recomendação",
            "indo mal",
            "melhores",
            "melhor",
        )
    )
    pure_problem_context = "problema" in query_norm or "problemas" in query_norm
    stock_risk_context = "estoque" in query_norm or "risco de estoque" in query_norm
    wants_financial_return = any(
        term in query_norm
        for term in (
            "retorno financeiro",
            "resultado financeiro",
            "retorno para empresa",
            "maior retorno",
            "rentabilidade",
            "rentavel",
            "rentaveis",
            "lucratividade",
            "lucrativo",
            "lucrativos",
            "margem",
            "lucro",
        )
    )
    margin_or_profit_context = any(
        term in query_norm
        for term in (
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
    )
    lowest_context = any(
        term in query_norm
        for term in (
            "menor",
            "pior",
            "mais baixo",
            "mais baixa",
            "menos",
            "baixo retorno",
            "baixa rentabilidade",
        )
    )
    highest_context = any(
        term in query_norm
        for term in (
            "maior",
            "melhor",
            "mais alto",
            "mais alta",
            "mais rentavel",
            "mais rentaveis",
            "mais lucrativo",
            "mais lucrativos",
            "maior retorno",
        )
    )
    sales_customer_context = any(term in query_norm for term in _SALES_CONTEXT_TERMS)
    customer_registry_context = (
        any(term in query_norm for term in ("cliente", "clientes", "comprador"))
        and not wants_financial_return
        and not sales_customer_context
        and not is_ranking
        and not comparison_context
    )
    registry_request = any(
        term in query_norm
        for term in (
            "lista",
            "listar",
            "listagem",
            "todos",
            "todas",
            "cadastro",
            "cadastrado",
            "cadastrados",
            "dados",
            "telefone",
            "email",
            "endereco",
            "cidade",
            "bairro",
            "cpf",
            "cnpj",
            "codigo",
            "sku",
            "ean",
            "estoque",
        )
    )

    seller_context = any(
        term in query_norm
        for term in (
            "vendedor",
            "vendedores",
            "representante",
            "consultor",
            "quem vendeu mais",
            "quem vendeu menos",
            "quem mais vendeu",
            "quem menos vendeu",
            "quem mais vendeu",
            "quem faturou mais",
            "quem faturou menos",
            "lider em faturamento",
            "lider de vendas",
            "quem ficou em segundo",
            "bateu meta",
            "meta",
        )
    )
    product_context = any(term in query_norm for term in ("produto", "produtos", "item", "itens", "sku", "mercadoria", "mercadorias", "insumo", "insumos"))
    supplier_context = any(term in query_norm for term in ("fornecedor", "fornecedores"))
    city_analytics_context = (
        "cidade" in query_norm
        and (comparison_context or is_ranking or sales_customer_context or "faturamento" in query_norm or "receita" in query_norm)
    )
    pronoun_context = any(term in query_norm for term in ("dele", "dela", "deles", "delas", "destes", "dessas", "desses"))
    explicit_table_context = any(term in query_norm for term in ("troque para tabela", "em tabela", "tabela"))
    explicit_graph_context = any(term in query_norm for term in ("em grafico", "usar grafico", "usando grafico", "gráfico", "grafico"))
    field_projection_context = registry_request and not (
        seller_context or product_context or supplier_context or customer_registry_context or sales_customer_context
        or comparison_context or wants_financial_return
    )
    if field_projection_context:
        if "descricao" in query_norm or ("codigo" in query_norm and "telefone" not in query_norm):
            product_context = True
        elif "cidade" in query_norm:
            customer_registry_context = True
        elif "telefone" in query_norm or "fone" in query_norm:
            seller_context = True
    product_analytic_context = (
        (is_ranking or wants_financial_return or sales_customer_context or comparison_context or "comprar mais" in query_norm)
        and "estoque" not in query_norm
        and not ("cadastro" in query_norm or "cadastrado" in query_norm or "cadastrados" in query_norm)
    )

    generic_search_context = (
        query_norm.startswith("procure ")
        or query_norm.startswith("buscar ")
        or query_norm.startswith("busque ")
        or query_norm.startswith("encontre ")
    )

    if ("cidade" in query_norm and ("telefone" in query_norm or "fone" in query_norm) and "nome" in query_norm and not (seller_context or product_context or supplier_context)):
        entity = "CLIENTE"
        operation = "LISTAGEM"
        metrics = []
        group_by = []
        chart_type = "TABLE"
        date_range = ""
        view = _find_catalog_view_for_fallback(catalog, ["VW_CLIENTES_CAD_LM", "CLIENTES_CAD", "VW_CLIENTES_CADASTRADO", "CLIENTES_CADASTRADO", "CLIENTE"])
    elif ("codigo" in query_norm and "descri" in query_norm and not (seller_context or supplier_context or customer_registry_context)):
        entity = "PRODUTO"
        operation = "LISTAGEM"
        metrics = []
        group_by = []
        chart_type = "TABLE"
        date_range = ""
        view = _find_catalog_view_for_fallback(catalog, ["VW_PRODUTOS_CAD_LM", "PRODUTOS_CAD", "PRODUTO_CAD", "PRODUTO"])
    elif product_context and "sem venda" in query_norm:
        entity = "PRODUTO"
        operation = "LISTAGEM"
        metrics = []
        group_by = []
        chart_type = "TABLE"
        date_range = ""
        view = _find_catalog_view_for_fallback(catalog, ["VW_PRODUTOS_CAD_LM", "PRODUTOS_CAD", "PRODUTO_CAD", "PRODUTO"])
    elif explicit_table_context and not generic_search_context and not (is_ranking or seller_context or product_context or supplier_context or customer_registry_context):
        entity = "VENDA"
        operation = "DETALHAMENTO"
        metrics = ["receita_total"]
        group_by = []
        chart_type = "TABLE"
        view = _find_catalog_view_for_fallback(catalog, ["VW_VENDAS_LM", "VENDAS_CONTEXTO_GERAL", "DETALHE_PEDIDOS", "VENDAS_MENSAIS"])
    elif explicit_graph_context and not (seller_context or product_context or supplier_context or customer_registry_context):
        entity = "VENDEDOR"
        operation = "RANKING"
        metrics = ["receita_total"]
        group_by = ["vendedor_nome"]
        chart_type = "BAR"
        view = _find_catalog_view_for_fallback(catalog, ["VW_VENDAS_LM", "VW_PERFORMANCE_VENDEDORES", "PERFORMANCE_VENDEDORES", "VENDAS"])
    elif re.search(r"\be\s+[a-z]{3,}\??$", query_norm):
        entity = "VENDEDOR"
        operation = "LISTAGEM"
        metrics = []
        group_by = []
        chart_type = "TABLE"
        date_range = ""
        view = _find_catalog_view_for_fallback(catalog, ["VW_VENDEDOR_CAD_LM", "VENDEDOR_CAD", "VENDEDORES_CAD", "VENDEDOR"])
    elif pronoun_context and ("cliente" in query_norm or "clientes" in query_norm or "compraram" in query_norm or "comprou" in query_norm):
        entity = "CLIENTE"
        operation = "DETALHAMENTO"
        metrics = ["receita_total"]
        group_by = ["cliente_nome"]
        chart_type = "TABLE"
        view = _find_catalog_view_for_fallback(catalog, ["VW_VENDAS_LM", "VENDAS_CONTEXTO", "DETALHE_PEDIDOS", "VENDAS"])
    elif query_norm.startswith("agora apenas") and "cidade" in query_norm:
        entity = "CLIENTE"
        operation = "DETALHAMENTO"
        metrics = ["receita_total"]
        group_by = ["cliente_nome"]
        chart_type = "TABLE"
        view = _find_catalog_view_for_fallback(catalog, ["VW_VENDAS_LM", "VENDAS_CONTEXTO", "DETALHE_PEDIDOS", "VENDAS"])
    elif query_norm.startswith("ordene") and ("faturamento" in query_norm or "receita" in query_norm):
        entity = "CLIENTE"
        operation = "RANKING"
        metrics = ["receita_total"]
        group_by = ["cliente_nome"]
        chart_type = "BAR"
        view = _find_catalog_view_for_fallback(catalog, ["VW_VENDAS_LM", "VENDAS_CONTEXTO", "DETALHE_PEDIDOS", "VENDAS"])
    elif query_norm.startswith("como esta ") and not (seller_context or product_context or supplier_context or customer_registry_context):
        entity = "CIDADE"
        operation = "RANKING"
        metrics = ["receita_total"]
        group_by = ["cidade"]
        chart_type = "BAR"
        view = _find_catalog_view_for_fallback(catalog, ["VW_VENDAS_LM", "VENDAS_CONTEXTO", "DETALHE_PEDIDOS", "VENDAS"])
    elif stock_risk_context:
        entity = "PRODUTO"
        operation = "LISTAGEM"
        metrics = []
        group_by = []
        chart_type = "TABLE"
        date_range = ""
        view = _find_catalog_view_for_fallback(catalog, ["VW_PRODUTOS_CAD_LM", "PRODUTOS_CAD", "PRODUTO_CAD", "PRODUTO"])
    elif generic_search_context and not (seller_context or product_context or supplier_context or customer_registry_context):
        entity = "VENDEDOR"
        operation = "LISTAGEM"
        metrics = []
        group_by = []
        chart_type = "TABLE"
        date_range = ""
        view = _find_catalog_view_for_fallback(catalog, ["VW_VENDEDOR_CAD_LM", "VENDEDOR_CAD", "VENDEDORES_CAD", "VENDEDOR"])
    elif supplier_context and not (is_ranking or wants_financial_return or sales_customer_context or "compra" in query_norm or comparison_context):
        entity = "FORNECEDOR"
        operation = "LISTAGEM"
        metrics = []
        group_by = []
        chart_type = "TABLE"
        date_range = ""
        view = _find_catalog_view_for_fallback(catalog, ["VW_FORNECEDOR_CAD_LM", "FORNECEDOR_CAD", "FORNECEDORES_CAD", "FORNECEDOR"])
    elif supplier_context:
        entity = "FORNECEDOR"
        operation = "RANKING"
        metrics = ["receita_total"]
        group_by = ["fornecedor_nome"]
        if product_context:
            group_by.append("produto_nome")
        chart_type = "TABLE" if query_norm.startswith("liste") or "fornecedor dos produtos" in query_norm or "fornecedores dos produtos" in query_norm else "BAR"
        view = _find_catalog_view_for_fallback(catalog, ["VW_VENDAS_LM", "VENDAS", "DETALHE_PEDIDOS"])
    elif product_context and seller_context and product_analytic_context:
        entity = "PRODUTO"
        operation = "TENDENCIA" if comparison_context else "RANKING"
        metrics = ["unidades_vendidas", "receita_total"]
        group_by = ["produto_nome", "vendedor_nome"]
        chart_type = "LINE" if comparison_context else "BAR"
        view = _find_catalog_view_for_fallback(catalog, ["VW_VENDAS_LM", "VW_PRODUTOS_MAIS_VENDIDOS", "RANKING_PRODUTOS", "VENDAS"])
    elif seller_context and (registry_request or not (is_ranking or sales_customer_context or wants_financial_return or comparison_context or ticket_context or problem_or_recommendation_context or target_context)):
        entity = "VENDEDOR"
        operation = "LISTAGEM"
        metrics = []
        group_by = []
        chart_type = "TABLE"
        date_range = ""
        view = _find_catalog_view_for_fallback(catalog, ["VW_VENDEDOR_CAD_LM", "VENDEDOR_CAD", "VENDEDORES_CAD", "VENDEDOR"])
    elif product_context and (
        not product_analytic_context
        or (
            registry_request
            and not (
                is_ranking
                or sales_customer_context
                or comparison_context
                or wants_financial_return
                or margin_or_profit_context
                or "comprar mais" in query_norm
            )
        )
    ):
        entity = "PRODUTO"
        operation = "LISTAGEM"
        metrics = []
        group_by = []
        chart_type = "TABLE"
        date_range = ""
        view = _find_catalog_view_for_fallback(catalog, ["VW_PRODUTOS_CAD_LM", "PRODUTOS_CAD", "PRODUTO_CAD", "PRODUTO"])
    elif customer_count_sales_context:
        entity = "CLIENTE"
        operation = "TOTAL"
        metrics = ["clientes_distintos"]
        group_by = []
        chart_type = "KPI"
        view = _find_catalog_view_for_fallback(catalog, ["VW_VENDAS_LM", "VENDAS_CONTEXTO", "DETALHE_PEDIDOS", "VENDAS"])
    elif seller_context:
        entity = "VENDEDOR"
        operation = "TENDENCIA" if comparison_context else "RANKING" if is_ranking or problem_or_recommendation_context or target_context else "SOMA"
        metrics = ["ticket_medio"] if ticket_context else ["receita_total"]
        group_by = ["vendedor_nome"]
        chart_type = "TABLE" if target_context else "LINE" if comparison_context else "BAR"
        view = _find_catalog_view_for_fallback(catalog, ["VW_VENDAS_LM", "VW_PERFORMANCE_VENDEDORES", "PERFORMANCE_VENDEDORES", "VENDAS"])
    elif product_context:
        entity = "PRODUTO"
        operation = "TENDENCIA" if comparison_context else "RANKING" if is_ranking or wants_financial_return or "comprar mais" in query_norm else "SOMA"
        metrics = ["margem_lucro", "lucro_bruto", "receita_total"] if margin_or_profit_context else ["unidades_vendidas", "receita_total"]
        group_by = ["produto_nome"]
        if "cidade" in query_norm:
            group_by.append("cidade")
        if "vendedor" in query_norm or "representante" in query_norm:
            group_by.append("vendedor_nome")
        chart_type = "TABLE" if "sem venda" in query_norm else "LINE" if comparison_context else "BAR"
        view = _find_catalog_view_for_fallback(catalog, ["VW_VENDAS_LM", "VW_PRODUTOS_MAIS_VENDIDOS", "RANKING_PRODUTOS", "VENDAS"])
    elif customer_registry_context:
        entity = "CLIENTE"
        operation = "LISTAGEM"
        metrics = []
        group_by = []
        chart_type = "TABLE"
        date_range = ""
        view = _find_catalog_view_for_fallback(catalog, ["VW_CLIENTES_CAD_LM", "CLIENTES_CAD", "VW_CLIENTES_CADASTRADO", "CLIENTES_CADASTRADO", "CLIENTE"])
    elif any(term in query_norm for term in ("cliente", "clientes", "comprador")):
        entity = "CLIENTE"
        operation = "TENDENCIA" if comparison_context else "RANKING" if is_ranking else "SOMA"
        metrics = ["receita_total"]
        group_by = ["cidade"] if "cidade" in query_norm else ["cliente_nome"]
        customer_table_requested = (
            query_norm.startswith("liste")
            or "clientes que" in query_norm
            or "acima de" in query_norm
            or "ordenados" in query_norm
            or "sem compras" in query_norm
        )
        chart_type = "TABLE" if customer_table_requested else "LINE" if comparison_context else "BAR"
        view = _find_catalog_view_for_fallback(catalog, ["VW_VENDAS_LM", "VENDAS_CONTEXTO", "DETALHE_PEDIDOS", "VENDAS"])
    elif city_analytics_context:
        entity = "CIDADE"
        operation = "TENDENCIA" if comparison_context else "RANKING"
        metrics = ["receita_total"]
        group_by = ["cidade"]
        chart_type = "LINE" if comparison_context else "BAR"
        view = _find_catalog_view_for_fallback(catalog, ["VW_VENDAS_LM", "VENDAS_CONTEXTO", "DETALHE_PEDIDOS", "VENDAS"])
    elif comparison_context:
        entity = "VENDA"
        operation = "TENDENCIA"
        metrics = ["receita_total"]
        group_by = ["cidade"] if "cidade" in query_norm else ["mes"]
        chart_type = "LINE"
        view = _find_catalog_view_for_fallback(catalog, ["VW_VENDAS_LM", "VENDAS_CONTEXTO_GERAL", "DETALHE_PEDIDOS", "VENDAS_MENSAIS"])
    elif quantity_sales_context:
        entity = "VENDA"
        operation = "TOTAL"
        metrics = ["quantidade_pedidos"]
        group_by = []
        chart_type = "KPI"
        view = _find_catalog_view_for_fallback(catalog, ["VW_VENDAS_LM", "VENDAS_CONTEXTO_GERAL", "DETALHE_PEDIDOS", "VENDAS_MENSAIS"])
    elif re.search(r"\b(?:maior|menor)\s+venda\b", query_norm):
        entity = "VENDA"
        operation = "MAXIMO" if "maior" in query_norm else "MINIMO"
        metrics = ["receita_total"]
        group_by = []
        chart_type = "KPI"
        view = _find_catalog_view_for_fallback(catalog, ["VW_VENDAS_LM", "VENDAS_CONTEXTO_GERAL", "DETALHE_PEDIDOS", "VENDAS_MENSAIS"])
    elif ticket_context:
        entity = "TICKET"
        operation = "MEDIA"
        metrics = ["ticket_medio"]
        group_by = []
        chart_type = "KPI"
        view = _find_catalog_view_for_fallback(catalog, ["VW_VENDAS_LM", "VENDAS_CONTEXTO_GERAL", "DETALHE_PEDIDOS", "VENDAS_MENSAIS"])
    elif pure_problem_context:
        entity = "VENDA"
        operation = "DETALHAMENTO"
        metrics = ["receita_total"]
        group_by = []
        chart_type = "TABLE"
        view = _find_catalog_view_for_fallback(catalog, ["VW_VENDAS_LM", "VENDAS_CONTEXTO_GERAL", "DETALHE_PEDIDOS", "VENDAS_MENSAIS"])
    elif is_ranking or problem_or_recommendation_context:
        entity = "VENDEDOR"
        operation = "RANKING"
        metrics = ["receita_total"]
        group_by = ["vendedor_nome"]
        chart_type = "BAR"
        view = _find_catalog_view_for_fallback(catalog, ["VW_VENDAS_LM", "VW_PERFORMANCE_VENDEDORES", "PERFORMANCE_VENDEDORES", "VENDAS"])
    else:
        entity = "VENDA"
        operation = "SOMA"
        metrics = ["receita_total"]
        group_by = []
        chart_type = "KPI"
        view = _find_catalog_view_for_fallback(catalog, ["VW_VENDAS_LM", "VENDAS_CONTEXTO_GERAL", "DETALHE_PEDIDOS", "VENDAS_MENSAIS"])

    plan = StructuredPlanSchema(
        request_id=request_id or str(uuid.uuid4()),
        intent=pergunta[:120] or "consulta corporativa",
        query_type="RANKING" if operation == "RANKING" else "SELECT",
        metrics=metrics,
        group_by=group_by,
        filters=PlanFiltersSchema(date_range=date_range),
        visualization=PlanVisualizationSchema(type=chart_type, layout_priority="ALTA"),
        requires_insight=True,
        confidence_score=0.72,
    )

    params: dict[str, str] = {}
    if date_range:
        params["date_range"] = date_range
    if limit:
        params["limite"] = str(limit)
    if operation in {"LISTAGEM", "DETALHAMENTO"} and (
        entity in {"CLIENTE", "VENDEDOR", "PRODUTO"} or entity == "FORNECEDOR"
    ):
        params.update(_extract_entity_registry_params_for_fallback(query_norm, entity))
    if entity == "CLIENTE" and "sem compras" in query_norm:
        params["_anti_join_sales"] = "clientes_sem_compras"
    if entity == "PRODUTO" and "sem venda" in query_norm:
        params["_anti_join_sales"] = "produtos_sem_venda"
    if entity == "PRODUTO" and margin_or_profit_context:
        order_metric = "margem_lucro" if "margem" in query_norm or "rentabilidade" in query_norm else "lucro_bruto"
        params["_order_metric"] = order_metric
        params["_order_direction"] = "ASC" if lowest_context else "DESC"
        if not limit and re.search(r"\bqual\s+(?:o\s+)?(?:produto|item|sku|mercadoria|insumo)\b", query_norm):
            params["limite"] = "1"
            limit = 1
            plan.filters.date_range = plan.filters.date_range or date_range

    return IntentionResponse(
        view_catalog_id=getattr(view, "id", None),
        confianca=0.72,
        parametros=params,
        justificativa=(
            "Fallback determinístico acionado porque o provedor de IA não respondeu corretamente. "
            "A intenção foi inferida por semântica local controlada."
        ),
        chart_type_sobrescrever=chart_type,
        chart_types_solicitados=[chart_type, "TABLE"],
        plano_estruturado=plan,
        operacao=operation,
        entidade_alvo=entity,
        quantidade_limite=limit,
        periodo_referencia=date_range,
        nivel_confianca="MEDIA",
        telemetry={"fallback": "deterministic_intent", "reason": reason},
    )


def validate_authorized_model(model: str | None) -> str:
    """Compatibility wrapper: model governance belongs to AICM."""
    return ai_credential_manager.validate_authorized_model(model)


def _get_openai_client() -> AsyncOpenAI:
    raise AIServiceError("Clientes de IA devem ser resolvidos exclusivamente pelo AI Credential Manager.")


async def _get_tenant_openai_client(api_key: str, tenant_id: uuid.UUID | str) -> AsyncOpenAI:
    lease = await ai_credential_manager.resolve_client(
        tenant_id=tenant_id,
        explicit_api_key=api_key,
        purpose="compatibility_tenant_client",
    )
    return lease.client


async def close_tenant_openai_client(tenant_id: uuid.UUID | str) -> None:
    await ai_credential_manager.invalidate_tenant(tenant_id)

# Funções da Ponte ──────────────────────────────────────────────────────────

async def identify_intention(
    pergunta: str,
    catalog: list[ViewCatalogSummary],
    api_key: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    custom_instructions: str | None = None,
    tenant_id: uuid.UUID | str | None = None,
    history: list[dict[str, str]] | None = None,
    request_id: str | None = None,
    user_id: uuid.UUID | str | None = None,
    session_id: str | None = None,
) -> list[IntentionResponse]:
    """v4.0: Encaminha NLU ao CIE usando exclusivamente o AI Credential Manager."""
    from services.ai.corporate_intelligence_engine import corporate_intelligence_engine
    from database import get_db_context
    import uuid as _uuid

    pergunta = validate_user_query(pergunta)
    history = sanitize_history(history)
    target_model = validate_authorized_model(model)
    _ = temperature

    if not catalog:
        return [IntentionResponse(
            view_catalog_id=None,
            confianca=0.0,
            parametros={},
            justificativa="Catalogo do tenant vazio.",
        )]

    explicit_api_key = str(api_key).strip() if api_key and not _is_probably_invalid_openai_key(api_key) else None
    tenant_uuid = _uuid.UUID(str(tenant_id)) if tenant_id else _uuid.uuid4()
    credential_tenant_id = tenant_uuid if tenant_id else None
    user_uuid = _uuid.UUID(str(user_id)) if user_id else None

    async def _run_cie(
        selected_client: AsyncOpenAI,
        resolved_model: str,
        _lease: Any,
    ) -> list[IntentionResponse]:
        async with get_db_context() as db:
            return await corporate_intelligence_engine.identify_intention(
                pergunta=pergunta,
                catalog=catalog,
                client=selected_client,
                target_model=resolved_model,
                db=db,
                tenant_id=tenant_uuid,
                history=history,
                custom_instructions=custom_instructions,
                request_id=request_id,
                user_id=user_uuid,
                session_id=session_id,
            )

    try:
        async with get_db_context() as credential_db:
            return await ai_invocation_manager.invoke(
                tenant_id=credential_tenant_id,
                db=credential_db,
                explicit_api_key=explicit_api_key,
                requested_model=target_model,
                purpose="intent_detection",
                context={
                    "query": pergunta,
                    "fresh_data_required": True,
                    "requires_precision": True,
                    "history_size": len(history or []),
                    "catalog_size": len(catalog),
                    "request_id": request_id,
                },
                force_ai=True,
                allow_response_reuse=False,
                operation=_run_cie,
            )
    except AICMError as exc:
        logger.warning("[AIService] IA indisponivel via AICM: %s", exc)
        raise AIServiceError(exc.user_message) from exc

async def generate_data_insights(
    pergunta: str,
    dados: list[dict[str, Any]] | dict[str, Any],
    view_name: str,
    api_key: str | None = None,
    model: str | None = None,
    tenant_id: uuid.UUID | str | None = None,
    history: list[dict[str, str]] | None = None,
    custom_instructions: str | None = None,
    mode: str = "analytical",
) -> str:
    """v4.0: Gera insights naturais usando exclusivamente o AI Credential Manager."""
    from services.ai.corporate_intelligence_engine import corporate_intelligence_engine
    from database import get_db_context

    pergunta = validate_user_query(pergunta)
    history = sanitize_history(history)
    target_model = validate_authorized_model(model)
    explicit_api_key = str(api_key).strip() if api_key and not _is_probably_invalid_openai_key(api_key) else None
    tenant_uuid = uuid.UUID(str(tenant_id)) if tenant_id else uuid.uuid4()
    credential_tenant_id = tenant_uuid if tenant_id else None

    async def _run_insights(
        selected_client: AsyncOpenAI,
        resolved_model: str,
        _lease: Any,
    ) -> str:
        return await corporate_intelligence_engine.generate_data_insights(
            pergunta=pergunta,
            dados=dados,
            view_name=view_name,
            client=selected_client,
            target_model=resolved_model,
            history=history,
            custom_instructions=custom_instructions,
            mode=mode,
        )

    try:
        async with get_db_context() as credential_db:
            return await ai_invocation_manager.invoke(
                tenant_id=credential_tenant_id,
                db=credential_db,
                explicit_api_key=explicit_api_key,
                requested_model=target_model,
                purpose="data_insights",
                context={
                    "query": pergunta,
                    "fresh_data_required": True,
                    "requires_precision": mode in {"executive", "analytical"},
                    "data_shape": {
                        "type": type(dados).__name__,
                        "rows": len(dados) if isinstance(dados, list) else len(dados.keys()) if isinstance(dados, dict) else 0,
                        "view_name": view_name,
                    },
                },
                force_ai=False,
                allow_response_reuse=False,
                operation=_run_insights,
            )
    except AICMError as exc:
        logger.warning("[AIService] Insights IA indisponiveis via AICM: %s", exc)
        raise AIServiceError(exc.user_message) from exc

def detect_user_session_profile(history: list[dict[str, str]] | None) -> str:
    """Ponte de compatibilidade para obter o perfil de memória da sessão."""
    from services.ai.memory_context_engine import memory_context_engine
    from services.ai.schemas import CIEContextSchema
    import uuid as _uuid
    ctx = CIEContextSchema(tenant_id=_uuid.uuid4(), historico_recente=history or [])
    return memory_context_engine.analyze_session_history(ctx)


_CATALOG_ITEM_TEMPLATE: Final[str] = (
    "  ▸ ID: {view_id}\n"
    "    Análise: {nome_view}\n"
    "    Tipo de Visualização Padrão: {tipo_grafico}\n"
    "    Descrição Semântica: {descricao}\n"
    "    Parâmetros Declarados (apenas estes são válidos se não for livre): {parametros}\n"
)

_SYSTEM_PROMPT_TEMPLATE: Final[str] = (
    "Você é o Motor de NLU do LuminaAI.\n\n"
    "## CATÁLOGO DE ANÁLISES DISPONÍVEIS:\n"
    "{catalog_block}"
)


def _build_system_prompt(
    catalog: list[ViewCatalogSummary],
    custom_instructions: str | None = None,
) -> str:
    """
    Constrói o prompt de sistema com o catálogo do tenant injetado dinamicamente.
    """
    catalog_block = "\n".join(
        _CATALOG_ITEM_TEMPLATE.format(
            view_id=str(view.id),
            nome_view=view.nome_view_oracle,
            tipo_grafico=view.tipo_grafico_padrao.value if hasattr(view.tipo_grafico_padrao, 'value') else view.tipo_grafico_padrao,
            descricao=view.descricao_para_ia,
            parametros=list(view.parametros_schema.keys()) if view.parametros_schema else "LIVRE (qualquer parâmetro é válido)",
        )
        for view in catalog
    )
    prompt = _SYSTEM_PROMPT_TEMPLATE.format(catalog_block=catalog_block)
    if custom_instructions:
        prompt += f"\n\n## DIRETRIZES ADICIONAIS DO CLIENTE:\n{custom_instructions}"
    return prompt
