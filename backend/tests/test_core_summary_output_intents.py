import pytest

from services.new_query_orchestrator import NewQueryOrchestrator

pytestmark = [pytest.mark.unit, pytest.mark.no_database]


def test_vendor_top_query_is_not_collapsed_with_ranking():
    orchestrator = NewQueryOrchestrator()

    topics = orchestrator._core_summary_topics("Qual vendedor que mais vendeu no mês 07/2026?")

    assert "top_vendedor" in topics
    assert "ranking_vendedores" not in topics


def test_vendor_ranking_query_keeps_ranked_output_intent():
    orchestrator = NewQueryOrchestrator()

    topics = orchestrator._core_summary_topics("Ranking com todos os vendedores, no mês 07/2026")

    assert "ranking_vendedores" in topics
    assert "top_vendedor" not in topics


def test_sales_by_vendor_query_is_ranked_output():
    orchestrator = NewQueryOrchestrator()

    topics = orchestrator._core_summary_topics("Venda por vendedor em 07/2026")

    assert "ranking_vendedores" in topics


def test_discount_by_vendor_has_own_ranked_output():
    orchestrator = NewQueryOrchestrator()

    topics = orchestrator._core_summary_topics("Ranking de vendedores por desconto em 07/2026")

    assert "ranking_vendedores_desconto" in topics
    assert "ranking_vendedores" not in topics
    assert "top_vendedor" not in topics


def test_rb_by_vendor_has_own_ranked_output():
    orchestrator = NewQueryOrchestrator()

    topics = orchestrator._core_summary_topics("Vendas RB por vendedor no mês 07/2026")

    assert "ranking_vendedores_rb" in topics
    assert "ranking_vendedores" not in topics
    assert orchestrator._primary_metric_for_query(orchestrator._normalize_query_text("Vendas RB por vendedor")) == "saida_rb"


def test_devolucao_by_vendor_has_own_ranked_output():
    orchestrator = NewQueryOrchestrator()

    topics = orchestrator._core_summary_topics("Devolucao por vendedor no mes 07/2026")

    assert "ranking_vendedores_devolucao" in topics
    assert "ranking_vendedores_rb" not in topics
    assert orchestrator._primary_metric_for_query(orchestrator._normalize_query_text("Devolucao por vendedor")) == "devolucao"


def test_context_followup_inherits_period_for_rb_query():
    orchestrator = NewQueryOrchestrator()

    inherited = orchestrator._question_with_inherited_period(
        "e quantas vendas foram RB?",
        [{"role": "user", "content": "Faturamento do mês 07/2026"}],
    )

    assert inherited.endswith("em 07/2026")
    assert "RB" in inherited


def test_context_followup_inherits_metric_for_rb_dimension_request():
    orchestrator = NewQueryOrchestrator()

    inherited = orchestrator._question_with_inherited_period(
        "agora separa esse dado por vendedor",
        [{"role": "user", "content": "Quantas vendas RB tivemos no mês 07/2026?"}],
    )
    topics = orchestrator._core_summary_topics(inherited)

    assert inherited.endswith("em 07/2026")
    assert "RB" in inherited
    assert "ranking_vendedores_rb" in topics
    assert "ranking_vendedores" not in topics


def test_context_followup_does_not_turn_unsupported_metric_into_sales_ranking():
    orchestrator = NewQueryOrchestrator()

    inherited = orchestrator._question_with_inherited_period(
        "separa por vendedor",
        [{"role": "user", "content": "Valor de vendas ainda nao faturadas no mês 07/2026"}],
    )
    topics = orchestrator._core_summary_topics(inherited)

    assert "vendas_nao_faturadas" in topics
    assert "ranking_vendedores" not in topics


def test_context_followup_inherits_ranking_dimension_for_visual_request():
    orchestrator = NewQueryOrchestrator()

    inherited = orchestrator._question_with_inherited_period(
        "me mostra esse ranking em grafico",
        [{"role": "user", "content": "Ranking de vendas RB por vendedor no mês 07/2026"}],
    )
    topics = orchestrator._core_summary_topics(inherited)

    assert "por vendedor" in inherited
    assert "RB" in inherited
    assert "ranking_vendedores_rb" in topics


def test_iso_period_from_assistant_response_keeps_long_context_alive():
    orchestrator = NewQueryOrchestrator()

    inherited = orchestrator._question_with_inherited_period(
        "ranking de clientes em tabela",
        [{"role": "assistant", "content": "Resumo do período 2026-07-01 a 2026-07-31: vendas ainda nao faturadas indisponiveis."}],
    )

    assert inherited.endswith("em 07/2026") or "2026-07-01" in inherited
    assert "vendas ainda nao faturadas" not in inherited
    assert "ranking_clientes" in orchestrator._core_summary_topics(inherited)


@pytest.mark.known_gap
def test_same_followup_inherits_metric_period_and_visual_request():
    orchestrator = NewQueryOrchestrator()

    inherited = orchestrator._question_with_inherited_period(
        "quero o mesmo em tabela e grafico",
        [{"role": "assistant", "content": "Resumo do período 2026-07-01 a 2026-07-31: faturamento comercial de R$ 1.721.983,54."}],
    )

    assert "faturamento" in inherited
    assert "07/2026" in inherited or "2026-07-01" in inherited
    assert orchestrator._schema_chart_types_from_text(
        orchestrator._normalize_query_text(inherited),
        ranking_kind=None,
    ) == ["TABLE", "BAR"]


def test_month_parser_accepts_text_slash_and_abbreviations():
    orchestrator = NewQueryOrchestrator()

    assert orchestrator._month_range_from_text("RANKING TODOS VENDEDORES JULHO/2026 EM GRAFICO") == (
        "2026-07-01",
        "2026-07-31",
    )
    assert orchestrator._month_range_from_text("qnt vendeu rb vendedor jul/2026 tabela") == (
        "2026-07-01",
        "2026-07-31",
    )


def test_leigo_rb_vendor_phrase_is_ranked_output():
    orchestrator = NewQueryOrchestrator()

    topics = orchestrator._core_summary_topics("qnt vendeu rb vendedor jul/2026 tabela")

    assert "ranking_vendedores_rb" in topics


def test_top_n_vendor_query_is_ranked_with_limit():
    orchestrator = NewQueryOrchestrator()
    normalized = orchestrator._normalize_query_text("Top 3 vendedores no mês 07/2026")

    topics = orchestrator._core_summary_topics("Top 3 vendedores no mês 07/2026")

    assert "ranking_vendedores" in topics
    assert orchestrator._ranking_limit_from_text(normalized) == 3


def test_client_ranking_defaults_to_top_50_unless_user_asks_all():
    orchestrator = NewQueryOrchestrator()

    assert orchestrator._ranking_limit_for_dimension("ranking de clientes", "cliente") == 50
    assert orchestrator._ranking_limit_for_dimension("ranking de todos os clientes", "cliente") is None
    assert orchestrator._ranking_limit_for_dimension("top 12 clientes", "cliente") == 12


def test_core_sales_queries_use_erp_commercial_sales_filter():
    orchestrator = NewQueryOrchestrator()

    assert orchestrator._erp_sales_filter_sql("lm") == "lm.tp_ IN (2, 61)"
    assert orchestrator._erp_sales_filter_sql() == "tp_ IN (2, 61)"
    assert orchestrator._erp_sales_filter_binds() == {}


def test_core_sales_queries_can_scope_erp_filter_by_filial():
    orchestrator = NewQueryOrchestrator()

    assert orchestrator._erp_sales_filter_sql("lm", "3") == "lm.tp_ IN (2, 61) AND lm.filial_ = :sales_filial"
    assert orchestrator._erp_sales_filter_binds("03") == {"sales_filial": "3"}
    assert orchestrator._filial_from_text("Faturamento da filial 03 no mes 07/2026") == "3"


def test_sales_by_filial_query_is_core_faturamento_output():
    orchestrator = NewQueryOrchestrator()

    topics = orchestrator._core_summary_topics("Vendas por filial no mes 07/2026")

    assert "faturamento" in topics


def test_ranking_rows_are_pivoted_by_dimension_and_filial():
    orchestrator = NewQueryOrchestrator()

    rows = orchestrator._pivot_ranking_rows_by_dimension(
        [
            {
                "posicao": 4,
                "vendedor": "WANESSA FERREIRA DA SILVA",
                "filial": "1",
                "faturamento_comercial": 100.0,
                "total_bruto": 120.0,
                "faturamento_comercial_total": 350.0,
                "total_bruto_total": 410.0,
                "pedidos_comerciais": 2,
                "pedidos_total": 3,
                "pedidos_comerciais_total": 7,
                "pedidos_total_periodo": 9,
                "desconto_total": 0.0,
                "desconto_total_periodo": 0.0,
            },
            {
                "posicao": 4,
                "vendedor": "WANESSA FERREIRA DA SILVA",
                "filial": "5",
                "faturamento_comercial": 250.0,
                "total_bruto": 290.0,
                "faturamento_comercial_total": 350.0,
                "total_bruto_total": 410.0,
                "pedidos_comerciais": 5,
                "pedidos_total": 6,
                "pedidos_comerciais_total": 7,
                "pedidos_total_periodo": 9,
                "desconto_total": 0.0,
                "desconto_total_periodo": 0.0,
            },
        ],
        "vendedor",
        primary_key="faturamento_comercial",
    )

    assert len(rows) == 1
    assert rows[0]["vendedor"] == "WANESSA FERREIRA DA SILVA"
    assert "filial" not in rows[0]
    assert rows[0]["filial_1_faturamento_comercial"] == 100.0
    assert rows[0]["filial_5_faturamento_comercial"] == 250.0
    assert rows[0]["valor_total"] == 350.0
    assert "filial_1_saida_rb" not in rows[0]
    assert "desconto_total_periodo" not in rows[0]


def test_ranking_rows_expand_operational_details_only_when_requested():
    orchestrator = NewQueryOrchestrator()

    rows = orchestrator._pivot_ranking_rows_by_dimension(
        [
            {
                "posicao": 1,
                "vendedor": "VENDEDOR TESTE",
                "filial": "1",
                "faturamento_comercial": 100.0,
                "saida_rb": 9.0,
                "faturamento_comercial_total": 100.0,
                "saida_rb_total": 9.0,
                "pedidos_comerciais": 2,
                "pedidos_saida_rb": 1,
                "pedidos_comerciais_total": 2,
                "pedidos_saida_rb_total": 1,
            }
        ],
        "vendedor",
        primary_key="saida_rb",
        include_operational_details=True,
    )

    assert rows[0]["filial_1_saida_rb"] == 9.0
    assert rows[0]["valor_total"] == 9.0
    assert rows[0]["pedidos_saida_rb_total"] == 1


def test_faturamento_breakdown_places_total_row_after_filiais():
    orchestrator = NewQueryOrchestrator()
    totals = {"faturamento_comercial": 300.0, "total_bruto": 330.0}
    filial_totals = [
        {"filial": "1", "faturamento_comercial": 100.0, "total_bruto": 110.0},
        {"filial": "2", "faturamento_comercial": 200.0, "total_bruto": 220.0},
    ]

    rows = orchestrator._period_value_breakdown_rows(totals, filial_totals, filial=None)

    assert [row["filial"] for row in rows] == ["1", "2", "Total geral"]
    assert rows[-1]["tipo_linha"] == "Total geral"
    assert rows[-1]["faturamento_comercial"] == 300.0


def test_faturamento_breakdown_can_return_gross_and_net_without_all_categories():
    orchestrator = NewQueryOrchestrator()
    totals = {"faturamento_comercial": 300.0, "total_bruto": 330.0, "pedidos_comerciais": 3, "pedidos_total": 4}
    filial_totals = [{"filial": "1", "faturamento_comercial": 300.0, "total_bruto": 330.0, "pedidos_comerciais": 3, "pedidos_total": 4}]

    rows = orchestrator._period_value_breakdown_rows(totals, filial_totals, filial=None, value_basis="ambos")

    assert rows[0]["faturamento_comercial"] == 300.0
    assert rows[0]["total_bruto"] == 330.0
    assert "saida_rb" not in rows[0]


def test_rb_period_breakdown_returns_value_and_count_by_filial_and_total():
    orchestrator = NewQueryOrchestrator()
    totals = {"saida_rb": 30.0, "pedidos_saida_rb": 3}
    filial_totals = [{"filial": "1", "saida_rb": 10.0, "pedidos_saida_rb": 1}]

    rows = orchestrator._period_category_breakdown_rows(
        totals,
        filial_totals,
        filial=None,
        category_key="saida_rb",
    )

    assert [row["filial"] for row in rows] == ["1", "Total geral"]
    assert rows[0]["valor"] == 10.0
    assert rows[-1]["pedidos"] == 3


def test_discount_breakdown_exposes_derived_source_warning():
    orchestrator = NewQueryOrchestrator()
    totals = {
        "desconto_comercial": 0.0,
        "desconto_total": 0.0,
        "pedidos_comerciais": 10,
        "pedidos_total": 12,
        "desconto_fonte_tipo": "derivado_sem_coluna_explicita",
        "desconto_fonte_confianca": "baixa",
    }

    rows = orchestrator._period_discount_breakdown_rows(totals, [], filial=None)

    assert rows[0]["desconto_fonte_tipo"] == "derivado_sem_coluna_explicita"
    assert rows[0]["desconto_fonte_confianca"] == "baixa"
    assert "nao possui coluna explicita de desconto" in rows[0]["observacao"]


def test_visualization_text_selects_graph_or_both_outputs():
    orchestrator = NewQueryOrchestrator()

    assert orchestrator._schema_chart_types_from_text("ranking em grafico", ranking_kind="vendedores") == ["BAR"]
    assert orchestrator._schema_chart_types_from_text("ranking em tabela e grafico", ranking_kind="vendedores") == ["TABLE", "BAR"]
    assert orchestrator._has_explicit_visualization_request("ranking em tabela")
    assert orchestrator._schema_chart_types_from_text("ranking em tabela", ranking_kind="vendedores") == ["TABLE"]


def test_response_modes_change_deterministic_text_depth():
    orchestrator = NewQueryOrchestrator()
    text = "Resumo do periodo: faturamento de R$ 10,00. Segunda frase com detalhes."

    quick = orchestrator._apply_response_mode(text, mode="operational", row_count=2, warnings=[])
    analytical = orchestrator._apply_response_mode(text, mode="analytical", row_count=2, warnings=[])
    executive = orchestrator._apply_response_mode(text, mode="executive", row_count=2, warnings=["fonte limitada"])

    assert quick == "Resumo do periodo: faturamento de R$ 10,00."
    assert analytical == text
    assert "Leitura executiva" in executive
