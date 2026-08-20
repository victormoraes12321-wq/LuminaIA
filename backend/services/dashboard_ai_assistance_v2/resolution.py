from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from contracts.dashboard_ai_assistance_v2 import (
    DashboardAiClarificationOptionV2,
    DashboardAiClarificationQuestionV2,
    DashboardAiDesignIntentV2,
    DashboardAiProposalEvidenceV2,
    DashboardDesignSpecV2,
    DashboardLayoutDesignSpecV2,
    DashboardWidgetDesignSpecV2,
)
from services.metric_registry import METRIC_DEFINITIONS

from .integrity import checksum, normalized_key

_METRICS = {
    "faturamento comercial": ("metric.revenue", "faturamento_comercial", "Faturamento comercial"),
    "faturamento bruto": ("metric.gross.revenue", "total_bruto", "Faturamento bruto"),
    "ticket medio": ("metric.average.ticket", "ticket_medio", "Ticket médio"),
    "desconto total": ("metric.discount.total", "desconto_total", "Desconto total"),
    "desconto medio": ("metric.discount.average", "desconto_medio", "Desconto médio"),
    "lucro": ("metric.gross.profit", "lucro", "Lucro"),
    "contas em aberto": ("metric.open.accounts", "vendas_nao_faturadas", "Contas em aberto"),
    "estoque": ("metric.inventory.balance", "total_movimentos_view", "Saldo de estoque"),
}
_DIMENSIONS = {
    "produto": "dimension.product", "filial": "dimension.branch", "vendedor": "dimension.seller",
    "categoria": "dimension.category", "cliente": "dimension.customer", "mes": "dimension.month",
}


@dataclass(frozen=True, slots=True)
class DashboardDesignResolutionV2:
    design_spec: DashboardDesignSpecV2 | None
    clarifications: tuple[DashboardAiClarificationQuestionV2, ...]
    evidence: tuple[DashboardAiProposalEvidenceV2, ...]
    blocking_code: str | None = None


def _evidence(kind: str, canonical: str, label: str, authority: str) -> DashboardAiProposalEvidenceV2:
    basis = {"kind": kind, "canonical": canonical, "authority": authority}
    return DashboardAiProposalEvidenceV2(
        evidence_id=f"evidence.{checksum(basis)[:24]}", evidence_type=kind,
        canonical_reference=canonical, public_label=label, authority_version=authority,
        checksum=checksum(basis),
    )


class DashboardDesignSpecServiceV2:
    def resolve(self, *, proposal_id: str, intent: DashboardAiDesignIntentV2) -> DashboardDesignResolutionV2:
        questions: list[DashboardAiClarificationQuestionV2] = []
        metric_ids: list[str] = []
        evidence: list[DashboardAiProposalEvidenceV2] = []
        mentions = tuple(normalized_key(item) for item in intent.metric_mentions)
        if not mentions and intent.objective.template_hint not in {"EXECUTIVE_OVERVIEW", "RECEIVABLES", "INVENTORY"}:
            questions.append(self._metric_question(proposal_id, "metric.required", "Qual métrica principal deve orientar o dashboard?"))
        for mention in mentions:
            if mention == "faturamento":
                questions.append(self._metric_question(proposal_id, "metric.revenue.ambiguity", "Você quer faturamento comercial ou bruto?"))
                continue
            row = _METRICS.get(mention)
            if row is None or row[1] not in METRIC_DEFINITIONS:
                return DashboardDesignResolutionV2(None, (), (), "DASHBOARD_AI_UNKNOWN_METRIC")
            metric_ids.append(row[0])
            evidence.append(_evidence("METRIC_REGISTRY", row[0], row[2], "metric-registry/1"))
        template = intent.objective.template_hint or "CUSTOM"
        if template == "EXECUTIVE_OVERVIEW" and not metric_ids:
            metric_ids = ["metric.revenue", "metric.average.ticket", "metric.discount.total", "metric.open.accounts"]
            for canonical in metric_ids:
                row = next(item for item in _METRICS.values() if item[0] == canonical)
                evidence.append(_evidence("METRIC_REGISTRY", canonical, row[2], "metric-registry/1"))
        elif template == "RECEIVABLES" and not metric_ids:
            metric_ids = ["metric.open.accounts"]
            evidence.append(_evidence("METRIC_REGISTRY", metric_ids[0], "Contas em aberto", "metric-registry/1"))
        elif template == "INVENTORY" and not metric_ids:
            metric_ids = ["metric.inventory.balance"]
            evidence.append(_evidence("METRIC_REGISTRY", metric_ids[0], "Saldo de estoque", "metric-registry/1"))
        dimensions: list[str] = []
        for mention in intent.dimension_mentions:
            canonical = _DIMENSIONS.get(normalized_key(mention))
            if canonical is None:
                return DashboardDesignResolutionV2(None, (), (), "DASHBOARD_AI_UNKNOWN_DIMENSION")
            dimensions.append(canonical)
            evidence.append(_evidence("CATALOG", canonical, mention, "analytical-catalog/1.0.0"))
        if template == "PRODUCT_RANKING" and "dimension.product" not in dimensions:
            dimensions.append("dimension.product")
        period_id = self._period(intent, proposal_id, questions)
        if questions:
            return DashboardDesignResolutionV2(None, tuple(questions), tuple(evidence))
        widgets: list[DashboardWidgetDesignSpecV2] = []
        for index, metric in enumerate(metric_ids):
            widgets.append(DashboardWidgetDesignSpecV2(widget_key=f"widget.ai.kpi.{index + 1}", purpose=f"Apresentar {metric}", widget_type="KPI", metric_ids=(metric,)))
        if "dimension.month" in dimensions and metric_ids:
            widgets.append(DashboardWidgetDesignSpecV2(widget_key="widget.ai.series", purpose="Mostrar evolução temporal", widget_type="LINE", metric_ids=(metric_ids[0],), dimension_ids=("dimension.month",)))
        if template == "PRODUCT_RANKING" and metric_ids:
            widgets.append(DashboardWidgetDesignSpecV2(widget_key="widget.ai.ranking", purpose="Ordenar produtos", widget_type="RANKING", metric_ids=(metric_ids[0],), dimension_ids=("dimension.product",), top_n=10))
        if template == "COMPARATIVE_ANALYSIS" and metric_ids:
            widgets.append(DashboardWidgetDesignSpecV2(widget_key="widget.ai.comparison", purpose="Comparar períodos", widget_type="COMPARISON", metric_ids=(metric_ids[0],)))
        title = intent.objective.summary[:120]
        resolution_basis = {"metrics": metric_ids, "dimensions": dimensions, "period": period_id, "template": template}
        spec = DashboardDesignSpecV2(
            design_spec_id=f"design.{checksum(resolution_basis)[:24]}", title=title,
            description=f"Proposta governada para: {intent.objective.summary[:900]}", template_id=template,
            audience=intent.audience, metric_ids=tuple(metric_ids), dimension_ids=tuple(dimensions),
            canonical_period_id=period_id, widgets=tuple(widgets), layout=DashboardLayoutDesignSpecV2(),
            resolution_checksum=checksum(resolution_basis),
        )
        evidence.append(_evidence("TEMPORAL", period_id, "Período normalizado", "lumina.temporal.pt-BR/1.0"))
        return DashboardDesignResolutionV2(spec, (), tuple(evidence))

    @staticmethod
    def _metric_question(proposal_id: str, key: str, prompt: str) -> DashboardAiClarificationQuestionV2:
        return DashboardAiClarificationQuestionV2(
            question_id=f"question.{checksum({'p': proposal_id, 'k': key})[:24]}", kind="METRIC", prompt=prompt,
            options=(
                DashboardAiClarificationOptionV2(option_id="option.metric.revenue", label="Faturamento comercial", description="Receita comercial governada.", canonical_reference="metric.revenue"),
                DashboardAiClarificationOptionV2(option_id="option.metric.gross.revenue", label="Faturamento bruto", description="Total bruto governado.", canonical_reference="metric.gross.revenue"),
            ),
        )

    @staticmethod
    def _period(intent: DashboardAiDesignIntentV2, proposal_id: str, questions: list[DashboardAiClarificationQuestionV2]) -> str:
        mentions = tuple(normalized_key(item) for item in intent.period_mentions)
        if not mentions:
            return "period.last.closed.month"
        if "hoje" in mentions:
            return "period.today"
        if "ontem" in mentions:
            return "period.yesterday"
        if "junho" in mentions:
            return "period.2026.06"
        if "julho" in mentions:
            return "period.2026.07"
        if any(item in {"este mes", "mes atual"} for item in mentions):
            questions.append(DashboardAiClarificationQuestionV2(
                question_id=f"question.{checksum({'p': proposal_id, 'k': 'period.current'})[:24]}", kind="PERIOD",
                prompt="Deseja o mês em andamento ou o último mês fechado?",
                options=(
                    DashboardAiClarificationOptionV2(option_id="option.period.current", label="Mês em andamento", description="Inclui o período parcial atual.", canonical_reference="period.current.month"),
                    DashboardAiClarificationOptionV2(option_id="option.period.closed", label="Último mês fechado", description="Usa somente um mês completo.", canonical_reference="period.last.closed.month"),
                ),
            ))
            return "period.pending"
        return "period.last.closed.month"

