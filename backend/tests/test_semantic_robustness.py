import uuid
from types import SimpleNamespace

import pytest

from models.view_catalog import ChartType
from schemas.view_catalog import ViewCatalogSummary
from services.ai_service import _build_deterministic_fallback_intention
from services.ai.legacy_contracts import PlanFiltersSchema, PlanVisualizationSchema, StructuredPlanSchema
from services.plan_validator import validate_and_normalize_plan
from services.postgresql_clone_service import _normalize_search_value
from services.query_intelligence_engine import (
    _catalog_gap_for_query,
    _extract_city_from_query,
    _extract_customer_registry_params,
)


def _view(name: str) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), nome_view_oracle=name)


@pytest.mark.parametrize(
    ("query", "expected_city"),
    [
        ("Quero uma lista de clientes da cidade de Ataléia", "ataleia"),
        ("clientes cadastrados em Ataleia", "ataleia"),
        ("clientes cadastrados na Ataléia", "ataleia"),
        ("todos os clientes que residem no município de Ataléia", "ataleia"),
        ("clientes que moram em São Paulo", "sao paulo"),
        ("clientes na cidade de Belo Horizonte", "belo horizonte"),
        ("lista de clientes da cidade de Vitória da Conquista", "vitoria da conquista"),
        ("clientes da cidade de Barra do Garças com telefone", "barra do garcas"),
        ("cadastro de clientes no município de Feira de Santana", "feira de santana"),
        ("clientes de Rio de Janeiro", "rio de janeiro"),
        ("quais clientes residem em Porto Alegre?", "porto alegre"),
        ("clientes cidade ITABUNA", "itabuna"),
    ],
)
def test_city_extraction_accepts_many_semantic_variants(query: str, expected_city: str):
    assert _extract_city_from_query(query) == expected_city


def test_customer_registry_param_extraction_for_common_fields():
    params = _extract_customer_registry_params(
        "Mostre o cadastro do cliente Casa do Campo com CPF 123.456.789-00 "
        "no bairro Centro, cidade de Ataléia, UF MG, telefone (33) 99999-1111"
    )

    assert params["cidade"] == "ataleia"
    assert params["documento"] == "12345678900"
    assert params["bairro"] == "centro"
    assert params["uf"] == "mg"
    assert params["telefone"] == "33999991111"
    assert params["cliente_nome"] == "casa do campo"


def test_customer_registry_param_extraction_stops_bairro_before_city_phrase():
    params = _extract_customer_registry_params("Mostre clientes do bairro Centro na cidade de Ataléia")

    assert params["bairro"] == "centro"
    assert params["cidade"] == "ataleia"


def test_customer_registry_param_extraction_does_not_treat_cpf_filter_as_customer_name():
    params = _extract_customer_registry_params("Procure cliente com CPF 123.456.789-00")

    assert params["documento"] == "12345678900"
    assert "cliente_nome" not in params


@pytest.mark.parametrize(
    "value",
    ["Ataléia", "ATALEIA", "ataleia", "São João do Paraíso", "VITÓRIA DA CONQUISTA"],
)
def test_clone_text_normalization_is_accent_and_case_insensitive(value: str):
    normalized = _normalize_search_value(value)
    assert normalized == normalized.lower()
    assert not any(ch in normalized for ch in "áéíóúãõâêôçÁÉÍÓÚÃÕÂÊÔÇ")


@pytest.mark.parametrize(
    ("query", "expected_gap"),
    [
        ("Quanto faturamos hoje?", "vendas"),
        ("Ranking dos vendedores em março de 2026", "vendedores"),
        ("Quais produtos mais vendidos?", "produtos"),
        ("Top clientes que mais compraram", "clientes_analitico"),
        ("Quero clientes cadastrados em Ataléia", None),
    ],
)
def test_catalog_guard_blocks_only_missing_view_families(query: str, expected_gap: str | None):
    catalog = [_view("VW_CLIENTES_CADASTRADO")]
    result = _catalog_gap_for_query(query, catalog)
    assert (result[0] if result else None) == expected_gap


@pytest.mark.parametrize(
    "query",
    [
        "Quanto faturamos hoje?",
        "Ranking dos vendedores em março de 2026",
        "Quais produtos mais vendidos?",
        "Top clientes que mais compraram",
    ],
)
def test_catalog_guard_allows_future_views_when_registered(query: str):
    future_catalog = [
        _view("VW_CLIENTES_CADASTRADO"),
        _view("VW_VENDAS_CONTEXTO_GERAL"),
        _view("VW_PERFORMANCE_VENDEDORES"),
        _view("VW_PRODUTOS_MAIS_VENDIDOS"),
        _view("VW_DETALHE_PEDIDOS"),
    ]
    assert _catalog_gap_for_query(query, future_catalog) is None


@pytest.mark.parametrize(
    "query",
    [
        "Quero uma lista de clientes da cidade de Ataléia",
        "clientes cadastrados em São Paulo",
        "qual o cpf do cliente Casa do Campo",
        "clientes do bairro Centro",
        "clientes com telefone 3333333333",
    ],
)
def test_customer_registry_validator_never_keeps_sales_metrics(query: str):
    plan = StructuredPlanSchema(
        request_id="semantic-robustness",
        intent=query,
        query_type="SELECT",
        metrics=["receita_total", "quantidade_pedidos", "listagem"],
        group_by=["cliente"],
        filters=PlanFiltersSchema(date_range="este mes"),
        visualization=PlanVisualizationSchema(type="KPI", layout_priority="ALTA"),
    )

    result = validate_and_normalize_plan(
        plan,
        query_text=query,
        view_name="VW_CLIENTES_CADASTRADO",
    )

    assert result.validated is True
    assert result.metrics == []
    assert result.filters["date_range"] == ""
    assert result.visualization["type"] == "TABLE"


def test_deterministic_fallback_understands_customer_registry_without_sales_metrics():
    catalog = [
        ViewCatalogSummary(
            id=uuid.uuid4(),
            nome_view_oracle="VW_CLIENTES_CADASTRADO",
            descricao_para_ia="Cadastro completo de clientes.",
            tipo_grafico_padrao=ChartType.TABLE,
            parametros_schema={"cidade": {"type": "string"}},
        )
    ]

    intention = _build_deterministic_fallback_intention(
        pergunta="Liste clientes de Vitória da Conquista com telefone 3333333333",
        catalog=catalog,
        request_id="semantic-fallback",
        reason="test",
    )

    assert intention.view_catalog_id == catalog[0].id
    assert intention.entidade_alvo == "CLIENTE"
    assert intention.operacao == "LISTAGEM"
    assert intention.plano_estruturado is not None
    assert intention.plano_estruturado.metrics == []
    assert intention.parametros["cidade"] == "vitoria da conquista"
    assert intention.parametros["telefone"] == "3333333333"
