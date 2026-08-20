import pytest
import uuid
from unittest.mock import MagicMock

from models.view_catalog import ChartType
from schemas.view_catalog import ViewCatalogSummary
from services.aqd_service import aqd, record_strategy_success, AQD_STRATEGY_HISTORY

@pytest.fixture
def dummy_catalog() -> list[ViewCatalogSummary]:
    return [
        ViewCatalogSummary(
            id=uuid.uuid4(),
            nome_view_oracle="VW_VENDAS_MENSAIS",
            descricao_para_ia="Volume e valor total de faturamento agrupados por mes. Suporta vendedor e produto.",
            tipo_grafico_padrao=ChartType.BAR,
            parametros_schema={
                "vendedor": {"type": "string"},
                "produto": {"type": "string"},
                "receita": {"type": "number"}
            }
        ),
        ViewCatalogSummary(
            id=uuid.uuid4(),
            nome_view_oracle="VW_METAS_VENDEDORES",
            descricao_para_ia="Exibe as metas estabelecidas para cada vendedor.",
            tipo_grafico_padrao=ChartType.TABLE,
            parametros_schema={
                "vendedor": {"type": "string"},
                "meta": {"type": "number"}
            }
        )
    ]

def test_aqd_arp_generation_and_ranking(dummy_catalog):
    # Executa a decomposição simples de uma consulta
    query = "Faturamento mensal de vendas por vendedor"
    result = aqd.decompose(query, dummy_catalog, uuid.uuid4())

    # Valida presença do ARP
    assert result.arp is not None
    assert result.arp.arp_id.startswith("arp_")
    assert result.arp.original_query == query
    assert len(result.arp.intencoes) == 1

    # Valida estratégias candidatas da intenção
    intent = result.arp.intencoes[0]
    assert len(intent.estrategias_candidatas) > 0

    # Verifica se as estratégias estão ordenadas decrescentemente pelo score geral
    scores = [s.overall_resolution_score for s in intent.estrategias_candidatas]
    assert scores == sorted(scores, reverse=True)

def test_aqd_composite_metric_detection(dummy_catalog):
    # Pergunta que exige meta e faturamento (vendas)
    query = "Quero ver a meta e o faturamento por vendedor"
    result = aqd.decompose(query, dummy_catalog, uuid.uuid4())

    assert result.arp is not None
    intent = result.arp.intencoes[0]
    
    # Verifica se gerou uma estratégia composta via JOIN
    composite_strats = [s for s in intent.estrategias_candidatas if s.necessidade_join]
    assert len(composite_strats) > 0
    assert "VW_VENDAS_MENSAIS" in composite_strats[0].views_utilizadas
    assert "VW_METAS_VENDEDORES" in composite_strats[0].views_utilizadas

def test_aqd_controlled_learning_reordering(dummy_catalog):
    # Reseta histórico da estratégia para testar reordenamento
    strat_id_vendas = "strat_single_vw_vendas_mensais_task_principal"
    strat_id_metas = "strat_single_vw_metas_vendedores_task_principal"
    
    if strat_id_vendas in AQD_STRATEGY_HISTORY:
        del AQD_STRATEGY_HISTORY[strat_id_vendas]
    if strat_id_metas in AQD_STRATEGY_HISTORY:
        del AQD_STRATEGY_HISTORY[strat_id_metas]

    # Decompõe originalmente
    query = "Metas de vendas"
    result_1 = aqd.decompose(query, dummy_catalog, uuid.uuid4())
    intent_1 = result_1.arp.intencoes[0]

    # A estratégia de metas deve estar listada
    strat_metas_1 = next((s for s in intent_1.estrategias_candidatas if "metas_vendedores" in s.id), None)
    assert strat_metas_1 is not None

    # Registra múltiplos sucessos na estratégia de metas para alavancar seu score histórico
    for _ in range(5):
        record_strategy_success(strat_metas_1.id, success=True, elapsed_time_ms=120)

    # Decompõe novamente após os sucessos registrados
    result_2 = aqd.decompose(query, dummy_catalog, uuid.uuid4())
    intent_2 = result_2.arp.intencoes[0]
    
    strat_metas_2 = next((s for s in intent_2.estrategias_candidatas if s.id == strat_metas_1.id), None)
    assert strat_metas_2 is not None
    # O score de sucesso histórico deve ter subido para 100.0%
    assert strat_metas_2.historical_success_score == 100.0


def test_aqd_does_not_decompose_simple_top_sellers_with_multiple_months():
    catalog = [
        ViewCatalogSummary(
            id=uuid.uuid4(),
            nome_view_oracle="VW_VENDAS_MENSAIS",
            descricao_para_ia="Vendas mensais consolidadas.",
            tipo_grafico_padrao=ChartType.BAR,
            parametros_schema={"receita": {"type": "number"}},
        ),
        ViewCatalogSummary(
            id=uuid.uuid4(),
            nome_view_oracle="VW_PERFORMANCE_VENDEDORES",
            descricao_para_ia="Ranking e performance completa de vendedores.",
            tipo_grafico_padrao=ChartType.BAR,
            parametros_schema={"vendedor": {"type": "string"}, "valor_vendido": {"type": "number"}},
        ),
    ]

    result = aqd.decompose(
        "Qual o top 3 de vendedores que mais venderam juntando os meses 2, 3 e 4 de 2026?",
        catalog,
        uuid.uuid4(),
    )

    assert result.decomposed is False
    assert result.tasks[0].fonte_sugerida == "VW_PERFORMANCE_VENDEDORES"
    assert "DIM_002" in result.tasks[0].corporate_ids
