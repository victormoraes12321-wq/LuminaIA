from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from services.temporal import EffectiveTemporalScope, EffectiveTemporalScopeKind


class SalesValueBreakdownService:
    """Centraliza a decomposicao de valores de venda por movimento e filial."""

    DISCOUNT_COLUMN_CANDIDATES = (
        "desconto_total",
        "valor_desconto",
        "vl_desconto",
        "vldesconto",
        "vldesc",
        "desconto",
    )

    CATEGORY_VALUE_KEYS = (
        "faturamento_comercial",
        "saida_rb",
        "devolucao",
        "venda_bonificada",
        "transferencias",
        "outras_vendas",
        "remessa_uso_consumo",
        "outros_movimentos",
    )
    CATEGORY_TOTAL_BRUTO_KEYS = tuple(key for key in CATEGORY_VALUE_KEYS if key != "transferencias")
    CATEGORY_LABELS = {
        "faturamento_comercial": "Faturamento comercial",
        "saida_rb": "Saida RB",
        "devolucao": "Devolucao",
        "saida_rb_devolucao": "Saida RB + Devolucao",
        "venda_bonificada": "Venda bonificada",
        "transferencias": "Transferencias",
        "outras_vendas": "Outras vendas",
        "remessa_uso_consumo": "Remessa / uso e consumo",
        "outros_movimentos": "Outros movimentos",
        "total_bruto": "Total bruto sem transferencias",
        "total_movimentos_view": "Total geral de movimentos",
    }

    def normalize_filial(self, filial: Any | None) -> str | None:
        value = str(filial or "").strip()
        if not value:
            return None
        try:
            return str(int(value))
        except ValueError:
            return value

    def commercial_filter_sql(self, alias: str = "", filial: Any | None = None) -> str:
        prefix = f"{alias}." if alias else ""
        parts = [f"{prefix}tp_ IN (2, 61)"]
        if self.normalize_filial(filial) is not None:
            parts.append(f"{prefix}filial_ = :sales_filial")
        return " AND ".join(parts)

    def default_binds(self, filial: Any | None = None) -> dict[str, Any]:
        normalized_filial = self.normalize_filial(filial)
        return {"sales_filial": normalized_filial} if normalized_filial is not None else {}

    def commercial_filter_label(self, filial: Any | None = None) -> str:
        normalized_filial = self.normalize_filial(filial)
        if normalized_filial is not None:
            return f"Filtro comercial: filial {normalized_filial} e tipos de venda 2/61."
        return "Filtro comercial: todas as filiais e tipos de venda 2/61."

    def period_where_sql(self, alias: str = "lm") -> str:
        prefix = f"{alias}." if alias else ""
        return f"{prefix}dtemissao_ >= :start_date AND {prefix}dtemissao_ < :end_exclusive"

    def tenant_scope_sql(self, alias: str = "lm") -> str:
        return ""

    def filial_scope_sql(self, alias: str = "lm", filial: Any | None = None) -> str:
        normalized_filial = self.normalize_filial(filial)
        if normalized_filial is None:
            return ""
        prefix = f"{alias}." if alias else ""
        return f"AND {prefix}filial_ = :sales_filial"

    def entity_scope_sql(
        self,
        alias: str = "lm",
        *,
        vendedor: Any | None = None,
        produto: Any | None = None,
    ) -> str:
        prefix = f"{alias}." if alias else ""
        parts: list[str] = []
        if vendedor not in (None, ""):
            parts.append(f"AND {prefix}rca_ = :sales_vendedor")
        if produto not in (None, ""):
            parts.append(f"AND {prefix}codprod_ = :sales_produto")
        return "\n".join(parts)

    def period_scope_sql(
        self,
        alias: str = "lm",
        *,
        all_history: bool = False,
        temporal_scope: EffectiveTemporalScope | None = None,
    ) -> str:
        if temporal_scope is not None:
            if temporal_scope.kind == EffectiveTemporalScopeKind.ALL_AVAILABLE_HISTORY:
                return "TRUE"
            if temporal_scope.kind != EffectiveTemporalScopeKind.BOUNDED:
                raise ValueError(
                    f"Unsupported singular analytical temporal scope: {temporal_scope.kind.value}"
                )
            return self.period_where_sql(alias)
        return "TRUE" if all_history else self.period_where_sql(alias)

    async def fetch_discount_source_profile(self, session: Any) -> dict[str, Any]:
        result = await session.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'vw_vendas_lm'
                ORDER BY ordinal_position
                """
            )
        )
        columns = [str(row[0]) for row in result.fetchall()]
        columns_by_lower = {column.lower(): column for column in columns}
        for candidate in self.DISCOUNT_COLUMN_CANDIDATES:
            column = columns_by_lower.get(candidate)
            if column:
                return {
                    "desconto_fonte_tipo": "coluna_explicita",
                    "desconto_fonte_coluna": column,
                    "desconto_fonte_confianca": "alta",
                    "desconto_fonte_observacao": f"Desconto lido diretamente da coluna {column} da view vw_vendas_lm.",
                }

        return {
            "desconto_fonte_tipo": "derivado_sem_coluna_explicita",
            "desconto_fonte_coluna": None,
            "desconto_fonte_confianca": "baixa",
            "desconto_fonte_observacao": (
                "A view vw_vendas_lm nao possui coluna explicita de desconto; "
                "o sistema tentou derivar por quantidade vezes preco unitario menos valor faturado."
            ),
        }

    def discount_expr_sql(self, alias: str = "lm", explicit_column: str | None = None) -> str:
        prefix = f"{alias}." if alias else ""
        if explicit_column:
            safe_column = str(explicit_column).replace('"', '""')
            return f'COALESCE({prefix}"{safe_column}", 0)'
        return (
            "GREATEST(ROUND(((COALESCE("
            f"{prefix}qtde_, 0) * COALESCE({prefix}p_unit_, 0)) - COALESCE({prefix}ptotal_, 0))::numeric, 2), 0::numeric)"
        )

    def category_case_sql(self, alias: str = "lm") -> str:
        prefix = f"{alias}." if alias else ""
        description = f"UPPER(COALESCE({prefix}tpdescricao_, ''))"
        return f"""
            CASE
                WHEN COALESCE({prefix}tp_, 0) = 22
                  OR {description} LIKE '%BONIFIC%'
                    THEN 'venda_bonificada'
                WHEN COALESCE({prefix}tp_, 0) = 9
                  OR {description} LIKE '%SAIDA RB%'
                    THEN 'saida_rb'
                WHEN {description} LIKE '%DEVOL%'
                    THEN 'devolucao'
                WHEN COALESCE({prefix}tp_, 0) IN (3, 31, 96)
                  OR {description} LIKE '%TRANSFERENCIA%'
                    THEN 'transferencias'
                WHEN COALESCE({prefix}tp_, 0) IN (2, 61)
                    THEN 'faturamento_comercial'
                WHEN {description} LIKE 'VENDA%'
                    THEN 'outras_vendas'
                WHEN {description} LIKE '%REMESSA%'
                  OR {description} LIKE '%USO E CONSUMO%'
                    THEN 'remessa_uso_consumo'
                ELSE 'outros_movimentos'
            END
        """

    def _with_default_binds(
        self,
        binds: dict[str, Any],
        filial: Any | None = None,
        temporal_scope: EffectiveTemporalScope | None = None,
    ) -> dict[str, Any]:
        query_binds = dict(binds)
        normalized_filial = self.normalize_filial(filial or query_binds.get("sales_filial"))
        if normalized_filial is not None:
            query_binds["sales_filial"] = normalized_filial
        else:
            query_binds.pop("sales_filial", None)
        tenant_id = query_binds.get("tenant_id")
        if not tenant_id or not str(tenant_id).strip():
            raise ValueError("tenant_id e obrigatorio para consultas em sales_value_breakdown")
        query_binds["tenant_id"] = str(tenant_id).strip()
        if temporal_scope is not None and temporal_scope.kind == EffectiveTemporalScopeKind.BOUNDED:
            window = temporal_scope.windows[0]
            query_binds.update(
                {
                    "start_date": window.start,
                    "end_date": window.end,
                    "end_exclusive": window.end + timedelta(days=1),
                }
            )
        from datetime import date as dt_date
        for dt_key in ("start_date", "end_date", "end_exclusive"):
            if dt_key in query_binds and isinstance(query_binds[dt_key], str):
                try:
                    query_binds[dt_key] = dt_date.fromisoformat(query_binds[dt_key][:10])
                except Exception:
                    pass
        return query_binds

    def _decimal(self, value: Any) -> Decimal:
        try:
            return Decimal(str(value or 0))
        except Exception:
            return Decimal("0")

    def _optional_decimal(self, value: Any) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    def _empty_totals(self) -> dict[str, Any]:
        totals: dict[str, Any] = {key: Decimal("0") for key in self.CATEGORY_VALUE_KEYS}
        totals.update(
            {
                "total_bruto": Decimal("0"),
                "total_movimentos_view": Decimal("0"),
                "saida_rb_devolucao": Decimal("0"),
                "desconto_comercial": Decimal("0"),
                "desconto_total": Decimal("0"),
                "desconto_movimentos_view": Decimal("0"),
                "pedidos_comerciais": 0,
                "pedidos_saida_rb": 0,
                "pedidos_devolucao": 0,
                "pedidos_saida_rb_devolucao": 0,
                "pedidos_bonificados": 0,
                "pedidos_transferencias": 0,
                "pedidos_outras_vendas": 0,
                "pedidos_remessa_uso_consumo": 0,
                "pedidos_outros": 0,
                "pedidos_total": 0,
                "pedidos_movimentos_view": 0,
                "source_row_count": 0,
                "commercial_row_count": 0,
                "eligible_non_transfer_row_count": 0,
                "quantidade_total": None,
                "clientes_distintos": 0,
            }
        )
        totals.update({f"{key}_row_count": 0 for key in self.CATEGORY_VALUE_KEYS})
        return totals

    def _pedido_key_for_category(self, category: str) -> str:
        return {
            "faturamento_comercial": "pedidos_comerciais",
            "saida_rb": "pedidos_saida_rb",
            "devolucao": "pedidos_devolucao",
            "venda_bonificada": "pedidos_bonificados",
            "transferencias": "pedidos_transferencias",
            "outras_vendas": "pedidos_outras_vendas",
            "remessa_uso_consumo": "pedidos_remessa_uso_consumo",
            "outros_movimentos": "pedidos_outros",
        }.get(category, "pedidos_outros")

    def _finalize_totals(self, totals: dict[str, Any]) -> dict[str, Any]:
        totals["saida_rb_devolucao"] = self._decimal(totals.get("saida_rb")) + self._decimal(totals.get("devolucao"))
        totals["pedidos_saida_rb_devolucao"] = int(totals.get("pedidos_saida_rb") or 0) + int(totals.get("pedidos_devolucao") or 0)
        totals["total_bruto"] = sum((self._decimal(totals[key]) for key in self.CATEGORY_TOTAL_BRUTO_KEYS), Decimal("0"))
        totals["total_movimentos_view"] = sum((self._decimal(totals[key]) for key in self.CATEGORY_VALUE_KEYS), Decimal("0"))
        return totals

    def _filial_sort_key(self, row: dict[str, Any]) -> tuple[int, str]:
        filial = str(row.get("filial") or "")
        try:
            return int(filial), filial
        except ValueError:
            return 999999, filial

    async def fetch_period_totals(
        self,
        session: Any,
        binds: dict[str, Any],
        *,
        filial: Any | None = None,
        vendedor: Any | None = None,
        produto: Any | None = None,
        all_history: bool = False,
        temporal_scope: EffectiveTemporalScope | None = None,
    ) -> dict[str, Any]:
        category_case = self.category_case_sql("lm")
        discount_source = await self.fetch_discount_source_profile(session)
        discount_expr = self.discount_expr_sql("lm", discount_source.get("desconto_fonte_coluna"))
        query_binds = self._with_default_binds(binds, filial, temporal_scope)
        filial_scope = self.filial_scope_sql("lm", filial or query_binds.get("sales_filial"))
        entity_scope = self.entity_scope_sql("lm", vendedor=vendedor, produto=produto)
        if vendedor not in (None, ""):
            query_binds["sales_vendedor"] = str(vendedor).strip()
        if produto not in (None, ""):
            query_binds["sales_produto"] = str(produto).strip()

        category_result = await session.execute(
            text(
                f"""
                WITH categorized AS (
                    SELECT
                        {category_case} AS categoria,
                        COALESCE(lm.ptotal_, 0) AS valor,
                        lm.qtde_ AS quantidade,
                        lm.pedido_ AS pedido,
                        lm.codcliente_ AS cliente,
                        {discount_expr} AS desconto
                    FROM vw_vendas_lm lm
                    WHERE {self.period_scope_sql("lm", all_history=all_history, temporal_scope=temporal_scope)}
                    {self.tenant_scope_sql("lm")}
                    {filial_scope}
                    {entity_scope}
                )
                SELECT
                    categoria,
                    COALESCE(SUM(valor), 0) AS valor,
                    COUNT(DISTINCT pedido) AS pedidos,
                    COALESCE(SUM(desconto), 0) AS desconto,
                    SUM(quantidade) AS quantidade,
                    COUNT(DISTINCT cliente) AS clientes_distintos,
                    COUNT(*) AS source_rows
                FROM categorized
                GROUP BY categoria
                """
            ),
            query_binds,
        )

        totals = self._empty_totals()
        for row in category_result.mappings().all():
            category = str(row.get("categoria") or "outros_movimentos")
            value = self._decimal(row.get("valor"))
            discount = self._decimal(row.get("desconto"))
            quantity = self._optional_decimal(row.get("quantidade"))
            source_row_count = int(row.get("source_rows") or 0)
            if category not in self.CATEGORY_VALUE_KEYS:
                category = "outros_movimentos"
            totals[category] += value
            totals[self._pedido_key_for_category(category)] = int(row.get("pedidos") or 0)
            totals[f"{category}_row_count"] += source_row_count
            if category == "faturamento_comercial":
                totals["desconto_comercial"] += discount
                if quantity is not None:
                    totals["quantidade_total"] = self._decimal(totals.get("quantidade_total")) + quantity
                totals["clientes_distintos"] = int(row.get("clientes_distintos") or 0)
                totals["commercial_row_count"] += source_row_count
            if category != "transferencias":
                totals["desconto_total"] += discount
                totals["eligible_non_transfer_row_count"] += source_row_count
            totals["desconto_movimentos_view"] += discount
            totals["source_row_count"] += source_row_count

        total_result = await session.execute(
            text(
                f"""
                WITH categorized AS (
                    SELECT
                        {category_case} AS categoria,
                        lm.pedido_ AS pedido
                    FROM vw_vendas_lm lm
                    WHERE {self.period_scope_sql("lm", all_history=all_history, temporal_scope=temporal_scope)}
                    {self.tenant_scope_sql("lm")}
                    {filial_scope}
                    {entity_scope}
                )
                SELECT
                    COUNT(DISTINCT CASE WHEN categoria <> 'transferencias' THEN pedido END) AS pedidos_total,
                    COUNT(DISTINCT pedido) AS pedidos_movimentos_view
                FROM categorized
                """
            ),
            query_binds,
        )
        total_row = total_result.mappings().first() or {}
        totals["pedidos_total"] = int(total_row.get("pedidos_total") or 0)
        totals["pedidos_movimentos_view"] = int(total_row.get("pedidos_movimentos_view") or 0)
        totals.update(discount_source)
        return self._finalize_totals(totals)

    async def fetch_document_details(
        self,
        session: Any,
        binds: dict[str, Any],
        *,
        filial: Any | None = None,
        category_key: str = "faturamento_comercial",
        limit: int = 500,
        temporal_scope: EffectiveTemporalScope | None = None,
    ) -> list[dict[str, Any]]:
        """Returns document-level traceability from the synchronized PostgreSQL view."""
        columns_result = await session.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'vw_vendas_lm'
                """
            )
        )
        columns = {str(row[0]).lower() for row in columns_result.fetchall()}
        if not {"pedido_", "dtemissao_", "ptotal_"}.issubset(columns):
            return []

        category_case = self.category_case_sql("lm")
        allowed_categories = set(self.CATEGORY_VALUE_KEYS) | {"total_bruto", "total_movimentos_view"}
        if category_key not in allowed_categories:
            category_key = "faturamento_comercial"
        if category_key == "total_bruto":
            category_filter = "categoria <> 'transferencias'"
        elif category_key == "total_movimentos_view":
            category_filter = "TRUE"
        else:
            category_filter = "categoria = :document_category"

        query_binds = self._with_default_binds(binds, filial, temporal_scope)
        query_binds.update({"document_category": category_key, "document_limit": max(1, min(int(limit), 2000))})
        filial_scope = self.filial_scope_sql("lm", filial or query_binds.get("sales_filial"))

        def optional(name: str, fallback: str = "NULL") -> str:
            return f"lm.{name}" if name.lower() in columns else fallback

        note_expr = optional("numero_nfe", optional("nota_"))
        series_expr = optional("serie_")
        customer_expr = optional("codcliente_")
        seller_expr = optional("codvendedor_", optional("vendedor_"))
        cfop_expr = optional("cfop_")
        type_expr = optional("tp_")
        description_expr = optional("tpdescricao_", "''")

        result = await session.execute(
            text(
                f"""
                WITH categorized AS (
                    SELECT
                        lm.dtemissao_ AS data_emissao,
                        COALESCE(NULLIF(TRIM(lm.filial_), ''), 'Sem filial') AS filial,
                        lm.pedido_ AS pedido,
                        {note_expr} AS nota,
                        {series_expr} AS serie,
                        {customer_expr} AS codigo_cliente,
                        {seller_expr} AS codigo_vendedor,
                        {cfop_expr} AS cfop,
                        {type_expr} AS tipo_operacao,
                        {description_expr} AS descricao_operacao,
                        {category_case} AS categoria,
                        COALESCE(lm.ptotal_, 0) AS valor
                    FROM vw_vendas_lm lm
                    WHERE {self.period_scope_sql("lm", temporal_scope=temporal_scope)}
                    {self.tenant_scope_sql("lm")}
                    {filial_scope}
                )
                SELECT
                    data_emissao,
                    filial,
                    pedido,
                    nota,
                    serie,
                    codigo_cliente,
                    codigo_vendedor,
                    cfop,
                    tipo_operacao,
                    descricao_operacao,
                    categoria,
                    COALESCE(SUM(valor), 0) AS valor_documento
                FROM categorized
                WHERE {category_filter}
                GROUP BY data_emissao, filial, pedido, nota, serie, codigo_cliente,
                         codigo_vendedor, cfop, tipo_operacao, descricao_operacao, categoria
                ORDER BY data_emissao DESC, filial, pedido
                LIMIT :document_limit
                """
            ),
            query_binds,
        )
        return [dict(row) for row in result.mappings().all()]

    async def fetch_period_totals_by_filial(
        self,
        session: Any,
        binds: dict[str, Any],
        *,
        filial: Any | None = None,
        vendedor: Any | None = None,
        produto: Any | None = None,
        all_history: bool = False,
        temporal_scope: EffectiveTemporalScope | None = None,
    ) -> list[dict[str, Any]]:
        category_case = self.category_case_sql("lm")
        discount_source = await self.fetch_discount_source_profile(session)
        discount_expr = self.discount_expr_sql("lm", discount_source.get("desconto_fonte_coluna"))
        query_binds = self._with_default_binds(binds, filial, temporal_scope)
        filial_scope = self.filial_scope_sql("lm", filial or query_binds.get("sales_filial"))
        entity_scope = self.entity_scope_sql("lm", vendedor=vendedor, produto=produto)
        if vendedor not in (None, ""):
            query_binds["sales_vendedor"] = str(vendedor).strip()
        if produto not in (None, ""):
            query_binds["sales_produto"] = str(produto).strip()

        category_result = await session.execute(
            text(
                f"""
                WITH categorized AS (
                    SELECT
                        COALESCE(NULLIF(TRIM(lm.filial_), ''), 'Sem filial') AS filial,
                        {category_case} AS categoria,
                        COALESCE(lm.ptotal_, 0) AS valor,
                        lm.qtde_ AS quantidade,
                        lm.pedido_ AS pedido,
                        lm.codcliente_ AS cliente,
                        {discount_expr} AS desconto
                    FROM vw_vendas_lm lm
                    WHERE {self.period_scope_sql("lm", all_history=all_history, temporal_scope=temporal_scope)}
                    {self.tenant_scope_sql("lm")}
                    {filial_scope}
                    {entity_scope}
                )
                SELECT
                    filial,
                    categoria,
                    COALESCE(SUM(valor), 0) AS valor,
                    COUNT(DISTINCT pedido) AS pedidos,
                    COALESCE(SUM(desconto), 0) AS desconto,
                    SUM(quantidade) AS quantidade,
                    COUNT(DISTINCT cliente) AS clientes_distintos,
                    COUNT(*) AS source_rows
                FROM categorized
                GROUP BY filial, categoria
                """
            ),
            query_binds,
        )

        by_filial: dict[str, dict[str, Any]] = {}
        for row in category_result.mappings().all():
            filial_key = str(row.get("filial") or "Sem filial")
            totals = by_filial.setdefault(filial_key, {"filial": filial_key, **self._empty_totals()})
            category = str(row.get("categoria") or "outros_movimentos")
            if category not in self.CATEGORY_VALUE_KEYS:
                category = "outros_movimentos"
            value = self._decimal(row.get("valor"))
            discount = self._decimal(row.get("desconto"))
            quantity = self._optional_decimal(row.get("quantidade"))
            source_row_count = int(row.get("source_rows") or 0)
            totals[category] += value
            totals[self._pedido_key_for_category(category)] = int(row.get("pedidos") or 0)
            totals[f"{category}_row_count"] += source_row_count
            if category == "faturamento_comercial":
                totals["desconto_comercial"] += discount
                if quantity is not None:
                    totals["quantidade_total"] = self._decimal(totals.get("quantidade_total")) + quantity
                totals["clientes_distintos"] = int(row.get("clientes_distintos") or 0)
                totals["commercial_row_count"] += source_row_count
            if category != "transferencias":
                totals["desconto_total"] += discount
                totals["eligible_non_transfer_row_count"] += source_row_count
            totals["desconto_movimentos_view"] += discount
            totals["source_row_count"] += source_row_count

        total_result = await session.execute(
            text(
                f"""
                WITH categorized AS (
                    SELECT
                        COALESCE(NULLIF(TRIM(lm.filial_), ''), 'Sem filial') AS filial,
                        {category_case} AS categoria,
                        lm.pedido_ AS pedido
                    FROM vw_vendas_lm lm
                    WHERE {self.period_scope_sql("lm", all_history=all_history, temporal_scope=temporal_scope)}
                    {self.tenant_scope_sql("lm")}
                    {filial_scope}
                    {entity_scope}
                )
                SELECT
                    filial,
                    COUNT(DISTINCT CASE WHEN categoria <> 'transferencias' THEN pedido END) AS pedidos_total,
                    COUNT(DISTINCT pedido) AS pedidos_movimentos_view
                FROM categorized
                GROUP BY filial
                """
            ),
            query_binds,
        )
        for row in total_result.mappings().all():
            filial_key = str(row.get("filial") or "Sem filial")
            totals = by_filial.setdefault(filial_key, {"filial": filial_key, **self._empty_totals()})
            totals["pedidos_total"] = int(row.get("pedidos_total") or 0)
            totals["pedidos_movimentos_view"] = int(row.get("pedidos_movimentos_view") or 0)

        rows = []
        for totals in by_filial.values():
            totals.update(discount_source)
            rows.append(self._finalize_totals(totals))
        return sorted(rows, key=self._filial_sort_key)

    async def fetch_vendor_ranking(
        self,
        session: Any,
        binds: dict[str, Any],
        *,
        limit: int | None,
        by_discount: bool = False,
        ranking_value_key: str = "faturamento_comercial",
        filial: Any | None = None,
        temporal_scope: EffectiveTemporalScope | None = None,
    ) -> list[dict[str, Any]]:
        return await self._fetch_dimension_ranking_by_filial(
            session,
            binds,
            dimension_sql="v.nome_ved",
            dimension_alias="vendedor",
            join_sql=(
                "INNER JOIN vw_vendedor_cad_lm v "
                "ON coalesce(nullif(ltrim(lm.rca_::text, '0'), ''), '0') "
                "= coalesce(nullif(ltrim(v.codi_ved::text, '0'), ''), '0')"
            ),
            extra_where="AND UPPER(COALESCE(v.nome_ved, '')) <> 'PADRAO'",
            limit=limit,
            by_discount=by_discount,
            ranking_value_key=ranking_value_key,
            filial=filial,
            temporal_scope=temporal_scope,
        )

    async def fetch_client_ranking(
        self,
        session: Any,
        binds: dict[str, Any],
        *,
        limit: int | None,
        ranking_value_key: str = "faturamento_comercial",
        filial: Any | None = None,
        temporal_scope: EffectiveTemporalScope | None = None,
    ) -> list[dict[str, Any]]:
        return await self._fetch_dimension_ranking_by_filial(
            session,
            binds,
            dimension_sql="c.nome",
            dimension_alias="cliente",
            join_sql=(
                "INNER JOIN vw_clientes_cad_lm c "
                "ON coalesce(nullif(ltrim(lm.codcliente_::text, '0'), ''), '0') "
                "= coalesce(nullif(ltrim(c.codigo::text, '0'), ''), '0')"
            ),
            extra_where="AND UPPER(COALESCE(c.nome, '')) <> 'LAGES E LOPES LTDA'",
            limit=limit,
            by_discount=False,
            ranking_value_key=ranking_value_key,
            filial=filial,
            temporal_scope=temporal_scope,
        )

    async def fetch_product_ranking(
        self,
        session: Any,
        binds: dict[str, Any],
        *,
        limit: int | None = 10,
        filial: Any | None = None,
        temporal_scope: EffectiveTemporalScope | None = None,
    ) -> list[dict[str, Any]]:
        query_binds = self._with_default_binds(binds, filial, temporal_scope)
        filial_where = self.filial_scope_sql(alias="lm", filial=filial)
        period_where = self.period_scope_sql(alias="lm", temporal_scope=temporal_scope)
        limit_sql = f"LIMIT {limit}" if limit and limit > 0 else ""

        sql = text(
            f"""
            SELECT 
                coalesce(p.nome_produto, lm.descricao_) as produto,
                lm.codprod_::text as codigo_produto,
                sum(lm.qtde_) as quantidade_vendida,
                coalesce(sum(lm.ptotal_), 0) as valor_total,
                coalesce(max(p.estoque), 0) as estoque_atual,
                coalesce(lm.filial_::text, '1') as filial
            FROM vw_vendas_lm lm
            LEFT JOIN vw_produtos_cad_lm p 
                ON coalesce(nullif(ltrim(lm.codprod_::text, '0'), ''), '0') = coalesce(nullif(ltrim(p.codigo::text, '0'), ''), '0')
            WHERE lm.tp_ IN (2, 61)
              AND {period_where}
              {self.tenant_scope_sql("lm")}
              {filial_where}
            GROUP BY 1, 2, 6
            ORDER BY quantidade_vendida DESC NULLS LAST, valor_total DESC
            {limit_sql}
            """
        )
        res = await session.execute(sql, query_binds)
        rows = []
        for idx, row in enumerate(res.fetchall(), 1):
            mapping = dict(row._mapping)
            v_total = float(mapping.get("valor_total") or 0)
            quantity_value = mapping.get("quantidade_vendida")
            q_total = float(quantity_value) if quantity_value is not None else None
            e_atual = float(mapping.get("estoque_atual") or 0)
            rows.append({
                "posicao": idx,
                "produto": str(mapping.get("produto") or "Produto N/A"),
                "codigo_produto": str(mapping.get("codigo_produto") or ""),
                "quantidade_vendida": q_total,
                "valor_total": v_total,
                "valor_formatado": f"R$ {v_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                "estoque_atual": e_atual,
                "filial": str(mapping.get("filial") or "1"),
            })
        return rows

    async def fetch_financial_open(
        self,
        session: Any,
        binds: dict[str, Any],
        *,
        limit: int | None = 50,
    ) -> list[dict[str, Any]]:
        query_binds = self._with_default_binds(binds)
        limit_sql = f"LIMIT {limit}" if limit and limit > 0 else ""
        sql = text(
            f"""
            SELECT 
                f.financeiro_id,
                f.status_pagamento,
                f.valor_parcela,
                f.data_vencimento,
                coalesce(c.nome, f.cliente_id::text) as cliente
            FROM vw_financeiro_lm f
            LEFT JOIN vw_clientes_cad_lm c 
                ON coalesce(nullif(ltrim(f.cliente_id::text, '0'), ''), '0') = coalesce(nullif(ltrim(c.codigo::text, '0'), ''), '0')
            WHERE f.tenant_id = :tenant_id
            ORDER BY f.data_vencimento ASC
            {limit_sql}
            """
        )
        res = await session.execute(sql, query_binds)
        rows = []
        for idx, row in enumerate(res.fetchall(), 1):
            mapping = dict(row._mapping)
            v_parcela = float(mapping.get("valor_parcela") or 0)
            rows.append({
                "posicao": idx,
                "financeiro_id": str(mapping.get("financeiro_id") or ""),
                "cliente": str(mapping.get("cliente") or "Cliente N/A"),
                "status_pagamento": str(mapping.get("status_pagamento") or "EM_ABERTO"),
                "valor_parcela": v_parcela,
                "valor_formatado": f"R$ {v_parcela:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                "data_vencimento": str(mapping.get("data_vencimento") or ""),
            })
        return rows


    async def _fetch_dimension_ranking_by_filial(
        self,
        session: Any,
        binds: dict[str, Any],
        *,
        dimension_sql: str,
        dimension_alias: str,
        join_sql: str,
        extra_where: str,
        limit: int | None,
        by_discount: bool,
        ranking_value_key: str,
        filial: Any | None,
        temporal_scope: EffectiveTemporalScope | None,
    ) -> list[dict[str, Any]]:
        category_case = self.category_case_sql("lm")
        discount_source = await self.fetch_discount_source_profile(session)
        discount_expr = self.discount_expr_sql("lm", discount_source.get("desconto_fonte_coluna"))
        query_binds = self._with_default_binds(binds, filial, temporal_scope)
        filial_scope = self.filial_scope_sql("lm", filial or query_binds.get("sales_filial"))
        limit_clause = "LIMIT :limit" if limit else ""
        if limit:
            query_binds["limit"] = limit
        allowed_ranking_keys = {*self.CATEGORY_VALUE_KEYS, "total_bruto", "total_movimentos_view"}
        if ranking_value_key not in allowed_ranking_keys:
            ranking_value_key = "faturamento_comercial"
        order_column = "ranking_desconto_total" if by_discount else f"ranking_{ranking_value_key}"
        ranking_filter = "WHERE ranking_desconto_total > 0" if by_discount else f"WHERE {order_column} <> 0"

        result = await session.execute(
            text(
                f"""
                WITH categorized AS (
                    SELECT
                        {dimension_sql} AS {dimension_alias},
                        COALESCE(NULLIF(TRIM(lm.filial_), ''), 'Sem filial') AS filial,
                        {category_case} AS categoria,
                        COALESCE(lm.ptotal_, 0) AS valor,
                        lm.pedido_ AS pedido,
                        {discount_expr} AS desconto
                    FROM vw_vendas_lm lm
                    {join_sql}
                    WHERE {self.period_scope_sql("lm", temporal_scope=temporal_scope)}
                    {self.tenant_scope_sql("lm")}
                    {filial_scope}
                    {extra_where}
                ),
                by_dimension AS (
                    SELECT
                        {dimension_alias},
                        COALESCE(SUM(CASE WHEN categoria = 'faturamento_comercial' THEN valor ELSE 0 END), 0) AS ranking_faturamento_comercial,
                        COALESCE(SUM(CASE WHEN categoria = 'saida_rb' THEN valor ELSE 0 END), 0) AS ranking_saida_rb,
                        COALESCE(SUM(CASE WHEN categoria = 'devolucao' THEN valor ELSE 0 END), 0) AS ranking_devolucao,
                        COALESCE(SUM(CASE WHEN categoria = 'venda_bonificada' THEN valor ELSE 0 END), 0) AS ranking_venda_bonificada,
                        COALESCE(SUM(CASE WHEN categoria = 'transferencias' THEN valor ELSE 0 END), 0) AS ranking_transferencias,
                        COALESCE(SUM(CASE WHEN categoria = 'outras_vendas' THEN valor ELSE 0 END), 0) AS ranking_outras_vendas,
                        COALESCE(SUM(CASE WHEN categoria = 'remessa_uso_consumo' THEN valor ELSE 0 END), 0) AS ranking_remessa_uso_consumo,
                        COALESCE(SUM(CASE WHEN categoria = 'outros_movimentos' THEN valor ELSE 0 END), 0) AS ranking_outros_movimentos,
                        COALESCE(SUM(CASE WHEN categoria <> 'transferencias' THEN valor ELSE 0 END), 0) AS ranking_total_bruto,
                        COALESCE(SUM(valor), 0) AS ranking_total_movimentos_view,
                        COUNT(DISTINCT CASE WHEN categoria = 'faturamento_comercial' THEN pedido END) AS ranking_pedidos_comerciais,
                        COUNT(DISTINCT CASE WHEN categoria = 'saida_rb' THEN pedido END) AS ranking_pedidos_saida_rb,
                        COUNT(DISTINCT CASE WHEN categoria = 'devolucao' THEN pedido END) AS ranking_pedidos_devolucao,
                        COUNT(DISTINCT CASE WHEN categoria = 'venda_bonificada' THEN pedido END) AS ranking_pedidos_bonificados,
                        COUNT(DISTINCT CASE WHEN categoria = 'transferencias' THEN pedido END) AS ranking_pedidos_transferencias,
                        COUNT(DISTINCT CASE WHEN categoria = 'outras_vendas' THEN pedido END) AS ranking_pedidos_outras_vendas,
                        COUNT(DISTINCT CASE WHEN categoria = 'remessa_uso_consumo' THEN pedido END) AS ranking_pedidos_remessa_uso_consumo,
                        COUNT(DISTINCT CASE WHEN categoria = 'outros_movimentos' THEN pedido END) AS ranking_pedidos_outros,
                        COUNT(DISTINCT CASE WHEN categoria <> 'transferencias' THEN pedido END) AS ranking_pedidos_total,
                        COUNT(DISTINCT pedido) AS ranking_pedidos_movimentos_view,
                        COALESCE(SUM(CASE WHEN categoria = 'faturamento_comercial' THEN desconto ELSE 0 END), 0) AS ranking_desconto_comercial,
                        COALESCE(SUM(CASE WHEN categoria <> 'transferencias' THEN desconto ELSE 0 END), 0) AS ranking_desconto_total,
                        COALESCE(SUM(desconto), 0) AS ranking_desconto_movimentos_view
                    FROM categorized
                    GROUP BY {dimension_alias}
                ),
                ranked_dimensions AS (
                    SELECT * FROM by_dimension
                    {ranking_filter}
                ),
                limited_dimensions AS (
                    SELECT
                        ROW_NUMBER() OVER (ORDER BY {order_column} DESC, {dimension_alias} ASC) AS posicao,
                        *
                    FROM ranked_dimensions
                    ORDER BY {order_column} DESC, {dimension_alias} ASC
                    {limit_clause}
                ),
                by_filial AS (
                    SELECT
                        {dimension_alias},
                        filial,
                        COALESCE(SUM(CASE WHEN categoria = 'faturamento_comercial' THEN valor ELSE 0 END), 0) AS faturamento_comercial,
                        COALESCE(SUM(CASE WHEN categoria = 'saida_rb' THEN valor ELSE 0 END), 0) AS saida_rb,
                        COALESCE(SUM(CASE WHEN categoria = 'devolucao' THEN valor ELSE 0 END), 0) AS devolucao,
                        COALESCE(SUM(CASE WHEN categoria = 'venda_bonificada' THEN valor ELSE 0 END), 0) AS venda_bonificada,
                        COALESCE(SUM(CASE WHEN categoria = 'transferencias' THEN valor ELSE 0 END), 0) AS transferencias,
                        COALESCE(SUM(CASE WHEN categoria = 'outras_vendas' THEN valor ELSE 0 END), 0) AS outras_vendas,
                        COALESCE(SUM(CASE WHEN categoria = 'remessa_uso_consumo' THEN valor ELSE 0 END), 0) AS remessa_uso_consumo,
                        COALESCE(SUM(CASE WHEN categoria = 'outros_movimentos' THEN valor ELSE 0 END), 0) AS outros_movimentos,
                        COALESCE(SUM(CASE WHEN categoria <> 'transferencias' THEN valor ELSE 0 END), 0) AS total_bruto,
                        COALESCE(SUM(valor), 0) AS total_movimentos_view,
                        COUNT(DISTINCT CASE WHEN categoria = 'faturamento_comercial' THEN pedido END) AS pedidos_comerciais,
                        COUNT(DISTINCT CASE WHEN categoria = 'saida_rb' THEN pedido END) AS pedidos_saida_rb,
                        COUNT(DISTINCT CASE WHEN categoria = 'devolucao' THEN pedido END) AS pedidos_devolucao,
                        COUNT(DISTINCT CASE WHEN categoria = 'venda_bonificada' THEN pedido END) AS pedidos_bonificados,
                        COUNT(DISTINCT CASE WHEN categoria = 'transferencias' THEN pedido END) AS pedidos_transferencias,
                        COUNT(DISTINCT CASE WHEN categoria = 'outras_vendas' THEN pedido END) AS pedidos_outras_vendas,
                        COUNT(DISTINCT CASE WHEN categoria = 'remessa_uso_consumo' THEN pedido END) AS pedidos_remessa_uso_consumo,
                        COUNT(DISTINCT CASE WHEN categoria = 'outros_movimentos' THEN pedido END) AS pedidos_outros,
                        COUNT(DISTINCT CASE WHEN categoria <> 'transferencias' THEN pedido END) AS pedidos_total,
                        COUNT(DISTINCT pedido) AS pedidos_movimentos_view,
                        COALESCE(SUM(CASE WHEN categoria = 'faturamento_comercial' THEN desconto ELSE 0 END), 0) AS desconto_comercial,
                        COALESCE(SUM(CASE WHEN categoria <> 'transferencias' THEN desconto ELSE 0 END), 0) AS desconto_total,
                        COALESCE(SUM(desconto), 0) AS desconto_movimentos_view
                    FROM categorized
                    GROUP BY {dimension_alias}, filial
                )
                SELECT
                    ld.posicao,
                    ld.{dimension_alias},
                    bf.filial,
                    bf.faturamento_comercial,
                    bf.saida_rb,
                    bf.devolucao,
                    bf.venda_bonificada,
                    bf.transferencias,
                    bf.outras_vendas,
                    bf.remessa_uso_consumo,
                    bf.outros_movimentos,
                    bf.total_bruto,
                    bf.total_movimentos_view,
                    bf.pedidos_comerciais,
                    bf.pedidos_saida_rb,
                    bf.pedidos_devolucao,
                    bf.pedidos_bonificados,
                    bf.pedidos_transferencias,
                    bf.pedidos_outras_vendas,
                    bf.pedidos_remessa_uso_consumo,
                    bf.pedidos_outros,
                    bf.pedidos_total,
                    bf.pedidos_movimentos_view,
                    bf.desconto_comercial,
                    bf.desconto_total,
                    bf.desconto_movimentos_view,
                    ld.ranking_faturamento_comercial,
                    ld.ranking_saida_rb,
                    ld.ranking_devolucao,
                    ld.ranking_venda_bonificada,
                    ld.ranking_transferencias,
                    ld.ranking_outras_vendas,
                    ld.ranking_remessa_uso_consumo,
                    ld.ranking_outros_movimentos,
                    ld.ranking_total_bruto,
                    ld.ranking_total_movimentos_view,
                    ld.ranking_pedidos_comerciais,
                    ld.ranking_pedidos_saida_rb,
                    ld.ranking_pedidos_devolucao,
                    ld.ranking_pedidos_bonificados,
                    ld.ranking_pedidos_transferencias,
                    ld.ranking_pedidos_outras_vendas,
                    ld.ranking_pedidos_remessa_uso_consumo,
                    ld.ranking_pedidos_outros,
                    ld.ranking_pedidos_total,
                    ld.ranking_pedidos_movimentos_view,
                    ld.ranking_desconto_comercial,
                    ld.ranking_desconto_total,
                    ld.ranking_desconto_movimentos_view
                FROM limited_dimensions ld
                INNER JOIN by_filial bf ON bf.{dimension_alias} = ld.{dimension_alias}
                ORDER BY ld.posicao, bf.faturamento_comercial DESC, bf.filial ASC
                """
            ),
            query_binds,
        )
        rows = []
        for row in result.mappings().all():
            item = dict(row)
            item.update(discount_source)
            rows.append(item)
        return rows


sales_value_breakdown = SalesValueBreakdownService()
