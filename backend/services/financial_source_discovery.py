from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import re
import unicodedata

from sqlalchemy import text


DISCOVERY_VERSION = "2026-07-20.financial-source-discovery"


@dataclass(frozen=True)
class ColumnProfile:
    name: str
    data_type: str


@dataclass(frozen=True)
class SourceProfile:
    schema: str
    name: str
    table_type: str
    columns: tuple[ColumnProfile, ...]
    row_count: int | None = None

    @property
    def full_name(self) -> str:
        return f"{self.schema}.{self.name}"


@dataclass
class SourceAssessment:
    source: str
    metric_family: str
    status: str
    score: int
    capabilities: dict[str, bool]
    matched_columns: dict[str, list[str]]
    missing_requirements: list[str]
    notes: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


class FinancialSourceDiscoveryService:
    """Discovers trustworthy sources for profit and unbilled-sales metrics.

    The service is intentionally conservative: it marks a source as ready only
    when the columns needed to filter, group and calculate the metric are visible.
    """

    SOURCE_NAME_KEYWORDS = (
        "lucro",
        "marg",
        "custo",
        "cmv",
        "impost",
        "desp",
        "pedido",
        "pend",
        "fatur",
        "venda",
        "financeiro",
        "nota",
        "nfe",
        "nf",
        "titulo",
        "carteira",
        "orcamento",
    )
    SYSTEM_SOURCE_PREFIXES = (
        "business_",
        "metadata_",
        "semantic_",
        "dashboard_",
        "package_",
        "svr_",
        "sync_",
        "users",
        "tenants",
        "favorites",
        "search_history",
        "blueprint_repository",
        "data_platform_history",
    )
    REVENUE_TERMS = ("receita", "fatur", "venda_valor", "ptotal", "valor_total", "total_venda")
    VALUE_TERMS = ("valor", "total", "ptotal", "venda_valor", "receita", "fatur")
    COST_TERMS = ("custo", "cust", "cmv", "pcusto", "preco_custo")
    PROFIT_TERMS = ("lucro", "margem", "resultado")
    NET_PROFIT_TERMS = ("lucro_liquido", "resultado_liquido", "margem_liquida")
    GROSS_PROFIT_TERMS = ("lucro_bruto", "margem_bruta")
    TAX_TERMS = ("imposto", "icms", "pis", "cofins", "iss", "ipi", "tribut")
    EXPENSE_TERMS = ("despesa", "frete", "comissao", "encargo")
    DATE_TERMS = ("data", "dt", "emissao", "vencimento", "referencia", "periodo")
    BRANCH_TERMS = ("filial", "loja", "unidade")
    SELLER_TERMS = ("vendedor", "rca", "representante")
    CUSTOMER_TERMS = ("cliente", "comprador", "codcliente", "razao")
    ORDER_TERMS = ("pedido", "orcamento", "carteira")
    STATUS_TERMS = ("status", "situacao", "sit_")
    BILLING_TERMS = ("faturado", "faturamento", "nota", "nfe", "nf", "numero_nfe")
    CANCELLATION_TERMS = ("cancel", "cancelado")

    def normalize_token(self, value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", str(value or ""))
        ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
        return ascii_text.lower().strip()

    def _column_names(self, source: SourceProfile) -> list[str]:
        return [column.name for column in source.columns]

    def _matches(self, names: list[str], terms: tuple[str, ...]) -> list[str]:
        matched: list[str] = []
        normalized_terms = tuple(self.normalize_token(term) for term in terms)
        for name in names:
            normalized_name = self.normalize_token(name)
            if any(term in normalized_name for term in normalized_terms):
                matched.append(name)
        return matched

    def _source_looks_business_relevant(self, source: SourceProfile) -> bool:
        name = self.normalize_token(source.name)
        if any(name.startswith(prefix) for prefix in self.SYSTEM_SOURCE_PREFIXES):
            return False
        return any(keyword in name for keyword in self.SOURCE_NAME_KEYWORDS)

    async def load_postgres_sources(
        self,
        session: Any,
        *,
        include_row_counts: bool = False,
    ) -> list[SourceProfile]:
        result = await session.execute(
            text(
                """
                SELECT table_schema, table_name, table_type
                FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY table_schema, table_name
                """
            )
        )
        raw_sources = [dict(row._mapping) for row in result.fetchall()]
        sources: list[SourceProfile] = []

        for raw in raw_sources:
            source_name = str(raw["table_name"])
            source = SourceProfile(
                schema=str(raw["table_schema"]),
                name=source_name,
                table_type=str(raw["table_type"]),
                columns=(),
            )
            if not self._source_looks_business_relevant(source):
                continue

            columns_result = await session.execute(
                text(
                    """
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = :schema
                      AND table_name = :table_name
                    ORDER BY ordinal_position
                    """
                ),
                {"schema": source.schema, "table_name": source.name},
            )
            columns = tuple(
                ColumnProfile(name=str(row[0]), data_type=str(row[1]))
                for row in columns_result.fetchall()
            )
            row_count = None
            if include_row_counts and self._is_safe_pg_identifier(source.schema) and self._is_safe_pg_identifier(source.name):
                try:
                    count_result = await session.execute(text(f'SELECT COUNT(*) FROM "{source.schema}"."{source.name}"'))
                    row_count = int(count_result.scalar() or 0)
                except Exception:
                    row_count = None

            sources.append(
                SourceProfile(
                    schema=source.schema,
                    name=source.name,
                    table_type=source.table_type,
                    columns=columns,
                    row_count=row_count,
                )
            )
        return sources

    def assess_profit_source(self, source: SourceProfile) -> SourceAssessment:
        names = self._column_names(source)
        matched = {
            "revenue": self._matches(names, self.REVENUE_TERMS),
            "cost": self._matches(names, self.COST_TERMS),
            "profit": self._matches(names, self.PROFIT_TERMS),
            "gross_profit": self._matches(names, self.GROSS_PROFIT_TERMS),
            "net_profit": self._matches(names, self.NET_PROFIT_TERMS),
            "tax": self._matches(names, self.TAX_TERMS),
            "expense": self._matches(names, self.EXPENSE_TERMS),
            "date": self._matches(names, self.DATE_TERMS),
            "branch": self._matches(names, self.BRANCH_TERMS),
            "seller": self._matches(names, self.SELLER_TERMS),
            "customer": self._matches(names, self.CUSTOMER_TERMS),
        }
        has_explicit_gross = bool(matched["gross_profit"])
        has_explicit_net = bool(matched["net_profit"])
        has_revenue_cost = bool(matched["revenue"] and matched["cost"])
        gross_ready = has_explicit_gross or has_revenue_cost
        net_ready = has_explicit_net or (has_revenue_cost and bool(matched["tax"] or matched["expense"]))

        missing: list[str] = []
        if not gross_ready:
            missing.append("lucro bruto: coluna explicita de lucro/margem bruta ou receita + custo/CMV")
        if not net_ready:
            missing.append("lucro liquido: coluna explicita de lucro liquido ou receita + custo + impostos/despesas")
        if not matched["date"]:
            missing.append("coluna de data/periodo para filtro mensal")

        score = 0
        score += 40 if has_explicit_gross or has_explicit_net else 0
        score += 25 if has_revenue_cost else 0
        score += 10 if matched["tax"] else 0
        score += 10 if matched["expense"] else 0
        score += 5 if matched["date"] else 0
        score += 5 if matched["branch"] else 0
        score += 5 if matched["seller"] or matched["customer"] else 0

        if gross_ready and net_ready and matched["date"]:
            status = "ready"
        elif score > 0:
            status = "partial"
        else:
            status = "missing"

        notes = []
        if source.name == "vw_vendas_lm":
            notes.append("A view de vendas faturadas nao possui custo, impostos, despesas ou margem no clone atual.")

        return SourceAssessment(
            source=source.full_name,
            metric_family="profit",
            status=status,
            score=score,
            capabilities={
                "lucro_bruto": gross_ready and bool(matched["date"]),
                "lucro_liquido": net_ready and bool(matched["date"]),
                "filial": bool(matched["branch"]),
                "vendedor": bool(matched["seller"]),
                "cliente": bool(matched["customer"]),
            },
            matched_columns={key: value for key, value in matched.items() if value},
            missing_requirements=missing,
            notes=notes,
        )

    def assess_unbilled_sales_source(self, source: SourceProfile) -> SourceAssessment:
        names = self._column_names(source)
        normalized_source_name = self.normalize_token(source.name)
        matched = {
            "order": self._matches(names, self.ORDER_TERMS),
            "status": self._matches(names, self.STATUS_TERMS),
            "billing": self._matches(names, self.BILLING_TERMS),
            "value": self._matches(names, self.VALUE_TERMS),
            "date": self._matches(names, self.DATE_TERMS),
            "branch": self._matches(names, self.BRANCH_TERMS),
            "seller": self._matches(names, self.SELLER_TERMS),
            "customer": self._matches(names, self.CUSTOMER_TERMS),
            "cancellation": self._matches(names, self.CANCELLATION_TERMS),
        }
        source_is_order_context = any(term in normalized_source_name for term in ("pedido", "orcamento", "carteira", "pend"))
        payment_status_only = bool(matched["status"]) and all("pagamento" in self.normalize_token(col) for col in matched["status"])

        ready = (
            source_is_order_context
            and bool(matched["order"])
            and bool(matched["status"])
            and bool(matched["value"])
            and bool(matched["date"])
            and not payment_status_only
        )
        missing: list[str] = []
        if not source_is_order_context:
            missing.append("fonte de contexto de pedido/carteira/orcamento pendente")
        if not matched["order"]:
            missing.append("numero/id do pedido")
        if not matched["status"] or payment_status_only:
            missing.append("status operacional do pedido/faturamento, nao apenas status de pagamento")
        if not matched["value"]:
            missing.append("valor do pedido ainda nao faturado")
        if not matched["date"]:
            missing.append("data do pedido/emissao para filtro mensal")

        score = 0
        score += 25 if source_is_order_context else 0
        score += 20 if matched["order"] else 0
        score += 20 if matched["status"] and not payment_status_only else 0
        score += 15 if matched["value"] else 0
        score += 10 if matched["date"] else 0
        score += 5 if matched["branch"] else 0
        score += 5 if matched["seller"] or matched["customer"] else 0

        if ready:
            status = "ready"
        elif score > 0:
            status = "partial"
        else:
            status = "missing"

        notes = []
        if source.name == "vw_vendas_lm":
            notes.append("Contem pedidos/notas ja emitidos; falta status de pendencia para separar nao faturadas.")
        if payment_status_only:
            notes.append("Status financeiro de pagamento nao substitui status operacional de faturamento do pedido.")

        return SourceAssessment(
            source=source.full_name,
            metric_family="unbilled_sales",
            status=status,
            score=score,
            capabilities={
                "vendas_nao_faturadas": ready,
                "filial": bool(matched["branch"]),
                "vendedor": bool(matched["seller"]),
                "cliente": bool(matched["customer"]),
                "cancelados": bool(matched["cancellation"]),
            },
            matched_columns={key: value for key, value in matched.items() if value},
            missing_requirements=missing,
            notes=notes,
        )

    async def discover_postgres(
        self,
        session: Any,
        *,
        include_row_counts: bool = False,
    ) -> dict[str, Any]:
        sources = await self.load_postgres_sources(session, include_row_counts=include_row_counts)
        profit_assessments = [self.assess_profit_source(source) for source in sources]
        unbilled_assessments = [self.assess_unbilled_sales_source(source) for source in sources]

        profit_payloads = sorted(
            (assessment.to_payload() for assessment in profit_assessments if assessment.score > 0),
            key=lambda item: (-int(item["score"]), str(item["source"])),
        )
        unbilled_payloads = sorted(
            (assessment.to_payload() for assessment in unbilled_assessments if assessment.score > 0),
            key=lambda item: (-int(item["score"]), str(item["source"])),
        )

        return {
            "version": DISCOVERY_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_count": len(sources),
            "sources": [
                {
                    "schema": source.schema,
                    "name": source.name,
                    "table_type": source.table_type,
                    "row_count": source.row_count,
                    "columns": [asdict(column) for column in source.columns],
                }
                for source in sources
            ],
            "profit": {
                "lucro_bruto": self._metric_status(profit_payloads, "lucro_bruto"),
                "lucro_liquido": self._metric_status(profit_payloads, "lucro_liquido"),
                "candidates": profit_payloads[:20],
            },
            "unbilled_sales": {
                "vendas_nao_faturadas": self._metric_status(unbilled_payloads, "vendas_nao_faturadas"),
                "candidates": unbilled_payloads[:20],
            },
            "required_contracts": {
                "lucro_bruto": [
                    "receita/faturamento",
                    "custo ou CMV",
                    "data de competencia/emissao",
                    "filial e dimensoes opcionais de vendedor/cliente/produto",
                ],
                "lucro_liquido": [
                    "receita/faturamento",
                    "custo ou CMV",
                    "impostos e despesas ou coluna explicita de lucro liquido",
                    "data de competencia/emissao",
                ],
                "vendas_nao_faturadas": [
                    "pedido/orcamento/carteira",
                    "status operacional de faturamento",
                    "valor do pedido",
                    "data do pedido",
                    "filial, vendedor e cliente quando existirem",
                    "flag/status de cancelamento quando existir",
                ],
            },
        }

    def _metric_status(self, candidates: list[dict[str, Any]], capability: str) -> dict[str, Any]:
        ready = [candidate for candidate in candidates if candidate.get("capabilities", {}).get(capability)]
        partial = [candidate for candidate in candidates if candidate.get("status") == "partial"]
        if ready:
            return {
                "status": "ready_for_formula_mapping",
                "active_mapping": False,
                "best_source": ready[0]["source"],
                "reason": "Fonte candidata possui as colunas minimas; ainda requer homologacao da formula de negocio antes de responder ao usuario.",
            }
        if partial:
            return {
                "status": "partial",
                "active_mapping": False,
                "best_source": partial[0]["source"],
                "reason": "Ha fonte candidata, mas faltam colunas obrigatorias para calculo confiavel.",
            }
        return {
            "status": "missing",
            "active_mapping": False,
            "best_source": None,
            "reason": "Nenhuma fonte com contrato minimo foi encontrada no clone atual.",
        }

    def source_warning(self, discovery: dict[str, Any] | None, metric_key: str) -> str:
        if not discovery:
            if metric_key == "vendas_nao_faturadas":
                return "Nao foi possivel auditar a fonte de vendas nao faturadas neste momento."
            return "Nao foi possivel auditar a fonte de lucro neste momento."

        if metric_key == "vendas_nao_faturadas":
            status = discovery.get("unbilled_sales", {}).get("vendas_nao_faturadas", {})
            reason = status.get("reason") or "Fonte nao homologada."
            return (
                "Vendas ainda nao faturadas continuam sem fonte ativa homologada. "
                f"Status da descoberta: {status.get('status', 'unknown')}. {reason}"
            )

        gross = discovery.get("profit", {}).get("lucro_bruto", {})
        net = discovery.get("profit", {}).get("lucro_liquido", {})
        return (
            "Lucro bruto/liquido continua sem fonte ativa homologada. "
            f"Lucro bruto: {gross.get('status', 'unknown')}; lucro liquido: {net.get('status', 'unknown')}. "
            "O sistema nao calcula lucro sem custo, impostos/despesas e formula validada."
        )

    def load_latest_report(self, reports_dir: str | Path = "reports") -> dict[str, Any] | None:
        base = Path(reports_dir)
        matches = sorted(base.glob("financial_source_discovery_*.json"))
        if not matches:
            return None
        try:
            return json.loads(matches[-1].read_text(encoding="utf-8"))
        except Exception:
            return None

    def _is_safe_pg_identifier(self, value: str) -> bool:
        return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(value or "")))


financial_source_discovery = FinancialSourceDiscoveryService()
