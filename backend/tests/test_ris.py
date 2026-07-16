import pytest
import uuid
from services.ris_service import ris
from services.roqg_service import roqg
from schemas.roqg import DeliveryDecision
from services.query_planner import QueryPlan, QueryPlanItem

@pytest.fixture
def base_query_plan() -> QueryPlan:
    item = QueryPlanItem(
        id=str(uuid.uuid4()),
        view_name="VW_VENDAS_MENSAIS",
        view_catalog_id=str(uuid.uuid4()),
        objetivo="Análise de Vendas"
    )
    object.__setattr__(item, "metrics", ["MET_001"])
    object.__setattr__(item, "group_by", ["DIM_001"])
    return QueryPlan(
        request_id=uuid.uuid4(),
        consulta_principal=item,
        consultas_relacionadas=[]
    )

def test_ris_freshness_engine():
    # Testa a freshness engine com uma view
    res = ris._run_freshness_engine("VW_VENDAS_MENSAIS")
    assert res.score > 50.0
    assert res.classification in ["Excelente", "Muito Bom", "Aceitável"]
    assert not res.alerta_gerado

    # Testa uma view com SLA estrito
    res_kpi = ris._run_freshness_engine("VW_KPI_REALTIME")
    assert res_kpi.view_frequency == "horaria"

def test_ris_sufficiency_analyzer():
    # Caso 1: Dataset vazio
    res_empty = ris._run_data_sufficiency_analyzer([])
    assert res_empty.score == 0.0
    assert res_empty.classification == "Insuficiente"
    assert res_empty.bloquear_insights

    # Caso 2: Dataset muito pequeno (menos de 5 registros)
    raw_rows_small = [{"vendedor": "Victor", "receita": 1000}] * 3
    res_small = ris._run_data_sufficiency_analyzer(raw_rows_small)
    # Deve sofrer penalização de representatividade estatística (-30)
    assert res_small.score < 80.0

    # Caso 3: Dataset suficiente
    raw_rows_ok = [{"vendedor": "Victor", "receita": 1000}] * 10
    res_ok = ris._run_data_sufficiency_analyzer(raw_rows_ok)
    assert res_ok.score == 100.0
    assert res_ok.classification == "Suficiente"
    assert not res_ok.bloquear_insights

def test_ris_consistency_checker():
    raw_rows = [
        {"vendedor": "A", "receita": 1000},
        {"vendedor": "B", "receita": 2000}
    ]
    # Caso 1: Dados consistentes (Soma da tabela 3000 bate com o valor do card no dashboard_payload)
    dashboard_payload_consistent = {
        "layout": {
            "widgets": [
                {"id": "w1", "type": "KPI_CARD", "value": "3000"}
            ]
        }
    }
    res_c = ris._run_consistency_checker(raw_rows, dashboard_payload_consistent, {})
    assert res_c.consistent
    assert res_c.max_desvio_percent == 0.0

    # Caso 2: Dados inconsistentes (Card exibe 5000, mas soma é 3000 -> desvio de 66.6%)
    dashboard_payload_inconsistent = {
        "layout": {
            "widgets": [
                {"id": "w1", "type": "KPI_CARD", "value": "5000"}
            ]
        }
    }
    res_i = ris._run_consistency_checker(raw_rows, dashboard_payload_inconsistent, {})
    assert not res_i.consistent
    assert res_i.max_desvio_percent > 1.0

def test_ris_contradiction_detector():
    # Caso 1: Contradição detectada (Dados mostram Queda, mas IA reporta crescimento)
    raw_rows_down = [
        {"mes": "Janeiro", "receita": 5000},
        {"mes": "Fevereiro", "receita": 1000} # Queda acentuada
    ]
    ia_analise_contradictory = "Tivemos um excelente crescimento e alta expressiva no faturamento corporativo."
    
    # Executa a consistência
    consistency_stub = ris._run_consistency_checker(raw_rows_down, {}, {})
    
    res = ris._run_contradiction_detector(raw_rows_down, ia_analise_contradictory, consistency_stub)
    assert res.contradiction_detected
    assert res.bloquear_dashboard
    assert res.score < 70.0

def test_roqg_integration_with_ris(base_query_plan):
    # Simula um resultado da RIS com falha de freshness crítica
    ris_failed_freshness = {
        "freshness": {"score": 30.0},
        "contradiction": {"score": 100.0},
        "sufficiency": {"classification": "Suficiente"}
    }
    
    # Processa pelo ROQG
    components_metadata = [
        {"status": "AVAILABLE", "prioridade": "CRITICO", "id": "comp_1"}
    ]
    
    # Executa decisão de entrega passando o ris_result inválido
    decision, score, msg = roqg._step_delivery_decision(components_metadata, [], ris_failed_freshness)
    assert decision == DeliveryDecision.UNAVAILABLE
    assert score == 0.0
    assert "Freshness crítico" in msg


def test_ris_engines_6_to_15_and_package(base_query_plan):
    tenant_id = uuid.uuid4()
    query_text = "Quero ver o faturamento de vendas mensal"
    raw_rows = [
        {"mes": "Janeiro", "receita": 10000.0},
        {"mes": "Fevereiro", "receita": 12000.0}
    ]
    ia_analise = "Tivemos um crescimento de 20% no faturamento mensal. Talvez isso seja devido à nova campanha."
    
    # Executa o pipeline RIS completo
    ris_res = ris.process_response(
        tenant_id=tenant_id,
        query_text=query_text,
        query_plan=base_query_plan,
        resultados_dict={"principal": {"view_name": "VW_VENDAS_MENSAIS", "raw_rows": raw_rows}},
        dashboard_payload={},
        analytics_results={},
        ia_analise=ia_analise,
        telemetry={"tempo_total_ms": 3200, "tokens_utilizados": 8500}
    )
    
    # Valida Engine 6: Business Context Analyzer
    assert ris_res.business_context.score == 100.0
    assert ris_res.business_context.area_negocio == "Comercial / Vendas"
    
    # Valida Engine 7: Explainability
    assert "obtidos através da métrica corporativa" in ris_res.explainability.explicacao_executiva
    
    # Valida Engine 8: Insights
    assert len(ris_res.insights) > 0
    # O faturamento contendo números deve ser validado
    assert any(i.classificacao == "Confirmado por dados" for i in ris_res.insights)
    
    # Valida Engine 9: Hypotheses
    assert any(h.categoria == "Hipótese" for h in ris_res.hypotheses)
    
    # Valida Engine 10: Ambiguidade
    assert not ris_res.ambiguity.solicitar_esclarecimento # pergunta longa o suficiente
    
    # Valida Engine 11: Reasoning
    assert ris_res.reasoning.processo_valido
    
    # Valida Engine 12: Recomendações
    assert len(ris_res.recommendations) > 0
    
    # Valida Engine 13: Quality
    assert ris_res.quality.score >= 90.0
    
    # Valida Engine 14: Trust Score
    assert ris_res.trust.score >= 70.0
    assert ris_res.trust.classification in ["Alta confiança", "Boa confiança"]
    
    # Valida Engine 15: SLA
    assert ris_res.sla.score == 100.0
    assert not ris_res.sla.tempo_total_ms > 5000
    
    # Valida o Response Intelligence Package (RIP)
    pkg = ris_res.package
    assert pkg.dados["dataset_rows"] == 2
    assert pkg.qualidade["trust_score"] == ris_res.trust.score
    assert pkg.auditoria["query_original"] == query_text


def test_roqg_rip_governance_decision():
    components_metadata = [
        {"status": "AVAILABLE", "prioridade": "CRITICO", "id": "comp_1"}
    ]
    
    # Caso 1: Trust Score < 50 deve causar bloqueio de entrega (DeliveryDecision.UNAVAILABLE)
    from services.ris_service import ResponseIntelligencePackage
    fake_package_low_trust = ResponseIntelligencePackage(
        dados={},
        estrategia={},
        qualidade={"trust_score": 45.0, "quality_score": 90.0, "consistency_score": 90.0, "sla_score": 90.0},
        evidencias={},
        inteligencia={},
        auditoria={}
    )
    decision, score, msg = roqg._step_delivery_decision(components_metadata, [], {}, fake_package_low_trust)
    assert decision == DeliveryDecision.UNAVAILABLE
    assert "Trust Score consolidado" in msg
    
    # Caso 2: Ambiguidade crítica marcada com solicitar_esclarecimento = True
    ris_result_ambiguous = {
        "ambiguity": {
            "solicitar_esclarecimento": True,
            "interpretacoes_possiveis": ["Interp A", "Interp B"]
        }
    }
    decision, score, msg = roqg._step_delivery_decision(components_metadata, [], ris_result_ambiguous)
    assert decision == DeliveryDecision.CONFIRMATION_REQUIRED
    assert "esclarecer sua pergunta" in msg
    
    # Caso 3: SLA estourado (tempo > 5s) deve entregar com warnings
    ris_result_sla_violated = {
        "sla": {
            "limite_violado": True,
            "score": 70.0,
            "alertas_sla": ["Tempo total de pipeline violado (SLA: 5s)"]
        }
    }
    decision, score, msg = roqg._step_delivery_decision(components_metadata, [], ris_result_sla_violated)
    assert decision == DeliveryDecision.PARTIAL_RENDERING
    assert "Tempo total de pipeline violado" in msg
