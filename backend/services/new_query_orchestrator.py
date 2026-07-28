import uuid
import time
import logging
import calendar
import re
import unicodedata
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import date, datetime, timezone, timedelta
from openai import AsyncOpenAI

from services.temporal import (
    PluralTemporalResultError,
    TemporalContext,
    TemporalFeaturePolicy,
    TemporalNormalizationGateway,
    TemporalRelation,
    default_temporal_context,
)
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
from services.financial_source_discovery import financial_source_discovery
from services.metric_registry import core_sales_metric_audit
from services.sales_value_breakdown import sales_value_breakdown
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
        from config import settings

        self.resolver = SemanticCanonicalizer()
        self.planner = MetadataResolver()
        self.optimizer = QueryOptimizer()
        self.generator = SQLGenerator()
        self.validator = SecurityValidator()
        self.temporal_gateway = TemporalNormalizationGateway(
            policy=TemporalFeaturePolicy.from_settings(settings)
        )
        self.comparison_planner_enabled = (
            settings.COMPARISON_PLANNER_V2_ENABLED
        )
        self.comparison_planner_shadow_mode = (
            settings.COMPARISON_PLANNER_V2_SHADOW_MODE
        )
        self.comparison_executor_enabled = (
            settings.COMPARISON_EXECUTOR_V2_ENABLED
        )
        self.comparison_executor_shadow_mode = (
            settings.COMPARISON_EXECUTOR_V2_SHADOW_MODE
        )

    def _erp_sales_filter_sql(self, alias: str = "", filial: Any | None = None) -> str:
        return sales_value_breakdown.commercial_filter_sql(alias, filial)

    def _erp_sales_filter_binds(self, filial: Any | None = None) -> Dict[str, Any]:
        return sales_value_breakdown.default_binds(filial)

    def _erp_sales_filter_label(self, filial: Any | None = None) -> str:
        return sales_value_breakdown.commercial_filter_label(filial)

    def _format_brl(self, value: Any) -> str:
        try:
            amount = Decimal(str(value or 0)).quantize(Decimal("0.01"))
        except Exception:
            amount = Decimal("0.00")
        raw = f"{amount:,.2f}"
        return "R$ " + raw.replace(",", "X").replace(".", ",").replace("X", ".")

    def _discount_source_is_explicit(self, source: Dict[str, Any]) -> bool:
        return str(source.get("desconto_fonte_tipo") or "") == "coluna_explicita"

    def _discount_source_observation(self, source: Dict[str, Any]) -> str:
        source_text = str(source.get("desconto_fonte_observacao") or "").strip()
        if source_text:
            return source_text
        return (
            "A view vw_vendas_lm nao possui coluna explicita de desconto; "
            "o sistema tentou derivar por quantidade vezes preco unitario menos valor faturado."
        )

    def _discount_source_warning(self, source: Dict[str, Any]) -> Optional[str]:
        if self._discount_source_is_explicit(source):
            return None
        return (
            "A view VW_VENDAS_LM nao traz uma coluna real de desconto. "
            "O valor exibido foi apenas uma derivacao por qtde_ * p_unit_ - ptotal_; "
            "com os dados atuais essa derivacao retorna zero e nao comprova que o ERP nao tenha descontos."
        )

    def _has_rb_term(self, normalized: str) -> bool:
        return any(
            term in normalized
            for term in (
                "venda rb",
                "vendas rb",
                "saida rb",
                "saidas rb",
                "rb",
            )
        )

    def _has_devolucao_term(self, normalized: str) -> bool:
        return any(term in normalized for term in ("devolucao", "devolucoes", "devolvido", "devolvida"))

    def _has_profit_term(self, normalized: str) -> bool:
        return any(term in normalized for term in ("lucro", "margem"))

    def _has_unbilled_sales_term(self, normalized: str) -> bool:
        return any(
            term in normalized
            for term in (
                "nao faturada",
                "nao faturadas",
                "nao faturado",
                "nao faturados",
                "não faturada",
                "não faturadas",
                "pendente de faturamento",
                "pendentes de faturamento",
                "a faturar",
                "sem faturar",
            )
        )

    def _is_faturamento_basis_ambiguous(self, pergunta: str) -> bool:
        normalized = self._normalize_query_text(pergunta)
        has_faturamento_term = any(
            term in normalized
            for term in ("faturamento", "vendas", "venda", "receita", "faturado", "faturados")
        )
        if not has_faturamento_term:
            return False

        has_explicit_basis = any(
            term in normalized
            for term in (
                "bruto", "bruta", "liquido", "liquida", "comercial", "ambos", "os dois", "preferencias", "preferencia", "base de valor"
            )
        )
        return not has_explicit_basis

    def _has_explicit_visualization_request(self, normalized: str) -> bool:
        explicit_patterns = [
            "grafico", "tabela", "pizza", "barra", "barras", "linha", "linhas",
            "kpi", "card", "cartao", "cartao de kpi", "destacado", "grade", "planilha",
            "baara", "baaras", "baras", "piza", "pisa", "pissa", "visualizacao",
            "colunas", "detalhada", "evolucao"
        ]
        return any(pattern in normalized for pattern in explicit_patterns)

    def _is_visualization_preference_ambiguous(self, pergunta: str) -> bool:
        normalized = self._normalize_query_text(pergunta)
        asks_to_choose = any(
            term in normalized
            for term in (
                "escolher",
                "escolha",
                "selecionar",
                "selecao",
                "configurar",
                "definir o formato",
            )
        )
        refers_to_output = any(
            term in normalized
            for term in ("dashboard", "formato", "visualizacao", "como mostrar")
        )
        concrete_format = any(
            term in normalized
            for term in (
                "grafico",
                "tabela",
                "planilha",
                "pizza",
                "barra",
                "linha",
                "kpi",
                "card",
            )
        )
        return asks_to_choose and refers_to_output and not concrete_format

    def _value_basis_from_text(self, normalized: str) -> str:
        wants_both = any(term in normalized for term in ("liquido e bruto", "bruto e liquido", "os dois", "ambos"))
        if wants_both:
            return "ambos"
        if any(term in normalized for term in ("bruto", "bruta")):
            return "bruto"
        if any(term in normalized for term in ("liquido", "liquida", "comercial")):
            return "liquido"
        return "liquido"

    def _primary_metric_for_query(self, normalized: str, *, by_discount: bool = False) -> str:
        if by_discount:
            return "desconto_total"
        if self._has_devolucao_term(normalized):
            return "devolucao"
        if self._has_rb_term(normalized):
            return "saida_rb"
        if self._value_basis_from_text(normalized) == "bruto":
            return "total_bruto"
        return "faturamento_comercial"

    def _include_operational_details(self, normalized: str) -> bool:
        return any(
            term in normalized
            for term in (
                "detalhado",
                "detalhada",
                "detalhe",
                "detalhes",
                "completo",
                "completa",
                "todos os valores",
                "todas as vendas",
                "todos os tipos",
                "rb",
                "devolucao",
                "devolucoes",
                "bonificada",
                "bonificadas",
                "transferencia",
                "transferencias",
                "remessa",
                "uso e consumo",
            )
        )

    def _include_discount_details(self, normalized: str) -> bool:
        return any(term in normalized for term in ("desconto", "descontos"))

    def _pedido_total_key_for_metric(self, metric_key: str) -> str:
        return {
            "faturamento_comercial": "pedidos_comerciais_total",
            "saida_rb": "pedidos_saida_rb_total",
            "devolucao": "pedidos_devolucao_total",
            "venda_bonificada": "pedidos_bonificados_total",
            "transferencias": "pedidos_transferencias_total",
            "outras_vendas": "pedidos_outras_vendas_total",
            "remessa_uso_consumo": "pedidos_remessa_uso_consumo_total",
            "outros_movimentos": "pedidos_outros_total",
            "total_bruto": "pedidos_total_periodo",
            "total_movimentos_view": "pedidos_movimentos_view_periodo",
        }.get(metric_key, "pedidos_total_periodo")

    def _pedido_filial_key_for_metric(self, metric_key: str) -> str:
        return {
            "faturamento_comercial": "pedidos_comerciais",
            "saida_rb": "pedidos_saida_rb",
            "devolucao": "pedidos_devolucao",
            "venda_bonificada": "pedidos_bonificados",
            "transferencias": "pedidos_transferencias",
            "outras_vendas": "pedidos_outras_vendas",
            "remessa_uso_consumo": "pedidos_remessa_uso_consumo",
            "outros_movimentos": "pedidos_outros",
            "total_bruto": "pedidos_total",
            "total_movimentos_view": "pedidos_movimentos_view",
        }.get(metric_key, "pedidos_total")

    def _metric_label(self, metric_key: str) -> str:
        if metric_key == "desconto_total":
            return "Desconto"
        return sales_value_breakdown.CATEGORY_LABELS.get(metric_key, metric_key.replace("_", " ").title())

    def _schema_chart_types_from_text(self, normalized: str, *, ranking_kind: Optional[str]) -> List[str]:
        wants_both = any(term in normalized for term in ("grafico e tabela", "tabela e grafico", "planilha e grafico", "os dois", "ambos"))

        if any(term in normalized for term in ("kpi", "card", "cartao", "cartão", "destacado")):
            return ["KPI"]
        elif any(term in normalized for term in ("pizza", "donut", "rosca", "piza", "pisa", "pissa")):
            return ["TABLE", "PIE"] if wants_both else ["PIE"]
        elif any(term in normalized for term in ("linha", "evolucao", "evolução", "linas", "lina")):
            return ["TABLE", "LINE"] if wants_both else ["LINE"]
        elif any(term in normalized for term in ("barra", "barras", "baara", "baaras", "bara", "baras", "coluna", "colunas")):
            return ["TABLE", "BAR"] if wants_both else ["BAR"]
        elif any(term in normalized for term in ("tabela", "planilha", "listagem", "grade", "detalhada")):
            return ["TABLE", "BAR"] if wants_both else ["TABLE"]
        elif "grafico" in normalized:
            return ["BAR"]

        return ["BAR"]

    def _visualization_type_for_schema(self, chart_type: str) -> VisualizationType:
        mapping = {
            "TABLE": VisualizationType.TABLE,
            "BAR": VisualizationType.BAR,
            "LINE": VisualizationType.LINE,
            "PIE": VisualizationType.PIE,
            "DONUT": VisualizationType.DONUT,
            "SCATTER": VisualizationType.SCATTER,
            "HEATMAP": VisualizationType.HEATMAP,
            "KPI": VisualizationType.KPI_CARD,
            "KPI_CARD": VisualizationType.KPI_CARD,
        }
        return mapping.get(chart_type, VisualizationType.TABLE)

    def _normalize_response_mode(self, mode: str | None) -> str:
        clean = str(mode or "analytical").strip().lower().replace("-", "_").replace(" ", "_")
        if clean in {"quick", "fast", "rapido", "rapida", "operational", "operacional", "mode_1"}:
            return "operational"
        if clean in {"executive", "executivo", "advisor", "consultor", "premium", "mode_3"}:
            return "executive"
        return "analytical"

    def _apply_response_mode(
        self,
        response_text: str,
        *,
        mode: str | None,
        row_count: int,
        warnings: List[str],
    ) -> str:
        response_mode = self._normalize_response_mode(mode)
        if response_mode == "operational":
            first_sentence = response_text.split(". ")[0].strip()
            return first_sentence + ("." if first_sentence and not first_sentence.endswith(".") else "")
        if response_mode == "executive":
            additions = [f"Leitura executiva: foram retornadas {row_count} linha(s) para auditoria."]
            if warnings:
                additions.append("Ponto de atenção: ha limitacao de fonte em pelo menos uma métrica solicitada.")
            return response_text + " " + " ".join(additions)
        return response_text

    def _core_summary_topics(self, pergunta: str) -> set[str]:
        normalized = self._normalize_query_text(pergunta)
        topics: set[str] = set()
        has_vendor_term = any(term in normalized for term in ("vendedor", "vendendor", "vendedores", "vendedora"))
        has_client_term = any(term in normalized for term in ("cliente", "clientes"))
        has_discount_term = any(term in normalized for term in ("desconto", "descontos"))
        has_rb_term = self._has_rb_term(normalized)
        has_devolucao_term = self._has_devolucao_term(normalized)
        has_unsupported_metric = self._has_profit_term(normalized) or self._has_unbilled_sales_term(normalized)
        has_ranking_signal = (
            self._has_explicit_core_metric_term(normalized)
            or bool(re.search(r"\b(?:ranking|rank|top)\b", normalized))
        )
        wants_vendor_ranking = (
            has_vendor_term
            and has_ranking_signal
            and self._wants_ranked_output(normalized, "vendedor")
        )
        wants_client_ranking = (
            has_client_term
            and has_ranking_signal
            and self._wants_ranked_output(normalized, "cliente")
        )
        wants_vendor_top = has_vendor_term and self._wants_top_output(normalized, "vendedor")
        wants_client_top = has_client_term and self._wants_top_output(normalized, "cliente")
        if (
            has_vendor_term
            and (has_rb_term or has_devolucao_term)
            and not wants_vendor_top
            and re.search(r"\b(qnt|qt|qto|quanto|quantas|vendas?|vendeu)\b", normalized)
        ):
            wants_vendor_ranking = True

        if self._has_profit_term(normalized):
            topics.add("lucro")
        if self._has_unbilled_sales_term(normalized):
            topics.add("vendas_nao_faturadas")

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
            "vendas por filial",
            "venda por filial",
            "vendas por loja",
            "venda por loja",
            "vendas por unidade",
            "venda por unidade",
        )) and not (wants_vendor_ranking or wants_client_ranking or wants_vendor_top or wants_client_top):
            topics.add("faturamento")
        if has_rb_term and not (wants_vendor_ranking or wants_client_ranking or wants_vendor_top or wants_client_top):
            topics.add("rb")
        if has_devolucao_term and not (wants_vendor_ranking or wants_client_ranking or wants_vendor_top or wants_client_top):
            topics.add("devolucao")
        if any(term in normalized for term in ("ticket", "tiket", "tiquete", "valor medio")):
            topics.add("ticket")
        if has_discount_term and not (wants_vendor_ranking or wants_client_ranking or wants_vendor_top or wants_client_top):
            topics.add("desconto")
        if any(term in normalized for term in (
            "ver documentos",
            "detalhe os pedidos",
            "detalhar os pedidos",
            "pedidos e notas",
            "notas que compoem",
            "documentos que compoem",
            "rastreabilidade",
        )):
            topics.add("documentos")

        if wants_vendor_ranking:
            if has_discount_term:
                topics.add("ranking_vendedores_desconto")
            elif has_devolucao_term and not has_rb_term:
                topics.add("ranking_vendedores_devolucao")
            elif has_rb_term:
                topics.add("ranking_vendedores_rb")
            elif not has_unsupported_metric:
                topics.add("ranking_vendedores")
        elif wants_vendor_top:
            if has_discount_term:
                topics.add("top_vendedor_desconto")
            elif has_devolucao_term and not has_rb_term:
                topics.add("top_vendedor_devolucao")
            elif has_rb_term:
                topics.add("top_vendedor_rb")
            elif not has_unsupported_metric:
                topics.add("top_vendedor")

        if wants_client_ranking:
            topics.add("ranking_clientes")
        elif wants_client_top:
            topics.add("top_cliente")

        # Tópicos de produtos mais vendidos
        has_product_term = any(term in normalized for term in ("produto", "produtos", "item", "itens", "mercadoria", "sku"))
        has_vendido_term = any(term in normalized for term in ("vendido", "vendidos", "vendida", "vendidas", "vendidoa", "mais vendeu", "mais popular", "top"))
        
        if (has_product_term and has_vendido_term) or ("produtos mais" in normalized) or ("mais vendido" in normalized) or ("mais vendidoa" in normalized):
            topics.add("produto_mais_vendido")

        # Tópico de estoque por produto
        if any(term in normalized for term in ("estoque", "saldo estoque", "posicao estoque", "nivel estoque")):
            topics.add("estoque_produto")
            if has_product_term or "produto" in normalized:
                topics.add("produto_mais_vendido")

        # Tópico de financeiro em aberto
        if any(term in normalized for term in (
            "financeiro", "financeiros", "parcela", "parcelas", "inadimplencia", "inadimplente",
            "inadimplentes", "titulo", "titulos", "contas a receber", "em aberto", "vencido",
            "vencidos", "devendo", "devedor", "devedores",
        )):
            topics.add("financeiro_aberto")

        return topics

    def _ranking_limit_from_text(self, normalized: str) -> Optional[int]:
        top_match = re.search(r"\btop\s*(\d{1,3})\b", normalized)
        if top_match:
            return max(1, min(int(top_match.group(1)), 500))

        leading_match = re.search(
            r"\b(\d{1,3})\s+(?:primeiros|primeiras|maiores|melhores|principais)\b",
            normalized,
        )
        if leading_match:
            return max(1, min(int(leading_match.group(1)), 500))

        return None

    def _wants_unbounded_ranking(self, normalized: str) -> bool:
        return any(
            term in normalized
            for term in (
                "todos",
                "todas",
                "com todos",
                "com todas",
                "sem limite",
                "completo",
                "completa",
                "lista completa",
            )
        )

    def _ranking_limit_for_dimension(self, normalized: str, dimension: str) -> Optional[int]:
        explicit_limit = self._ranking_limit_from_text(normalized)
        if explicit_limit is not None:
            return explicit_limit
        if self._wants_unbounded_ranking(normalized):
            return None
        if dimension == "cliente":
            return 50
        return None

    def _filial_from_text(self, pergunta: str) -> Optional[str]:
        normalized = self._normalize_query_text(pergunta)
        patterns = (
            r"\b(?:filial|loja|unidade)\s*(?:n(?:o|umero)?\.?\s*)?[:#-]?\s*(\d{1,3})\b",
            r"\b(?:da|de|na|no)\s+(?:filial|loja|unidade)\s*(\d{1,3})\b",
        )
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if not match:
                continue
            return sales_value_breakdown.normalize_filial(match.group(1))
        return None

    def _filial_scope_label(self, filial: Optional[str]) -> str:
        return f"filial {filial}" if filial else "todas as filiais"

    def _wants_ranked_output(self, normalized: str, dimension: str) -> bool:
        plural = f"{dimension}es" if dimension == "vendedor" else f"{dimension}s"
        if self._ranking_limit_from_text(normalized) is not None:
            return True
        if any(term in normalized for term in (
            "ranking",
            "rank",
            "lista",
            "listar",
            "todos",
            "todas",
            "cada",
            "completo",
            "completa",
            f"por {dimension}",
            f"por {plural}",
            f"{plural} por",
            f"todos os {plural}",
            f"todas as {plural}",
            f"todos {plural}",
            f"{plural} que mais",
        )):
            return True
        if "top" in normalized and plural in normalized:
            return True
        return False

    def _wants_top_output(self, normalized: str, dimension: str) -> bool:
        if self._wants_ranked_output(normalized, dimension):
            return False
        if any(term in normalized for term in (
            "mais vendeu",
            "maior venda",
            "vendeu mais",
            "maior desconto",
            "mais desconto",
            "lider",
            "campeao",
            f"melhor {dimension}",
            f"qual {dimension}",
            f"quem foi o {dimension}",
            f"quem e o {dimension}",
            f"top {dimension}",
            "primeiro lugar",
            "1 lugar",
        )):
            return True
        if dimension == "cliente" and any(term in normalized for term in ("mais comprou", "mais compraram", "maior cliente", "maior compra")):
            return True
        return False

    def _has_explicit_core_metric_term(self, normalized: str) -> bool:
        metric_terms = (
            "faturamento",
            "receita",
            "ticket",
            "desconto",
            "rb",
            "saida rb",
            "devolucao",
            "devolucoes",
            "bonificada",
            "transferencia",
            "lucro",
            "margem",
            "nao faturada",
            "nao faturadas",
            "nao faturado",
            "nao faturados",
        )
        if any(term in normalized for term in metric_terms):
            return True
        return bool(re.search(r"\bvendas?\b", normalized))

    def _looks_like_metric_followup(self, normalized: str) -> bool:
        if any(
            term in normalized
            for term in (
                "isso",
                "esse dado",
                "essa informacao",
                "esse valor",
                "esse ranking",
                "essa lista",
                "mesmo dado",
                "mesma informacao",
                "mesmo",
                "mesma",
                "agora",
                "separa",
                "separar",
                "detalha",
                "detalhe",
            )
        ):
            return True
        return bool(
            re.fullmatch(
                r"(?:e\s+)?(?:por\s+)?(?:vendedor|vendedores|cliente|clientes|filial|filiais|loja|lojas|unidade|unidades)",
                normalized.strip(),
            )
        )

    def _has_explicit_dimension_term(self, normalized: str) -> bool:
        return any(
            term in normalized
            for term in (
                "vendedor",
                "vendedores",
                "vendedora",
                "cliente",
                "clientes",
                "filial",
                "filiais",
                "loja",
                "unidade",
            )
        )

    def _dimension_suffix_from_context_text(self, content: str) -> str:
        normalized = self._normalize_query_text(content)
        if any(term in normalized for term in ("vendedor", "vendedores", "vendedora")):
            return " por vendedor"
        if any(term in normalized for term in ("cliente", "clientes")):
            return " por cliente"
        if any(term in normalized for term in ("filial", "filiais", "loja", "unidade")):
            return " por filial"
        return ""

    def _metric_suffix_from_context_text(self, content: str) -> str:
        normalized = self._normalize_query_text(content)
        if self._has_unbilled_sales_term(normalized):
            return " vendas ainda nao faturadas"
        if self._has_profit_term(normalized):
            return " lucro"
        if self._has_devolucao_term(normalized):
            return " devolucao"
        if self._has_rb_term(normalized):
            return " vendas RB"
        if "desconto" in normalized:
            return " desconto"
        if any(term in normalized for term in ("ticket", "tiket", "tiquete")):
            return " ticket medio"
        if any(term in normalized for term in ("faturamento", "receita")) or re.search(r"\bvendas?\b", normalized):
            return " faturamento"
        return ""

    def _question_with_inherited_metric(
        self,
        pergunta: str,
        history: Optional[List[Dict[str, str]]],
    ) -> str:
        normalized = self._normalize_query_text(pergunta)
        has_explicit_metric = self._has_explicit_core_metric_term(normalized)
        has_explicit_dimension = self._has_explicit_dimension_term(normalized)
        if has_explicit_metric and has_explicit_dimension:
            return pergunta
        if not self._looks_like_metric_followup(normalized):
            return pergunta

        metric_suffix = ""
        dimension_suffix = ""
        for message in reversed(history or []):
            content = str((message or {}).get("content") or "")
            if not metric_suffix and not has_explicit_metric:
                metric_suffix = self._metric_suffix_from_context_text(content)
            if not dimension_suffix and not has_explicit_dimension:
                dimension_suffix = self._dimension_suffix_from_context_text(content)
            if (metric_suffix or has_explicit_metric) and (dimension_suffix or has_explicit_dimension):
                break

        contextual_question = pergunta
        if dimension_suffix:
            contextual_question = f"{contextual_question}{dimension_suffix}"
        if metric_suffix:
            contextual_question = f"{contextual_question} de{metric_suffix}"
        return contextual_question

    def _is_core_summary_query(self, pergunta: str) -> bool:
        topics = self._core_summary_topics(pergunta)
        if not topics:
            return False
        # Se não há período, tentaremos assumir o mês atual — não bloqueamos
        if len(topics) >= 2:
            return True

        normalized = self._normalize_query_text(pergunta)
        single_topic = next(iter(topics))
        if single_topic in {
            "faturamento",
            "ticket",
            "desconto",
            "rb",
            "devolucao",
            "lucro",
            "vendas_nao_faturadas",
            "top_vendedor",
            "top_vendedor_desconto",
            "top_vendedor_rb",
            "top_vendedor_devolucao",
            "ranking_vendedores",
            "ranking_vendedores_desconto",
            "ranking_vendedores_rb",
            "ranking_vendedores_devolucao",
            "ranking_clientes",
            "produto_mais_vendido",
            "estoque_produto",
            "financeiro_aberto",
        }:
            return True
        if single_topic == "top_cliente":
            return "ranking" not in normalized
        return False


    def _question_with_inherited_period(
        self,
        pergunta: str,
        history: Optional[List[Dict[str, str]]],
        temporal_context: TemporalContext | None = None,
    ) -> str:
        contextual_question = self._question_with_inherited_metric(pergunta, history)
        if self._month_ranges_from_text(contextual_question, temporal_context):
            return contextual_question
        if not self._core_summary_topics(contextual_question):
            return contextual_question

        for message in reversed(history or []):
            content = str((message or {}).get("content") or "")
            periods = self._month_ranges_from_text(content, temporal_context)
            if len(periods) != 1:
                continue
            period = periods[0]
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
            return f"{contextual_question} em {inherited}"

        return contextual_question

    def _question_with_inherited_context(
        self,
        pergunta: str,
        history: Optional[List[Dict[str, str]]],
        temporal_context: TemporalContext | None = None,
    ) -> str:
        contextual_question = self._question_with_inherited_period(
            pergunta,
            history,
            temporal_context,
        )
        normalized = self._normalize_query_text(contextual_question)
        if self._filial_from_text(contextual_question) is not None:
            return contextual_question
        if any(term in normalized for term in ("todas as filiais", "todas filiais", "todas as lojas", "todas lojas")):
            return contextual_question
        if not self._looks_like_metric_followup(normalized):
            return contextual_question

        for message in reversed(history or []):
            if str((message or {}).get("role") or "") != "user":
                continue
            inherited_filial = self._filial_from_text(str((message or {}).get("content") or ""))
            if inherited_filial is not None:
                return f"{contextual_question} na filial {inherited_filial}"
        return contextual_question

    def _decimal_value(self, value: Any) -> Decimal:
        try:
            return Decimal(str(value or 0))
        except Exception:
            return Decimal("0")

    def _format_breakdown_ranking_row(
        self,
        row: Dict[str, Any],
        dimension_key: str,
        *,
        primary_key: str,
    ) -> Dict[str, Any]:
        ranking_primary_key = f"ranking_{primary_key}"
        primary_value = self._decimal_value(row.get(ranking_primary_key, row.get(primary_key)))
        filial_value = self._decimal_value(row.get(primary_key))
        ranking_discount_total = self._decimal_value(row.get("ranking_desconto_total", row.get("desconto_total")))
        filial_discount_total = self._decimal_value(row.get("desconto_total"))
        filial = str(row.get("filial") or "Sem filial")
        formatted: Dict[str, Any] = {
            "posicao": int(row.get("posicao") or 0),
            dimension_key: str(row.get(dimension_key) or "Nao identificado"),
            "filial": filial,
            "valor_total": float(primary_value),
            "valor_formatado": self._format_brl(primary_value),
            "valor_filial": float(filial_value),
            "valor_filial_formatado": self._format_brl(filial_value),
        }

        for key in sales_value_breakdown.CATEGORY_VALUE_KEYS:
            formatted[key] = float(self._decimal_value(row.get(key)))
            formatted[f"{key}_total"] = float(self._decimal_value(row.get(f"ranking_{key}", row.get(key))))

        formatted.update(
            {
                "total_bruto": float(self._decimal_value(row.get("total_bruto"))),
                "total_movimentos_view": float(self._decimal_value(row.get("total_movimentos_view"))),
                "faturamento_comercial_total": float(self._decimal_value(row.get("ranking_faturamento_comercial"))),
                "total_bruto_total": float(self._decimal_value(row.get("ranking_total_bruto"))),
                "total_movimentos_view_total": float(self._decimal_value(row.get("ranking_total_movimentos_view"))),
                "pedidos_comerciais": int(row.get("pedidos_comerciais") or 0),
                "pedidos_saida_rb": int(row.get("pedidos_saida_rb") or 0),
                "pedidos_devolucao": int(row.get("pedidos_devolucao") or 0),
                "pedidos_bonificados": int(row.get("pedidos_bonificados") or 0),
                "pedidos_transferencias": int(row.get("pedidos_transferencias") or 0),
                "pedidos_outras_vendas": int(row.get("pedidos_outras_vendas") or 0),
                "pedidos_remessa_uso_consumo": int(row.get("pedidos_remessa_uso_consumo") or 0),
                "pedidos_outros": int(row.get("pedidos_outros") or 0),
                "pedidos_total": int(row.get("pedidos_total") or 0),
                "pedidos_movimentos_view": int(row.get("pedidos_movimentos_view") or 0),
                "pedidos_comerciais_total": int(row.get("ranking_pedidos_comerciais") or 0),
                "pedidos_saida_rb_total": int(row.get("ranking_pedidos_saida_rb") or 0),
                "pedidos_devolucao_total": int(row.get("ranking_pedidos_devolucao") or 0),
                "pedidos_bonificados_total": int(row.get("ranking_pedidos_bonificados") or 0),
                "pedidos_transferencias_total": int(row.get("ranking_pedidos_transferencias") or 0),
                "pedidos_outras_vendas_total": int(row.get("ranking_pedidos_outras_vendas") or 0),
                "pedidos_remessa_uso_consumo_total": int(row.get("ranking_pedidos_remessa_uso_consumo") or 0),
                "pedidos_outros_total": int(row.get("ranking_pedidos_outros") or 0),
                "pedidos_total_periodo": int(row.get("ranking_pedidos_total") or 0),
                "pedidos_movimentos_view_periodo": int(row.get("ranking_pedidos_movimentos_view") or 0),
                "desconto_comercial": float(self._decimal_value(row.get("desconto_comercial"))),
                "desconto_total": float(filial_discount_total),
                "desconto_total_periodo": float(ranking_discount_total),
                "desconto_formatado": self._format_brl(ranking_discount_total),
                "desconto_fonte_tipo": str(row.get("desconto_fonte_tipo") or "derivado_sem_coluna_explicita"),
                "desconto_fonte_coluna": row.get("desconto_fonte_coluna"),
                "desconto_fonte_confianca": str(row.get("desconto_fonte_confianca") or "baixa"),
                "desconto_fonte_observacao": self._discount_source_observation(row),
            }
        )
        return formatted

    def _sorted_filial_labels(self, labels: set[str]) -> List[str]:
        def sort_key(label: str) -> tuple[int, str]:
            try:
                return int(label), label
            except ValueError:
                return 999999, label

        return sorted(labels, key=sort_key)

    def _filial_column_suffix(self, filial: Any) -> str:
        normalized = self._normalize_query_text(str(filial or "sem_filial"))
        suffix = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
        return suffix or "sem_filial"

    def _pivot_ranking_rows_by_dimension(
        self,
        rows: List[Dict[str, Any]],
        dimension_key: str,
        *,
        primary_key: str,
        include_operational_details: bool = False,
        include_discount_details: bool = False,
        include_count_details: bool = True,
    ) -> List[Dict[str, Any]]:
        if not rows:
            return []

        filial_labels = self._sorted_filial_labels({str(row.get("filial") or "Sem filial") for row in rows})
        grouped: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            dimension_value = str(row.get(dimension_key) or "Nao identificado")
            group = grouped.setdefault(
                dimension_value,
                {
                    "posicao": int(row.get("posicao") or 0),
                    "rows": [],
                },
            )
            group["posicao"] = min(group["posicao"] or int(row.get("posicao") or 0), int(row.get("posicao") or 0))
            group["rows"].append(row)

        metric_keys: tuple[str, ...] = (primary_key,) if primary_key != "desconto_total" else ("desconto_total",)
        if include_operational_details:
            metric_keys = tuple(dict.fromkeys((*metric_keys, *sales_value_breakdown.CATEGORY_VALUE_KEYS, "total_bruto", "total_movimentos_view")))
        if include_discount_details:
            metric_keys = tuple(dict.fromkeys((*metric_keys, "desconto_comercial", "desconto_total")))
        count_keys: tuple[str, ...] = ()
        if include_count_details:
            count_keys = tuple(dict.fromkeys((self._pedido_filial_key_for_metric(primary_key), "pedidos_total")))
        pivoted_rows: List[Dict[str, Any]] = []

        for dimension_value, group in sorted(grouped.items(), key=lambda item: (item[1]["posicao"], item[0])):
            branch_rows = list(group["rows"])
            representative = branch_rows[0]
            by_filial = {str(row.get("filial") or "Sem filial"): row for row in branch_rows}
            filiais_com_movimento = [filial for filial in filial_labels if filial in by_filial]

            output: Dict[str, Any] = {
                "posicao": int(group["posicao"] or 0),
                dimension_key: dimension_value,
                "filiais_com_movimento": ", ".join(filiais_com_movimento),
            }

            for filial_label in filial_labels:
                branch = by_filial.get(filial_label, {})
                prefix = f"filial_{self._filial_column_suffix(filial_label)}"
                for metric_key in metric_keys:
                    output[f"{prefix}_{metric_key}"] = float(self._decimal_value(branch.get(metric_key)))
                for count_key in count_keys:
                    output[f"{prefix}_{count_key}"] = int(branch.get(count_key) or 0)

            fallback_faturamento = sum((self._decimal_value(row.get("faturamento_comercial")) for row in branch_rows), Decimal("0"))
            fallback_total_bruto = sum((self._decimal_value(row.get("total_bruto")) for row in branch_rows), Decimal("0"))
            fallback_total_movimentos = sum((self._decimal_value(row.get("total_movimentos_view")) for row in branch_rows), Decimal("0"))
            fallback_desconto_comercial = sum((self._decimal_value(row.get("desconto_comercial")) for row in branch_rows), Decimal("0"))
            fallback_desconto_total = sum((self._decimal_value(row.get("desconto_total")) for row in branch_rows), Decimal("0"))
            fallback_primary = sum((self._decimal_value(row.get(primary_key)) for row in branch_rows), Decimal("0"))

            faturamento_total = self._decimal_value(representative.get("faturamento_comercial_total")) or fallback_faturamento
            total_bruto_total = self._decimal_value(representative.get("total_bruto_total")) or fallback_total_bruto
            total_movimentos_view_total = self._decimal_value(representative.get("total_movimentos_view_total")) or fallback_total_movimentos
            desconto_comercial_total = self._decimal_value(representative.get("ranking_desconto_comercial")) or fallback_desconto_comercial
            desconto_total_periodo = self._decimal_value(representative.get("desconto_total_periodo")) or fallback_desconto_total
            pedidos_comerciais_total = int(representative.get("pedidos_comerciais_total") or sum(int(row.get("pedidos_comerciais") or 0) for row in branch_rows))
            pedidos_total_periodo = int(representative.get("pedidos_total_periodo") or sum(int(row.get("pedidos_total") or 0) for row in branch_rows))
            pedidos_movimentos_view_periodo = int(
                representative.get("pedidos_movimentos_view_periodo")
                or sum(int(row.get("pedidos_movimentos_view") or 0) for row in branch_rows)
            )
            primary_total = (
                desconto_total_periodo
                if primary_key == "desconto_total"
                else self._decimal_value(representative.get(f"{primary_key}_total")) or fallback_primary
            )
            primary_pedidos_total_key = self._pedido_total_key_for_metric(primary_key)
            primary_pedidos_total = int(
                representative.get(primary_pedidos_total_key)
                or sum(int(row.get(self._pedido_filial_key_for_metric(primary_key)) or 0) for row in branch_rows)
            )

            output["valor_total"] = float(primary_total)
            output["valor_total_formatado"] = self._format_brl(primary_total)
            output[primary_pedidos_total_key] = primary_pedidos_total
            if include_operational_details:
                output.update(
                    {
                        "faturamento_comercial_total": float(faturamento_total),
                        "total_bruto_total": float(total_bruto_total),
                        "total_movimentos_view_total": float(total_movimentos_view_total),
                        "pedidos_comerciais_total": pedidos_comerciais_total,
                        "pedidos_total_periodo": pedidos_total_periodo,
                        "pedidos_movimentos_view_periodo": pedidos_movimentos_view_periodo,
                    }
                )
            if include_discount_details:
                output.update(
                    {
                        "desconto_comercial_total": float(desconto_comercial_total),
                        "desconto_total_periodo": float(desconto_total_periodo),
                        "desconto_fonte_tipo": str(representative.get("desconto_fonte_tipo") or "derivado_sem_coluna_explicita"),
                        "desconto_fonte_coluna": representative.get("desconto_fonte_coluna"),
                        "desconto_fonte_confianca": str(representative.get("desconto_fonte_confianca") or "baixa"),
                        "desconto_fonte_observacao": self._discount_source_observation(representative),
                    }
                )
            pivoted_rows.append(output)

        return pivoted_rows

    def _period_value_breakdown_rows(
        self,
        totals: Dict[str, Any],
        filial_totals: List[Dict[str, Any]],
        *,
        filial: Optional[str],
        value_basis: str = "liquido",
        include_operational_details: bool = False,
    ) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        value_basis = value_basis if value_basis in {"liquido", "bruto", "ambos"} else "liquido"

        def make_row(source: Dict[str, Any], filial_label: str, tipo_linha: str) -> Dict[str, Any]:
            faturamento = self._decimal_value(source.get("faturamento_comercial"))
            total_bruto = self._decimal_value(source.get("total_bruto"))
            if value_basis == "bruto":
                valor_principal = total_bruto
                pedidos_principais = int(source.get("pedidos_total") or 0)
                tipo_valor = "Total bruto sem transferencias"
            else:
                valor_principal = faturamento
                pedidos_principais = int(source.get("pedidos_comerciais") or 0)
                tipo_valor = "Faturamento comercial"
            row: Dict[str, Any] = {
                "filial": filial_label,
                "tipo_linha": tipo_linha,
                "tipo_valor": tipo_valor if value_basis != "ambos" else "Faturamento comercial e total bruto sem transferencias",
                "valor": float(valor_principal),
                "valor_formatado": self._format_brl(valor_principal),
                "pedidos": pedidos_principais,
                "pedidos_comerciais": int(source.get("pedidos_comerciais") or 0),
                "pedidos_total": int(source.get("pedidos_total") or 0),
                "observacao": self._erp_sales_filter_label(filial) if tipo_linha == "Total geral" else "Valores separados por filial; transferencias ficam em coluna propria e fora do total bruto.",
            }
            if value_basis in {"liquido", "ambos"}:
                row["faturamento_comercial"] = float(faturamento)
            if value_basis in {"bruto", "ambos"}:
                row["total_bruto"] = float(total_bruto)
            if include_operational_details:
                for key in sales_value_breakdown.CATEGORY_VALUE_KEYS:
                    row[key] = float(self._decimal_value(source.get(key)))
                row["total_bruto"] = float(total_bruto)
                row["total_movimentos_view"] = float(self._decimal_value(source.get("total_movimentos_view")))
            return row

        for filial_row in filial_totals:
            filial_label = str(filial_row.get("filial") or "Sem filial")
            rows.append(make_row(filial_row, filial_label, "Filial"))
        if filial is None:
            rows.append(make_row(totals, "Total geral", "Total geral"))
        return rows

    def _period_category_breakdown_rows(
        self,
        totals: Dict[str, Any],
        filial_totals: List[Dict[str, Any]],
        *,
        filial: Optional[str],
        category_key: str,
    ) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        pedido_key = self._pedido_filial_key_for_metric(category_key)
        label = self._metric_label(category_key)
        for filial_label, tipo_linha, source in self._period_source_rows(totals, filial_totals, filial=filial):
            value = self._decimal_value(source.get(category_key))
            rows.append(
                {
                    "indicador": label,
                    "filial": filial_label,
                    "tipo_linha": tipo_linha,
                    "tipo_valor": category_key,
                    "valor": float(value),
                    "valor_formatado": self._format_brl(value),
                    "pedidos": int(source.get(pedido_key) or 0),
                    "observacao": f"{label} separado por filial.",
                }
            )
        return rows

    def _period_source_rows(
        self,
        totals: Dict[str, Any],
        filial_totals: List[Dict[str, Any]],
        *,
        filial: Optional[str],
    ) -> List[tuple[str, str, Dict[str, Any]]]:
        rows: List[tuple[str, str, Dict[str, Any]]] = []
        for filial_row in filial_totals:
            rows.append((str(filial_row.get("filial") or "Sem filial"), "Filial", filial_row))
        if filial is None:
            rows.append(("Total geral", "Total geral", totals))
        return rows

    def _period_ticket_breakdown_rows(
        self,
        totals: Dict[str, Any],
        filial_totals: List[Dict[str, Any]],
        *,
        filial: Optional[str],
    ) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for filial_label, tipo_linha, source in self._period_source_rows(totals, filial_totals, filial=filial):
            faturamento = self._decimal_value(source.get("faturamento_comercial"))
            total_bruto = self._decimal_value(source.get("total_bruto"))
            pedidos_comerciais = int(source.get("pedidos_comerciais") or 0)
            pedidos_total = int(source.get("pedidos_total") or 0)
            ticket_comercial = faturamento / Decimal(pedidos_comerciais) if pedidos_comerciais else Decimal("0")
            ticket_bruto = total_bruto / Decimal(pedidos_total) if pedidos_total else Decimal("0")
            rows.append(
                {
                    "indicador": "Ticket medio",
                    "filial": filial_label,
                    "tipo_linha": tipo_linha,
                    "ticket_medio_comercial": float(ticket_comercial),
                    "ticket_medio_comercial_formatado": self._format_brl(ticket_comercial),
                    "ticket_medio_bruto": float(ticket_bruto),
                    "ticket_medio_bruto_formatado": self._format_brl(ticket_bruto),
                    "faturamento_comercial": float(faturamento),
                    "total_bruto": float(total_bruto),
                    "pedidos_comerciais": pedidos_comerciais,
                    "pedidos_total": pedidos_total,
                    "observacao": "Ticket comercial usa tipos 2/61; ticket bruto exclui transferencias e mantem transferencias em coluna propria.",
                }
            )
        return rows

    def _period_discount_breakdown_rows(
        self,
        totals: Dict[str, Any],
        filial_totals: List[Dict[str, Any]],
        *,
        filial: Optional[str],
    ) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for filial_label, tipo_linha, source in self._period_source_rows(totals, filial_totals, filial=filial):
            desconto_comercial = self._decimal_value(source.get("desconto_comercial"))
            desconto_total = self._decimal_value(source.get("desconto_total"))
            pedidos_comerciais = int(source.get("pedidos_comerciais") or 0)
            pedidos_total = int(source.get("pedidos_total") or 0)
            desconto_medio_comercial = desconto_comercial / Decimal(pedidos_comerciais) if pedidos_comerciais else Decimal("0")
            desconto_medio_total = desconto_total / Decimal(pedidos_total) if pedidos_total else Decimal("0")
            rows.append(
                {
                    "indicador": "Desconto",
                    "filial": filial_label,
                    "tipo_linha": tipo_linha,
                    "desconto_comercial": float(desconto_comercial),
                    "desconto_comercial_formatado": self._format_brl(desconto_comercial),
                    "desconto_medio_comercial": float(desconto_medio_comercial),
                    "desconto_medio_comercial_formatado": self._format_brl(desconto_medio_comercial),
                    "desconto_total": float(desconto_total),
                    "desconto_total_formatado": self._format_brl(desconto_total),
                    "desconto_medio_total": float(desconto_medio_total),
                    "desconto_medio_total_formatado": self._format_brl(desconto_medio_total),
                    "pedidos_comerciais": pedidos_comerciais,
                    "pedidos_total": pedidos_total,
                    "desconto_fonte_tipo": str(source.get("desconto_fonte_tipo") or "derivado_sem_coluna_explicita"),
                    "desconto_fonte_coluna": source.get("desconto_fonte_coluna"),
                    "desconto_fonte_confianca": str(source.get("desconto_fonte_confianca") or "baixa"),
                    "desconto_fonte_observacao": self._discount_source_observation(source),
                    "observacao": self._discount_source_observation(source),
                }
            )
        return rows

    def _decorate_rows_with_indicator(self, rows: List[Dict[str, Any]], indicador: str) -> List[Dict[str, Any]]:
        return [
            {
                "indicador": indicador,
                **row,
                "observacao": "Valores separados por filial e tipo de movimento.",
            }
            for row in rows
        ]

    def _distinct_count(self, rows: List[Dict[str, Any]], key: str) -> int:
        return len({str(row.get(key) or "") for row in rows if row.get(key)})

    def _scope_suffix(self, filial: Optional[str]) -> str:
        return f" na filial {filial}" if filial else " em todas as filiais"

    async def _fetch_vendor_ranking(
        self,
        session: Any,
        binds: Dict[str, Any],
        *,
        limit: Optional[int],
        by_discount: bool = False,
        primary_key: str = "faturamento_comercial",
        include_operational_details: bool = False,
        include_discount_details: bool = False,
        filial: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        ranking_value_key = "faturamento_comercial" if by_discount else primary_key
        detailed_rows = await sales_value_breakdown.fetch_vendor_ranking(
            session,
            binds,
            limit=limit,
            by_discount=by_discount,
            ranking_value_key=ranking_value_key,
            filial=filial,
        )
        primary_key = "desconto_total" if by_discount else primary_key
        branch_rows = [
            self._format_breakdown_ranking_row(row, "vendedor", primary_key=primary_key)
            for row in detailed_rows
        ]
        return self._pivot_ranking_rows_by_dimension(
            branch_rows,
            "vendedor",
            primary_key=primary_key,
            include_operational_details=include_operational_details,
            include_discount_details=include_discount_details or by_discount,
        )

    async def _fetch_client_ranking(
        self,
        session: Any,
        binds: Dict[str, Any],
        *,
        limit: Optional[int],
        primary_key: str = "faturamento_comercial",
        include_operational_details: bool = False,
        include_discount_details: bool = False,
        filial: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        detailed_rows = await sales_value_breakdown.fetch_client_ranking(
            session,
            binds,
            limit=limit,
            ranking_value_key=primary_key,
            filial=filial,
        )
        branch_rows = [
            self._format_breakdown_ranking_row(row, "cliente", primary_key=primary_key)
            for row in detailed_rows
        ]
        return self._pivot_ranking_rows_by_dimension(
            branch_rows,
            "cliente",
            primary_key=primary_key,
            include_operational_details=include_operational_details,
            include_discount_details=include_discount_details,
        )


    async def _execute_core_summary_query(
        self,
        pergunta: str,
        tenant_id: str,
        session_key: str,
        trace_id: uuid.UUID,
        start_time: float,
        debug_data: Dict[str, Any],
        conversation_graph_manager: Any,
        mode: str = "analytical",
        temporal_context: TemporalContext | None = None,
    ) -> Dict[str, Any]:
        _periods_from_text = self._month_ranges_from_text(pergunta, temporal_context)
        if len(_periods_from_text) > 1:
            elapsed = (time.perf_counter() - start_time) * 1000
            return {
                "status": "AMBIGUOUS",
                "goal": pergunta,
                "ambiguities": [
                    "Comparar os periodos informados",
                    "Analisar os periodos como lista independente",
                ],
                "missing_information": ["operacao_temporal"],
                "resposta_direta": (
                    "Reconheci varios periodos, mas este executor singular nao pode "
                    "escolher um deles sem perder informacao."
                ),
                "pergunta_original": pergunta,
                "execution_time_ms": elapsed,
            }
        _period_from_text = _periods_from_text[0] if _periods_from_text else None
        if _period_from_text is None:
            # Sem período explícito: assume o mês atual como padrão
            current_ranges = self._month_ranges_from_text("mes atual", temporal_context)
            if not current_ranges:
                raise ValueError("Temporal normalizer did not resolve the current month")
            _period_from_text = current_ranges[0]
            logger.info("[Orchestrator] Período não especificado — assumindo mês atual: %s a %s", *_period_from_text)
        start_date_raw, end_date_raw = _period_from_text
        start_date = date.fromisoformat(start_date_raw)
        end_date = date.fromisoformat(end_date_raw)
        topics = self._core_summary_topics(pergunta)
        normalized_query = self._normalize_query_text(pergunta)
        vendor_ranking_limit = self._ranking_limit_for_dimension(normalized_query, "vendedor")
        client_ranking_limit = self._ranking_limit_for_dimension(normalized_query, "cliente")
        selected_filial = self._filial_from_text(pergunta)
        scope_text = self._scope_suffix(selected_filial)
        value_basis = self._value_basis_from_text(normalized_query)
        include_operational_details = self._include_operational_details(normalized_query)
        include_discount_details = self._include_discount_details(normalized_query)
        primary_sales_key = self._primary_metric_for_query(normalized_query)
        unsupported_warnings: List[str] = []
        financial_source_report: Dict[str, Any] | None = None

        summary_rows: List[Dict[str, Any]] = []
        binds = {
            "start_date": start_date,
            "end_date": end_date,
            "end_exclusive": end_date + timedelta(days=1),
            **self._erp_sales_filter_binds(selected_filial),
        }
        ranking_rows: List[Dict[str, Any]] = []
        document_rows: List[Dict[str, Any]] = []
        ranking_kind: Optional[str] = None

        async with get_db_context() as session:
            period_totals = await sales_value_breakdown.fetch_period_totals(
                session,
                binds,
                filial=selected_filial,
            )
            period_filial_totals = await sales_value_breakdown.fetch_period_totals_by_filial(
                session,
                binds,
                filial=selected_filial,
            )
            if "documentos" in topics:
                document_rows = await sales_value_breakdown.fetch_document_details(
                    session,
                    binds,
                    filial=selected_filial,
                    category_key=primary_sales_key,
                    limit=500,
                )
            if "lucro" in topics or "vendas_nao_faturadas" in topics:
                try:
                    financial_source_report = await financial_source_discovery.discover_postgres(session)
                except Exception as exc:
                    financial_source_report = {
                        "version": "discovery_failed",
                        "error": {"type": type(exc).__name__, "message": str(exc)},
                    }
                if "lucro" in topics:
                    unsupported_warnings.append(
                        financial_source_discovery.source_warning(financial_source_report, "lucro")
                    )
                if "vendas_nao_faturadas" in topics:
                    unsupported_warnings.append(
                        financial_source_discovery.source_warning(financial_source_report, "vendas_nao_faturadas")
                    )
            faturamento_total = self._decimal_value(period_totals.get("faturamento_comercial"))
            total_bruto = self._decimal_value(period_totals.get("total_bruto"))
            pedidos = int(period_totals.get("pedidos_comerciais") or 0)
            pedidos_total = int(period_totals.get("pedidos_total") or 0)
            desconto_total = self._decimal_value(period_totals.get("desconto_comercial"))
            desconto_total_bruto = self._decimal_value(period_totals.get("desconto_total"))
            ticket_medio = faturamento_total / Decimal(pedidos) if pedidos else Decimal("0")
            ticket_medio_bruto = total_bruto / Decimal(pedidos_total) if pedidos_total else Decimal("0")
            desconto_medio = desconto_total / Decimal(pedidos) if pedidos else Decimal("0")
            desconto_medio_bruto = desconto_total_bruto / Decimal(pedidos_total) if pedidos_total else Decimal("0")

            top_vendor = None
            top_vendor_rows: List[Dict[str, Any]] = []
            top_vendor_discount = None
            top_discount_rows: List[Dict[str, Any]] = []
            top_vendor_rb = None
            top_vendor_rb_rows: List[Dict[str, Any]] = []
            top_vendor_devolucao = None
            top_vendor_devolucao_rows: List[Dict[str, Any]] = []
            if "top_vendedor" in topics:
                top_vendor_rows = await self._fetch_vendor_ranking(
                    session,
                    binds,
                    limit=1,
                    by_discount=False,
                    primary_key=primary_sales_key,
                    include_operational_details=include_operational_details,
                    include_discount_details=include_discount_details,
                    filial=selected_filial,
                )
                top_vendor = top_vendor_rows[0] if top_vendor_rows else {}
            if "top_vendedor_desconto" in topics:
                top_discount_rows = await self._fetch_vendor_ranking(
                    session,
                    binds,
                    limit=1,
                    by_discount=True,
                    include_operational_details=include_operational_details,
                    include_discount_details=True,
                    filial=selected_filial,
                )
                top_vendor_discount = top_discount_rows[0] if top_discount_rows else None
            if "top_vendedor_rb" in topics:
                top_vendor_rb_rows = await self._fetch_vendor_ranking(
                    session,
                    binds,
                    limit=1,
                    by_discount=False,
                    primary_key="saida_rb",
                    include_operational_details=include_operational_details,
                    include_discount_details=include_discount_details,
                    filial=selected_filial,
                )
                top_vendor_rb = top_vendor_rb_rows[0] if top_vendor_rb_rows else {}
            if "top_vendedor_devolucao" in topics:
                top_vendor_devolucao_rows = await self._fetch_vendor_ranking(
                    session,
                    binds,
                    limit=1,
                    by_discount=False,
                    primary_key="devolucao",
                    include_operational_details=include_operational_details,
                    include_discount_details=include_discount_details,
                    filial=selected_filial,
                )
                top_vendor_devolucao = top_vendor_devolucao_rows[0] if top_vendor_devolucao_rows else {}

            if "ranking_vendedores" in topics:
                ranking_kind = "vendedores"
                ranking_rows = await self._fetch_vendor_ranking(
                    session,
                    binds,
                    limit=vendor_ranking_limit,
                    by_discount=False,
                    primary_key=primary_sales_key,
                    include_operational_details=include_operational_details,
                    include_discount_details=include_discount_details,
                    filial=selected_filial,
                )
            elif "ranking_vendedores_desconto" in topics:
                ranking_kind = "vendedores_desconto"
                ranking_rows = await self._fetch_vendor_ranking(
                    session,
                    binds,
                    limit=vendor_ranking_limit,
                    by_discount=True,
                    include_operational_details=include_operational_details,
                    include_discount_details=True,
                    filial=selected_filial,
                )
            elif "ranking_vendedores_rb" in topics:
                ranking_kind = "vendedores_rb"
                ranking_rows = await self._fetch_vendor_ranking(
                    session,
                    binds,
                    limit=vendor_ranking_limit,
                    by_discount=False,
                    primary_key="saida_rb",
                    include_operational_details=include_operational_details,
                    include_discount_details=include_discount_details,
                    filial=selected_filial,
                )
            elif "ranking_vendedores_devolucao" in topics:
                ranking_kind = "vendedores_devolucao"
                ranking_rows = await self._fetch_vendor_ranking(
                    session,
                    binds,
                    limit=vendor_ranking_limit,
                    by_discount=False,
                    primary_key="devolucao",
                    include_operational_details=include_operational_details,
                    include_discount_details=include_discount_details,
                    filial=selected_filial,
                )

            top_client = None
            top_client_rows: List[Dict[str, Any]] = []
            if "top_cliente" in topics:
                client_primary_key = primary_sales_key if primary_sales_key in {*sales_value_breakdown.CATEGORY_VALUE_KEYS, "total_bruto"} else "faturamento_comercial"
                top_client_rows = await self._fetch_client_ranking(
                    session,
                    binds,
                    limit=1,
                    primary_key=client_primary_key,
                    include_operational_details=include_operational_details,
                    include_discount_details=include_discount_details,
                    filial=selected_filial,
                )
                top_client = top_client_rows[0] if top_client_rows else {}
            if "ranking_clientes" in topics:
                ranking_kind = "clientes"
                client_primary_key = primary_sales_key if primary_sales_key in {*sales_value_breakdown.CATEGORY_VALUE_KEYS, "total_bruto"} else "faturamento_comercial"
                ranking_rows = await self._fetch_client_ranking(
                    session,
                    binds,
                    limit=client_ranking_limit,
                    primary_key=client_primary_key,
                    include_operational_details=include_operational_details,
                    include_discount_details=include_discount_details,
                    filial=selected_filial,
                )
            if "produto_mais_vendido" in topics or "estoque_produto" in topics:
                ranking_kind = "produtos"
                explicit_limit = self._ranking_limit_from_text(normalized_query) or 10
                ranking_rows = await sales_value_breakdown.fetch_product_ranking(
                    session,
                    binds,
                    limit=explicit_limit,
                    filial=selected_filial,
                )
            elif "financeiro_aberto" in topics:
                ranking_kind = "financeiro"
                ranking_rows = await sales_value_breakdown.fetch_financial_open(
                    session,
                    binds,
                    limit=50,
                )

        period_label = f"{start_date.isoformat()} a {end_date.isoformat()}"
        response_text = ""
        discount_warning = self._discount_source_warning(period_totals)
        discount_query_requested = any("desconto" in topic for topic in topics)

        if ranking_kind:
            summary_rows = ranking_rows
            effective_ranking_limit = client_ranking_limit if ranking_kind == "clientes" else vendor_ranking_limit
            displayed = f"top {effective_ranking_limit}" if effective_ranking_limit else "todos"
            if ranking_kind == "vendedores":
                total_rows = self._distinct_count(ranking_rows, "vendedor")
                response_text = (
                    f"Ranking de vendedores no período {period_label}{scope_text}: "
                    f"{total_rows} vendedor(es) retornado(s) ({displayed}), detalhados por filial."
                )
                if ranking_rows:
                    first = ranking_rows[0]
                    response_text += f" Líder: {first['vendedor']} ({self._format_brl(first.get('valor_total'))})."
                response_text += " O cadastro técnico PADRAO foi desconsiderado apenas no ranking de vendedores."
            elif ranking_kind == "vendedores_desconto":
                total_rows = self._distinct_count(ranking_rows, "vendedor")
                response_text = (
                    f"Ranking de vendedores por desconto no período {period_label}{scope_text}: "
                    f"{total_rows} vendedor(es) retornado(s) ({displayed}), detalhados por filial."
                )
                if ranking_rows:
                    first = ranking_rows[0]
                    response_text += f" Maior desconto: {first['vendedor']} ({self._format_brl(first.get('valor_total'))})."
                else:
                    if discount_warning:
                        response_text += " Nao ha coluna explicita de desconto para montar ranking; a derivacao atual retornou zero."
                    else:
                        response_text += " Não houve desconto registrado para montar ranking nesse período."
                response_text += " O cadastro técnico PADRAO foi desconsiderado apenas no ranking de vendedores."
            elif ranking_kind == "vendedores_rb":
                total_rows = self._distinct_count(ranking_rows, "vendedor")
                response_text = (
                    f"Ranking de vendedores por Saida RB no período {period_label}{scope_text}: "
                    f"{total_rows} vendedor(es) retornado(s) ({displayed}), detalhados por filial."
                )
                if ranking_rows:
                    first = ranking_rows[0]
                    response_text += f" Maior valor de RB: {first['vendedor']} ({self._format_brl(first.get('valor_total'))})."
                else:
                    response_text += " Nao houve Saida RB registrada para montar ranking nesse período."
                response_text += " O cadastro técnico PADRAO foi desconsiderado apenas no ranking de vendedores."
            elif ranking_kind == "vendedores_devolucao":
                total_rows = self._distinct_count(ranking_rows, "vendedor")
                response_text = (
                    f"Ranking de vendedores por Devolucao no periodo {period_label}{scope_text}: "
                    f"{total_rows} vendedor(es) retornado(s) ({displayed}), detalhados por filial."
                )
                if ranking_rows:
                    first = ranking_rows[0]
                    response_text += f" Maior valor de devolucao: {first['vendedor']} ({self._format_brl(first.get('valor_total'))})."
                else:
                    response_text += " Nao houve Devolucao registrada para montar ranking nesse periodo."
                response_text += " O cadastro tecnico PADRAO foi desconsiderado apenas no ranking de vendedores."
            elif ranking_kind == "clientes":
                total_rows = self._distinct_count(ranking_rows, "cliente")
                response_text = (
                    f"Ranking de clientes no período {period_label}{scope_text}: "
                    f"{total_rows} cliente(s) retornado(s) ({displayed}), detalhados por filial."
                )
                if ranking_rows:
                    first = ranking_rows[0]
                    response_text += f" Líder: {first['cliente']} ({self._format_brl(first.get('valor_total'))})."
                response_text += " O cliente interno LAGES E LOPES LTDA foi desconsiderado apenas no ranking de clientes."
            elif ranking_kind == "produtos":
                total_rows = len(ranking_rows)
                response_text = (
                    f"Produtos mais vendidos e posição de estoque no período {period_label}{scope_text}: "
                    f"{total_rows} produto(s) retornado(s)."
                )
                if ranking_rows:
                    first = ranking_rows[0]
                    response_text += f" Produto líder: {first['produto']} (Qtd: {int(first.get('quantidade_vendida') or 0):,}, Estoque atual: {int(first.get('estoque_atual') or 0):,})."
            elif ranking_kind == "financeiro":
                total_rows = len(ranking_rows)
                response_text = (
                    f"Títulos e parcelas financeiras em aberto no período {period_label}{scope_text}: "
                    f"{total_rows} registro(s) retornado(s)."
                )

        if not ranking_kind and "faturamento" in topics:
            summary_rows = self._period_value_breakdown_rows(
                period_totals,
                period_filial_totals,
                filial=selected_filial,
                value_basis=value_basis,
                include_operational_details=include_operational_details,
            )
        if not ranking_kind and "rb" in topics:
            summary_rows.extend(
                self._period_category_breakdown_rows(
                    period_totals,
                    period_filial_totals,
                    filial=selected_filial,
                    category_key="saida_rb",
                )
            )
        if not ranking_kind and "devolucao" in topics:
            summary_rows.extend(
                self._period_category_breakdown_rows(
                    period_totals,
                    period_filial_totals,
                    filial=selected_filial,
                    category_key="devolucao",
                )
            )
        if "ticket" in topics:
            summary_rows.extend(
                self._period_ticket_breakdown_rows(
                    period_totals,
                    period_filial_totals,
                    filial=selected_filial,
                )
            )
        if "desconto" in topics:
            summary_rows.extend(
                self._period_discount_breakdown_rows(
                    period_totals,
                    period_filial_totals,
                    filial=selected_filial,
                )
            )
        if not ranking_kind and top_vendor:
            summary_rows.extend(self._decorate_rows_with_indicator(top_vendor_rows or [top_vendor], "Vendedor com maior venda"))
        if not ranking_kind and top_vendor_discount:
            summary_rows.extend(self._decorate_rows_with_indicator(top_discount_rows or [top_vendor_discount], "Vendedor com maior desconto"))
        if not ranking_kind and top_vendor_rb:
            summary_rows.extend(self._decorate_rows_with_indicator(top_vendor_rb_rows or [top_vendor_rb], "Vendedor com maior RB"))
        if not ranking_kind and top_vendor_devolucao:
            summary_rows.extend(self._decorate_rows_with_indicator(top_vendor_devolucao_rows or [top_vendor_devolucao], "Vendedor com maior devolucao"))
        if not ranking_kind and top_client:
            summary_rows.extend(self._decorate_rows_with_indicator(top_client_rows or [top_client], "Cliente com maior compra"))
        parts = []
        if not ranking_kind and "faturamento" in topics:
            if value_basis == "bruto":
                faturamento_part = f"total bruto sem transferencias{scope_text} de {self._format_brl(total_bruto)}"
            elif value_basis == "ambos":
                faturamento_part = (
                    f"faturamento comercial{scope_text} de {self._format_brl(faturamento_total)} "
                    f"e total bruto sem transferencias de {self._format_brl(total_bruto)}"
                )
            else:
                faturamento_part = f"faturamento comercial{scope_text} de {self._format_brl(faturamento_total)}"
            parts.append(
                f"{faturamento_part}; tabela separada por filial"
            )
        if not ranking_kind and "rb" in topics:
            rb_value = self._decimal_value(period_totals.get("saida_rb"))
            rb_orders = int(period_totals.get("pedidos_saida_rb") or 0)
            parts.append(f"Saida RB{scope_text} de {self._format_brl(rb_value)} em {rb_orders} pedido(s)")
        if not ranking_kind and "devolucao" in topics:
            devolucao_value = self._decimal_value(period_totals.get("devolucao"))
            devolucao_orders = int(period_totals.get("pedidos_devolucao") or 0)
            parts.append(f"Devolucao{scope_text} de {self._format_brl(devolucao_value)} em {devolucao_orders} pedido(s)")
        if not ranking_kind and "ticket" in topics:
            parts.append(f"ticket médio{scope_text} de {self._format_brl(ticket_medio)}")
        if not ranking_kind and "desconto" in topics:
            if discount_warning:
                parts.append(
                    f"desconto real indisponivel na view; derivacao atual{scope_text} retornou "
                    f"{self._format_brl(desconto_total)} e media de {self._format_brl(desconto_medio)}"
                )
            else:
                parts.append(f"desconto total{scope_text} de {self._format_brl(desconto_total)} e desconto médio de {self._format_brl(desconto_medio)}")
        if not ranking_kind and top_vendor:
            parts.append(f"vendedor com maior venda: {top_vendor.get('vendedor')} ({self._format_brl(top_vendor.get('valor_total') or 0)})")
        if not ranking_kind and top_vendor_discount:
            parts.append(f"vendedor com maior desconto: {top_vendor_discount.get('vendedor')} ({self._format_brl(top_vendor_discount.get('valor_total') or 0)})")
        if not ranking_kind and top_vendor_rb:
            parts.append(f"vendedor com maior RB: {top_vendor_rb.get('vendedor')} ({self._format_brl(top_vendor_rb.get('valor_total') or 0)})")
        if not ranking_kind and top_vendor_devolucao:
            parts.append(f"vendedor com maior devolucao: {top_vendor_devolucao.get('vendedor')} ({self._format_brl(top_vendor_devolucao.get('valor_total') or 0)})")
        if not ranking_kind and top_client:
            parts.append(f"cliente com maior compra: {top_client.get('cliente')} ({self._format_brl(top_client.get('valor_total') or 0)})")
        if not ranking_kind and unsupported_warnings:
            parts.extend(unsupported_warnings)
        if not ranking_kind and parts:
            response_text = f"Resumo do período {period_label}: " + "; ".join(parts) + "."
        elif not ranking_kind and "top_vendedor_desconto" in topics and discount_warning:
            response_text = (
                f"Nao ha coluna explicita de desconto na view para identificar o vendedor com maior desconto "
                f"no periodo {period_label}{scope_text}; a derivacao atual retornou zero."
            )
        elif not ranking_kind:
            response_text = f"Não foram encontrados dados suficientes para responder no período {period_label}."
        if discount_query_requested and discount_warning:
            response_text += f" Atencao: {discount_warning}"
        if not ranking_kind and ("top_vendedor" in topics or "top_vendedor_desconto" in topics or "top_vendedor_rb" in topics or "top_vendedor_devolucao" in topics):
            response_text += " O cadastro técnico PADRAO foi desconsiderado apenas no ranking de vendedores."
        if not ranking_kind and "top_cliente" in topics:
            response_text += " O cliente interno LAGES E LOPES LTDA foi desconsiderado apenas no ranking de clientes."

        if "documentos" in topics:
            summary_rows = document_rows
            response_text = (
                f"Documentos que compõem a métrica no período {period_label}{scope_text}: "
                f"até {len(document_rows)} registro(s), agrupados por pedido, nota, filial e tipo de operação."
            )

        from models.view_catalog import ChartType as SchemaChartType
        from services.data_transformer import transform_data

        all_warnings = [*unsupported_warnings]
        if discount_query_requested and discount_warning:
            all_warnings.append(discount_warning)

        response_text = self._apply_response_mode(
            response_text,
            mode=mode,
            row_count=len(summary_rows),
            warnings=all_warnings,
        )

        breakdown_resumo = {
            key: float(self._decimal_value(period_totals.get(key)))
            for key in sales_value_breakdown.CATEGORY_VALUE_KEYS
        }
        core_resumo = {
            "periodo": period_label,
            "filial": selected_filial or "todas",
            "faturamento_total": float(faturamento_total),
            "total_bruto": float(total_bruto),
            "total_movimentos_view": float(self._decimal_value(period_totals.get("total_movimentos_view"))),
            **breakdown_resumo,
            "ticket_medio": float(ticket_medio),
            "ticket_medio_bruto": float(ticket_medio_bruto),
            "desconto_total": float(desconto_total),
            "desconto_total_bruto": float(desconto_total_bruto),
            "desconto_medio_bruto": float(desconto_medio_bruto),
            "desconto_fonte_tipo": str(period_totals.get("desconto_fonte_tipo") or "derivado_sem_coluna_explicita"),
            "desconto_fonte_coluna": period_totals.get("desconto_fonte_coluna"),
            "desconto_fonte_confianca": str(period_totals.get("desconto_fonte_confianca") or "baixa"),
            "desconto_fonte_observacao": self._discount_source_observation(period_totals),
            "pedidos_comerciais": pedidos,
            "pedidos_total": pedidos_total,
            "pedidos_movimentos_view": int(period_totals.get("pedidos_movimentos_view") or 0),
            "total_indicadores": len(summary_rows),
            "tipo_saida": ranking_kind or "resumo",
            "filtro_comercial": self._erp_sales_filter_label(selected_filial),
            "filiais": period_filial_totals,
            "base_valor": value_basis,
            "primary_metric": primary_sales_key,
            "modo_resposta": self._normalize_response_mode(mode),
            "financial_source_discovery_version": (financial_source_report or {}).get("version"),
        }
        metric_audit = core_sales_metric_audit(
            topics=topics,
            value_basis=value_basis,
            ranking_kind=ranking_kind,
            primary_metric=primary_sales_key,
            period_label=period_label,
            filial=selected_filial,
            discount_source=period_totals,
            financial_source_discovery=financial_source_report,
        )
        core_resumo["metric_registry_version"] = metric_audit["registry_version"]

        chart_type_values = self._schema_chart_types_from_text(normalized_query, ranking_kind=ranking_kind)
        visualizations_payload: List[Dict[str, Any]] = []
        for chart_type_value in chart_type_values:
            try:
                target_chart_type = SchemaChartType(chart_type_value)
            except ValueError:
                target_chart_type = SchemaChartType.TABLE
                chart_type_value = SchemaChartType.TABLE.value
            transformed = transform_data(summary_rows, target_chart_type)
            if isinstance(transformed, dict):
                existing_resumo = transformed.get("resumo") if isinstance(transformed.get("resumo"), dict) else {}
                transformed["resumo"] = {**existing_resumo, **core_resumo}
            visualizations_payload.append(
                {
                    "chart_type": chart_type_value,
                    "chart_data": transformed,
                }
            )
        chart_data = visualizations_payload[0]["chart_data"] if visualizations_payload else transform_data(summary_rows, SchemaChartType.TABLE)
        primary_chart_type = visualizations_payload[0]["chart_type"] if visualizations_payload else SchemaChartType.TABLE.value
        elapsed = (time.perf_counter() - start_time) * 1000
        plan_intent = IntentType.RANKING if ranking_kind else IntentType.AGGREGATION
        plan_dimensions = ["Vendedor.nome"] if ranking_kind and "vendedores" in ranking_kind else ["Venda.dtemissao_"]
        if ranking_kind == "clientes":
            plan_dimensions = ["Cliente.nome"]
        if "Venda.filial_" not in plan_dimensions:
            plan_dimensions.append("Venda.filial_")

        canonical_plan = CanonicalPlan(
            trace_id=trace_id,
            status=ExecutionStatus.READY,
            intent=plan_intent,
            goal=pergunta,
            entities=["Venda"],
            metrics=sorted(topics),
            dimensions=plan_dimensions,
            suggested_visualization=self._visualization_type_for_schema(primary_chart_type),
        )
        db_state = DashboardState(
            chart_type=self._visualization_type_for_schema(primary_chart_type),
            selected_filters={"tenant_id": tenant_id, "periodo": period_label, "filial": selected_filial or "todas"},
        )
        exec_res = ExecutionResult(
            status=ExecutionStatus.READY,
            dataset=summary_rows,
            metadata={"rule": "core_summary_query", "binds": binds, "business_filter": self._erp_sales_filter_label(selected_filial)},
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
        debug_data["chart"] = {"primary": primary_chart_type, "visualizations": visualizations_payload}
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
            "chart_type": primary_chart_type,
            "chart_data": chart_data,
            "sample_rows": summary_rows,
            "visualizations": visualizations_payload if len(visualizations_payload) > 1 else None,
            "insights": [],
            "recommendations": [],
            "warnings": all_warnings,
            "bi_intelligence": {
                "metric_definitions": metric_audit["metric_definitions"],
                "calculation_steps": metric_audit["calculation_steps"],
                "unsupported_metrics": metric_audit["unsupported_metrics"],
                "source_warnings": all_warnings,
                "financial_source_discovery": financial_source_report,
            },
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
                "confidence_score": 1.0 if not all_warnings else 0.55,
                "calculation": "deterministic_core_summary",
                "discount_source": period_totals.get("desconto_fonte_tipo") or "derivado_sem_coluna_explicita",
                "metric_registry": metric_audit,
                "financial_source_discovery": financial_source_report,
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

    def _repair_mojibake_text(self, value: str) -> str:
        text_value = str(value or "")
        if any(marker in text_value for marker in ("Ã", "Â", "â€", "�")):
            for _ in range(2):
                try:
                    repaired = text_value.encode("cp1252").decode("utf-8")
                except UnicodeError:
                    break
                if repaired == text_value:
                    break
                text_value = repaired
        return (
            text_value
            .replace("Ã¡", "á")
            .replace("Ã ", "à")
            .replace("Ã¢", "â")
            .replace("Ã£", "ã")
            .replace("Ã©", "é")
            .replace("Ãª", "ê")
            .replace("Ã­", "í")
            .replace("Ã³", "ó")
            .replace("Ã´", "ô")
            .replace("Ãµ", "õ")
            .replace("Ãº", "ú")
            .replace("Ã§", "ç")
        )

    def _normalize_query_text(self, value: str) -> str:
        text_value = unicodedata.normalize("NFKD", self._repair_mojibake_text(str(value or "")).lower())
        normalized = "".join(ch for ch in text_value if not unicodedata.combining(ch))
        normalized = re.sub(r"mar\?+o", "marco", normalized)
        normalized = re.sub(r"m\?+s", "mes", normalized)
        normalized = re.sub(r"gr\?+fico", "grafico", normalized)
        normalized = re.sub(r"l\?+quido", "liquido", normalized)
        normalized = re.sub(r"l\?+quida", "liquida", normalized)
        normalized = re.sub(r"per\?+odo", "periodo", normalized)
        normalized = re.sub(r"m\?+dio", "medio", normalized)
        normalized = re.sub(r"n\?+o", "nao", normalized)
        normalized = re.sub(r"devolu\?+\w*", "devolucao", normalized)
        return (
            normalized
            .replace("mar?o", "marco")
            .replace("m?s", "mes")
            .replace("n?o", "nao")
            .replace("m?dio", "medio")
            .replace("gr?fico", "grafico")
            .replace("l?quido", "liquido")
            .replace("per?odo", "periodo")
        )

    def _month_ranges_from_text(
        self,
        text_value: str,
        temporal_context: TemporalContext | None = None,
    ) -> list[tuple[str, str]]:
        """Canonical plural month API used by comparison-aware contracts."""
        context = temporal_context or default_temporal_context()
        _, selected = self.temporal_gateway.select_ranges(
            text_value,
            context,
            legacy_parser=self._month_range_from_text_legacy,
        )
        return selected

    def _month_range_from_text(
        self,
        text_value: str,
        temporal_context: TemporalContext | None = None,
    ) -> Optional[tuple[str, str]]:
        """Deprecated singular wrapper that refuses plural temporal semantics."""
        ranges = self._month_ranges_from_text(text_value, temporal_context)
        if len(ranges) > 1:
            raise PluralTemporalResultError(
                "Orchestrator singular period wrapper refuses multiple windows"
            )
        return ranges[0] if ranges else None

    def _month_range_from_text_legacy(self, text_value: str) -> Optional[tuple[str, str]]:
        normalized = self._normalize_query_text(text_value)

        iso_range_match = re.search(
            r"\b(20\d{2}-\d{2}-\d{2})\s*(?:a|ate|to|--?|->)\s*(20\d{2}-\d{2}-\d{2})\b",
            normalized,
        )
        if iso_range_match:
            try:
                start_date = date.fromisoformat(iso_range_match.group(1))
                end_date = date.fromisoformat(iso_range_match.group(2))
            except ValueError:
                return None
            if start_date <= end_date:
                return start_date.isoformat(), end_date.isoformat()

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
            "jan": 1,
            "fevereiro": 2,
            "fev": 2,
            "marco": 3,
            "mar": 3,
            "abril": 4,
            "abr": 4,
            "maio": 5,
            "mai": 5,
            "junho": 6,
            "jun": 6,
            "julho": 7,
            "jul": 7,
            "agosto": 8,
            "ago": 8,
            "setembro": 9,
            "set": 9,
            "outubro": 10,
            "out": 10,
            "novembro": 11,
            "nov": 11,
            "dezembro": 12,
            "dez": 12,
        }
        month_match = re.search(
            r"\b(janeiro|jan|fevereiro|fev|marco|mar|abril|abr|maio|mai|junho|jun|julho|jul|agosto|ago|setembro|set|outubro|out|novembro|nov|dezembro|dez)\b(?:\s+de)?\s*/?\s*(20\d{2})",
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
            "hoje",
            "este mes",
            "esse mes",
            "mes atual",
            "ultimos 30 dias",
            "ultimas semanas",
        )
        if any(pattern in normalized for pattern in current_month_patterns):
            last_day = calendar.monthrange(today.year, today.month)[1]
            return f"{today.year:04d}-{today.month:02d}-01", f"{today.year:04d}-{today.month:02d}-{last_day:02d}"

        # Se encontrou um ano de 4 dígitos isolado (ex: "ano de 2026", "em 2026", "2026")
        year_match = re.search(r"\b(?:no\s+ano\s+de\s+|ano\s+de\s+|ano\s+)?(20\d{2})\b", normalized)
        if year_match:
            year = int(year_match.group(1))
            return f"{year:04d}-01-01", f"{year:04d}-12-31"

        # Retorna None — caller vai usar mês atual como fallback
        return None

    def _ensure_period_filter(
        self,
        semantic_plan: SemanticPlan,
        pergunta: str,
        temporal_context: TemporalContext | None = None,
    ) -> None:
        text_value = f"{pergunta or ''} {semantic_plan.goal or ''}"
        month_range = self._month_range_from_text(text_value, temporal_context)
        if not month_range:
            # Fallback: usa mês atual como período padrão se não houver período no texto
            current_ranges = self._month_ranges_from_text("mes atual", temporal_context)
            if not current_ranges:
                raise ValueError("Temporal normalizer did not resolve the current month")
            month_range = current_ranges[0]
            logger.info("[Orchestrator] _ensure_period_filter: Período ausente — assumindo mês atual %s a %s", *month_range)

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

    def _repair_core_business_query(
        self,
        semantic_plan: SemanticPlan,
        pergunta: str,
        temporal_context: TemporalContext | None = None,
    ) -> None:
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

        self._ensure_period_filter(semantic_plan, pergunta, temporal_context)

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
        parent_id: Optional[str] = None,
        mode: str = "analytical",
        conversation_state: Optional[Any] = None,
        postgres_conversation_authority: bool = False,
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
                with open(os.path.join(log_dir, f"debug_{trace_id}.json"), "w", encoding="utf-8") as f:
                    f.write(debug_json)
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
        from services.metadata_catalog.conversation_graph import (
            StatelessConversationGraphAdapter,
            conversation_graph_manager as legacy_conversation_graph_manager,
        )
        conversation_graph_manager = (
            StatelessConversationGraphAdapter()
            if postgres_conversation_authority
            else legacy_conversation_graph_manager
        )
        graph = conversation_graph_manager.get_graph(session_key)
        if postgres_conversation_authority:
            history = []
            debug_data["conversation_state"] = {
                "authority": "POSTGRESQL",
                "schema_version": getattr(conversation_state, "schema_version", None),
                "context_epoch": getattr(conversation_state, "context_epoch", 0),
                "context_version": getattr(conversation_state, "context_version", 0),
            }

        # Se o parent_id foi fornecido explicitamente, navega/muda o nó ativo para ele
        if parent_id and parent_id in graph.nodes:
            graph.current_node_id = parent_id
            conversation_graph_manager.save_graph(session_key, graph)

        temporal_context = default_temporal_context(
            reference_datetime=datetime.now(timezone.utc),
        )
        effective_pergunta = self._question_with_inherited_context(
            pergunta,
            history,
            temporal_context,
        )
        temporal_result = self.temporal_gateway.normalize(
            effective_pergunta,
            temporal_context,
            legacy_parser=self._month_range_from_text_legacy,
        )
        debug_data["temporal_normalization"] = {
            "normalizer_version": temporal_result.normalizer_version,
            "rule_ids": list(temporal_result.rule_ids),
            "window_count": len(temporal_result.windows),
            "relation": temporal_result.relation.value,
            "readiness": temporal_result.readiness.value,
            "timezone": temporal_result.timezone,
            "duration_ms": temporal_result.duration_ms,
        }
        if (
            temporal_result.relation == TemporalRelation.COMPARISON
            and (
                self.comparison_planner_enabled
                or self.comparison_planner_shadow_mode
            )
        ):
            try:
                from contracts.analytical_v2 import (
                    PipelineKind,
                    build_intent_v2,
                    build_plan_v2,
                )

                comparison_intent = build_intent_v2(
                    effective_pergunta,
                    pipeline=PipelineKind.NEW,
                    temporal_context=temporal_context,
                    temporal_result=temporal_result,
                )
                comparison_plan = build_plan_v2(
                    comparison_intent,
                    tenant_id=uuid.UUID(tenant_id),
                    user_id=None,
                    user_role="CONSULTA",
                    session_id=session_key,
                    allowed_source_ids=["vw_vendas_lm"],
                    pipeline=PipelineKind.NEW,
                    comparison_planner_enabled=self.comparison_planner_enabled,
                    comparison_planner_shadow_mode=self.comparison_planner_shadow_mode,
                )
                planner_metadata = comparison_plan.contract.extensions.get(
                    "comparison_planner",
                    {},
                )
                debug_data["comparison_planning"] = {
                    "planner_version": planner_metadata.get("planner_version"),
                    "kind": planner_metadata.get("kind"),
                    "operand_count": planner_metadata.get("operand_count"),
                    "metric_count": planner_metadata.get("metric_count"),
                    "dimension_count": planner_metadata.get("dimension_count"),
                    "complexity": planner_metadata.get("complexity"),
                    "readiness": comparison_plan.intent.readiness.value,
                    "issue_codes": planner_metadata.get("issue_codes", []),
                    "strategy_hint": planner_metadata.get("strategy_hint"),
                    "cache_identity": comparison_plan.cache_identity,
                }
                if (
                    comparison_plan.intent.readiness.value == "READY"
                    and (
                        self.comparison_executor_enabled
                        or self.comparison_executor_shadow_mode
                    )
                ):
                    from services.comparison_execution import (
                        ComparisonExecutionRejected,
                        execution_result_to_legacy,
                    )
                    from services.comparison_execution.runtime import (
                        ComparisonRuntimeUnavailable,
                        execute_plan_on_tenant_clone,
                    )

                    shadow_safe = (
                        len(comparison_plan.comparison.operands) <= 2
                        and len(comparison_plan.dimension_refs) <= 1
                        and (comparison_plan.limit or 1000) <= 1000
                    )
                    if self.comparison_executor_enabled or shadow_safe:
                        try:
                            comparison_result = await execute_plan_on_tenant_clone(
                                comparison_plan
                            )
                            debug_data["comparison_execution"] = {
                                "executor_version": comparison_result.executor_version,
                                "status": comparison_result.status.value,
                                "strategy": comparison_result.strategy_used.value,
                                "operand_count": len(comparison_result.operands),
                                "calculation_count": len(comparison_result.calculations),
                                "validation": comparison_result.validation.status.value,
                                "partial": comparison_result.partial,
                                "cache_status": comparison_result.cache_status,
                                "duration_ms": float(comparison_result.duration_ms),
                            }
                            if self.comparison_executor_enabled:
                                return write_debug_and_return(
                                    execution_result_to_legacy(
                                        comparison_result,
                                        comparison_plan,
                                    )
                                )
                        except (
                            ComparisonExecutionRejected,
                            ComparisonRuntimeUnavailable,
                            RuntimeError,
                            ValueError,
                        ) as executor_exc:
                            logger.warning(
                                "Comparison executor V2 did not produce a result | error=%s",
                                type(executor_exc).__name__,
                            )
                            debug_data["comparison_execution"] = {
                                "status": "BLOCKED",
                                "error_type": type(executor_exc).__name__,
                            }
                            if self.comparison_executor_enabled:
                                return write_debug_and_return(
                                    {
                                        "status": "SECURITY_VIOLATION",
                                        "mensagem": (
                                            "A comparacao foi bloqueada porque a fonte "
                                            "analitica nao comprovou todos os requisitos "
                                            "de seguranca e validacao."
                                        ),
                                        "resposta_direta": (
                                            "Nao foi possivel executar esta comparacao "
                                            "com seguranca."
                                        ),
                                        "chart_data": None,
                                    }
                                )
            except (TypeError, ValueError) as planner_exc:
                logger.warning(
                    "Comparison planner preview was not produced | error=%s",
                    type(planner_exc).__name__,
                )
                debug_data["comparison_planning"] = {
                    "readiness": "ERROR",
                    "error_type": type(planner_exc).__name__,
                }
        if effective_pergunta != pergunta:
            debug_data["pergunta_contextualizada"] = effective_pergunta

        # ── Intercepção de Ambiguidade: 1) Faturamento Bruto vs Líquido ──────
        if self._is_faturamento_basis_ambiguous(pergunta):
            logger.info("[Orchestrator] Faturamento ambíguo detectado sem especificação de Bruto/Líquido. Disparando popup.")
            elapsed = (time.perf_counter() - start_time) * 1000
            amb_res = {
                "status": "AMBIGUOUS",
                "goal": pergunta,
                "ambiguities": [
                    "Faturamento Líquido (Base Comercial Padrão - Vendas Válidas)",
                    "Faturamento Bruto (Total Sem Descontos ou Devoluções)"
                ],
                "missing_information": [],
                "resposta_direta": "Identifiquei que você solicitou Faturamento. Por favor, selecione qual base de valor deseja analisar:",
                "pergunta_original": pergunta,
                "execution_time_ms": elapsed
            }
            return write_debug_and_return(amb_res)

        # ── Intercepção de Ambiguidade: 2) Escolha Obrigatória do Formato de Dashboard ──
        if self._is_visualization_preference_ambiguous(pergunta):
            logger.info("[Orchestrator] Preferência de dashboard não especificada. Disparando popup para escolha visual.")
            elapsed = (time.perf_counter() - start_time) * 1000
            amb_res = {
                "status": "AMBIGUOUS",
                "goal": pergunta,
                "ambiguities": [
                    "Tabela Detalhada com Colunas",
                    "Gráfico de Barras",
                    "Gráfico de Linhas (Evolução Temporal)",
                    "Gráfico de Pizza (Distribuição em %)",
                    "Cartão de KPI Destacado"
                ],
                "missing_information": [],
                "resposta_direta": "Como você deseja visualizar este dashboard?",
                "pergunta_original": pergunta,
                "execution_time_ms": elapsed
            }
            return write_debug_and_return(amb_res)

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
                mode=mode,
                temporal_context=temporal_context,
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

        # ── Intercepção de Ambiguidade: 1) Faturamento Bruto vs Líquido ──────
        if self._is_faturamento_basis_ambiguous(pergunta):
            logger.info("[Orchestrator] Faturamento ambíguo detectado sem especificação de Bruto/Líquido. Disparando popup.")
            elapsed = (time.perf_counter() - start_time) * 1000
            amb_res = {
                "status": "AMBIGUOUS",
                "goal": pergunta,
                "ambiguities": [
                    "Faturamento Líquido (Base Comercial Padrão - Vendas Válidas)",
                    "Faturamento Bruto (Total Sem Descontos ou Devoluções)"
                ],
                "missing_information": [],
                "resposta_direta": "Identifiquei que você solicitou Faturamento. Por favor, selecione qual base de valor deseja analisar:",
                "pergunta_original": pergunta,
                "execution_time_ms": elapsed
            }
            return write_debug_and_return(amb_res)

        # ── Intercepção de Ambiguidade: 2) Escolha Obrigatória do Formato de Dashboard ──
        if self._is_visualization_preference_ambiguous(pergunta):
            logger.info("[Orchestrator] Preferência de dashboard não especificada. Disparando popup para escolha visual.")
            elapsed = (time.perf_counter() - start_time) * 1000
            amb_res = {
                "status": "AMBIGUOUS",
                "goal": pergunta,
                "ambiguities": [
                    "Tabela Detalhada com Colunas",
                    "Gráfico de Barras",
                    "Gráfico de Linhas (Evolução Temporal)",
                    "Gráfico de Pizza (Distribuição em %)",
                    "Cartão de KPI Destacado"
                ],
                "missing_information": [],
                "resposta_direta": "Como você deseja visualizar este dashboard?",
                "pergunta_original": pergunta,
                "execution_time_ms": elapsed
            }
            return write_debug_and_return(amb_res)
        # Inicializa o cache de planos na classe se necessário
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
                query_context=last_q_context,
                temporal_context={
                    "normalizer_version": temporal_result.normalizer_version,
                    "timezone": temporal_result.timezone,
                    "relation": temporal_result.relation.value,
                    "windows": [
                        {
                            "start": window.start.isoformat(),
                            "end": window.end.isoformat(),
                            "granularity": window.granularity.value,
                        }
                        for window in temporal_result.windows
                    ],
                    "unresolved_count": len(temporal_result.unresolved_expressions),
                },
            )
            debug_data["timeline"]["3. Intent Engine Concluído"] = get_timestamp()
            debug_data["resposta_bruta_llm"] = getattr(intent_output, "raw_response", None) or intent_output.model_dump_json()

            # Se for continuidade e houver plano anterior no cache, aplica os patches
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

            if intent_output.status == ExecutionStatus.READY:
                self._repair_core_business_query(
                    semantic_plan,
                    pergunta,
                    temporal_context,
                )

            semantic_plan.status = intent_output.status
            debug_data["semantic_plan"] = semantic_plan.model_dump()

            if intent_output.status in (
                ExecutionStatus.AMBIGUOUS,
                ExecutionStatus.MISSING_INFORMATION,
                ExecutionStatus.OUT_OF_SCOPE,
                ExecutionStatus.UNSUPPORTED,
            ):
                elapsed = (time.perf_counter() - start_time) * 1000
                direct_messages = {
                    ExecutionStatus.AMBIGUOUS: "A pergunta analitica precisa de esclarecimento.",
                    ExecutionStatus.MISSING_INFORMATION: "Faltam informacoes para executar a consulta com seguranca.",
                    ExecutionStatus.OUT_OF_SCOPE: "Esta pergunta esta fora do escopo analitico empresarial.",
                    ExecutionStatus.UNSUPPORTED: "Esta operacao analitica ainda nao possui execucao suportada.",
                }
                res = {
                    "status": intent_output.status.value,
                    "goal": semantic_plan.goal or pergunta,
                    "ambiguities": intent_output.ambiguities,
                    "missing_information": intent_output.missing_information,
                    "resposta_direta": direct_messages[intent_output.status],
                    "pergunta_original": pergunta,
                    "execution_time_ms": elapsed
                }
                return write_debug_and_return(res)

            # Salva o plano semântico bem-sucedido no cache para futuras continuidades
        except Exception as exc:
            import traceback
            debug_data["error_traceback"] = traceback.format_exc()
            logger.error("[Orchestrator] Falha no Motor de Intenções Refatorado: %s", exc, exc_info=True)
            # Fail closed: a falha de interpretacao nao inventa entidade nem dataset.
            elapsed = (time.perf_counter() - start_time) * 1000
            return write_debug_and_return({
                "status": "INTENT_ENGINE_ERROR",
                "goal": pergunta,
                "ambiguities": [],
                "missing_information": [],
                "resposta_direta": (
                    "Nao foi possivel interpretar a pergunta com seguranca. "
                    "Nenhuma consulta foi executada."
                ),
                "mensagem": "Falha controlada no motor de intencoes.",
                "pergunta_original": pergunta,
                "execution_time_ms": elapsed,
                "chart_type": None,
                "chart_data": None,
                "visualizations": None,
                "pode_favoritar": False,
            })

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
                                query_context=last_q_context,
                                temporal_context={
                                    "normalizer_version": temporal_result.normalizer_version,
                                    "timezone": temporal_result.timezone,
                                    "relation": temporal_result.relation.value,
                                    "windows": [
                                        {
                                            "start": window.start.isoformat(),
                                            "end": window.end.isoformat(),
                                        }
                                        for window in temporal_result.windows
                                    ],
                                },
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

        normalized_question_for_visual = self._normalize_query_text(pergunta)
        explicit_chart_type_values = (
            self._schema_chart_types_from_text(normalized_question_for_visual, ranking_kind=None)
            if self._has_explicit_visualization_request(normalized_question_for_visual)
            else []
        )

        v_type_str = canonical_plan.suggested_visualization.value.upper() if hasattr(canonical_plan.suggested_visualization, 'value') else str(canonical_plan.suggested_visualization).upper()
        target_chart_type = vis_map.get(v_type_str, SchemaChartType.TABLE)

        # Coerção inteligente baseada na intenção analítica do negócio
        intent_str = canonical_plan.intent.value.upper() if hasattr(canonical_plan.intent, 'value') else str(canonical_plan.intent).upper()
        if explicit_chart_type_values:
            target_chart_type = vis_map.get(explicit_chart_type_values[0], SchemaChartType.TABLE)
        else:
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
        chart_type_sequence = explicit_chart_type_values or [target_chart_type.value]
        visualizations_payload: List[Dict[str, Any]] = []
        for chart_type_value in chart_type_sequence:
            chart_type_for_payload = vis_map.get(chart_type_value, SchemaChartType.TABLE)
            visualizations_payload.append(
                {
                    "chart_type": chart_type_for_payload.value,
                    "chart_data": transform_data(normalized_rows, chart_type_for_payload),
                }
            )
        target_chart_type = vis_map.get(visualizations_payload[0]["chart_type"], SchemaChartType.TABLE)
        transformed_chart_data = visualizations_payload[0]["chart_data"]
        debug_data["transformer"]["output"] = transformed_chart_data
        debug_data["chart"] = {
            "type": target_chart_type.value,
            "data": transformed_chart_data,
            "visualizations": visualizations_payload,
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
            "visualizations": visualizations_payload if len(visualizations_payload) > 1 else None,
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
