"""
LuminaAI — Camada Semântica de Conhecimento de Negócio (v5.7)
------------------------------------------------------------
Define de forma imutável, única e padronizada as fórmulas, definições,
regras de validação, fontes de dados e dependências das métricas corporativas.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Final

from services.business.synonym_cache import _SYNONYM_CACHE

logger = logging.getLogger("luminaai.services.semantic_layer")

_STATIC_METRIC_ALIASES: Final[dict[str, str]] = {
    "total": "receita_total",
    "receita": "receita_total",
    "receita total": "receita_total",
    "receita_total": "receita_total",
    "receita bruta": "receita_total",
    "revenue": "receita_total",
    "faturamento": "receita_total",
    "faturamento total": "receita_total",
    "faturamento_total": "receita_total",
    "total faturado": "receita_total",
    "faturado": "receita_total",
    "venda": "receita_total",
    "vendas": "receita_total",
    "venda bruta": "receita_total",
    "venda total": "receita_total",
    "total venda": "receita_total",
    "vendas totais": "receita_total",
    "total vendas": "receita_total",
    "total_vendas": "receita_total",
    "total de vendas": "receita_total",
    "total das vendas": "receita_total",
    "valor vendido": "receita_total",
    "valor de venda": "receita_total",
    "valor de vendas": "receita_total",
    "valor das vendas": "receita_total",
    "valor total": "receita_total",
    "valor_total": "receita_total",
    "valor total de vendas": "receita_total",
    "valor total das vendas": "receita_total",
    "total vendido": "receita_total",
    "total_vendido": "receita_total",
    "valor total vendido": "receita_total",
    "retorno financeiro": "receita_total",
    "resultado financeiro": "receita_total",
    "maior retorno financeiro": "receita_total",
    "retorno para empresa": "receita_total",
    "retorno da empresa": "receita_total",
    "produto com maior retorno": "receita_total",
    "vendido": "receita_total",
    "vendeu": "receita_total",
    "vendas realizadas": "receita_total",
    "lucro": "lucro_bruto",
    "profit": "lucro_bruto",
    "lucro bruto": "lucro_bruto",
    "lucro_bruto": "lucro_bruto",
    "margem": "margem_lucro",
    "margem lucro": "margem_lucro",
    "margem_lucro": "margem_lucro",
    "margem bruta": "margem_lucro",
    "margem liquida": "margem_lucro",
    "lucratividade": "margem_lucro",
    "rentabilidade": "margem_lucro",
    "rentabilidade do produto": "margem_lucro",
    "retorno percentual": "margem_lucro",
    "custo": "custo_total",
    "custos": "custo_total",
    "custo total": "custo_total",
    "custo_total": "custo_total",
    "qtd pedidos": "quantidade_pedidos",
    "qtd_pedidos": "quantidade_pedidos",
    "quantidade pedidos": "quantidade_pedidos",
    "quantidade de pedidos": "quantidade_pedidos",
    "quantidade vendas": "quantidade_pedidos",
    "quantidade de vendas": "quantidade_pedidos",
    "qtd vendas": "quantidade_pedidos",
    "qtd de vendas": "quantidade_pedidos",
    "quantidade vendida": "unidades_vendidas",
    "quantidade_vendida": "unidades_vendidas",
    "quantidade total vendida": "unidades_vendidas",
    "qtd vendida": "unidades_vendidas",
    "qtd produto vendido": "unidades_vendidas",
    "qtd produtos vendidos": "unidades_vendidas",
    "unidade vendida": "unidades_vendidas",
    "unidades vendidas": "unidades_vendidas",
    "produtos vendidos": "unidades_vendidas",
    "itens vendidos": "unidades_vendidas",
    "total pedidos": "quantidade_pedidos",
    "total de pedidos": "quantidade_pedidos",
    "pedidos total": "quantidade_pedidos",
    "pedidos totais": "quantidade_pedidos",
    "pedidos_totais": "quantidade_pedidos",
    "numero de vendas": "quantidade_pedidos",
    "número de vendas": "quantidade_pedidos",
    "numero vendas": "quantidade_pedidos",
    "volume vendas": "quantidade_pedidos",
    "volume de vendas": "quantidade_pedidos",
    "pedidos": "quantidade_pedidos",
    "clientes distintos": "clientes_distintos",
    "clientes_distintos": "clientes_distintos",
    "quantos clientes": "clientes_distintos",
    "quantidade de clientes": "clientes_distintos",
    "numero de clientes": "clientes_distintos",
    "nÃºmero de clientes": "clientes_distintos",
    "clientes que compraram": "clientes_distintos",
    "ticket": "ticket_medio",
    "ticket medio": "ticket_medio",
    "ticket_medio": "ticket_medio",
    "ticket médio": "ticket_medio",
    "valor medio": "ticket_medio",
    "valor médio": "ticket_medio",
    "valor medio compra": "ticket_medio",
    "valor_medio_compra": "ticket_medio",
    "churn": "churn_rate",
    "churn rate": "churn_rate",
    "taxa churn": "churn_rate",
    "taxa de churn": "churn_rate",
    "ltv": "ltv_estimado",
    "ltv estimado": "ltv_estimado",
    "cac": "cac_estimado",
    "cac estimado": "cac_estimado",
    "conversao": "taxa_conversao",
    "conversão": "taxa_conversao",
    "taxa conversao": "taxa_conversao",
    "taxa de conversao": "taxa_conversao",
    "taxa de conversão": "taxa_conversao",
    "faturamento realizado": "faturamento_realizado",
    "faturamento_realizado": "faturamento_realizado",
    "meta mensal": "meta_mensal",
    "meta_mensal": "meta_mensal",
    "percentual de atingimento da meta": "atingimento_meta",
    "atingimento da meta": "atingimento_meta",
    "atingimento_meta": "atingimento_meta",
    "atingimento de meta": "atingimento_meta",
    "valor vendido": "valor_vendido",
    "valor_vendido": "valor_vendido",
    "meta valor": "meta_valor",
    "meta_valor": "meta_valor",
    "atingimento": "atingimento",
    "comissao": "comissao",
    "pedidos qtd": "pedidos_qtd",
    "pedidos_qtd": "pedidos_qtd",
    "numero de vendas fechadas": "pedidos_qtd",
    "vendas fechadas": "pedidos_qtd",
    "ranking": "ranking",
}

_SEMANTIC_STOPWORDS: Final[set[str]] = {
    "a", "as", "o", "os", "de", "do", "da", "dos", "das", "no", "na", "nos", "nas",
    "em", "por", "para", "por favor", "qual", "quais", "quanto", "quantos", "foi",
    "foram", "me", "mostre", "mostrar", "ver", "sobre",
}

_VIEW_METRIC_EQUIVALENTS: Final[dict[str, dict[str, str]]] = {
    "VW_PERFORMANCE_VENDEDORES": {
        "receita_total": "valor_vendido",
        "faturamento": "valor_vendido",
        "faturamento_realizado": "valor_vendido",
        "meta_mensal": "meta_valor",
        "atingimento_meta": "atingimento",
        "quantidade_pedidos": "pedidos_qtd",
    },
    "VW_FATURAMENTO_MENSAIS": {
        "receita_total": "faturamento_realizado",
        "faturamento": "faturamento_realizado",
        "valor_vendido": "faturamento_realizado",
        "meta_valor": "meta_mensal",
        "atingimento": "atingimento_meta",
    },
    "VW_FATURAMENTO_MENSAL": {
        "receita_total": "faturamento_realizado",
        "faturamento": "faturamento_realizado",
        "valor_vendido": "faturamento_realizado",
        "meta_valor": "meta_mensal",
        "atingimento": "atingimento_meta",
    },
    "VW_VENDAS_MENSAIS": {
        "faturamento_realizado": "receita_total",
        "valor_vendido": "receita_total",
        "meta_mensal": "receita_total",
        "atingimento_meta": "receita_total",
    },
    "VW_VENDAS_CONTEXTO_GERAL": {
        "faturamento_realizado": "receita_total",
        "valor_vendido": "receita_total",
        "meta_mensal": "receita_total",
        "atingimento_meta": "receita_total",
    },
    "VW_VENDAS_LM": {
        "faturamento": "receita_total",
        "faturamento_realizado": "receita_total",
        "valor_vendido": "receita_total",
        "lucro": "lucro_bruto",
        "lucro_bruto": "lucro_bruto",
        "margem": "margem_lucro",
        "margem_lucro": "margem_lucro",
        "margem_media": "margem_lucro",
        "quantidade_pedidos": "quantidade_pedidos",
        "pedidos_qtd": "quantidade_pedidos",
        "quantidade_vendida": "unidades_vendidas",
        "clientes_distintos": "clientes_distintos",
    },
    "VW_PRODUTOS_MAIS_VENDIDOS": {
        "quantidade_pedidos": "unidades_vendidas",
        "pedidos_qtd": "unidades_vendidas",
        "faturamento": "receita_total",
        "faturamento_realizado": "receita_total",
        "valor_vendido": "receita_total",
        "margem_lucro": "margem_media",
    },
    "VW_RANKING_PRODUTOS": {
        "quantidade_pedidos": "unidades_vendidas",
        "pedidos_qtd": "unidades_vendidas",
        "faturamento": "receita_total",
        "faturamento_realizado": "receita_total",
        "valor_vendido": "receita_total",
        "margem_lucro": "margem_media",
    },
}

# Dicionário central e imutável de conceitos e métricas de negócio
_BUSINESS_DICT: dict[str, dict[str, Any]] = {
    "receita_total": {
        "metric_name": "receita_total",
        "definition": "Total de vendas realizadas em um período comercial.",
        "formula": "sum(vendas_aprovadas)",
        "validation_rules": ["exclui_canceladas", "exclui_estornadas"],
        "data_sources": ["VW_VENDAS_LM", "VW_VENDAS_MENSAIS", "VW_VENDAS_CONTEXTO_GERAL", "VW_PERFORMANCE_VENDEDORES", "VW_DETALHE_PEDIDOS", "VW_PRODUTOS_MAIS_VENDIDOS", "VW_RANKING_PRODUTOS"],
        "dependencies": []
    },
    "faturamento": {
        "metric_name": "faturamento",
        "definition": "Valor total bruto movimentado em vendas registradas.",
        "formula": "sum(todas_as_vendas)",
        "validation_rules": ["inclui_todas_as_vendas", "pode_incluir_pedidos_pendentes"],
        "data_sources": ["VW_VENDAS_LM", "VW_VENDAS_MENSAIS", "VW_VENDAS_CONTEXTO_GERAL", "VW_DETALHE_PEDIDOS", "VW_PRODUTOS_MAIS_VENDIDOS", "VW_RANKING_PRODUTOS"],
        "dependencies": []
    },
    "lucro_bruto": {
        "metric_name": "lucro_bruto",
        "definition": "Receita total liquida deduzindo custos operacionais diretos, taxas e impostos.",
        "formula": "receita_total - custo_total - taxas - impostos",
        "validation_rules": ["depende_de_receita", "depende_de_custos"],
        "data_sources": ["VW_VENDAS_LM", "VW_VENDAS_MENSAIS", "VW_VENDAS_CONTEXTO_GERAL", "VW_DETALHE_PEDIDOS", "VW_PRODUTOS_MAIS_VENDIDOS", "VW_RANKING_PRODUTOS"],
        "dependencies": ["receita_total", "custo_total"]
    },
    "margem_lucro": {
        "metric_name": "margem_lucro",
        "definition": "Margem percentual de lucratividade sobre a receita total gerada.",
        "formula": "(lucro_bruto / receita_total) * 100",
        "validation_rules": ["depende_de_lucro"],
        "data_sources": ["VW_VENDAS_LM", "VW_VENDAS_MENSAIS", "VW_VENDAS_CONTEXTO_GERAL", "VW_DETALHE_PEDIDOS", "VW_PRODUTOS_MAIS_VENDIDOS", "VW_RANKING_PRODUTOS"],
        "dependencies": ["lucro_bruto", "receita_total"]
    },
    "ticket_medio": {
        "metric_name": "ticket_medio",
        "definition": "Valor médio transacionado por cada venda concluída.",
        "formula": "receita_total / numero_de_vendas",
        "validation_rules": ["depende_de_receita", "depende_de_volume"],
        "data_sources": ["VW_VENDAS_LM", "VW_VENDAS_MENSAIS", "VW_VENDAS_CONTEXTO_GERAL", "VW_DETALHE_PEDIDOS", "VW_PRODUTOS_MAIS_VENDIDOS", "VW_RANKING_PRODUTOS"],
        "dependencies": ["receita_total"]
    },
    "cliente_ativo": {
        "metric_name": "cliente_ativo",
        "definition": "Cliente que realizou pelo menos 1 compra aprovada nos últimos 30 dias.",
        "formula": "count(clientes_com_compra_recente_30d)",
        "validation_rules": ["periodo_padrao_30_dias"],
        "data_sources": ["VW_EVOLUCAO_CLIENTES"],
        "dependencies": []
    },
    "churn_rate": {
        "metric_name": "churn_rate",
        "definition": "Percentual de evasão de clientes inativos no período de referência.",
        "formula": "clientes_inativos / total_clientes",
        "validation_rules": ["periodo_definido"],
        "data_sources": ["VW_EVOLUCAO_CLIENTES"],
        "dependencies": []
    },
    "ltv_estimado": {
        "metric_name": "ltv_estimado",
        "definition": "Valor total estimado gerado por um cliente individual durante todo seu ciclo de vida.",
        "formula": "ticket_medio * frequencia_compras * tempo_vida_medio",
        "validation_rules": ["depende_de_ticket_medio"],
        "data_sources": ["VW_EVOLUCAO_CLIENTES"],
        "dependencies": ["ticket_medio"]
    },
    "cac_estimado": {
        "metric_name": "cac_estimado",
        "definition": "Custo total médio de marketing e vendas para aquisição de um novo cliente.",
        "formula": "custo_total_marketing / novos_clientes",
        "validation_rules": ["exclui_clientes_recorrentes"],
        "data_sources": ["VW_EVOLUCAO_CLIENTES"],
        "dependencies": []
    },
    "taxa_conversao": {
        "metric_name": "taxa_conversao",
        "definition": "Percentual de vendas concluídas em relação ao volume total de leads ou visitas.",
        "formula": "vendas / leads_ou_visitas",
        "validation_rules": ["leads_ou_visitas_maior_que_zero"],
        "data_sources": ["VW_EVOLUCAO_CLIENTES", "VW_VENDAS_CONTEXTO_GERAL"],
        "dependencies": []
    },
    "custo_total": {
        "metric_name": "custo_total",
        "definition": "Soma de todos os custos diretos associados à aquisição e fabricação de produtos.",
        "formula": "sum(custo_produto)",
        "validation_rules": ["exclui_despesas_indiretas"],
        "data_sources": ["VW_VENDAS_MENSAIS", "VW_VENDAS_CONTEXTO_GERAL"],
        "dependencies": []
    },
    "quantidade_pedidos": {
        "metric_name": "quantidade_pedidos",
        "definition": "Número total de pedidos ou transações de vendas no período.",
        "formula": "count(pedidos)",
        "validation_rules": ["exclui_cancelados"],
        "data_sources": ["VW_VENDAS_LM", "VW_VENDAS_MENSAIS", "VW_VENDAS_CONTEXTO_GERAL", "VW_PERFORMANCE_VENDEDORES", "VW_DETALHE_PEDIDOS"],
        "dependencies": []
    },
    "unidades_vendidas": {
        "metric_name": "unidades_vendidas",
        "definition": "Quantidade total de unidades de produtos vendidas no perÃ­odo.",
        "formula": "sum(unidades_vendidas)",
        "validation_rules": ["exclui_cancelados"],
        "data_sources": ["VW_VENDAS_LM", "VW_PRODUTOS_MAIS_VENDIDOS", "VW_RANKING_PRODUTOS"],
        "dependencies": []
    },
    "clientes_distintos": {
        "metric_name": "clientes_distintos",
        "definition": "Quantidade de clientes distintos que realizaram compras no perÃ­odo.",
        "formula": "count_distinct(clientes_com_compra)",
        "validation_rules": ["exclui_cancelados"],
        "data_sources": ["VW_VENDAS_LM", "VW_DETALHE_PEDIDOS"],
        "dependencies": []
    },
    "margem_media": {
        "metric_name": "margem_media",
        "definition": "Margem mÃ©dia dos produtos vendidos.",
        "formula": "avg(margem_media)",
        "validation_rules": [],
        "data_sources": ["VW_PRODUTOS_MAIS_VENDIDOS", "VW_RANKING_PRODUTOS"],
        "dependencies": []
    },
    "faturamento_realizado": {
        "metric_name": "faturamento_realizado",
        "definition": "Faturamento bruto efetivamente realizado no período.",
        "formula": "sum(faturamento_realizado)",
        "validation_rules": [],
        "data_sources": ["VW_VENDAS_LM", "VW_FATURAMENTO_MENSAIS", "VW_FATURAMENTO_MENSAL"],
        "dependencies": []
    },
    "meta_mensal": {
        "metric_name": "meta_mensal",
        "definition": "Meta mensal de faturamento estabelecida.",
        "formula": "sum(meta_mensal)",
        "validation_rules": [],
        "data_sources": ["VW_FATURAMENTO_MENSAIS", "VW_FATURAMENTO_MENSAL"],
        "dependencies": []
    },
    "atingimento_meta": {
        "metric_name": "atingimento_meta",
        "definition": "Percentual de atingimento da meta mensal.",
        "formula": "(faturamento_realizado / meta_mensal) * 100",
        "validation_rules": [],
        "data_sources": ["VW_FATURAMENTO_MENSAIS", "VW_FATURAMENTO_MENSAL"],
        "dependencies": ["faturamento_realizado", "meta_mensal"]
    },
    "valor_vendido": {
        "metric_name": "valor_vendido",
        "definition": "Valor total vendido por vendedor.",
        "formula": "sum(valor_vendido)",
        "validation_rules": [],
        "data_sources": ["VW_PERFORMANCE_VENDEDORES"],
        "dependencies": []
    },
    "meta_valor": {
        "metric_name": "meta_valor",
        "definition": "Meta de vendas do vendedor.",
        "formula": "sum(meta_valor)",
        "validation_rules": [],
        "data_sources": ["VW_PERFORMANCE_VENDEDORES"],
        "dependencies": []
    },
    "atingimento": {
        "metric_name": "atingimento",
        "definition": "Percentual de atingimento da meta de vendas do vendedor.",
        "formula": "(valor_vendido / meta_valor) * 100",
        "validation_rules": [],
        "data_sources": ["VW_PERFORMANCE_VENDEDORES"],
        "dependencies": ["valor_vendido", "meta_valor"]
    },
    "comissao": {
        "metric_name": "comissao",
        "definition": "Comissão ganha pelo vendedor pelas vendas aprovadas.",
        "formula": "sum(comissao)",
        "validation_rules": [],
        "data_sources": ["VW_PERFORMANCE_VENDEDORES"],
        "dependencies": []
    },
    "pedidos_qtd": {
        "metric_name": "pedidos_qtd",
        "definition": "Número de vendas fechadas ou pedidos do vendedor.",
        "formula": "sum(pedidos_qtd)",
        "validation_rules": [],
        "data_sources": ["VW_PERFORMANCE_VENDEDORES"],
        "dependencies": []
    },
    "ranking": {
        "metric_name": "ranking",
        "definition": "Posição no ranking de vendas dos vendedores.",
        "formula": "ranking",
        "validation_rules": [],
        "data_sources": ["VW_PERFORMANCE_VENDEDORES"],
        "dependencies": []
    }
}


def _normalize_alias_key(text: str) -> str:
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", str(text).lower().strip())
    without_accents = "".join(c for c in normalized if not unicodedata.combining(c))
    for sep in ("_", "-", ".", "/", "\\"):
        without_accents = without_accents.replace(sep, " ")
    clean = re.sub(r"[^a-z0-9\s]", " ", without_accents)
    return " ".join(clean.split())


def _singularize_token(token: str) -> str:
    if token.endswith("ais") and len(token) > 4:
        return f"{token[:-3]}al"
    if token.endswith("oes") and len(token) > 4:
        return f"{token[:-3]}ao"
    if token.endswith("s") and len(token) > 3:
        return token[:-1]
    return token


def _metric_key_variants(text: str) -> list[str]:
    base = _normalize_alias_key(text)
    if not base:
        return []

    variants = [base]
    tokens = base.split()

    without_stopwords = [token for token in tokens if token not in _SEMANTIC_STOPWORDS]
    if without_stopwords and without_stopwords != tokens:
        variants.append(" ".join(without_stopwords))

    singular_tokens = [_singularize_token(token) for token in tokens]
    singular = " ".join(singular_tokens)
    if singular != base:
        variants.append(singular)

    singular_without_stopwords = [
        _singularize_token(token)
        for token in without_stopwords
        if token not in _SEMANTIC_STOPWORDS
    ]
    if singular_without_stopwords:
        variants.append(" ".join(singular_without_stopwords))

    return list(dict.fromkeys(v for v in variants if v))


def _build_metric_alias_index() -> dict[str, str]:
    index: dict[str, str] = {}

    for official_name in _BUSINESS_DICT:
        for variant in _metric_key_variants(official_name):
            index.setdefault(variant, official_name)

    for alias, official_name in _STATIC_METRIC_ALIASES.items():
        for variant in _metric_key_variants(alias):
            index[variant] = official_name

    for synonym, official_name in _SYNONYM_CACHE.items():
        if official_name:
            for variant in _metric_key_variants(synonym):
                index[variant] = official_name

    return index


def _resolve_metric_by_safe_similarity(alias_key: str, alias_index: dict[str, str]) -> str | None:
    if len(alias_key) < 6:
        return None

    from difflib import SequenceMatcher

    best_key = ""
    best_score = 0.0
    for known_key in alias_index:
        score = SequenceMatcher(None, alias_key, known_key).ratio()
        if score > best_score:
            best_key = known_key
            best_score = score

    if best_score >= 0.88:
        return alias_index[best_key]

    return None


def canonicalize_metric_name(metric_name: str) -> str:
    """Resolve metric aliases to the official corporate semantic identifier."""
    candidate = str(metric_name or "").strip()
    if not candidate:
        return candidate

    alias_index = _build_metric_alias_index()
    for alias_key in _metric_key_variants(candidate):
        canonical = alias_index.get(alias_key)
        if canonical:
            return canonical

    primary_key = _normalize_alias_key(candidate)
    fuzzy_canonical = _resolve_metric_by_safe_similarity(primary_key, alias_index)
    if fuzzy_canonical:
        logger.info(
            "[SemanticLayer] Metrica normalizada por similaridade segura: %r -> %s",
            metric_name,
            fuzzy_canonical,
        )
        return fuzzy_canonical

    return candidate


def get_metric_info(metric_name: str) -> dict[str, Any] | None:
    """
    Retorna as especificações de negócio da métrica solicitada.
    """
    direct = _BUSINESS_DICT.get(str(metric_name or "").strip())
    if direct:
        return direct
    return _BUSINESS_DICT.get(canonicalize_metric_name(metric_name))


def resolve_metric_for_view(metric_name: str, view_name: str = "") -> str:
    """
    Resolve metric aliases and adapts equivalent business metrics to the selected view.

    Example: a seller ranking can request faturamento_realizado, but the
    VW_PERFORMANCE_VENDEDORES view exposes that concept as valor_vendido.
    """
    canonical_metric = canonicalize_metric_name(metric_name)
    view_upper = (view_name or "").upper()
    if not view_upper:
        return canonical_metric

    equivalents = _VIEW_METRIC_EQUIVALENTS.get(view_upper, {})
    equivalent = equivalents.get(canonical_metric)
    if equivalent and equivalent in _BUSINESS_DICT:
        logger.info(
            "[SemanticLayer] Metrica adaptada ao contexto da view: %s -> %s | view=%s",
            canonical_metric,
            equivalent,
            view_upper,
        )
        return equivalent

    metric_info = _BUSINESS_DICT.get(canonical_metric)
    if metric_info:
        compatible_sources = [src.upper() for src in metric_info.get("data_sources", [])]
        if view_upper in compatible_sources:
            return canonical_metric

    return canonical_metric


def validate_metrics_and_sources(metrics: list[str], view_name: str) -> list[str]:
    """
    Valida a existência e compatibilidade das métricas com a view catalogada (dataset).
    Retorna uma lista de erros encontrados. Se vazia, a validação passou.
    """
    errors: list[str] = []
    v_upper = view_name.upper() if view_name else ""

    for m in metrics:
        canonical_metric = resolve_metric_for_view(m, view_name)
        m_info = _BUSINESS_DICT.get(canonical_metric)
        if not m_info:
            errors.append(f"Métrica '{m}' não está cadastrada no dicionário semântico de negócios corporativo.")
            continue

        # Verifica compatibilidade com fontes de dados
        compatible_sources = m_info.get("data_sources", [])
        if v_upper and v_upper not in [src.upper() for src in compatible_sources]:
            errors.append(
                f"Métrica '{canonical_metric}' é incompatível com a fonte de dados '{view_name}'. "
                f"Fontes compatíveis: {', '.join(compatible_sources)}."
            )

    return errors


def register_custom_metric(
    name: str,
    definition: str,
    formula: str,
    validation_rules: list[str],
    data_sources: list[str],
    dependencies: list[str]
) -> None:
    """
    Registra uma métrica de negócios customizada (Extensibilidade).
    """
    global _BUSINESS_DICT
    _BUSINESS_DICT[name] = {
        "metric_name": name,
        "definition": definition,
        "formula": formula,
        "validation_rules": validation_rules,
        "data_sources": [src.upper() for src in data_sources],
        "dependencies": dependencies
    }
    logger.info("Nova métrica customizada registrada com sucesso: %s", name)


async def sync_from_semantic_catalog(tenant_id: str) -> int:
    """
    Sincroniza o dicionário estático em memória (_BUSINESS_DICT) com os registros
    dinâmicos do SemanticCatalog e do Business Knowledge Engine (BKE) no banco de dados.
    Também popula o cache de sinônimos do BusinessLayer.

    Deve ser chamado na inicialização do sistema e após qualquer alteração no SemanticCatalog.

    Returns:
        Número de conceitos sincronizados.
    """
    import uuid as _uuid
    from sqlalchemy import select, and_
    from models.semantic_catalog import SemanticCatalog
    from models.business_concept import BusinessConcept
    from models.business_kpi import BusinessKPI
    from database import get_db_context
    import json

    logger.info("[SemanticLayer] Sincronizando com SemanticCatalog e BKE... (tenant=%s)", str(tenant_id)[:8])
    count = 0

    try:
        async with get_db_context() as session:
            # 1. Sincroniza do SemanticCatalog legado
            stmt = select(SemanticCatalog).where(
                SemanticCatalog.tenant_id == _uuid.UUID(tenant_id)
            )
            result = await session.execute(stmt)
            concepts = result.scalars().all()

            for concept in concepts:
                nome = concept.nome_oficial
                entry = _BUSINESS_DICT.setdefault(nome, {
                    "metric_name": nome,
                    "definition": "",
                    "formula": "",
                    "validation_rules": [],
                    "data_sources": [],
                    "dependencies": []
                })

                if concept.descricao:
                    entry["definition"] = concept.descricao

                sinonimos = concept.sinonimos
                if isinstance(sinonimos, str):
                    sinonimos = json.loads(sinonimos)

                if sinonimos:
                    for syn in sinonimos:
                        _SYNONYM_CACHE[syn.lower().strip()] = nome
                count += 1

            # 2. Sincroniza conceitos do BKE
            stmt_bke_concepts = select(BusinessConcept).where(
                and_(
                    BusinessConcept.tenant_id == _uuid.UUID(tenant_id),
                    BusinessConcept.status == "ACTIVE"
                )
            )
            res_bke_concepts = await session.execute(stmt_bke_concepts)
            bke_concepts = res_bke_concepts.scalars().all()

            for bc in bke_concepts:
                # Evita colisão com mocks genéricos de testes legados
                if not isinstance(bc, BusinessConcept) and type(bc).__name__ != "BusinessConcept":
                    continue
                nome = bc.nome
                entry = _BUSINESS_DICT.setdefault(nome, {
                    "metric_name": nome,
                    "definition": bc.descricao,
                    "formula": bc.definicao_oficial,
                    "validation_rules": [],
                    "data_sources": [bc.origem] if bc.origem else [],
                    "dependencies": []
                })
                
                # Popula sinônimos do conceito
                for syn in (bc.sinonimos or []):
                    _SYNONYM_CACHE[syn.lower().strip()] = nome
                count += 1

            # 3. Sincroniza KPIs do BKE
            stmt_bke_kpis = select(BusinessKPI).where(
                and_(
                    BusinessKPI.tenant_id == _uuid.UUID(tenant_id),
                    BusinessKPI.status == "ACTIVE"
                )
            )
            res_bke_kpis = await session.execute(stmt_bke_kpis)
            bke_kpis = res_bke_kpis.scalars().all()

            for bk in bke_kpis:
                # Evita colisão com mocks genéricos de testes legados
                if not isinstance(bk, BusinessKPI) and type(bk).__name__ != "BusinessKPI":
                    continue
                nome = bk.nome
                entry = _BUSINESS_DICT.setdefault(nome, {
                    "metric_name": nome,
                    "definition": bk.descricao,
                    "formula": bk.formula_oficial,
                    "validation_rules": list(bk.faixas.keys()) if bk.faixas else [],
                    "data_sources": [],
                    "dependencies": list(bk.tags or [])
                })
                
                # Popula tags como sinônimos secundários
                for tag in (bk.tags or []):
                    _SYNONYM_CACHE[tag.lower().strip()] = nome
                count += 1

        logger.info("[SemanticLayer] Sincronização BKE/SemanticCatalog concluída: %d conceitos processados.", count)

    except Exception as exc:
        logger.warning("[SemanticLayer] Sincronização com SemanticCatalog/BKE falhou: %s", exc)

    return count
