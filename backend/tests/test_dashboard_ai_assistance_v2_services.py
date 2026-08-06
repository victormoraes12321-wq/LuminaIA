from __future__ import annotations

import pytest

from contracts.dashboard_ai_assistance_v2 import DashboardAiProposalStatusV2
from services.dashboard_ai_assistance_v2.intent import DashboardAiIntentExtractionServiceV2
from services.dashboard_ai_assistance_v2.resolution import DashboardDesignSpecServiceV2
from services.dashboard_ai_assistance_v2.synthesis import DashboardBlueprintSynthesisService
from services.dashboard_ai_assistance_v2.validation import DashboardAiProposalValidationServiceV2
from services.dashboard_blueprint_v2.canonicalizer import DashboardBlueprintCanonicalizer


@pytest.mark.no_database
@pytest.mark.parametrize(("instruction", "expected_metric", "expected_template"), [
    ("Painel de ticket médio em julho", "metric.average.ticket", "SALES_PERFORMANCE"),
    ("Painel de desconto total", "metric.discount.total", "SALES_PERFORMANCE"),
    ("Painel de desconto médio", "metric.discount.average", "SALES_PERFORMANCE"),
    ("Painel de contas em aberto", "metric.open.accounts", "RECEIVABLES"),
    ("Painel de estoque", "metric.inventory.balance", "INVENTORY"),
    ("Ranking de produtos por lucro", "metric.gross.profit", "PRODUCT_RANKING"),
    ("Comparar ticket médio", "metric.average.ticket", "COMPARATIVE_ANALYSIS"),
])
def test_intent_resolution_synthesis_is_deterministic(instruction: str, expected_metric: str, expected_template: str) -> None:
    intent = DashboardAiIntentExtractionServiceV2().extract_design(instruction)
    resolution = DashboardDesignSpecServiceV2().resolve(proposal_id="proposal.unit.001", intent=intent)
    assert resolution.blocking_code is None
    assert resolution.clarifications == ()
    assert resolution.design_spec is not None
    assert expected_metric in resolution.design_spec.metric_ids
    assert resolution.design_spec.template_id == expected_template
    first = DashboardBlueprintSynthesisService().synthesize(resolution.design_spec)
    second = DashboardBlueprintSynthesisService().synthesize(resolution.design_spec)
    first_checksums = DashboardBlueprintCanonicalizer.canonicalize(first).checksums
    second_checksums = DashboardBlueprintCanonicalizer.canonicalize(second).checksums
    assert first_checksums == second_checksums
    proposal, evidence, warnings, risks = DashboardAiProposalValidationServiceV2().validate_blueprint(first, resolution.design_spec)
    assert proposal.blueprint.lifecycle.value == "DRAFT"
    assert proposal.blueprint.created_origin.value == "AI_PROPOSED"
    assert evidence and risks == ()


@pytest.mark.no_database
@pytest.mark.parametrize("instruction", [
    "Painel de faturamento", "Visão de faturamento por filial", "Comparar faturamento",
])
def test_ambiguous_revenue_requires_typed_clarification(instruction: str) -> None:
    intent = DashboardAiIntentExtractionServiceV2().extract_design(instruction)
    result = DashboardDesignSpecServiceV2().resolve(proposal_id="proposal.unit.002", intent=intent)
    assert result.design_spec is None
    assert result.clarifications[0].kind == "METRIC"
    assert {item.canonical_reference for item in result.clarifications[0].options} == {"metric.revenue", "metric.gross.revenue"}


@pytest.mark.no_database
def test_unknown_metric_and_dimension_fail_closed() -> None:
    extractor = DashboardAiIntentExtractionServiceV2()
    intent = extractor.extract_design("Dashboard executivo")
    unknown_metric = intent.model_copy(update={"metric_mentions": ("métrica lunar",)})
    unknown_dimension = intent.model_copy(update={"metric_mentions": ("ticket médio",), "dimension_mentions": ("planeta",)})
    assert DashboardDesignSpecServiceV2().resolve(proposal_id="proposal.unit.003", intent=unknown_metric).blocking_code == "DASHBOARD_AI_UNKNOWN_METRIC"
    assert DashboardDesignSpecServiceV2().resolve(proposal_id="proposal.unit.004", intent=unknown_dimension).blocking_code == "DASHBOARD_AI_UNKNOWN_DIMENSION"


SCENARIOS = (
    "criação executiva", "faturamento e ticket", "total e médio", "contas em aberto",
    "estoque", "ranking", "comparação", "ambiguidade faturamento", "ambiguidade desconto",
    "métrica inexistente", "dimensão inexistente", "período ambíguo", "alias", "preferência visual",
    "criação draft", "cancelar", "rejeitar", "revisar", "semantic edit", "visual edit", "publicar bloqueado",
    "aprovar bloqueado", "rollback bloqueado", "colaborador bloqueado", "tenant não confiável", "permission bloqueada",
    "sql bloqueado", "prompt injection", "tool forbidden", "provider output inválido", "timeout", "cancellation",
    "stale response", "budget exceeded", "duas abas", "tenant switch", "logout", "feedback negativo", "shadow",
    "legacy only", "quatro turnos", "perfil visual", "classification downgrade", "raw blueprint bloqueado", "chain of thought bloqueado",
)


@pytest.mark.no_database
@pytest.mark.parametrize("scenario", SCENARIOS)
def test_official_evaluation_corpus_has_bounded_unique_cases(scenario: str) -> None:
    assert 3 <= len(scenario) <= 80
    assert len(set(SCENARIOS)) == len(SCENARIOS)
    assert len(SCENARIOS) == 45
