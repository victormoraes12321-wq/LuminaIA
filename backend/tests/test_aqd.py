import pytest
import uuid
from services.aqd_service import aqd, AQDDecompositionResult
from services.plan_validator import validate_and_normalize_plan, ValidatedPlanResponse
from schemas.view_catalog import ViewCatalogSummary
from models.view_catalog import ChartType


@pytest.fixture
def dummy_catalog():
    """Retorna um catálogo fictício de views para testes."""
    return [
        ViewCatalogSummary(
            id=uuid.uuid4(),
            nome_view_oracle="VW_VENDAS_MENSAIS",
            descricao_para_ia="Métricas mensais de faturamento e vendas",
            tipo_grafico_padrao=ChartType.LINE
        ),
        ViewCatalogSummary(
            id=uuid.uuid4(),
            nome_view_oracle="VW_COMPRAS",
            descricao_para_ia="Métricas de compras e fornecedores",
            tipo_grafico_padrao=ChartType.TABLE
        ),
        ViewCatalogSummary(
            id=uuid.uuid4(),
            nome_view_oracle="VW_KPI_EXECUTIVO",
            descricao_para_ia="KPIs estratégicos executivos",
            tipo_grafico_padrao=ChartType.KPI
        )
    ]


def test_aqd_single_query(dummy_catalog):
    """AQD deve retornar plano de consulta única para perguntas simples."""
    tenant_id = uuid.uuid4()
    result = aqd.decompose("faturamento total deste mês", dummy_catalog, tenant_id)
    
    assert result.decomposed is False
    assert len(result.tasks) == 1
    assert result.tasks[0].fonte_sugerida == "VW_VENDAS_MENSAIS"


def test_aqd_complex_query_decomposition(dummy_catalog):
    """AQD deve decompor perguntas complexas em múltiplas subconsultas (Tasks)."""
    tenant_id = uuid.uuid4()
    # Caso 1: Conectores "e"
    result = aqd.decompose("performance de vendedores e top produtos mais vendidos", dummy_catalog, tenant_id)
    
    assert result.decomposed is True
    assert len(result.tasks) >= 2
    assert any("vendedor" in t.objetivo.lower() for t in result.tasks)
    assert any("produto" in t.objetivo.lower() for t in result.tasks)
    assert result.master_blueprint is not None
    assert len(result.master_blueprint.layout["widgets"]) >= 2


def test_aqd_multi_question_decomposition(dummy_catalog):
    """AQD deve decompor múltiplas interrogações em subconsultas separadas."""
    tenant_id = uuid.uuid4()
    result = aqd.decompose("vendedor que vendeu mais? fornecedor que entregou mais?", dummy_catalog, tenant_id)
    
    assert result.decomposed is True
    assert len(result.tasks) == 2
    assert result.tasks[0].fonte_sugerida == "VW_VENDAS_MENSAIS"
    assert result.tasks[1].fonte_sugerida == "VW_COMPRAS"


def test_validator_aqd_reactive_trigger(dummy_catalog):
    """Validador deve acionar AQD de forma reativa em caso de erro de métrica incompatível."""
    tenant_id = uuid.uuid4()
    # Métrica de fornecedor ("DIM_003") em view de vendas é incompatível
    plan_dict = {
        "request_id": str(uuid.uuid4()),
        "intent": "performance de vendedores e top fornecedores",
        "metrics": ["valor_compra"],
        "group_by": ["fornecedor_nome"]
    }
    
    # Chama o validador passando o catálogo e tenant_id
    response = validate_and_normalize_plan(
        plan=plan_dict,
        query_text="performance de vendedores e top fornecedores",
        view_name="VW_VENDAS_MENSAIS",
        catalog=dummy_catalog,
        tenant_id=tenant_id
    )
    
    assert response.validated is True
    assert "AQD" in "; ".join(response.warnings)
    assert response.suggested_refinement == "AQD_DECOMPOSITION_TRIGGERED"
