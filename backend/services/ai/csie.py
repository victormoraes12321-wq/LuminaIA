import logging
import uuid
import re
import json
import unicodedata
from datetime import datetime, timezone
from typing import Any, Final, Literal

from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from services.ai_credential_manager import AICMError, ai_credential_manager
from services.ai_invocation_manager import ai_invocation_manager
from services.semantic_memory_repo import (
    get_semantic_memory_record,
    increment_memory_frequencia,
    create_semantic_memory_record
)

logger = logging.getLogger("luminaai.ai.csie")

# --- MAPEAMENTO OFICIAL DE IDS CORPORATIVOS ESTAVEIS ---

STABLE_METRICS: Final[dict[str, dict[str, Any]]] = {
    "MET_001": {"name": "receita_total", "label": "Receita Total", "aliases": ["venda", "vendas", "vendido", "vendidos", "vendeu", "venderam", "total", "valor total", "valor vendido", "valor das vendas", "quanto vendemos", "quanto vendeu", "quanto arrecadamos", "arrecadacao", "receita bruta", "retorno financeiro", "resultado financeiro", "retorno para empresa", "maior retorno financeiro"]},
    "MET_002": {"name": "faturamento_realizado", "label": "Faturamento Realizado", "aliases": ["faturado", "faturamento", "total faturado", "faturamento bruto"]},
    "MET_003": {"name": "lucro_bruto", "label": "Lucro Bruto", "aliases": ["lucro", "lucros", "rentabilidade", "lucro liquido", "lucro bruto", "ganho financeiro", "resultado liquido", "retorno liquido"]},
    "MET_004": {"name": "margem_lucro", "label": "Margem de Lucro", "aliases": ["margem", "margens", "lucratividade", "margem liquida", "margem bruta", "rentabilidade do produto", "retorno percentual"]},
    "MET_005": {"name": "ticket_medio", "label": "Ticket Medio", "aliases": ["ticket", "valor medio", "media por venda", "ticket medio compra"]},
    "MET_006": {"name": "quantidade_pedidos", "label": "Quantidade de Pedidos", "aliases": ["pedidos", "vendas fechadas", "numero de vendas", "transacoes", "quantidade vendas", "quantidade vendida", "unidades vendidas", "volume vendido", "produtos vendidos", "mais vendidos"]},
    "MET_007": {"name": "custo_total", "label": "Custo Total", "aliases": ["custo", "custos", "custo de mercadoria", "cmv"]},
    "MET_008": {"name": "atingimento_meta", "label": "Atingimento da Meta", "aliases": ["atingimento", "meta atingida", "atingimento de meta"]},
    "MET_009": {"name": "meta_mensal", "label": "Meta Mensal", "aliases": ["meta do mes", "meta estabelecida"]},
    "MET_010": {"name": "meta_valor", "label": "Meta de Vendas", "aliases": ["meta", "metas"]},
    "MET_011": {"name": "atingimento", "label": "Atingimento do Vendedor", "aliases": ["atingimento do vendedor", "percentual atingido"]},
    "MET_012": {"name": "comissao", "label": "Comissao", "aliases": ["comissao do vendedor", "comissoes"]},
    "MET_013": {"name": "ranking", "label": "Posicao no Ranking", "aliases": ["posicao", "ranking de vendas", "campeoes"]},
    "MET_014": {"name": "taxa_conversao", "label": "Taxa de Conversao", "aliases": ["conversao", "conversao de leads"]},
    "MET_015": {"name": "churn_rate", "label": "Taxa de Churn", "aliases": ["churn", "perda de clientes", "evasao"]},
    "MET_016": {"name": "ltv_estimado", "label": "LTV Estimado", "aliases": ["ltv", "life time value", "valor do ciclo de vida"]},
    "MET_017": {"name": "cac_estimado", "label": "CAC Estimado", "aliases": ["cac", "custo de aquisicao", "custo aquisicao cliente"]},
    "MET_018": {"name": "cliente_ativo", "label": "Clientes Ativos", "aliases": ["ativos", "clientes recorrentes"]}
}

STABLE_DIMENSIONS: Final[dict[str, dict[str, Any]]] = {
    "DIM_001": {"name": "cliente", "label": "Cliente", "aliases": ["comprador", "agropecuaria", "fazenda", "parceiro"]},
    "DIM_002": {"name": "vendedor", "label": "Vendedor", "aliases": ["representante", "consultor", "agente", "vendedor"]},
    "DIM_003": {"name": "produto", "label": "Produto", "aliases": ["produto", "produtos", "item", "itens", "sku", "insumo", "sementes", "defensivos", "adubo", "mercadoria"]},
    "DIM_004": {"name": "categoria", "label": "Categoria", "aliases": ["grupo", "tipo de produto", "subcategoria"]},
    "DIM_005": {"name": "regiao", "label": "Regiao", "aliases": ["filial", "loja", "estado", "cidade", "filial_nome"]},
    "DIM_006": {"name": "mes", "label": "Mes", "aliases": ["periodo", "mes venda"]},
    "DIM_007": {"name": "ano", "label": "Ano", "aliases": ["exercicio", "ano fiscal"]},
    "DIM_008": {"name": "forma_pagamento", "label": "Forma de Pagamento", "aliases": ["pagamento", "condicao de pagamento"]},
    "DIM_009": {"name": "status", "label": "Status do Pedido", "aliases": ["situacao", "estado da venda"]},
    "DIM_010": {"name": "cidade", "label": "Cidade", "aliases": ["municipio"]},
    "DIM_011": {"name": "estado", "label": "Estado", "aliases": ["uf"]}
}

STABLE_PERIODS: Final[dict[str, dict[str, Any]]] = {
    "PER_TODAY": {"name": "PER_TODAY", "label": "Hoje", "aliases": ["hoje", "dia de hoje", "data atual"]},
    "PER_YESTERDAY": {"name": "PER_YESTERDAY", "label": "Ontem", "aliases": ["ontem", "dia anterior"]},
    "PER_LAST_7_DAYS": {"name": "PER_LAST_7_DAYS", "label": "Ultimos 7 dias", "aliases": ["semana passada", "ultimos 7 dias"]},
    "PER_LAST_30_DAYS": {"name": "PER_LAST_30_DAYS", "label": "Ultimos 30 dias", "aliases": ["ultimos 30 dias", "mes passado", "mes anterior"]},
    "PER_LAST_90_DAYS": {"name": "PER_LAST_90_DAYS", "label": "Ultimos 90 dias", "aliases": ["trimestre", "ultimos 90 dias", "ultimos 3 meses", "ultimos tres meses"]},
    "PER_CURRENT_MONTH": {"name": "PER_CURRENT_MONTH", "label": "Este mes", "aliases": ["este mes", "mes atual"]},
    "PER_CURRENT_YEAR": {"name": "PER_CURRENT_YEAR", "label": "Este ano", "aliases": ["este ano", "ano atual", "exercicio fiscal"]},
    "PER_LAST_YEAR": {"name": "PER_LAST_YEAR", "label": "Ano anterior", "aliases": ["ano anterior", "ano passado"]}
}


class CorporateConceptRef(BaseModel):
    id: str
    label: str
    concept_type: Literal["METRIC", "DIMENSION", "PERIOD", "ENTITY", "KPI", "FILTER"]
    aliases_matched: list[str] = Field(default_factory=list)


class CorporateFilterRef(BaseModel):
    concept_id: str
    label: str
    value: Any
    operator: str = "IN"


class SemanticScores(BaseModel):
    semantic_confidence_score: float = 0.0
    context_score: float = 0.0
    ambiguity_score: float = 0.0
    intent_quality_score: float = 0.0
    business_alignment_score: float = 0.0
    conversation_continuity_score: float = 0.0


class SemanticHypothesis(BaseModel):
    hypothesis_id: str
    description: str
    concepts: list[CorporateConceptRef] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    period: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = 0.0
    context_score: float = 0.0
    selected: bool = False
    rationale: str = ""


class CorporateIntentPlan(BaseModel):
    cip_id: str = Field(default_factory=lambda: f"cip_{uuid.uuid4().hex[:12]}")
    original_query: str
    primary_intent: str
    secondary_intents: list[str] = Field(default_factory=list)
    analytical_objective: str
    corporate_metrics: list[CorporateConceptRef] = Field(default_factory=list)
    corporate_dimensions: list[CorporateConceptRef] = Field(default_factory=list)
    filters: list[CorporateFilterRef] = Field(default_factory=list)
    period: CorporateConceptRef | None = None
    desired_granularity: str | None = None
    ordering: list[str] = Field(default_factory=list)
    groupings: list[str] = Field(default_factory=list)
    operational_context: dict[str, Any] = Field(default_factory=dict)
    suggested_visualization: str = "TABLE"
    hypotheses: list[SemanticHypothesis] = Field(default_factory=list)
    confidence_level: str = "MEDIA"
    ambiguity_level: str = "MODERADA"
    scores: SemanticScores = Field(default_factory=SemanticScores)
    selected_hypothesis_id: str | None = None
    explanation: dict[str, Any] = Field(default_factory=dict)
    audit: dict[str, Any] = Field(default_factory=dict)
    version: str = "CIP-1.0"

    def to_legacy_semantic_plan(self) -> dict[str, Any]:
        return {
            "metrics": [concept.id for concept in self.corporate_metrics],
            "dimensions": [concept.id for concept in self.corporate_dimensions],
            "period": self.period.id if self.period else None,
            "filters": {item.concept_id: item.value for item in self.filters},
            "corporate_intent_plan": self.model_dump(),
            "hypotheses": [hypothesis.model_dump() for hypothesis in self.hypotheses],
            "scores": self.scores.model_dump(),
            "ambiguity_level": self.ambiguity_level,
            "confidence_level": self.confidence_level,
        }


class CorporateSemanticIntelligenceEngine:
    """
    Corporate Semantic Intelligence Engine (CSIE)
    Traduz linguagem natural coloquial, regionalismos e erros ortograficos em IDs corporativos estaveis.
    Garante isolamento fisico de colunas e governanca contextual dinamica sem tabelas fixas.
    """

    def clean_text(self, text: str) -> str:
        """Limpa o texto, removendo acentos, excesso de espacos e pontuacao."""
        if not text:
            return ""
        text = text.lower().strip()
        normalized = unicodedata.normalize("NFKD", text)
        without_accents = "".join(c for c in normalized if not unicodedata.combining(c))
        clean = re.sub(r"[^a-z0-9\s_]", " ", without_accents)
        return " ".join(clean.split())

    def _contains_alias(self, text_clean: str, alias: str) -> bool:
        alias_clean = self.clean_text(alias)
        if not alias_clean:
            return False
        if " " in alias_clean:
            return alias_clean in text_clean
        return re.search(rf"\b{re.escape(alias_clean)}\b", text_clean) is not None

    def _detect_concepts_from_text(self, text_clean: str) -> dict[str, Any]:
        metrics: list[str] = []
        dimensions: list[str] = []
        period: str | None = None

        for metric_id, metric_info in STABLE_METRICS.items():
            aliases = [metric_info["name"], *metric_info.get("aliases", [])]
            if any(self._contains_alias(text_clean, alias) for alias in aliases):
                metrics.append(metric_id)

        for dimension_id, dimension_info in STABLE_DIMENSIONS.items():
            aliases = [dimension_info["name"], *dimension_info.get("aliases", [])]
            if any(self._contains_alias(text_clean, alias) for alias in aliases):
                dimensions.append(dimension_id)

        for period_id, period_info in STABLE_PERIODS.items():
            aliases = [period_info["name"], period_info.get("label", ""), *period_info.get("aliases", [])]
            if any(self._contains_alias(text_clean, alias) for alias in aliases):
                period = period_id
                break

        if re.search(r"\bultimos?\s+3\s+mes(?:es)?\b", text_clean):
            period = "PER_LAST_90_DAYS"
        elif re.search(r"\bultimos?\s+30\s+dias?\b", text_clean):
            period = "PER_LAST_30_DAYS"
        elif re.search(r"\bultimos?\s+7\s+dias?\b", text_clean):
            period = "PER_LAST_7_DAYS"

        if any(term in text_clean for term in ("vendedor", "vendedores", "representante", "consultor")):
            dimensions.append("DIM_002")
        if any(term in text_clean for term in ("produto", "produtos", "item", "itens", "sku", "mercadoria")):
            dimensions.append("DIM_003")
        if any(term in text_clean for term in ("cliente", "clientes", "comprador", "parceiro")):
            dimensions.append("DIM_001")

        primary_intent = self._classify_intent(text_clean)
        asks_financial_return = any(
            term in text_clean
            for term in (
                "retorno financeiro",
                "resultado financeiro",
                "retorno para empresa",
                "maior retorno",
                "rentabilidade",
                "lucratividade",
                "margem",
                "lucro",
            )
        )
        asks_volume = any(
            term in text_clean
            for term in ("mais vendidos", "quantidade", "volume", "unidades", "qtd", "pedidos")
        )

        if "DIM_003" in dimensions and asks_financial_return:
            metrics.extend(["MET_001", "MET_004"])
        elif "DIM_003" in dimensions and asks_volume:
            metrics.extend(["MET_006", "MET_001"])
        elif "DIM_003" in dimensions and primary_intent == "RANKING" and not metrics:
            metrics.extend(["MET_001", "MET_006"])

        if "DIM_002" in dimensions and primary_intent == "RANKING" and not metrics:
            metrics.append("MET_001")

        if primary_intent in ("RANKING", "COMPARACAO", "EVOLUCAO", "DISTRIBUICAO") and not metrics:
            metrics.append("MET_001")

        return {
            "metrics": list(dict.fromkeys(metrics)),
            "dimensions": list(dict.fromkeys(dimensions)),
            "period": period,
            "filters": {},
        }


    def _concept_ref(self, concept_id: str, concept_type: Literal["METRIC", "DIMENSION", "PERIOD", "ENTITY", "KPI", "FILTER"]) -> CorporateConceptRef:
        source = {}
        if concept_type == "METRIC":
            source = STABLE_METRICS.get(concept_id, {})
        elif concept_type == "DIMENSION":
            source = STABLE_DIMENSIONS.get(concept_id, {})
        elif concept_type == "PERIOD":
            source = STABLE_PERIODS.get(concept_id, {})
        return CorporateConceptRef(
            id=concept_id,
            label=str(source.get("label") or source.get("name") or concept_id),
            concept_type=concept_type,
        )

    def _classify_intent(self, text_clean: str) -> str:
        if any(term in text_clean for term in ("comparar", "comparacao", "versus", " vs ", "percentual", "a mais", "a menos")):
            return "COMPARACAO"
        if any(term in text_clean for term in ("top", "ranking", "maior", "menor", "lider", "mais vendido", "mais vendeu")):
            return "RANKING"
        if any(term in text_clean for term in ("evolucao", "historico", "tendencia", "ao longo")):
            return "EVOLUCAO"
        if any(term in text_clean for term in ("distribuicao", "participacao", "share", "proporcao")):
            return "DISTRIBUICAO"
        if any(term in text_clean for term in ("por que", "porque", "diagnostico", "causa")):
            return "DIAGNOSTICO"
        if any(term in text_clean for term in ("anomalia", "fora do normal", "queda", "crescimento anormal")):
            return "ANOMALIA"
        if any(term in text_clean for term in ("previsao", "projecao", "projetar")):
            return "PROJECAO"
        if any(term in text_clean for term in ("resumo", "executivo", "visao geral")):
            return "RESUMO_EXECUTIVO"
        return "CONSULTA"

    def _suggest_visualization(self, primary_intent: str, dimensions: list[str]) -> str:
        if primary_intent == "RANKING":
            return "BAR"
        if primary_intent in ("EVOLUCAO", "PROJECAO"):
            return "LINE"
        if primary_intent == "DISTRIBUICAO":
            return "PIE"
        if primary_intent == "COMPARACAO":
            return "BAR"
        if not dimensions:
            return "KPI"
        return "TABLE"

    def _confidence_level(self, score: float) -> str:
        if score >= 90:
            return "ALTA"
        if score >= 70:
            return "MEDIA"
        if score >= 50:
            return "BAIXA_CONTROLADA"
        return "INSUFICIENTE"

    def _ambiguity_level(self, score: float, hypotheses_count: int) -> str:
        if score >= 90 and hypotheses_count <= 1:
            return "BAIXA"
        if score >= 70:
            return "MODERADA"
        if score >= 50:
            return "ALTA"
        return "CRITICA"

    def _build_scores(self, confidence_0_to_1: float, context_score: float, hypotheses_count: int) -> SemanticScores:
        semantic_score = max(0.0, min(100.0, confidence_0_to_1 * 100))
        ambiguity_score = max(0.0, min(100.0, 100.0 - semantic_score + max(0, hypotheses_count - 1) * 6))
        return SemanticScores(
            semantic_confidence_score=semantic_score,
            context_score=context_score,
            ambiguity_score=ambiguity_score,
            intent_quality_score=max(50.0, semantic_score - (5 if hypotheses_count > 1 else 0)),
            business_alignment_score=max(50.0, semantic_score),
            conversation_continuity_score=context_score,
        )

    def _build_hypotheses(
        self,
        text_clean: str,
        metrics: list[str],
        dimensions: list[str],
        period: str | None,
        filters: dict[str, Any],
        confidence_score: float,
    ) -> list[SemanticHypothesis]:
        hypotheses: list[SemanticHypothesis] = []
        concepts = [self._concept_ref(m, "METRIC") for m in metrics] + [self._concept_ref(d, "DIMENSION") for d in dimensions]
        hypotheses.append(
            SemanticHypothesis(
                hypothesis_id="H1",
                description="Interpretacao principal com base nos conceitos corporativos identificados.",
                concepts=concepts,
                metrics=metrics,
                dimensions=dimensions,
                period=period,
                filters=filters,
                confidence_score=round(confidence_score * 100, 2),
                context_score=80.0,
                selected=True,
                rationale="Maior aderencia semantica aos termos informados pelo usuario.",
            )
        )

        if "quem vendeu mais" in text_clean or ("vendeu mais" in text_clean and not metrics):
            hypotheses = [
                SemanticHypothesis(
                    hypothesis_id="H1",
                    description="Ranking por maior faturamento.",
                    concepts=[self._concept_ref("MET_001", "METRIC"), self._concept_ref("DIM_002", "DIMENSION")],
                    metrics=["MET_001"],
                    dimensions=["DIM_002"],
                    period=period,
                    filters=filters,
                    confidence_score=97.0,
                    context_score=85.0,
                    selected=True,
                    rationale="No contexto comercial, 'vendeu mais' normalmente representa faturamento.",
                ),
                SemanticHypothesis(
                    hypothesis_id="H2",
                    description="Ranking por maior margem.",
                    concepts=[self._concept_ref("MET_004", "METRIC"), self._concept_ref("DIM_002", "DIMENSION")],
                    metrics=["MET_004"],
                    dimensions=["DIM_002"],
                    period=period,
                    filters=filters,
                    confidence_score=91.0,
                    context_score=80.0,
                    rationale="Tambem pode representar melhor retorno percentual.",
                ),
                SemanticHypothesis(
                    hypothesis_id="H3",
                    description="Ranking por maior quantidade vendida.",
                    concepts=[self._concept_ref("MET_006", "METRIC"), self._concept_ref("DIM_002", "DIMENSION")],
                    metrics=["MET_006"],
                    dimensions=["DIM_002"],
                    period=period,
                    filters=filters,
                    confidence_score=86.0,
                    context_score=78.0,
                    rationale="Interpretacao plausivel quando o usuario fala em volume.",
                ),
            ]

        if "DIM_003" in dimensions and any(term in text_clean for term in ("mais vendidos", "mais vendido", "produto que mais", "produtos que mais")):
            hypotheses = [
                SemanticHypothesis(
                    hypothesis_id="H1",
                    description="Ranking de produtos por quantidade vendida.",
                    concepts=[self._concept_ref("MET_006", "METRIC"), self._concept_ref("DIM_003", "DIMENSION")],
                    metrics=["MET_006"],
                    dimensions=["DIM_003"],
                    period=period,
                    filters=filters,
                    confidence_score=94.0,
                    context_score=84.0,
                    selected=True,
                    rationale="'Produtos mais vendidos' normalmente indica volume/unidades vendidas.",
                ),
                SemanticHypothesis(
                    hypothesis_id="H2",
                    description="Ranking de produtos por receita gerada.",
                    concepts=[self._concept_ref("MET_001", "METRIC"), self._concept_ref("DIM_003", "DIMENSION")],
                    metrics=["MET_001"],
                    dimensions=["DIM_003"],
                    period=period,
                    filters=filters,
                    confidence_score=90.0,
                    context_score=82.0,
                    rationale="Em contexto comercial, 'mais vendido' tambem pode significar maior faturamento.",
                ),
            ]

        if "DIM_003" in dimensions and any(term in text_clean for term in ("retorno financeiro", "maior retorno", "rentabilidade", "lucratividade")):
            hypotheses = [
                SemanticHypothesis(
                    hypothesis_id="H1",
                    description="Produto com maior receita gerada.",
                    concepts=[self._concept_ref("MET_001", "METRIC"), self._concept_ref("DIM_003", "DIMENSION")],
                    metrics=["MET_001"],
                    dimensions=["DIM_003"],
                    period=period,
                    filters=filters,
                    confidence_score=93.0,
                    context_score=84.0,
                    selected=True,
                    rationale="'Retorno financeiro' foi interpretado como valor financeiro gerado para a empresa.",
                ),
                SemanticHypothesis(
                    hypothesis_id="H2",
                    description="Produto com melhor margem de lucro.",
                    concepts=[self._concept_ref("MET_004", "METRIC"), self._concept_ref("DIM_003", "DIMENSION")],
                    metrics=["MET_004"],
                    dimensions=["DIM_003"],
                    period=period,
                    filters=filters,
                    confidence_score=88.0,
                    context_score=80.0,
                    rationale="Retorno financeiro tambem pode indicar rentabilidade percentual.",
                ),
            ]

        return hypotheses

    def _build_cip_from_stable_plan(
        self,
        pergunta: str,
        stable_plan: dict[str, Any],
        confidence_0_to_1: float,
        origin: str,
        context: dict[str, Any] | None = None,
    ) -> CorporateIntentPlan:
        text_clean = self.clean_text(pergunta)
        metrics = list(dict.fromkeys(stable_plan.get("metrics", []) or []))
        dimensions = list(dict.fromkeys(stable_plan.get("dimensions", []) or []))
        period_id = stable_plan.get("period")
        filters_raw = dict(stable_plan.get("filters", {}) or {})
        primary_intent = self._classify_intent(text_clean)
        hypotheses = self._build_hypotheses(text_clean, metrics, dimensions, period_id, filters_raw, confidence_0_to_1)
        scores = self._build_scores(confidence_0_to_1, context_score=80.0 if context else 65.0, hypotheses_count=len(hypotheses))

        return CorporateIntentPlan(
            original_query=pergunta,
            primary_intent=primary_intent,
            secondary_intents=[],
            analytical_objective=f"{primary_intent}: interpretar a solicitacao usando apenas conceitos corporativos.",
            corporate_metrics=[self._concept_ref(metric, "METRIC") for metric in metrics],
            corporate_dimensions=[self._concept_ref(dimension, "DIMENSION") for dimension in dimensions],
            filters=[
                CorporateFilterRef(
                    concept_id=concept_id,
                    label=self._concept_ref(concept_id, "DIMENSION").label,
                    value=value,
                )
                for concept_id, value in filters_raw.items()
            ],
            period=self._concept_ref(period_id, "PERIOD") if period_id else None,
            desired_granularity="conceitual",
            ordering=["ranking"] if primary_intent == "RANKING" else [],
            groupings=dimensions,
            operational_context=context or {},
            suggested_visualization=self._suggest_visualization(primary_intent, dimensions),
            hypotheses=hypotheses,
            confidence_level=self._confidence_level(scores.semantic_confidence_score),
            ambiguity_level=self._ambiguity_level(scores.semantic_confidence_score, len(hypotheses)),
            scores=scores,
            selected_hypothesis_id=next((h.hypothesis_id for h in hypotheses if h.selected), None),
            explanation={
                "origin": origin,
                "selected_reason": "Hipotese selecionada por maior aderencia semantica e contexto corporativo.",
                "discarded_hypotheses": [h.hypothesis_id for h in hypotheses if not h.selected],
                "policy": "Somente solicitar esclarecimento abaixo de 50 quando nao houver conceitos suficientes.",
            },
            audit={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "CSIE",
                "contains_physical_metadata": False,
            },
        )

    def _match_static_fast(self, text_clean: str) -> tuple[dict[str, Any] | None, float]:
        """Tenta encontrar correspondencias nos mapeamentos locais."""
        detected_plan = self._detect_concepts_from_text(text_clean)
        if detected_plan["metrics"] or detected_plan["dimensions"] or detected_plan["period"]:
            score = 0.95
            return detected_plan, score

        # 1. Correspondencia exata de aliases ou do nome (maior prioridade)
        for m_id, m_info in STABLE_METRICS.items():
            if m_info["name"] == text_clean or text_clean in m_info["aliases"]:
                return {"metrics": [m_id], "dimensions": [], "period": None, "filters": {}}, 0.95

        for d_id, d_info in STABLE_DIMENSIONS.items():
            if d_info["name"] == text_clean or text_clean in d_info["aliases"]:
                return {"metrics": [], "dimensions": [d_id], "period": None, "filters": {}}, 0.95

        for p_id, p_info in STABLE_PERIODS.items():
            if p_info["name"] == text_clean or text_clean in p_info["aliases"]:
                return {"metrics": [], "dimensions": [], "period": p_id, "filters": {}}, 0.95

        # 2. Correspondencia parcial (menor prioridade)
        for m_id, m_info in STABLE_METRICS.items():
            for alias in [m_info["name"], *m_info["aliases"]]:
                if alias in text_clean or text_clean in alias:
                    if len(text_clean) >= 6 and len(alias) >= 6:
                        return {"metrics": [m_id], "dimensions": [], "period": None, "filters": {}}, 0.95

        for d_id, d_info in STABLE_DIMENSIONS.items():
            for alias in [d_info["name"], *d_info["aliases"]]:
                if alias in text_clean or text_clean in alias:
                    if len(text_clean) >= 6 and len(alias) >= 6:
                        return {"metrics": [], "dimensions": [d_id], "period": None, "filters": {}}, 0.95

        return None, 0.0

    async def generate_corporate_intent_plan(
        self,
        pergunta: str,
        tenant_id: uuid.UUID,
        db: AsyncSession,
        client: AsyncOpenAI | None = None,
        context: dict[str, Any] | None = None,
    ) -> tuple[CorporateIntentPlan, float, str]:
        """
        Produces a Corporate Intent Plan (CIP) using only corporate concepts.
        It does not select views, tables, columns, SQL, joins, schemas, or ERP details.
        """
        start_time = datetime.now()
        text_clean = self.clean_text(pergunta)

        try:
            memory = await get_semantic_memory_record(db, tenant_id, text_clean)
            if memory and memory.score >= 90.0:
                await increment_memory_frequencia(db, memory)
                obj_res = memory.objeto_resolvido
                if isinstance(obj_res, str):
                    obj_res = json.loads(obj_res)
                cip = self._build_cip_from_stable_plan(
                    pergunta=pergunta,
                    stable_plan=obj_res if isinstance(obj_res, dict) else {},
                    confidence_0_to_1=min(float(memory.score) / 100.0, 1.0),
                    origin="MEMORY",
                    context=context,
                )
                elapsed = (datetime.now() - start_time).total_seconds() * 1000
                logger.info("[CSIE] CIP gerado via memoria | tempo=%.2fms score=%.2f", elapsed, memory.score)
                return cip, min(float(memory.score) / 100.0, 1.0), "MEMORY"
        except Exception as exc:
            logger.error("[CSIE] Falha ao acessar memoria semantica: %s", exc)

        obj_fast, score_fast = self._match_static_fast(text_clean)
        if obj_fast and score_fast >= 0.50:
            cip = self._build_cip_from_stable_plan(
                pergunta=pergunta,
                stable_plan=obj_fast,
                confidence_0_to_1=score_fast,
                origin="STATIC",
                context=context,
            )
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            logger.info("[CSIE] CIP gerado via dicionario corporativo | tempo=%.2fms score=%.2f", elapsed, score_fast)
            return cip, score_fast, "STATIC"

        prompt_system = f"""
Voce e o Corporate Semantic Intelligence Engine (CSIE) do LuminaAI.
Sua unica responsabilidade e gerar um Corporate Intent Plan conceitual.

Regras obrigatorias:
- Use somente IDs corporativos de metricas, dimensoes e periodos.
- Nunca cite tabelas, views, colunas, SQL, joins, schemas ou detalhes de ERP.
- Se houver ambiguidade, gere hipoteses em vez de rejeitar automaticamente.
- Retorne JSON puro.

Metricas corporativas disponiveis:
{json.dumps({k: {"label": v["label"], "aliases": v["aliases"]} for k, v in STABLE_METRICS.items()}, indent=2, ensure_ascii=False)}

Dimensoes corporativas disponiveis:
{json.dumps({k: {"label": v["label"], "aliases": v["aliases"]} for k, v in STABLE_DIMENSIONS.items()}, indent=2, ensure_ascii=False)}

Periodos corporativos disponiveis:
{json.dumps({k: {"label": v["label"], "aliases": v["aliases"]} for k, v in STABLE_PERIODS.items()}, indent=2, ensure_ascii=False)}

Formato esperado:
{{
  "metrics": ["MET_001"],
  "dimensions": ["DIM_002"],
  "period": "PER_CURRENT_MONTH",
  "filters": {{"DIM_003": ["valor"]}},
  "confidence": 0.85,
  "hypotheses": [
    {{"description": "...", "metrics": ["MET_001"], "dimensions": ["DIM_002"], "confidence_score": 90}}
  ]
}}
"""

        try:
            resolved_model_used = ai_credential_manager.validate_authorized_model(None)

            async def _request_completion(
                selected_client: AsyncOpenAI,
                resolved_model: str,
                _lease: Any,
            ) -> Any:
                nonlocal resolved_model_used
                resolved_model_used = resolved_model
                return await selected_client.chat.completions.create(
                    model=resolved_model,
                    messages=[
                        {"role": "system", "content": prompt_system},
                        {"role": "user", "content": pergunta},
                    ],
                    temperature=0.0,
                    response_format={"type": "json_object"},
                )

            if client:
                response = await _request_completion(client, resolved_model_used, None)
            else:
                response = await ai_invocation_manager.invoke(
                    tenant_id=tenant_id,
                    db=db,
                    requested_model=resolved_model_used,
                    purpose="csie_corporate_intent_plan",
                    context={
                        "query": pergunta,
                        "fresh_data_required": True,
                        "requires_precision": True,
                        "expected_confidence": 90,
                        "semantic_similarity_score": 0,
                    },
                    force_ai=True,
                    allow_response_reuse=False,
                    operation=_request_completion,
                )
            raw_json = json.loads(response.choices[0].message.content)
            confidence = float(raw_json.get("confidence", 0.70))
            stable_plan = {
                "metrics": raw_json.get("metrics", []),
                "dimensions": raw_json.get("dimensions", []),
                "period": raw_json.get("period"),
                "filters": raw_json.get("filters", {}),
            }
            cip = self._build_cip_from_stable_plan(
                pergunta=pergunta,
                stable_plan=stable_plan,
                confidence_0_to_1=confidence,
                origin="IA",
                context=context,
            )
            usage = getattr(response, "usage", None)
            cip.audit["model"] = resolved_model_used
            cip.audit["tokens_consumed"] = int(getattr(usage, "total_tokens", 0) or 0)

            llm_hypotheses = raw_json.get("hypotheses") or []
            if isinstance(llm_hypotheses, list) and llm_hypotheses:
                cip.hypotheses = []
                for idx, item in enumerate(llm_hypotheses, start=1):
                    if not isinstance(item, dict):
                        continue
                    h_metrics = list(item.get("metrics") or stable_plan["metrics"])
                    h_dimensions = list(item.get("dimensions") or stable_plan["dimensions"])
                    cip.hypotheses.append(
                        SemanticHypothesis(
                            hypothesis_id=f"H{idx}",
                            description=str(item.get("description") or "Hipotese semantica"),
                            concepts=[self._concept_ref(m, "METRIC") for m in h_metrics]
                            + [self._concept_ref(d, "DIMENSION") for d in h_dimensions],
                            metrics=h_metrics,
                            dimensions=h_dimensions,
                            period=item.get("period") or stable_plan.get("period"),
                            filters=dict(item.get("filters") or stable_plan.get("filters") or {}),
                            confidence_score=float(item.get("confidence_score") or item.get("confidence") or confidence * 100),
                            context_score=float(item.get("context_score") or 75.0),
                            selected=idx == 1,
                            rationale=str(item.get("rationale") or "Hipotese gerada pela interpretacao semantica."),
                        )
                    )
                if cip.hypotheses:
                    cip.selected_hypothesis_id = cip.hypotheses[0].hypothesis_id
                    cip.ambiguity_level = self._ambiguity_level(cip.scores.semantic_confidence_score, len(cip.hypotheses))

            if confidence >= 0.90:
                await create_semantic_memory_record(
                    db=db,
                    tenant_id=tenant_id,
                    text_clean=text_clean,
                    objeto_resolvido=cip.to_legacy_semantic_plan(),
                    score=confidence * 100,
                    confianca="ALTA" if confidence >= 0.95 else "MEDIA",
                    origem="IA",
                )

            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            logger.info("[CSIE] CIP gerado via IA | tempo=%.2fms score=%.2f", elapsed, confidence)
            return cip, confidence, "IA"

        except AICMError as ia_exc:
            logger.warning("[CSIE] AICM indisponivel; gerando CIP local seguro: %s", ia_exc)
            fallback_plan = {"metrics": ["MET_001"], "dimensions": [], "period": "PER_CURRENT_MONTH", "filters": {}}
            cip = self._build_cip_from_stable_plan(
                pergunta=pergunta,
                stable_plan=fallback_plan,
                confidence_0_to_1=0.50,
                origin="AICM_UNAVAILABLE",
                context=context,
            )
            cip.audit["ai_unavailable"] = True
            cip.audit["aicm_error"] = type(ia_exc).__name__
            return cip, 0.50, "AICM_UNAVAILABLE"
        except Exception as ia_exc:
            logger.warning("[CSIE] IA indisponivel; gerando CIP local seguro: %s", ia_exc)
            fallback_plan = {"metrics": ["MET_001"], "dimensions": [], "period": "PER_CURRENT_MONTH", "filters": {}}
            cip = self._build_cip_from_stable_plan(
                pergunta=pergunta,
                stable_plan=fallback_plan,
                confidence_0_to_1=0.50,
                origin="FALLBACK",
                context=context,
            )
            return cip, 0.50, "FALLBACK"

    async def resolve_query(
        self,
        pergunta: str,
        tenant_id: uuid.UUID,
        db: AsyncSession,
        client: AsyncOpenAI | None = None,
    ) -> tuple[dict[str, Any], float, str]:
        """Compatibility wrapper returning the legacy semantic object."""
        text_clean = self.clean_text(pergunta)
        try:
            memory = await get_semantic_memory_record(db, tenant_id, text_clean)
            if memory and memory.score >= 90.0:
                await increment_memory_frequencia(db, memory)
                obj_res = memory.objeto_resolvido
                if isinstance(obj_res, str):
                    obj_res = json.loads(obj_res)
                return obj_res, float(memory.score), "MEMORY"
        except Exception as exc:
            logger.error("[CSIE] Falha ao acessar memoria semantica: %s", exc)

        cip, score, origin = await self.generate_corporate_intent_plan(
            pergunta=pergunta,
            tenant_id=tenant_id,
            db=db,
            client=client,
        )
        return cip.to_legacy_semantic_plan(), score, origin

    async def translate_plan_to_physical(
        self,
        stable_plan: dict[str, Any],
        view_name: str,
        tenant_id: uuid.UUID,
        meta_catalog: list[Any],
        db: AsyncSession | None = None,
        semantic_version: str | None = None,
        mapping_version: str | None = None,
        blueprint_version: str | None = None,
    ) -> dict[str, Any]:
        """
        Backward-compatible facade. Physical/execution mapping belongs to CAL,
        not to CSIE. The view/meta arguments are kept only to avoid breaking
        older callers.
        """
        from services.corporate_abstraction_layer import corporate_abstraction_layer

        return await corporate_abstraction_layer.translate_plan_to_execution(
            stable_plan=stable_plan,
            tenant_id=tenant_id,
            db=db,
            semantic_version=semantic_version,
            mapping_version=mapping_version,
            blueprint_version=blueprint_version,
        )

    def resolve_metric_fallback(self, metric: str) -> str | None:
        """
        Chamado pelo validador antes de rejeitar um plano com metrica desconhecida.
        Tenta mapear o termo desconhecido para a chave semantica corporativa oficial.
        """
        clean_name = self.clean_text(metric)
        for m_id, m_info in STABLE_METRICS.items():
            if clean_name in m_info["aliases"] or m_info["name"] == clean_name:
                return m_info["name"]
        return None


# Singleton export
csie = CorporateSemanticIntelligenceEngine()
