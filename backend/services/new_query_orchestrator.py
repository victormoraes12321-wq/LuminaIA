import uuid
import time
import logging
import calendar
import re
import unicodedata
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import date, datetime, timezone
from openai import AsyncOpenAI

from models.new_pipeline_contracts import (
    SemanticPlan, CanonicalPlan, ExecutionPlan, ExecutionResult, QueryContext,
    DashboardState, ConversationNode, ConversationGraph, ExecutionStatus,
    IntentType, VisualizationType, ComparisonOperator, EmptyDatasetPolicy,
    SemanticFilter
)
from services.metadata_catalog import (
    SemanticCanonicalizer, MetadataResolver, QueryOptimizer, SQLGenerator, SecurityValidator
)
from services.security_and_normalization_engine import EmptyDatasetAnomalyError
from services.ai_credential_manager import ai_credential_manager
from database import get_db_context
from sqlalchemy import select, text

logger = logging.getLogger("luminaai.services.new_query_orchestrator")

# ── A) Contrato Estruturado de Explicação da IA ─────────────────────

class ExecutiveExplanation(BaseModel):
    summary: str = Field(..., description="Resumo executivo em linguagem de negócios simples dos resultados.")
    insights: List[str] = Field(default_factory=list, description="Lista de insights analíticos identificados nos dados.")
    recommendations: List[str] = Field(default_factory=list, description="Recomendações comerciais acionáveis com base nos dados.")
    warnings: List[str] = Field(default_factory=list, description="Alertas ou limitações identificadas na análise.")

# ── B) Orquestrador Unificado do Novo Pipeline ──────────────────────

class NewQueryOrchestrator:
    """
    Orquestrador central unificado do novo pipeline cognitivo (Decoupled NLU-SQL) do LuminaAI.
    """
    def __init__(self, provider: Optional[Any] = None):
        self.resolver = SemanticCanonicalizer()
        self.planner = MetadataResolver()
        self.optimizer = QueryOptimizer()
        self.generator = SQLGenerator()
        self.validator = SecurityValidator()

    def _format_brl(self, value: Any) -> str:
        try:
            amount = Decimal(str(value or 0)).quantize(Decimal("0.01"))
        except Exception:
            amount = Decimal("0.00")
        raw = f"{amount:,.2f}"
        return "R$ " + raw.replace(",", "X").replace(".", ",").replace("X", ".")

    def _core_summary_topics(self, pergunta: str) -> set[str]:
        normalized = self._normalize_query_text(pergunta)
        topics: set[str] = set()

        if any(term in normalized for term in (
            "faturamento",
            "fatiramento",
            "faturament",
            "receita",
            "quanto vendeu",
            "qto vendeu",
            "qt vendeu",
            "total vendeu",
            "vendeu no total",
            "venda total",
            "vendas totais",
            "vendas total",
            "vendas do mes",
            "vendas no mes",
        )):
            topics.add("faturamento")
        if any(term in normalized for term in ("ticket", "tiket", "tiquete", "valor medio")):
            topics.add("ticket")
        if any(term in normalized for term in ("desconto", "descontos")):
            topics.add("desconto")
        has_vendor_term = any(term in normalized for term in ("vendedor", "vendendor", "vendedores", "vendedora"))
        if has_vendor_term and any(term in normalized for term in (
            "mais vendeu",
            "maior venda",
            "vendeu mais",
            "lider",
            "campeao",
            "melhor vendedor",
            "quem vendeu mais",
            "ranking",
            "top",
        )):
            topics.add("top_vendedor")
        if "cliente" in normalized and any(term in normalized for term in ("mais comprou", "mais compraram", "top", "ranking", "maior cliente", "maior compra")):
            topics.add("top_cliente")

        return topics

    def _is_core_summary_query(self, pergunta: str) -> bool:
        topics = self._core_summary_topics(pergunta)
        if not topics or self._month_range_from_text(pergunta) is None:
            return False
        if len(topics) >= 2:
            return True

        normalized = self._normalize_query_text(pergunta)
        single_topic = next(iter(topics))
        if single_topic in {"faturamento", "ticket", "desconto", "top_vendedor"}:
            return True
        if single_topic == "top_cliente":
            return "ranking" not in normalized
        return False

    def _question_with_inherited_period(self, pergunta: str, history: Optional[List[Dict[str, str]]]) -> str:
        if self._month_range_from_text(pergunta) is not None:
            return pergunta
        if not self._core_summary_topics(pergunta):
            return pergunta

        for message in reversed(history or []):
            content = str((message or {}).get("content") or "")
            period = self._month_range_from_text(content)
            if not period:
                continue
            start_raw, end_raw = period
            try:
                start_date = date.fromisoformat(start_raw)
                end_date = date.fromisoformat(end_raw)
            except ValueError:
                continue

            if start_date == end_date:
                inherited = start_date.strftime("%d/%m/%Y")
            else:
                inherited = start_date.strftime("%m/%Y")
            return f"{pergunta} em {inherited}"

        return pergunta

    async def _execute_core_summary_query(
        self,
        pergunta: str,
        tenant_id: str,
        session_key: str,
        trace_id: uuid.UUID,
        start_time: float,
        debug_data: Dict[str, Any],
        conversation_graph_manager: Any,
    ) -> Dict[str, Any]:
        start_date_raw, end_date_raw = self._month_range_from_text(pergunta) or ("", "")
        start_date = date.fromisoformat(start_date_raw)
        end_date = date.fromisoformat(end_date_raw)
        topics = self._core_summary_topics(pergunta)

        summary_rows: List[Dict[str, Any]] = []
        binds = {"start_date": start_date, "end_date": end_date}

        async with get_db_context() as session:
            totals_result = await session.execute(
                text(
                    """
                    SELECT
                        COALESCE(SUM(ptotal_), 0) AS faturamento_total,
                        COUNT(DISTINCT pedido_) AS pedidos,
                        COALESCE(SUM(GREATEST(ROUND(((qtde_ * p_unit_) - ptotal_)::numeric, 2), 0::numeric)), 0) AS desconto_total
                    FROM vw_vendas_lm
                    WHERE dtemissao_ BETWEEN :start_date AND :end_date
                    """
                ),
                binds,
            )
            totals = dict(totals_result.mappings().first() or {})
            faturamento_total = Decimal(str(totals.get("faturamento_total") or 0))
            pedidos = int(totals.get("pedidos") or 0)
            desconto_total = Decimal(str(totals.get("desconto_total") or 0))
            ticket_medio = faturamento_total / Decimal(pedidos) if pedidos else Decimal("0")
            desconto_medio = desconto_total / Decimal(pedidos) if pedidos else Decimal("0")

            top_vendor = None
            if "top_vendedor" in topics:
                vendor_result = await session.execute(
                    text(
                        """
                        SELECT v.nome_ved AS vendedor, COALESCE(SUM(lm.ptotal_), 0) AS valor_total
                        FROM vw_vendas_lm lm
                        INNER JOIN vw_vendedor_cad_lm v
                          ON coalesce(nullif(ltrim(lm.rca_::text, '0'), ''), '0')
                           = coalesce(nullif(ltrim(v.codi_ved::text, '0'), ''), '0')
                        WHERE lm.dtemissao_ BETWEEN :start_date AND :end_date
                          AND UPPER(COALESCE(v.nome_ved, '')) <> 'PADRAO'
                        GROUP BY v.nome_ved
                        ORDER BY valor_total DESC
                        LIMIT 1
                        """
                    ),
                    binds,
                )
                top_vendor = dict(vendor_result.mappings().first() or {})

            top_client = None
            if "top_cliente" in topics:
                client_result = await session.execute(
                    text(
                        """
                        SELECT c.nome AS cliente, COALESCE(SUM(lm.ptotal_), 0) AS valor_total
                        FROM vw_vendas_lm lm
                        INNER JOIN vw_clientes_cad_lm c
                          ON coalesce(nullif(ltrim(lm.codcliente_::text, '0'), ''), '0')
                           = coalesce(nullif(ltrim(c.codigo::text, '0'), ''), '0')
                        WHERE lm.dtemissao_ BETWEEN :start_date AND :end_date
                          AND UPPER(COALESCE(c.nome, '')) <> 'LAGES E LOPES LTDA'
                        GROUP BY c.nome
                        ORDER BY valor_total DESC
                        LIMIT 1
                        """
                    ),
                    binds,
                )
                top_client = dict(client_result.mappings().first() or {})

        if "faturamento" in topics:
            summary_rows.append({
                "indicador": "Faturamento total",
                "valor": float(faturamento_total),
                "valor_formatado": self._format_brl(faturamento_total),
                "observacao": "Total de vendas no período informado.",
            })
        if "ticket" in topics:
            summary_rows.append({
                "indicador": "Ticket médio",
                "valor": float(ticket_medio),
                "valor_formatado": self._format_brl(ticket_medio),
                "observacao": f"Calculado por {pedidos} pedidos distintos.",
            })
        if "desconto" in topics:
            summary_rows.append({
                "indicador": "Desconto total",
                "valor": float(desconto_total),
                "valor_formatado": self._format_brl(desconto_total),
                "observacao": "Derivado de quantidade vezes preço unitário menos valor faturado.",
            })
            summary_rows.append({
                "indicador": "Desconto médio",
                "valor": float(desconto_medio),
                "valor_formatado": self._format_brl(desconto_medio),
                "observacao": f"Calculado por {pedidos} pedidos distintos.",
            })
        if top_vendor:
            summary_rows.append({
                "indicador": "Vendedor com maior venda",
                "valor": float(top_vendor.get("valor_total") or 0),
                "valor_formatado": self._format_brl(top_vendor.get("valor_total") or 0),
                "observacao": str(top_vendor.get("vendedor") or "Não identificado"),
            })
        if top_client:
            summary_rows.append({
                "indicador": "Cliente com maior compra",
                "valor": float(top_client.get("valor_total") or 0),
                "valor_formatado": self._format_brl(top_client.get("valor_total") or 0),
                "observacao": str(top_client.get("cliente") or "Não identificado"),
            })

        period_label = f"{start_date.isoformat()} a {end_date.isoformat()}"
        parts = []
        if "faturamento" in topics:
            parts.append(f"faturamento total de {self._format_brl(faturamento_total)}")
        if "ticket" in topics:
            parts.append(f"ticket médio de {self._format_brl(ticket_medio)}")
        if "desconto" in topics:
            parts.append(f"desconto total de {self._format_brl(desconto_total)} e desconto médio de {self._format_brl(desconto_medio)}")
        if top_vendor:
            parts.append(f"vendedor com maior venda: {top_vendor.get('vendedor')} ({self._format_brl(top_vendor.get('valor_total') or 0)})")
        if top_client:
            parts.append(f"cliente com maior compra: {top_client.get('cliente')} ({self._format_brl(top_client.get('valor_total') or 0)})")
        response_text = f"Resumo do período {period_label}: " + "; ".join(parts) + "."
        if "top_vendedor" in topics:
            response_text += " O cadastro técnico PADRAO foi desconsiderado apenas no ranking de vendedores."
        if "top_cliente" in topics:
            response_text += " O cliente interno LAGES E LOPES LTDA foi desconsiderado apenas no ranking de clientes."

        from models.view_catalog import ChartType as SchemaChartType
        from services.data_transformer import transform_data

        chart_data = transform_data(summary_rows, SchemaChartType.TABLE)
        if isinstance(chart_data, dict):
            chart_data["resumo"] = {
                "periodo": period_label,
                "faturamento_total": float(faturamento_total),
                "ticket_medio": float(ticket_medio),
                "desconto_total": float(desconto_total),
                "total_indicadores": len(summary_rows),
            }
        elapsed = (time.perf_counter() - start_time) * 1000

        canonical_plan = CanonicalPlan(
            trace_id=trace_id,
            status=ExecutionStatus.READY,
            intent=IntentType.AGGREGATION,
            goal=pergunta,
            entities=["Venda"],
            metrics=sorted(topics),
            dimensions=["Venda.dtemissao_"],
            suggested_visualization=VisualizationType.TABLE,
        )
        db_state = DashboardState(
            chart_type=VisualizationType.TABLE,
            selected_filters={"tenant_id": tenant_id, "periodo": period_label},
        )
        exec_res = ExecutionResult(
            status=ExecutionStatus.READY,
            dataset=summary_rows,
            metadata={"rule": "core_summary_query", "binds": binds},
            execution_time_ms=elapsed,
            row_count=len(summary_rows),
        )
        query_context = QueryContext(
            dataset_id=f"node_{trace_id.hex[:8]}",
            row_count=len(summary_rows),
            execution_time_ms=elapsed,
        )
        conv_node = ConversationNode(
            node_id=f"node_{uuid.uuid4().hex[:8]}",
            user_query=pergunta,
            canonical_plan=canonical_plan,
            execution_result=exec_res,
            query_context=query_context,
            dashboard_state=db_state,
        )
        conversation_graph_manager.add_node(session_key, conv_node)

        debug_data["semantic_plan"] = canonical_plan.model_dump()
        debug_data["canonical_plan"] = canonical_plan.model_dump()
        debug_data["sql"]["raw_sql"] = "CORE_SUMMARY_QUERY"
        debug_data["sql"]["parameters"] = binds
        debug_data["rows"] = len(summary_rows)
        debug_data["sample_rows"] = summary_rows
        debug_data["transformer"]["input"] = summary_rows
        debug_data["transformer"]["output"] = chart_data
        debug_data["llm_response"] = response_text
        debug_data["timeline"]["Core Summary Deterministico"] = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        return {
            "status": "FULL_RENDERING",
            "pergunta_original": pergunta,
            "mensagem": None,
            "resposta_direta": response_text,
            "ia_justificativa": response_text,
            "view_name": "VW_VENDAS_LM",
            "view_catalog_id": None,
            "parametros_extraidos": {str(key): str(value) for key, value in binds.items()},
            "ia_confianca": 1.0,
            "pode_favoritar": True,
            "chart_type": SchemaChartType.TABLE.value,
            "chart_data": chart_data,
            "insights": [],
            "recommendations": [],
            "warnings": [],
            "telemetry": {
                "timings": {
                    "total_pipeline": elapsed,
                    "deterministic_summary": elapsed,
                },
                "trace_id": str(trace_id),
                "pipeline_version": "2.0-core-summary",
            },
            "trust_center": {
                "source": "Oracle ERP -> VW_VENDAS_LM",
                "confidence_score": 1.0,
                "calculation": "deterministic_core_summary",
            },
        }

    def _is_missing_physical_column_error(self, exc: Exception) -> bool:
        error_text = str(exc).lower()
        return any(
            token in error_text
            for token in (
                "undefinedcolumn",
                "undefined column",
                "does not exist",
                "coluna",
                "nao existe",
                "não existe",
            )
        )

    def _normalize_query_text(self, value: str) -> str:
        text_value = unicodedata.normalize("NFKD", str(value or "").lower())
        normalized = "".join(ch for ch in text_value if not unicodedata.combining(ch))
        normalized = re.sub(r"mar\?+o", "marco", normalized)
        normalized = re.sub(r"m\?+s", "mes", normalized)
        return (
            normalized
            .replace("mar?o", "marco")
            .replace("m?s", "mes")
            .replace("n?o", "nao")
            .replace("m?dio", "medio")
        )

    def _month_range_from_text(self, text_value: str) -> Optional[tuple[str, str]]:
        normalized = self._normalize_query_text(text_value)

        day_match = re.search(r"\b(0?[1-9]|[12]\d|3[01])\s*/\s*(0?[1-9]|1[0-2])\s*/\s*(20\d{2})\b", normalized)
        if day_match:
            day = int(day_match.group(1))
            month = int(day_match.group(2))
            year = int(day_match.group(3))
            try:
                exact_day = date(year, month, day)
            except ValueError:
                return None
            return exact_day.isoformat(), exact_day.isoformat()

        numeric_match = re.search(r"\b(0?[1-9]|1[0-2])\s*/\s*(20\d{2})\b", normalized)
        if numeric_match:
            month = int(numeric_match.group(1))
            year = int(numeric_match.group(2))
            last_day = calendar.monthrange(year, month)[1]
            return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}"

        month_names = {
            "janeiro": 1,
            "fevereiro": 2,
            "marco": 3,
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
        month_match = re.search(
            r"\b(janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\b(?:\s+de)?\s+(20\d{2})",
            normalized,
        )
        if month_match:
            month = month_names[month_match.group(1)]
            year = int(month_match.group(2))
            last_day = calendar.monthrange(year, month)[1]
            return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}"

        today = date.today()
        if "mes anterior" in normalized or "mes passado" in normalized:
            year = today.year
            month = today.month - 1
            if month == 0:
                month = 12
                year -= 1
            last_day = calendar.monthrange(year, month)[1]
            return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}"

        current_month_patterns = (
            "faturamento do mes",
            "faturamento mes",
            "venda do mes",
            "vendas do mes",
            "ticket medio do mes",
            "desconto do mes",
        )
        if any(pattern in normalized for pattern in current_month_patterns):
            last_day = calendar.monthrange(today.year, today.month)[1]
            return f"{today.year:04d}-{today.month:02d}-01", f"{today.year:04d}-{today.month:02d}-{last_day:02d}"

        return None

    def _ensure_period_filter(self, semantic_plan: SemanticPlan, pergunta: str) -> None:
        text_value = f"{pergunta or ''} {semantic_plan.goal or ''}"
        month_range = self._month_range_from_text(text_value)
        if not month_range:
            return

        has_date_filter = any(
            any(token in str(query_filter.field).lower() for token in ("data", "dt", "emissao", "periodo", "mes", "ano"))
            for query_filter in semantic_plan.filters
        )
        if has_date_filter:
            return

        start_date, end_date = month_range
        semantic_plan.filters.append(
            SemanticFilter(
                field="Data",
                operator=ComparisonOperator.BETWEEN,
                value=f"{start_date},{end_date}",
            )
        )
        if "Data" not in semantic_plan.dimensions:
            semantic_plan.dimensions.append("Data")

    def _repair_core_business_query(self, semantic_plan: SemanticPlan, pergunta: str) -> None:
        normalized = self._normalize_query_text(f"{pergunta or ''} {semantic_plan.goal or ''}")

        def apply_rank_limit(default_limit: int = 10) -> None:
            top_match = re.search(r"\b(?:top|primeiros|maiores)\s+(\d{1,3})\b", normalized)
            if top_match:
                semantic_plan.limit = max(1, min(int(top_match.group(1)), 100))
            elif any(term in normalized for term in ("maior", "mais vendeu", "vendeu mais", "mais comprou", "comprou mais")):
                semantic_plan.limit = 1
            elif not semantic_plan.limit or semantic_plan.limit > default_limit:
                semantic_plan.limit = default_limit

        if "desconto" in normalized:
            semantic_plan.status = ExecutionStatus.READY
            if "Venda" not in semantic_plan.entities:
                semantic_plan.entities.append("Venda")
            if "vendedor" in normalized and "Vendedor" not in semantic_plan.entities:
                semantic_plan.entities.append("Vendedor")

            is_average = any(term in normalized for term in ("medio", "media"))
            metric_name = "Desconto Medio" if is_average else "Desconto"
            semantic_plan.metrics = [metric_name]

            if "vendedor" in normalized:
                semantic_plan.intent = IntentType.RANKING
                semantic_plan.suggested_visualization = VisualizationType.BAR
                semantic_plan.limit = 1 if any(term in normalized for term in ("maior", "top", "mais")) else semantic_plan.limit
                if "Vendedor" not in semantic_plan.dimensions:
                    semantic_plan.dimensions.append("Vendedor")
            else:
                semantic_plan.intent = IntentType.KPI
                semantic_plan.suggested_visualization = VisualizationType.KPI_CARD

        if any(term in normalized for term in ("faturamento", "receita", "venda", "ticket")):
            if "Venda" not in semantic_plan.entities:
                semantic_plan.entities.append("Venda")

        if "ticket" in normalized:
            semantic_plan.status = ExecutionStatus.READY
            semantic_plan.metrics = ["Ticket Medio"]
            semantic_plan.intent = IntentType.KPI
            semantic_plan.suggested_visualization = VisualizationType.KPI_CARD

        is_monthly_sales_kpi = any(
            term in normalized
            for term in (
                "venda do mes",
                "vendas do mes",
                "venda no mes",
                "vendas no mes",
                "venda em",
                "vendas em",
            )
        ) and not any(term in normalized for term in ("por vendedor", "por cliente", "ranking", "top"))

        if "faturamento" in normalized or "receita" in normalized or is_monthly_sales_kpi:
            semantic_plan.status = ExecutionStatus.READY
            semantic_plan.intent = IntentType.KPI
            semantic_plan.suggested_visualization = VisualizationType.KPI_CARD
            if not semantic_plan.metrics:
                semantic_plan.metrics = ["Receita"]

        if "vendedor" in normalized and any(term in normalized for term in ("maior venda", "mais vendeu", "vendeu mais", "venda por vendedor", "vendas por vendedor")):
            semantic_plan.status = ExecutionStatus.READY
            semantic_plan.intent = IntentType.RANKING
            semantic_plan.suggested_visualization = VisualizationType.BAR
            if "Venda" not in semantic_plan.entities:
                semantic_plan.entities.append("Venda")
            if "Vendedor" not in semantic_plan.entities:
                semantic_plan.entities.append("Vendedor")
            if "Receita" not in semantic_plan.metrics:
                semantic_plan.metrics = ["Receita"]
            if "Vendedor" not in semantic_plan.dimensions:
                semantic_plan.dimensions.append("Vendedor")
            if any(term in normalized for term in ("maior", "mais vendeu", "vendeu mais")):
                semantic_plan.limit = 1

        if "cliente" in normalized and any(
            term in normalized
            for term in (
                "ranking",
                "top",
                "maior",
                "mais comprou",
                "mais compraram",
                "comprou mais",
                "compraram mais",
                "clientes que mais",
                "cliente que mais",
                "venda por cliente",
                "vendas por cliente",
                "faturamento por cliente",
            )
        ):
            semantic_plan.status = ExecutionStatus.READY
            semantic_plan.intent = IntentType.RANKING
            semantic_plan.suggested_visualization = VisualizationType.BAR
            if "Venda" not in semantic_plan.entities:
                semantic_plan.entities.append("Venda")
            if "Cliente" not in semantic_plan.entities:
                semantic_plan.entities.append("Cliente")
            semantic_plan.metrics = ["Receita"]
            if "Cliente" not in semantic_plan.dimensions:
                semantic_plan.dimensions.append("Cliente")
            apply_rank_limit()

        self._ensure_period_filter(semantic_plan, pergunta)

    def _extract_storage_date_params(self, canonical_plan: CanonicalPlan) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        for query_filter in canonical_plan.filters:
            field_name = str(query_filter.field or "").lower()
            if not any(term in field_name for term in ("data", "dt", "emissao", "periodo", "mes", "ano")):
                continue

            raw_value = query_filter.value
            if isinstance(raw_value, (list, tuple)):
                dates = [str(item)[:10] for item in raw_value if item not in (None, "")]
            else:
                dates = re.findall(r"\d{4}-\d{2}-\d{2}", str(raw_value))
                if not dates and raw_value not in (None, ""):
                    dates = [str(raw_value)[:10]]

            if not dates:
                continue

            if query_filter.operator == ComparisonOperator.BETWEEN and len(dates) >= 2:
                params["data_inicio"] = dates[0]
                params["data_fim"] = dates[1]
            else:
                params["data_inicio"] = dates[0]
                params["data_fim"] = dates[-1] if len(dates) > 1 else dates[0]

        return params

    def _storage_metric_key(self, metric_name: str) -> str:
        metric = str(metric_name or "").lower()
        if "desconto" in metric:
            return "desconto_medio" if any(term in metric for term in ("médio", "medio", "media")) else "desconto_total"
        if "ticket" in metric:
            return "ticket_medio"
        if any(term in metric for term in ("quantidade", "qtd", "unidade")):
            return "unidades_vendidas"
        if any(term in metric for term in ("lucro", "margem")):
            return "lucro_bruto" if "lucro" in metric else "margem_lucro"
        return "receita_total"

    def _storage_group_key(self, dimension_name: str) -> Optional[str]:
        dimension = str(dimension_name or "").lower()
        if "vendedor" in dimension or "nome_ved" in dimension:
            return "vendedor"
        if "cliente" in dimension or "razao" in dimension:
            return "cliente_nome"
        if "produto" in dimension or "descricao" in dimension:
            return "produto"
        if any(term in dimension for term in ("data", "dt", "periodo", "mes", "ano", "emissao")):
            return None
        return None

    def _fallback_view_for_plan(self, canonical_plan: CanonicalPlan, pergunta: str) -> Optional[str]:
        semantic_text = " ".join(
            [
                pergunta or "",
                canonical_plan.goal or "",
                " ".join(canonical_plan.entities),
                " ".join(canonical_plan.metrics),
                " ".join(canonical_plan.dimensions),
            ]
        ).lower()
        if any(term in semantic_text for term in ("venda", "receita", "ticket", "faturamento", "vendedor", "desconto")):
            return "VW_VENDAS_CONTEXTO_GERAL"
        return None

    def _build_storage_fallback_params(self, canonical_plan: CanonicalPlan, tenant_id: str) -> Dict[str, Any]:
        params = {"tenant_id": tenant_id}
        params.update(self._extract_storage_date_params(canonical_plan))

        metric_keys: List[str] = []
        for metric in canonical_plan.metrics:
            metric_key = self._storage_metric_key(metric)
            if metric_key not in metric_keys:
                metric_keys.append(metric_key)
        if not metric_keys:
            metric_keys.append("receita_total")
        params["_metrics"] = ",".join(metric_keys)

        group_keys: List[str] = []
        for dimension in canonical_plan.dimensions:
            group_key = self._storage_group_key(dimension)
            if group_key and group_key not in group_keys:
                group_keys.append(group_key)
        if canonical_plan.intent == IntentType.RANKING and not group_keys:
            for entity in canonical_plan.entities:
                group_key = self._storage_group_key(entity)
                if group_key and group_key not in group_keys:
                    group_keys.append(group_key)

        if group_keys:
            params["_group_by"] = ",".join(group_keys)
            params["_order_metric"] = metric_keys[0]
            params["_order_direction"] = "DESC"

        if canonical_plan.limit:
            params["limite"] = canonical_plan.limit

        return params

    def _is_zero_discount_ranking(self, canonical_plan: CanonicalPlan, rows: List[Dict[str, Any]]) -> bool:
        if canonical_plan.intent != IntentType.RANKING or not rows:
            return False
        if not any("desconto" in str(metric or "").lower() for metric in canonical_plan.metrics):
            return False

        discount_values: List[float] = []
        for row in rows:
            for key, value in row.items():
                if "desconto" not in str(key or "").lower():
                    continue
                try:
                    discount_values.append(float(value or 0))
                except (TypeError, ValueError):
                    continue

        return bool(discount_values) and max(discount_values) <= 0

    async def _execute_storage_fallback(
        self,
        canonical_plan: CanonicalPlan,
        tenant_id: str,
        pergunta: str,
    ) -> Optional[tuple[List[Dict[str, Any]], str, Dict[str, Any]]]:
        fallback_view = self._fallback_view_for_plan(canonical_plan, pergunta)
        if not fallback_view:
            return None

        try:
            from models.tenant import Tenant
            from services.data_platform.analytical_storage import AnalyticalStorage

            params = self._build_storage_fallback_params(canonical_plan, tenant_id)
            async with get_db_context() as db_session:
                tenant_result = await db_session.execute(
                    select(Tenant).where(Tenant.id == uuid.UUID(str(tenant_id)))
                )
                tenant = tenant_result.scalar_one_or_none()
                if not tenant:
                    logger.warning("[Orchestrator] Fallback analitico ignorado: tenant nao localizado.")
                    return None

                rows = await AnalyticalStorage().execute_view(
                    tenant=tenant,
                    view_name=fallback_view,
                    parameters=params,
                    db_session=db_session,
                )
            return rows, fallback_view, params
        except Exception as fallback_exc:
            logger.warning("[Orchestrator] Fallback analitico nao conseguiu recuperar a consulta: %s", fallback_exc)
            return None

    async def run_pipeline(
        self,
        pergunta: str,
        tenant_id: str,
        session_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        dashboard_state_override: Optional[DashboardState] = None,
        parent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        trace_id = uuid.uuid4()
        history = history or []
        session_key = session_id or tenant_id

        # ── Inicialização do PIPELINE DEBUG ──
        debug_data = {
            "pergunta": pergunta,
            "resposta_bruta_llm": None,
            "semantic_plan": None,
            "canonical_plan": None,
            "execution_plan": None,
            "selected_views": [],
            "joins": [],
            "sql": {
                "raw_sql": None,
                "parameters": {}
            },
            "execution_time_ms": 0.0,
            "rows": 0,
            "sample_rows": [],
            "transformer": {
                "input": [],
                "output": {}
            },
            "chart": None,
            "llm_prompt": None,
            "llm_response": None,
            "error_traceback": None,
            "timeline": {}
        }

        from datetime import datetime
        def get_timestamp() -> str:
            return datetime.now().strftime("%H:%M:%S.%f")[:-3]

        debug_data["timeline"]["1. Pergunta Recebida"] = get_timestamp()

        def save_debug_logs(payload: dict):
            try:
                import os
                import json

                # Popula o payload final no debug
                debug_data["payload_frontend"] = payload
                debug_data["timeline"]["16. Frontend Retornado"] = get_timestamp()

                # Se houver erro ou exceção no status do payload
                if payload.get("status") in ("AMBIGUOUS", "MISSING_INFORMATION", "OUT_OF_SCOPE", "SECURITY_VIOLATION", "DATABASE_ERROR", "EMPTY_ANOMALY"):
                    if not debug_data.get("error_traceback"):
                        debug_data["error_traceback"] = payload.get("message") or payload.get("mensagem") or payload.get("resposta_direta")

                # Latência total
                debug_data["timeline"]["Total Processamento"] = f"{(time.perf_counter() - start_time) * 1000:.2f}ms"

                # Formata SQL com quebras de linha estéticas para legibilidade no trace
                if debug_data["sql"]["raw_sql"]:
                    raw = debug_data["sql"]["raw_sql"]
                    formatted = raw.replace(" SELECT ", "\nSELECT\n  ").replace(" FROM ", "\nFROM\n  ").replace(" LEFT JOIN ", "\nLEFT JOIN\n  ").replace(" INNER JOIN ", "\nINNER JOIN\n  ").replace(" JOIN ", "\nJOIN\n  ").replace(" WHERE ", "\nWHERE\n  ").replace(" GROUP BY ", "\nGROUP BY\n  ").replace(" HAVING ", "\nHAVING\n  ").replace(" ORDER BY ", "\nORDER BY\n  ").replace(" LIMIT ", "\nLIMIT\n  ")
                    debug_data["sql"]["raw_sql"] = formatted

                log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runtime-logs", "debug")
                os.makedirs(log_dir, exist_ok=True)

                debug_json = json.dumps(debug_data, indent=4, default=str, ensure_ascii=False)

                # Salva trace persistente por trace_id
                with open(os.path.join(log_dir, f"debug_{trace_id}.json"), "w", encoding="utf-8") as f:
                    f.write(debug_json)
                # Sobrescreve trace global da última execução
                with open(os.path.join(log_dir, "debug_steps.json"), "w", encoding="utf-8") as f:
                    f.write(debug_json)
            except Exception as e_log:
                logger.error("Erro ao salvar log de debug em disco: %s", e_log)

        def write_debug_and_return(payload: dict) -> dict:
            payload["trace_id"] = str(trace_id)
            payload["query_id"] = str(trace_id)
            payload["request_id"] = str(trace_id)
            save_debug_logs(payload)
            payload["debug_info"] = debug_data
            return payload

        # ── 1. Conversation Graph Recuperação ─────────────────────────
        from services.metadata_catalog.conversation_graph import conversation_graph_manager
        graph = conversation_graph_manager.get_graph(session_key)

        # Se o parent_id foi fornecido explicitamente, navega/muda o nó ativo para ele
        if parent_id and parent_id in graph.nodes:
            graph.current_node_id = parent_id
            conversation_graph_manager.save_graph(session_key, graph)

        effective_pergunta = self._question_with_inherited_period(pergunta, history)
        if effective_pergunta != pergunta:
            debug_data["pergunta_contextualizada"] = effective_pergunta

        if self._is_core_summary_query(effective_pergunta):
            debug_data["timeline"]["Core Summary Detectado"] = get_timestamp()
            summary_payload = await self._execute_core_summary_query(
                pergunta=effective_pergunta,
                tenant_id=tenant_id,
                session_key=session_key,
                trace_id=trace_id,
                start_time=start_time,
                debug_data=debug_data,
                conversation_graph_manager=conversation_graph_manager,
            )
            summary_payload["pergunta_original"] = pergunta
            if effective_pergunta != pergunta:
                parametros = dict(summary_payload.get("parametros_extraidos") or {})
                parametros["periodo_herdado_de_contexto"] = "true"
                summary_payload["parametros_extraidos"] = parametros
            return write_debug_and_return(summary_payload)

        # Adquire cliente OpenAI correspondente ao tenant usando o resolve_client correto
        lease = await ai_credential_manager.resolve_client(tenant_id=uuid.UUID(tenant_id))
        client = lease.client
        model = lease.model

        # ── 2. Intercepção Local: Operações Visuais, Drill-down e Explicações ──────
        # A) Operações de UI / Visuais sem tocar no banco ou na IA
        visual_res = conversation_graph_manager.try_visual_only_update(
            pergunta=pergunta, graph=graph, session_id=session_key, trace_id=trace_id
        )
        if visual_res:
            debug_data["timeline"]["Local UI Interception"] = get_timestamp()
            return write_debug_and_return(visual_res)

        # B) Drill-down local em memória se os dados estiverem disponíveis
        drilldown_res = conversation_graph_manager.try_local_drilldown(
            pergunta=pergunta, graph=graph, session_id=session_key, trace_id=trace_id
        )
        if drilldown_res:
            debug_data["timeline"]["Local Drill-Down Interception"] = get_timestamp()
            return write_debug_and_return(drilldown_res)

        # C) Perguntas explicativas locais sobre os dados já carregados
        from services.metadata_catalog.explainability import explainability_engine
        explain_local_res = await explainability_engine.explain_local_dataset(
            query=pergunta, graph=graph, client=client, model=model
        )
        if explain_local_res:
            debug_data["timeline"]["Local Explainability Interception"] = get_timestamp()
            return write_debug_and_return(explain_local_res)

        # Inicializa o cache de planos na classe se necessário
        if not hasattr(self, "_last_semantic_plans"):
            self._last_semantic_plans = {}

        # Extrai contexto conversacional estruturado do nó ativo atual para guiar a IA
        last_plan = None
        last_db_state = None
        last_q_context = None

        if graph.current_node_id and graph.current_node_id in graph.nodes:
            active_node = graph.nodes[graph.current_node_id]
            last_plan = SemanticPlan(
                status=active_node.canonical_plan.status,
                intent=active_node.canonical_plan.intent,
                goal=active_node.canonical_plan.goal,
                entities=active_node.canonical_plan.entities,
                metrics=active_node.canonical_plan.metrics,
                dimensions=active_node.canonical_plan.dimensions,
                filters=[],  # IA analisa o plano limpo
                trace_id=active_node.canonical_plan.trace_id
            )
            last_db_state = active_node.dashboard_state
            last_q_context = active_node.query_context

        # ── 2. LLM Intent Engine (Fase de Entrada Refatorada) ─────────
        semantic_plan = None
        debug_data["timeline"]["2. Intent Engine Iniciado"] = get_timestamp()
        try:
            from services.metadata_catalog.intent_engine import corporate_intent_engine
            intent_output = await corporate_intent_engine.analyze_query(
                query=pergunta,
                tenant_id=tenant_id,
                history=history,
                last_plan=last_plan,
                dashboard_state=last_db_state,
                query_context=last_q_context
            )
            debug_data["timeline"]["3. Intent Engine Concluído"] = get_timestamp()
            debug_data["resposta_bruta_llm"] = getattr(intent_output, "raw_response", None) or intent_output.model_dump_json()

            # Se for continuidade e houver plano anterior no cache, aplica os patches
            cache_key = session_id or tenant_id
            if intent_output.is_continuity and last_plan:
                base_plan = last_plan

                # Importa copy localmente para segurança
                import copy
                semantic_plan = copy.deepcopy(base_plan)
                semantic_plan.trace_id = trace_id

                # Aplica cada patch semântico gerado pelo interpretador conceitual
                for patch in intent_output.patches:
                    op = patch.operation.upper()
                    if op == "ADD_FILTER" and patch.field and patch.value is not None:
                        semantic_plan.filters.append(
                            SemanticFilter(
                                field=patch.field,
                                operator=ComparisonOperator.EQUALS,
                                value=patch.value
                            )
                        )
                    elif op == "CHANGE_PERIOD" and patch.value:
                        # Limpa datas antigas
                        semantic_plan.filters = [f for f in semantic_plan.filters if f.field.lower() not in ("periodo", "data", "date", "dtemissao", "dtemissao_")]
                        semantic_plan.filters.append(
                            SemanticFilter(
                                field="Periodo",
                                operator=ComparisonOperator.EQUALS,
                                value=patch.value
                            )
                        )
                    elif op == "REMOVE_FILTER" and patch.field:
                        semantic_plan.filters = [f for f in semantic_plan.filters if f.field.lower() != patch.field.lower()]
                    elif op == "ADD_METRIC" and patch.field:
                        if patch.field not in semantic_plan.metrics:
                            semantic_plan.metrics.append(patch.field)
                    elif op == "CHANGE_LIMIT" and patch.value is not None:
                        try:
                            semantic_plan.limit = int(patch.value)
                        except ValueError:
                            pass
                debug_data["timeline"]["4. Patches Semânticos Aplicados"] = get_timestamp()
                logger.info("[Orchestrator] Patches semânticos aplicados com sucesso sobre o plano anterior.")
            else:
                if intent_output.plan:
                    semantic_plan = intent_output.plan
                    semantic_plan.trace_id = trace_id
                else:
                    raise ValueError("Plano semântico não gerado pela IA no modo normal.")

            # Auto-cura de status analítico: se a LLM classificar pessimistamente como MISSING_INFORMATION,
            # mas termos ou entidades válidos estão presentes no plano, coage o status para READY para viabilizar a execução.
            if intent_output.status in (ExecutionStatus.MISSING_INFORMATION, ExecutionStatus.UNSUPPORTED):
                if semantic_plan.intent in (IntentType.LIST, IntentType.AGGREGATION, IntentType.RANKING, IntentType.TREND) or len(semantic_plan.entities) > 0:
                    logger.info("[Orchestrator] Auto-cura: Coagindo status de %s para READY para viabilizar execucao.", intent_output.status)
                    intent_output.status = ExecutionStatus.READY
                    semantic_plan.status = ExecutionStatus.READY

            # Trata status não-prontos
            self._repair_core_business_query(semantic_plan, pergunta)
            if semantic_plan.status == ExecutionStatus.READY:
                intent_output.status = ExecutionStatus.READY

            semantic_plan.status = intent_output.status
            debug_data["semantic_plan"] = semantic_plan.model_dump()

            if intent_output.status in (ExecutionStatus.AMBIGUOUS, ExecutionStatus.MISSING_INFORMATION, ExecutionStatus.OUT_OF_SCOPE):
                elapsed = (time.perf_counter() - start_time) * 1000
                res = {
                    "status": intent_output.status.value,
                    "goal": semantic_plan.goal or pergunta,
                    "ambiguities": intent_output.ambiguities,
                    "missing_information": intent_output.missing_information,
                    "resposta_direta": "Identifiquei termos ambíguos ou informações ausentes na pergunta analítica.",
                    "pergunta_original": pergunta,
                    "execution_time_ms": elapsed
                }
                return write_debug_and_return(res)

            # Salva o plano semântico bem-sucedido no cache para futuras continuidades
            self._last_semantic_plans[cache_key] = semantic_plan

        except Exception as exc:
            import traceback
            debug_data["error_traceback"] = traceback.format_exc()
            logger.error("[Orchestrator] Falha no Motor de Intenções Refatorado: %s", exc, exc_info=True)
            # Fallback determinístico seguro
            semantic_plan = SemanticPlan(
                status=ExecutionStatus.READY,
                intent=IntentType.LIST,
                goal=pergunta,
                entities=["Cliente"],
                metrics=[],
                dimensions=[],
                trace_id=trace_id
            )
            debug_data["semantic_plan"] = semantic_plan.model_dump()

        # ── 3. Query Intent Resolver ──────────────────────────────────
        debug_data["timeline"]["5. Canonicalizer Iniciado"] = get_timestamp()
        canonical_plan = self.resolver.canonicalize(semantic_plan)
        debug_data["timeline"]["6. Canonicalizer Concluído"] = get_timestamp()
        debug_data["canonical_plan"] = canonical_plan.model_dump()

        # ── 4. Reutilização de Dataset em Memória RAM ─────────────────
        # Desabilitado para garantir execução analítica fresca e evitar contaminação entre perguntas consecutivas
        reused_rows = None

        # Mapeia optimized_plan como exec_plan para compatibilidade posterior no fluxo de salvamento do nó
        optimized_plan = None
        exec_plan = None
        data_source_view_name = None
        sql = ""
        binds = {}

        if canonical_plan.status in (ExecutionStatus.AMBIGUOUS, ExecutionStatus.MISSING_INFORMATION, ExecutionStatus.OUT_OF_SCOPE, ExecutionStatus.UNSUPPORTED):
            logger.warning(f"[Orchestrator] Interrompendo pipeline devido a status conceitual inválido: {canonical_plan.status}")
            elapsed = (time.perf_counter() - start_time) * 1000

            status_map = {
                ExecutionStatus.AMBIGUOUS: "AMBIGUOUS",
                ExecutionStatus.MISSING_INFORMATION: "MISSING_INFORMATION",
                ExecutionStatus.OUT_OF_SCOPE: "OUT_OF_SCOPE",
                ExecutionStatus.UNSUPPORTED: "UNSUPPORTED"
            }

            msg_map = {
                ExecutionStatus.AMBIGUOUS: "Sua pergunta analítica contém ambiguidades estruturais. Por favor, tente ser mais específico.",
                ExecutionStatus.MISSING_INFORMATION: "Faltam informações comerciais essenciais para responder à sua pergunta.",
                ExecutionStatus.OUT_OF_SCOPE: "Esta pergunta está fora do escopo da análise de dados de BI da empresa.",
                ExecutionStatus.UNSUPPORTED: "Não foi possível mapear os termos informados para colunas físicas existentes no catálogo corporativo."
            }

            res = {
                "status": status_map.get(canonical_plan.status, "INVALID_PLAN"),
                "message": msg_map.get(canonical_plan.status, "Plano analítico conceitual inválido."),
                "mensagem": msg_map.get(canonical_plan.status, "Plano analítico conceitual inválido."),
                "resposta_direta": msg_map.get(canonical_plan.status, "Plano analítico conceitual inválido."),
                "pergunta_original": pergunta,
                "execution_time_ms": elapsed,
                "sample_rows": [],
                "transformer": {"output": None},
                "llm_response": msg_map.get(canonical_plan.status, "Plano analítico conceitual inválido.")
            }
            return write_debug_and_return(res)

        if reused_rows is not None:
            logger.info("[Orchestrator] Poupando execução de query física: dataset compatível reutilizado do Conversation Graph.")
            normalized_rows = reused_rows
            sql = "REUSED_FROM_MEMORY"
            binds = {}
            debug_data["sql"]["raw_sql"] = sql
            debug_data["sql"]["parameters"] = binds
            debug_data["rows"] = len(normalized_rows)
            debug_data["sample_rows"] = normalized_rows[:20]
            debug_data["timeline"]["Reuso de Dataset em RAM"] = get_timestamp()
        else:
            # ── 5. Planner Engine (BFS Dijkstra) ──────────────────────────
            debug_data["timeline"]["7. Metadata Resolver Iniciado"] = get_timestamp()
            exec_plan = self.planner.resolve(canonical_plan)
            debug_data["timeline"]["8. Metadata Resolver Concluído"] = get_timestamp()
            debug_data["execution_plan"] = exec_plan.model_dump()
            data_source_view_name = exec_plan.selected_views[0] if exec_plan.selected_views else None

            # Coleta as views candidatas avaliadas com os scores e joins
            debug_data["selected_views"] = getattr(exec_plan, "selected_views", [])
            debug_data["joins"] = getattr(exec_plan.resolved_entities, "joins", []) if getattr(exec_plan, "resolved_entities", None) else []

            if canonical_plan.intent in (IntentType.KPI, IntentType.AGGREGATION):
                exec_plan.empty_dataset_policy = EmptyDatasetPolicy.EMPTY_UNEXPECTED

            if exec_plan.status == ExecutionStatus.NEEDS_REPLANNING:
                elapsed = (time.perf_counter() - start_time) * 1000
                res = {
                    "status": "NEEDS_REPLANNING",
                    "message": "Nao foi possivel estabelecer relacionamentos fisicos de JOIN no catalogo de views.",
                    "mensagem": "Nao foi possivel estabelecer relacionamentos fisicos de JOIN no catalogo de views.",
                    "resposta_direta": "Nao foi possivel estabelecer relacionamentos fisicos de JOIN no catalogo de views.",
                    "pergunta_original": pergunta,
                    "execution_time_ms": elapsed
                }
                return write_debug_and_return(res)

            # ── 6. Query Optimizer & SQL Generator ────────────────────────
            debug_data["timeline"]["9. SQL Generator Iniciado"] = get_timestamp()
            optimized_plan = self.optimizer.optimize_plan(exec_plan)
            sql, binds = self.generator.generate_sql(optimized_plan)
            if not sql or not sql.strip():
                logger.warning("[Orchestrator] SQL gerado está vazio. Retornando erro de plano analítico.")
                elapsed = (time.perf_counter() - start_time) * 1000
                res = {
                    "status": "INVALID_PLAN",
                    "message": "Não foi possível gerar uma consulta estruturada a partir dos conceitos fornecidos. Certifique-se de que a pergunta analítica se refere a entidades e dimensões válidas do catálogo.",
                    "mensagem": "Não foi possível gerar uma consulta estruturada a partir dos conceitos fornecidos. Certifique-se de que a pergunta analítica se refere a entidades e dimensões válidas do catálogo.",
                    "resposta_direta": "Não foi possível gerar uma consulta estruturada a partir dos conceitos fornecidos. Certifique-se de que a pergunta analítica se refere a entidades e dimensões válidas do catálogo.",
                    "pergunta_original": pergunta,
                    "execution_time_ms": elapsed,
                    "sample_rows": [],
                    "transformer": {"output": None},
                    "llm_response": "Não foi possível gerar uma consulta estruturada a partir dos conceitos fornecidos. Certifique-se de que a pergunta analítica se refere a entidades e dimensões válidas do catálogo."
                }
                return write_debug_and_return(res)

            debug_data["timeline"]["10. SQL Generator Concluído"] = get_timestamp()
            debug_data["sql"]["raw_sql"] = sql
            debug_data["sql"]["parameters"] = binds

            # ── 7. Security Validator ─────────────────────────────────────
            debug_data["timeline"]["11. Security Validator Iniciado"] = get_timestamp()
            try:
                self.validator.validate_sql_safety(sql, tenant_id)
                debug_data["timeline"]["12. Security Validator Concluído"] = get_timestamp()
            except Exception as sec_exc:
                import traceback
                debug_data["error_traceback"] = traceback.format_exc()
                logger.error("[Orchestrator] SQL bloqueado pelo validador de seguranca: %s", sec_exc)
                elapsed = (time.perf_counter() - start_time) * 1000
                res = {
                    "status": "SECURITY_VIOLATION",
                    "message": f"Erro de seguranca analitica: {sec_exc}",
                    "mensagem": f"Erro de seguranca analitica: {sec_exc}",
                    "resposta_direta": f"Erro de seguranca analitica: {sec_exc}",
                    "pergunta_original": pergunta,
                    "execution_time_ms": elapsed,
                    "sample_rows": [],
                    "transformer": {"output": None},
                    "llm_response": f"Erro de seguranca analitica: {sec_exc}"
                }
                return write_debug_and_return(res)

            # ── 8. Execution & Result Normalizer (Self-Healing Loop) ──────
            debug_data["timeline"]["13. Database Executor Iniciado"] = get_timestamp()
            execution_success = False
            attempts = 2
            normalized_rows = []

            while attempts > 0 and not execution_success:
                attempts -= 1
                try:
                    # Executa a query física usando o novo DatabaseExecutor unificado do CKG
                    from services.metadata_catalog.executor import database_executor
                    from services.security_and_normalization_engine import EmptyDatasetAnomalyError
                    from services.metadata_catalog.self_healing import self_healing_engine

                    result_dataset = await database_executor.execute_query(
                        plan=optimized_plan,
                        sql=sql,
                        binds=binds,
                        tenant_id=tenant_id
                    )

                    # Dispara anomalia caso o status indique necessidade de replanejamento ou dataset vazio
                    if result_dataset.get("status") == "NEEDS_REPLANNING" or (not result_dataset.get("values") and self_healing_engine.should_heal(str(trace_id), exec_plan.status, [], optimized_plan)):
                        raise EmptyDatasetAnomalyError("Dataset vazio inesperado detectado durante a execução analítica.")

                    normalized_rows = result_dataset.get("values", [])
                    execution_success = True
                    debug_data["rows"] = len(normalized_rows)
                    debug_data["sample_rows"] = normalized_rows[:20]
                    debug_data["timeline"]["13. Database Executor Concluído"] = get_timestamp()
                except EmptyDatasetAnomalyError as anomaly_exc:
                    logger.warning("[Orchestrator] Loop de Auto-Cura acionado por anomalia: %s", anomaly_exc)
                    if attempts > 0 and self_healing_engine.should_heal(str(trace_id), exec_plan.status, [], optimized_plan):
                        self_healing_engine.mark_healed(str(trace_id))
                        feedback_prompt = self_healing_engine.generate_healing_feedback(str(anomaly_exc), optimized_plan)
                        try:
                            # Re-planeja utilizando o Intent Engine conceitual
                            from services.metadata_catalog.intent_engine import corporate_intent_engine
                            intent_output = await corporate_intent_engine.analyze_query(
                                query=feedback_prompt,
                                tenant_id=tenant_id,
                                history=history,
                                last_plan=last_plan,
                                dashboard_state=last_db_state,
                                query_context=last_q_context
                            )

                            if intent_output.plan:
                                semantic_plan = intent_output.plan
                                semantic_plan.trace_id = trace_id

                                # Re-planeja e re-otimiza
                                canonical_plan = self.resolver.canonicalize(semantic_plan)
                                exec_plan = self.planner.resolve(canonical_plan)
                                data_source_view_name = exec_plan.selected_views[0] if exec_plan.selected_views else data_source_view_name
                                optimized_plan = self.optimizer.optimize_plan(exec_plan)
                                sql, binds = self.generator.generate_sql(optimized_plan)
                                if not sql or not sql.strip():
                                    logger.warning("[Orchestrator] SQL regenerado na auto-cura está vazio. Abortando loop de cura.")
                                    break
                                debug_data["sql"]["raw_sql"] = sql
                                debug_data["sql"]["parameters"] = binds
                            else:
                                break
                        except Exception as regen_exc:
                            logger.error("[Orchestrator] Falha ao regenerar plano na auto-cura: %s", regen_exc)
                            break
                    else:
                        elapsed = (time.perf_counter() - start_time) * 1000
                        res = {
                            "status": "EMPTY_ANOMALY",
                            "message": "Não foram encontrados dados nos registros desta empresa para o período solicitado.",
                            "mensagem": "Não foram encontrados dados nos registros desta empresa para o período solicitado.",
                            "resposta_direta": "Não foram encontrados dados nos registros desta empresa para o período solicitado.",
                            "pergunta_original": pergunta,
                            "execution_time_ms": elapsed,
                            "sample_rows": [],
                            "transformer": {"output": None},
                            "llm_response": "Não foram encontrados registros comerciais ou financeiros correspondentes para o período ou filtros informados."
                        }
                        return write_debug_and_return(res)
                except Exception as db_exc:
                    import traceback
                    debug_data["error_traceback"] = traceback.format_exc()
                    logger.error("[Orchestrator] Erro na execucao fisica do SQL: %s", db_exc)
                    if self._is_missing_physical_column_error(db_exc):
                        fallback_result = await self._execute_storage_fallback(canonical_plan, tenant_id, pergunta)
                        if fallback_result is not None:
                            normalized_rows, fallback_view, fallback_params = fallback_result
                            data_source_view_name = fallback_view
                            sql = f"ANALYTICAL_STORAGE_FALLBACK:{fallback_view}"
                            binds = fallback_params
                            execution_success = True
                            debug_data["sql"]["raw_sql"] = sql
                            debug_data["sql"]["parameters"] = binds
                            debug_data["rows"] = len(normalized_rows)
                            debug_data["sample_rows"] = normalized_rows[:20]
                            debug_data["timeline"]["13. Analytical Storage Fallback Concluido"] = get_timestamp()
                            logger.info(
                                "[Orchestrator] Consulta recuperada via AnalyticalStorage fallback | view=%s rows=%d",
                                fallback_view,
                                len(normalized_rows),
                            )
                            break
                    elapsed = (time.perf_counter() - start_time) * 1000
                    db_error_message = f"Erro de processamento assincrono de dados no servidor: {db_exc}"
                    res = {
                        "status": "DATABASE_ERROR",
                        "message": db_error_message,
                        "mensagem": db_error_message,
                        "resposta_direta": db_error_message,
                        "pergunta_original": pergunta,
                        "execution_time_ms": elapsed
                    }
                    return write_debug_and_return(res)

        zero_discount_ranking = self._is_zero_discount_ranking(canonical_plan, normalized_rows)
        if zero_discount_ranking:
            normalized_rows = []
            debug_data["business_rule"] = {
                "rule": "zero_discount_ranking",
                "message": "Ranking de desconto suprimido porque o maior desconto calculado foi zero.",
            }

        # ── 8. LLM Explainability (Fase de Saída) ─────────────────────
        debug_data["timeline"]["13. Explainability Iniciado"] = get_timestamp()
        from services.metadata_catalog.explainability import explainability_engine
        explanation, explain_prompt = await explainability_engine.generate_explanation(
            query=pergunta,
            plan=canonical_plan,
            dataset=normalized_rows,
            db_state=dashboard_state_override or DashboardState(chart_type=VisualizationType.TABLE),
            client=client,
            model=model
        )
        debug_data["timeline"]["13. Explainability Concluído"] = get_timestamp()
        debug_data["llm_prompt"] = explain_prompt
        if zero_discount_ranking:
            explanation.summary = "Não houve desconto registrado no período informado; por isso não há vendedor com maior desconto."
            explanation.insights = ["O desconto total calculado para o período foi R$ 0,00."]
            explanation.warnings = ["A view de vendas não possui uma coluna explícita de desconto; o valor foi derivado de quantidade vezes preço unitário menos valor faturado."]
        debug_data["llm_response"] = explanation.summary

        # ── 11. Transformer Integration & Graph Update ────────────────
        from services.data_transformer import transform_data
        from models.view_catalog import ChartType as SchemaChartType

        vis_map = {
            "TABLE": SchemaChartType.TABLE,
            "BAR": SchemaChartType.BAR,
            "LINE": SchemaChartType.LINE,
            "PIE": SchemaChartType.PIE,
            "KPI": SchemaChartType.KPI,
            "AREA": SchemaChartType.AREA,
            "SCATTER": SchemaChartType.SCATTER
        }

        v_type_str = canonical_plan.suggested_visualization.value.upper() if hasattr(canonical_plan.suggested_visualization, 'value') else str(canonical_plan.suggested_visualization).upper()
        target_chart_type = vis_map.get(v_type_str, SchemaChartType.TABLE)

        # Coerção inteligente baseada na intenção analítica do negócio
        intent_str = canonical_plan.intent.value.upper() if hasattr(canonical_plan.intent, 'value') else str(canonical_plan.intent).upper()
        if "curva abc" in pergunta.lower():
            target_chart_type = SchemaChartType.BAR
        elif intent_str == "RANKING":
            target_chart_type = SchemaChartType.BAR
        elif intent_str == "TREND":
            target_chart_type = SchemaChartType.LINE
        elif intent_str in ("KPI", "AGGREGATION") and len(normalized_rows) == 1:
            target_chart_type = SchemaChartType.KPI

        debug_data["timeline"]["14. Data Transformer Iniciado"] = get_timestamp()
        debug_data["transformer"]["input"] = normalized_rows[:50]

        # Converte o dataset para o formato Chart.js do frontend
        transformed_chart_data = transform_data(normalized_rows, target_chart_type)
        debug_data["transformer"]["output"] = transformed_chart_data
        debug_data["chart"] = {
            "type": target_chart_type.value,
            "data": transformed_chart_data
        }
        debug_data["timeline"]["15. Data Transformer Concluído"] = get_timestamp()

        elapsed = (time.perf_counter() - start_time) * 1000

        # Mapeia de volta para VisualizationType correspondente
        vis_reverse_map = {
            "TABLE": VisualizationType.TABLE,
            "BAR": VisualizationType.BAR,
            "LINE": VisualizationType.LINE,
            "PIE": VisualizationType.PIE,
            "KPI": VisualizationType.KPI_CARD,
            "KPI_CARD": VisualizationType.KPI_CARD,
            "SCATTER": VisualizationType.SCATTER
        }

        # ── 9. Conversation Graph Update & Return ─────────────────────
        db_state = DashboardState(
            chart_type=vis_reverse_map.get(target_chart_type.value.upper(), VisualizationType.TABLE),
            selected_filters={"tenant_id": tenant_id}
        )

        node_id = f"node_{uuid.uuid4().hex[:8]}"
        exec_res = ExecutionResult(
            status=ExecutionStatus.READY,
            dataset=normalized_rows,
            metadata={"sql": sql, "binds": str(binds)},
            execution_time_ms=elapsed,
            row_count=len(normalized_rows)
        )

        query_context = QueryContext(
            dataset_id=node_id,
            row_count=len(normalized_rows),
            execution_time_ms=elapsed
        )

        conv_node = ConversationNode(
            node_id=node_id,
            user_query=pergunta,
            canonical_plan=canonical_plan,
            execution_result=exec_res,
            query_context=query_context,
            dashboard_state=db_state
        )

        # Persiste o nó conversacional no grafo de sessão
        conversation_graph_manager.add_node(session_key, conv_node)

        primary_view_name = data_source_view_name
        if not primary_view_name and optimized_plan and getattr(optimized_plan, "selected_views", None):
            primary_view_name = optimized_plan.selected_views[0]
        parametros_extraidos = {str(key): str(value) for key, value in (binds or {}).items()}

        # Monta payload final
        final_payload = {
            "status": "FULL_RENDERING",
            "pergunta_original": pergunta,
            "mensagem": None,
            "resposta_direta": explanation.summary,
            "ia_justificativa": explanation.summary,
            "view_name": primary_view_name,
            "view_catalog_id": None,
            "parametros_extraidos": parametros_extraidos,
            "ia_confianca": 1.0,
            "pode_favoritar": bool(primary_view_name),
            "chart_type": target_chart_type.value,
            "chart_data": transformed_chart_data,
            "insights": explanation.insights,
            "recommendations": explanation.recommendations,
            "warnings": explanation.warnings,
            "execution_time_ms": elapsed,
            "telemetry": {
                "sql": sql,
                "timings": {"total_pipeline": elapsed}
            }
        }

        return write_debug_and_return(final_payload)

new_query_orchestrator = NewQueryOrchestrator()
