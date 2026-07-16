import asyncio
import logging
import json
import uuid
import unicodedata
from typing import Any

import asyncpg
from services.oracle_service import decrypt_connection_details

logger = logging.getLogger("luminaai.services.postgres_clone")

def _clone_table_name(view_name: str) -> str:
    """Converte OWNER.VIEW ou VIEW no nome fisico local seguro do clone."""
    raw = str(view_name or "").strip().lower()
    parts = raw.split(".")
    if len(parts) > 2:
        raise ValueError(f"Nome de view invalido ou suspeito detectado: '{view_name}'")
    object_name = parts[-1]
    clean_view_name = "".join(c for c in object_name if c.isalnum() or c == "_")
    if not clean_view_name or clean_view_name != object_name:
        raise ValueError(f"Nome de view invalido ou suspeito detectado: '{view_name}'")
    return clean_view_name

_ACCENT_SOURCE = "ÁÀÂÃÄÅáàâãäåÉÈÊËéèêëÍÌÎÏíìîïÓÒÔÕÖóòôõöÚÙÛÜúùûüÇçÑñ"
_ACCENT_TARGET = "AAAAAAaaaaaaEEEEeeeeIIIIiiiiOOOOOoooooUUUUuuuuCcNn"


def _normalize_search_value(value: Any) -> str:
    """Normaliza texto para filtros robustos contra acento e caixa."""
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _text_search_clause(column_name: str, param_index: int) -> str:
    return (
        f"LOWER(TRANSLATE({column_name}::TEXT, "
        f"'{_ACCENT_SOURCE}', '{_ACCENT_TARGET}')) LIKE ${param_index}"
    )


def _text_search_pattern(value: Any) -> str:
    return f"%{_normalize_search_value(value)}%"


def _parse_internal_list(value: Any) -> list[str]:
    if value in (None, "", [], ()):
        return []
    if isinstance(value, (list, tuple, set)):
        raw_items = [str(item) for item in value]
    else:
        raw_items = str(value).split(",")
    parsed: list[str] = []
    for item in raw_items:
        clean = "".join(ch for ch in item.strip().lower() if ch.isalnum() or ch == "_")
        if clean:
            parsed.append(clean)
    return list(dict.fromkeys(parsed))


def _first_present(row: dict[str, Any], candidates: tuple[str, ...]) -> Any:
    for candidate in candidates:
        if candidate in row and row[candidate] is not None:
            return row[candidate]
    return None


def _enrich_semantic_aliases(row: dict[str, Any]) -> dict[str, Any]:
    """Adiciona aliases corporativos sem apagar os nomes fisicos vindos do clone."""
    enriched = dict(row)
    semantic_sources: dict[str, tuple[str, ...]] = {
        "RECEITA_TOTAL": ("RECEITA_TOTAL", "FATURAMENTO_REALIZADO", "VALOR_VENDIDO", "VALOR_TOTAL", "TOTAL_VENDIDO", "PTOTAL_", "PTOTAL"),
        "FATURAMENTO_REALIZADO": ("FATURAMENTO_REALIZADO", "RECEITA_TOTAL", "VALOR_VENDIDO", "PTOTAL_", "PTOTAL"),
        "VALOR_TOTAL": ("VALOR_TOTAL", "RECEITA_TOTAL", "PTOTAL_", "PTOTAL"),
        "UNIDADES_VENDIDAS": ("UNIDADES_VENDIDAS", "QUANTIDADE_VENDIDA", "QTDE_", "QTDE", "QUANTIDADE"),
        "QUANTIDADE_PEDIDOS": ("QUANTIDADE_PEDIDOS", "PEDIDOS_QTD", "PEDIDO_", "PEDIDO", "NOTA_", "NOTA"),
        "CLIENTES_DISTINTOS": ("CLIENTES_DISTINTOS", "CODCLIENTE_", "CODCLIENTE", "CODIGO_CLIENTE"),
        "PRECO_UNITARIO": ("PRECO_UNITARIO", "PRECO_MEDIO", "P_UNIT_", "P_UNIT"),
        "DATA_REF": ("DATA_REF", "DATA_REFERENCIA", "DATA_VENDA", "DTEMISSAO_", "DT_EMISSAO", "DATA"),
        "CLIENTE_NOME": ("CLIENTE_NOME", "CLIENTE", "RAZAO_", "RAZAO", "NOME_CLIENTE", "NM_CLIENTE", "FANTASIA"),
        "CODIGO_CLIENTE": ("CODIGO_CLIENTE", "CODCLIENTE_", "CODCLIENTE", "CLIENTE_ID", "CD_CLIENTE", "CODIGO"),
        "PRODUTO_NOME": ("PRODUTO_NOME", "PRODUTO", "DESCRICAO_", "DESCRICAO", "NOME_PRODUTO", "NM_PRODUTO", "DESC_PRODUTO"),
        "CODIGO_PRODUTO": ("CODIGO_PRODUTO", "CODPROD_", "CODPROD", "CD_PRODUTO", "SKU", "CODIGO"),
        "VENDEDOR_NOME": ("VENDEDOR_NOME", "VENDEDOR", "NOME_", "NOME_VENDEDOR", "NOME_VED", "NM_VENDEDOR"),
        "CODIGO_VENDEDOR": ("CODIGO_VENDEDOR", "RCA_", "RCA", "CODI_VED", "VENDEDOR_ID", "CODIGO"),
        "FILIAL": ("FILIAL", "FILIAL_", "LOJA", "UNIDADE"),
        "NOTA": ("NOTA", "NOTA_", "NUMERO_NFE"),
        "PEDIDO": ("PEDIDO", "PEDIDO_"),
        "LUCRO_BRUTO": ("LUCRO_BRUTO", "LUCRO", "VALOR_LUCRO"),
        "MARGEM_LUCRO": ("MARGEM_LUCRO", "MARGEM_MEDIA", "MARGEM", "MARGEM_BRUTA"),
        "MARGEM_MEDIA": ("MARGEM_MEDIA", "MARGEM_LUCRO", "MARGEM", "MARGEM_BRUTA"),
    }
    for alias, candidates in semantic_sources.items():
        value = _first_present(enriched, candidates)
        if value is not None:
            enriched.setdefault(alias, value)
    return enriched


_METRIC_COLUMN_ALIASES: dict[str, tuple[str, tuple[str, ...]]] = {
    "receita_total": ("SUM", ("RECEITA_TOTAL", "FATURAMENTO_REALIZADO", "VALOR_VENDIDO", "VALOR_TOTAL", "TOTAL_VENDIDO", "PTOTAL_", "PTOTAL")),
    "faturamento": ("SUM", ("FATURAMENTO_REALIZADO", "RECEITA_TOTAL", "PTOTAL_", "PTOTAL")),
    "faturamento_realizado": ("SUM", ("FATURAMENTO_REALIZADO", "RECEITA_TOTAL", "PTOTAL_", "PTOTAL")),
    "valor_vendido": ("SUM", ("VALOR_VENDIDO", "RECEITA_TOTAL", "PTOTAL_", "PTOTAL")),
    "unidades_vendidas": ("SUM", ("UNIDADES_VENDIDAS", "QUANTIDADE_VENDIDA", "QTDE_", "QTDE", "QUANTIDADE")),
    "quantidade_vendida": ("SUM", ("UNIDADES_VENDIDAS", "QUANTIDADE_VENDIDA", "QTDE_", "QTDE", "QUANTIDADE")),
    "quantidade_pedidos": ("COUNT_DISTINCT", ("PEDIDO_", "PEDIDO", "NOTA_", "NOTA", "NUMERO_NFE")),
    "pedidos_qtd": ("COUNT_DISTINCT", ("PEDIDO_", "PEDIDO", "NOTA_", "NOTA", "NUMERO_NFE")),
    "clientes_distintos": ("COUNT_DISTINCT", ("CODCLIENTE_", "CODCLIENTE", "CODIGO_CLIENTE", "CLIENTE_ID", "CD_CLIENTE")),
    "ticket_medio": ("AVG", ("RECEITA_TOTAL", "VALOR_TOTAL", "PTOTAL_", "PTOTAL")),
    "preco_unitario": ("AVG", ("PRECO_UNITARIO", "PRECO_MEDIO", "P_UNIT_", "P_UNIT")),
    "lucro_bruto": ("SUM", ("LUCRO_BRUTO", "LUCRO", "VALOR_LUCRO")),
    "margem_lucro": ("AVG", ("MARGEM_LUCRO", "MARGEM_MEDIA", "MARGEM", "MARGEM_BRUTA")),
    "margem_media": ("AVG", ("MARGEM_MEDIA", "MARGEM_LUCRO", "MARGEM", "MARGEM_BRUTA")),
}

_DIMENSION_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "vendedor": ("VENDEDOR_NOME", "VENDEDOR", "NOME_", "NOME_VENDEDOR", "NOME_VED", "NM_VENDEDOR"),
    "vendedor_nome": ("VENDEDOR_NOME", "VENDEDOR", "NOME_", "NOME_VENDEDOR", "NOME_VED", "NM_VENDEDOR"),
    "codigo_vendedor": ("CODIGO_VENDEDOR", "RCA_", "RCA", "CODI_VED", "VENDEDOR_ID"),
    "produto": ("PRODUTO_NOME", "PRODUTO", "DESCRICAO_", "DESCRICAO", "NOME_PRODUTO", "NM_PRODUTO"),
    "produto_nome": ("PRODUTO_NOME", "PRODUTO", "DESCRICAO_", "DESCRICAO", "NOME_PRODUTO", "NM_PRODUTO"),
    "codigo_produto": ("CODIGO_PRODUTO", "CODPROD_", "CODPROD", "CD_PRODUTO", "SKU"),
    "cliente": ("CLIENTE_NOME", "CLIENTE", "RAZAO_", "RAZAO", "NOME_CLIENTE", "NM_CLIENTE", "FANTASIA"),
    "cliente_nome": ("CLIENTE_NOME", "CLIENTE", "RAZAO_", "RAZAO", "NOME_CLIENTE", "NM_CLIENTE", "FANTASIA"),
    "codigo_cliente": ("CODIGO_CLIENTE", "CODCLIENTE_", "CODCLIENTE", "CLIENTE_ID", "CD_CLIENTE"),
    "cidade": ("NOME_CIDADE", "CIDADE", "MUNICIPIO", "MUNI_VED"),
    "estado": ("UF", "ESTADO"),
    "uf": ("UF", "ESTADO"),
    "fornecedor": ("FORNECEDOR_NOME", "FORNECEDOR", "NOME_FORNECEDOR", "NM_FORNECEDOR", "FANTASIA_FORNECEDOR"),
    "fornecedor_nome": ("FORNECEDOR_NOME", "FORNECEDOR", "NOME_FORNECEDOR", "NM_FORNECEDOR", "FANTASIA_FORNECEDOR"),
    "filial": ("FILIAL", "FILIAL_", "LOJA", "UNIDADE"),
    "loja": ("FILIAL", "FILIAL_", "LOJA", "UNIDADE"),
    "cfop": ("CFOP_", "CFOP"),
    "ncm": ("NCM_", "NCM"),
    "plano": ("PLANO_", "PLANO"),
    "data": ("DATA_REF", "DATA_REFERENCIA", "DATA_VENDA", "DATA_PEDIDO", "DTEMISSAO_", "DT_EMISSAO", "DATA"),
    "data_ref": ("DATA_REF", "DATA_REFERENCIA", "DATA_VENDA", "DATA_PEDIDO", "DTEMISSAO_", "DT_EMISSAO", "DATA"),
}


def _resolve_existing_column(real_columns: list[str], candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        candidate_upper = candidate.upper()
        if candidate_upper in real_columns:
            return candidate_upper
    return None


def _metric_select_expression(metric_name: str, real_columns: list[str], table_prefix: str = "") -> tuple[str, str] | None:
    clean_metric = "".join(ch for ch in str(metric_name or "").lower() if ch.isalnum() or ch == "_")
    if not clean_metric:
        return None
    if clean_metric == "ticket_medio":
        value_col = _resolve_existing_column(real_columns, _METRIC_COLUMN_ALIASES["receita_total"][1])
        order_col = _resolve_existing_column(real_columns, _METRIC_COLUMN_ALIASES["quantidade_pedidos"][1])
        if value_col and order_col:
            return f"(SUM({table_prefix}{value_col}) / NULLIF(COUNT(DISTINCT {table_prefix}{order_col}), 0)) AS TICKET_MEDIO", "TICKET_MEDIO"
    if clean_metric == "lucro_bruto":
        profit_col = _resolve_existing_column(real_columns, _METRIC_COLUMN_ALIASES["lucro_bruto"][1])
        if profit_col:
            return f"SUM({table_prefix}{profit_col}) AS LUCRO_BRUTO", "LUCRO_BRUTO"
        value_col = _resolve_existing_column(real_columns, _METRIC_COLUMN_ALIASES["receita_total"][1])
        cost_col = _resolve_existing_column(real_columns, ("CUSTO_TOTAL", "VALOR_CUSTO", "CUSTO", "PCUSTO_", "PCUSTO"))
        if value_col and cost_col:
            return (
                f"SUM(COALESCE({table_prefix}{value_col}, 0) - COALESCE({table_prefix}{cost_col}, 0)) AS LUCRO_BRUTO",
                "LUCRO_BRUTO",
            )
    if clean_metric in {"margem_lucro", "margem_media"}:
        margin_col = _resolve_existing_column(real_columns, _METRIC_COLUMN_ALIASES["margem_lucro"][1])
        if margin_col:
            return f"AVG({table_prefix}{margin_col}) AS MARGEM_LUCRO", "MARGEM_LUCRO"
        value_col = _resolve_existing_column(real_columns, _METRIC_COLUMN_ALIASES["receita_total"][1])
        profit_col = _resolve_existing_column(real_columns, _METRIC_COLUMN_ALIASES["lucro_bruto"][1])
        cost_col = _resolve_existing_column(real_columns, ("CUSTO_TOTAL", "VALOR_CUSTO", "CUSTO", "PCUSTO_", "PCUSTO"))
        if value_col and profit_col:
            return (
                f"(SUM({table_prefix}{profit_col}) / NULLIF(SUM({table_prefix}{value_col}), 0)) * 100 AS MARGEM_LUCRO",
                "MARGEM_LUCRO",
            )
        if value_col and cost_col:
            return (
                f"(SUM(COALESCE({table_prefix}{value_col}, 0) - COALESCE({table_prefix}{cost_col}, 0)) / NULLIF(SUM({table_prefix}{value_col}), 0)) * 100 AS MARGEM_LUCRO",
                "MARGEM_LUCRO",
            )
    aggregate, candidates = _METRIC_COLUMN_ALIASES.get(clean_metric, ("SUM", (clean_metric.upper(),)))
    column = _resolve_existing_column(real_columns, candidates)
    if not column:
        return None
    alias = clean_metric.upper()
    if aggregate == "COUNT_DISTINCT":
        return f"COUNT(DISTINCT {table_prefix}{column})::numeric AS {alias}", alias
    if aggregate == "AVG":
        return f"AVG({table_prefix}{column}) AS {alias}", alias
    return f"SUM({table_prefix}{column}) AS {alias}", alias


def _normalize_metric_key(metric_name: Any) -> str:
    return "".join(ch for ch in str(metric_name or "").lower() if ch.isalnum() or ch == "_")


def _order_alias_from_metrics(metric_aliases: list[str], requested_metric: str | None) -> str:
    if not metric_aliases:
        return ""
    requested = _normalize_metric_key(requested_metric)
    if not requested:
        return metric_aliases[0]

    alias_by_key = {_normalize_metric_key(alias): alias for alias in metric_aliases}
    synonyms = {
        "margem_lucro": ("margem_lucro", "margem_media", "margem"),
        "lucro_bruto": ("lucro_bruto", "lucro", "valor_lucro"),
        "receita_total": ("receita_total", "faturamento", "faturamento_realizado", "valor_vendido"),
        "unidades_vendidas": ("unidades_vendidas", "quantidade_vendida", "quantidade"),
        "ticket_medio": ("ticket_medio",),
    }
    for candidate in synonyms.get(requested, (requested,)):
        alias = alias_by_key.get(_normalize_metric_key(candidate))
        if alias:
            return alias
    return metric_aliases[0]


def _safe_order_direction(direction: Any) -> str:
    return "ASC" if str(direction or "").strip().upper() == "ASC" else "DESC"


def _dimension_select_expression(
    dimension_name: str,
    real_columns: list[str],
    date_column: str | None,
    table_prefix: str = "",
) -> tuple[str, str, str] | None:
    clean_dimension = "".join(ch for ch in str(dimension_name or "").lower() if ch.isalnum() or ch == "_")
    if not clean_dimension:
        return None
    if clean_dimension in {"mes", "month"} and date_column:
        return f"DATE_TRUNC('month', {table_prefix}{date_column})::date", "MES", f"DATE_TRUNC('month', {table_prefix}{date_column})::date"
    if clean_dimension in {"ano", "year"} and date_column:
        return f"EXTRACT(YEAR FROM {table_prefix}{date_column})::int", "ANO", f"EXTRACT(YEAR FROM {table_prefix}{date_column})::int"
    candidates = _DIMENSION_COLUMN_ALIASES.get(clean_dimension, (clean_dimension.upper(),))
    column = _resolve_existing_column(real_columns, candidates)
    if not column:
        return None
    return f"{table_prefix}{column}", clean_dimension.upper(), f"{table_prefix}{column}"


def _build_aggregate_query(
    clean_view_name: str,
    real_columns: list[str],
    metric_names: list[str],
    group_by_names: list[str],
    date_column: str | None,
    where_clauses: list[str],
    values: list[Any],
    limit: int | None,
    order_metric: str | None = None,
    order_direction: str = "DESC",
) -> tuple[str, list[Any]] | None:
    metrics = list(dict.fromkeys(metric_names or []))
    groups = list(dict.fromkeys(group_by_names or []))
    if not metrics and not groups:
        return None

    group_selects: list[str] = []
    group_exprs: list[str] = []
    for group_name in groups:
        resolved = _dimension_select_expression(group_name, real_columns, date_column)
        if not resolved:
            continue
        expression, alias, group_expression = resolved
        group_selects.append(f"{expression} AS {alias}")
        group_exprs.append(group_expression)

    metric_selects: list[str] = []
    metric_aliases: list[str] = []
    for metric_name in metrics or ["receita_total"]:
        resolved_metric = _metric_select_expression(metric_name, real_columns)
        if not resolved_metric:
            continue
        expression, alias = resolved_metric
        metric_selects.append(expression)
        metric_aliases.append(alias)

    if not metric_selects:
        return None

    sql = f"SELECT {', '.join(group_selects + metric_selects)} FROM {clean_view_name}"
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
    if group_exprs:
        sql += " GROUP BY " + ", ".join(group_exprs)
    if metric_aliases:
        order_alias = _order_alias_from_metrics(metric_aliases, order_metric)
        sql += f" ORDER BY {order_alias} {_safe_order_direction(order_direction)}"

    bounded_limit = min(max(int(limit or 500), 1), 500)
    query_values = list(values)
    sql += f" LIMIT ${len(query_values) + 1}"
    query_values.append(bounded_limit)
    return sql, query_values


def _sales_enriched_dimension_expression(
    dimension_name: str,
    real_columns: list[str],
    date_column: str | None,
) -> tuple[str, str, str] | None:
    clean_dimension = "".join(ch for ch in str(dimension_name or "").lower() if ch.isalnum() or ch == "_")
    if clean_dimension in {"cidade", "municipio"}:
        return "COALESCE(__clientes.NOME_CIDADE, 'Sem cidade')", "CIDADE", "COALESCE(__clientes.NOME_CIDADE, 'Sem cidade')"
    if clean_dimension in {"estado", "uf"}:
        return "COALESCE(__clientes.UF, 'Sem UF')", "UF", "COALESCE(__clientes.UF, 'Sem UF')"
    if clean_dimension in {"fornecedor", "fornecedor_nome"}:
        return "COALESCE(__fornecedores.NOME, __fornecedores.FANTASIA, 'Sem fornecedor')", "FORNECEDOR_NOME", "COALESCE(__fornecedores.NOME, __fornecedores.FANTASIA, 'Sem fornecedor')"
    return _dimension_select_expression(dimension_name, real_columns, date_column, table_prefix="vw_vendas_lm.")


def _build_sales_enriched_aggregate_query(
    clean_view_name: str,
    real_columns: list[str],
    metric_names: list[str],
    group_by_names: list[str],
    date_column: str | None,
    where_clauses: list[str],
    values: list[Any],
    params: dict[str, str],
    limit: int | None,
    order_metric: str | None = None,
    order_direction: str = "DESC",
) -> tuple[str, list[Any]] | None:
    if clean_view_name != "vw_vendas_lm":
        return None

    metrics = list(dict.fromkeys(metric_names or []))
    groups = list(dict.fromkeys(group_by_names or []))
    normalized_groups = {str(group).lower() for group in groups}
    params = params or {}
    needs_clients = bool(
        normalized_groups.intersection({"cidade", "municipio", "estado", "uf"})
        or params.get("cidade")
        or params.get("municipio")
        or params.get("estado")
        or params.get("uf")
    )
    needs_suppliers = bool(
        normalized_groups.intersection({"fornecedor", "fornecedor_nome"})
        or params.get("fornecedor_nome")
        or params.get("codigo_fornecedor")
    )
    if not needs_clients and not needs_suppliers:
        return None

    group_selects: list[str] = []
    group_exprs: list[str] = []
    for group_name in groups:
        resolved = _sales_enriched_dimension_expression(group_name, real_columns, date_column)
        if not resolved:
            continue
        expression, alias, group_expression = resolved
        group_selects.append(f"{expression} AS {alias}")
        group_exprs.append(group_expression)

    metric_selects: list[str] = []
    metric_aliases: list[str] = []
    for metric_name in metrics or ["receita_total"]:
        resolved_metric = _metric_select_expression(metric_name, real_columns, table_prefix="vw_vendas_lm.")
        if not resolved_metric:
            continue
        expression, alias = resolved_metric
        metric_selects.append(expression)
        metric_aliases.append(alias)

    if not metric_selects:
        return None

    sql = "SELECT " + ", ".join(group_selects + metric_selects) + " FROM vw_vendas_lm"
    if needs_clients:
        sql += " LEFT JOIN vw_clientes_cad_lm __clientes ON __clientes.CODIGO::TEXT = vw_vendas_lm.CODCLIENTE_::TEXT"
    if needs_suppliers:
        sql += " LEFT JOIN vw_produtos_cad_lm __produtos ON __produtos.CODIGO::TEXT = vw_vendas_lm.CODPROD_::TEXT"
        sql += " LEFT JOIN vw_fornecedor_cad_lm __fornecedores ON __fornecedores.CODIGO::TEXT = __produtos.CODIGO_FORNECEDOR::TEXT"

    query_values = list(values)
    enriched_where = list(where_clauses)
    city_value = params.get("cidade") or params.get("municipio")
    if needs_clients and city_value:
        enriched_where.append(_text_search_clause("__clientes.NOME_CIDADE", len(query_values) + 1))
        query_values.append(_text_search_pattern(city_value))
    state_value = params.get("uf") or params.get("estado")
    if needs_clients and state_value:
        enriched_where.append(_text_search_clause("__clientes.UF", len(query_values) + 1))
        query_values.append(_text_search_pattern(state_value))
    supplier_value = params.get("fornecedor_nome")
    if needs_suppliers and supplier_value:
        enriched_where.append(
            "("
            + _text_search_clause("__fornecedores.NOME", len(query_values) + 1)
            + " OR "
            + _text_search_clause("__fornecedores.FANTASIA", len(query_values) + 1)
            + ")"
        )
        query_values.append(_text_search_pattern(supplier_value))

    if enriched_where:
        sql += " WHERE " + " AND ".join(enriched_where)
    if group_exprs:
        sql += " GROUP BY " + ", ".join(group_exprs)
    if metric_aliases:
        order_alias = _order_alias_from_metrics(metric_aliases, order_metric)
        sql += f" ORDER BY {order_alias} {_safe_order_direction(order_direction)}"

    bounded_limit = min(max(int(limit or 500), 1), 500)
    sql += f" LIMIT ${len(query_values) + 1}"
    query_values.append(bounded_limit)
    return sql, query_values

# Cache global de pools de conexão PostgreSQL clonados por tenant
_pg_pools: dict[str, asyncpg.Pool] = {}
_pg_lock: asyncio.Lock | None = None
_pg_lock_loop = None

def _get_pg_lock() -> asyncio.Lock:
    global _pg_lock, _pg_lock_loop
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.Lock()
    if _pg_lock is None or _pg_lock_loop != current_loop:
        _pg_lock = asyncio.Lock()
        _pg_lock_loop = current_loop
    return _pg_lock


async def close_clone_db_pool(tenant_id: uuid.UUID | str) -> None:
    """
    Fecha e remove o pool de conexões PostgreSQL clonado de um tenant específico.
    """
    global _pg_pools
    tenant_key = str(tenant_id)
    async with _get_pg_lock():
        if tenant_key in _pg_pools:
            pool = _pg_pools[tenant_key]
            logger.info("Fechando pool de conexões Postgres Clone do tenant %s", tenant_key)
            try:
                await pool.close()
            except Exception as exc:
                logger.error("Erro ao fechar pool Postgres do tenant %s: %s", tenant_key, exc)
            del _pg_pools[tenant_key]


async def get_clone_db_connection(
    details: dict[str, Any],
    tenant_id: uuid.UUID | str | None = None
) -> asyncpg.Connection:
    """
    Obtém uma conexão com o banco PostgreSQL clonado.
    Se tenant_id for informado, utiliza um pool de conexões cacheado.
    """
    # Validação de chaves
    required_keys = ("host", "port", "user", "password", "database")
    for key in required_keys:
        if key not in details:
            raise KeyError(f"Parâmetro obrigatório '{key}' ausente nas configurações de conexão do PostgreSQL clonado.")

    host = details["host"]
    try:
        port = int(details["port"])
    except ValueError as exc:
        raise ValueError("A porta de conexão do banco PostgreSQL clonado deve ser um valor numérico.") from exc

    user = details["user"]
    password = details["password"]
    database = details["database"]

    if tenant_id is not None:
        tenant_key = str(tenant_id)
        global _pg_pools

        async with _get_pg_lock():
            if tenant_key in _pg_pools:
                cached_pool = _pg_pools[tenant_key]
                current_loop = asyncio.get_running_loop()
                if getattr(cached_pool, "_loop", None) != current_loop or cached_pool._closed or cached_pool._closing:
                    logger.info("Descartando pool Postgres antigo com event loop diferente para o tenant %s", tenant_key)
                    try:
                        await cached_pool.close()
                    except Exception:
                        pass
                    del _pg_pools[tenant_key]

            if tenant_key not in _pg_pools:
                logger.info("Criando novo Pool de Conexões Postgres Clone para o tenant %s (host=%s)", tenant_key, host)
                _pg_pools[tenant_key] = await asyncpg.create_pool(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=database,
                    min_size=1,
                    max_size=4,
                    command_timeout=30.0
                )

        pool = _pg_pools[tenant_key]
        return await pool.acquire()
    else:
        # Conexão standalone
        return await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            timeout=10.0
        )


async def release_clone_db_connection(
    connection: asyncpg.Connection,
    tenant_id: uuid.UUID | str | None = None
) -> None:
    """
    Libera a conexão de volta para o pool ou a fecha caso seja standalone.
    """
    if tenant_id is not None:
        tenant_key = str(tenant_id)
        global _pg_pools
        # Não precisa lock para ler a chave no dict de forma segura
        pool = _pg_pools.get(tenant_key)
        if pool is not None:
            await pool.release(connection)
            return
            
    # Caso standalone ou pool não encontrado
    try:
        await connection.close()
    except Exception as exc:
        logger.error("Erro ao fechar conexão PostgreSQL clonada: %s", exc)


async def get_clone_view_columns(connection: asyncpg.Connection, view_name: str) -> list[tuple[str, str]]:
    """
    Inspeciona dinamicamente as colunas de uma tabela/view no PostgreSQL clonado.
    """
    clean_view_name = _clone_table_name(view_name)

    sql = f"SELECT * FROM {clean_view_name} WHERE 1=0"
    try:
        stmt = await connection.prepare(sql)
        columns = []
        for attr in stmt.get_attributes():
            col_name = attr.name.upper()
            type_name = attr.type.name.lower()

            # Simplifica os tipos
            col_type = "STRING"
            if any(num in type_name for num in ("int", "num", "float", "double", "decimal")):
                col_type = "NUMBER"
            elif any(dt in type_name for dt in ("date", "time", "timestamp")):
                col_type = "DATE"

            columns.append((col_name, col_type))
        return columns
    except Exception as exc:
        logger.error("Erro ao ler as colunas da view/tabela PostgreSQL clonada %s: %s", clean_view_name, exc)
        raise RuntimeError(
            f"Erro ao analisar o esquema da tabela/view '{clean_view_name}' no banco do clone. "
            "Certifique-se de que o banco de dados clonado foi atualizado."
        ) from exc


async def execute_clone_view(
    connection: asyncpg.Connection,
    view_name: str,
    params: dict[str, str],
    tenant_id: uuid.UUID | str | None = None
) -> list[dict[str, Any]]:
    """
    Executa a consulta contra a tabela/view no PostgreSQL clonado aplicando filtros livres.
    
    Suporta o mesmo mapeamento de parâmetros de oracle_service.py:
    - vendedor_nome, cliente_nome, produto_nome, regiao, loja, status, etc.
    - Filtros temporais (data_inicio, data_fim) e mes/ano.
    - Limite de linhas (limite).
    Proteção total contra SQL Injection via parâmetros posicionais ($1, $2, ...).
    """
    # ESP - Security Guardian
    from services.security.enterprise_security_platform import esp_platform
    esp_platform.protect_query_injection(view_name)

    clean_view_name = _clone_table_name(view_name)
    columns_info = await get_clone_view_columns(connection, view_name)
    real_columns = [col[0].upper() for col in columns_info]
    col_type_map = {col[0].upper(): col[1] for col in columns_info}

    # Localiza o primeiro campo de data/timestamp
    date_column = None
    for col_name, col_type in columns_info:
        if col_type == "DATE":
            date_column = col_name.upper()
            break

    where_clauses = []
    values = []
    limite = None
    requested_metrics = _parse_internal_list(params.get("_metrics") if params else None)
    requested_group_by = _parse_internal_list(params.get("_group_by") if params else None)
    order_metric = str((params or {}).get("_order_metric") or "").strip().lower() or None
    order_direction = _safe_order_direction((params or {}).get("_order_direction"))
    anti_join_sales = str((params or {}).get("_anti_join_sales") or "").strip().lower()
    control_params = {
        "tenant_id",
        "limite",
        "limit",
        "row_limit",
        "page",
        "pagina",
        "offset",
        "per_page",
        "_metrics",
        "_group_by",
        "_anti_join_sales",
        "_order_metric",
        "_order_direction",
    }

    # ESP - Row Level Security (RLS)
    if "TENANT_ID" in real_columns and tenant_id:
        where_clauses.append(f"TENANT_ID = ${len(values) + 1}")
        values.append(str(tenant_id))

    if anti_join_sales == "clientes_sem_compras" and "cliente" in clean_view_name:
        client_code_col = _resolve_existing_column(real_columns, ("CODIGO", "CODCLIENTE", "CODIGO_CLIENTE", "CLIENTE_ID", "CD_CLIENTE"))
        if client_code_col:
            where_clauses.append(
                "NOT EXISTS ("
                "SELECT 1 FROM vw_vendas_lm __sales "
                f"WHERE __sales.CODCLIENTE_::TEXT = {clean_view_name}.{client_code_col}::TEXT"
                ")"
            )

    if anti_join_sales == "produtos_sem_venda" and "produto" in clean_view_name:
        product_code_col = _resolve_existing_column(real_columns, ("CODIGO", "CODPROD", "CODIGO_PRODUTO", "CD_PRODUTO", "SKU"))
        if product_code_col:
            where_clauses.append(
                "NOT EXISTS ("
                "SELECT 1 FROM vw_vendas_lm __sales "
                f"WHERE __sales.CODPROD_::TEXT = {clean_view_name}.{product_code_col}::TEXT"
                ")"
            )

    # Mapeamento de parâmetros semânticos livres idêntico ao Oracle
    ALIAS_MAP: dict[str, list[str]] = {
        "vendedor_nome": ["NOME_", "NOME_VED", "VENDEDOR", "NOME_VENDEDOR", "NM_VENDEDOR", "VENDEDOR_NOME"],
        "codigo_vendedor": ["RCA_", "RCA", "CODI_VED", "CODIGO_VENDEDOR", "VENDEDOR_ID", "CODIGO"],
        "cliente_nome": ["RAZAO_", "RAZAO", "CLIENTE", "NOME", "FANTASIA", "NOME_CLIENTE", "NM_CLIENTE", "CLIENTE_NOME", "COMPRADOR"],
        "nome_cliente": ["RAZAO_", "RAZAO", "NOME", "FANTASIA", "CLIENTE", "NOME_CLIENTE", "NM_CLIENTE", "CLIENTE_NOME"],
        "nome_fantasia": ["FANTASIA", "NOME"],
        "produto_nome": ["DESCRICAO_", "DESCRICAO", "NOME_PRODUTO", "PRODUTO", "NM_PRODUTO", "DESCRICAO_PRODUTO", "DESC_PRODUTO"],
        "codigo_produto": ["CODPROD_", "CODPROD", "CODIGO", "CODIGO_PRODUTO", "CD_PRODUTO", "SKU"],
        "codigo_barras": ["CODIGO_BARRAS_EAN", "EAN", "CODIGO_BARRAS", "BARRAS"],
        "ean": ["CODIGO_BARRAS_EAN", "EAN", "CODIGO_BARRAS", "BARRAS"],
        "fornecedor_nome": ["FORNECEDOR", "NOME", "FANTASIA", "NOME_FORNECEDOR", "NM_FORNECEDOR"],
        "codigo_fornecedor": ["CODIGO_FORNECEDOR", "CODIGO", "FORNECEDOR_ID"],
        "documento": ["CNPJ_", "CPF_", "CNPJ_CPF", "CPF_CNPJ", "CPF", "CNPJ", "DOCUMENTO", "CPFC_VED", "CGC", "CGC_CPF"],
        "cpf": ["CPF_", "CNPJ_CPF", "CPF_CNPJ", "CPF", "DOCUMENTO", "CPFC_VED", "CGC", "CGC_CPF"],
        "cnpj": ["CNPJ_", "CNPJ_CPF", "CPF_CNPJ", "CNPJ", "DOCUMENTO", "CGC", "CGC_CPF"],
        "cpf_cnpj": ["CNPJ_", "CPF_", "CNPJ_CPF", "CPF_CNPJ", "CPF", "CNPJ", "DOCUMENTO", "CPFC_VED", "CGC", "CGC_CPF"],
        "tipo_cliente": ["TPCLI", "TIPO_CLIENTE", "TIPO"],
        "regiao": ["REGIAO", "REGIAO_LOJA", "PRACA", "UF", "ESTADO"],
        "cidade": ["NOME_CIDADE", "CIDADE", "MUNICIPIO", "MUNI_VED"],
        "municipio": ["NOME_CIDADE", "CIDADE", "MUNICIPIO", "MUNI_VED"],
        "estado": ["UF", "ESTADO"],
        "uf": ["UF", "ESTADO"],
        "praca": ["PRACA", "REGIAO", "REGIAO_LOJA"],
        "loja": ["FILIAL_", "LOJA", "FILIAL", "NOME_LOJA", "CD_LOJA", "UNIDADE"],
        "filial": ["FILIAL_", "FILIAL", "LOJA", "UNIDADE"],
        "status": ["STATUS", "STATUS_PEDIDO", "SITUACAO", "SIT_PEDIDO"],
        "status_pedido": ["STATUS_PEDIDO", "STATUS", "SITUACAO"],
        "categoria": ["CATEGORIA", "CATEGORIA_PRODUTO", "CATEG", "FAMILIA", "CODIGO_FAMILIA_PRODUTO"],
        "familia": ["FAMILIA", "CODIGO_FAMILIA_PRODUTO", "CATEGORIA"],
        "classe": ["CLASSE", "CATEGORIA", "FAMILIA"],
        "tipo_alerta": ["TIPO_ALERTA", "TIPO", "ALERTA"],
        "forma_pagamento": ["FORMA_PAGAMENTO", "PAGAMENTO", "FORMA_PGTO"],
        "periodo": ["PERIODO", "PERIODO_REFERENCIA"],
        "cliente_id": ["CODCLIENTE_", "CODCLIENTE", "CODIGO", "CLIENTE_ID", "CD_CLIENTE", "CLIENTE"],
        "codigo_cliente": ["CODCLIENTE_", "CODCLIENTE", "CODIGO", "CLIENTE_ID", "CD_CLIENTE"],
        "telefone": ["FONE1", "FONE2", "FONE3", "TELEFONE", "CELULAR", "TELC_VED"],
        "fone": ["FONE1", "FONE2", "FONE3", "TELEFONE", "CELULAR", "TELC_VED"],
        "celular": ["FONE1", "FONE2", "FONE3", "CELULAR", "TELEFONE", "TELC_VED"],
        "email": ["E_MAIL", "EMAIL", "MAIL_VED"],
        "e_mail": ["E_MAIL", "EMAIL", "MAIL_VED"],
        "endereco": ["ENDERECO", "BAIRRO", "NOME_CIDADE", "UF", "CEP_ENDERECO"],
        "cep": ["CEP_ENDERECO", "CEP"],
        "area": ["AREA_VED", "AREA"],
        "estoque": ["ESTOQUE"],
        "situacao": ["SITUACAO", "STATUS"],
        "nota": ["NOTA_", "NOTA", "NUMERO_NFE"],
        "pedido": ["PEDIDO_", "PEDIDO"],
        "cfop": ["CFOP_", "CFOP"],
        "ncm": ["NCM_", "NCM"],
        "plano": ["PLANO_", "PLANO"],
        "tipo": ["TP_", "TP", "TPDESCRICAO_", "TPDESCRICAO"],
    }
    for param_name, param_value in params.items():
        if not param_value:
            continue

        clean_param = "".join(c for c in param_name if c.isalnum() or c == "_")
        if not clean_param:
            continue

        # Extrai limite e ignora metadados de execucao que nao sao filtros fisicos.
        if clean_param in ("limite", "limit", "row_limit"):
            try:
                limite = min(int(param_value), 500)
            except ValueError:
                limite = 500
            continue
        if clean_param in control_params:
            continue

        param_upper = clean_param.upper()
        str_value = str(param_value)

        # A. Match direto
        if param_upper in real_columns:
            col_type = col_type_map.get(param_upper, "STRING")
            if clean_param in ("ano", "mes"):
                try:
                    where_clauses.append(f"{param_upper} = ${len(values) + 1}")
                    values.append(int(str_value))
                except ValueError:
                    where_clauses.append(f"{param_upper} = ${len(values) + 1}")
                    values.append(str_value)
            elif col_type == "NUMBER":
                try:
                    where_clauses.append(f"{param_upper} = ${len(values) + 1}")
                    values.append(float(str_value))
                except ValueError:
                    where_clauses.append(_text_search_clause(param_upper, len(values) + 1))
                    values.append(_text_search_pattern(str_value))
            else:
                where_clauses.append(_text_search_clause(param_upper, len(values) + 1))
                values.append(_text_search_pattern(str_value))

        # B. Filtros de data
        elif clean_param == "data_inicio" and date_column:
            from datetime import datetime
            try:
                date_val = datetime.strptime(str_value, "%Y-%m-%d").date()
                where_clauses.append(f"{date_column} >= ${len(values) + 1}")
                values.append(date_val)
            except ValueError:
                where_clauses.append(f"{date_column} >= ${len(values) + 1}::DATE")
                values.append(str_value)

        elif clean_param == "data_fim" and date_column:
            from datetime import datetime
            try:
                date_val = datetime.strptime(str_value, "%Y-%m-%d").date()
                where_clauses.append(f"{date_column} <= ${len(values) + 1}")
                values.append(date_val)
            except ValueError:
                where_clauses.append(f"{date_column} <= ${len(values) + 1}::DATE")
                values.append(str_value)

        # C. Mapeamento por alias
        elif clean_param in ALIAS_MAP:
            candidate_cols = ALIAS_MAP[clean_param]
            matched_col = next((c for c in candidate_cols if c in real_columns), None)
            if matched_col:
                col_type = col_type_map.get(matched_col, "STRING")
                if col_type == "NUMBER":
                    try:
                        where_clauses.append(f"{matched_col} = ${len(values) + 1}")
                        values.append(float(str_value))
                    except ValueError:
                        where_clauses.append(_text_search_clause(matched_col, len(values) + 1))
                        values.append(_text_search_pattern(str_value))
                else:
                    where_clauses.append(_text_search_clause(matched_col, len(values) + 1))
                    values.append(_text_search_pattern(str_value))

        # D. Match parcial/fuzzy
        else:
            fuzzy_col = next(
                (col for col in real_columns if clean_param in col or col in param_upper),
                None
            )
            if fuzzy_col:
                col_type = col_type_map.get(fuzzy_col, "STRING")
                if col_type == "NUMBER":
                    try:
                        where_clauses.append(f"{fuzzy_col} = ${len(values) + 1}")
                        values.append(float(str_value))
                    except ValueError:
                        pass
                else:
                    where_clauses.append(_text_search_clause(fuzzy_col, len(values) + 1))
                    values.append(_text_search_pattern(str_value))

    aggregate_query = _build_sales_enriched_aggregate_query(
        clean_view_name=clean_view_name,
        real_columns=real_columns,
        metric_names=requested_metrics,
        group_by_names=requested_group_by,
        date_column=date_column,
        where_clauses=where_clauses,
        values=values,
        params=params or {},
        limit=limite,
        order_metric=order_metric,
        order_direction=order_direction,
    ) or _build_aggregate_query(
        clean_view_name=clean_view_name,
        real_columns=real_columns,
        metric_names=requested_metrics,
        group_by_names=requested_group_by,
        date_column=date_column,
        where_clauses=where_clauses,
        values=values,
        limit=limite,
        order_metric=order_metric,
        order_direction=order_direction,
    )
    if aggregate_query:
        sql, values = aggregate_query
    else:
        sql = f"SELECT * FROM {clean_view_name}"
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        
        # Aplica limite no Postgres
        if limite:
            sql += f" LIMIT ${len(values) + 1}"
            values.append(limite)
        else:
            sql += f" LIMIT ${len(values) + 1}"
            values.append(500)

    logger.info("Executando query no PostgreSQL clonado: %s | Params: %s", sql, values)
    try:
        rows = await connection.fetch(sql, *values)
        results = []
        for row in rows:
            row_dict = {k.upper(): v for k, v in row.items()}
            results.append(_enrich_semantic_aliases(row_dict))
        return results
    except Exception as exc:
        logger.error("Erro ao executar a query no PostgreSQL clonado '%s': %s", sql, exc)
        raise RuntimeError(f"Falha na base de dados clonada ao processar a análise: {exc}") from exc
