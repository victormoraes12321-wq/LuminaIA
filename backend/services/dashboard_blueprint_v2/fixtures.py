"""Synthetic deterministic fixtures used by tests and the official exporter."""
from __future__ import annotations

from copy import deepcopy
from datetime import date

from contracts.dashboard_blueprint_v2 import (
    DashboardAccessibilityV2,
    DashboardAudienceV2,
    DashboardBarChartWidgetV2,
    DashboardBlueprintV2,
    DashboardChartAxisV2,
    DashboardChartSeriesV2,
    DashboardClassificationV2,
    DashboardComparisonBindingV2,
    DashboardComparisonKpiWidgetV2,
    DashboardCompatibilityV2,
    DashboardCompletenessRequirementV2,
    DashboardDataBindingV2,
    DashboardDimensionBindingV2,
    DashboardErrorStateV2,
    DashboardFilterDefaultV2,
    DashboardFilterScopeV2,
    DashboardFixedPeriodBindingV2,
    DashboardFormattingV2,
    DashboardGovernanceV2,
    DashboardGridItemV2,
    DashboardGridV2,
    DashboardIdentityV2,
    DashboardKpiWidgetV2,
    DashboardLayoutV2,
    DashboardLifecycleV2,
    DashboardLineChartWidgetV2,
    DashboardLoadingStateV2,
    DashboardMetricBindingV2,
    DashboardOriginV2,
    DashboardPatchOperationKindV2,
    DashboardPatchOperationV2,
    DashboardProvenanceRequirementV2,
    DashboardPurposeV2,
    DashboardRankingWidgetV2,
    DashboardResponsiveBreakpointV2,
    DashboardResultShapeV2,
    DashboardRevisionV2,
    DashboardSemanticPatchV2,
    DashboardSingleSelectFilterV2,
    DashboardTableColumnV2,
    DashboardTableWidgetV2,
    DashboardThemeTokenV2,
    DashboardVersionV2,
    DashboardVisualPatchV2,
    DashboardWidgetAccessibilityV2,
    DashboardWidgetIdentityV2,
    DashboardWidgetStatesV2,
    DashboardWidgetTitleV2,
    DashboardBreakpointV2,
)

from .canonicalizer import DashboardBlueprintCanonicalizer


def widget_states(label: str) -> DashboardWidgetStatesV2:
    return DashboardWidgetStatesV2(
        loading=DashboardLoadingStateV2(label=f"Carregando {label}"),
        empty={"title": "Sem dados", "message": f"Não há dados sintéticos para {label}."},
        partial_message="Resultado parcial; consulte a proveniência.",
        stale_message="Resultado desatualizado; consulte a origem.",
        truncated_message="Resultado truncado; nem todas as linhas estão visíveis.",
        error=DashboardErrorStateV2(
            title="Não foi possível exibir",
            message="A validação governada bloqueou ou falhou.",
        ),
        permission_denied_message="Permissão insuficiente para este conteúdo.",
        unavailable_message="Conteúdo temporariamente indisponível.",
    )


def widget_accessibility(label: str, *, chart: bool = False) -> DashboardWidgetAccessibilityV2:
    return DashboardWidgetAccessibilityV2(
        accessible_name=label,
        accessible_description=f"Visualização sintética e governada de {label}.",
        summary_template=f"Resumo textual obrigatório de {label}.",
        table_alternative_required=chart,
        chart_text_summary_required=chart,
    )


def fixed_period(month: int) -> DashboardFixedPeriodBindingV2:
    end_day = 30 if month == 6 else 31
    return DashboardFixedPeriodBindingV2(
        period_type="FIXED",
        period_id=f"period.2026.{month:02d}",
        start_date=date(2026, month, 1),
        end_date=date(2026, month, end_day),
    )


def metric_binding(metric_id: str, unit: str = "BRL", aggregation: str = "SUM") -> DashboardMetricBindingV2:
    return DashboardMetricBindingV2(
        metric_id=metric_id,
        metric_registry_version="metric-registry/1",
        expected_unit=unit,
        expected_aggregation=aggregation,
        expected_fingerprint=f"fingerprint-{metric_id.replace('.', '-')}",
    )


def data_binding(
    binding_id: str,
    metric_id: str,
    shape: DashboardResultShapeV2,
    *,
    dimension_id: str | None = None,
    comparison: DashboardComparisonBindingV2 | None = None,
    aggregation: str = "SUM",
) -> DashboardDataBindingV2:
    dimensions = ()
    if dimension_id:
        dimensions = (
            DashboardDimensionBindingV2(
                dimension_id=dimension_id,
                display_label="Dimensão sintética",
                grouping_intent="TIME_BUCKET" if "month" in dimension_id else "CATEGORY",
                sorting_intent="ASC",
                maximum_visual_cardinality=50,
                drilldown_eligible=True,
            ),
        )
    return DashboardDataBindingV2(
        binding_id=binding_id,
        analytical_dataset_id="dataset.synthetic.sales",
        metrics=(metric_binding(metric_id, aggregation=aggregation),),
        dimensions=dimensions,
        period=fixed_period(7),
        comparison=comparison,
        expected_result_shape=shape,
        provenance=DashboardProvenanceRequirementV2(),
        classification=DashboardClassificationV2.TENANT_BUSINESS_DATA,
    )


def kpi_widget(widget_id: str, binding_id: str, title: str) -> DashboardKpiWidgetV2:
    return DashboardKpiWidgetV2(
        widget_type="KPI",
        identity=DashboardWidgetIdentityV2(widget_id=widget_id, canonical_name=widget_id),
        title=DashboardWidgetTitleV2(title=title),
        binding_id=binding_id,
        expected_result_shape=DashboardResultShapeV2.SCALAR,
        formatting=DashboardFormattingV2(),
        accessibility=widget_accessibility(title),
        states=widget_states(title),
    )


def line_widget(widget_id: str, binding_id: str, metric_id: str) -> DashboardLineChartWidgetV2:
    return DashboardLineChartWidgetV2(
        widget_type="LINE_CHART",
        identity=DashboardWidgetIdentityV2(widget_id=widget_id, canonical_name=widget_id),
        title=DashboardWidgetTitleV2(title="Evolução mensal"),
        binding_id=binding_id,
        expected_result_shape=DashboardResultShapeV2.TIME_SERIES,
        series=(
            DashboardChartSeriesV2(
                series_id="series.revenue",
                metric_id=metric_id,
                label="Faturamento",
                theme_token=DashboardThemeTokenV2.SERIES_1,
            ),
        ),
        category_axis=DashboardChartAxisV2(
            binding_id="dimension.month", label="Mês", scale="TIME"
        ),
        value_axis=DashboardChartAxisV2(
            binding_id=metric_id, label="Valor", scale="LINEAR"
        ),
        accessibility=widget_accessibility("Evolução mensal", chart=True),
        states=widget_states("evolução mensal"),
    )


def ranking_widget(widget_id: str, binding_id: str, metric_id: str) -> DashboardRankingWidgetV2:
    return DashboardRankingWidgetV2(
        widget_type="RANKING",
        identity=DashboardWidgetIdentityV2(widget_id=widget_id, canonical_name=widget_id),
        title=DashboardWidgetTitleV2(title="Ranking de produtos"),
        binding_id=binding_id,
        expected_result_shape=DashboardResultShapeV2.RANKING,
        metric_id=metric_id,
        ranking_dimension_id="dimension.product",
        accessibility=widget_accessibility("Ranking de produtos"),
        states=widget_states("ranking de produtos"),
    )


def table_widget(widget_id: str, binding_id: str) -> DashboardTableWidgetV2:
    return DashboardTableWidgetV2(
        widget_type="TABLE",
        identity=DashboardWidgetIdentityV2(widget_id=widget_id, canonical_name=widget_id),
        title=DashboardWidgetTitleV2(title="Tabela detalhada sintética"),
        binding_id=binding_id,
        expected_result_shape=DashboardResultShapeV2.TABLE,
        columns=(
            DashboardTableColumnV2(
                column_id="column.product",
                source_binding_id="dimension.product",
                column_kind="DIMENSION",
                label="Produto",
            ),
            DashboardTableColumnV2(
                column_id="column.revenue",
                source_binding_id="metric.revenue",
                column_kind="METRIC",
                label="Faturamento",
            ),
        ),
        truncation_indicator="REQUIRED",
        accessibility=widget_accessibility("Tabela detalhada sintética"),
        states=widget_states("tabela detalhada"),
    )


def _layout(widget_ids: tuple[str, ...]) -> DashboardLayoutV2:
    limits = {
        DashboardBreakpointV2.MOBILE: (0, 4),
        DashboardBreakpointV2.TABLET: (768, 8),
        DashboardBreakpointV2.DESKTOP: (1280, 12),
        DashboardBreakpointV2.ULTRAWIDE: (1920, 16),
    }
    return DashboardLayoutV2(
        breakpoints=tuple(
            DashboardResponsiveBreakpointV2(
                breakpoint=breakpoint,
                minimum_width_px=minimum_width,
                grid=DashboardGridV2(columns=columns),
                items=tuple(
                    DashboardGridItemV2(
                        widget_id=widget_id,
                        x=0,
                        y=index * 4,
                        width=columns,
                        height=4,
                        reading_order=index,
                    )
                    for index, widget_id in enumerate(widget_ids)
                ),
            )
            for breakpoint, (minimum_width, columns) in limits.items()
        )
    )


def assemble_blueprint(
    widgets: tuple,
    bindings: tuple[DashboardDataBindingV2, ...],
    *,
    blueprint_id: str,
    title: str,
    filters: tuple = (),
) -> DashboardBlueprintV2:
    widget_ids = tuple(widget.identity.widget_id for widget in widgets)
    return DashboardBlueprintV2(
        version=DashboardVersionV2(revision=DashboardRevisionV2()),
        identity=DashboardIdentityV2(
            blueprint_id=blueprint_id,
            canonical_name=blueprint_id,
            title=title,
            description="Dashboard sintético para certificação do contrato declarativo V2.",
        ),
        purpose=DashboardPurposeV2(
            purpose_id="purpose.executive.analysis",
            summary="Apoiar decisões usando apenas referências analíticas canônicas.",
            analytical_domains=("sales",),
            intended_decisions=("monitorar desempenho",),
        ),
        lifecycle=DashboardLifecycleV2.DRAFT,
        created_origin=DashboardOriginV2.HUMAN_AUTHORED,
        audience=DashboardAudienceV2(audience_ids=("audience.management",)),
        governance=DashboardGovernanceV2(),
        layout=_layout(widget_ids),
        widgets=widgets,
        data_bindings=bindings,
        filters=filters,
        accessibility=DashboardAccessibilityV2(
            accessible_title=title,
            accessible_description="Dashboard sintético com leitura e fallback textual governados.",
            reading_order=widget_ids,
            landmark_strategy="SECTIONS_WITH_LABELS",
            keyboard_navigation="DOCUMENT_ORDER",
            screen_reader_summary="Resumo textual dos indicadores e visualizações sintéticas.",
        ),
        compatibility=DashboardCompatibilityV2(
            required_features=("responsive_grid", "accessibility_summary", "provenance_panel")
        ),
    )


def build_executive_dashboard() -> DashboardBlueprintV2:
    metrics = (
        ("widget.revenue", "binding.revenue", "metric.revenue", "Faturamento"),
        ("widget.average.ticket", "binding.average.ticket", "metric.average.ticket", "Ticket médio"),
        ("widget.discount.total", "binding.discount.total", "metric.discount.total", "Desconto total"),
        ("widget.open.accounts", "binding.open.accounts", "metric.open.accounts", "Contas em aberto"),
    )
    widgets = tuple(kpi_widget(widget, binding, title) for widget, binding, _, title in metrics)
    bindings = tuple(data_binding(binding, metric, DashboardResultShapeV2.SCALAR) for _, binding, metric, _ in metrics)
    widgets += (
        line_widget("widget.revenue.series", "binding.revenue.series", "metric.revenue"),
        ranking_widget("widget.product.ranking", "binding.product.ranking", "metric.revenue"),
    )
    bindings += (
        data_binding(
            "binding.revenue.series",
            "metric.revenue",
            DashboardResultShapeV2.TIME_SERIES,
            dimension_id="dimension.month",
        ),
        data_binding(
            "binding.product.ranking",
            "metric.revenue",
            DashboardResultShapeV2.RANKING,
            dimension_id="dimension.product",
        ),
    )
    filter_widget_ids = tuple(widget.identity.widget_id for widget in widgets)
    filters = (
        DashboardSingleSelectFilterV2(
            filter_type="SINGLE_SELECT",
            filter_id="filter.branch",
            canonical_target_id="dimension.branch",
            scope=DashboardFilterScopeV2.DASHBOARD_GLOBAL,
            target_widget_ids=filter_widget_ids,
            default=DashboardFilterDefaultV2(mode="ALL_ALLOWED"),
            allowed_source="USER_SELECTION",
            accessibility_label="Filial",
        ),
    )
    return assemble_blueprint(
        widgets,
        bindings,
        blueprint_id="dashboard.executive.sales",
        title="Dashboard executivo sintético",
        filters=filters,
    )


def build_minimal_dashboard(
    *,
    blueprint_id: str = "dashboard.monthly.revenue",
    metric_id: str = "metric.revenue",
    title: str = "Faturamento mensal",
) -> DashboardBlueprintV2:
    widget = kpi_widget("widget.primary.kpi", "binding.primary.kpi", title)
    binding = data_binding("binding.primary.kpi", metric_id, DashboardResultShapeV2.SCALAR)
    return assemble_blueprint((widget,), (binding,), blueprint_id=blueprint_id, title=title)


def build_comparison_dashboard() -> DashboardBlueprintV2:
    comparison = DashboardComparisonBindingV2(
        current_period=fixed_period(7),
        baseline_period=fixed_period(6),
        relationship="PERIOD_OVER_PERIOD",
    )
    binding = data_binding(
        "binding.revenue.comparison",
        "metric.revenue",
        DashboardResultShapeV2.COMPARISON,
        comparison=comparison,
    )
    widget = DashboardComparisonKpiWidgetV2(
        widget_type="COMPARISON_KPI",
        identity=DashboardWidgetIdentityV2(
            widget_id="widget.revenue.comparison", canonical_name="widget.revenue.comparison"
        ),
        title=DashboardWidgetTitleV2(title="Faturamento julho versus junho"),
        binding_id=binding.binding_id,
        expected_result_shape=DashboardResultShapeV2.COMPARISON,
        zero_denominator_presentation="NOT_APPLICABLE",
        accessibility=widget_accessibility("Comparação de faturamento"),
        states=widget_states("comparação de faturamento"),
    )
    return assemble_blueprint(
        (widget,), (binding,), blueprint_id="dashboard.revenue.comparison", title="Comparação mensal"
    )


def build_table_dashboard() -> DashboardBlueprintV2:
    widget = table_widget("widget.sales.table", "binding.sales.table")
    binding = data_binding(
        "binding.sales.table",
        "metric.revenue",
        DashboardResultShapeV2.TABLE,
        dimension_id="dimension.product",
    )
    binding = binding.model_copy(
        update={"completeness": DashboardCompletenessRequirementV2.TRUNCATION_ALLOWED_WITH_NOTICE}
    )
    return assemble_blueprint(
        (widget,), (binding,), blueprint_id="dashboard.sales.table", title="Tabela truncation-aware"
    )


def build_ranking_dashboard() -> DashboardBlueprintV2:
    widget = ranking_widget("widget.product.ranking", "binding.product.ranking", "metric.revenue")
    binding = data_binding(
        "binding.product.ranking",
        "metric.revenue",
        DashboardResultShapeV2.RANKING,
        dimension_id="dimension.product",
    )
    return assemble_blueprint(
        (widget,), (binding,), blueprint_id="dashboard.product.ranking", title="Ranking de produtos"
    )


def golden_cases() -> dict[str, object]:
    executive = build_executive_dashboard()
    minimal = build_minimal_dashboard()
    comparison = build_comparison_dashboard()
    table = build_table_dashboard()
    ranking = build_ranking_dashboard()
    checksums = DashboardBlueprintCanonicalizer.canonicalize(executive).checksums
    visual_patch = DashboardVisualPatchV2(
        blueprint_id=executive.identity.blueprint_id,
        base_blueprint_checksum=checksums.blueprint_checksum,
        base_semantic_checksum=checksums.semantic_checksum,
        base_visual_revision=1,
        target_visual_revision=2,
        operations=(
            DashboardPatchOperationV2(
                operation=DashboardPatchOperationKindV2.REPLACE,
                path="/identity/title",
                value="Novo título visual",
            ),
        ),
    )
    semantic_patch = DashboardSemanticPatchV2(
        blueprint_id=executive.identity.blueprint_id,
        base_blueprint_checksum=checksums.blueprint_checksum,
        base_semantic_checksum=checksums.semantic_checksum,
        base_semantic_revision=1,
        target_semantic_revision=2,
        operations=(
            DashboardPatchOperationV2(
                operation=DashboardPatchOperationKindV2.REPLACE,
                path="/data_bindings/0/metrics/0/metric_id",
                value="metric.net.revenue",
            ),
        ),
    )
    visual_bad = visual_patch.model_dump(mode="json")
    visual_bad["operations"][0]["path"] = "/data_bindings/0/metrics/0/metric_id"
    visual_bad["operations"][0]["value"] = "metric.net.revenue"
    overlap = executive.model_dump(mode="json")
    overlap["layout"]["breakpoints"][0]["items"][1]["y"] = 0
    incompatible = minimal.model_dump(mode="json")
    incompatible["data_bindings"][0]["expected_result_shape"] = "TIME_SERIES"
    unsafe = minimal.model_dump(mode="json")
    unsafe["identity"]["title"] = "<script>alert(1)</script>"
    missing_a11y = minimal.model_dump(mode="json")
    del missing_a11y["accessibility"]
    wrong_version = minimal.model_dump(mode="json")
    wrong_version["version"]["contract_version"] = "lumina.dashboard-blueprint/3.0"
    return {
        "01_executive_sales": {"payload": executive.model_dump(mode="json"), "expected": "VALID"},
        "02_monthly_revenue": {"payload": minimal.model_dump(mode="json"), "expected": "VALID"},
        "03_june_july_comparison": {"payload": comparison.model_dump(mode="json"), "expected": "VALID"},
        "04_average_ticket": {"payload": build_minimal_dashboard(blueprint_id="dashboard.average.ticket", metric_id="metric.average.ticket", title="Ticket médio").model_dump(mode="json"), "expected": "VALID"},
        "05_total_and_average_discount": {"payload": executive.model_dump(mode="json"), "expected": "VALID"},
        "06_product_ranking": {"payload": ranking.model_dump(mode="json"), "expected": "VALID"},
        "07_open_accounts": {"payload": build_minimal_dashboard(blueprint_id="dashboard.open.accounts", metric_id="metric.open.accounts", title="Contas em aberto").model_dump(mode="json"), "expected": "VALID"},
        "08_inventory": {"payload": build_minimal_dashboard(blueprint_id="dashboard.inventory", metric_id="metric.inventory.balance", title="Estoque sintético").model_dump(mode="json"), "expected": "VALID"},
        "09_responsive_dashboard": {"payload": executive.model_dump(mode="json"), "expected": "VALID"},
        "10_truncation_aware_table": {"payload": table.model_dump(mode="json"), "expected": "VALID"},
        "11_public_provenance": {"payload": minimal.model_dump(mode="json"), "expected": "VALID"},
        "12_valid_visual_patch": {"payload": visual_patch.model_dump(mode="json"), "expected": "VALID"},
        "13_visual_patch_metric_blocked": {"payload": visual_bad, "expected": "INVALID"},
        "14_valid_semantic_patch": {"payload": semantic_patch.model_dump(mode="json"), "expected": "VALID"},
        "15_layout_overlap": {"payload": overlap, "expected": "INVALID"},
        "16_widget_binding_incompatible": {"payload": incompatible, "expected": "INVALID"},
        "17_html_javascript_blocked": {"payload": unsafe, "expected": "BLOCKED"},
        "18_accessibility_missing": {"payload": missing_a11y, "expected": "INVALID"},
        "19_legacy_adaptation": {"payload": {"name": "Legacy synthetic", "components": [{"id": "legacy-kpi", "type": "KPI_CARD", "title": "Indicador"}]}, "expected": "COMPLETE_WITH_WARNINGS"},
        "20_incompatible_version": {"payload": wrong_version, "expected": "UNSUPPORTED_VERSION"},
    }
