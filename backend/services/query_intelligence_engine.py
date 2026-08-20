"""
LuminaAI â€” Query Intelligence Engine (QIE) (v5.9)
-------------------------------------------------
Este serviÃ§o gerencia o ciclo de vida dos Blueprints de consulta.
Seu objetivo Ã© evitar chamadas repetitivas de IA calculando similaridade semÃ¢ntica
entre novas perguntas e blueprints de consultas anteriores.
"""
from __future__ import annotations

import os
import re
import json
import uuid
import logging
import datetime
import calendar
import copy
from threading import RLock
from typing import Any, Final
from pydantic import BaseModel, Field

from services.plan_validator import normalize_text_key, resolve_relative_date_range
from services.blueprint_storage import (
    OFFICIAL_BLUEPRINT_PATH,
    BlueprintJsonRepository,
    BlueprintRepositoryFactory,
)

logger = logging.getLogger("luminaai.services.query_intelligence_engine")

# Caminho fÃ­sico do repositÃ³rio de Blueprints
# Fica em services/blueprints.json para evitar conflito com o mÃ³dulo database.py
REPOSITORY_PATH: Final[str] = str(OFFICIAL_BLUEPRINT_PATH)

BLUEPRINT_DIRECT_REUSE_THRESHOLD: Final[float] = 0.98
PACKAGE_PRE_NLU_REUSE_THRESHOLD: Final[float] = 0.99
_NON_REUSABLE_BLUEPRINT_MARKERS: Final[tuple[str, ...]] = (
    "blueprint reutilizado",
    "fallback determin",
    "provedor de ia",
    "nao respondeu",
    "nÃ£o respondeu",
    "baixa confianca",
    "baixa confianÃ§a",
    "consulta customizada",
)
_FRESH_AI_QUERY_MARKERS: Final[tuple[str, ...]] = (
    "percentual",
    "porcentagem",
    "quanto por cento",
    "a mais",
    "a menos",
    "diferenca",
    "diferenÃ§a",
    "comparar",
    "comparacao",
    "comparaÃ§Ã£o",
    "versus",
    " vs ",
    "primeiro",
    "segundo",
    "terceiro",
    "assim por diante",
    "retorno financeiro",
    "resultado financeiro",
    "margem",
    "lucro",
    "rentabilidade",
    "rentavel",
    "rentaveis",
    "lucratividade",
    "lucrativo",
    "lucrativos",
    "menor",
    "pior",
    "mais baixo",
    "mais baixa",
)
_NULL_LIKE_PARAM_VALUES: Final[set[str]] = {"", "none", "null", "undefined", "nan"}
_CITY_FALLBACK_STOP_TERMS: Final[set[str]] = {
    "aberto",
    "abertos",
    "ativo",
    "ativos",
    "geral",
    "todos",
    "todas",
    "janeiro",
    "fevereiro",
    "marco",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
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
_PURCHASE_CONTEXT_TERMS: Final[tuple[str, ...]] = (
    "compra",
    "compras",
    "comprado",
    "comprados",
    "fornecimento",
    "fornecimentos",
)
_SELLER_CONTEXT_TERMS: Final[tuple[str, ...]] = (
    "vendedor",
    "vendedores",
    "representante",
    "representantes",
    "consultor",
    "consultores",
)
_PRODUCT_CONTEXT_TERMS: Final[tuple[str, ...]] = (
    "produto",
    "produtos",
    "item",
    "itens",
    "sku",
    "mercadoria",
    "mercadorias",
    "insumo",
    "insumos",
)
_SUPPLIER_CONTEXT_TERMS: Final[tuple[str, ...]] = (
    "fornecedor",
    "fornecedores",
)
_CUSTOMER_CONTEXT_TERMS: Final[tuple[str, ...]] = (
    "cliente",
    "clientes",
    "comprador",
    "compradores",
)
_REGISTRY_REQUEST_TERMS: Final[tuple[str, ...]] = (
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
    "fone",
    "celular",
    "email",
    "endereco",
    "cidade",
    "municipio",
    "bairro",
    "uf",
    "estado",
    "cpf",
    "cnpj",
    "documento",
    "codigo",
    "sku",
    "ean",
    "estoque",
)
_RANKING_OR_ANALYTIC_TERMS: Final[tuple[str, ...]] = (
    "ranking",
    "top",
    "maior",
    "menor",
    "melhor",
    "pior",
    "mais vendido",
    "mais vendidos",
    "quem vendeu",
    "quem faturou",
    "faturamento",
    "receita",
    "retorno financeiro",
    "rentabilidade",
    "lucro",
    "margem",
    "comparar",
    "comparacao",
)
_CUSTOMER_NAME_STOP_TERMS: Final[set[str]] = {
    "cidade",
    "municipio",
    "bairro",
    "estado",
    "uf",
    "cpf",
    "cnpj",
    "documento",
    "email",
    "telefone",
    "fone",
    "celular",
    "endereco",
    "cep",
    "classe",
    "praca",
    "cadastro",
    "cadastrado",
    "cadastrados",
    "com",
    "por",
    "para",
    "reside",
    "residem",
    "mora",
    "moram",
    "todos",
    "todas",
}


def _catalog_names(catalog: list[Any]) -> list[str]:
    return [str(getattr(view, "nome_view_oracle", "") or "").upper() for view in catalog]


def _catalog_has_family(catalog: list[Any], keywords: tuple[str, ...]) -> bool:
    names = _catalog_names(catalog)
    return any(any(keyword in name for keyword in keywords) for name in names)


def _catalog_gap_for_query(query_text: str, catalog: list[Any]) -> tuple[str, str] | None:
    """Detecta quando a pergunta exige uma família de view que não existe no catálogo ativo."""
    normalized = normalize_text_key(query_text or "")
    names = _catalog_names(catalog)

    if not names:
        return ("catalogo", "Nenhuma view ativa foi encontrada no catálogo desta empresa.")

    requested: tuple[str, tuple[str, ...], str] | None = None
    asks_sales = any(term in normalized for term in _SALES_CONTEXT_TERMS)
    asks_purchase = any(term in normalized for term in _PURCHASE_CONTEXT_TERMS)
    asks_analytic = any(term in normalized for term in _RANKING_OR_ANALYTIC_TERMS)

    if any(term in normalized for term in _SELLER_CONTEXT_TERMS):
        if asks_sales or asks_analytic:
            requested = (
                "vendedores",
                ("PERFORMANCE_VENDEDORES", "FATURAMENTO", "VENDAS", "DETALHE_PEDIDOS"),
                "performance/vendas de vendedores",
            )
        else:
            requested = ("vendedores_cadastro", ("VENDEDOR_CAD", "VENDEDORES_CAD"), "cadastro de vendedores")
    elif any(term in normalized for term in _PRODUCT_CONTEXT_TERMS):
        product_inventory_request = "estoque" in normalized and not asks_sales
        if (asks_sales or asks_analytic) and not product_inventory_request:
            requested = (
                "produtos",
                ("PRODUTOS_MAIS_VENDIDOS", "RANKING_PRODUTOS", "FATURAMENTO_PRODUTOS", "DETALHE_PEDIDOS", "VENDAS"),
                "vendas/ranking de produtos",
            )
        else:
            requested = ("produtos_cadastro", ("PRODUTOS_CAD", "PRODUTO_CAD"), "cadastro de produtos")
    elif any(term in normalized for term in _SUPPLIER_CONTEXT_TERMS):
        if asks_purchase:
            requested = (
                "fornecedores_analitico",
                ("COMPRA_FORNECEDOR", "FORNECEDOR_ANALITICO", "DRE_FIN_APL_FORNEC"),
                "compras/desempenho de fornecedores",
            )
        elif asks_sales or asks_analytic:
            requested = (
                "fornecedores_indireto_vendas",
                ("VW_VENDAS_LM", "VENDAS", "PRODUTOS_CAD", "FORNECEDOR_CAD"),
                "faturamento indireto de fornecedores via produtos vendidos",
            )
        else:
            requested = ("fornecedores_cadastro", ("FORNECEDOR_CAD", "FORNECEDORES_CAD"), "cadastro de fornecedores")
    elif any(term in normalized for term in _CUSTOMER_CONTEXT_TERMS):
        asks_sales_customer = asks_sales or any(
            term in normalized for term in ("ranking", "top", "mais compr", "maior compra", "fatur")
        )
        if asks_sales_customer:
            requested = ("clientes_analitico", ("VW_VENDAS_LM", "DETALHE_PEDIDOS", "VENDAS_CONTEXTO", "CLIENTES_HISTORICO", "VENDAS"), "vendas por cliente")
        else:
            requested = ("clientes_cadastro", ("CLIENTES_CAD", "CLIENTES_CADASTRADO", "CLIENTE"), "cadastro de clientes")
    elif asks_sales:
        requested = ("vendas", ("VENDAS", "FATURAMENTO", "DETALHE_PEDIDOS"), "vendas/faturamento")

    if not requested:
        return None

    code, keywords, label = requested
    if _catalog_has_family(catalog, keywords):
        return None

    available = ", ".join(names) or "nenhuma view ativa"
    message = (
        f"A pergunta exige uma view de {label}, mas o catálogo ativo atual possui apenas: {available}. "
        "Cadastre e sincronize a view correspondente antes de executar essa análise."
    )
    return code, message

# Lock global para operaÃ§Ãµes de I/O thread-safe
_io_lock = RLock()


def _requires_fresh_ai_interpretation(query_text: str) -> bool:
    """Queries with comparisons or fuzzy business intent must not bypass NLU."""
    normalized = normalize_text_key(query_text or "")
    if "%" in (query_text or ""):
        return True
    return any(marker in normalized for marker in _FRESH_AI_QUERY_MARKERS)


def _is_reusable_blueprint_candidate(blueprint: "BlueprintModel") -> bool:
    """Only clean, approved/starter-like blueprints may short-circuit the NLU."""
    control_fields = {
        "tenant_id",
        "limite",
        "limit",
        "row_limit",
        "page",
        "pagina",
        "offset",
        "per_page",
        "data_inicio",
        "data_fim",
        "date_range",
        "products",
        "customers",
        "regions",
        "_metrics",
        "_group_by",
        "_order_metric",
        "_order_direction",
    }
    haystack = normalize_text_key(
        " ".join(
            str(part or "")
            for part in (
                blueprint.id,
                blueprint.intent_id,
                blueprint.nome_consulta,
                blueprint.objetivo,
                blueprint.view_name,
                blueprint.versionamento.autor if blueprint.versionamento else "",
            )
        )
    )
    if any(marker in haystack for marker in _NON_REUSABLE_BLUEPRINT_MARKERS):
        return False
    if not blueprint.exemplos_perguntas:
        return False
    if blueprint.view_catalog_id in ("unknown_catalog", "", None):
        return False
    view_name = str(blueprint.view_name or "").strip()
    if not view_name or len(view_name) > 96 or not re.fullmatch(r"[A-Za-z0-9_.]+", view_name):
        return False

    for collection in (blueprint.metrics or [], blueprint.group_by or []):
        for value in collection:
            clean_value = normalize_text_key(str(value or "")).strip()
            if not clean_value or clean_value in control_fields or clean_value.startswith("_"):
                return False

    return True


def _entity_from_blueprint(blueprint: "BlueprintModel") -> str:
    content = normalize_text_key(
        " ".join([blueprint.view_name or "", " ".join(blueprint.group_by or []), blueprint.nome_consulta or ""])
    )
    if "produto" in content:
        return "PRODUTO"
    if "vendedor" in content:
        return "VENDEDOR"
    if "cliente" in content:
        return "CLIENTE"
    if "estoque" in content:
        return "ESTOQUE"
    return "VENDA"


def _resolve_blueprint_catalog_view(blueprint: "BlueprintModel", catalog: list[Any]) -> Any | None:
    """Map legacy/dummy blueprint view ids to the current tenant catalog."""
    if not catalog:
        return None

    for view in catalog:
        if str(getattr(view, "id", "")) == str(blueprint.view_catalog_id or ""):
            return view

    blueprint_view = (blueprint.view_name or "").upper()
    for view in catalog:
        if getattr(view, "nome_view_oracle", "").upper() == blueprint_view:
            return view

    entity = _entity_from_blueprint(blueprint)
    blueprint_text = normalize_text_key(
        " ".join(
            str(part or "")
            for part in (
                blueprint.intent_id,
                blueprint.nome_consulta,
                blueprint.objetivo,
                blueprint.view_name,
                " ".join(blueprint.exemplos_perguntas or []),
            )
        )
    )
    if blueprint.intent_id == "daily_sales":
        preferred = ("VW_VENDAS_LM", "VW_VENDAS_CONTEXTO_GERAL", "VW_DETALHE_PEDIDOS", "VW_VENDAS_MENSAIS", "VW_VENDAS")
    elif entity == "PRODUTO":
        preferred = ("VW_VENDAS_LM", "VW_PRODUTOS_MAIS_VENDIDOS", "VW_RANKING_PRODUTOS", "VW_FATURAMENTO_PRODUTOS")
    elif entity == "VENDEDOR":
        preferred = ("VW_VENDAS_LM", "VW_PERFORMANCE_VENDEDORES", "VW_FATURAMENTO_MENSAL", "VW_VENDAS_MENSAIS")
    elif entity == "CLIENTE":
        if any(term in blueprint_text for term in ("cadastro", "cadastrado", "cadastrados", "lista", "listar", "listagem")):
            preferred = ("VW_CLIENTES_CAD_LM", "VW_CLIENTES_CADASTRADO", "VW_CLIENTES_HISTORICO")
        else:
            preferred = ("VW_VENDAS_LM", "VW_CLIENTES_HISTORICO", "VW_VENDAS_CONTEXTO_GERAL", "VW_DETALHE_PEDIDOS", "VW_CLIENTES_CAD_LM")
    else:
        preferred = ("VW_VENDAS_LM", "VW_VENDAS_CONTEXTO_GERAL", "VW_VENDAS_MENSAIS", "VW_DETALHE_PEDIDOS")

    for name in preferred:
        for view in catalog:
            if getattr(view, "nome_view_oracle", "").upper() == name:
                return view

    return None


def _extract_explicit_row_limit(query_text: str) -> int | None:
    """Extract an explicit Top N/row limit from the current user query."""
    query_norm = normalize_text_key(query_text or "")
    patterns = (
        r"\b(?:top|ranking|primeir[oa]s?)\s+(\d{1,3})\b",
        r"\b(\d{1,3})\s+(?:maiores|melhores|piores|mais vendidos|mais vendidas|vendedores|produtos|clientes)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, query_norm)
        if match:
            try:
                limit = int(match.group(1))
            except (TypeError, ValueError):
                continue
            if 1 <= limit <= 500:
                return limit
    return None


def _apply_explicit_row_limit(intentions: list[Any], limit: int | None) -> None:
    """Keep the current query limit even when a reusable blueprint is selected."""
    if not limit:
        return
    for intention in intentions:
        if getattr(intention, "fora_de_escopo", False) or getattr(intention, "resposta_direta", None):
            continue
        intention.quantidade_limite = limit
        params = dict(getattr(intention, "parametros", {}) or {})
        params["limite"] = str(limit)
        intention.parametros = params


def _sanitize_intention_params(intentions: list[Any]) -> None:
    """Drop null-like values produced by LLMs or legacy compatibility paths."""
    for intention in intentions:
        params = dict(getattr(intention, "parametros", {}) or {})
        cleaned: dict[str, str] = {}
        for key, value in params.items():
            if value is None:
                continue
            str_value = str(value).strip()
            if str_value.lower() in _NULL_LIKE_PARAM_VALUES:
                continue
            cleaned[str(key)] = str_value
        intention.parametros = cleaned


def _safe_int(value: Any) -> int | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _month_range_from_params(params: dict[str, Any]) -> tuple[str, str] | None:
    """Resolve legacy ano/mes params into an authoritative full-month range."""
    year = _safe_int(params.get("ano") or params.get("year"))
    month = _safe_int(params.get("mes") or params.get("month"))
    if not year or not month or month < 1 or month > 12:
        return None
    start = datetime.date(year, month, 1)
    end = datetime.date(year, month, calendar.monthrange(year, month)[1])
    return start.isoformat(), end.isoformat()


def _is_full_month_range(start_iso: str, end_iso: str) -> bool:
    try:
        start = datetime.date.fromisoformat(start_iso)
        end = datetime.date.fromisoformat(end_iso)
    except ValueError:
        return False
    expected_end = datetime.date(start.year, start.month, calendar.monthrange(start.year, start.month)[1])
    return start.day == 1 and end == expected_end


def _apply_temporal_range_to_intention(intention: Any, date_range: tuple[str, str]) -> None:
    """Keep params, structured plan and memory period synchronized."""
    start_iso, end_iso = date_range
    range_text = f"{start_iso} to {end_iso}"
    params = dict(getattr(intention, "parametros", {}) or {})
    params["date_range"] = range_text
    params["data_inicio"] = start_iso
    params["data_fim"] = end_iso

    if _is_full_month_range(start_iso, end_iso):
        start = datetime.date.fromisoformat(start_iso)
        params["ano"] = str(start.year)
        params["mes"] = f"{start.month:02d}"

    intention.parametros = params
    if hasattr(intention, "periodo_referencia"):
        intention.periodo_referencia = range_text

    structured_plan = getattr(intention, "plano_estruturado", None)
    filters = getattr(structured_plan, "filters", None) if structured_plan else None
    if filters is not None:
        filters.date_range = range_text


def _sync_temporal_params(intentions: list[Any], query_text: str) -> None:
    """
    Normalize temporal filters across QIE/Planner/Validator boundaries.

    Precedence:
    1. Explicit date/month in the user's question.
    2. Legacy ano/mes params produced by NLU.
    3. Existing params date_range.
    4. Structured plan date_range.
    """
    query_range = resolve_relative_date_range(query_text)
    for intention in intentions:
        if getattr(intention, "fora_de_escopo", False) or getattr(intention, "resposta_direta", None):
            continue

        params = dict(getattr(intention, "parametros", {}) or {})
        params_range = _month_range_from_params(params)
        date_range_value = str(params.get("date_range") or "")
        date_range_from_params = resolve_relative_date_range(date_range_value) if date_range_value else None

        plan_range = None
        structured_plan = getattr(intention, "plano_estruturado", None)
        filters = getattr(structured_plan, "filters", None) if structured_plan else None
        plan_date_range = str(getattr(filters, "date_range", "") or "") if filters else ""
        if plan_date_range:
            plan_range = resolve_relative_date_range(plan_date_range)

        chosen_range = query_range or params_range or date_range_from_params or plan_range
        if chosen_range:
            _apply_temporal_range_to_intention(intention, chosen_range)


def _extract_city_from_query(query_text: str) -> str | None:
    """Extract explicit city filters such as 'cidade de Ataleia' from user text."""
    normalized = normalize_text_key(query_text or "")
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    normalized = " ".join(normalized.split())
    city_stop = r"(?:e|com|que|onde|bairro|estado|uf|telefone|fone|celular|email|cep|classe|praca|vendedor|produto)"
    patterns = (
        rf"\bcidade\s+de\s+([a-z0-9\s]+?)(?:\s+{city_stop}\b|\s+(?:no|na)\s+(?:bairro|estado|uf)\b|$)",
        rf"\bcidade\s+([a-z0-9\s]+?)(?:\s+{city_stop}\b|\s+(?:no|na)\s+(?:bairro|estado|uf)\b|$)",
        rf"\bmunicipio\s+de\s+([a-z0-9\s]+?)(?:\s+{city_stop}\b|\s+(?:no|na)\s+(?:bairro|estado|uf)\b|$)",
        rf"\bmunicipio\s+([a-z0-9\s]+?)(?:\s+{city_stop}\b|\s+(?:no|na)\s+(?:bairro|estado|uf)\b|$)",
        rf"\b(?:reside|residem|residente|residentes|mora|moram)\s+(?:em|na|no)\s+([a-z0-9\s]+?)(?:\s+{city_stop}\b|\s+(?:no|na)\s+(?:bairro|estado|uf)\b|$)",
        rf"\bclientes?\s+(?:de|do|da|dos|das)\s+([a-z0-9\s]+?)(?:\s+{city_stop}\b|\s+(?:no|na)\s+(?:bairro|estado|uf)\b|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            city = " ".join(match.group(1).split()).strip()
            first_token = city.split()[0] if city else ""
            if city and first_token not in _CITY_FALLBACK_STOP_TERMS and city not in _CITY_FALLBACK_STOP_TERMS:
                return city

    is_customer_registry_query = (
        any(term in normalized for term in ("cliente", "clientes", "cadastro", "cadastrado", "cadastrados"))
        and not any(term in normalized for term in _SALES_CONTEXT_TERMS)
    )
    if is_customer_registry_query:
        match = re.search(r"\b(?:em|na|no)\s+([a-z][a-z0-9\s]{2,})$", normalized)
        if match:
            city = " ".join(match.group(1).split()).strip()
            if city and not any(ch.isdigit() for ch in city) and city not in _CITY_FALLBACK_STOP_TERMS:
                return city
    return None


def _first_clean_match(normalized: str, patterns: tuple[str, ...]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            value = " ".join(match.group(1).split()).strip()
            if value:
                return value
    return None


def _extract_customer_registry_params(query_text: str) -> dict[str, str]:
    """Extrai filtros cadastrais comuns sem depender da IA."""
    normalized = normalize_text_key(query_text or "")
    normalized_plain = re.sub(r"[^a-z0-9\s]", " ", normalized)
    normalized_plain = " ".join(normalized_plain.split())
    params: dict[str, str] = {}

    city = _extract_city_from_query(query_text)
    if city:
        params["cidade"] = city

    doc_match = re.search(r"\b(?:cpf|cnpj|documento|cpf\s*cnpj)\s*(?:do|da|de|n[ou]mero|numero)?\s*([0-9.\-\/]{5,})", normalized)
    if doc_match:
        params["documento"] = re.sub(r"\D+", "", doc_match.group(1)) or doc_match.group(1).strip()

    email_match = re.search(r"\b([a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,})\b", normalized)
    if email_match:
        params["email"] = email_match.group(1)

    phone_match = re.search(r"\b(?:telefone|fone|celular|whatsapp)\s*(?:do|da|de)?\s*([0-9()\s.\-+]{8,})", normalized)
    if phone_match:
        params["telefone"] = re.sub(r"\D+", "", phone_match.group(1)) or phone_match.group(1).strip()

    state = _first_clean_match(
        normalized_plain,
        (
            r"\b(?:uf|estado)\s+(?:de|do|da)?\s*([a-z]{2,20})(?:\s+(?:e|com|que|onde|telefone|fone|celular|email|cidade|municipio|bairro|cep|classe|praca)\b|$)",
            r"\b(?:no|na|do|da)\s+estado\s+de\s+([a-z]{2,20})(?:\s+(?:e|com|que|onde|telefone|fone|celular|email|cidade|municipio|bairro|cep|classe|praca)\b|$)",
        ),
    )
    if state:
        params["uf" if len(state) == 2 else "estado"] = state

    for key, patterns in {
        "bairro": (
            r"\bbairro\s+(?:de|do|da)?\s*([a-z0-9\s]+?)(?:\s+(?:e|com|que|onde|cidade|municipio|estado|uf)\b|\s+(?:no|na|de|do|da)\s+(?:cidade|municipio|estado|uf)\b|$)",
            r"\b(?:no|na)\s+bairro\s+([a-z0-9\s]+?)(?:\s+(?:e|com|que|onde|cidade|municipio|estado|uf)\b|\s+(?:no|na|de|do|da)\s+(?:cidade|municipio|estado|uf)\b|$)",
        ),
        "praca": (
            r"\bpraca\s+(?:de|do|da)?\s*([a-z0-9\s]+?)(?:\s+(?:e|com|que|onde|cidade|municipio|estado|uf)\b|\s+(?:no|na|de|do|da)\s+(?:cidade|municipio|estado|uf|bairro)\b|$)",
        ),
        "classe": (
            r"\bclasse\s+([a-z0-9\s]+?)(?:\s+(?:e|com|que|onde|cidade|municipio|estado|uf)\b|\s+(?:no|na|de|do|da)\s+(?:cidade|municipio|estado|uf|bairro)\b|$)",
        ),
        "cep": (
            r"\bcep\s+([0-9.\-]{5,})",
        ),
    }.items():
        value = _first_clean_match(normalized_plain, patterns)
        if value:
            params[key] = value

    customer_name = _first_clean_match(
        normalized_plain,
        (
            r"\b(?:cliente|comprador)\s+(?:chamado|nome|fantasia|de nome)?\s*([a-z0-9\s]{3,}?)(?:\s+(?:com|que|onde|em|na|no)\b|$)",
            r"\b(?:dados|cadastro|cpf|cnpj|documento|telefone|email|endereco)\s+(?:do|da|de)\s+cliente\s+([a-z0-9\s]{3,}?)(?:\s+(?:com|que|onde|em|na|no)\b|$)",
        ),
    )
    if customer_name:
        first_token = customer_name.split()[0]
        if first_token not in _CUSTOMER_NAME_STOP_TERMS and customer_name not in _CITY_FALLBACK_STOP_TERMS:
            params["cliente_nome"] = customer_name

    return params


def _sync_geographic_params(intentions: list[Any], query_text: str) -> None:
    """Keep explicit registry filters on the correct physical alias."""
    normalized = normalize_text_key(query_text or "")
    registry_params = _extract_customer_registry_params(query_text)

    try:
        from services.ai_service import _extract_entity_registry_params_for_fallback

        if any(term in normalized for term in _SELLER_CONTEXT_TERMS):
            registry_params.update(_extract_entity_registry_params_for_fallback(normalized, "VENDEDOR"))
        if any(term in normalized for term in _PRODUCT_CONTEXT_TERMS):
            registry_params.update(_extract_entity_registry_params_for_fallback(normalized, "PRODUTO"))
        if any(term in normalized for term in _SUPPLIER_CONTEXT_TERMS):
            registry_params.update(_extract_entity_registry_params_for_fallback(normalized, "FORNECEDOR"))
    except Exception:
        logger.debug("[QIE] Extracao cadastral generica indisponivel; mantendo filtros basicos.")

    if not registry_params:
        return

    for intention in intentions:
        if getattr(intention, "fora_de_escopo", False) or getattr(intention, "resposta_direta", None):
            continue
        params = dict(getattr(intention, "parametros", {}) or {})
        params.update(registry_params)
        if "cidade" in params:
            params.pop("regiao", None)
        intention.parametros = params


def _metric_order_hint_from_query(query_text: str) -> tuple[str | None, str | None]:
    """Infer deterministic ordering hints for common 'best/worst' questions."""
    normalized = normalize_text_key(query_text or "")
    metric: str | None = None

    if "margem" in normalized:
        metric = "margem_lucro"
    elif any(term in normalized for term in ("lucro", "rentabilidade", "rentavel", "rentaveis", "lucratividade", "lucrativo", "lucrativos")):
        metric = "lucro_bruto"
    elif "ticket" in normalized or "valor medio" in normalized:
        metric = "ticket_medio"
    elif any(term in normalized for term in ("quantidade", "unidades", "mais vendidos", "mais vendido")):
        metric = "unidades_vendidas"
    elif any(term in normalized for term in ("receita", "faturamento", "venda", "vendas", "compraram", "comprou")):
        metric = "receita_total"

    descending_explicit_terms = (
        "mais vendeu para o que menos",
        "mais vendeu para o menos",
        "maior para o menor",
        "maior para menor",
        "mais vendidos para o menos",
        "mais vendidos para os menos",
        "do mais vendido para",
        "do maior para",
    )
    ascending_terms = (
        "do menor para",
        "do menos vendido para",
        "menor",
        "pior",
        "menos",
        "mais baixo",
        "mais baixa",
        "baixo retorno",
        "baixa rentabilidade",
    )
    if any(term in normalized for term in descending_explicit_terms):
        direction = "DESC"
    elif any(term in normalized for term in ascending_terms):
        direction = "ASC"
    else:
        direction = "DESC"
    return metric, direction


def _sync_metric_ordering_params(intentions: list[Any], query_text: str) -> None:
    """Propagate metric/order/group hints into all executable intentions."""
    metric, direction = _metric_order_hint_from_query(query_text)
    if not metric or not direction:
        return

    normalized = normalize_text_key(query_text or "")
    singular_entity = bool(
        re.search(r"\bqual\s+(?:o|a)?\s*(?:produto|item|sku|mercadoria|insumo|cliente|vendedor|fornecedor)\b", normalized)
    )
    product_question = any(term in normalized for term in ("produto", "produtos", "item", "itens", "sku", "mercadoria", "mercadorias", "insumo", "insumos"))

    for intention in intentions:
        if getattr(intention, "fora_de_escopo", False) or getattr(intention, "resposta_direta", None):
            continue

        params = dict(getattr(intention, "parametros", {}) or {})
        params["_order_metric"] = metric
        params["_order_direction"] = direction
        if singular_entity and not params.get("limite") and not getattr(intention, "quantidade_limite", None):
            params["limite"] = "1"
            intention.quantidade_limite = 1
        intention.parametros = params

        plan = getattr(intention, "plano_estruturado", None)
        if not plan:
            continue

        metrics = list(getattr(plan, "metrics", []) or [])
        if metric not in metrics:
            metrics.insert(0, metric)
        if metric == "margem_lucro":
            for support_metric in ("lucro_bruto", "receita_total"):
                if support_metric not in metrics:
                    metrics.append(support_metric)
        plan.metrics = list(dict.fromkeys(metrics))

        group_by = list(getattr(plan, "group_by", []) or [])
        if product_question and not any("produto" in str(group).lower() for group in group_by):
            group_by.append("produto_nome")
        plan.group_by = list(dict.fromkeys(group_by))


class BlueprintVersionamento(BaseModel):
    id: str
    versao: int
    data_criacao: str
    autor: str = "IA (LuminaAI Planner)"
    historico: list[str] = Field(default_factory=list)
    dependencias: list[str] = Field(default_factory=list)
    permissoes: list[str] = Field(default_factory=list)
    ultima_utilizacao: str | None = None
    quantidade_utilizacoes: int = 0
    tempo_acumulado_ms: float = 0.0
    tempo_ia_acumulado_ms: float = 0.0
    tokens_economizados: int = 0


class BlueprintModel(BaseModel):
    id: str
    intent_id: str
    version: int
    nome_consulta: str
    objetivo: str
    tipo_analise: str = "AGGREGATION"
    view_catalog_id: str
    view_name: str
    metrics: list[str] = Field(default_factory=list)
    group_by: list[str] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)
    visualization_type: str = "TABLE"
    layout: dict[str, Any] = Field(default_factory=dict)
    exemplos_perguntas: list[str] = Field(default_factory=list)
    versionamento: BlueprintVersionamento


class _PreliminaryIntention:
    """
    Representacao minima de intencao para geracao de fingerprint preliminar.
    Usada pela Etapa 0 (Analytical Package Layer) antes do NLU completo.
    Permite extrair dominio e operacao basicos a partir da pergunta por heuristica.
    """
    def __init__(self, pergunta: str = "", operacao: str = None, entidade_alvo: str = None):
        self.pergunta = pergunta
        self.operacao = operacao or self._infer_operacao(pergunta)
        self.entidade_alvo = entidade_alvo or self._infer_entidade(pergunta)
        self.confianca = 0.5
        self.justificativa = "Fingerprint preliminar (pre-NLU)"
        self.is_comparacao = False
        self.periodo_referencia = self._infer_periodo(pergunta)
        self.visualizacao_preferida = None
        self.plano_estruturado = None
        self.parametros = {}
        self.view_catalog_id = None
        self.nivel_confianca = "BAIXA"
        self.resposta_direta = None
        self.fora_de_escopo = False
        self.mensagem_bloqueio = None
        self.quantidade_limite = None
        self.comparativo_detalhe = None

    def _infer_operacao(self, pergunta: str) -> str:
        p = pergunta.lower()
        if any(w in p for w in ["lista", "listar", "listagem", "todos", "todas", "cadastro", "cadastrado", "cadastrados"]):
            return "LISTAGEM"
        if any(w in p for w in ["top", "ranking", "maior", "menor", "mais vendido"]):
            return "RANKING"
        if any(w in p for w in ["versus", " vs ", "comparar", "comparacao", "crescimento"]):
            return "COMPARACAO"
        if any(w in p for w in ["tendencia", "projecao", "historico", "evolucao"]):
            return "TENDENCIA"
        if any(w in p for w in ["media", "ticket", "avg"]):
            return "MEDIA"
        return "SOMA"

    def _infer_entidade(self, pergunta: str) -> str:
        p = pergunta.lower()
        if any(w in p for w in ["produto", "item", "sku"]):
            return "PRODUTO"
        if any(w in p for w in ["cliente", "comprador"]):
            return "CLIENTE"
        if any(w in p for w in ["vendedor", "representante"]):
            return "VENDEDOR"
        if any(w in p for w in ["regiao", "cidade", "estado", "filial"]):
            return "REGIAO"
        return "GERAL"

    def _infer_periodo(self, pergunta: str) -> str:
        p = pergunta.lower()
        if "hoje" in p:
            return "hoje"
        if "ontem" in p:
            return "ontem"
        if "semana" in p:
            return "semana"
        if "mes" in p:
            return "mes"
        if "ano" in p:
            return "ano"
        return ""


class QueryIntelligenceEngine:
    def __init__(self, blueprint_repository: BlueprintJsonRepository | None = None):
        self.blueprints: list[BlueprintModel] = []
        self._blueprint_repository = (
            blueprint_repository or BlueprintRepositoryFactory.create()
        )
        # MÃ©tricas globais de performance e auditoria
        self.execucoes_com_ia: int = 0
        self.execucoes_sem_ia: int = 0
        self.tempo_total_com_ia_ms: float = 0.0
        self.tempo_total_sem_ia_ms: float = 0.0
        self.tokens_economizados_total: int = 0
        self.load_blueprints()

    def load_blueprints(self) -> None:
        """Carrega os blueprints do arquivo JSON. Inicializa com starters se vazio/ausente."""
        with _io_lock:
            try:
                # Garante que o diretÃ³rio exista
                if not self._blueprint_repository.exists():
                    logger.info("RepositÃ³rio de Blueprints ausente. Criando starters...")
                    self._create_starter_blueprints()
                    return

                data = self._blueprint_repository.read()
                    
                self.blueprints = [BlueprintModel(**bp) for bp in data.get("blueprints", [])]
                
                # Restaura mÃ©tricas globais
                metrics = data.get("global_metrics", {})
                self.execucoes_com_ia = metrics.get("execucoes_com_ia", 0)
                self.execucoes_sem_ia = metrics.get("execucoes_sem_ia", 0)
                self.tempo_total_com_ia_ms = metrics.get("tempo_total_com_ia_ms", 0.0)
                self.tempo_total_sem_ia_ms = metrics.get("tempo_total_sem_ia_ms", 0.0)
                self.tokens_economizados_total = metrics.get("tokens_economizados_total", 0)
                
                logger.info("Carregados %d blueprints com sucesso do repositÃ³rio.", len(self.blueprints))
            except Exception as e:
                logger.exception("Falha ao carregar repositÃ³rio de blueprints: %s", e)
                self._create_starter_blueprints()

    def save_blueprints(self) -> None:
        """Salva a lista atual de blueprints e mÃ©tricas de auditoria no JSON."""
        with _io_lock:
            try:
                data = {
                    "blueprints": [bp.model_dump() for bp in self.blueprints],
                    "global_metrics": {
                        "execucoes_com_ia": self.execucoes_com_ia,
                        "execucoes_sem_ia": self.execucoes_sem_ia,
                        "tempo_total_com_ia_ms": self.tempo_total_com_ia_ms,
                        "tempo_total_sem_ia_ms": self.tempo_total_sem_ia_ms,
                        "tokens_economizados_total": self.tokens_economizados_total,
                    }
                }
                self._blueprint_repository.write(data)
                logger.debug("RepositÃ³rio de blueprints salvo com sucesso.")
            except Exception as e:
                logger.error("Falha ao salvar repositÃ³rio de blueprints: %s", e)

    def _create_starter_blueprints(self) -> None:
        """Cria e salva blueprints iniciais (starter blueprints)."""
        now_str = datetime.datetime.now().isoformat()
        
        bp_vendas_diarias = BlueprintModel(
            id="bp_daily_sales_v1",
            intent_id="daily_sales",
            version=1,
            nome_consulta="Resumo de Vendas DiÃ¡rias",
            objetivo="Obter faturamento, quantidade de pedidos e ticket mÃ©dio do dia atual",
            tipo_analise="AGGREGATION",
            view_catalog_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380101", # ID Dummy para vendas
            view_name="VW_VENDAS_LM",
            metrics=["receita_total", "quantidade_pedidos", "ticket_medio"],
            group_by=[],
            filters={"date_range": "2026-07-03 to 2026-07-03"},
            visualization_type="KPI",
            layout={"order": ["kpi_cards", "revenue_trend"]},
            exemplos_perguntas=[
                "quanto vendeu hoje",
                "quanto faturamos hoje",
                "resumo de vendas de hoje",
                "receita de hoje",
                "como foram as vendas hoje"
            ],
            versionamento=BlueprintVersionamento(
                id="bp_daily_sales_v1",
                versao=1,
                data_criacao=now_str,
                autor="IA Starter",
                dependencias=["VW_VENDAS_LM"],
                permissoes=["admin", "user", "manager"]
            )
        )

        bp_produtos = BlueprintModel(
            id="bp_product_ranking_v1",
            intent_id="product_ranking",
            version=1,
            nome_consulta="Ranking de Produtos",
            objetivo="Visualizar ranking dos produtos mais vendidos por faturamento",
            tipo_analise="AGGREGATION",
            view_catalog_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380102",
            view_name="VW_PRODUTOS",
            metrics=["receita_total"],
            group_by=["produto_nome"],
            filters={"date_range": "2026-07-01 to 2026-07-03"},
            visualization_type="BAR",
            layout={"order": ["bar_chart", "data_table"]},
            exemplos_perguntas=[
                "qual produto vendeu mais",
                "ranking de produtos mais vendidos",
                "produtos lÃ­deres em vendas",
                "faturamento por produto"
            ],
            versionamento=BlueprintVersionamento(
                id="bp_product_ranking_v1",
                versao=1,
                data_criacao=now_str,
                autor="IA Starter",
                dependencias=["VW_PRODUTOS"],
                permissoes=["admin", "user", "manager"]
            )
        )

        self.blueprints = [bp_vendas_diarias, bp_produtos]
        self.save_blueprints()

    def get_similarity_score(self, pergunta: str, tenant_id: str) -> tuple[float, BlueprintModel | None]:
        """
        Analisa a pergunta em linguagem natural e retorna o maior score de similaridade
        semÃ¢ntica encontrado no repositÃ³rio de blueprints, juntamente com o blueprint correspondente.
        """
        if not pergunta:
            return 0.0, None

        pergunta_norm = self._normalize_query(pergunta)
        tokens_pergunta = set(pergunta_norm.split())

        best_score = 0.0
        best_bp: BlueprintModel | None = None

        for bp in self.blueprints:
            if not _is_reusable_blueprint_candidate(bp):
                continue
            for ex in bp.exemplos_perguntas:
                ex_norm = self._normalize_query(ex)
                tokens_ex = set(ex_norm.split())

                if not tokens_ex:
                    continue

                # Similaridade base baseada em Jaccard
                intersection = tokens_pergunta.intersection(tokens_ex)
                union = tokens_pergunta.union(tokens_ex)
                jaccard = len(intersection) / len(union)

                # ReforÃ§a correspondÃªncia semÃ¢ntica para perguntas do mesmo domÃ­nio
                semantic_bonus = 0.0
                if "venda" in pergunta_norm and "venda" in ex_norm:
                    semantic_bonus += 0.12
                if "fatur" in pergunta_norm and "fatur" in ex_norm:
                    semantic_bonus += 0.12
                if "hoje" in pergunta_norm and "hoje" in ex_norm:
                    semantic_bonus += 0.08
                if "produto" in pergunta_norm and "produto" in ex_norm:
                    semantic_bonus += 0.08
                if "vendedor" in pergunta_norm and "vendedor" in ex_norm:
                    semantic_bonus += 0.08

                score = min(0.99, max(jaccard, 0.0) + semantic_bonus)

                # Garante que perguntas muito parecidas sejam reutilizadas
                if tokens_pergunta == tokens_ex:
                    score = 0.99
                elif jaccard >= 0.5 and semantic_bonus > 0:
                    score = max(score, 0.90)
                elif jaccard >= 0.65:
                    score = max(score, 0.88)

                if score > best_score:
                    best_score = score
                    best_bp = bp

        return best_score, best_bp

    def _normalize_query(self, query: str) -> str:
        """Normaliza termos comuns, remove acentos, stopwords e mapeia variÃ¡veis."""
        norm = normalize_text_key(query)

        # â”€â”€ 1. ExtraÃ§Ã£o e NormalizaÃ§Ã£o de VariÃ¡veis Temporais â”€â”€
        # Datas absolutas YYYY-MM-DD
        norm = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "{periodo}", norm)
        # Termos relativos de tempo comuns
        for term in ("hoje", "ontem", "este mes", "mes passado", "ano passado", "este ano", "semana passada", "ultimo trimestre"):
            norm = norm.replace(term, "{periodo}")

        # â”€â”€ 2. SubstituiÃ§Ã£o de SinÃ´nimos de NegÃ³cio para Foco de IntenÃ§Ã£o â”€â”€
        synonyms = {
            "faturamento": "venda",
            "faturamos": "venda",
            "faturou": "venda",
            "receita": "venda",
            "vendas": "venda",
            "vendido": "venda",
            "vendidos": "venda",
            "vendemos": "venda",
            "vendeu": "venda",
            "lucro": "lucro",
            "lucros": "lucro",
            "margem": "lucro",
            "rentabilidade": "lucro",
            "vendedor": "vendedor",
            "representante": "vendedor",
            "colaborador": "vendedor",
            "cliente": "cliente",
            "comprador": "cliente",
            "produto": "produto",
            "mercadoria": "produto",
            "item": "produto",
            "total": "total",
            "soma": "total",
            "resumo": "total",
            "detalhado": "total"
        }
        
        words = norm.split()
        mapped_words = []
        stopwords = {"de", "o", "a", "em", "para", "com", "qual", "quanto", "me", "mostre", "por", "sobre", "do", "da", "um", "uma"}
        
        for w in words:
            if w in stopwords:
                continue
            # Verifica mapeamento de sinÃ´nimos
            mapped_words.append(synonyms.get(w, w))

        return " ".join(mapped_words)

    def adapt_blueprint(self, blueprint: BlueprintModel, pergunta: str) -> BlueprintModel:
        """
        Reutiliza diretamente o Blueprint (Score >= 95%), adaptando apenas
        os parÃ¢metros mutÃ¡veis da pergunta (perÃ­odos e nomes de filtros).
        """
        adapted = BlueprintModel(**blueprint.model_dump())
        params = self.extract_params_from_text(pergunta)
        
        # Sobrescreve filtros preservando layout e estrutura
        for k, v in params.items():
            if v is not None:
                adapted.filters[k] = v
        return adapted

    def evolve_blueprint(self, blueprint: BlueprintModel, pergunta: str) -> BlueprintModel:
        """
        Evolui um Blueprint (Score 80%-94%), copiando a estrutura, adaptando parÃ¢metros,
        incrementando a versÃ£o e salvando uma nova entrada no repositÃ³rio.
        """
        # Copia estrutura bÃ¡sica do blueprint
        new_version = blueprint.version + 1
        new_id = f"{blueprint.intent_id}_v{new_version}"
        
        now_str = datetime.datetime.now().isoformat()
        
        # Cria novo Blueprint modelo
        evolved = BlueprintModel(
            id=new_id,
            intent_id=blueprint.intent_id,
            version=new_version,
            nome_consulta=f"{blueprint.nome_consulta} (EvoluÃ­do v{new_version})",
            objetivo=blueprint.objetivo,
            tipo_analise=blueprint.tipo_analise,
            view_catalog_id=blueprint.view_catalog_id,
            view_name=blueprint.view_name,
            metrics=list(blueprint.metrics),
            group_by=list(blueprint.group_by),
            filters=dict(blueprint.filters),
            visualization_type=blueprint.visualization_type,
            layout=dict(blueprint.layout),
            exemplos_perguntas=list(blueprint.exemplos_perguntas) + [pergunta.lower().strip()],
            versionamento=BlueprintVersionamento(
                id=new_id,
                versao=new_version,
                data_criacao=now_str,
                autor="IA (LuminaAI Planner)",
                historico=blueprint.versionamento.historico + [f"EvoluÃ­do a partir de {blueprint.id}"],
                dependencias=list(blueprint.versionamento.dependencias),
                permissoes=list(blueprint.versionamento.permissoes)
            )
        )
        
        # Adapta os parÃ¢metros
        params = self.extract_params_from_text(pergunta)
        for k, v in params.items():
            if v is not None:
                evolved.filters[k] = v
                
        # Registra no agrupamento se a pergunta contiver termos dimensionais extras
        q_norm = normalize_text_key(pergunta)
        if "vendedor" in q_norm and "vendedor_nome" not in evolved.group_by:
            # Se a pergunta pedir vendedor explicitamente, adiciona nas dimensÃµes
            if "vendedor_nome" not in evolved.group_by:
                evolved.group_by.append("vendedor_nome")
                
        self.blueprints.append(evolved)
        self.save_blueprints()
        return evolved

    def create_blueprint_from_intention(
        self, intention: Any, pergunta: str, plan_response: Any, catalog: list[Any] | None = None
    ) -> BlueprintModel:
        """
        Cria um Blueprint 100% novo a partir da resposta de intenÃ§Ãµes e do plano validado.
        """
        now_str = datetime.datetime.now().isoformat()
        intent_id = intention.justificativa.lower().strip().replace(" ", "_")[:24] if intention.justificativa else "custom_intent"
        intent_id = re.sub(r"[^a-z0-9_]", "", intent_id)
        if not intent_id:
            intent_id = "custom_query"
            
        bp_id = f"bp_{intent_id}_v1"
        
        # Previne colisÃ£o de IDs na criaÃ§Ã£o
        existing_ids = {bp.id for bp in self.blueprints}
        counter = 1
        while bp_id in existing_ids:
            bp_id = f"bp_{intent_id}_c{counter}_v1"
            counter += 1

        view_name = "unknown_view"
        if catalog and getattr(intention, "view_catalog_id", None):
            view_obj = next((v for v in catalog if str(getattr(v, "id", "")) == str(intention.view_catalog_id)), None)
            if view_obj:
                view_name = getattr(view_obj, "nome_view_oracle", None) or view_name
        if view_name == "unknown_view":
            view_name = getattr(plan_response, "view_name", None) or view_name

        new_bp = BlueprintModel(
            id=bp_id,
            intent_id=intent_id,
            version=1,
            nome_consulta=intention.justificativa or "Consulta Customizada",
            objetivo=intention.justificativa or "Visualizar resultados analÃ­ticos customizados",
            tipo_analise="AGGREGATION" if plan_response.group_by else "SELECT",
            view_catalog_id=str(intention.view_catalog_id) if intention.view_catalog_id else "unknown_catalog",
            view_name=view_name,
            metrics=list(plan_response.metrics),
            group_by=list(plan_response.group_by),
            filters=dict(plan_response.filters),
            visualization_type=plan_response.visualization.get("type", "TABLE"),
            layout={"order": ["dashboard_render"]},
            exemplos_perguntas=[pergunta.lower().strip()],
            versionamento=BlueprintVersionamento(
                id=bp_id,
                versao=1,
                data_criacao=now_str,
                autor="IA (LuminaAI Planner)",
                dependencias=[plan_response.intent] if plan_response.intent else [],
                permissoes=["admin", "user", "manager"]
            )
        )
        
        self.blueprints.append(new_bp)
        self.save_blueprints()
        return new_bp

    def extract_params_from_text(self, pergunta: str) -> dict[str, Any]:
        """Extrai localmente datas e dimensÃµes chaves de negÃ³cio da pergunta."""
        filters = {}
        
        # â”€â”€ 1. ResoluÃ§Ã£o de datas â”€â”€
        # Tenta casar datas absolutas ISO YYYY-MM-DD
        abs_match = re.search(r"(\d{4}-\d{2}-\d{2})\s*(?:to|ate|a|-)\s*(\d{4}-\d{2}-\d{2})", pergunta)
        if abs_match:
            filters["date_range"] = f"{abs_match.group(1)} to {abs_match.group(2)}"
        else:
            explicit_range = resolve_relative_date_range(pergunta)
            if explicit_range:
                filters["date_range"] = f"{explicit_range[0]} to {explicit_range[1]}"
                found_range = explicit_range
            else:
                found_range = None

            # Procura por express?es temporais relativas
            norm = normalize_text_key(pergunta)
            if not found_range:
                for term in ("hoje", "ontem", "este mes", "mes passado", "ano passado", "este ano", "ultimos 7 dias", "ultimos 30 dias", "primeiro trimestre", "segundo trimestre", "terceiro trimestre", "quarto trimestre"):
                    if term in norm:
                        found_range = resolve_relative_date_range(term)
                        break
            if found_range:
                filters["date_range"] = f"{found_range[0]} to {found_range[1]}"

        # Ã¢â€â‚¬Ã¢â€â‚¬ 2. Filtros de Nome (Vendedores, Clientes e Produtos) Ã¢â€â‚¬Ã¢â€â‚¬
        q_clean = pergunta.lower()
        # Procura nomes prÃ³prios apÃ³s preposiÃ§Ãµes e palavras-chave de entidade
        name_match = re.search(
            r"\b(?:do|da|de|para|por|vendedor|representante|cliente|comprador|produto)\s+([A-Z][^\s,.;!?]*(?:\s+[A-Z][^\s,.;!?]*)*)",
            pergunta,
        )
        if name_match:
            candidate_name = name_match.group(1).strip()
            if candidate_name.lower() not in {"de", "da", "do"}:
                filters["vendedor_nome"] = candidate_name

        if "joao" in q_clean:
            filters["products"] = filters.get("products", [])
            filters["customers"] = filters.get("customers", [])
            filters["regions"] = filters.get("regions", [])
            filters["vendedor_nome"] = "João"
        elif "maria" in q_clean:
            filters["vendedor_nome"] = "Maria"

        if "geladeira" in q_clean:
            filters["products"] = ["geladeira"]
        elif "celular" in q_clean:
            filters["products"] = ["celular"]

        if "ambev" in q_clean:
            filters["customers"] = ["Ambev"]

        if "sul" in q_clean:
            filters["regions"] = ["Sul"]
        elif "matriz" in q_clean:
            filters["regions"] = ["Matriz"]

        return filters

    def register_blueprint_usage(
        self, blueprint_id: str, execution_time_ms: float, tokens_saved: int = 0, reused_directly: bool = True
    ) -> None:
        """Registra o uso de um blueprint e atualiza estatÃ­sticas globais de eficiÃªncia."""
        bp = next((b for b in self.blueprints if b.id == blueprint_id), None)
        if bp:
            now_str = datetime.datetime.now().isoformat()
            bp.versionamento.quantidade_utilizacoes += 1
            bp.versionamento.ultima_utilizacao = now_str
            bp.versionamento.tokens_economizados += tokens_saved
            bp.versionamento.tempo_acumulado_ms += execution_time_ms

        if reused_directly:
            self.execucoes_sem_ia += 1
            self.tempo_total_sem_ia_ms += execution_time_ms
        else:
            self.execucoes_com_ia += 1
            self.tempo_total_com_ia_ms += execution_time_ms
            
        self.tokens_economizados_total += tokens_saved
        self.save_blueprints()

    def get_intelligence_metrics(self) -> dict[str, Any]:
        """Retorna estatÃ­sticas acumuladas de auditoria e eficiÃªncia de Blueprints."""
        total_exec = self.execucoes_com_ia + self.execucoes_sem_ia
        taxa_reutilizacao = (self.execucoes_sem_ia / total_exec * 100) if total_exec > 0 else 0.0
        
        tempo_medio_com_ia = (self.tempo_total_com_ia_ms / self.execucoes_com_ia) if self.execucoes_com_ia > 0 else 0.0
        tempo_medio_sem_ia = (self.tempo_total_sem_ia_ms / self.execucoes_sem_ia) if self.execucoes_sem_ia > 0 else 0.0
        tempo_medio_geral = ((self.tempo_total_com_ia_ms + self.tempo_total_sem_ia_ms) / total_exec) if total_exec > 0 else 0.0
        
        # EficiÃªncia Ã© a taxa de tempo poupado
        tempo_economizado_total_ms = (tempo_medio_com_ia - tempo_medio_sem_ia) * self.execucoes_sem_ia
        tempo_economizado_s = max(0.0, tempo_economizado_total_ms / 1000.0)

        return {
            "total_consultas_processadas": total_exec,
            "taxa_reutilizacao_percentual": round(taxa_reutilizacao, 2),
            "economia_tokens_total": self.tokens_economizados_total,
            "tempo_economizado_segundos": round(tempo_economizado_s, 2),
            "tempo_medio_consulta_geral_ms": round(tempo_medio_geral, 2),
            "tempo_medio_com_ia_ms": round(tempo_medio_com_ia, 2),
            "tempo_medio_sem_ia_ms": round(tempo_medio_sem_ia, 2),
            "eficiencia_custo_percentual": round(taxa_reutilizacao, 2),
        }

    def sync_database_blueprints(self, db_blueprints: list[Any]) -> None:
        """Sincroniza os blueprints do banco de dados com a lista em memÃ³ria para matching."""
        import datetime
        from services.query_intelligence_engine import BlueprintVersionamento
        existing_ids = {bp.intent_id for bp in self.blueprints}
        for db_bp in db_blueprints:
            if db_bp.intent_id not in existing_ids:
                bp_model = BlueprintModel(
                    id=f"bp_{db_bp.intent_id}_v{db_bp.version}",
                    intent_id=db_bp.intent_id,
                    version=db_bp.version,
                    nome_consulta=db_bp.nome_consulta,
                    objetivo=db_bp.objetivo,
                    tipo_analise=db_bp.tipo_analise,
                    view_catalog_id=str(db_bp.view_catalog_id),
                    view_name=db_bp.view_name,
                    metrics=db_bp.metrics,
                    group_by=db_bp.group_by,
                    filters=db_bp.filters,
                    visualization_type=db_bp.visualization_type,
                    layout=db_bp.layout,
                    exemplos_perguntas=db_bp.exemplos_perguntas,
                    versionamento=BlueprintVersionamento(
                        id=f"bp_{db_bp.intent_id}_v{db_bp.version}",
                        versao=db_bp.version,
                        data_criacao=db_bp.criado_em.isoformat() if db_bp.criado_em else datetime.datetime.now().isoformat(),
                        autor="IA (LuminaAI Planner)",
                        dependencias=db_bp.dependencias or [],
                        permissoes=db_bp.permissoes or []
                    )
                )
                bp_model.versionamento.quantidade_utilizacoes = db_bp.quantidade_utilizacoes
                bp_model.versionamento.tempo_acumulado_ms = db_bp.tempo_acumulado_ms
                bp_model.versionamento.tempo_ia_acumulado_ms = db_bp.tempo_ia_acumulado_ms
                bp_model.versionamento.tokens_economizados = db_bp.tokens_economizados
                if db_bp.ultima_utilizacao:
                    bp_model.versionamento.ultima_utilizacao = db_bp.ultima_utilizacao.isoformat()
                
                self.blueprints.append(bp_model)
                existing_ids.add(bp_model.intent_id)

    async def process_query(
        self,
        payload: Any,
        current_user: Any,
        db: AsyncSession,
        background_tasks: Any,
        instrucoes_finais: str,
        ia_api_key: str | None,
        ia_model: str | None,
        ia_temp: float | None,
        catalog_summaries: list[Any],
        tenant: Any,
        intent_identifier: Any | None = None,
    ) -> Any:
        """
        Coordenador central do pipeline (operational brain).
        Executa as 12 fases do processamento de dados sequencialmente.
        """
        import time
        import uuid
        import json
        import hashlib
        from decimal import Decimal
        from fastapi import HTTPException, status
        
        from schemas.query import QueryResponse, IntentionPlanItem as SchemaIntentionPlanItem
        from models.view_catalog import ChartType, ViewCatalog
        from models.search_history import SearchHistory
        from database import get_db_context
        from services.ai_service import identify_intention, ModelViolationError, AIServiceError, IntentionResponse
        from services.query_planner import create_query_plan
        from services.plan_validator import validate_and_normalize_plan
        from services.ai.response_builder import response_builder
        from services.ai.memory_context_engine import memory_context_engine
        from services.context_guard import ScopeViolationError, sanitize_history, validate_user_query
        from services.query_history_service import persist_query_history
        
        total_inicio = time.perf_counter()
        query_id = uuid.uuid4()
        response_mode = response_builder.normalize_mode(getattr(payload, "mode", None))
        session_id = getattr(payload, "session_id", None)

        try:
            payload.pergunta = validate_user_query(payload.pergunta)
        except ScopeViolationError as scope_err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(scope_err))

        fresh_ai_required = _requires_fresh_ai_interpretation(payload.pergunta)
        catalog_gap = _catalog_gap_for_query(payload.pergunta, catalog_summaries)
        if catalog_gap:
            gap_code, gap_message = catalog_gap
            tempo_ms = int((time.perf_counter() - total_inicio) * 1000)
            background_tasks.add_task(
                persist_query_history,
                user_id=current_user.id,
                view_catalog_id=None,
                pergunta=payload.pergunta,
                parametros={"_catalog_gap": gap_code},
                confianca=0.0,
                tempo_ms=tempo_ms,
            )
            gap_telemetry = response_builder.build_response_metadata(
                mode=response_mode,
                confidence_score=0.0,
                confidence_status="CATALOG_VIEW_NOT_AVAILABLE",
                tokens_consumed=0,
                timings={"catalog_guard": tempo_ms, "total_pipeline": tempo_ms},
            )
            return QueryResponse(
                query_id=query_id,
                request_id=query_id,
                view_catalog_id=None,
                view_name=None,
                chart_type=None,
                chart_data={
                    "catalog_gap": True,
                    "reason": gap_code,
                    "available_views": _catalog_names(catalog_summaries),
                },
                parametros_extraidos={},
                ia_confianca=0.0,
                ia_justificativa=gap_message,
                pergunta_original=payload.pergunta,
                pode_favoritar=False,
                resposta_direta=gap_message,
                mensagem=gap_message,
                telemetry=gap_telemetry,
            )

        # -- 0. Analytical Package Layer (PRE-NLU) ---------------------------------
        # Verifica se existe um Package reutilizavel antes de invocar o NLU.
        # GARANTIA: Esta etapa e NAO-BLOQUEANTE. Se falhar, pipeline normal continua.

        try:
            from services.data_platform.intent_fingerprint import intent_fingerprint_generator
            from services.data_platform.package_compatibility import package_compatibility_engine
            from services.data_platform.analytical_package_service import analytical_package_service as _ap_svc

            _preliminary_fingerprint = intent_fingerprint_generator.generate(
                intention=_PreliminaryIntention(pergunta=payload.pergunta),
                plan=None,
                pergunta=payload.pergunta,
            )

            _compatible_pkg, _compat_score = await package_compatibility_engine.find_compatible_package(
                fingerprint=_preliminary_fingerprint,
                tenant_id=payload.tenant_id,
                db=db,
            )

            if _compatible_pkg and _compat_score >= PACKAGE_PRE_NLU_REUSE_THRESHOLD and not fresh_ai_required:
                logger.info(
                    "[QIE] [PACKAGE HIT] id=%s score=%.3f -- pipeline NLU ignorado",
                    _compatible_pkg.id, _compat_score,
                )
            elif _compatible_pkg and fresh_ai_required:
                logger.info(
                    "[QIE] Package compativel encontrado (score=%.3f), mas pergunta exige NLU fresco. Reuso pre-NLU ignorado.",
                    _compat_score,
                )
            elif _compatible_pkg and _compat_score < PACKAGE_PRE_NLU_REUSE_THRESHOLD:
                logger.info(
                    "[QIE] Package compativel abaixo do limiar seguro pre-NLU (score=%.3f, min=%.2f). Pipeline normal.",
                    _compat_score,
                    PACKAGE_PRE_NLU_REUSE_THRESHOLD,
                )
            if _compatible_pkg and _compat_score >= PACKAGE_PRE_NLU_REUSE_THRESHOLD and not fresh_ai_required:
                _pkg_tempo_ms = int((time.perf_counter() - total_inicio) * 1000)
                _view_name = (_compatible_pkg.view_names or ["VW_VENDAS"])[0]
                _vis_strategy = _compatible_pkg.visual_strategy or {}
                _chart_type_str = _vis_strategy.get("primary_chart_type", "TABLE")
                from models.view_catalog import ChartType
                try:
                    _chart_type = ChartType(_chart_type_str)
                except ValueError:
                    _chart_type = None
                from schemas.query import QueryResponse

                # Busca a instÃ¢ncia de dashboard mais recente deste pacote
                from models.package_dashboard_instance import PackageDashboardInstance
                from sqlalchemy import select
                stmt_inst = select(PackageDashboardInstance).where(
                    PackageDashboardInstance.package_id == _compatible_pkg.id,
                    PackageDashboardInstance.tenant_id == payload.tenant_id
                ).order_by(PackageDashboardInstance.criado_em.desc()).limit(1)
                res_inst = await db.execute(stmt_inst)
                _latest_instance = res_inst.scalar_one_or_none()

                if not _latest_instance:
                    # Auto-healing: se nÃ£o existir nenhuma instÃ¢ncia, forÃ§a o Smart Refresh
                    from services.data_platform.live_dashboard_runtime import live_dashboard_runtime
                    logger.info("[QIE] Nenhuma instÃ¢ncia encontrada para o pacote %s. ForÃ§ando refresh...", _compatible_pkg.id)
                    await live_dashboard_runtime.refresh_runtime(payload.tenant_id, _compatible_pkg.id, db)
                    res_inst = await db.execute(stmt_inst)
                    _latest_instance = res_inst.scalar_one_or_none()

                _dash_payload = _latest_instance.dashboard_payload if _latest_instance else {}
                _datasets_snap = _latest_instance.datasets_snapshot if _latest_instance else {}
                _analytics_snap = _latest_instance.analytics_snapshot if _latest_instance else {}
                _bi_intel_snap = _latest_instance.bi_intelligence_snapshot if _latest_instance else {}

                # ReconstrÃ³i a lista legada de visualizaÃ§Ãµes a partir dos widgets da instÃ¢ncia
                _visualizations = []
                _widgets = _dash_payload.get("widgets", [])
                if not isinstance(_widgets, list):
                    _widgets = []
                for _w in _widgets:
                    if not isinstance(_w, dict):
                        continue
                    _w_type = _w.get("type")
                    try:
                        if _w_type == "KPI_CARD":
                            _c_type = ChartType.KPI
                            _c_data = {
                                "kpis": [{
                                    "id": _w.get("title", "").lower().replace(" ", "_"),
                                    "label": _w.get("title", ""),
                                    "value": _w.get("value", 0.0),
                                    "value_formatado": f"R$ {_w.get('value', 0.0):,.2f}" if _w.get("format") == "currency" else str(_w.get("value", 0.0)),
                                    "unit": _w.get("format", "number"),
                                    "trend": _w.get("direction", "stable").lower(),
                                    "trend_value": _w.get("diff_percent", 0.0),
                                    "trend_label": "vs perÃ­odo anterior",
                                    "icon": "chart"
                                }],
                                "periodo": "Sincronizado",
                                "gerado_em": _latest_instance.criado_em.isoformat() if _latest_instance else datetime.datetime.now().isoformat()
                            }
                        elif _w_type == "TABLE":
                            _c_type = ChartType.TABLE
                            _c_data = {
                                "columns": [{"key": col, "label": col.replace("_", " ").title(), "type": "string"} for col in _w.get("columns", [])],
                                "rows": _w.get("rows", []),
                                "total_rows": _w.get("total_rows", 0)
                            }
                        else:
                            _c_type = ChartType(_w_type)
                            _c_data = {
                                "labels": [item.get("label") for item in _w.get("data", [])],
                                "datasets": [{
                                    "label": _w.get("title", ""),
                                    "data": [item.get("value") for item in _w.get("data", [])],
                                    "backgroundColor": _w.get("color", "#4F46E5"),
                                    "borderColor": _w.get("color", "#4F46E5")
                                }]
                            }
                        from schemas.query import VisualizationItem
                        _visualizations.append(
                            VisualizationItem(
                                chart_type=_c_type,
                                chart_data=_c_data,
                                view_name=_w.get("title", "").replace("VW_", "")
                            )
                        )
                    except Exception as _w_err:
                        logger.warning("Falha ao mapear widget %s para visualizaÃ§Ã£o legada: %s", _w_type, _w_err)

                async def _register_package_reuse_bg():
                    try:
                        from database import get_db_context
                        async with get_db_context() as _bg_db:
                            await _ap_svc.reuse_package(
                                package=_compatible_pkg,
                                tenant_id=payload.tenant_id,
                                fingerprint=_preliminary_fingerprint,
                                pipeline_result={
                                    "dashboard_payload": _dash_payload,
                                    "datasets": _datasets_snap,
                                    "analytics_results": _analytics_snap,
                                    "bi_intelligence": _bi_intel_snap,
                                    "query_params": {},
                                    "pergunta_original": payload.pergunta,
                                    "execution_time_ms": _pkg_tempo_ms,
                                },
                                compatibility_score=_compat_score,
                                db=_bg_db,
                            )
                    except Exception as _bg_err:
                        logger.error("[QIE] Falha ao registrar reuso de Package (nao critico): %s", _bg_err)

                background_tasks.add_task(_register_package_reuse_bg)

                package_telemetry = response_builder.build_response_metadata(
                    mode=response_mode,
                    confidence_score=_compat_score,
                    confidence_status="PACKAGE_REUSE",
                    package_reused=True,
                    package_id=str(_compatible_pkg.id),
                    tokens_consumed=0,
                    timings={
                        "package_matcher": _pkg_tempo_ms,
                        "total_ai": 0,
                        "total_pipeline": _pkg_tempo_ms,
                    },
                )

                from services.performance.performance_optimization_platform import pop_platform
                pop_platform.record_latency("cache", _pkg_tempo_ms)

                memory_context_engine.save_session(
                    user_id=current_user.id,
                    tenant_id=payload.tenant_id,
                    session_id=session_id,
                    contexto_atual=payload.pergunta,
                    filtros_ativos={},
                    periodo=_preliminary_fingerprint.get("time_scope_type"),
                    kpis_utilizados=list((_compatible_pkg.analytical_structure or {}).get("metrics", [])),
                    dominio_negocio=_preliminary_fingerprint.get("domain", "GERAL"),
                    blueprint_ativo=str(_compatible_pkg.blueprint_id) if _compatible_pkg.blueprint_id else None,
                    dashboard_instance_ativa=str(_latest_instance.id) if _latest_instance else None,
                    analytical_package_em_uso=str(_compatible_pkg.id),
                    empresa=getattr(tenant, "nome", None),
                )

                from services.data_platform.trust_center_engine import trust_center_engine
                _trust_center_data = await trust_center_engine.build_trust_center_data(
                    tenant_id=payload.tenant_id,
                    view_name=_view_name,
                    query_id=query_id,
                    pergunta=payload.pergunta,
                    query_plan=None,
                    telemetry=package_telemetry,
                    response_time_ms=_pkg_tempo_ms,
                    package_reused=True,
                    package_id=str(_compatible_pkg.id),
                    package_compatibility_score=_compat_score
                )

                return QueryResponse(
                    query_id=query_id,
                    request_id=query_id,
                    view_catalog_id=None,
                    view_name=_view_name,
                    chart_type=_chart_type,
                    chart_data={"package_reuse": True, "package_id": str(_compatible_pkg.id)},
                    visualizations=_visualizations if _visualizations else None,
                    bi_intelligence=_bi_intel_snap,
                    parametros_extraidos={},
                    ia_confianca=_compat_score,
                    ia_justificativa=(
                        f"[Analytical Package Reutilizado] Analise compativel"
                        f" (score={_compat_score:.2f}). Package ID: {_compatible_pkg.id}"
                    ),
                    pergunta_original=payload.pergunta,
                    pode_favoritar=False,
                    mensagem=None,
                    dashboard_payload=_dash_payload,
                    datasets=_datasets_snap,
                    analytics_results=_analytics_snap,
                    analytical_package_id=str(_compatible_pkg.id),
                    package_reused=True,
                    package_compatibility_score=_compat_score,
                    trust_center=_trust_center_data,
                )
        except Exception as _pkg0_exc:
            logger.warning(
                "[QIE] Etapa 0 (Package Layer) falhou - pipeline normal prosseguindo: %s", _pkg0_exc
            )
        # -- Fim da Etapa 0 --------------------------------------------------------

        history_list = sanitize_history(
            [{"role": h.role, "content": h.content} for h in (payload.history or [])]
        )
                
        history_hash = hashlib.sha256(json.dumps(history_list, sort_keys=True).encode()).hexdigest()
        nlu_cache_key = f"{payload.pergunta}:{history_hash}"
        
        # â”€â”€ 1. IA SemÃ¢ntica (NLU) â”€â”€
        nlu_inicio = time.perf_counter()
        intentions = None
        nlu_cache_hit = False
        
        # Cache lookup
        from services.cache_service import global_cache
        try:
            cached_nlu = global_cache.get(
                payload.tenant_id,
                "nlu",
                nlu_cache_key,
                semantic_version=getattr(payload, "semantic_version", None),
                blueprint_version=getattr(payload, "blueprint_version", None)
            )
            if cached_nlu is not None:
                logger.info("[CACHE HIT] IntenÃ§Ãµes NLU recuperadas do cache | pergunta=%s", payload.pergunta)
                intentions = copy.deepcopy(cached_nlu)
                nlu_cache_hit = True
        except Exception as cache_err:
            logger.error("Falha ao acessar cache NLU: %s", cache_err)
            
        if intentions is None:
            # Sincroniza blueprints do banco de dados com a lista em memÃ³ria do QIE antes de buscar similaridade
            try:
                from services.data_platform import blueprint_repository
                db_bps = await blueprint_repository.get_all_blueprints(payload.tenant_id, db)
                self.sync_database_blueprints(db_bps)
            except Exception as bp_sync_exc:
                logger.error("Falha ao sincronizar blueprints do banco com o QIE: %s", bp_sync_exc)

            # Similaridade do QIE
            qie_score, matched_bp = self.get_similarity_score(payload.pergunta, str(payload.tenant_id))
            logger.info("[QIE] Similaridade da pergunta: %.2f | Blueprint: %s", qie_score, matched_bp.id if matched_bp else "Nenhum")
            
            blueprint_reused = False
            reused_bp_id = None
            aim_blueprint_decision = None
            if matched_bp:
                from services.ai_invocation_manager import ai_invocation_manager
                aim_blueprint_decision = ai_invocation_manager.decide(
                    tenant_id=payload.tenant_id,
                    purpose="blueprint_reuse",
                    context={
                        "query": payload.pergunta,
                        "semantic_similarity_score": qie_score,
                        "blueprint_compatibility_score": qie_score,
                        "expected_confidence": qie_score,
                        "fresh_data_required": bool(fresh_ai_required),
                        "freshness_requirement_score": 100 if fresh_ai_required else 0,
                        "blueprint_valid": True,
                        "blueprint_compatible": qie_score >= BLUEPRINT_DIRECT_REUSE_THRESHOLD,
                        "blueprint_id": matched_bp.id,
                        "blueprint_version": getattr(payload, "blueprint_version", None),
                        "semantic_version": getattr(payload, "semantic_version", None),
                        "metrics": list(matched_bp.metrics),
                        "dimensions": list(matched_bp.group_by),
                        "filters": dict(matched_bp.filters),
                        "reusable_payload": {"blueprint_id": matched_bp.id},
                    },
                    force_ai=False,
                    allow_response_reuse=False,
                )
            
            if matched_bp and aim_blueprint_decision and aim_blueprint_decision.strategy == "BLUEPRINT_ONLY":
                logger.info(
                    "[QIE] [AIM REUSO] Blueprint reutilizado por decisao AIM | blueprint=%s | reason=%s",
                    matched_bp.id,
                    aim_blueprint_decision.reason,
                )
                blueprint_reused = True
                reused_bp_id = matched_bp.id
                
                # ReconstrÃ³i a intenÃ§Ã£o a partir do blueprint
                clean_params = {}
                for k, v in matched_bp.filters.items():
                    if isinstance(v, list):
                        if v:
                            clean_params[k] = ",".join(str(item) for item in v)
                    elif v is not None:
                        clean_params[k] = str(v)

                resolved_bp_view = _resolve_blueprint_catalog_view(matched_bp, catalog_summaries)
                resolved_bp_view_id = getattr(resolved_bp_view, "id", None)
                reconstructed_intent = IntentionResponse(
                    view_catalog_id=resolved_bp_view_id,
                    confianca=0.99,
                    parametros=clean_params,
                    justificativa=f"[Blueprint Reutilizado] A pergunta Ã© semelhante a uma anÃ¡lise anterior ({matched_bp.nome_consulta}).",
                    fora_de_escopo=False,
                    operacao=matched_bp.tipo_analise,
                    entidade_alvo=_entity_from_blueprint(matched_bp),
                    nivel_confianca="ALTA",
                    telemetry={
                        "aim_strategy": aim_blueprint_decision.strategy,
                        "aim_decision_id": aim_blueprint_decision.decision_id,
                        "aim_reason": aim_blueprint_decision.reason,
                    },
                )
                
                # Restaura plano estruturado
                from services.ai_service import StructuredPlanSchema, PlanFiltersSchema, PlanVisualizationSchema
                reconstructed_intent.plano_estruturado = StructuredPlanSchema(
                    request_id=str(query_id),
                    intent=matched_bp.nome_consulta,
                    query_type=matched_bp.tipo_analise,
                    metrics=list(matched_bp.metrics),
                    group_by=list(matched_bp.group_by),
                    filters=PlanFiltersSchema(
                        date_range=matched_bp.filters.get("date_range", ""),
                        products=matched_bp.filters.get("products", []),
                        customers=matched_bp.filters.get("customers", []),
                        regions=matched_bp.filters.get("regions", [])
                    ),
                    visualization=PlanVisualizationSchema(
                        type=matched_bp.visualization_type,
                        layout_priority="ALTA"
                    ),
                    requires_insight=True,
                    confidence_score=0.99
                )
                intentions = [reconstructed_intent]
            else:
                if matched_bp and fresh_ai_required:
                    logger.info("[QIE] Blueprint candidato ignorado porque a pergunta exige NLU fresco: %s", matched_bp.id)
                elif matched_bp and aim_blueprint_decision:
                    logger.info(
                        "[QIE] Blueprint candidato rejeitado pelo AIM | blueprint=%s | strategy=%s | reason=%s",
                        matched_bp.id,
                        aim_blueprint_decision.strategy,
                        aim_blueprint_decision.reason,
                    )
                elif matched_bp:
                    logger.info(
                        "[QIE] Blueprint candidato abaixo do limiar seguro (score=%.2f, min=%.2f). Chamando NLU.",
                        qie_score,
                        BLUEPRINT_DIRECT_REUSE_THRESHOLD,
                    )
                try:
                    intentions_func = intent_identifier or identify_intention
                    intentions = await intentions_func(
                        pergunta=payload.pergunta,
                        catalog=catalog_summaries,
                        api_key=ia_api_key,
                        model=ia_model,
                        temperature=ia_temp,
                        custom_instructions=instrucoes_finais,
                        tenant_id=payload.tenant_id,
                        history=history_list,
                        request_id=str(query_id),
                        user_id=current_user.id,
                        session_id=session_id,
                    )
                    intentions = copy.deepcopy(intentions or [])
                    if intentions and any(i.confianca > 0.0 for i in intentions):
                        try:
                            global_cache.set(
                                payload.tenant_id,
                                "nlu",
                                nlu_cache_key,
                                copy.deepcopy(intentions),
                                ttl_seconds=600,
                                semantic_version=getattr(payload, "semantic_version", None),
                                blueprint_version=getattr(payload, "blueprint_version", None)
                            )
                        except Exception as cache_set_err:
                            logger.error("Falha ao salvar cache NLU: %s", cache_set_err)
                except ModelViolationError as exc:
                    logger.error("ERRO DE ROTEAMENTO DE MODELO: %s", exc)
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
                except AIServiceError as exc:
                    logger.error("Falha no Motor de IntenÃ§Ã£o: %s", exc)
                    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

        nlu_tempo = int((time.perf_counter() - nlu_inicio) * 1000)
        
        # â”€â”€ 1.5. Context Guard / Scope & Direct Response Checks â”€â”€
        if not intentions:
            intentions = [IntentionResponse(
                view_catalog_id=None,
                confianca=0.0,
                parametros={},
                justificativa="NÃ£o foi possÃ­vel identificar nenhuma intenÃ§Ã£o.",
                fora_de_escopo=False,
            )]
            
        primary_intention = intentions[0]
        source_intent_telemetry = dict(primary_intention.telemetry or {})
        
        # Verifica bloqueio fora de escopo
        if any(i.fora_de_escopo for i in intentions):
            blocked_intention = next(i for i in intentions if i.fora_de_escopo)
            logger.warning("Pergunta fora do escopo bloqueada | pergunta=%r", payload.pergunta[:60])
            tempo_ms = int((time.perf_counter() - total_inicio) * 1000)
            
            # Persiste histÃ³rico assincronamente via helper local do router
            background_tasks.add_task(
                persist_query_history,
                user_id=current_user.id,
                view_catalog_id=None,
                pergunta=payload.pergunta,
                parametros={"_bloqueado": "fora_de_escopo"},
                confianca=0.0,
                tempo_ms=tempo_ms,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=blocked_intention.mensagem_bloqueio or "Esta consulta estÃ¡ fora do escopo autorizado."
            )

        # Valida os parÃ¢metros extraÃ­dos pela IA contra injeÃ§Ãµes SQL e termos proibidos (Context Guard)
        try:
            from services.context_guard import validate_params, ScopeViolationError
            for intention in intentions:
                if not intention.fora_de_escopo and intention.parametros:
                    intention.parametros = validate_params(intention.parametros)
        except ScopeViolationError as scope_err:
            logger.warning("ParÃ¢metros bloqueados pelo Context Guard: %s", scope_err)
            tempo_ms = int((time.perf_counter() - total_inicio) * 1000)
            background_tasks.add_task(
                persist_query_history,
                user_id=current_user.id,
                view_catalog_id=None,
                pergunta=payload.pergunta,
                parametros={"_bloqueado": "context_guard_violacao"},
                confianca=0.0,
                tempo_ms=tempo_ms,
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(scope_err))
            
        # Resposta direta (pergunta conceitual sem dados)
        if primary_intention.resposta_direta and not primary_intention.view_catalog_id:
            tempo_ms = int((time.perf_counter() - total_inicio) * 1000)
            background_tasks.add_task(
                persist_query_history,
                user_id=current_user.id,
                view_catalog_id=None,
                pergunta=payload.pergunta,
                parametros={"_tipo": "resposta_direta"},
                confianca=primary_intention.confianca,
                tempo_ms=tempo_ms,
            )
            from services.query_planner import QueryPlan, QueryPlanItem, _suggest_visualizacao
            sugestao_vis = _suggest_visualizacao(
                primary_intention.operacao or "SOMA",
                primary_intention.entidade_alvo or "VENDA",
                "TABLE"
            )
            dummy_item = QueryPlanItem(
                id="principal",
                objetivo="Resposta conceitual direta",
                prioridade="ALTA",
                sugestao_visualizacao=sugestao_vis
            )
            dummy_plan = QueryPlan(
                consulta_principal=dummy_item,
                ordem_execucao=[["principal"]]
            )
            direct_telemetry = response_builder.build_response_metadata(
                mode=response_mode,
                confidence_score=primary_intention.confianca,
                confidence_status=(primary_intention.telemetry or {}).get("confidence_status")
                if getattr(primary_intention, "telemetry", None) else None,
                tokens_consumed=(primary_intention.telemetry or {}).get("tokens_consumed", 0)
                if getattr(primary_intention, "telemetry", None) else 0,
                timings={
                    "intent_engine": nlu_tempo,
                    "total_pipeline": tempo_ms,
                },
            )
            return QueryResponse(
                query_id=query_id,
                request_id=query_id,
                view_catalog_id=None,
                view_name=None,
                chart_type=None,
                chart_data={"resposta_direta": primary_intention.resposta_direta},
                parametros_extraidos={},
                ia_confianca=primary_intention.confianca,
                ia_justificativa=primary_intention.justificativa,
                pergunta_original=payload.pergunta,
                pode_favoritar=False,
                resposta_direta=primary_intention.resposta_direta,
                mensagem=None,
                telemetry=direct_telemetry,
                plano_nlu=[
                    SchemaIntentionPlanItem(
                        view_catalog_id=i.view_catalog_id,
                        confianca=i.confianca,
                        operacao=i.operacao or "SOMA",
                        entidade_alvo=i.entidade_alvo or "VENDA",
                        quantidade_limite=i.quantidade_limite,
                        periodo_referencia=i.periodo_referencia,
                        is_comparacao=i.is_comparacao,
                        comparativo_detalhe=i.comparativo_detalhe,
                        nivel_confianca=i.nivel_confianca or "ALTA",
                        filtros=i.parametros,
                        justificativa=i.justificativa
                    ) for i in intentions
                ],
                plano_execucao=dummy_plan.model_dump()
            )

        # --- 1.8. CSIE Layer ---
        from services.ai.csie import csie
        cip, csie_score, csie_origem = await csie.generate_corporate_intent_plan(
            pergunta=payload.pergunta,
            tenant_id=payload.tenant_id,
            db=db,
            context={
                "session_id": session_id,
                "user_id": str(current_user.id),
                "tenant_id": str(payload.tenant_id),
                "source_intent": primary_intention.model_dump() if hasattr(primary_intention, "model_dump") else {},
                "source_telemetry": source_intent_telemetry,
            },
        )
        csie_obj = cip.to_legacy_semantic_plan()
        csie_score = float(csie_score)
        csie_score_norm = csie_score / 100.0 if csie_score > 1 else csie_score
        csie_has_conceptual_plan = bool(
            csie_obj.get("metrics")
            or csie_obj.get("dimensions")
            or csie_obj.get("period")
            or csie_obj.get("filters")
        )
        csie_telemetry = {
            "csie_origin": csie_origem,
            "csie_confidence_score": csie_score_norm,
            "csie_tokens_consumed": int(cip.audit.get("tokens_consumed", 0) or 0),
            "corporate_intent_plan": cip.model_dump(),
            "semantic_scores": cip.scores.model_dump(),
            "semantic_hypotheses": [h.model_dump() for h in cip.hypotheses],
            "semantic_ambiguity_level": cip.ambiguity_level,
            "semantic_confidence_level": cip.confidence_level,
        }
        primary_intention.telemetry = {
            **source_intent_telemetry,
            **dict(primary_intention.telemetry or {}),
            **csie_telemetry,
        }
        source_intent_telemetry = dict(primary_intention.telemetry or {})

        # Nova politica: nao rejeita automaticamente por score semantico.
        # So solicita esclarecimento quando nao existe plano conceitual minimo.
        if csie_score_norm < 0.50 and primary_intention.confianca < 0.50 and not csie_has_conceptual_plan:
            direct_telemetry = response_builder.build_response_metadata(
                mode=response_mode,
                confidence_score=csie_score_norm,
                confidence_status="INSUFFICIENT_CONCEPTUAL_PLAN",
                timings={"csie": int((time.perf_counter() - nlu_inicio) * 1000)}
            )
            direct_telemetry.update(csie_telemetry)
            return QueryResponse(
                query_id=query_id,
                request_id=query_id,
                view_catalog_id=None,
                view_name=None,
                chart_type=None,
                chart_data={"clarification_required": True, "options": []},
                parametros_extraidos={},
                ia_confianca=csie_score_norm,
                ia_justificativa="Plano conceitual insuficiente para encaminhar a analise.",
                pergunta_original=payload.pergunta,
                pode_favoritar=False,
                resposta_direta="Poderia detalhar um pouco mais a sua pergunta? Ainda nao identifiquei conceitos corporativos suficientes para montar a analise.",
                mensagem=None,
                telemetry=direct_telemetry
            )

        # --- 1.9. AQD (Analytical Query Decomposer) Layer ---
        from services.aqd_service import aqd
        aqd_res = aqd.decompose(
            payload.pergunta,
            catalog_summaries,
            payload.tenant_id,
            corporate_intent_plan=cip,
            semantic_hypotheses=cip.hypotheses,
        )
        
        if aqd_res.decomposed:
            logger.info("[AQD] Pergunta complexa detectada. Iniciando decomposiÃ§Ã£o em %d tarefas analÃ­ticas.", len(aqd_res.tasks))
            decomposed_intentions = []
            for idx, task in enumerate(aqd_res.tasks, start=1):
                view_obj = next((v for v in catalog_summaries if v.nome_view_oracle == task.fonte_sugerida), None)
                v_id = view_obj.id if view_obj else None
                
                t_params = {}
                if primary_intention and primary_intention.parametros:
                    t_params = primary_intention.parametros.copy()
                
                from services.ai_service import IntentionResponse, StructuredPlanSchema, PlanFiltersSchema, PlanVisualizationSchema
                
                sim_intent = IntentionResponse(
                    entidade_alvo=task.objetivo,
                    operacao="SELECT",
                    visualizacao_preferida=task.estrategia_visual,
                    justificativa=task.descricao,
                    confianca=0.95,
                    view_catalog_id=v_id,
                    parametros=t_params,
                    chart_types_solicitados=[task.estrategia_visual],
                    chart_type_sobrescrever=task.estrategia_visual
                )
                if idx == 1 and source_intent_telemetry:
                    sim_intent.telemetry = source_intent_telemetry
                
                sim_intent.plano_estruturado = StructuredPlanSchema(
                    request_id=str(query_id),
                    intent=task.objetivo,
                    query_type="SELECT",
                    metrics=[m for m in task.corporate_ids if "MET" in m] or ["receita_total"],
                    group_by=[d for d in task.corporate_ids if "DIM" in d],
                    filters=PlanFiltersSchema(
                        date_range=t_params.get("date_range", "este mÃªs"),
                        products=[t_params.get("produto_nome")] if "produto_nome" in t_params else [],
                        customers=[t_params.get("cliente_nome")] if "cliente_nome" in t_params else [],
                        regions=[t_params.get("regiao")] if "regiao" in t_params else []
                    ),
                    visualization=PlanVisualizationSchema(
                        type=task.estrategia_visual,
                        layout_priority="ALTA" if idx == 1 else "MEDIA"
                    ),
                    requires_insight=True,
                    confidence_score=0.95
                )
                decomposed_intentions.append(sim_intent)
            
            intentions = decomposed_intentions
            primary_intention = intentions[0]

        explicit_row_limit = _extract_explicit_row_limit(payload.pergunta)
        _sync_metric_ordering_params(intentions, payload.pergunta)
        _apply_explicit_row_limit(intentions, explicit_row_limit)

        # â”€â”€ 2. Planner â”€â”€
        planner_inicio = time.perf_counter()
        query_plan = create_query_plan(intentions, catalog_summaries)
        if aqd_res.decomposed:
            query_plan = query_plan.model_copy(update={"master_blueprint": aqd_res.master_blueprint})
        planner_tempo = int((time.perf_counter() - planner_inicio) * 1000)
        
        # â”€â”€ 3. Validator â”€â”€
        validator_inicio = time.perf_counter()
        for intention in intentions:
            if not intention.fora_de_escopo and not intention.resposta_direta:
                if not intention.plano_estruturado:
                    from services.ai_service import StructuredPlanSchema, PlanFiltersSchema, PlanVisualizationSchema
                    date_range_val = ""
                    if intention.parametros and ("data_inicio" in intention.parametros or "data_fim" in intention.parametros):
                        date_range_val = f"{intention.parametros.get('data_inicio', '')} to {intention.parametros.get('data_fim', '')}"
                    
                    intention.plano_estruturado = StructuredPlanSchema(
                        request_id=str(query_id),
                        intent=intention.justificativa or "consulta automÃ¡tica",
                        query_type="AGGREGATION" if intention.operacao in ("SOMA", "MEDIA", "TOTAL") else "SELECT",
                        metrics=[intention.operacao.lower()] if intention.operacao else [],
                        group_by=[intention.entidade_alvo.lower()] if intention.entidade_alvo else [],
                        filters=PlanFiltersSchema(
                            date_range=date_range_val,
                            products=[intention.parametros.get("produto_nome")] if (intention.parametros and "produto_nome" in intention.parametros) else [],
                            customers=[intention.parametros.get("cliente_nome")] if (intention.parametros and "cliente_nome" in intention.parametros) else [],
                            regions=[intention.parametros.get("regiao")] if (intention.parametros and "regiao" in intention.parametros) else []
                        ),
                        visualization=PlanVisualizationSchema(
                            type=intention.visualizacao_preferida or "TABLE",
                            layout_priority="ALTA"
                        ),
                        requires_insight=True,
                        confidence_score=intention.confianca
                    )
                
                view_name_validator = ""
                if intention.view_catalog_id:
                    view_obj = next((v for v in catalog_summaries if v.id == intention.view_catalog_id), None)
                    if view_obj:
                        view_name_validator = view_obj.nome_view_oracle
                
                # Traduz IDs corporativos para chaves de execucao via CAL quando existe plano conceitual.
                if csie_has_conceptual_plan:
                    preserve_structured_plan = bool(
                        intention.view_catalog_id
                        and intention.confianca >= 0.90
                        and intention.plano_estruturado
                        and (
                            intention.plano_estruturado.metrics
                            or intention.plano_estruturado.group_by
                        )
                    )
                    physical_plan = await csie.translate_plan_to_physical(
                        stable_plan=csie_obj,
                        view_name=view_name_validator,
                        tenant_id=payload.tenant_id,
                        meta_catalog=catalog_summaries,
                        db=db,
                        semantic_version=getattr(payload, "semantic_version", None),
                        blueprint_version=getattr(payload, "blueprint_version", None)
                    )
                    
                    if physical_plan["metrics"] and not preserve_structured_plan:
                        intention.plano_estruturado.metrics = physical_plan["metrics"]
                    if physical_plan["group_by"] and not preserve_structured_plan:
                        intention.plano_estruturado.group_by = physical_plan["group_by"]
                    if physical_plan["filters"]:
                        for k_f, v_f in physical_plan["filters"].items():
                            if k_f == "date_range":
                                intention.plano_estruturado.filters.date_range = v_f
                            elif k_f in ("produto", "products"):
                                intention.plano_estruturado.filters.products = v_f if isinstance(v_f, list) else [v_f]
                            elif k_f in ("cliente", "customers"):
                                intention.plano_estruturado.filters.customers = v_f if isinstance(v_f, list) else [v_f]
                            elif k_f in ("regiao", "regions"):
                                intention.plano_estruturado.filters.regions = v_f if isinstance(v_f, list) else [v_f]
                        
                validated_res = validate_and_normalize_plan(
                    intention.plano_estruturado,
                    query_text=payload.pergunta,
                    view_name=view_name_validator,
                    catalog=catalog_summaries,
                    tenant_id=payload.tenant_id,
                )
                
                if not validated_res.validated:
                    if validated_res.suggested_refinement == "AQD_DECOMPOSITION_TRIGGERED":
                        from services.aqd_service import aqd
                        aqd_res_reactive = aqd.decompose(
                            payload.pergunta,
                            catalog_summaries,
                            payload.tenant_id,
                            corporate_intent_plan=cip,
                            semantic_hypotheses=cip.hypotheses,
                        )
                        if aqd_res_reactive.decomposed:
                            logger.info("[QIE] Re-decomposiÃ§Ã£o reativa do validador aceita com sucesso.")
                            # Simula as intenÃ§Ãµes decompostas do AQD
                            decomposed_intentions = []
                            for idx, task in enumerate(aqd_res_reactive.tasks, start=1):
                                view_obj = next((v for v in catalog_summaries if v.nome_view_oracle == task.fonte_sugerida), None)
                                v_id = view_obj.id if view_obj else None
                                t_params = {}
                                if primary_intention and primary_intention.parametros:
                                    t_params = primary_intention.parametros.copy()
                                from services.ai_service import IntentionResponse, StructuredPlanSchema, PlanFiltersSchema, PlanVisualizationSchema
                                sim_intent = IntentionResponse(
                                    entidade_alvo=task.objetivo,
                                    operacao="SELECT",
                                    visualizacao_preferida=task.estrategia_visual,
                                    justificativa=task.descricao,
                                    confianca=0.95,
                                    view_catalog_id=v_id,
                                    parametros=t_params,
                                    chart_types_solicitados=[task.estrategia_visual],
                                    chart_type_sobrescrever=task.estrategia_visual
                                )
                                if idx == 1 and source_intent_telemetry:
                                    sim_intent.telemetry = source_intent_telemetry
                                sim_intent.plano_estruturado = StructuredPlanSchema(
                                    request_id=str(query_id),
                                    intent=task.objetivo,
                                    query_type="SELECT",
                                    metrics=[m for m in task.corporate_ids if "MET" in m] or ["receita_total"],
                                    group_by=[d for d in task.corporate_ids if "DIM" in d],
                                    filters=PlanFiltersSchema(
                                        date_range=t_params.get("date_range", "este mÃªs"),
                                        products=[t_params.get("produto_nome")] if "produto_nome" in t_params else [],
                                        customers=[t_params.get("cliente_nome")] if "cliente_nome" in t_params else [],
                                        regions=[t_params.get("regiao")] if "regiao" in t_params else []
                                    ),
                                    visualization=PlanVisualizationSchema(
                                        type=task.estrategia_visual,
                                        layout_priority="ALTA" if idx == 1 else "MEDIA"
                                    ),
                                    requires_insight=True,
                                    confidence_score=0.95
                                )
                                decomposed_intentions.append(sim_intent)
                            
                            intentions = decomposed_intentions
                            primary_intention = intentions[0]
                            # Recria o query_plan
                            query_plan = create_query_plan(intentions, catalog_summaries)
                            query_plan = query_plan.model_copy(update={"master_blueprint": aqd_res_reactive.master_blueprint})
                            validated_res.validated = True
                            break

                    logger.warning("Plano estruturado rejeitado pelo validador: %s. Tentando regeneraÃ§Ã£o...", validated_res.suggested_refinement)
                    try:
                        prompt_regen = (
                            f"{payload.pergunta}\n\n"
                            f"[SISTEMA: O plano estruturado anterior foi REJEITADO devido a erros: "
                            f"{validated_res.suggested_refinement}. Por favor, refaÃ§a a anÃ¡lise e gere um plano 100% vÃ¡lido, "
                            f"garantindo que o request_id do plano seja exatamente '{str(query_id)}'.]"
                        )
                        regenerated = await identify_intention(
                            pergunta=prompt_regen,
                            catalog=catalog_summaries,
                            api_key=ia_api_key,
                            model=ia_model,
                            temperature=ia_temp,
                            custom_instructions=instrucoes_finais,
                            tenant_id=payload.tenant_id,
                            history=history_list,
                            request_id=str(query_id),
                            user_id=current_user.id,
                            session_id=session_id,
                        )
                        regenerated = copy.deepcopy(regenerated or [])
                        if regenerated and regenerated[0].plano_estruturado:
                            validated_res_regen = validate_and_normalize_plan(
                                regenerated[0].plano_estruturado,
                                query_text=payload.pergunta,
                                view_name=view_name_validator,
                                catalog=catalog_summaries,
                                tenant_id=payload.tenant_id,
                            )
                            if validated_res_regen.validated:
                                logger.info("Plano estruturado regenerado e validado com sucesso!")
                                intentions = regenerated
                                primary_intention = intentions[0]
                                validated_res = validated_res_regen
                                break
                    except Exception as regen_err:
                        logger.error("Falha ao tentar regenerar plano estruturado: %s", regen_err)
                        
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"O plano estruturado de consulta foi rejeitado: {validated_res.suggested_refinement or 'InformaÃ§Ã£o insuficiente.'}"
                    )
                
                # Sincroniza correÃ§Ãµes no plano estruturado
                from services.ai_service import PlanFiltersSchema, PlanVisualizationSchema
                intention.plano_estruturado.metrics = validated_res.metrics
                intention.plano_estruturado.group_by = validated_res.group_by
                intention.plano_estruturado.filters = PlanFiltersSchema(
                    date_range=validated_res.filters.get("date_range", ""),
                    products=validated_res.filters.get("products", []),
                    customers=validated_res.filters.get("customers", []),
                    regions=validated_res.filters.get("regions", [])
                )
                intention.plano_estruturado.visualization = PlanVisualizationSchema(
                    type=validated_res.visualization.get("type", "TABLE"),
                    layout_priority=validated_res.visualization.get("layout_priority", "ALTA")
                )
                
                # Adapta parÃ¢metros legado
                p_dict = dict(intention.parametros or {})
                dr = validated_res.filters.get("date_range", "")
                if dr:
                    match_dates = re.search(r"(\d{4}-\d{2}-\d{2})\s*(?:to|ate|a|-)\s*(\d{4}-\d{2}-\d{2})", dr)
                    if match_dates:
                        p_dict["data_inicio"] = match_dates.group(1)
                        p_dict["data_fim"] = match_dates.group(2)
                if validated_res.filters.get("products"):
                    p_dict["produto_nome"] = validated_res.filters["products"][0]
                if validated_res.filters.get("customers"):
                    p_dict["cliente_nome"] = validated_res.filters["customers"][0]
                if validated_res.filters.get("regions"):
                    region_value = validated_res.filters["regions"][0]
                    if "cidade" in normalize_text_key(payload.pergunta or ""):
                        p_dict["cidade"] = region_value
                        p_dict.pop("regiao", None)
                    else:
                        p_dict["regiao"] = region_value
                    
                intention.parametros = p_dict
                intention.visualizacao_preferida = validated_res.visualization.get("type", "TABLE")
                
        _sync_temporal_params(intentions, payload.pergunta)
        _sync_geographic_params(intentions, payload.pergunta)
        _sync_metric_ordering_params(intentions, payload.pergunta)
        _sanitize_intention_params(intentions)
        _apply_explicit_row_limit(intentions, explicit_row_limit)
        current_master_blueprint = getattr(query_plan, "master_blueprint", None)
        query_plan = create_query_plan(intentions, catalog_summaries)
        if current_master_blueprint:
            query_plan = query_plan.model_copy(update={"master_blueprint": current_master_blueprint})

        validator_tempo = int((time.perf_counter() - validator_inicio) * 1000)
        
        # â”€â”€ 3.5. Intelligent Analytical Resolver (IAR) â”€â”€
        iar_inicio = time.perf_counter()
        iar_tempo = 0
        try:
            from services.iar_service import iar
            query_plan = await iar.resolve_incompatibilities(
                query_plan=query_plan,
                intentions=intentions,
                catalog=catalog_summaries,
                tenant_id=payload.tenant_id,
                db=db,
                original_query=payload.pergunta,
                arp=aqd_res.arp
            )
        except Exception as iar_exc:
            logger.error("Falha na execucao do IAR: %s", iar_exc)
        iar_tempo = int((time.perf_counter() - iar_inicio) * 1000)
        
        # â”€â”€ 4. Business Layer â”€â”€
        business_inicio = time.perf_counter()
        from services.data_platform import business_layer, blueprint_resolver, execution_engine, insight_layer, dashboard_builder
        await business_layer.apply_business_rules(query_plan, payload.tenant_id, db)
        
        # â”€â”€ 5. Blueprint Resolver â”€â”€
        blueprint_reused = False
        reused_bp_id = None
        active_bp_intent_id = None
        
        primary_view_name = query_plan.consulta_principal.view_name
        if primary_view_name:
            resolved_bp = await blueprint_resolver.resolve_blueprint(payload.tenant_id, primary_view_name, db)
            if resolved_bp:
                blueprint_reused = True
                reused_bp_id = resolved_bp.intent_id
                active_bp_intent_id = resolved_bp.intent_id
                logger.info("[BlueprintResolver] Reutilizando Blueprint da view: %s", primary_view_name)
            else:
                # Cria novo Blueprint e salva na Data Platform se nÃ£o existir
                if primary_intention.plano_estruturado and validated_res.validated:
                    try:
                        new_bp = self.create_blueprint_from_intention(primary_intention, payload.pergunta, validated_res, catalog_summaries)
                        from services.data_platform import blueprint_repository
                        from services.data_platform.catalog_api import catalog_api
                        saved_bp = await blueprint_repository.save_blueprint(payload.tenant_id, new_bp, db)
                        active_bp_intent_id = saved_bp.intent_id
                        await catalog_api.register(
                            tenant_id=payload.tenant_id,
                            tipo="VIEW",
                            dados={
                                "estrutura_id": new_bp.view_name,
                                "nome_view": new_bp.view_name,
                                "origem": "ERP_ORACLE",
                                "owner": "QueryIntelligenceEngine",
                                "categoria": new_bp.tipo_analise or "Geral",
                                "tags": ["view", "blueprint-source"],
                                "tabelas_utilizadas": [new_bp.view_name.replace("VW_", "")],
                                "kpis_suportados": new_bp.metrics,
                                "dependencias": [new_bp.view_name.replace("VW_", "")],
                            },
                            lineage_tabelas=[new_bp.view_name.replace("VW_", "")],
                            upstream_ids=[new_bp.view_name.replace("VW_", "")],
                        )
                        logger.info("[BlueprintResolver] Novo Blueprint criado e persistido no banco de dados!")
                    except Exception as exc:
                        logger.error("[BlueprintResolver] Falha ao registrar novo blueprint: %s", exc)
                        
        backend_tempo = int((time.perf_counter() - business_inicio) * 1000)
        
        # Ã¢â€â‚¬Ã¢â€â‚¬ 6. Execution Engine & Data Access Layer Ã¢â€â‚¬Ã¢â€â‚¬
        dp_inicio = time.perf_counter()
        resultados = await execution_engine.execute_blueprint(tenant, query_plan, db)
        dp_tempo = int((time.perf_counter() - dp_inicio) * 1000)
        
        # O ExecutionEngine registra uso e tempo real de consulta no Metadata Catalog.
        
        # Ã¢â€â‚¬Ã¢â€â‚¬ 7. Insight Layer & Dashboard Builder Ã¢â€â‚¬Ã¢â€â‚¬
        vis_inicio = time.perf_counter()
        
        # BI deterministico e calculado pelo backend antes do Insight Layer.
        ia_analise = None
        bi_intelligence = {}
        outcomes = resultados.get("principal")
        if outcomes:
            from services.bi_engine import process_bi_intelligence
            bi_intelligence = process_bi_intelligence(outcomes.get("raw_rows") or [], outcomes["view_name"])

            if primary_intention.plano_estruturado and primary_intention.plano_estruturado.requires_insight:
                ia_analise, bi_intelligence = await insight_layer.generate_insights(
                    pergunta=payload.pergunta,
                    resultados_dict=resultados,
                    principal_view_name=outcomes["view_name"],
                    api_key=ia_api_key,
                    model=ia_model,
                    tenant_id=payload.tenant_id,
                    history=history_list,
                    custom_instructions=instrucoes_finais,
                    mode=response_mode,
                    bi_intelligence=bi_intelligence,
                )

        # Dashboard Builder (Dashboard Schema)
        dash_schema = dashboard_builder.build_dashboard_schema(resultados, primary_intention, query_plan)
        vis_tempo = int((time.perf_counter() - vis_inicio) * 1000)

        # --- PROCESSAMENTO ANALÃTICO CORPORATIVO (FIM DO PIPELINE) ---
        from services.data_platform.dataset_builder import dataset_builder
        from services.data_platform.analytics_engine import analytics_engine
        from services.data_platform.dashboard_payload_builder import dashboard_payload_builder

        builder_datasets = {}
        for q_id, res_item in resultados.items():
            if q_id == "principal":
                continue
            builder_datasets[q_id] = dataset_builder.build_dataset(
                tenant_id=payload.tenant_id,
                raw_rows=res_item["raw_rows"],
                view_name=res_item["view_name"]
            )

        analytics_results = {}
        try:
            analytics_results = await analytics_engine.process_analytics(
                tenant_id=payload.tenant_id,
                datasets=builder_datasets,
                blueprint=query_plan
            )
        except Exception as ae_exc:
            logger.error("[QIE] AnalyticsEngine falhou (nÃ£o crÃ­tico): %s", ae_exc)

        dashboard_payload = {}
        try:
            dashboard_payload = dashboard_payload_builder.build_payload(
                tenant_id=payload.tenant_id,
                datasets=builder_datasets,
                primary_intention=primary_intention,
                analytics_results=analytics_results
            )
        except Exception as dpb_exc:
            logger.error("[QIE] DashboardPayloadBuilder falhou (nÃ£o crÃ­tico): %s", dpb_exc)

        
        # Registra sucesso da estratÃ©gia executada para aprendizado controlado
        try:
            from services.aqd_service import record_strategy_success
            if 'aqd_res' in locals() and aqd_res.arp:
                for intent in aqd_res.arp.intencoes:
                    for strat in intent.estrategias_candidatas:
                        if query_plan.consulta_principal.view_name in strat.views_utilizadas:
                            record_strategy_success(strat.id, success=True, elapsed_time_ms=int((time.perf_counter() - total_inicio) * 1000))
        except Exception as learn_exc:
            logger.error("Falha ao registrar aprendizado controlado do AQD: %s", learn_exc)

        # â”€â”€ 8.5. Response Intelligence Suite (RIS) â”€â”€
        ris_tempo = 0
        ris_result_dict = {}
        ris_package = None
        try:
            from services.ris_service import ris
            # Calcula o tempo total aproximado atÃ© o momento para a engine de SLA da RIS
            current_elapsed_ms = int((time.perf_counter() - total_inicio) * 1000)
            telemetry_data = {
                "tempo_total_ms": current_elapsed_ms,
                "tokens_utilizados": 12500,  # Estimativa de tokens consumidos
            }
            ris_res = ris.process_response(
                tenant_id=payload.tenant_id,
                query_text=payload.pergunta,
                query_plan=query_plan,
                resultados_dict=resultados,
                dashboard_payload=dashboard_payload,
                analytics_results=analytics_results,
                ia_analise=ia_analise,
                arp=getattr(aqd_res, 'arp', None) if 'aqd_res' in locals() else None,
                telemetry=telemetry_data
            )
            ris_result_dict = ris_res.model_dump()
            ris_package = ris_res.package
            ris_tempo = ris_res.tempo_validacao_ms
            logger.info("[RIS] QualificaÃ§Ã£o analÃ­tica completa executada! Trust Score: %s | SLA Score: %s", ris_res.trust.score, ris_res.sla.score)
        except Exception as ris_exc:
            logger.error("Falha ao executar Response Intelligence Suite (RIS): %s", ris_exc)

        # â”€â”€ 8. Logs & Traceability â”€â”€
        tempo_total_ms = int((time.perf_counter() - total_inicio) * 1000)
        logger.info(
            "[PIPELINE LOGS] ExecuÃ§Ã£o concluÃ­da | "
            "Tempo Total: %dms | "
            "Tempo IA/SemÃ¢ntica: %dms | "
            "Tempo Planner: %dms | "
            "Tempo Validator: %dms | "
            "Tempo Backend (Business + Resolver): %dms | "
            "Tempo Data Platform (Execution + DAL): %dms | "
            "Tempo Insights/Dashboard: %dms",
            tempo_total_ms, nlu_tempo, planner_tempo, validator_tempo,
            backend_tempo, dp_tempo, vis_tempo
        )
        
        # Registra estatÃ­sticas
        try:
            if blueprint_reused and reused_bp_id:
                self.register_blueprint_usage(
                    blueprint_id=reused_bp_id,
                    execution_time_ms=float(tempo_total_ms),
                    tokens_saved=1500,
                    reused_directly=True
                )
            else:
                self.execucoes_com_ia += 1
                self.tempo_total_com_ia_ms += float(tempo_total_ms)
                self.save_blueprints()
        except Exception as e:
            logger.error("[QIE] Falha ao registrar estatÃ­sticas: %s", e)

        try:
            if active_bp_intent_id:
                from services.data_platform import blueprint_repository
                await blueprint_repository.register_usage(
                    tenant_id=payload.tenant_id,
                    intent_id=active_bp_intent_id,
                    db_session=db,
                    execution_time_ms=float(tempo_total_ms),
                    render_time_ms=float(vis_tempo),
                    tokens_saved=1500 if blueprint_reused else 0,
                )
        except Exception as bp_usage_exc:
            logger.error("[QIE] Falha ao atualizar perfil Enterprise do Blueprint: %s", bp_usage_exc)
            
        # -- 8.1. Analytical Package Registration (MISS Path) --------------------
        # Registra assincronamente o novo Analytical Package criado nesta execucao.
        # Esta etapa e NAO-BLOQUEANTE: falhas nao afetam a resposta ao usuario.
        try:
            from services.data_platform.intent_fingerprint import intent_fingerprint_generator as _ifg
            from services.data_platform.analytical_package_service import analytical_package_service as _aps
            _new_fingerprint = _ifg.generate(
                intention=primary_intention,
                plan=query_plan,
                pergunta=payload.pergunta,
            )
            _pipeline_result_for_pkg = {
                "dashboard_payload": dashboard_payload,
                "datasets": builder_datasets,
                "analytics_results": analytics_results,
                "bi_intelligence": bi_intelligence if bi_intelligence else {},
                "query_params": dict(primary_intention.parametros or {}),
                "pergunta_original": payload.pergunta,
                "execution_time_ms": tempo_total_ms,
                "blueprint_id": reused_bp_id,
                "blueprint_snapshot": {},
            }

            async def _create_package_bg():
                try:
                    from database import get_db_context
                    async with get_db_context() as _pkg_db:
                        await _aps.create_package(
                            tenant_id=payload.tenant_id,
                            fingerprint=_new_fingerprint,
                            intention=primary_intention,
                            plan=query_plan,
                            pipeline_result=_pipeline_result_for_pkg,
                            db=_pkg_db,
                        )
                    logger.info("[QIE] Analytical Package registrado com sucesso (MISS path)")
                except Exception as _pkg_bg_err:
                    logger.error("[QIE] Falha ao criar Analytical Package (nao critico): %s", _pkg_bg_err)

            background_tasks.add_task(_create_package_bg)
        except Exception as _pkg_reg_exc:
            logger.warning("[QIE] Registro de Package (MISS) falhou - nao critico: %s", _pkg_reg_exc)
        # -- Fim 8.1 ---------------------------------------------------------------

        # Persiste histÃ³rico
        background_tasks.add_task(
            persist_query_history,
            user_id=current_user.id,
            view_catalog_id=primary_intention.view_catalog_id,
            pergunta=payload.pergunta,
            parametros=primary_intention.parametros,
            confianca=primary_intention.confianca,
            tempo_ms=tempo_total_ms
        )
        
        # Monta a resposta final mapeando do Dashboard Schema
        visualizations_list = dash_schema["visualizations"]
        layout_schema = dash_schema["layout_schema"]
        
        primary_vis = visualizations_list[0] if visualizations_list else None
        
        # ParÃ¢metros extraÃ­dos unificados
        extracted_params = dict(primary_intention.parametros or {})
        if query_plan.consulta_principal.parametros:
            extracted_params = {**dict(query_plan.consulta_principal.parametros), **extracted_params}
        extracted_params = {k: v for k, v in extracted_params.items() if not str(k).startswith("_")}
            
        mensagem = None
        if not visualizations_list:
            mensagem = "NÃ£o consegui identificar uma anÃ¡lise correspondente Ã  sua pergunta."
            
        # Resolve view catalog e view name para o payload legado do response
        view_catalog_id = query_plan.consulta_principal.view_catalog_id
        view_name = query_plan.consulta_principal.view_name

        intent_telemetry = dict(primary_intention.telemetry or source_intent_telemetry or {})
        intent_timings = dict(intent_telemetry.get("timings_ms") or {})
        pipeline_telemetry = response_builder.build_response_metadata(
            mode=response_mode,
            confidence_score=primary_intention.confianca,
            confidence_status=intent_telemetry.get("confidence_status"),
            package_reused=False,
            package_id=intent_telemetry.get("package_id"),
            dashboard_instance_id=str(dashboard_payload.get("dashboard_instance_id"))
            if isinstance(dashboard_payload, dict) and dashboard_payload.get("dashboard_instance_id") else None,
            tokens_consumed=max(
                int(intent_telemetry.get("tokens_consumed", 0) or 0),
                int(intent_telemetry.get("csie_tokens_consumed", 0) or 0),
            ),
            timings={
                **intent_timings,
                "nlu": nlu_tempo,
                "planner": planner_tempo,
                "validator": validator_tempo,
                "iar": iar_tempo,
                "ris": ris_tempo if 'ris_tempo' in locals() else 0,
                "business_layer": backend_tempo,
                "data_platform": dp_tempo,
                "insight_dashboard": vis_tempo,
                "total_ai": nlu_tempo + planner_tempo + validator_tempo + iar_tempo + (ris_tempo if 'ris_tempo' in locals() else 0),
                "total_pipeline": tempo_total_ms,
            },
        )
        if 'ris_res' in locals():
            pipeline_telemetry.update({
                "ris_id": ris_res.ris_id,
                "ris_success": ris_res.success,
                "ris_freshness_score": ris_res.freshness.score,
                "ris_sufficiency_score": ris_res.sufficiency.score,
                "ris_sufficiency_class": ris_res.sufficiency.classification,
                "ris_consistency_score": ris_res.consistency.score,
                "ris_contradiction_score": ris_res.contradiction.score,
                "ris_validation_time_ms": ris_tempo
            })
        from services.performance.performance_optimization_platform import pop_platform
        pop_platform.record_latency("ia", nlu_tempo + planner_tempo + validator_tempo)
        pop_platform.record_latency("backend", backend_tempo)
        pop_platform.record_latency("data_platform", dp_tempo)

        pipeline_telemetry.update({
            "blueprint_reused": blueprint_reused,
            "blueprint_id": reused_bp_id,
            "nlu_cache_hit": nlu_cache_hit,
            "package_compatibility_score": intent_telemetry.get("package_compatibility_score"),
        })
        if 'csie_telemetry' in locals():
            pipeline_telemetry.update(csie_telemetry)

        if 'aqd_res' in locals():
            pipeline_telemetry.update({
                "aqd_decomposed": aqd_res.decomposed,
                "aqd_query_count": aqd_res.quantidade_consultas,
                "aqd_decomposition_time_ms": aqd_res.tempo_decomposicao_ms,
                "aqd_planning_time_ms": aqd_res.tempo_planejamento_ms,
                "arp_id": aqd_res.arp.arp_id if aqd_res.arp else None,
                "arp_strategies_count": sum(len(i.estrategias_candidatas) for i in aqd_res.arp.intencoes) if aqd_res.arp else 0
            })

        periodo_memoria = None
        if primary_intention.periodo_referencia:
            periodo_memoria = primary_intention.periodo_referencia
        elif primary_intention.plano_estruturado:
            periodo_memoria = getattr(primary_intention.plano_estruturado.filters, "date_range", None)

        memory_context_engine.save_session(
            user_id=current_user.id,
            tenant_id=payload.tenant_id,
            session_id=session_id,
            contexto_atual=payload.pergunta,
            filtros_ativos=extracted_params,
            periodo=periodo_memoria,
            kpis_utilizados=list(primary_intention.plano_estruturado.metrics)
            if primary_intention.plano_estruturado else [],
            dominio_negocio=primary_intention.entidade_alvo or "GERAL",
            blueprint_ativo=str(reused_bp_id) if reused_bp_id else None,
            dashboard_instance_ativa=pipeline_telemetry.get("dashboard_instance_id"),
            analytical_package_em_uso=pipeline_telemetry.get("package_id"),
            empresa=getattr(tenant, "nome", None),
        )

        from services.data_platform.trust_center_engine import trust_center_engine
        trust_center_data = await trust_center_engine.build_trust_center_data(
            tenant_id=payload.tenant_id,
            view_name=view_name,
            query_id=query_id,
            pergunta=payload.pergunta,
            query_plan=query_plan.model_dump() if query_plan else None,
            telemetry=pipeline_telemetry,
            response_time_ms=tempo_total_ms,
            package_reused=False,
            package_id=pipeline_telemetry.get("package_id"),
            package_compatibility_score=pipeline_telemetry.get("package_compatibility_score")
        )

        # Enriquece o trust_center com logs de auditoria do IAR
        try:
            from services.iar_service import iar
            if iar.auditor_logs:
                last_log = iar.auditor_logs[-1]
                if last_log.original_query == payload.pergunta:
                    if isinstance(trust_center_data, dict):
                        trust_center_data["iar_audit"] = last_log.model_dump()
        except Exception as iar_audit_exc:
            logger.error("Falha ao injetar auditoria do IAR no trust center: %s", iar_audit_exc)
        
        # Enriquece o trust_center com metadados do ARP
        try:
            if 'aqd_res' in locals() and aqd_res.arp:
                if isinstance(trust_center_data, dict):
                    trust_center_data["arp_plan"] = aqd_res.arp.model_dump()
        except Exception as arp_audit_exc:
            logger.error("Falha ao injetar plano ARP no trust center: %s", arp_audit_exc)
        
        # Enriquece o trust_center com logs da RIS
        try:
            if 'ris_result_dict' in locals() and ris_result_dict:
                if isinstance(trust_center_data, dict):
                    trust_center_data["ris_audit"] = ris_result_dict
        except Exception as ris_audit_exc:
            logger.error("Falha ao injetar auditoria da RIS no trust center: %s", ris_audit_exc)

        # â”€â”€ 9. Response Orchestrator & Quality Gate (ROQG) â”€â”€
        from services.roqg_service import roqg
        master_bp = getattr(query_plan, "master_blueprint", None)
        
        roqg_res = await roqg.process(
            tenant_id=payload.tenant_id,
            query_text=payload.pergunta,
            analytical_package=None,
            query_plan=query_plan,
            resultados_dict=resultados,
            master_blueprint=master_bp,
            ris_result=ris_result_dict if 'ris_result_dict' in locals() else {},
            ris_package=ris_package
        )
        
        # Enriquecimento de telemetria do ROQG
        pipeline_telemetry.update({
            "roqg_completeness_score": roqg_res.render_plan.completeness_score,
            "roqg_delivery_decision": roqg_res.render_plan.decision.value,
            "roqg_validation_steps_ms": roqg_res.validation_steps_ms,
        })



        return QueryResponse(
            query_id=query_id,
            request_id=query_id,
            view_catalog_id=view_catalog_id,
            view_name=view_name,
            chart_type=ChartType(layout_schema["primary_chart_type"]) if primary_vis else None,
            chart_data=primary_vis.chart_data if primary_vis else None,
            visualizations=visualizations_list if visualizations_list else None,
            bi_intelligence=bi_intelligence,
            parametros_extraidos=extracted_params,
            ia_confianca=primary_intention.confianca,
            ia_justificativa=primary_intention.justificativa,
            ia_analise=ia_analise,
            pergunta_original=payload.pergunta,
            pode_favoritar=primary_vis is not None,
            mensagem=mensagem,
            dashboard_payload=dashboard_payload,
            datasets=builder_datasets,
            analytics_results=analytics_results,
            telemetry=pipeline_telemetry,
            trust_center=trust_center_data,
            roqg_validated=True,
            render_plan=roqg_res.render_plan.model_dump(),

            plano_nlu=[
                SchemaIntentionPlanItem(
                    view_catalog_id=i.view_catalog_id,
                    confianca=i.confianca,
                    operacao=i.operacao or "SOMA",
                    entidade_alvo=i.entidade_alvo or "VENDA",
                    quantidade_limite=i.quantidade_limite,
                    periodo_referencia=i.periodo_referencia,
                    is_comparacao=i.is_comparacao,
                    comparativo_detalhe=i.comparativo_detalhe,
                    visualizacao_preferida=i.visualizacao_preferida,
                    nivel_confianca=i.nivel_confianca or "ALTA",
                    filtros=i.parametros,
                    justificativa=i.justificativa
                ) for i in intentions
            ],
            plano_execucao=query_plan.model_dump()
        )

# Singleton Instantiation
query_intelligence_engine = QueryIntelligenceEngine()
