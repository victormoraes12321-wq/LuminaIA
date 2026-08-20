import pytest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from models.view_catalog import ChartType
from schemas.view_catalog import ViewCatalogSummary
from services.query_planner import QueryPlan, QueryPlanItem
from services.ai_service import IntentionResponse, StructuredPlanSchema, PlanFiltersSchema, PlanVisualizationSchema
from services.iar_service import iar, CORPORATE_DICTIONARY_METRICS, CORPORATE_DICTIONARY_DIMENSIONS

@pytest.fixture
def dummy_catalog() -> list[ViewCatalogSummary]:
    return [
        ViewCatalogSummary(
            id=uuid.uuid4(),
            nome_view_oracle="VW_VENDAS_CONSOLIDADO",
            descricao_para_ia="Exibe vendas por vendedor, cliente e produto. Suporta receita_total e ticket_medio.",
            tipo_grafico_padrao=ChartType.BAR,
            parametros_schema={
                "vendedor": {"type": "string"},
                "receita_total": {"type": "number"},
                "ticket_medio": {"type": "number"}
            }
        ),
        ViewCatalogSummary(
            id=uuid.uuid4(),
            nome_view_oracle="VW_PRODUTOS_DETALHE",
            descricao_para_ia="Exibe faturamento por produto e categoria.",
            tipo_grafico_padrao=ChartType.PIE,
            parametros_schema={
                "produto": {"type": "string"},
                "faturamento": {"type": "number"}
            }
        )
    ]

@pytest.mark.asyncio
async def test_iar_alias_and_corporate_id_resolution(dummy_catalog):
    # Simula um plano original com aliases do usuário (ex: faturamento)
    intent = IntentionResponse(
        entidade_alvo="venda",
        operacao="SOMA",
        confianca=0.9,
        view_catalog_id=dummy_catalog[0].id,
        parametros={"_tipo": "teste"}
    )
    intent.plano_estruturado = StructuredPlanSchema(
        request_id=str(uuid.uuid4()),
        intent="teste",
        query_type="SELECT",
        metrics=["faturamento"], # Alias!
        group_by=["vendedor"],     # Alias!
        filters=PlanFiltersSchema(date_range="este mês"),
        visualization=PlanVisualizationSchema(type="BAR")
    )

    query_item = QueryPlanItem(
        id="principal",
        objetivo="teste",
        prioridade="ALTA",
        sugestao_visualizacao="BAR",
        view_name="VW_VENDAS_CONSOLIDADO",
        view_catalog_id=str(dummy_catalog[0].id)
    )
    query_plan = QueryPlan(consulta_principal=query_item, ordem_execucao=[["principal"]])

    # Executa a resolução do IAR
    resolved_plan = await iar.resolve_incompatibilities(
        query_plan=query_plan,
        intentions=[intent],
        catalog=dummy_catalog,
        tenant_id=uuid.uuid4(),
        db=None,
        original_query="Faturamento por vendedor"
    )

    # Verifica se os aliases foram convertidos para Corporate IDs e depois mapeados para as colunas físicas da View no plano estruturado
    assert "receita_total" in intent.plano_estruturado.metrics or "MET_001" in intent.plano_estruturado.metrics
    assert "vendedor" in intent.plano_estruturado.group_by or "DIM_001" in intent.plano_estruturado.group_by
    assert len(iar.auditor_logs) > 0

@pytest.mark.asyncio
async def test_iar_view_redirection_by_score(dummy_catalog):
    # Simula plano estruturado solicitando faturamento de produto
    intent = IntentionResponse(
        entidade_alvo="produto",
        operacao="SELECT",
        confianca=0.95,
        view_catalog_id=dummy_catalog[0].id, # Mapeado erradamente para VW_VENDAS_CONSOLIDADO
        parametros={}
    )
    intent.plano_estruturado = StructuredPlanSchema(
        request_id=str(uuid.uuid4()),
        intent="faturamento produto",
        query_type="SELECT",
        metrics=["faturamento"],
        group_by=["produto"],
        filters=PlanFiltersSchema(date_range="este mês"),
        visualization=PlanVisualizationSchema(type="PIE")
    )

    query_item = QueryPlanItem(
        id="principal",
        objetivo="teste",
        prioridade="ALTA",
        sugestao_visualizacao="PIE",
        view_name="VW_VENDAS_CONSOLIDADO", # View errada
        view_catalog_id=str(dummy_catalog[0].id)
    )
    query_plan = QueryPlan(consulta_principal=query_item, ordem_execucao=[["principal"]])

    # Executa a resolução
    resolved_plan = await iar.resolve_incompatibilities(
        query_plan=query_plan,
        intentions=[intent],
        catalog=dummy_catalog,
        tenant_id=uuid.uuid4(),
        db=None,
        original_query="Faturamento de produto"
    )

    # Como VW_PRODUTOS_DETALHE possui maior compatibilidade específica para faturamento + produto, o IAR deve redirecionar!
    assert resolved_plan.consulta_principal.view_name == "VW_PRODUTOS_DETALHE"
    assert resolved_plan.consulta_principal.view_catalog_id == str(dummy_catalog[1].id)


@pytest.mark.asyncio
async def test_iar_blocks_arp_redirect_across_strong_business_domain(dummy_catalog):
    intent = IntentionResponse(
        entidade_alvo="produto",
        operacao="RANKING",
        confianca=0.95,
        view_catalog_id=dummy_catalog[1].id,
        parametros={}
    )
    intent.plano_estruturado = StructuredPlanSchema(
        request_id=str(uuid.uuid4()),
        intent="produtos mais vendidos",
        query_type="RANKING",
        metrics=["quantidade"],
        group_by=["produto"],
        filters=PlanFiltersSchema(date_range="ultimos 3 meses"),
        visualization=PlanVisualizationSchema(type="PIE")
    )

    query_item = QueryPlanItem(
        id="principal",
        objetivo="produtos mais vendidos",
        prioridade="ALTA",
        sugestao_visualizacao="PIE",
        view_name="VW_PRODUTOS_DETALHE",
        view_catalog_id=str(dummy_catalog[1].id)
    )
    query_plan = QueryPlan(consulta_principal=query_item, ordem_execucao=[["principal"]])
    arp = SimpleNamespace(
        intencoes=[
            SimpleNamespace(
                objetivo="produtos mais vendidos",
                estrategias_candidatas=[
                    SimpleNamespace(
                        id="bad_sales_monthly_redirect",
                        views_utilizadas=["VW_VENDAS_MENSAIS"],
                        overall_resolution_score=98.0,
                        descricao="Estratégia incompatível para produto",
                    )
                ],
            )
        ]
    )

    resolved_plan = await iar.resolve_incompatibilities(
        query_plan=query_plan,
        intentions=[intent],
        catalog=dummy_catalog,
        tenant_id=uuid.uuid4(),
        db=None,
        original_query="Quais os produtos mais vendidos nos ultimos 3 meses?",
        arp=arp,
    )

    assert resolved_plan.consulta_principal.view_name == "VW_PRODUTOS_DETALHE"

@pytest.mark.asyncio
@patch("services.iar_service.IntelligentAnalyticalResolver._ai_semantic_fallback")
async def test_iar_ai_semantic_fallback_triggered(mock_fallback, dummy_catalog):
    mock_fallback.return_value = "receita"

    intent = IntentionResponse(
        entidade_alvo="venda",
        operacao="SOMA",
        confianca=0.9,
        view_catalog_id=dummy_catalog[0].id,
        parametros={}
    )
    # Métrica totalmente desconhecida do dicionário estático local
    intent.plano_estruturado = StructuredPlanSchema(
        request_id=str(uuid.uuid4()),
        intent="teste",
        query_type="SELECT",
        metrics=["unknown_metric"], 
        group_by=["vendedor"],
        filters=PlanFiltersSchema(date_range="este mês"),
        visualization=PlanVisualizationSchema(type="BAR")
    )

    query_item = QueryPlanItem(
        id="principal",
        objetivo="teste",
        prioridade="ALTA",
        sugestao_visualizacao="BAR",
        view_name="VW_VENDAS_CONSOLIDADO",
        view_catalog_id=str(dummy_catalog[0].id)
    )
    query_plan = QueryPlan(consulta_principal=query_item, ordem_execucao=[["principal"]])

    # Executa a resolução
    resolved_plan = await iar.resolve_incompatibilities(
        query_plan=query_plan,
        intentions=[intent],
        catalog=dummy_catalog,
        tenant_id=uuid.uuid4(),
        db=None,
        original_query="Quanto arrecadamos por vendedor"
    )

    # A métrica desconhecida deve ter sido resolvida pela IA para receita (que vira receita_total na view)
    mock_fallback.assert_called_once()
    assert "receita_total" in intent.plano_estruturado.metrics

@pytest.mark.asyncio
async def test_iar_blocks_arp_redirect_from_daily_sales_to_monthly_view():
    daily_id = uuid.uuid4()
    monthly_id = uuid.uuid4()
    catalog = [
        ViewCatalogSummary(
            id=daily_id,
            nome_view_oracle="VW_VENDAS_CONTEXTO_GERAL",
            descricao_para_ia="Vendas diarias detalhadas com data_ref.",
            tipo_grafico_padrao=ChartType.TABLE,
            parametros_schema={"data_ref": {"type": "date"}, "receita_total": {"type": "number"}},
        ),
        ViewCatalogSummary(
            id=monthly_id,
            nome_view_oracle="VW_VENDAS_MENSAIS",
            descricao_para_ia="Vendas mensais consolidadas por periodo.",
            tipo_grafico_padrao=ChartType.BAR,
            parametros_schema={"mes": {"type": "number"}, "receita_total": {"type": "number"}},
        ),
    ]
    intent = IntentionResponse(
        entidade_alvo="VENDA",
        operacao="SOMA",
        confianca=0.99,
        view_catalog_id=daily_id,
        parametros={"data_inicio": "2026-06-05", "data_fim": "2026-06-05"},
    )
    intent.plano_estruturado = StructuredPlanSchema(
        request_id=str(uuid.uuid4()),
        intent="valor vendas dia",
        query_type="SELECT",
        metrics=["receita_total"],
        group_by=[],
        filters=PlanFiltersSchema(date_range="2026-06-05 to 2026-06-05"),
        visualization=PlanVisualizationSchema(type="TABLE"),
    )
    query_item = QueryPlanItem(
        id="principal",
        objetivo="valor das vendas no dia",
        prioridade="ALTA",
        sugestao_visualizacao="TABLE",
        view_name="VW_VENDAS_CONTEXTO_GERAL",
        view_catalog_id=str(daily_id),
    )
    query_plan = QueryPlan(consulta_principal=query_item, ordem_execucao=[["principal"]])
    arp = SimpleNamespace(
        intencoes=[
            SimpleNamespace(
                objetivo="valor das vendas no dia",
                estrategias_candidatas=[
                    SimpleNamespace(
                        id="bad_monthly_redirect",
                        views_utilizadas=["VW_VENDAS_MENSAIS"],
                        overall_resolution_score=99.0,
                        descricao="Estrategia mensal nao permitida para data diaria",
                    )
                ],
            )
        ]
    )

    resolved_plan = await iar.resolve_incompatibilities(
        query_plan=query_plan,
        intentions=[intent],
        catalog=catalog,
        tenant_id=uuid.uuid4(),
        db=None,
        original_query="Qual foi o valor das vendas em 05/06/2026?",
        arp=arp,
    )

    assert resolved_plan.consulta_principal.view_name == "VW_VENDAS_CONTEXTO_GERAL"
