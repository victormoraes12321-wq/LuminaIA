from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from typing import Any
import calendar
import inspect

from services.sales_value_breakdown import sales_value_breakdown


RECONCILIATION_VERSION = "2026-07-20.erp-reconciliation"
OFFICIAL_ERP_FILTERS: dict[str, str] = {
    "period": "dtemissao_ >= start_date AND dtemissao_ < end_exclusive",
    "commercial_revenue": "tp_ IN (2, 61)",
    "saida_rb": "tp_ = 9 OR UPPER(tpdescricao_) LIKE '%SAIDA RB%'",
    "devolucao": "UPPER(tpdescricao_) LIKE '%DEVOL%'",
    "bonificados": "tp_ = 22 OR UPPER(tpdescricao_) LIKE '%BONIFIC%'",
    "transferencias": "tp_ IN (3, 31, 96) OR UPPER(tpdescricao_) LIKE '%TRANSFERENCIA%'",
    "filial": "filial_ = selected_filial when the user asks for one filial",
    "vendedor_ranking_exclusion": "UPPER(nome_ved) <> 'PADRAO'",
    "cliente_ranking_exclusion": "UPPER(nome) <> 'LAGES E LOPES LTDA'",
    "total_bruto": "Soma movimentos classificados exceto transferencias",
    "ticket_medio": "commercial_revenue / COUNT(DISTINCT pedido_) inside the same period and filial scope",
    "cancelados": "No explicit cancelado/status column exists in vw_vendas_lm clone; must be validated in ERP source contract.",
    "cfop": "cfop_ is preserved for audit, but the default commercial rule is type-based until ERP validates a CFOP exclusion list.",
    "status": "No explicit operational status column exists in vw_vendas_lm clone.",
}


@dataclass(frozen=True)
class ReconciliationPeriod:
    label: str
    start_date: date
    end_date: date
    end_exclusive: date


class ERPReconciliationService:
    """Builds repeatable ERP-vs-clone reconciliation reports for critical KPIs."""

    tolerance = Decimal("0.01")

    def parse_period(self, period: str) -> ReconciliationPeriod:
        raw = str(period or "").strip()
        if not raw:
            raise ValueError("periodo vazio")
        if len(raw) == 7 and raw[4] == "-":
            year = int(raw[:4])
            month = int(raw[5:7])
            last_day = calendar.monthrange(year, month)[1]
            start = date(year, month, 1)
            end = date(year, month, last_day)
            return ReconciliationPeriod(
                label=f"{year:04d}-{month:02d}",
                start_date=start,
                end_date=end,
                end_exclusive=end + timedelta(days=1),
            )
        parsed = date.fromisoformat(raw)
        return ReconciliationPeriod(
            label=parsed.isoformat(),
            start_date=parsed,
            end_date=parsed,
            end_exclusive=parsed + timedelta(days=1),
        )

    def binds_for_period(self, period: ReconciliationPeriod, filial: Any | None = None) -> dict[str, Any]:
        return {
            "start_date": period.start_date,
            "end_date": period.end_date,
            "end_exclusive": period.end_exclusive,
            **sales_value_breakdown.default_binds(filial),
        }

    async def reconcile(
        self,
        session: Any,
        *,
        periods: list[str],
        oracle_connection: Any | None = None,
        oracle_error: dict[str, Any] | None = None,
        include_oracle: bool = True,
    ) -> dict[str, Any]:
        parsed_periods = [self.parse_period(period) for period in periods]
        period_reports = []
        for period in parsed_periods:
            clone = await self.build_clone_period_report(session, period)
            oracle = None
            if include_oracle and oracle_connection is not None:
                oracle = await self.build_oracle_period_report(oracle_connection, period)
            elif include_oracle:
                oracle = {
                    "status": "oracle_unavailable",
                    "error": oracle_error or {"code": "ORACLE_NOT_CONNECTED", "message": "Oracle connection was not available."},
                }
            else:
                oracle = {"status": "skipped", "error": None}

            comparison = self.compare_period_reports(clone, oracle)
            period_reports.append(
                {
                    "period": period.label,
                    "range": {
                        "start_date": period.start_date.isoformat(),
                        "end_date": period.end_date.isoformat(),
                        "end_exclusive": period.end_exclusive.isoformat(),
                    },
                    "clone": clone,
                    "erp": oracle,
                    "comparison": comparison,
                }
            )

        comparison_statuses = {str(item["comparison"]["status"]) for item in period_reports}
        overall_status = "ok"
        if "mismatch" in comparison_statuses:
            overall_status = "mismatch"
        elif comparison_statuses & {"oracle_unavailable", "skipped"}:
            overall_status = "needs_erp_connection"
        elif comparison_statuses != {"ok"}:
            overall_status = "oracle_query_failed"

        return self._json_safe({
            "version": RECONCILIATION_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "official_filters": OFFICIAL_ERP_FILTERS,
            "overall_status": overall_status,
            "periods": period_reports,
        })

    async def build_clone_period_report(self, session: Any, period: ReconciliationPeriod) -> dict[str, Any]:
        binds = self.binds_for_period(period)
        totals = await sales_value_breakdown.fetch_period_totals(session, binds)
        by_filial = await sales_value_breakdown.fetch_period_totals_by_filial(session, binds)
        vendor_ranking = await sales_value_breakdown.fetch_vendor_ranking(
            session,
            binds,
            limit=None,
            ranking_value_key="faturamento_comercial",
        )
        vendor_rb_ranking = await sales_value_breakdown.fetch_vendor_ranking(
            session,
            binds,
            limit=None,
            ranking_value_key="saida_rb",
        )
        vendor_devolucao_ranking = await sales_value_breakdown.fetch_vendor_ranking(
            session,
            binds,
            limit=None,
            ranking_value_key="devolucao",
        )
        client_ranking = await sales_value_breakdown.fetch_client_ranking(
            session,
            binds,
            limit=50,
            ranking_value_key="faturamento_comercial",
        )

        return self._json_safe(
            {
                "status": "ok",
                "faturamento_total": self._sales_total_payload(totals),
                "faturamento_por_filial": [self._sales_total_payload(row, filial=row.get("filial")) for row in by_filial],
                "ranking_vendedores": self._aggregate_dimension_rows(vendor_ranking, "vendedor", "faturamento_comercial"),
                "ranking_vendedores_rb": self._aggregate_dimension_rows(vendor_rb_ranking, "vendedor", "saida_rb"),
                "ranking_vendedores_devolucao": self._aggregate_dimension_rows(vendor_devolucao_ranking, "vendedor", "devolucao"),
                "saida_rb": {
                    "valor": self._decimal(totals.get("saida_rb")),
                    "pedidos": int(totals.get("pedidos_saida_rb") or 0),
                    "por_filial": [
                        {
                            "filial": row.get("filial"),
                            "valor": self._decimal(row.get("saida_rb")),
                            "pedidos": int(row.get("pedidos_saida_rb") or 0),
                        }
                        for row in by_filial
                    ],
                },
                "devolucao": {
                    "valor": self._decimal(totals.get("devolucao")),
                    "pedidos": int(totals.get("pedidos_devolucao") or 0),
                    "por_filial": [
                        {
                            "filial": row.get("filial"),
                            "valor": self._decimal(row.get("devolucao")),
                            "pedidos": int(row.get("pedidos_devolucao") or 0),
                        }
                        for row in by_filial
                    ],
                },
                "ticket_medio": {
                    "valor": self._ticket(totals, gross=False),
                    "valor_bruto": self._ticket(totals, gross=True),
                    "pedidos_comerciais": int(totals.get("pedidos_comerciais") or 0),
                    "pedidos_total": int(totals.get("pedidos_total") or 0),
                    "por_filial": [
                        {
                            "filial": row.get("filial"),
                            "valor": self._ticket(row, gross=False),
                            "valor_bruto": self._ticket(row, gross=True),
                            "pedidos_comerciais": int(row.get("pedidos_comerciais") or 0),
                            "pedidos_total": int(row.get("pedidos_total") or 0),
                        }
                        for row in by_filial
                    ],
                },
                "top_clientes": self._aggregate_dimension_rows(client_ranking, "cliente", "faturamento_comercial"),
                "discount_source": {
                    "type": totals.get("desconto_fonte_tipo"),
                    "column": totals.get("desconto_fonte_coluna"),
                    "confidence": totals.get("desconto_fonte_confianca"),
                    "observation": totals.get("desconto_fonte_observacao"),
                },
            }
        )

    async def build_oracle_period_report(self, connection: Any, period: ReconciliationPeriod) -> dict[str, Any]:
        binds = {
            "start_date": period.start_date.isoformat(),
            "end_exclusive": period.end_exclusive.isoformat(),
        }
        try:
            oracle_sources = await self._resolve_oracle_sources(connection)
            totals = await self._oracle_fetch_totals(connection, binds, sales_view=oracle_sources["sales"])
            by_filial = await self._oracle_fetch_totals_by_filial(connection, binds, sales_view=oracle_sources["sales"])
            vendors = await self._oracle_fetch_dimension_ranking(
                connection,
                binds,
                sales_view=oracle_sources["sales"],
                dimension_alias="vendedor",
                dimension_sql="v.nome_ved",
                join_sql=(
                    f"INNER JOIN {oracle_sources['seller']} v "
                    "ON NVL(NULLIF(LTRIM(TO_CHAR(lm.rca_), '0'), ''), '0') "
                    "= NVL(NULLIF(LTRIM(TO_CHAR(v.codi_ved), '0'), ''), '0')"
                ),
                extra_where="AND UPPER(NVL(v.nome_ved, '')) <> 'PADRAO'",
                ranking_value_key="faturamento_comercial",
                limit=None,
            )
            vendors_rb = await self._oracle_fetch_dimension_ranking(
                connection,
                binds,
                sales_view=oracle_sources["sales"],
                dimension_alias="vendedor",
                dimension_sql="v.nome_ved",
                join_sql=(
                    f"INNER JOIN {oracle_sources['seller']} v "
                    "ON NVL(NULLIF(LTRIM(TO_CHAR(lm.rca_), '0'), ''), '0') "
                    "= NVL(NULLIF(LTRIM(TO_CHAR(v.codi_ved), '0'), ''), '0')"
                ),
                extra_where="AND UPPER(NVL(v.nome_ved, '')) <> 'PADRAO'",
                ranking_value_key="saida_rb",
                limit=None,
            )
            vendors_devolucao = await self._oracle_fetch_dimension_ranking(
                connection,
                binds,
                sales_view=oracle_sources["sales"],
                dimension_alias="vendedor",
                dimension_sql="v.nome_ved",
                join_sql=(
                    f"INNER JOIN {oracle_sources['seller']} v "
                    "ON NVL(NULLIF(LTRIM(TO_CHAR(lm.rca_), '0'), ''), '0') "
                    "= NVL(NULLIF(LTRIM(TO_CHAR(v.codi_ved), '0'), ''), '0')"
                ),
                extra_where="AND UPPER(NVL(v.nome_ved, '')) <> 'PADRAO'",
                ranking_value_key="devolucao",
                limit=None,
            )
            clients = await self._oracle_fetch_dimension_ranking(
                connection,
                binds,
                sales_view=oracle_sources["sales"],
                dimension_alias="cliente",
                dimension_sql="c.nome",
                join_sql=(
                    f"INNER JOIN {oracle_sources['client']} c "
                    "ON NVL(NULLIF(LTRIM(TO_CHAR(lm.codcliente_), '0'), ''), '0') "
                    "= NVL(NULLIF(LTRIM(TO_CHAR(c.codigo), '0'), ''), '0')"
                ),
                extra_where="AND UPPER(NVL(c.nome, '')) <> 'LAGES E LOPES LTDA'",
                ranking_value_key="faturamento_comercial",
                limit=50,
            )
            return self._json_safe(
                {
                    "status": "ok",
                    "oracle_sources": oracle_sources,
                    "faturamento_total": self._sales_total_payload(totals),
                    "faturamento_por_filial": [self._sales_total_payload(row, filial=row.get("filial")) for row in by_filial],
                    "ranking_vendedores": self._aggregate_dimension_rows(vendors, "vendedor", "faturamento_comercial"),
                    "ranking_vendedores_rb": self._aggregate_dimension_rows(vendors_rb, "vendedor", "saida_rb"),
                    "ranking_vendedores_devolucao": self._aggregate_dimension_rows(vendors_devolucao, "vendedor", "devolucao"),
                    "saida_rb": {
                        "valor": self._decimal(totals.get("saida_rb")),
                        "pedidos": int(totals.get("pedidos_saida_rb") or 0),
                        "por_filial": [
                            {
                                "filial": row.get("filial"),
                                "valor": self._decimal(row.get("saida_rb")),
                                "pedidos": int(row.get("pedidos_saida_rb") or 0),
                            }
                            for row in by_filial
                        ],
                    },
                    "devolucao": {
                        "valor": self._decimal(totals.get("devolucao")),
                        "pedidos": int(totals.get("pedidos_devolucao") or 0),
                        "por_filial": [
                            {
                                "filial": row.get("filial"),
                                "valor": self._decimal(row.get("devolucao")),
                                "pedidos": int(row.get("pedidos_devolucao") or 0),
                            }
                            for row in by_filial
                        ],
                    },
                    "ticket_medio": {
                        "valor": self._ticket(totals, gross=False),
                        "valor_bruto": self._ticket(totals, gross=True),
                        "pedidos_comerciais": int(totals.get("pedidos_comerciais") or 0),
                        "pedidos_total": int(totals.get("pedidos_total") or 0),
                        "por_filial": [
                            {
                                "filial": row.get("filial"),
                                "valor": self._ticket(row, gross=False),
                                "valor_bruto": self._ticket(row, gross=True),
                                "pedidos_comerciais": int(row.get("pedidos_comerciais") or 0),
                                "pedidos_total": int(row.get("pedidos_total") or 0),
                            }
                            for row in by_filial
                        ],
                    },
                    "top_clientes": self._aggregate_dimension_rows(clients, "cliente", "faturamento_comercial"),
                }
            )
        except Exception as exc:
            return {
                "status": "oracle_query_failed",
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            }

    def compare_period_reports(self, clone: dict[str, Any], erp: dict[str, Any] | None) -> dict[str, Any]:
        if not erp:
            return {"status": "oracle_unavailable", "checks": []}
        erp_status = erp.get("status")
        if erp_status != "ok":
            return {"status": str(erp_status or "oracle_unavailable"), "checks": []}

        checks: list[dict[str, Any]] = []
        self._add_value_check(checks, "faturamento_total", clone, erp, ("faturamento_total", "faturamento_comercial"))
        self._add_value_check(checks, "total_bruto", clone, erp, ("faturamento_total", "total_bruto"))
        self._add_value_check(checks, "saida_rb", clone, erp, ("saida_rb", "valor"))
        self._add_value_check(checks, "devolucao", clone, erp, ("devolucao", "valor"))
        self._add_value_check(checks, "ticket_medio", clone, erp, ("ticket_medio", "valor"))
        checks.extend(self._compare_by_filial(clone, erp, "faturamento_por_filial", "faturamento_comercial"))
        checks.extend(self._compare_by_filial(clone, erp, "faturamento_por_filial", "saida_rb"))
        checks.extend(self._compare_by_filial(clone, erp, "faturamento_por_filial", "devolucao"))
        checks.extend(self._compare_top_dimension(clone, erp, "ranking_vendedores", "vendedor"))
        checks.extend(self._compare_top_dimension(clone, erp, "ranking_vendedores_rb", "vendedor"))
        checks.extend(self._compare_top_dimension(clone, erp, "ranking_vendedores_devolucao", "vendedor"))
        checks.extend(self._compare_top_dimension(clone, erp, "top_clientes", "cliente"))
        failed = [check for check in checks if check["status"] != "ok"]
        return {
            "status": "mismatch" if failed else "ok",
            "tolerance": float(self.tolerance),
            "checks": checks,
            "failed_checks": failed,
        }

    def _sales_total_payload(self, row: dict[str, Any], filial: Any | None = None) -> dict[str, Any]:
        return {
            "filial": filial,
            "faturamento_comercial": self._decimal(row.get("faturamento_comercial")),
            "total_bruto": self._decimal(row.get("total_bruto")),
            "total_movimentos_view": self._decimal(row.get("total_movimentos_view")),
            "saida_rb": self._decimal(row.get("saida_rb")),
            "devolucao": self._decimal(row.get("devolucao")),
            "venda_bonificada": self._decimal(row.get("venda_bonificada")),
            "transferencias": self._decimal(row.get("transferencias")),
            "outras_vendas": self._decimal(row.get("outras_vendas")),
            "remessa_uso_consumo": self._decimal(row.get("remessa_uso_consumo")),
            "outros_movimentos": self._decimal(row.get("outros_movimentos")),
            "pedidos_comerciais": int(row.get("pedidos_comerciais") or 0),
            "pedidos_total": int(row.get("pedidos_total") or 0),
            "pedidos_movimentos_view": int(row.get("pedidos_movimentos_view") or 0),
            "pedidos_saida_rb": int(row.get("pedidos_saida_rb") or 0),
            "pedidos_devolucao": int(row.get("pedidos_devolucao") or 0),
        }

    def _aggregate_dimension_rows(self, rows: list[dict[str, Any]], dimension_key: str, ranking_value_key: str) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            name = str(row.get(dimension_key) or "").strip() or "Sem identificacao"
            item = grouped.setdefault(
                name,
                {
                    dimension_key: name,
                    "faturamento_comercial": Decimal("0"),
                    "saida_rb": Decimal("0"),
                    "devolucao": Decimal("0"),
                    "total_bruto": Decimal("0"),
                    "total_movimentos_view": Decimal("0"),
                    "pedidos_comerciais": 0,
                    "pedidos_total": 0,
                    "pedidos_movimentos_view": 0,
                    "por_filial": [],
                },
            )
            item["faturamento_comercial"] += self._decimal(row.get("faturamento_comercial"))
            item["saida_rb"] += self._decimal(row.get("saida_rb"))
            item["devolucao"] += self._decimal(row.get("devolucao"))
            item["total_bruto"] += self._decimal(row.get("total_bruto"))
            item["total_movimentos_view"] += self._decimal(row.get("total_movimentos_view"))
            item["pedidos_comerciais"] += int(row.get("pedidos_comerciais") or 0)
            item["pedidos_total"] += int(row.get("pedidos_total") or 0)
            item["pedidos_movimentos_view"] += int(row.get("pedidos_movimentos_view") or 0)
            item["por_filial"].append(
                {
                    "filial": row.get("filial"),
                    "faturamento_comercial": self._decimal(row.get("faturamento_comercial")),
                    "saida_rb": self._decimal(row.get("saida_rb")),
                    "devolucao": self._decimal(row.get("devolucao")),
                    "total_bruto": self._decimal(row.get("total_bruto")),
                    "total_movimentos_view": self._decimal(row.get("total_movimentos_view")),
                    "pedidos_comerciais": int(row.get("pedidos_comerciais") or 0),
                    "pedidos_total": int(row.get("pedidos_total") or 0),
                    "pedidos_movimentos_view": int(row.get("pedidos_movimentos_view") or 0),
                }
            )

        def sort_key(item: dict[str, Any]) -> tuple[Decimal, str]:
            return (self._decimal(item.get(ranking_value_key)), str(item.get(dimension_key) or ""))

        ranked = sorted(grouped.values(), key=sort_key, reverse=True)
        for index, item in enumerate(ranked, start=1):
            item["posicao"] = index
            item["valor_ranking"] = self._decimal(item.get(ranking_value_key))
        return ranked

    def _ticket(self, row: dict[str, Any], *, gross: bool) -> Decimal:
        if gross:
            total = self._decimal(row.get("total_bruto"))
            orders = int(row.get("pedidos_total") or 0)
        else:
            total = self._decimal(row.get("faturamento_comercial"))
            orders = int(row.get("pedidos_comerciais") or 0)
        return (total / Decimal(orders)).quantize(Decimal("0.01")) if orders else Decimal("0")

    def _decimal(self, value: Any) -> Decimal:
        try:
            return Decimal(str(value or 0)).quantize(Decimal("0.01"))
        except Exception:
            return Decimal("0.00")

    def _add_value_check(
        self,
        checks: list[dict[str, Any]],
        name: str,
        clone: dict[str, Any],
        erp: dict[str, Any],
        path: tuple[str, str],
    ) -> None:
        clone_value = self._decimal((clone.get(path[0]) or {}).get(path[1]))
        erp_value = self._decimal((erp.get(path[0]) or {}).get(path[1]))
        delta = (clone_value - erp_value).copy_abs()
        checks.append(
            {
                "name": name,
                "clone": clone_value,
                "erp": erp_value,
                "delta": delta,
                "status": "ok" if delta <= self.tolerance else "mismatch",
            }
        )

    def _compare_by_filial(
        self,
        clone: dict[str, Any],
        erp: dict[str, Any],
        report_key: str,
        metric_key: str,
    ) -> list[dict[str, Any]]:
        clone_rows = {str(row.get("filial")): row for row in clone.get(report_key, [])}
        erp_rows = {str(row.get("filial")): row for row in erp.get(report_key, [])}
        all_filiais = sorted(set(clone_rows) | set(erp_rows), key=self._filial_sort_key)
        checks = []
        for filial in all_filiais:
            clone_value = self._decimal((clone_rows.get(filial) or {}).get(metric_key))
            erp_value = self._decimal((erp_rows.get(filial) or {}).get(metric_key))
            delta = (clone_value - erp_value).copy_abs()
            checks.append(
                {
                    "name": f"{metric_key}_filial_{filial}",
                    "clone": clone_value,
                    "erp": erp_value,
                    "delta": delta,
                    "status": "ok" if delta <= self.tolerance else "mismatch",
                }
            )
        return checks

    def _compare_top_dimension(
        self,
        clone: dict[str, Any],
        erp: dict[str, Any],
        report_key: str,
        dimension_key: str,
    ) -> list[dict[str, Any]]:
        clone_rows = clone.get(report_key) or []
        erp_rows = erp.get(report_key) or []
        if not clone_rows and not erp_rows:
            return [{"name": f"{report_key}_top", "status": "ok", "clone": None, "erp": None, "delta": Decimal("0")}]
        clone_top = clone_rows[0] if clone_rows else {}
        erp_top = erp_rows[0] if erp_rows else {}
        clone_name = str(clone_top.get(dimension_key) or "")
        erp_name = str(erp_top.get(dimension_key) or "")
        clone_value = self._decimal(clone_top.get("valor_ranking"))
        erp_value = self._decimal(erp_top.get("valor_ranking"))
        delta = (clone_value - erp_value).copy_abs()
        status = "ok" if clone_name == erp_name and delta <= self.tolerance else "mismatch"
        return [
            {
                "name": f"{report_key}_top",
                "clone": {"name": clone_name, "value": clone_value},
                "erp": {"name": erp_name, "value": erp_value},
                "delta": delta,
                "status": status,
            }
        ]

    def _category_case_sql_oracle(self, alias: str = "lm") -> str:
        prefix = f"{alias}." if alias else ""
        description = f"UPPER(NVL({prefix}tpdescricao_, ''))"
        return f"""
            CASE
                WHEN NVL({prefix}tp_, 0) = 22
                  OR {description} LIKE '%BONIFIC%'
                    THEN 'venda_bonificada'
                WHEN NVL({prefix}tp_, 0) = 9
                  OR {description} LIKE '%SAIDA RB%'
                    THEN 'saida_rb'
                WHEN {description} LIKE '%DEVOL%'
                    THEN 'devolucao'
                WHEN NVL({prefix}tp_, 0) IN (3, 31, 96)
                  OR {description} LIKE '%TRANSFERENCIA%'
                    THEN 'transferencias'
                WHEN NVL({prefix}tp_, 0) IN (2, 61)
                    THEN 'faturamento_comercial'
                WHEN {description} LIKE 'VENDA%'
                    THEN 'outras_vendas'
                WHEN {description} LIKE '%REMESSA%'
                  OR {description} LIKE '%USO E CONSUMO%'
                    THEN 'remessa_uso_consumo'
                ELSE 'outros_movimentos'
            END
        """

    async def _resolve_oracle_sources(self, connection: Any) -> dict[str, str]:
        required = {
            "sales": "VW_VENDAS_LM",
            "seller": "VW_VENDEDOR_CAD_LM",
            "client": "VW_CLIENTES_CAD_LM",
        }
        rows = await self._oracle_fetch_mappings(
            connection,
            """
            SELECT owner, object_name
            FROM all_objects
            WHERE object_name IN ('VW_VENDAS_LM', 'VW_VENDEDOR_CAD_LM', 'VW_CLIENTES_CAD_LM')
              AND object_type IN ('TABLE', 'VIEW', 'SYNONYM')
            ORDER BY CASE WHEN owner = USER THEN 0 ELSE 1 END, owner
            """,
            {},
        )
        by_name: dict[str, str] = {}
        for row in rows:
            object_name = str(row.get("object_name") or "").upper()
            owner = str(row.get("owner") or "").upper()
            if object_name not in by_name and owner:
                by_name[object_name] = self._safe_oracle_identifier(f"{owner}.{object_name}")

        resolved: dict[str, str] = {}
        missing = []
        for key, object_name in required.items():
            identifier = by_name.get(object_name)
            if not identifier:
                missing.append(object_name)
            else:
                resolved[key] = identifier
        if missing:
            raise RuntimeError(f"Views Oracle nao encontradas para reconciliacao: {', '.join(missing)}")
        return resolved

    async def _oracle_fetch_totals(self, connection: Any, binds: dict[str, Any], *, sales_view: str) -> dict[str, Any]:
        category_case = self._category_case_sql_oracle("lm")
        rows = await self._oracle_fetch_mappings(
            connection,
            f"""
            WITH categorized AS (
                SELECT
                    {category_case} AS categoria,
                    NVL(lm.ptotal_, 0) AS valor,
                    lm.pedido_ AS pedido
                FROM {sales_view} lm
                WHERE lm.dtemissao_ >= TO_DATE(:start_date, 'YYYY-MM-DD')
                  AND lm.dtemissao_ < TO_DATE(:end_exclusive, 'YYYY-MM-DD')
            )
            SELECT categoria, SUM(valor) AS valor, COUNT(DISTINCT pedido) AS pedidos
            FROM categorized
            GROUP BY categoria
            """,
            binds,
        )
        totals = self._empty_totals()
        for row in rows:
            category = str(row.get("categoria") or "outros_movimentos").lower()
            if category not in sales_value_breakdown.CATEGORY_VALUE_KEYS:
                category = "outros_movimentos"
            totals[category] += self._decimal(row.get("valor"))
            totals[self._pedido_key_for_category(category)] = int(row.get("pedidos") or 0)
        total_orders = await self._oracle_fetch_mappings(
            connection,
            f"""
            WITH categorized AS (
                SELECT
                    {category_case} AS categoria,
                    lm.pedido_ AS pedido
                FROM {sales_view} lm
                WHERE lm.dtemissao_ >= TO_DATE(:start_date, 'YYYY-MM-DD')
                  AND lm.dtemissao_ < TO_DATE(:end_exclusive, 'YYYY-MM-DD')
            )
            SELECT
                COUNT(DISTINCT CASE WHEN categoria <> 'transferencias' THEN pedido END) AS pedidos_total,
                COUNT(DISTINCT pedido) AS pedidos_movimentos_view
            FROM categorized
            """,
            binds,
        )
        if total_orders:
            totals["pedidos_total"] = int(total_orders[0].get("pedidos_total") or 0)
            totals["pedidos_movimentos_view"] = int(total_orders[0].get("pedidos_movimentos_view") or 0)
        return sales_value_breakdown._finalize_totals(totals)

    async def _oracle_fetch_totals_by_filial(self, connection: Any, binds: dict[str, Any], *, sales_view: str) -> list[dict[str, Any]]:
        category_case = self._category_case_sql_oracle("lm")
        rows = await self._oracle_fetch_mappings(
            connection,
            f"""
            WITH categorized AS (
                SELECT
                    NVL(NULLIF(TRIM(TO_CHAR(lm.filial_)), ''), 'Sem filial') AS filial,
                    {category_case} AS categoria,
                    NVL(lm.ptotal_, 0) AS valor,
                    lm.pedido_ AS pedido
                FROM {sales_view} lm
                WHERE lm.dtemissao_ >= TO_DATE(:start_date, 'YYYY-MM-DD')
                  AND lm.dtemissao_ < TO_DATE(:end_exclusive, 'YYYY-MM-DD')
            )
            SELECT filial, categoria, SUM(valor) AS valor, COUNT(DISTINCT pedido) AS pedidos
            FROM categorized
            GROUP BY filial, categoria
            """,
            binds,
        )
        by_filial: dict[str, dict[str, Any]] = {}
        for row in rows:
            filial = str(row.get("filial") or "Sem filial")
            totals = by_filial.setdefault(filial, {"filial": filial, **self._empty_totals()})
            category = str(row.get("categoria") or "outros_movimentos").lower()
            if category not in sales_value_breakdown.CATEGORY_VALUE_KEYS:
                category = "outros_movimentos"
            totals[category] += self._decimal(row.get("valor"))
            totals[self._pedido_key_for_category(category)] = int(row.get("pedidos") or 0)

        total_orders = await self._oracle_fetch_mappings(
            connection,
            f"""
            WITH categorized AS (
                SELECT
                    NVL(NULLIF(TRIM(TO_CHAR(lm.filial_)), ''), 'Sem filial') AS filial,
                    {category_case} AS categoria,
                    lm.pedido_ AS pedido
                FROM {sales_view} lm
                WHERE lm.dtemissao_ >= TO_DATE(:start_date, 'YYYY-MM-DD')
                  AND lm.dtemissao_ < TO_DATE(:end_exclusive, 'YYYY-MM-DD')
            )
            SELECT
                filial,
                COUNT(DISTINCT CASE WHEN categoria <> 'transferencias' THEN pedido END) AS pedidos_total,
                COUNT(DISTINCT pedido) AS pedidos_movimentos_view
            FROM categorized
            GROUP BY filial
            """,
            binds,
        )
        for row in total_orders:
            filial = str(row.get("filial") or "Sem filial")
            totals = by_filial.setdefault(filial, {"filial": filial, **self._empty_totals()})
            totals["pedidos_total"] = int(row.get("pedidos_total") or 0)
            totals["pedidos_movimentos_view"] = int(row.get("pedidos_movimentos_view") or 0)

        output = []
        for row in by_filial.values():
            output.append(sales_value_breakdown._finalize_totals(row))
        return sorted(output, key=lambda item: self._filial_sort_key(str(item.get("filial") or "")))

    async def _oracle_fetch_dimension_ranking(
        self,
        connection: Any,
        binds: dict[str, Any],
        *,
        sales_view: str,
        dimension_alias: str,
        dimension_sql: str,
        join_sql: str,
        extra_where: str,
        ranking_value_key: str,
        limit: int | None,
    ) -> list[dict[str, Any]]:
        category_case = self._category_case_sql_oracle("lm")
        query_binds = dict(binds)
        query_binds["limit_rows"] = int(limit or 0)
        rows = await self._oracle_fetch_mappings(
            connection,
            f"""
            WITH categorized AS (
                SELECT
                    {dimension_sql} AS {dimension_alias},
                    NVL(NULLIF(TRIM(TO_CHAR(lm.filial_)), ''), 'Sem filial') AS filial,
                    {category_case} AS categoria,
                    NVL(lm.ptotal_, 0) AS valor,
                    lm.pedido_ AS pedido
                FROM {sales_view} lm
                {join_sql}
                WHERE lm.dtemissao_ >= TO_DATE(:start_date, 'YYYY-MM-DD')
                  AND lm.dtemissao_ < TO_DATE(:end_exclusive, 'YYYY-MM-DD')
                  {extra_where}
            ),
            by_dimension AS (
                SELECT
                    {dimension_alias},
                    SUM(CASE WHEN categoria = 'faturamento_comercial' THEN valor ELSE 0 END) AS ranking_faturamento_comercial,
                    SUM(CASE WHEN categoria = 'saida_rb' THEN valor ELSE 0 END) AS ranking_saida_rb,
                    SUM(CASE WHEN categoria = 'devolucao' THEN valor ELSE 0 END) AS ranking_devolucao,
                    SUM(CASE WHEN categoria <> 'transferencias' THEN valor ELSE 0 END) AS ranking_total_bruto,
                    SUM(valor) AS ranking_total_movimentos_view
                FROM categorized
                GROUP BY {dimension_alias}
            ),
            ranked AS (
                SELECT
                    {dimension_alias},
                    ROW_NUMBER() OVER (ORDER BY ranking_{ranking_value_key} DESC, {dimension_alias} ASC) AS rn
                FROM by_dimension
                WHERE ranking_{ranking_value_key} <> 0
            ),
            limited AS (
                SELECT {dimension_alias}
                FROM ranked
                WHERE :limit_rows = 0 OR rn <= :limit_rows
            )
            SELECT
                c.{dimension_alias},
                c.filial,
                SUM(CASE WHEN c.categoria = 'faturamento_comercial' THEN c.valor ELSE 0 END) AS faturamento_comercial,
                SUM(CASE WHEN c.categoria = 'saida_rb' THEN c.valor ELSE 0 END) AS saida_rb,
                SUM(CASE WHEN c.categoria = 'devolucao' THEN c.valor ELSE 0 END) AS devolucao,
                SUM(CASE WHEN c.categoria = 'venda_bonificada' THEN c.valor ELSE 0 END) AS venda_bonificada,
                SUM(CASE WHEN c.categoria = 'transferencias' THEN c.valor ELSE 0 END) AS transferencias,
                SUM(CASE WHEN c.categoria = 'outras_vendas' THEN c.valor ELSE 0 END) AS outras_vendas,
                SUM(CASE WHEN c.categoria = 'remessa_uso_consumo' THEN c.valor ELSE 0 END) AS remessa_uso_consumo,
                SUM(CASE WHEN c.categoria = 'outros_movimentos' THEN c.valor ELSE 0 END) AS outros_movimentos,
                SUM(CASE WHEN c.categoria <> 'transferencias' THEN c.valor ELSE 0 END) AS total_bruto,
                SUM(c.valor) AS total_movimentos_view,
                COUNT(DISTINCT CASE WHEN c.categoria = 'faturamento_comercial' THEN c.pedido END) AS pedidos_comerciais,
                COUNT(DISTINCT CASE WHEN c.categoria = 'saida_rb' THEN c.pedido END) AS pedidos_saida_rb,
                COUNT(DISTINCT CASE WHEN c.categoria = 'devolucao' THEN c.pedido END) AS pedidos_devolucao,
                COUNT(DISTINCT CASE WHEN c.categoria = 'venda_bonificada' THEN c.pedido END) AS pedidos_bonificados,
                COUNT(DISTINCT CASE WHEN c.categoria = 'transferencias' THEN c.pedido END) AS pedidos_transferencias,
                COUNT(DISTINCT CASE WHEN c.categoria = 'outras_vendas' THEN c.pedido END) AS pedidos_outras_vendas,
                COUNT(DISTINCT CASE WHEN c.categoria = 'remessa_uso_consumo' THEN c.pedido END) AS pedidos_remessa_uso_consumo,
                COUNT(DISTINCT CASE WHEN c.categoria = 'outros_movimentos' THEN c.pedido END) AS pedidos_outros,
                COUNT(DISTINCT CASE WHEN c.categoria <> 'transferencias' THEN c.pedido END) AS pedidos_total,
                COUNT(DISTINCT c.pedido) AS pedidos_movimentos_view
            FROM categorized c
            INNER JOIN limited l ON l.{dimension_alias} = c.{dimension_alias}
            GROUP BY c.{dimension_alias}, c.filial
            """,
            query_binds,
        )
        return rows

    async def _oracle_fetch_mappings(self, connection: Any, sql: str, binds: dict[str, Any]) -> list[dict[str, Any]]:
        cursor = connection.cursor()
        try:
            await cursor.execute(sql, binds)
            raw_rows = await cursor.fetchall()
            columns = [str(description[0]).lower() for description in cursor.description]
            return [dict(zip(columns, row)) for row in raw_rows]
        finally:
            close_result = cursor.close()
            if inspect.isawaitable(close_result):
                await close_result

    def _empty_totals(self) -> dict[str, Any]:
        totals = {key: Decimal("0") for key in sales_value_breakdown.CATEGORY_VALUE_KEYS}
        totals.update(
            {
                "total_bruto": Decimal("0"),
                "total_movimentos_view": Decimal("0"),
                "saida_rb_devolucao": Decimal("0"),
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
            }
        )
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

    def _filial_sort_key(self, value: Any) -> tuple[int, str]:
        filial = str(value or "")
        try:
            return int(filial), filial
        except ValueError:
            return 999999, filial

    def _safe_oracle_identifier(self, value: str) -> str:
        raw = str(value or "").strip().upper()
        parts = raw.split(".")
        if len(parts) not in (1, 2):
            raise ValueError(f"Identificador Oracle invalido: {value!r}")
        for part in parts:
            if not part or not all(char.isalnum() or char in "_$#" for char in part):
                raise ValueError(f"Identificador Oracle invalido: {value!r}")
        return ".".join(parts)

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, dict):
            return {key: self._json_safe(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._json_safe(item) for item in value]
        return value


erp_reconciliation = ERPReconciliationService()
