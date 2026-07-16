import json
import logging
import re
from datetime import date
from typing import Any

from config import settings
from models.tenant import Tenant
from services.oracle_service import decrypt_connection_details
from services.postgresql_clone_service import (
    execute_clone_view,
    get_clone_db_connection,
    get_clone_view_columns,
    release_clone_db_connection,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("luminaai.data_platform.analytical_storage")

_LOCAL_DEMO_TENANT_IDS = {"a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"}

_MOCK_VIEW_TABLES: dict[str, str] = {
    "VW_VENDAS_MENSAIS": "mock_oracle_vw_vendas_mensais",
    "VW_VENDAS_CONTEXTO_GERAL": "mock_oracle_vw_vendas_mensais",
    "VW_DETALHE_PEDIDOS": "mock_oracle_vw_vendas_mensais",
    "VW_FATURAMENTO_MENSAL": "mock_oracle_vw_faturamento_mensal",
    "VW_FATURAMENTO_MENSAIS": "mock_oracle_vw_faturamento_mensal",
    "VW_PERFORMANCE_VENDEDORES": "mock_oracle_vw_performance_vendedores",
    "VW_KPI_EXECUTIVO": "mock_oracle_vw_kpi_executivo",
    "VW_KPI_EXECUTIVO_VENDAS": "mock_oracle_vw_kpi_executivo",
    "VW_PRODUTOS_MAIS_VENDIDOS": "mock_oracle_vw_ranking_produtos",
    "VW_RANKING_PRODUTOS": "mock_oracle_vw_ranking_produtos",
    "VW_ESTOQUE_PRODUTOS": "mock_oracle_vw_estoque_produtos",
    "VW_ESTOQUE_STATUS": "mock_oracle_vw_estoque_produtos",
    "VW_HISTORICO_CLIENTES": "mock_oracle_vw_historico_clientes",
    "VW_CLIENTES_HISTORICO": "mock_oracle_vw_historico_clientes",
    "VW_LOJAS_REGIOES": "mock_oracle_vw_lojas_regioes",
    "VW_METAS_VENDEDORES": "mock_oracle_vw_metas_vendedores",
    "VW_METAS_ATINGIMENTO": "mock_oracle_vw_metas_vendedores",
}

_CONTROL_PARAMS = {
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
    "_order_metric",
    "_order_direction",
}

_DATE_COLUMN_PRIORITY = (
    "dtemissao_",
    "dt_emissao",
    "data_referencia",
    "data_ref",
    "data_venda",
    "data_pedido",
    "data",
)

_FILTER_ALIASES: dict[str, tuple[str, ...]] = {
    "vendedor_nome": ("nome_", "vendedor", "nome_vendedor", "nome_ved", "nm_vendedor", "vendedor_nome"),
    "codigo_vendedor": ("rca_", "rca", "codi_ved", "codigo_vendedor", "vendedor_id", "codigo"),
    "cliente_nome": ("razao_", "razao", "cliente", "nome", "fantasia", "nome_cliente", "nm_cliente", "cliente_nome", "comprador"),
    "nome_cliente": ("razao_", "razao", "nome", "fantasia", "cliente", "nome_cliente", "nm_cliente", "cliente_nome"),
    "nome_fantasia": ("fantasia", "nome"),
    "produto_nome": ("descricao_", "descricao", "produto", "nome_produto", "nm_produto", "descricao_produto", "desc_produto"),
    "produto": ("descricao_", "descricao", "produto", "nome_produto", "nm_produto", "descricao_produto", "desc_produto"),
    "codigo_produto": ("codprod_", "codprod", "codigo_produto", "cd_produto", "sku", "codigo"),
    "documento": ("cnpj_", "cpf_", "cnpj_cpf", "cpf_cnpj", "cpf", "cnpj", "documento"),
    "cpf": ("cpf_", "cnpj_cpf", "cpf_cnpj", "cpf", "documento"),
    "cnpj": ("cnpj_", "cnpj_cpf", "cpf_cnpj", "cnpj", "documento"),
    "cpf_cnpj": ("cnpj_", "cpf_", "cnpj_cpf", "cpf_cnpj", "cpf", "cnpj", "documento"),
    "tipo_cliente": ("tpcli", "tipo_cliente", "tipo"),
    "categoria": ("categoria", "categoria_produto", "categ", "classe"),
    "classe": ("classe", "categoria"),
    "regiao": ("regiao", "regiao_loja", "praca", "uf", "estado"),
    "cidade": ("nome_cidade", "cidade", "municipio"),
    "municipio": ("nome_cidade", "cidade", "municipio"),
    "estado": ("uf", "estado"),
    "uf": ("uf", "estado"),
    "praca": ("praca", "regiao", "regiao_loja"),
    "loja": ("filial_", "loja", "filial", "nome_loja", "cd_loja", "unidade"),
    "filial": ("filial_", "filial", "loja", "unidade"),
    "status": ("status", "status_pedido", "situacao", "sit_pedido", "status_alerta"),
    "status_pedido": ("status_pedido", "status", "situacao"),
    "forma_pagamento": ("forma_pagamento", "pagamento", "forma_pgto"),
    "periodo": ("periodo", "periodo_referencia"),
    "cliente_id": ("codcliente_", "codcliente", "codigo", "cliente_id", "cd_cliente", "cliente"),
    "codigo_cliente": ("codcliente_", "codcliente", "codigo", "cliente_id", "cd_cliente"),
    "telefone": ("fone1", "fone2", "fone3", "telefone", "celular"),
    "fone": ("fone1", "fone2", "fone3", "telefone", "celular"),
    "celular": ("fone1", "fone2", "fone3", "celular", "telefone"),
    "email": ("e_mail", "email"),
    "e_mail": ("e_mail", "email"),
    "endereco": ("endereco", "bairro", "nome_cidade", "uf", "cep_endereco"),
    "cep": ("cep_endereco", "cep"),
    "nota": ("nota_", "nota", "numero_nfe"),
    "pedido": ("pedido_", "pedido"),
    "cfop": ("cfop_", "cfop"),
    "ncm": ("ncm_", "ncm"),
    "plano": ("plano_", "plano"),
}

def _safe_identifier(value: str) -> str:
    return "".join(c for c in str(value or "").lower() if c.isalnum() or c == "_")


def _parse_internal_list(value: Any) -> list[str]:
    if value in (None, "", [], ()):
        return []
    if isinstance(value, (list, tuple, set)):
        raw_items = [str(item) for item in value]
    else:
        raw_items = str(value).split(",")
    parsed: list[str] = []
    for item in raw_items:
        clean = _safe_identifier(item.strip())
        if clean:
            parsed.append(clean)
    return list(dict.fromkeys(parsed))


def _safe_order_direction(value: Any) -> str:
    return "ASC" if str(value or "").strip().upper() == "ASC" else "DESC"


class AnalyticalStorage:
    """
    Data Platform analytical storage reader.

    User queries never hit the ERP directly. In production this class reads the
    analytical PostgreSQL clone. In the local demo tenant it reads the seeded
    mock_oracle_* tables so manual validation uses realistic, date-filterable
    data instead of stale generic clone rows.
    """

    async def execute_view(
        self,
        tenant: Tenant,
        view_name: str,
        parameters: dict[str, Any],
        db_session: AsyncSession,
    ) -> list[dict[str, Any]]:
        """Execute an analytical view from the allowed analytical storage."""
        if await self._should_use_local_mock(tenant, view_name, db_session):
            logger.info(
                "[AnalyticalStorage] Local demo mode - reading official mock data for view %s",
                view_name,
            )
            return await self._execute_local_mock_view(view_name, parameters, db_session)

        if self._should_use_generated_mock_fallback(tenant, view_name):
            from services.mock_service import gerar_raw_rows_mock

            logger.info(
                "[AnalyticalStorage] Generated mock fallback for technical test view %s",
                view_name,
            )
            return gerar_raw_rows_mock(view_name, parameters)

        clone_conn_config = tenant.clone_db_conn
        if isinstance(clone_conn_config, str):
            clone_conn_config = json.loads(clone_conn_config) if clone_conn_config.strip() else {}

        oracle_conn_config = tenant.oracle_conn
        if isinstance(oracle_conn_config, str):
            oracle_conn_config = json.loads(oracle_conn_config) if oracle_conn_config.strip() else {}

        payload_str = clone_conn_config.get("payload")
        oracle_payload_str = oracle_conn_config.get("payload")
        is_demo = not payload_str or oracle_payload_str == "DEMO_TENANT_ORACLE_CONN_ENCRYPTED_REPLACE_WITH_REAL"

        if is_demo:
            from services.mock_service import gerar_raw_rows_mock

            logger.info("[AnalyticalStorage] Legacy demo/mock mode for view %s", view_name)
            return gerar_raw_rows_mock(view_name, parameters)

        logger.info("[AnalyticalStorage] Executing view %s on analytical PostgreSQL clone", view_name)
        details = decrypt_connection_details(clone_conn_config)
        conn = await get_clone_db_connection(details, tenant_id=tenant.id)
        try:
            return await execute_clone_view(conn, view_name, parameters, tenant_id=tenant.id)
        finally:
            await release_clone_db_connection(conn, tenant_id=tenant.id)

    async def view_exists(self, tenant: Tenant, view_name: str) -> bool:
        """Check whether an analytical view is available."""
        if await self._should_use_local_mock_for_exists(tenant, view_name):
            return True

        clone_conn_config = tenant.clone_db_conn
        if isinstance(clone_conn_config, str):
            clone_conn_config = json.loads(clone_conn_config) if clone_conn_config.strip() else {}

        if not clone_conn_config.get("payload"):
            return True

        try:
            details = decrypt_connection_details(clone_conn_config)
            conn = await get_clone_db_connection(details, tenant_id=tenant.id)
            try:
                await get_clone_view_columns(conn, view_name)
                return True
            except Exception:
                return False
            finally:
                await release_clone_db_connection(conn, tenant_id=tenant.id)
        except Exception:
            return False

    async def _should_use_local_mock(
        self,
        tenant: Tenant,
        view_name: str,
        db_session: AsyncSession,
    ) -> bool:
        if not self._is_local_mock_enabled_for_tenant(tenant):
            return False
        table_name = self._mock_table_for_view(view_name)
        return bool(table_name and await self._table_exists(db_session, table_name))

    async def _should_use_local_mock_for_exists(self, tenant: Tenant, view_name: str) -> bool:
        if not self._is_local_mock_enabled_for_tenant(tenant):
            return False
        return bool(self._mock_table_for_view(view_name))

    def _is_local_mock_enabled_for_tenant(self, tenant: Tenant) -> bool:
        return settings.MOCK_ORACLE or (
            settings.is_development and str(tenant.id) in _LOCAL_DEMO_TENANT_IDS
        )

    def _should_use_generated_mock_fallback(self, tenant: Tenant, view_name: str) -> bool:
        if settings.MOCK_ORACLE:
            return True
        if not settings.is_development or str(tenant.id) not in _LOCAL_DEMO_TENANT_IDS:
            return False
        return str(view_name or "").upper().startswith("VW_TEST")

    def _mock_table_for_view(self, view_name: str) -> str:
        view_upper = (view_name or "").upper()
        mapped = _MOCK_VIEW_TABLES.get(view_upper)
        if mapped:
            return mapped
        clean_view = _safe_identifier(view_name)
        return f"mock_oracle_{clean_view}" if clean_view else ""

    async def _table_exists(self, db_session: AsyncSession, table_name: str) -> bool:
        result = await db_session.execute(text("select to_regclass(:table_name)"), {"table_name": table_name})
        return result.scalar() is not None

    async def _get_local_columns(self, db_session: AsyncSession, table_name: str) -> dict[str, str]:
        result = await db_session.execute(
            text(
                """
                select column_name, data_type
                from information_schema.columns
                where table_schema = current_schema()
                  and table_name = :table_name
                order by ordinal_position
                """
            ),
            {"table_name": table_name},
        )
        return {str(row.column_name).lower(): str(row.data_type).lower() for row in result.fetchall()}

    async def _execute_local_mock_view(
        self,
        view_name: str,
        parameters: dict[str, Any],
        db_session: AsyncSession,
    ) -> list[dict[str, Any]]:
        table_name = self._mock_table_for_view(view_name)
        if not table_name or not await self._table_exists(db_session, table_name):
            return []

        columns = await self._get_local_columns(db_session, table_name)
        if not columns:
            return []

        where_clauses: list[str] = []
        binds: dict[str, Any] = {}
        date_col = next((col for col in _DATE_COLUMN_PRIORITY if col in columns), None)

        start_date = (parameters or {}).get("data_inicio")
        end_date = (parameters or {}).get("data_fim")
        date_range = (parameters or {}).get("date_range")
        if date_range and (not start_date or not end_date):
            range_match = re.search(
                r"(\d{4}-\d{2}-\d{2})\s*(?:to|ate|a|-)\s*(\d{4}-\d{2}-\d{2})",
                str(date_range),
            )
            if range_match:
                start_date = start_date or range_match.group(1)
                end_date = end_date or range_match.group(2)
        if date_col and start_date:
            where_clauses.append(f"DATE({date_col}) >= :data_inicio")
            binds["data_inicio"] = self._coerce_date_value(start_date)
        if date_col and end_date:
            where_clauses.append(f"DATE({date_col}) <= :data_fim")
            binds["data_fim"] = self._coerce_date_value(end_date)

        for raw_name, raw_value in (parameters or {}).items():
            if raw_value in (None, "", [], ()):  # keep false-y zero as a valid filter
                continue

            clean_param = _safe_identifier(raw_name)
            if not clean_param or clean_param in _CONTROL_PARAMS or clean_param in {"data_inicio", "data_fim"}:
                continue

            value = raw_value[0] if isinstance(raw_value, (list, tuple)) and raw_value else raw_value
            bind_name = f"p_{len(binds)}"

            if clean_param in {"mes", "ano"} and clean_param in columns:
                where_clauses.append(f"{clean_param} = :{bind_name}")
                binds[bind_name] = int(value) if str(value).isdigit() else value
                continue

            alias_col = self._resolve_alias_column(clean_param, columns)
            if alias_col:
                where_clauses.append(f"{alias_col}::TEXT ILIKE :{bind_name}")
                binds[bind_name] = f"%{value}%"
                continue

            if clean_param in columns:
                where_clauses.append(self._build_column_filter(clean_param, columns[clean_param], bind_name))
                binds[bind_name] = self._coerce_filter_value(value, columns[clean_param])

        limit = self._extract_limit(parameters or {})
        binds["limit_value"] = limit

        requested_metrics = _parse_internal_list((parameters or {}).get("_metrics"))
        requested_group_by = _parse_internal_list((parameters or {}).get("_group_by"))
        sql = self._build_local_aggregate_query(
            table_name=table_name,
            columns=columns,
            metric_names=requested_metrics,
            group_by_names=requested_group_by,
            where_clauses=where_clauses,
            parameters=parameters or {},
        )
        if not sql:
            sql = f"SELECT * FROM {table_name}"
            if where_clauses:
                sql += " WHERE " + " AND ".join(where_clauses)

            order_clause = self._build_order_clause(table_name, columns, date_col, parameters or {})
            if order_clause:
                sql += f" ORDER BY {order_clause}"
            sql += " LIMIT :limit_value"

        result = await db_session.execute(text(sql), binds)
        rows = [dict(row) for row in result.mappings().all()]
        enriched = [self._enrich_local_mock_row(row) for row in rows]
        logger.info(
            "[AnalyticalStorage] Local mock executed | view=%s table=%s rows=%d filters=%s",
            view_name,
            table_name,
            len(enriched),
            {k: v for k, v in (parameters or {}).items() if k not in _CONTROL_PARAMS},
        )
        return enriched

    def _build_local_aggregate_query(
        self,
        table_name: str,
        columns: dict[str, str],
        metric_names: list[str],
        group_by_names: list[str],
        where_clauses: list[str],
        parameters: dict[str, Any],
    ) -> str | None:
        metrics = list(dict.fromkeys(metric_names or []))
        groups = list(dict.fromkeys(group_by_names or []))
        if not metrics and not groups:
            return None

        group_selects: list[str] = []
        group_exprs: list[str] = []
        for group_name in groups:
            clean_group = _safe_identifier(group_name)
            column = self._resolve_alias_column(clean_group, columns) or (clean_group if clean_group in columns else None)
            if not column:
                continue
            alias = clean_group.upper()
            group_selects.append(f"{column} AS {alias}")
            group_exprs.append(column)

        metric_selects: list[str] = []
        metric_aliases: list[str] = []
        for metric_name in metrics or ["receita_total"]:
            resolved = self._local_metric_expression(metric_name, columns)
            if not resolved:
                continue
            expression, alias = resolved
            metric_selects.append(f"{expression} AS {alias}")
            metric_aliases.append(alias)

        if not metric_selects:
            return None

        sql = f"SELECT {', '.join(group_selects + metric_selects)} FROM {table_name}"
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        if group_exprs:
            sql += " GROUP BY " + ", ".join(group_exprs)

        order_alias = self._local_order_alias(metric_aliases, parameters.get("_order_metric"))
        if order_alias:
            sql += f" ORDER BY {order_alias} {_safe_order_direction(parameters.get('_order_direction'))}"
        sql += " LIMIT :limit_value"
        return sql

    def _first_existing_column(self, columns: dict[str, str], candidates: tuple[str, ...]) -> str | None:
        for candidate in candidates:
            clean = _safe_identifier(candidate)
            if clean in columns:
                return clean
        return None

    def _local_metric_expression(self, metric_name: str, columns: dict[str, str]) -> tuple[str, str] | None:
        metric = _safe_identifier(metric_name)
        revenue = self._first_existing_column(
            columns,
            ("receita_total", "faturamento_realizado", "valor_vendido", "valor_total", "total_vendido", "ptotal_", "ptotal", "venda_valor"),
        )
        quantity = self._first_existing_column(
            columns,
            ("unidades_vendidas", "quantidade_vendida", "venda_quantidade", "qtde_", "qtde", "quantidade"),
        )
        order_id = self._first_existing_column(columns, ("pedido_", "pedido", "nota_", "nota", "numero_nfe"))
        cost = self._first_existing_column(columns, ("custo_total", "valor_custo", "custo", "pcusto_", "pcusto"))
        profit = self._first_existing_column(columns, ("lucro_bruto", "lucro", "valor_lucro"))
        margin = self._first_existing_column(columns, ("margem_lucro", "margem_media", "margem", "margem_bruta"))

        if metric in {"receita_total", "faturamento", "faturamento_realizado", "valor_vendido"} and revenue:
            return f"SUM({revenue})", "RECEITA_TOTAL"
        if metric in {"unidades_vendidas", "quantidade_vendida"} and quantity:
            return f"SUM({quantity})", "UNIDADES_VENDIDAS"
        if metric in {"quantidade_pedidos", "pedidos_qtd"} and order_id:
            return f"COUNT(DISTINCT {order_id})::numeric", "QUANTIDADE_PEDIDOS"
        if metric == "ticket_medio" and revenue:
            divisor = f"COUNT(DISTINCT {order_id})" if order_id else "NULLIF(SUM(1), 0)"
            return f"(SUM({revenue}) / NULLIF({divisor}, 0))", "TICKET_MEDIO"
        if metric == "lucro_bruto":
            if profit:
                return f"SUM({profit})", "LUCRO_BRUTO"
            if revenue and cost:
                return f"SUM(COALESCE({revenue}, 0) - COALESCE({cost}, 0))", "LUCRO_BRUTO"
        if metric in {"margem_lucro", "margem_media"}:
            if margin:
                return f"AVG({margin})", "MARGEM_LUCRO"
            if profit and revenue:
                return f"(SUM({profit}) / NULLIF(SUM({revenue}), 0)) * 100", "MARGEM_LUCRO"
            if revenue and cost:
                return f"(SUM(COALESCE({revenue}, 0) - COALESCE({cost}, 0)) / NULLIF(SUM({revenue}), 0)) * 100", "MARGEM_LUCRO"

        column = self._first_existing_column(columns, (metric,))
        if column:
            aggregate = "AVG" if "margem" in metric or "ticket" in metric else "SUM"
            return f"{aggregate}({column})", metric.upper()
        return None

    def _local_order_alias(self, metric_aliases: list[str], requested_metric: Any) -> str:
        if not metric_aliases:
            return ""
        requested = _safe_identifier(str(requested_metric or ""))
        if not requested:
            return metric_aliases[0]

        alias_by_key = {_safe_identifier(alias): alias for alias in metric_aliases}
        synonyms = {
            "margem_lucro": ("margem_lucro", "margem_media", "margem"),
            "lucro_bruto": ("lucro_bruto", "lucro", "valor_lucro"),
            "receita_total": ("receita_total", "faturamento", "faturamento_realizado", "valor_vendido"),
            "unidades_vendidas": ("unidades_vendidas", "quantidade_vendida", "quantidade"),
            "ticket_medio": ("ticket_medio",),
        }
        for candidate in synonyms.get(requested, (requested,)):
            alias = alias_by_key.get(_safe_identifier(candidate))
            if alias:
                return alias
        return metric_aliases[0]

    def _resolve_alias_column(self, clean_param: str, columns: dict[str, str]) -> str | None:
        for candidate in _FILTER_ALIASES.get(clean_param, ()):
            if candidate in columns:
                return candidate
        return None

    def _build_column_filter(self, column: str, data_type: str, bind_name: str) -> str:
        if "int" in data_type or "numeric" in data_type or "double" in data_type or "real" in data_type:
            return f"{column} = :{bind_name}"
        if "date" in data_type or "timestamp" in data_type:
            return f"DATE({column}) = :{bind_name}"
        return f"{column}::TEXT ILIKE :{bind_name}"

    def _coerce_filter_value(self, value: Any, data_type: str) -> Any:
        if "int" in data_type:
            try:
                return int(value)
            except (TypeError, ValueError):
                return value
        if "numeric" in data_type or "double" in data_type or "real" in data_type:
            try:
                return float(value)
            except (TypeError, ValueError):
                return value
        if "date" in data_type or "timestamp" in data_type:
            return self._coerce_date_value(value)
        return f"%{value}%"

    def _coerce_date_value(self, value: Any) -> Any:
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value)[:10])
        except (TypeError, ValueError):
            return value

    def _extract_limit(self, parameters: dict[str, Any]) -> int:
        raw_limit = parameters.get("limite") or parameters.get("limit") or parameters.get("row_limit") or 500
        try:
            return max(1, min(int(raw_limit), 500))
        except (TypeError, ValueError):
            return 500

    def _build_order_clause(self, table_name: str, columns: dict[str, str], date_col: str | None, parameters: dict[str, Any]) -> str:
        order_metric = _safe_identifier(str((parameters or {}).get("_order_metric") or ""))
        if order_metric:
            order_col = self._first_existing_column(
                columns,
                {
                    "margem_lucro": ("margem_lucro", "margem_media", "margem", "margem_bruta"),
                    "lucro_bruto": ("lucro_bruto", "lucro", "valor_lucro"),
                    "receita_total": ("receita_total", "valor_vendido", "venda_valor", "ptotal_", "ptotal"),
                    "unidades_vendidas": ("unidades_vendidas", "quantidade_vendida", "venda_quantidade", "qtde_"),
                    "ticket_medio": ("ticket_medio", "valor_medio"),
                }.get(order_metric, (order_metric,)),
            )
            if order_col:
                return f"{order_col} {_safe_order_direction((parameters or {}).get('_order_direction'))}"

        if table_name == "mock_oracle_vw_ranking_produtos":
            if "unidades_vendidas" in columns and "receita_total" in columns:
                return "unidades_vendidas DESC, receita_total DESC"
            if "receita_total" in columns:
                return "receita_total DESC"

        if table_name == "mock_oracle_vw_performance_vendedores":
            if "ranking" in columns:
                return "ranking ASC"
            if "valor_vendido" in columns:
                return "valor_vendido DESC"

        if date_col:
            return f"{date_col} ASC"

        return ""

    def _enrich_local_mock_row(self, row: dict[str, Any]) -> dict[str, Any]:
        enriched = dict(row)

        if "venda_valor" in enriched:
            enriched.setdefault("receita_total", enriched["venda_valor"])
            enriched.setdefault("valor_vendido", enriched["venda_valor"])
        if "venda_quantidade" in enriched:
            enriched.setdefault("quantidade_pedidos", enriched["venda_quantidade"])
        if "data_referencia" in enriched:
            enriched.setdefault("data_ref", enriched["data_referencia"])
        if "unidades_vendidas" in enriched:
            enriched.setdefault("quantidade_vendida", enriched["unidades_vendidas"])
            enriched.setdefault("quantidade_pedidos", enriched["unidades_vendidas"])
        if "margem_media" in enriched:
            enriched.setdefault("margem_lucro", enriched["margem_media"])
        if "valor_vendido" in enriched:
            enriched.setdefault("receita_total", enriched["valor_vendido"])
        if "pedidos_qtd" in enriched:
            enriched.setdefault("quantidade_pedidos", enriched["pedidos_qtd"])

        return enriched
